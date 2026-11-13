# -*- coding: utf-8 -*-
"""Testes do recebimento de medicoes experimentais (caracterizacao).

Fluxo provado:

    - medicao valida e' gravada em `amb_medicoes` e preenche o descritor 7Dx4;
    - replicatas suficientes e RSR baixo elevam o estado para `validado`
      (com uma replicata o estado fica `presente`, com o motivo registrado);
    - unidade errada, valor fora da faixa fisica e tipo desconhecido voltam 400
      dizendo o que corrigir — nada e' aceito por omissao;
    - lote com item invalido grava os validos e reporta a falha item por item;
    - listagem, resumo por descritor e remocao funcionam.

Sem rede: usa o TestClient do conftest e o banco temporario de teste.
"""
from __future__ import annotations

import itertools

_SEQUENCIA = itertools.count(1)


def _material(cliente, nome=None):
    """Cria pesquisa + material e devolve (pesquisa_id, material_id).

    O nome leva sufixo unico porque o backend reaproveita material existente
    pelo nome: sem isso as medicoes de um teste apareceriam no seguinte.
    """
    nome = nome or "carvao ativado de teste %d" % next(_SEQUENCIA)
    pesquisa = cliente.post("/api/research", json={
        "pergunta": "adsorcao de chumbo em carvao ativado",
        "material": nome, "contaminante": "chumbo", "aplicacao": "agua",
        "condicoes": {"Ce": 10.0}})
    assert pesquisa.status_code == 201, pesquisa.text
    pesquisa_id = pesquisa.json()["id"]
    criado = cliente.post("/api/research/%s/materials" % pesquisa_id,
                          json={"nome": nome})
    assert criado.status_code == 201, criado.text
    return pesquisa_id, criado.json()["material"]["id"]


def test_catalogo_de_tipos(cliente):
    resposta = cliente.get("/api/measurements/types")
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["total"] >= 10
    tipos = {item["tipo"]: item for item in dados["tipos"]}
    assert tipos["bet_area"]["unidade"] == "m2/g"
    assert tipos["bet_area"]["descritor"] == "S3"
    assert tipos["pzc"]["descritor"] == "P2"


def test_bet_com_replicatas_fica_validado(cliente):
    pesquisa_id, material_id = _material(cliente)
    resposta = cliente.post(
        "/api/materials/%s/measurements" % material_id,
        json={"tipo": "bet_area", "replicatas": [748.0, 752.0, 750.0],
              "instrumento": "Quantachrome Nova 1200e",
              "laboratorio": "LABCAR", "operador": "teste",
              "pesquisa_id": pesquisa_id})
    assert resposta.status_code == 201, resposta.text
    dados = resposta.json()
    assert dados["descritor"] == "S3"
    assert dados["estado"] == "validado"
    assert abs(dados["valor"] - 750.0) < 1e-6
    assert dados["estatistica"]["n"] == 3
    assert dados["origem"] == "medicao_experimental"

    matriz = cliente.get("/api/materials/%s/descriptors" % material_id).json()
    s3 = next(item for item in matriz["descritores"] if item["codigo"] == "S3")
    assert s3["estado"] in ("presente", "validado")
    assert abs(s3["valor"] - 750.0) < 1e-6
    assert matriz["preenchimento"]["com_dado"] >= 1


def test_uma_replicata_fica_presente_com_motivo(cliente):
    _, material_id = _material(cliente)
    resposta = cliente.post(
        "/api/materials/%s/measurements" % material_id,
        json={"tipo": "pzc", "valor": 7.4})
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["estado"] == "presente"
    assert resposta.json()["motivo_estado"]


def test_unidade_errada_e_recusada(cliente):
    _, material_id = _material(cliente)
    resposta = cliente.post(
        "/api/materials/%s/measurements" % material_id,
        json={"tipo": "bet_area", "valor": 700.0, "unidade": "cm3/g"})
    assert resposta.status_code == 400
    assert "m2/g" in resposta.json()["erro"]["mensagem"]


def test_valor_fora_da_faixa_e_recusado(cliente):
    _, material_id = _material(cliente)
    resposta = cliente.post(
        "/api/materials/%s/measurements" % material_id,
        json={"tipo": "pzc", "valor": 15.0})
    assert resposta.status_code == 400
    assert "faixa" in resposta.json()["erro"]["mensagem"].lower()


def test_tipo_desconhecido_e_recusado(cliente):
    _, material_id = _material(cliente)
    resposta = cliente.post(
        "/api/materials/%s/measurements" % material_id,
        json={"tipo": "espectroscopia_gama", "valor": 1.0})
    assert resposta.status_code == 400
    assert "desconhecido" in resposta.json()["erro"]["mensagem"]


def test_grupos_ftir_aceita_texto(cliente):
    _, material_id = _material(cliente)
    resposta = cliente.post(
        "/api/materials/%s/measurements" % material_id,
        json={"tipo": "grupos_ftir",
              "valor_texto": "O-H (3420); C=C (1590); C-O (1100)"})
    assert resposta.status_code == 201, resposta.text
    dados = resposta.json()
    assert dados["descritor"] == "S6"
    assert dados["valor"] is None
    assert "3420" in dados["valor_texto"]


def test_lote_grava_validos_e_reporta_falhas(cliente):
    pesquisa_id, material_id = _material(cliente)
    resposta = cliente.post(
        "/api/materials/%s/measurements/batch" % material_id,
        json={"medicoes": [
            {"tipo": "volume_poros", "replicatas": [0.31, 0.33],
             "pesquisa_id": pesquisa_id},
            {"tipo": "pzc", "valor": 99.0},
            {"tipo": "diametro_particula", "replicatas": [480.0, 505.0]}]})
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["total_recebidas"] == 3
    assert dados["registradas"] == 2
    assert dados["falhas"] == 1
    assert dados["erros"][0]["tipo"] == "pzc"


def test_listagem_resumo_e_remocao(cliente):
    pesquisa_id, material_id = _material(cliente)
    criada = cliente.post(
        "/api/materials/%s/measurements" % material_id,
        json={"tipo": "lixiviacao", "valor": 4.3,
              "condicoes": {"tempo_h": 24, "pH": 5.0},
              "pesquisa_id": pesquisa_id})
    assert criada.status_code == 201, criada.text
    medicao_id = criada.json()["medicao_id"]

    lista = cliente.get("/api/materials/%s/measurements" % material_id).json()
    assert lista["total"] == 1
    assert lista["medicoes"][0]["medicao_id"] == medicao_id

    resumo = cliente.get(
        "/api/materials/%s/measurements/summary" % material_id).json()
    assert resumo["total_medicoes"] == 1
    assert "P7" in resumo["descritores_cobertos"]

    detalhe = cliente.get("/api/measurements/%s" % medicao_id)
    assert detalhe.status_code == 200, detalhe.text
    assert detalhe.json()["condicoes"]["tempo_h"] == 24

    remocao = cliente.delete("/api/measurements/%s" % medicao_id)
    assert remocao.status_code == 200, remocao.text
    assert cliente.get("/api/measurements/%s" % medicao_id).status_code == 404


def test_medicao_sem_valor_nem_texto_e_recusada(cliente):
    _, material_id = _material(cliente)
    resposta = cliente.post(
        "/api/materials/%s/measurements" % material_id,
        json={"tipo": "bet_area"})
    assert resposta.status_code == 400
    assert "valor" in resposta.json()["erro"]["mensagem"]
