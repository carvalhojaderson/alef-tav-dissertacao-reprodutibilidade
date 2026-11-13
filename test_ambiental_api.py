# -*- coding: utf-8 -*-
"""Testes do backend ambiental (API + persistencia + motores).

Nenhum teste usa rede: a busca bibliografica e os simuladores sao substituidos
por dublês (`busca_falsa`, `motores_falsos`). O que se prova:

    - a matriz 7Dx4 tem 28 descritores e devolve estado por descritor;
    - o fluxo pergunta -> protocolo -> material -> descritores -> evidencia ->
      simulacao -> viabilidade -> prova -> relatorio grava tudo no banco;
    - erro de entrada volta como 400/404/422 com codigo estavel;
    - simulacao assincrona devolve tarefa e conclui.
"""
from __future__ import annotations

import time

import pytest


def criar_pesquisa(cliente, pergunta=None, material="carvao ativado"):
    """Cria uma pesquisa valida e devolve o JSON (helper dos testes)."""
    corpo = {"pergunta": pergunta or (
        "adsorcao de chumbo em agua com carvao ativado"),
        "material": material, "contaminante": "chumbo",
        "aplicacao": "agua", "condicoes": {"Ce": 10.0}}
    resposta = cliente.post("/api/research", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# ------------------------------------------------------------------------ base
def test_health_e_matriz(cliente):
    resposta = cliente.get("/api/health")
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["estado"] == "ok"
    assert dados["matriz"] == {"dimensoes": 4, "descritores": 28}
    assert "banco" in dados and "motores" in dados

    matriz = cliente.get("/api/matriz").json()
    assert matriz["total"] == 28
    codigos = [item["codigo"] for item in matriz["descritores"]]
    assert len(set(codigos)) == 28
    for item in matriz["descritores"]:
        assert item["unidade"] and item["regra"] and item["definicao"]
    assert cliente.get("/api/matriz/S3").json()["nome"].startswith("Area")


def test_matriz_calcular_d6(cliente):
    resposta = cliente.post("/api/matriz/D6/calcular",
                            json={"C0": 100, "Ce": 20})
    dados = resposta.json()
    assert dados["estado"] == "calculado"
    assert abs(dados["valor"] - 80.0) < 1e-9


def test_openapi_publicado(cliente):
    esquema = cliente.get("/openapi.json").json()
    caminhos = esquema["paths"]
    for rota in ("/api/research", "/api/research/{pesquisa_id}",
                 "/api/research/{pesquisa_id}/protocol",
                 "/api/research/{pesquisa_id}/materials",
                 "/api/materials", "/api/materials/{material_id}",
                 "/api/materials/{material_id}/descriptors",
                 "/api/research/{pesquisa_id}/evidence",
                 "/api/research/{pesquisa_id}/evidence/search",
                 "/api/research/{pesquisa_id}/simulations",
                 "/api/research/{pesquisa_id}/viability",
                 "/api/research/{pesquisa_id}/proof-of-concept",
                 "/api/research/{pesquisa_id}/reports",
                 "/api/reports/{relatorio_id}", "/api/health"):
        assert rota in caminhos, rota


# -------------------------------------------------------------------- pesquisa
def test_pesquisa_ciclo_basico(cliente):
    criada = criar_pesquisa(cliente)
    assert criada["id"].startswith("pesq_")
    assert criada["estado"] == "criada"
    assert criada["estrutura_da_pergunta"]["contaminante"] == "chumbo"
    assert criada["estrutura_da_pergunta"]["aplicacao"] == "agua"

    lida = cliente.get("/api/research/%s" % criada["id"]).json()
    assert lida["id"] == criada["id"]

    lista = cliente.get("/api/research").json()
    assert any(item["id"] == criada["id"] for item in lista["pesquisas"])


def test_erros_de_entrada(cliente):
    curta = cliente.post("/api/research", json={"pergunta": "curta"})
    assert curta.status_code == 400
    assert curta.json()["erro"]["codigo"] == "entrada_invalida"

    sem_corpo = cliente.post("/api/research", json={})
    assert sem_corpo.status_code == 422
    assert sem_corpo.json()["erro"]["codigo"] == "validacao"

    inexistente = cliente.get("/api/research/pesq_naoexiste")
    assert inexistente.status_code == 404
    assert inexistente.json()["erro"]["codigo"] == "nao_encontrado"


# ------------------------------------------------------------------- protocolo
def test_protocolo_seleciona_descritores(cliente, motores_falsos):
    pesquisa = criar_pesquisa(cliente)
    antes = cliente.get("/api/research/%s/protocol" % pesquisa["id"])
    assert antes.status_code == 404
    assert antes.json()["erro"]["codigo"] == "protocolo_ausente"

    criado = cliente.post("/api/research/%s/protocol" % pesquisa["id"], json={})
    assert criado.status_code == 201, criado.text
    protocolo = criado.json()
    assert len(protocolo["descritores"]) == 28
    assert protocolo["criterios"]["tolerancia_comparacao"] == 0.2
    assert protocolo["perguntas"]["pergunta_de_pesquisa"]
    codigos = [item["codigo"] for item in protocolo["descritores"]]
    assert "D1" in codigos and "D6" in codigos

    lido = cliente.get("/api/research/%s/protocol" % pesquisa["id"]).json()
    assert lido["id"] == protocolo["id"]


# -------------------------------------------------------------------- materiais
def test_material_e_matriz_do_material(cliente):
    pesquisa = criar_pesquisa(cliente)
    criado = cliente.post("/api/research/%s/materials" % pesquisa["id"], json={
        "nome": "carvao ativado de casca de coco", "formula": "C",
        "classe": "adsorvente",
        "composicao": [{"elemento": "C", "fracao_massica": 0.9}],
        "propriedades": [{"nome": "area_bet", "valor": 750,
                          "unidade": "m2/g", "origem": "ensaio"}]})
    assert criado.status_code == 201, criado.text
    material = criado.json()["material"]
    assert criado.json()["criado"] is True

    detalhe = cliente.get("/api/materials/%s" % material["id"]).json()
    assert detalhe["composicao"][0]["elemento"] == "C"
    assert detalhe["propriedades"][0]["valor"] == 750

    matriz = cliente.get("/api/materials/%s/descriptors" % material["id"]).json()
    assert matriz["total"] == 28
    assert matriz["preenchimento"]["com_dado"] == 0
    assert all(item["estado"] == "ausente" for item in matriz["descritores"])


def test_reaproveita_material_existente(cliente):
    pesquisa = criar_pesquisa(cliente)
    primeiro = cliente.post("/api/research/%s/materials" % pesquisa["id"],
                            json={"nome": "zeolita 4A"}).json()
    segundo = cliente.post("/api/research/%s/materials" % pesquisa["id"],
                           json={"nome": "Zeolita 4a"}).json()
    assert segundo["criado"] is False
    assert segundo["material"]["id"] == primeiro["material"]["id"]


def test_descritores_calculados_e_informados(cliente):
    pesquisa = criar_pesquisa(cliente)
    material = cliente.post(
        "/api/research/%s/materials" % pesquisa["id"],
        json={"nome": "biochar de eucalipto"}).json()["material"]
    resposta = cliente.post(
        "/api/research/%s/materials/%s/descriptors"
        % (pesquisa["id"], material["id"]),
        json={"calculo": {"D1": {"pontos": [{"Ce": 5, "qe": 20},
                                            {"Ce": 10, "qe": 30},
                                            {"Ce": 20, "qe": 42}]},
                          "D6": {"C0": 100, "Ce": 20}},
              "valores": {"S3": {"valor": 750, "unidade": "m2/g",
                                 "estado": "presente", "fonte": "artigo"}}})
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    estados = {item["codigo"]: item["estado"] for item in dados["descritores"]}
    assert estados["D1"] == "calculado"
    assert estados["D6"] == "calculado"
    assert estados["S3"] == "presente"
    assert dados["preenchimento"]["com_dado"] == 3
    d1 = next(item for item in dados["descritores"] if item["codigo"] == "D1")
    assert abs(d1["valor"] - 66.8182) < 0.01


def test_descritor_desconhecido(cliente):
    pesquisa = criar_pesquisa(cliente)
    material = cliente.post("/api/research/%s/materials" % pesquisa["id"],
                            json={"nome": "argila"}).json()["material"]
    resposta = cliente.post(
        "/api/research/%s/materials/%s/descriptors"
        % (pesquisa["id"], material["id"]),
        json={"valores": {"Z9": {"valor": 1}}})
    assert resposta.status_code == 400
    assert "Z9" in resposta.json()["erro"]["mensagem"]


# -------------------------------------------------------------------- evidencias
def test_evidencias_persistidas_e_deduplicadas(cliente, busca_falsa):
    pesquisa = criar_pesquisa(cliente)
    primeira = cliente.post("/api/research/%s/evidence/search" % pesquisa["id"],
                            json={"n": 2, "max_bases": 2})
    assert primeira.status_code == 200, primeira.text
    dados = primeira.json()
    assert dados["novas"] == 2 and dados["repetidas"] == 0
    assert dados["motor"] == "pesquisa_cientifica.pesquisar"

    segunda = cliente.post("/api/research/%s/evidence/search" % pesquisa["id"],
                           json={"n": 2})
    assert segunda.json()["repetidas"] == 2

    listadas = cliente.get("/api/research/%s/evidence" % pesquisa["id"]).json()
    assert listadas["total"] == 2
    assert listadas["evidencias"][0]["titulo"]
    assert listadas["evidencias"][0]["relevancia"] >= 0


# ------------------------------------------------------------------- simulacoes
def test_simulacao_sincrona(cliente, motores_falsos):
    pesquisa = criar_pesquisa(cliente)
    resposta = cliente.post("/api/research/%s/simulations" % pesquisa["id"],
                            json={"simuladores": ["superficie"],
                                  "parametros": {"qmax": 120},
                                  "sincrono": True})
    assert resposta.status_code == 202, resposta.text
    dados = resposta.json()
    assert dados["sincrono"] is True
    simulacao = dados["simulacoes"][0]
    assert simulacao["estado"] == "ok"
    assert simulacao["resultado"]["qmax_mg_g"] == 120.0
    assert simulacao["duracao_s"] >= 0

    listadas = cliente.get("/api/research/%s/simulations"
                           % pesquisa["id"]).json()
    assert listadas["total"] == 1
    detalhe = cliente.get("/api/research/%s/simulations/%s"
                          % (pesquisa["id"], simulacao["id"])).json()
    assert detalhe["id"] == simulacao["id"]


def test_simulacao_assincrona_conclui(cliente, motores_falsos):
    pesquisa = criar_pesquisa(cliente)
    resposta = cliente.post("/api/research/%s/simulations" % pesquisa["id"],
                            json={"simuladores": ["metais"]})
    assert resposta.status_code == 202
    dados = resposta.json()
    assert dados["sincrono"] is False
    assert dados["tarefa_ids"]

    tarefa_id = dados["tarefa_ids"][0]
    estado = None
    for _ in range(60):
        estado = cliente.get("/api/tasks/%s" % tarefa_id).json()
        if estado["estado"] in ("concluida", "falhou"):
            break
        time.sleep(0.2)
    assert estado["estado"] == "concluida", estado
    assert estado["progresso"] == 100

    listadas = cliente.get("/api/research/%s/simulations"
                           % pesquisa["id"]).json()
    assert listadas["simulacoes"][0]["estado"] == "ok"


def test_simulador_desconhecido(cliente, motores_falsos):
    pesquisa = criar_pesquisa(cliente)
    resposta = cliente.post("/api/research/%s/simulations" % pesquisa["id"],
                            json={"simuladores": ["nao_existe"],
                                  "sincrono": True})
    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "simulador_desconhecido"


def test_simulacao_de_outra_pesquisa_nao_vaza(cliente, motores_falsos):
    primeira = criar_pesquisa(cliente)
    segunda = criar_pesquisa(cliente)
    simulacao = cliente.post("/api/research/%s/simulations" % primeira["id"],
                             json={"simuladores": ["superficie"],
                                   "sincrono": True}).json()["simulacoes"][0]
    resposta = cliente.get("/api/research/%s/simulations/%s"
                           % (segunda["id"], simulacao["id"]))
    assert resposta.status_code == 404


# --------------------------------------------------------------- viabilidade
def _fluxo_completo(cliente):
    pesquisa = criar_pesquisa(cliente)
    cliente.post("/api/research/%s/protocol" % pesquisa["id"], json={})
    material = cliente.post(
        "/api/research/%s/materials" % pesquisa["id"],
        json={"nome": "biochar de pirolise"}).json()["material"]
    cliente.post("/api/research/%s/materials/%s/descriptors"
                 % (pesquisa["id"], material["id"]),
                 json={"calculo": {"D1": {"pontos": [{"Ce": 5, "qe": 20},
                                                     {"Ce": 10, "qe": 30},
                                                     {"Ce": 20, "qe": 42}]},
                                   "D2": {"pontos": [{"Ce": 5, "qe": 20},
                                                     {"Ce": 10, "qe": 30},
                                                     {"Ce": 20, "qe": 42}],
                                          "C0": 10},
                                   "D6": {"C0": 100, "Ce": 20}},
                       "valores": {"S3": {"valor": 750, "unidade": "m2/g"},
                                   "P7": {"valor": 0.2, "unidade": "%"},
                                   "C1": {"valor_texto": "GHS09"},
                                   "C6": {"valor_texto": "CONAMA 430"}}})
    cliente.post("/api/research/%s/evidence/search" % pesquisa["id"], json={})
    cliente.post("/api/research/%s/simulations" % pesquisa["id"],
                 json={"simuladores": ["superficie"], "sincrono": True})
    return pesquisa, material


def test_viabilidade_e_prova_de_conceito(cliente, motores_falsos, busca_falsa):
    pesquisa, _material = _fluxo_completo(cliente)
    viabilidade = cliente.post("/api/research/%s/viability" % pesquisa["id"],
                               json={"tolerancia": 0.2})
    assert viabilidade.status_code == 200, viabilidade.text
    dados = viabilidade.json()
    assert 0 <= dados["pontuacao"] <= 100
    assert dados["classificacao"] in ("viavel", "viavel_com_restricoes",
                                      "requer_dados",
                                      "inviavel_no_estado_atual")
    assert len(dados["criterios"]) == 6
    assert cliente.get("/api/research/%s/viability"
                       % pesquisa["id"]).json()["id"] == dados["id"]

    prova = cliente.post("/api/research/%s/proof-of-concept" % pesquisa["id"])
    assert prova.status_code == 200, prova.text
    corpo = prova.json()
    passos = {item["passo"]: item["estado"] for item in corpo["passos"]}
    assert passos["calculo_isoterma"] == "ok"
    assert passos["simulacoes"] == "ok"
    assert corpo["resultado"]["demonstravel"] is True


# -------------------------------------------------------------------- relatorios
def test_relatorio_markdown_e_json(cliente, motores_falsos, busca_falsa):
    import os

    pesquisa, _material = _fluxo_completo(cliente)
    cliente.post("/api/research/%s/viability" % pesquisa["id"], json={})
    cliente.post("/api/research/%s/proof-of-concept" % pesquisa["id"])

    criado = cliente.post("/api/research/%s/reports" % pesquisa["id"],
                          json={"tipo": "viabilidade", "formato": "md"})
    assert criado.status_code == 201, criado.text
    relatorio = criado.json()
    assert relatorio["formato"] == "md"
    assert os.path.isfile(relatorio["arquivo"])
    assert relatorio["tamanho_bytes"] > 500

    conteudo = cliente.get("/api/reports/%s" % relatorio["id"]).json()
    for secao in ("1. Pergunta", "3. Matriz 7Dx4", "6. Evidencias",
                  "11. Avaliacao de viabilidade", "12. Limitacoes",
                  "13. Conclusao", "14. Recomendacoes"):
        assert secao in conteudo["conteudo"], secao

    arquivo = cliente.get("/api/reports/%s/arquivo" % relatorio["id"])
    assert arquivo.status_code == 200
    assert "text/markdown" in arquivo.headers["content-type"]

    json_relatorio = cliente.post("/api/research/%s/reports" % pesquisa["id"],
                                  json={"formato": "json"}).json()
    conteudo_json = cliente.get("/api/reports/%s"
                                % json_relatorio["id"]).json()["conteudo"]
    assert '"pesquisa"' in conteudo_json

    listados = cliente.get("/api/research/%s/reports" % pesquisa["id"]).json()
    assert listados["total"] >= 2


def test_relatorio_formato_invalido(cliente, motores_falsos):
    pesquisa = criar_pesquisa(cliente)
    resposta = cliente.post("/api/research/%s/reports" % pesquisa["id"],
                            json={"formato": "xlsx"})
    assert resposta.status_code == 400
    assert resposta.json()["erro"]["codigo"] == "entrada_invalida"


# ------------------------------------------------------------------------ cors
ORIGEM_FRONTEND = ("https://ais-dev-762xvkh6mpwv73wh6pxb4n-17975995585"
                   ".us-east1.run.app")


def test_cors_libera_o_frontend_do_cloud_run(cliente):
    preflight = cliente.options("/api/research", headers={
        "Origin": ORIGEM_FRONTEND,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert preflight.status_code == 200, preflight.text
    assert preflight.headers["access-control-allow-origin"] == ORIGEM_FRONTEND
    metodos = preflight.headers["access-control-allow-methods"]
    for metodo in ("GET", "POST", "PATCH", "DELETE", "OPTIONS"):
        assert metodo in metodos

    leitura = cliente.get("/api/matriz", headers={"Origin": ORIGEM_FRONTEND})
    assert leitura.status_code == 200
    assert leitura.headers["access-control-allow-origin"] == ORIGEM_FRONTEND

    edicao = cliente.options("/api/research/pesq_x", headers={
        "Origin": ORIGEM_FRONTEND,
        "Access-Control-Request-Method": "PATCH"})
    assert edicao.status_code == 200
    assert "PATCH" in edicao.headers["access-control-allow-methods"]


def test_cors_recusa_origem_desconhecida(cliente):
    intruso = "https://site-nao-autorizado.example"
    preflight = cliente.options("/api/research", headers={
        "Origin": intruso,
        "Access-Control-Request-Method": "POST"})
    assert preflight.status_code == 403
    assert "access-control-allow-origin" not in preflight.headers
    assert preflight.json()["erro"]["codigo"] == "origem_nao_autorizada"

    leitura = cliente.get("/api/matriz", headers={"Origin": intruso})
    assert leitura.status_code == 403
    assert "access-control-allow-origin" not in leitura.headers


def test_chamada_sem_origin_continua_permitida(cliente):
    """Script, curl e teste interno nao mandam Origin: seguem funcionando."""
    resposta = cliente.get("/api/matriz")
    assert resposta.status_code == 200


def test_cors_nunca_e_aberto_por_omissao():
    from ambiental_backend import config

    assert "*" not in config.origens_cors()
    assert ORIGEM_FRONTEND in config.origens_cors()
    assert config.origem_regex().startswith("^https://")


def test_ready_responde_sem_tocar_no_banco(cliente):
    resposta = cliente.get("/api/ready")
    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "pronto"


def test_persistencia_remota_inativa_por_omissao(cliente):
    """Sem AMBIENTAL_BACKUP_REPO o modulo nao faz nada e diz isso."""
    from ambiental_backend import persistencia_remota

    estado = persistencia_remota.estado()
    assert estado["configurado"] is False
    assert "banco_local" in estado
    assert persistencia_remota.enviar()["enviado"] is False
    assert persistencia_remota.restaurar()["feito"] is False

    saude = cliente.get("/api/health").json()
    assert saude["persistencia_remota"]["configurado"] is False


def test_sync_sem_configuracao_responde_que_nao_enviou(cliente):
    resposta = cliente.post("/api/persistence/sync")
    assert resposta.status_code == 200
    assert resposta.json()["enviado"] is False


def test_relatorio_inexistente(cliente):
    resposta = cliente.get("/api/reports/rel_naoexiste")
    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "nao_encontrado"


# ------------------------------------------------- edicao, painel e historico
def test_patch_pesquisa_atualiza_e_versiona(cliente):
    pesquisa = criar_pesquisa(cliente)
    assert pesquisa["versao"] == 1

    resposta = cliente.patch("/api/research/%s" % pesquisa["id"],
                             json={"titulo": "Adsorcao de Pb em carvao",
                                   "estado": "em_andamento",
                                   "condicoes": {"pH": 6.0}})
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["atualizada"] is True
    assert dados["alterados"]["estado"] == "em_andamento"
    assert dados["pesquisa"]["versao"] == 2
    assert dados["pesquisa"]["estado"] == "em_andamento"
    assert dados["pesquisa"]["condicoes"]["pH"] == 6.0
    assert dados["pesquisa"]["condicoes"]["Ce"] == 10.0

    igual = cliente.patch("/api/research/%s" % pesquisa["id"],
                          json={"estado": "em_andamento"}).json()
    assert igual["atualizada"] is False
    assert igual["pesquisa"]["versao"] == 2


def test_patch_pesquisa_valida_entrada(cliente):
    pesquisa = criar_pesquisa(cliente)
    curta = cliente.patch("/api/research/%s" % pesquisa["id"],
                          json={"pergunta": "curta"})
    assert curta.status_code == 400
    assert curta.json()["erro"]["codigo"] == "entrada_invalida"

    estado = cliente.patch("/api/research/%s" % pesquisa["id"],
                           json={"estado": "inventado"})
    assert estado.status_code == 400

    ausente = cliente.patch("/api/research/pesq_inexistente",
                            json={"titulo": "x"})
    assert ausente.status_code == 404


def test_patch_pesquisa_aceita_estado_que_o_motor_gravou(cliente):
    """O motor grava estados próprios ('prova_executada'); reenviá-los não pode
    quebrar a edição: valor igual ao gravado não é validado nem versionado."""
    from ambiental_backend import persistencia as db

    pesquisa = criar_pesquisa(cliente)
    sessao_db = db.sessao()
    try:
        registro = sessao_db.get(db.Pesquisa, pesquisa["id"])
        registro.estado = "prova_executada"
        sessao_db.commit()
    finally:
        sessao_db.close()

    resposta = cliente.patch("/api/research/%s" % pesquisa["id"],
                             json={"estado": "prova_executada",
                                   "titulo": "Titulo ajustado"})
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["atualizada"] is True
    assert dados["alterados"] == {"titulo": "Titulo ajustado"}
    assert dados["pesquisa"]["estado"] == "prova_executada"


def test_patch_material_faz_merge(cliente):
    pesquisa = criar_pesquisa(cliente)
    material = cliente.post(
        "/api/research/%s/materials" % pesquisa["id"],
        json={"nome": "zeolita de teste integracao",
              "composicao": [{"elemento": "Si", "fracao_massica": 0.4}],
              "propriedades": [{"nome": "area_superficial",
                                "valor": 300.0, "unidade": "m2/g"}]}).json()
    material_id = material["material"]["id"]

    resposta = cliente.patch("/api/materials/%s" % material_id, json={
        "formula": "Na2O.Al2O3.2SiO2",
        "propriedades": [{"nome": "area_superficial", "valor": 350.0},
                         {"nome": "pH_PZC", "valor": 8.0,
                          "origem": "medido"}],
        "composicao": [{"elemento": "Si", "fracao_massica": 0.45}]})
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["atualizado"] is True
    assert dados["alterados"]["formula"]
    assert dados["propriedades_novas"] == 1
    detalhe = dados["material"]
    assert detalhe["formula"] == "Na2O.Al2O3.2SiO2"
    valores = {p["nome"]: p["valor"] for p in detalhe["propriedades"]}
    assert valores["area_superficial"] == 350.0
    assert valores["pH_PZC"] == 8.0
    assert len(detalhe["propriedades"]) == 2


def test_stats_e_historico_refletem_o_banco(cliente):
    pesquisa = criar_pesquisa(cliente)
    cliente.post("/api/research/%s/materials" % pesquisa["id"],
                 json={"nome": "carvao do teste stats"})

    stats = cliente.get("/api/stats")
    assert stats.status_code == 200, stats.text
    dados = stats.json()
    assert dados["dados_demonstracao"] is False
    assert dados["pesquisas"]["total"] >= 1
    assert dados["materiais"]["total"] >= 1
    assert dados["matriz"]["descritores_por_material"] == 28
    assert dados["matriz"]["linhas_possiveis"] == (
        28 * dados["materiais"]["total"])
    assert 0.0 <= dados["matriz"]["cobertura_pct"] <= 100.0
    assert "por_estado" in dados["pesquisas"]

    historico = cliente.get("/api/history?limite=20")
    assert historico.status_code == 200, historico.text
    corpo = historico.json()
    ids = [item["id"] for item in corpo["pesquisas"]]
    assert pesquisa["id"] in ids
    acoes = [item["acao"] for item in corpo["eventos"]]
    assert "criada" in acoes
    assert isinstance(corpo["relatorios"], list)

    filtrado = cliente.get("/api/history?pesquisa_id=%s" % pesquisa["id"]).json()
    assert filtrado["total_eventos"] >= 1
    assert all(item["entidade_id"] == pesquisa["id"]
               or pesquisa["id"] in str(item["detalhe"])
               for item in filtrado["eventos"])
