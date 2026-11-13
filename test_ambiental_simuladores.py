# -*- coding: utf-8 -*-
"""Testes do adendo: simuladores ligados aos descritores e validacao de adsorventes.

Nenhum teste usa rede nem motor pesado: os simuladores sao dublês injetados com
`adaptadores.definir_motores_simulacao`, que devolvem exatamente as chaves de
saida que o nucleo real devolve (medidas em
`auditoria/inventario_simuladores.json`).
"""
from __future__ import annotations

import pytest

from ambiental_backend import adaptadores, adsorventes, descritores_simuladores


@pytest.fixture
def motores_adsorcao():
    """Dublês com as mesmas chaves de saida dos simuladores reais."""
    registro = {
        "superficie": lambda pergunta, params: {
            "simulador": "Superficie", "area_m2g": params.get("area_m2g", 500)},
        "nano": lambda pergunta, params: {
            "simulador": "Nanomateriais",
            "area_relativa": 6.0 / float(params["diametro_nm"])},
        "cristalografia": lambda pergunta, params: {
            "simulador": "Cristalografia", "motor": "dublê",
            "densidade_g_cm3": 2.1, "d_espacamento_m": 3.5e-10},
        "dft": lambda pergunta, params: {
            "simulador": "Referencias internas", "material": params["material"],
            "bandgap_eV": 2.2, "tipo": "indireto"},
        "cfd": lambda pergunta, params: {
            "simulador": "CFD", "Reynolds": 1500.0, "regime": "laminar"},
        "poluicao": lambda pergunta, params: {
            "simulador": "Poluicao", "C_final": 36.7879},
        "metais": lambda pergunta, params: {
            "simulador": "Metais", "velocidade_som_ms": 5063.0},
    }
    adaptadores.definir_motores_simulacao(registro)
    try:
        yield registro
    finally:
        adaptadores.definir_motores_simulacao(None)


def criar_pesquisa(cliente, contaminante="chumbo", ph=5.0):
    corpo = {"pergunta": "adsorcao de chumbo em agua com carvao ativado",
             "material": "carvao ativado", "contaminante": contaminante,
             "aplicacao": "agua",
             "condicoes": {"Ce": 10.0, "pH": ph}}
    resposta = cliente.post("/api/research", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# --------------------------------------------------------------- mapa e painel
def test_mapa_descritor_para_simulador(cliente):
    mapa = cliente.get("/api/descritores/simuladores")
    assert mapa.status_code == 200, mapa.text
    dados = mapa.json()
    assert dados["total"] == 28
    por_codigo = {item["codigo"]: item for item in dados["descritores"]}

    assert por_codigo["D1"]["regra"]["requisitos"][0]["chave"] == "pontos"
    assert por_codigo["D1"]["modelos"], "D1 deve listar modelos de adsorcao"
    assert any(s["simulador"] == "superficie"
               for s in por_codigo["S3"]["simuladores"])
    # S6 saiu do antigo estado "sem_simulador": Boehm e FTIR passaram a existir
    # como motores proprios (ver motores_ambientais) e o mapa reflete isso.
    assert por_codigo["S6"]["cobertura"] != "sem_simulador"
    assert por_codigo["S6"]["simuladores"]
    assert por_codigo["S6"]["lacuna"] is None
    assert dados["sem_simulador"] == 0
    assert dados["com_regra_matematica"] == 10
    assert dados["com_simulador"] >= 4

    fontes_s3 = cliente.get("/api/descritores/S3/fontes").json()
    assert fontes_s3["codigo"] == "S3"
    assert cliente.get("/api/descritores/ZZ/fontes").status_code == 404


def test_matriz_traz_simuladores_por_descritor(cliente):
    matriz = cliente.get("/api/matriz").json()
    assert matriz["total"] == 28
    for item in matriz["descritores"]:
        assert "simuladores" in item and "cobertura" in item
        assert "exige_ensaio" in item
    por_codigo = {item["codigo"]: item for item in matriz["descritores"]}
    assert por_codigo["D6"]["regra_automatica"]["motor"].endswith("_regra_d6")
    # C1 (toxicidade) deixou de exigir ensaio para existir: o motor
    # perigo_composicao calcula o indicador GHS a partir da composicao.
    assert por_codigo["C1"]["exige_ensaio"] is False
    assert any(s["simulador"] == "perigo_composicao"
               for s in por_codigo["C1"]["simuladores"])
    assert matriz["fontes"]["com_regra_matematica"] == 10


def test_painel_simuladores_mostra_requisitos_e_historico(cliente,
                                                          motores_adsorcao):
    painel = cliente.get("/api/simulators").json()
    assert painel["total"] >= 24
    assert painel["com_descritor"] >= 4
    superficie = next(s for s in painel["simuladores"]
                      if s["simulador"] == "superficie")
    assert superficie["disponivel"] is True
    assert superficie["requisitos"][0]["chave"] == "area_m2g"
    assert superficie["requisitos"][0]["unidade"] == "m2/g"
    assert [d["codigo"] for d in superficie["descritores"]] == ["S3"]
    # O banco da sessao e' compartilhado pelos testes: o painel deve apenas ser
    # coerente entre contagem e ultima execucao.
    assert (superficie["ultima_execucao"] is None) == (
        superficie["total_execucoes"] == 0)

    detalhe = cliente.get("/api/simulators/superficie").json()
    assert detalhe["requisitos_detalhados"]["tipo"] == "simulador"
    assert detalhe["estado_atual"]["estado"] == "bloqueado_por_parametros"

    requisitos = cliente.get("/api/simulators/nano/requirements").json()
    assert requisitos["requisitos"][0]["chave"] == "diametro_nm"
    assert cliente.get("/api/simulators/inexistente").status_code == 404
    assert cliente.get("/api/simulators/inexistente/requirements"
                       ).status_code == 404


# -------------------------------------------------------------------- execucao
def test_execucao_manual_sem_pesquisa_nao_persiste(cliente, motores_adsorcao):
    saida = cliente.post("/api/simulators/nano/run",
                         json={"parametros": {"diametro_nm": 40}}).json()
    assert saida["estado"] == "ok", saida
    assert saida["persistido"] is False
    assert saida["executado"] is True
    codigos = {item["codigo"]: item for item in saida["descritores"]}
    assert codigos["S5"]["valor"] == 40.0
    assert codigos["S5"]["estado"] == "presente"
    assert codigos["S3"]["modo"] == "apoio"
    assert codigos["S3"]["valor_apoio"] == pytest.approx(0.15)


def test_execucao_bloqueada_por_falta_de_parametros(cliente, motores_adsorcao):
    saida = cliente.post("/api/simulators/superficie/run", json={}).json()
    assert saida["estado"] == "bloqueado_por_parametros"
    assert saida["executado"] is False
    assert saida["faltando"] == ["area_m2g"]
    assert saida["resultado"] is None

    forcar = cliente.post("/api/simulators/superficie/run",
                          json={"requer_completo": False}).json()
    assert forcar["estado"] == "ok_com_aproximacao"
    assert forcar["executado"] is True
    assert forcar["descritores"] == []
    assert any("padrao interno" in aviso for aviso in forcar["avisos"])


def test_execucao_com_pesquisa_atualiza_matriz(cliente, motores_adsorcao):
    pesquisa = criar_pesquisa(cliente)
    material = cliente.post("/api/research/%s/materials" % pesquisa["id"],
                            json={"nome": "carvao ativado teste"}).json()
    material_id = material["material"]["id"]

    saida = cliente.post("/api/simulators/superficie/run", json={
        "pesquisa_id": pesquisa["id"], "material_id": material_id,
        "parametros": {"area_m2g": 750}}).json()
    assert saida["persistido"] is True
    assert saida["estado"] == "ok"
    assert saida["descritores_atualizados"][0]["codigo"] == "S3"
    assert saida["descritores_atualizados"][0]["valor"] == 750.0

    matriz = cliente.get("/api/materials/%s/descriptors"
                         % material_id).json()
    linha = next(item for item in matriz["descritores"]
                 if item["codigo"] == "S3")
    assert linha["valor"] == 750.0
    assert linha["estado"] == "presente"
    assert "universal" in (linha["fonte"] or "")

    painel = cliente.get("/api/simulators?pesquisa_id=%s"
                         % pesquisa["id"]).json()
    superficie = next(s for s in painel["simuladores"]
                      if s["simulador"] == "superficie")
    assert superficie["total_execucoes"] == 1
    assert superficie["sucessos"] == 1
    assert superficie["ultima_execucao"]["estado"] == "ok"


# ------------------------------------------------------- validacao adsorvente
ISOTERMA_LANGMUIR = [
    {"Ce": 1.0, "qe": 6.666667},
    {"Ce": 2.0, "qe": 10.0},
    {"Ce": 5.0, "qe": 14.285714},
    {"Ce": 10.0, "qe": 16.666667},
]


def test_validacao_adsorvente_completa(cliente, motores_adsorcao):
    pesquisa = criar_pesquisa(cliente)
    resposta = cliente.post("/api/research/%s/adsorbent" % pesquisa["id"], json={
        "material": "carvao ativado de casca de arroz",
        "classe": "adsorvente",
        "composicao": [{"elemento": "C", "fracao_massica": 0.82},
                       {"elemento": "SiO2", "fracao_massica": 0.05}],
        "caracterizacao": {
            "area_superficial": {"valor": 750, "unidade": "m2/g",
                                 "metodo": "BET N2"},
            "pzc": {"valor": 6.5, "unidade": "pH"},
            "densidade_real": {"valor": 2.1, "unidade": "g/cm3"},
            "diametro_particula": {"valor": 40, "unidade": "nm"},
            "ctc": {"valor": 12.5, "unidade": "cmol/kg"},
        },
        "condicoes": {"pH": 5.0},
        "calculo": {"D1": {"pontos": ISOTERMA_LANGMUIR},
                    "D6": {"C0": 100, "Ce": 20, "volume_L": 0.1,
                           "massa_g": 0.05}},
        "simuladores": ["superficie", "nano", "cristalografia", "cfd"],
        "parametros_simulador": {"parametro_rede": 3.5, "densidade": 1000,
                                 "velocidade": 0.01, "diametro": 0.005,
                                 "viscosidade": 1e-3},
        "modelos": ["langmuir"],
    })
    assert resposta.status_code == 201, resposta.text
    dados = resposta.json()
    assert dados["material"]["criado"] is True
    assert dados["caracterizacao"]["propriedades_gravadas"] == 5
    assert dados["caracterizacao"]["composicao"] == 2

    descritores = {item["codigo"]: item for item in dados["descritores"]}
    assert descritores["S3"]["valor"] == 750.0
    assert descritores["P2"]["valor"] == 6.5
    assert descritores["S5"]["valor"] == 40.0
    assert descritores["P1"]["valor"] == 2.1
    assert descritores["P1"]["estado"] == "presente"
    assert descritores["D1"]["valor"] == pytest.approx(20.0, rel=1e-4)
    assert descritores["D2"]["valor"] == pytest.approx(0.5, rel=1e-4)
    assert descritores["D6"]["valor"] == pytest.approx(80.0, rel=1e-6)
    assert descritores["S1"]["valor_texto"].startswith("C 0.82")

    simuladores = {item["simulador"]: item for item in dados["simuladores"]}
    assert set(simuladores) == {"superficie", "nano", "cristalografia", "cfd"}
    for nome, item in simuladores.items():
        assert item["executado"] is True, (nome, item)
    assert simuladores["nano"]["resultado"]["area_relativa"] == pytest.approx(0.15)
    assert simuladores["cfd"]["resultado"]["Reynolds"] == 1500.0
    p1_simulador = next(item for item in simuladores["cristalografia"]["descritores"]
                        if item["codigo"] == "P1")
    assert p1_simulador["estado"] == "calculado"
    assert p1_simulador["valor"] == 2.1
    apoio_c7 = simuladores["cfd"]["descritores"][0]
    assert apoio_c7["codigo"] == "C7" and apoio_c7["modo"] == "apoio"
    assert apoio_c7["valor_apoio"] == 1500.0

    modelos = {item["modelo"]: item for item in dados["modelos"]}
    assert modelos["langmuir"]["estado"] == "calculado"
    assert modelos["langmuir"]["qe"] == pytest.approx(16.6667, rel=1e-3)
    assert "nao e' validacao experimental" in modelos["langmuir"]["natureza"]

    assert dados["compatibilidade"]["veredito"] == "desfavoravel"
    assert dados["compatibilidade"]["classe_contaminante"] == "cation_metalico"
    assert dados["compatibilidade"]["carga_superficie"] == "positiva"

    lacunas = {item["codigo"] for item in dados["lacunas_experimentais"]}
    assert {"D3", "D7", "C1", "C6"} <= lacunas
    assert dados["preenchimento"]["com_dado"] >= 7

    salvo = cliente.get("/api/research/%s/adsorbent" % pesquisa["id"]).json()
    assert salvo["material"]["nome"] == "carvao ativado de casca de arroz"
    codigos = {item["codigo"] for item in salvo["descritores"]}
    assert {"S3", "P2", "D1", "D2"} <= codigos
    assert any(item["simulador"] == "superficie"
               for item in salvo["simulacoes"])

def test_validacao_minima_marca_lacunas_e_nao_inventa(cliente, motores_adsorcao):
    pesquisa = criar_pesquisa(cliente)
    dados = cliente.post("/api/research/%s/adsorbent" % pesquisa["id"],
                         json={"material": "zeolita 4A"}).json()
    assert dados["caracterizacao"]["propriedades_gravadas"] == 0
    assert dados["descritores"] == []
    assert len(dados["lacunas_experimentais"]) == 10
    modelos = {item["modelo"]: item for item in dados["modelos"]}
    assert modelos["langmuir"]["estado"] == "bloqueado_por_parametros"
    assert "qmax" in modelos["langmuir"]["faltando"]
    assert modelos["pfo_cinetica"]["estado"] == "bloqueado_por_parametros"
    assert dados["compatibilidade"]["veredito"] == "indeterminado"
    assert "P2 (PZC)" in dados["compatibilidade"]["faltando"]
    assert dados["simuladores"] == []


def test_propriedade_sem_descritor_nao_vira_descritor(cliente, motores_adsorcao):
    pesquisa = criar_pesquisa(cliente)
    dados = cliente.post("/api/research/%s/adsorbent" % pesquisa["id"], json={
        "material": "biochar de lodo",
        "caracterizacao": {"cor_superficial": {"valor": "preto"},
                           "area_superficial": {"valor": 320,
                                                "unidade": "m2/g"}},
    }).json()
    assert "cor_superficial" in dados["caracterizacao"]["nao_mapeadas"]
    codigos = [item["codigo"] for item in dados["descritores"]]
    assert codigos == ["S3"]
    assert dados["material"]["criado"] is True


def test_adsorvente_exige_material(cliente):
    pesquisa = criar_pesquisa(cliente)
    resposta = cliente.post("/api/research/%s/adsorbent" % pesquisa["id"],
                            json={"caracterizacao": {"pzc": 6.0}})
    assert resposta.status_code == 400
    assert resposta.json()["erro"]["codigo"] == "entrada_invalida"
    assert cliente.post("/api/research/pesq_inexistente/adsorbent",
                        json={"material": "x"}).status_code == 404


# ------------------------------------------------------------- prova conceito
def test_prova_de_conceito_por_material(cliente, motores_adsorcao):
    pesquisa = criar_pesquisa(cliente)
    validacao = cliente.post("/api/research/%s/adsorbent" % pesquisa["id"],
                             json={
        "material": "carvao ativado referencia interna",
        "caracterizacao": {"area_superficial": {"valor": 750,
                                                "unidade": "m2/g"},
                           "pzc": {"valor": 3.5, "unidade": "pH"}},
        "condicoes": {"pH": 5.5},
        "calculo": {"D1": {"pontos": ISOTERMA_LANGMUIR}},
        "simuladores": ["superficie"],
        "modelos": ["langmuir"],
    }).json()
    material_id = validacao["material"]["id"]

    prova = cliente.post("/api/research/%s/proof-of-concept" % pesquisa["id"],
                         json={"material_id": material_id,
                               "validacao": {"simuladores": ["superficie"],
                                             "modelos": ["langmuir"]}})
    assert prova.status_code == 200, prova.text
    dados = prova.json()
    passos = {item["passo"]: item for item in dados["passos"]}
    assert "validacao_adsorvente" in passos
    assert passos["simulador_superficie"]["estado"] == "ok"
    assert passos["modelos_adsorcao"]["estado"] == "ok"
    assert passos["compatibilidade"]["estado"] == "ok"   # pH > PZC, cation
    assert "lacunas_experimentais" in passos
    assert dados["resultado"]["validacao_adsorvente"]["material"]["id"] == material_id
    assert dados["resultado"]["calculo"]["q_e"] > 0

    anterior = cliente.get("/api/research/%s/proof-of-concept"
                           % pesquisa["id"]).json()
    assert anterior["id"] == dados["id"]


def test_compatibilidade_regra_explicita():
    favoravel = adsorventes.compatibilidade("chumbo", 3.5, 5.5)
    assert favoravel["veredito"] == "favoravel"
    assert favoravel["carga_superficie"] == "negativa"
    anion = adsorventes.compatibilidade("arsenato", 3.5, 5.5)
    assert anion["classe_contaminante"] == "oxianion"
    assert anion["veredito"] == "desfavoravel"
    sem_dado = adsorventes.compatibilidade("chumbo", None, 5.5)
    assert sem_dado["veredito"] == "indeterminado"
    assert "P2 (PZC)" in sem_dado["faltando"]


def test_classificacao_e_requisitos_pendentes():
    assert descritores_simuladores.requisitos_pendentes(
        "cfd", {"densidade": 1000}) == ["velocidade", "diametro"]
    assert descritores_simuladores.classificar(
        "superficie", {"area_m2g": 700})["estado"] == "pronto"
    assert descritores_simuladores.classificar(
        "superficie", {})["estado"] == "bloqueado_por_parametros"
    assert descritores_simuladores.classificar(
        "cristalografia",
        {"parametro_rede": 3.5})["estado"] == "ok_com_aproximacao"
    assert descritores_simuladores.classificar("nada", {})["estado"] == "sem_mapeamento"



