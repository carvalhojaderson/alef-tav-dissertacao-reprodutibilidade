# -*- coding: utf-8 -*-
"""[QA LOCAL] Stub de `analises_experimentais` para execucao local da API.

Por que este arquivo existe
===========================

Na copia do projeto em `Desktop\\Projetos\\Nova pasta`, o modulo original e' um
carregador de bytecode CPython 3.10 (`_recuperacao/analises_experimentais
.cpython-310.pyc`). Esse `.pyc` NAO esta presente nesta copia, entao o import
falha com `RuntimeError` e a aplicacao inteira nao sobe — inclusive as rotas de
pesquisa/material/adsorvente, que nao usam este modulo.

Este stub permite subir a API na 7860 para o teste de QA do fluxo SMX. Ele NAO
reimplementa nenhuma analise: qualquer tentativa de usar um motor de analise
experimental levanta `RuntimeError` dizendo que o motor nao foi executado.
Nenhum numero e' inventado.

O arquivo original do carregador foi preservado ao lado como
`analises_experimentais.pycshim`. Para restaurar:

    Copy-Item analises_experimentais.pycshim analises_experimentais.py -Force
"""
from __future__ import annotations

print("[QA] analises_experimentais: STUB LOCAL ativo "
      "(bytecode CPython 3.10 ausente nesta copia)")

# Constantes de nivel de validacao lidas pelos motores ambientais.
NIVEL_ANALITICO = "analitico"
NIVEL_AJUSTE = "ajuste"
NIVEL_TABELA = "tabela"
NIVEL_INDICE = "indice"

STUB_QA = True


class EntradaInvalida(ValueError):
    """Mesmo nome de excecao usado pelos motores ambientais."""


def _indisponivel(nome):
    raise RuntimeError(
        "analises_experimentais.%s indisponivel: esta copia nao contem o "
        "bytecode CPython 3.10 do modulo original; o motor nao foi executado "
        "e nenhum resultado foi inventado" % nome)


def __getattr__(nome):
    if nome.startswith("__"):
        raise AttributeError(nome)
    return lambda *args, **kwargs: _indisponivel(nome)
