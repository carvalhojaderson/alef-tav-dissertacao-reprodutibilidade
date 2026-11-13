# -*- coding: utf-8 -*-
"""Testes dos cruzamentos 7x4, dos pesos e da caracterizacao dos componentes.

O que estes testes protegem:

* os 28 cruzamentos (7 dimensoes informacionais x 4 componentes) existem e
  todo descritor 7Dx4 esta' classificado em pelo menos um deles;
* a matriz e' dinamica: celula sem dado volta como lacuna, nunca como zero;
* o peso sai dos criterios do projeto (qualidade, pertinencia, entropia,
  redundancia) e normaliza em 1 dentro do cruzamento;
* entropia e redundancia so' aparecem quando ha' material suficiente;
* a caracterizacao dos quatro componentes grava origem/estado e alimenta o
  descritor e os simuladores.
"""
from __future__ import annotations

import pytest

from ambiental_backend import matriz_7d4, matriz_cruzamentos


def _linhas(**valores):
    return [{"codigo": codigo, "estado": estado, "valor": valor,
             "unidade": "", "fonte": "teste"}
            for codigo, (valor, estado) in valores.items()]


def test_estrutura_tem_28_cruzamentos_e_cobre_os_28_descritores():
    estrutura = matriz_cruzamentos.estrutura()
    assert estrutura["total_dimensoes"] == 7
    assert estrutura["total_componentes"] == 4
    assert estrutura["total_cruzamentos"] == 28
    assert [item["letra"] for item in estrutura["dimensoes"]] == [
        "E", "P", "D", "S", "I", "C", "O"]
    assert not estrutura["sem_cruzamento"]
    assert set(estrutura["relacoes"]) == set(matriz_7d4.DESCRITORES_POR_CODIGO)


def test_cada_cruzamento_tem_id_unico_e_lista_de_candidatos():
    celulas = matriz_cruzamentos.celulas()
    ids = [celula["id"] for celula in celulas]
    assert len(ids) == len(set(ids)) == 28
    for celula in celulas:
        assert celula["descritores_possiveis"] or celula["parametros_possiveis"], \
            celula["id"]


def test_descritor_pode_informar_mais_de_um_cruzamento():
    relacoes = matriz_cruzamentos.relacoes("P2")
    assert [item["dimensao"] for item in relacoes] == ["S", "I"]
    assert relacoes[0]["principal"] is True
    assert relacoes[1]["principal"] is False


def test_matriz_vazia_nao_inventa_valor_nem_zero():
    montada = matriz_cruzamentos.montar(material_id="m1")
    assert len(montada["cruzamentos"]) == 28
    for celula in montada["cruzamentos"]:
        assert celula["extras"]["com_dado"] == 0
        assert celula["extras"]["cobertura"] == 0
        assert celula["extras"]["indice_qualidade"] == 0
        assert celula["extras"]["indice_comparativo"] is None
        for item in celula["descritores"]:
            assert item["peso"] == 0
            assert item["valor"] is None
    assert montada["resumo"]["cruzamentos_com_dado"] == 0



def test_celula_com_dado_recebe_peso_normalizado_em_1():
    linhas = _linhas(S3=(750.0, "validado"), S1=(0.9, "presente"))
    montada = matriz_cruzamentos.montar(linhas=linhas, material_id="m1",
                                       aplicacao="agua")
    celula = next(item for item in montada["cruzamentos"]
                  if item["id"] == "D-adsorvente")
    pesos = [item["peso"] for item in celula["descritores"]]
    assert sum(pesos) == pytest.approx(1.0, abs=1e-6)
    validado = next(item for item in celula["descritores"]
                    if item["codigo"] == "S3")
    presente = next(item for item in celula["descritores"]
                    if item["codigo"] == "S1")
    assert validado["peso"] > presente["peso"]
    assert validado["qualidade"] == 1.0
    assert presente["qualidade"] == 0.85
    assert "S4" in celula["extras"]["lacunas"]


def test_ausencia_de_dado_nao_recebe_peso():
    linhas = _linhas(S3=(750.0, "presente"))
    montada = matriz_cruzamentos.montar(linhas=linhas, material_id="m1")
    celula = next(item for item in montada["cruzamentos"]
                  if item["id"] == "D-adsorvente")
    ausente = next(item for item in celula["descritores"]
                   if item["codigo"] == "S4")
    assert ausente["estado"] == "ausente"
    assert ausente["peso"] == 0.0
    assert ausente["valor"] is None


def test_entropia_e_indice_comparativo_so_com_dois_materiais():
    linhas = _linhas(S3=(750.0, "validado"))
    so_um = matriz_cruzamentos.montar(
        linhas=linhas, material_id="m1",
        valores_por_material={"m1": {"S3": 750.0}})
    celula = next(item for item in so_um["cruzamentos"]
                  if item["id"] == "D-adsorvente")
    assert celula["extras"]["indice_comparativo"] is None
    assert "dois materiais" in (celula["extras"]["motivo_indice"] or "")

    dois = matriz_cruzamentos.montar(
        linhas=linhas, material_id="m1",
        valores_por_material={"m1": {"S3": 750.0}, "m2": {"S3": 250.0}})
    celula = next(item for item in dois["cruzamentos"]
                  if item["id"] == "D-adsorvente")
    assert celula["extras"]["indice_comparativo"] == pytest.approx(1.0)
    s3 = next(item for item in celula["descritores"] if item["codigo"] == "S3")
    assert s3["utilidade"] == pytest.approx(1.0)
    assert s3["valor_normalizado"] == pytest.approx(1.0)


def test_redundancia_exige_quatro_materiais_e_correlacao_significativa():
    linhas = _linhas(S3=(100.0, "validado"), D1=(100.0, "validado"))
    colineares = matriz_cruzamentos.montar(
        linhas=linhas, material_id="m1",
        valores_por_material={"m%d" % i: {"S3": i * 100.0, "D1": i * 100.0}
                              for i in range(1, 5)})
    s3 = next(item for item in next(
        celula for celula in colineares["cruzamentos"]
        if celula["id"] == "D-adsorvente")["descritores"]
        if item["codigo"] == "S3")
    assert s3["redundancia"] == pytest.approx(1.0, abs=1e-6)

    poucos = matriz_cruzamentos.montar(
        linhas=linhas, material_id="m1",
        valores_por_material={"m1": {"S3": 1.0, "D1": 1.0},
                              "m2": {"S3": 2.0, "D1": 2.0},
                              "m3": {"S3": 3.0, "D1": 3.0}})
    s3_poucos = next(item for item in next(
        celula for celula in poucos["cruzamentos"]
        if celula["id"] == "D-adsorvente")["descritores"]
        if item["codigo"] == "S3")
    assert s3_poucos["redundancia"] == 0.0


def test_parametros_de_componente_entram_no_cruzamento():
    montada = matriz_cruzamentos.montar(
        parametros={"ph": 5.5, "temperatura": 25.0})
    celula = next(item for item in montada["cruzamentos"]
                  if item["id"] == "O-meio")
    ph = next(item for item in celula["parametros"] if item["chave"] == "ph")
    assert ph["valor"] == 5.5
    assert ph["estado"] == "presente"
    assert celula["extras"]["com_parametro"] == 2
    assert celula["extras"]["com_dado"] == 0


def test_exportacao_csv_traz_cabecalho_e_ausentes():
    linhas = _linhas(S3=(750.0, "validado"))
    montada = matriz_cruzamentos.montar(linhas=linhas, material_id="m1",
                                       parametros={"ph": 7.0})
    texto = matriz_cruzamentos.exportar_csv(montada)
    linhas_csv = texto.strip().splitlines()
    assert linhas_csv[0].startswith("cruzamento;dimensao;componente;tipo;codigo")
    assert any(";descritor;S3;" in linha for linha in linhas_csv)
    assert any(";parametro;ph;" in linha for linha in linhas_csv)
    assert any(";ausente;" in linha for linha in linhas_csv)


def test_metodo_declara_a_formula_dos_pesos():
    metodo = matriz_cruzamentos.montar()["metodo"]
    assert "entropia" in metodo["utilidade"]
    assert "Pearson" in metodo["redundancia"]
    assert metodo["qualidade_por_estado"]["ausente"] == 0.0



# --------------------------------------------------------------------- API
def _pesquisa_com_material(cliente, nome="carvao de casca de coco"):
    pesquisa = cliente.post("/api/research", json={
        "pergunta": "adsorcao de chumbo em carvao ativado",
        "aplicacao": "agua", "contaminante": "chumbo"}).json()
    material = cliente.post("/api/research/%s/materials" % pesquisa["id"],
                            json={"nome": nome}).json()
    material = material.get("material", material)
    return pesquisa["id"], material["id"]


def test_api_estrutura_publica_os_28_cruzamentos(cliente):
    dados = cliente.get("/api/matriz/estrutura").json()
    assert dados["total_cruzamentos"] == 28
    assert len(dados["dimensoes"]) == 7
    assert len(dados["componentes"]) == 4
    assert dados["componentes_parametros"]["total"] >= 50
    assert not dados["sem_cruzamento"]


def test_api_cruzamentos_monta_matriz_do_material(cliente):
    pesquisa_id, material_id = _pesquisa_com_material(cliente)
    cliente.post("/api/materials/%s/components/adsorvente" % material_id, json={
        "pesquisa_id": pesquisa_id,
        "parametros": [{"chave": "area_superficial", "valor": 640.0,
                        "metodo": "BET N2"}]})
    dados = cliente.get("/api/matriz/cruzamentos", params={
        "material_id": material_id, "pesquisa_id": pesquisa_id}).json()
    assert len(dados["cruzamentos"]) == 28
    celula = next(item for item in dados["cruzamentos"]
                  if item["id"] == "D-adsorvente")
    s3 = next(item for item in celula["descritores"] if item["codigo"] == "S3")
    assert s3["peso"] == pytest.approx(1.0)
    assert s3["estado"] == "presente"
    assert "BET N2" in (s3["fonte"] or "")
    assert celula["extras"]["com_parametro"] == 1
    assert dados["resumo"]["cruzamentos_com_dado"] >= 1


def test_api_componente_invalido_devolve_400(cliente):
    _pesquisa_id, material_id = _pesquisa_com_material(cliente)
    errado = cliente.post("/api/materials/%s/components/meio" % material_id,
                          json={"chave": "area_superficial", "valor": 10})
    assert errado.status_code == 400
    assert "adsorvente" in errado.json()["erro"]["mensagem"]
    desconhecido = cliente.post("/api/materials/%s/components/meio" % material_id,
                                json={"chave": "inventado", "valor": 1})
    assert desconhecido.status_code == 400
    assert cliente.post("/api/materials/%s/components/componente_x" % material_id,
                        json={"chave": "ph", "valor": 7}).status_code == 400


def test_api_simulador_le_a_caracterizacao_do_material(cliente):
    pesquisa_id, material_id = _pesquisa_com_material(cliente)
    cliente.post("/api/materials/%s/components/adsorvente" % material_id, json={
        "pesquisa_id": pesquisa_id,
        "parametros": [{"chave": "area_superficial", "valor": 512.0}]})
    dados = cliente.get("/api/simulators/superficie/parameters",
                        params={"material_id": material_id}).json()
    assert dados["parametros"]["area_m2g"] == 512.0
    assert dados["estado"]["estado"] == "pronto"
    requisito = next(item for item in dados["requisitos"]
                     if item["chave"] == "area_m2g")
    assert requisito["valor_sugerido"] == 512.0
    assert requisito["fonte"].startswith("caracterizacao:")


def test_api_exporta_a_matriz_em_csv(cliente):
    pesquisa_id, material_id = _pesquisa_com_material(cliente)
    cliente.post("/api/materials/%s/components/meio" % material_id, json={
        "pesquisa_id": pesquisa_id,
        "parametros": [{"chave": "ph", "valor": 6.5}]})
    resposta = cliente.get("/api/matriz/exportar", params={
        "material_id": material_id, "pesquisa_id": pesquisa_id})
    assert resposta.status_code == 200
    assert "text/csv" in resposta.headers["content-type"]
    assert "attachment" in resposta.headers["content-disposition"]
    assert resposta.text.splitlines()[0].startswith("cruzamento;dimensao")
    assert ";parametro;ph;" in resposta.text

