# -*- coding: utf-8 -*-
"""Motores de analise experimental do backend ambiental (modulo recuperado).

AVISO DE RECUPERACAO (ler antes de editar)
==========================================

O arquivo `.py` original deste modulo foi destruido por corrupcao de disco
(ficou com 71.825 bytes, todos NUL). O texto-fonte nao existe em nenhum backup
nem em nenhum historico de sessao. Entretanto o bytecode compilado pelo
CPython 3.10 sobreviveu intacto em `__pycache__/analises_experimentais.cpython-310.pyc`
(cabecalho: `source_size=71166`, mtime 2026-11-03 18:28) e foi preservado em
`_recuperacao/` junto com a especificacao extraida dele.

Este arquivo, portanto, **nao contem o codigo-fonte**: ele carrega aquele
bytecode e o executa no namespace deste modulo. Consequencias praticas:

* o comportamento e' exatamente o original — nao houve reescrita, entao
  nenhum resultado cientifico foi inventado, arredondado ou reinterpretado;
* exige CPython 3.10 (a versao do `.pyc` e da imagem `python:3.10-slim` usada
  pelo Space). Em outra versao o modulo levanta `RuntimeError` com mensagem
  explicita em vez de falhar em silencio;
* `inspect.getsource()`, depuracao passo a passo e edicao fina nao funcionam
  aqui: e' divida tecnica conhecida e registrada no relatorio da versao.

Reescrita prevista (v1.1): cada funcao sera reimplementada em Python legivel e
conferida contra este mesmo bytecode, usado como oraculo numerico — a
especificacao recuperada (`_recuperacao/_analises_full.txt`) traz assinatura,
docstring e constantes de cada funcao, e a comparacao de saidas garante
equivalencia antes de aposentar o `.pyc`.
"""
from __future__ import annotations

import marshal
import pathlib

VERSAO_RECUPERADA = "1.0.0"

# Cabecalho de um `.pyc` do CPython 3.10: magic 3439 + 12 bytes (flags, mtime,
# tamanho da origem). O magic garante que o bytecode veio desta versao.
_MAGIC_310 = b"\x6f\x0d\x0d\x0a"
_TAMANHO_CABECALHO = 16

_PASTA = pathlib.Path(__file__).resolve().parent
_CANDIDATOS = (
    _PASTA / "_recuperacao" / "analises_experimentais.cpython-310.pyc",
    _PASTA / "__pycache__" / "analises_experimentais.cpython-310.pyc",
)


def _carregar_codigo():
    """Devolve (caminho, code object) do bytecode original preservado."""
    tentativas = []
    for caminho in _CANDIDATOS:
        if not caminho.is_file():
            tentativas.append("%s: ausente" % caminho)
            continue
        dados = caminho.read_bytes()
        if dados[:4] != _MAGIC_310:
            tentativas.append("%s: magic %s (bytecode de outra versao)"
                              % (caminho, dados[:4].hex()))
            continue
        try:
            return caminho, marshal.loads(dados[_TAMANHO_CABECALHO:])
        except (EOFError, ValueError, TypeError) as erro:
            tentativas.append("%s: bytecode ilegivel (%s)" % (caminho, erro))
    raise RuntimeError(
        "analises_experimentais: nao foi possivel carregar o bytecode "
        "original preservado. O modulo recuperado exige CPython 3.10, que e' "
        "a versao do Space. Tentativas: %s"
        % ("; ".join(tentativas) or "nenhum candidato encontrado"))


ORIGEM_RECUPERACAO, _CODIGO = _carregar_codigo()

# O docstring original do modulo e' a primeira constante do code object; o
# `exec` nao o reinstala (isso e' feito pelo import machinery), por isso ele
# e' preservado aqui e reaplicado no fim.
_DOC_ORIGINAL = ""
if _CODIGO.co_consts and isinstance(_CODIGO.co_consts[0], str):
    _DOC_ORIGINAL = _CODIGO.co_consts[0]

exec(_CODIGO, globals())                              # noqa: S102

__doc__ = "%s\n\n%s" % (__doc__, _DOC_ORIGINAL)
del _CODIGO
