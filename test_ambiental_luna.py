# -*- coding: utf-8 -*-
"""Testes da Luna (assistente OpenAI) — nenhum teste usa rede.

O transporte HTTP e' substituido por um duble roteirizado, entao o que se prova
aqui e' o que o backend faz de fato:

    - sem `OPENAI_API_KEY` a rota responde 503 `luna_nao_configurada` (nunca
      uma resposta fingida) e nada e' gravado no historico;
    - com chave, a Luna pede a ferramenta, o backend le' o banco real e devolve
      o dado ao modelo: `ferramentas` documenta o que foi consultado;
    - o historico fica isolado por pesquisa e por usuario;
    - a chave nunca aparece em resposta nem em mensagem de erro.

A chamada real a OpenAI e' feita fora da suite (`_smoke_luna.py`), quando o
Secret existir.
"""
from __future__ import annotations

import json
import urllib.error

import pytest

from ambiental_backend import luna

CHAVE_FALSA = "sk-teste-0000000000000000000000000000000000000000"


def _pesquisa_com_material(cliente, material="carvao ativado de casca de coco"):
    """Pesquisa + material + um parametro de caracterizacao real."""
    pesquisa = cliente.post("/api/research", json={
        "pergunta": "adsorcao de chumbo em agua com carvao ativado",
        "material": material, "contaminante": "chumbo", "aplicacao": "agua",
    }).json()
    criado = cliente.post("/api/research/%s/materials" % pesquisa["id"],
                          json={"nome": material}).json()
    material_id = criado["material"]["id"]
    catalogo = cliente.get("/api/componentes?componente=adsorvente").json()
    escolhido = None
    for bloco in catalogo.get("componentes") or []:
        for item in bloco.get("parametros") or []:
            if item.get("tipo") == "numero":
                escolhido = item
                break
        if escolhido:
            break
    if escolhido:
        cliente.post("/api/materials/%s/components/adsorvente" % material_id,
                     json={"parametros": [{"chave": escolhido["chave"],
                                           "valor": 750.0,
                                           "unidade": escolhido.get("unidade")}]})
    return pesquisa["id"], material_id, escolhido


@pytest.fixture
def com_chave(monkeypatch):
    """Chave falsa + modelo fixo: nenhuma chamada real a `/v1/models`."""
    monkeypatch.setenv("OPENAI_API_KEY", CHAVE_FALSA)
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    luna._CACHE_MODELOS.update({"quando": 0.0, "ids": []})
    yield CHAVE_FALSA
    luna._CACHE_MODELOS.update({"quando": 0.0, "ids": []})


class TransporteFalso:
    """Substitui `luna._http`: devolve respostas na ordem e guarda o que saiu."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def __call__(self, metodo, caminho, corpo=None, timeout=None):
        self.chamadas.append({"metodo": metodo, "caminho": caminho,
                              "corpo": corpo})
        if not self.respostas:
            raise AssertionError("chamada a mais para a OpenAI: %s" % caminho)
        return self.respostas.pop(0)


def _mensagens(transporte, indice=-1):
    return transporte.chamadas[indice]["corpo"]["messages"]


# ------------------------------------------------------------------- sem chave
def test_status_sem_chave_diz_o_que_falta(cliente, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    dados = cliente.get("/api/luna/status").json()
    assert dados["configurada"] is False
    assert dados["modelo"] is None
    assert dados["total_ferramentas"] == 16
    assert "OPENAI_API_KEY" in dados["aviso"]
    assert "matriz_montada" in dados["ferramentas"]
    assert "gpt-6" in dados["modelos_preferidos"]


def test_chat_sem_chave_responde_503_e_nao_grava(cliente, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pesquisa_id, material_id, _ = _pesquisa_com_material(
        cliente, "zeolita sem chave")
    consulta = ("/api/luna/historico?pesquisa_id=%s&usuario=teste_sem_chave"
                % pesquisa_id)
    assert cliente.get(consulta).json()["total"] == 0
    resposta = cliente.post("/api/luna/chat", json={
        "mensagem": "quais lacunas existem?", "pesquisa_id": pesquisa_id,
        "material_id": material_id, "usuario": "teste_sem_chave"})
    assert resposta.status_code == 503
    assert resposta.json()["erro"]["codigo"] == "luna_nao_configurada"
    assert cliente.get(consulta).json()["total"] == 0


def test_chat_com_mensagem_vazia_responde_400(cliente):
    resposta = cliente.post("/api/luna/chat", json={"mensagem": "   "})
    assert resposta.status_code == 400
    assert resposta.json()["erro"]["codigo"] == "entrada_invalida"


# ------------------------------------------------------- conversa com ferramenta
def test_luna_le_o_banco_antes_de_responder(cliente, com_chave, monkeypatch):
    pesquisa_id, material_id, escolhido = _pesquisa_com_material(
        cliente, "carvao de teste luna")
    transporte = TransporteFalso([
        {"choices": [{"message": {
            "role": "assistant", "content": "",
            "tool_calls": [{"id": "call_1", "type": "function", "function": {
                "name": "descritores_material",
                "arguments": json.dumps({"material_id": material_id})}}]}}],
         "usage": {"prompt_tokens": 120, "completion_tokens": 8,
                   "total_tokens": 128}},
        {"choices": [{"message": {
            "role": "assistant",
            "content": "O material tem 28 descritores e S3 e' a area BET."}}],
         "usage": {"prompt_tokens": 260, "completion_tokens": 30,
                   "total_tokens": 290}},
    ])
    monkeypatch.setattr(luna, "_http", transporte)

    resposta = cliente.post("/api/luna/chat", json={
        "mensagem": "o que ja esta registrado para este material?",
        "pesquisa_id": pesquisa_id, "material_id": material_id,
        "usuario": "pesquisador_1"})
    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["resposta"].startswith("O material tem 28 descritores")
    assert dados["modelo"] == "gpt-5-mini"
    assert dados["modelo_origem"] == "OPENAI_MODEL"
    assert dados["total_ferramentas"] == 1
    assert dados["ferramentas"][0]["ferramenta"] == "descritores_material"
    assert dados["ferramentas"][0]["ok"] is True
    assert dados["uso"]["total_tokens"] == 418

    # a segunda chamada levou o resultado real da ferramenta (role=tool)
    ferramentas = [item for item in _mensagens(transporte)
                   if item["role"] == "tool"]
    assert len(ferramentas) == 1
    corpo = json.loads(ferramentas[0]["content"])
    assert corpo["total"] == 28
    assert "S3" in [item["codigo"] for item in corpo["descritores"]]
    assert corpo["material"]["nome"] == "carvao de teste luna"
    if escolhido:
        assert corpo["com_valor"] >= 1

    # o historico guarda pergunta, resposta, modelo e ferramenta
    historico = cliente.get("/api/luna/historico?pesquisa_id=%s&usuario="
                            "pesquisador_1" % pesquisa_id).json()
    assert historico["total"] == 2
    assert [item["papel"] for item in historico["mensagens"]] == ["usuario",
                                                                 "luna"]
    assert historico["mensagens"][1]["ferramentas"][0]["ferramenta"] == \
        "descritores_material"
    assert historico["mensagens"][1]["modelo"] == "gpt-5-mini"
    assert CHAVE_FALSA not in json.dumps(historico)


def test_historico_isolado_por_pesquisa_e_usuario(cliente, com_chave,
                                                  monkeypatch):
    pesquisa_a, material_a, _ = _pesquisa_com_material(cliente, "material A")
    pesquisa_b, material_b, _ = _pesquisa_com_material(cliente, "material B")
    transporte = TransporteFalso([
        {"choices": [{"message": {"role": "assistant",
                                  "content": "resposta da pesquisa A"}}]},
        {"choices": [{"message": {"role": "assistant",
                                  "content": "resposta da pesquisa B"}}]},
    ])
    monkeypatch.setattr(luna, "_http", transporte)
    for pesquisa_id, material_id in ((pesquisa_a, material_a),
                                     (pesquisa_b, material_b)):
        assert cliente.post("/api/luna/chat", json={
            "mensagem": "resuma", "pesquisa_id": pesquisa_id,
            "material_id": material_id,
            "usuario": "dono_a"}).status_code == 200

    de_a = cliente.get("/api/luna/historico?pesquisa_id=%s&usuario=dono_a"
                       % pesquisa_a).json()
    assert de_a["total"] == 2
    assert "pesquisa A" in de_a["mensagens"][1]["conteudo"]
    de_b = cliente.get("/api/luna/historico?pesquisa_id=%s&usuario=dono_a"
                       % pesquisa_b).json()
    assert de_b["total"] == 2
    assert "pesquisa B" in de_b["mensagens"][1]["conteudo"]
    assert cliente.get("/api/luna/historico?pesquisa_id=%s&usuario=dono_b"
                       % pesquisa_a).json()["total"] == 0

    apagado = cliente.delete("/api/luna/historico?pesquisa_id=%s&usuario=dono_a"
                             % pesquisa_a).json()
    assert apagado["removidas"] == 2
    assert cliente.get("/api/luna/historico?pesquisa_id=%s&usuario=dono_a"
                       % pesquisa_a).json()["total"] == 0
    assert cliente.get("/api/luna/historico?pesquisa_id=%s&usuario=dono_a"
                       % pesquisa_b).json()["total"] == 2


# --------------------------------------------------------------- unidades puras
def test_ferramentas_leem_dado_real_do_backend(cliente):
    pesquisa_id, material_id, _ = _pesquisa_com_material(cliente, "material C")
    estrutura = luna.executar_ferramenta("estrutura_matriz", {})
    assert estrutura["total_cruzamentos"] == 28
    assert len(estrutura["cruzamentos"]) == 28
    assert estrutura["total_parametros"] >= 50

    matriz = luna.executar_ferramenta("matriz_montada",
                                      {"pesquisa_id": pesquisa_id,
                                       "material_id": material_id})
    assert matriz["material_id"] == material_id
    assert len(matriz["cruzamentos"]) == 28
    assert "resumo" in matriz

    explicado = luna.executar_ferramenta("explicar_descritor", {"codigo": "S3"})
    assert explicado["codigo"] == "S3"
    assert explicado["cruzamentos"]
    assert "erro" in luna.executar_ferramenta("explicar_descritor",
                                              {"codigo": "ZZ"})
    assert "erro" in luna.executar_ferramenta("ferramenta_que_nao_existe", {})
    assert "S3" in json.dumps(luna.executar_ferramenta(
        "descritores_material", {"material_id": material_id}))


def test_redige_a_chave_em_mensagem_de_erro(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", CHAVE_FALSA)

    class RespostaFalsa:
        def read(self):
            return json.dumps({"error": {
                "message": "chave invalida: %s" % CHAVE_FALSA}}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def urlopen_falso(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "https://api.openai.com/v1/chat/completions", 401,
            "Unauthorized", {}, RespostaFalsa())

    monkeypatch.setattr(luna.urllib.request, "urlopen", urlopen_falso)
    with pytest.raises(luna.LunaIndisponivel) as erro:
        luna._http("POST", "/chat/completions", {"model": "x"})
    assert CHAVE_FALSA not in str(erro.value)
    assert "sk-***" in str(erro.value)
    assert "401" in str(erro.value)


def test_modelo_preferido_e_o_gpt6_quando_a_conta_autoriza(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setattr(luna, "modelos_disponiveis",
                        lambda forcar=False: ["gpt-4o-mini", "gpt-6",
                                              "gpt-6-mini",
                                              "text-embedding-3-small"])
    escolha = luna.resolver_modelo()
    assert escolha["modelo"] == "gpt-6"
    assert escolha["origem"] == "descoberto na conta"

    monkeypatch.setattr(luna, "modelos_disponiveis",
                        lambda forcar=False: ["text-embedding-3-small"])
    with pytest.raises(luna.LunaIndisponivel):
        luna.resolver_modelo()
