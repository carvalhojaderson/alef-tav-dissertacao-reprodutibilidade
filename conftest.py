# -*- coding: utf-8 -*-
"""Configuracao dos testes do backend ambiental.

Banco de teste em arquivo temporario (nunca o `alef_tav.db` do projeto) e
motores falsos injetados: nenhum teste depende de rede nem de simulador real.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

_TMP = pathlib.Path(tempfile.mkdtemp(prefix="ambiental_teste_"))
os.environ["ALEF_TAV_DATABASE_URL"] = "sqlite:///" + (_TMP / "teste.db").as_posix()
os.environ["DATABASE_URL"] = ""
os.environ["AMBIENTAL_DADOS"] = str(_TMP / "dados")
os.environ["ALEF_SEM_PREAQUECER"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import pytest                                     # noqa: E402
from fastapi.testclient import TestClient         # noqa: E402

from ambiental_backend import adaptadores, tarefas  # noqa: E402
from ambiental_backend.app import create_app      # noqa: E402


@pytest.fixture(scope="session")
def cliente():
    with TestClient(create_app()) as aplicacao:
        yield aplicacao
    tarefas.encerrar()


@pytest.fixture
def motores_falsos():
    """Dois simuladores de mentira com resultado deterministico."""
    registro = {
        "superficie": lambda pergunta, params: {
            "simulador": "superficie", "qmax_mg_g": 120.0,
            "pergunta": pergunta, "parametros": params},
        "metais": lambda pergunta, params: {
            "simulador": "metais", "remocao_pct": 92.5},
        "quebrado": lambda pergunta, params: 1 / 0,
    }
    adaptadores.definir_motores_simulacao(registro)
    try:
        yield registro
    finally:
        adaptadores.definir_motores_simulacao(None)


@pytest.fixture
def busca_falsa():
    """Substitui `pesquisa_cientifica.pesquisar` por um corpus fixo."""
    def pesquisar(termo, bases=None, n=3, max_bases=4, salvar=False,
                  timeout=None, **_):
        itens = [
            {"base": "openalex", "fonte": "OpenAlex", "ano": 2021,
             "titulo": "Adsorcao de chumbo em carvao ativado",
             "resumo": "Capacidade maxima de 118,5 mg/g para Pb(II).",
             "link": "https://example.org/a", "doi": "10.1/a"},
            {"base": "crossref", "fonte": "Crossref", "ano": 2019,
             "titulo": "Langmuir adsorption of lead on biochar",
             "resumo": "qmax = 121 mg/g e area BET de 750 m2/g.",
             "link": "https://example.org/b", "doi": ""},
        ]
        return {"estado": "OK", "termo": termo, "itens": itens,
                "falhas": {}, "duplicados": 0,
                "totais": {"bases": 2, "itens": 2}}
    adaptadores.definir_funcao_pesquisa(pesquisar)
    try:
        yield pesquisar
    finally:
        adaptadores.definir_funcao_pesquisa(None)
