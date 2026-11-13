# -*- coding: utf-8 -*-
"""Semelhanca de cosseno entre adsorventes e entre adsorvente e contaminante.

O que este modulo faz
=====================

Le a matriz preenchida (`amb_descritores` + `amb_componentes`) e monta um vetor
por material.  Cada descritor vira um numero entre 0 e 1 pela faixa fisica
declarada em `NORMALIZACAO` (nunca pela faixa observada na amostra, que
dependeria de quantos materiais existem).  Depois calcula:

    cos(A, B)          diferenca entre os dois carvoes no espaco dos 28
    cos(A, SMX)        semelhanca de perfil material x contaminante nos 7 eixos
    perfil de delta    quais descritores realmente separam A de B

Regras de honestidade
=====================

* descritor `ausente`/`nao_aplicavel`/texto puro fica fora do vetor (nunca
  entra como zero: zero e' um valor, ausencia nao e');
* o cosseno roda **sobre as dimensoes comuns** aos dois vetores e o numero de
  dimensoes usadas aparece ao lado do resultado (`n`);
* existe o recorte "lastro" (nivel 1-2: medido + derivado) e o recorte
  "completo" (inclui nivel 3: cenario).  Se o resultado muda muito entre os
  dois, a diferenca nao e' do material - e' do cenario.

Interpretacao
=============

Cosseno alto entre materiais = perfis parecidos.  Cosseno alto entre material e
contaminante **nao** e' previsao de adsorcao: e' semelhanca de perfil nos eixos
que o sistema mede.  Afinidade se prova em isoterma, nao em cosseno.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import dossie_matriz as dossie                      # noqa: E402

BANCO_COPIA = AQUI / "_qa_matriz" / "ambiental.db"
BANCO_REAL = AQUI / "dados_ambiental" / "ambiental.db"
SAIDA_JSON = AQUI / "semelhanca_cosseno.json"

#: codigo -> (minimo fisico, maximo fisico, direcao, escala)
#: direcao: +1 maior e' melhor, -1 menor e' melhor, 0 neutro (so normaliza)
NORMALIZACAO = {
    "S1": (70.0, 100.0, +1, "linear"),     # pureza %
    "S3": (100.0, 2000.0, +1, "linear"),   # area BET m2/g
    "S4": (0.10, 1.20, +1, "linear"),      # volume de poros cm3/g
    "S5": (5.0, 500.0, -1, "linear"),      # d50 um
    "S6": (0.0, 3.0, +1, "linear"),        # acidez total mmol/g
    "S7": (5.0, 500.0, -1, "linear"),      # d50 um (PSD)
    "P1": (0.30, 1.20, 0, "linear"),       # densidade aparente g/cm3
    "P2": (3.0, 11.0, 0, "linear"),        # PZC
    "P3": (0.0, 60.0, +1, "linear"),       # CTC cmol/kg
    "P4": (20.0, 60.0, +1, "linear"),      # energia superficial mN/m
    "P5": (200.0, 700.0, +1, "linear"),    # onset TGA C
    "P7": (0.0, 20.0, -1, "linear"),       # lixiviacao %
    "D1": (10.0, 300.0, +1, "linear"),     # qmax mg/g
    "D2": (0.005, 1.0, +1, "log"),         # KL L/mg
    "D3": (1e-5, 1e-2, +1, "log"),         # k2 g/(mg min)
    "D4": (1.0, 10.0, +1, "linear"),       # seletividade
    "D5": (0.0, 20.0, +1, "linear"),       # ciclos
    "D6": (0.0, 100.0, +1, "linear"),      # remocao %
    "C2": (0.0, 5.0, -1, "linear"),        # R$/g removido
    "C4": (0.0, 50.0, -1, "linear"),       # kWh/kg
    "C5": (0.0, 1.0, +1, "linear"),        # indice de reciclabilidade
    "C6": (0.0, 100.0, +1, "linear"),      # margem de conformidade %
    "C7": (0.0, 120.0, -1, "linear"),      # TRH min
}

#: parametros do adsorbato (SMX) -> faixa de normalizacao
NORMALIZACAO_ADSORBATO = {
    "massa_molar": (50.0, 1000.0, 0, "linear"),
    "pka": (0.0, 14.0, 0, "linear"),
    "log_kow": (-3.0, 5.0, 0, "linear"),
    "carga_ionica": (-2.0, 2.0, 0, "linear"),
    "raio_ionico": (0.1, 2.0, 0, "linear"),
    "concentracao_trabalho": (0.0, 100.0, 0, "linear"),
}


def _normalizar(valor, regra):
    if valor is None or regra is None:
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero):
        return None
    minimo, maximo, direcao, escala = regra
    if escala == "log":
        if numero <= 0 or minimo <= 0:
            return None
        numero, minimo, maximo = (math.log10(numero), math.log10(minimo),
                                  math.log10(maximo))
    fracao = (numero - minimo) / (maximo - minimo)
    fracao = min(1.0, max(0.0, fracao))
    return (1.0 - fracao) if direcao < 0 else fracao


def cosseno(esquerda: dict, direita: dict) -> dict:
    """Cosseno sobre as chaves presentes nos dois vetores."""
    chaves = sorted(k for k in esquerda
                    if k in direita and esquerda[k] is not None
                    and direita[k] is not None)
    if not chaves:
        return {"valor": None, "n": 0, "dimensoes": []}
    produto = sum(esquerda[k] * direita[k] for k in chaves)
    norma_a = math.sqrt(sum(esquerda[k] ** 2 for k in chaves))
    norma_b = math.sqrt(sum(direita[k] ** 2 for k in chaves))
    if norma_a == 0 or norma_b == 0:
        return {"valor": None, "n": len(chaves), "dimensoes": chaves}
    return {"valor": round(produto / (norma_a * norma_b), 6),
            "n": len(chaves), "dimensoes": chaves}



# ------------------------------------------------------------------ vetores
def _nivel(linha: dict):
    """Nivel de lastro gravado em `dados_json.complemento.nivel`."""
    detalhe = linha.get("detalhe") or {}
    if not isinstance(detalhe, dict):
        return None
    if detalhe.get("nivel") is not None:
        return int(detalhe["nivel"])
    complemento = detalhe.get("complemento") or {}
    if isinstance(complemento, dict) and complemento.get("nivel") is not None:
        return int(complemento["nivel"])
    return None


def vetor(descritores: dict, recorte: str = "completo") -> dict:
    """codigo -> valor normalizado.  `recorte='lastro'` so usa nivel 1-2."""
    saida = {}
    for codigo, linha in descritores.items():
        regra = NORMALIZACAO.get(codigo)
        if regra is None:
            continue
        estado = (linha.get("estado") or "").lower()
        if estado in ("ausente", "nao_aplicavel", ""):
            continue
        if recorte == "lastro":
            nivel = _nivel(linha)
            if nivel is None or nivel > 2:
                continue
        valor = _normalizar(linha.get("valor"), regra)
        if valor is not None:
            saida[codigo] = valor
    return saida


def perfil_eixos(vetor_normalizado: dict, relacoes: dict) -> dict:
    """Media dos valores normalizados por eixo (E, P, D, S, I, C, O)."""
    grupos = {}
    for codigo, valor in vetor_normalizado.items():
        relacao = relacoes.get(codigo) or []
        if not relacao:
            continue
        grupos.setdefault(relacao[0][0], []).append(valor)
    return {eixo: round(sum(itens) / len(itens), 6)
            for eixo, itens in grupos.items()}


def perfil_adsorbato(parametros: dict, catalogo: dict) -> dict:
    """Perfil do contaminante nos mesmos eixos (so o que tem faixa declarada)."""
    grupos = {}
    for chave, valor in parametros.items():
        regra = NORMALIZACAO_ADSORBATO.get(chave)
        if regra is None:
            continue
        normalizado = _normalizar(valor, regra)
        if normalizado is None:
            continue
        meta = catalogo.get(chave) or {}
        eixo = meta.get("dimensao")
        if not eixo:
            continue
        grupos.setdefault(eixo, []).append(normalizado)
    return {eixo: round(sum(itens) / len(itens), 6)
            for eixo, itens in grupos.items()}


# --------------------------------------------------------------------- banco
def carregar(banco: Path) -> dict:
    import sqlite3

    from ambiental_backend import matriz_cruzamentos as cruz

    conexao = sqlite3.connect(str(banco))
    conexao.row_factory = sqlite3.Row
    materiais = {linha["id"]: dict(linha) for linha in conexao.execute(
        "select id, nome from amb_materiais")}

    descritores = {}
    for linha in conexao.execute("select * from amb_descritores"):
        item = dict(linha)
        descritores.setdefault(item["material_id"], {})[item["codigo"]] = {
            "valor": item["valor"], "valor_texto": item["valor_texto"],
            "unidade": item["unidade"], "estado": item["estado"],
            "fonte": item["fonte"],
            "detalhe": json.loads(item["dados_json"] or "{}"),
        }

    parametros = {}
    try:
        for linha in conexao.execute("select * from amb_componentes"):
            item = dict(linha)
            parametros.setdefault(item["material_id"], {}).setdefault(
                item["componente"], {})[item["chave"]] = item["valor"]
    except sqlite3.Error:
        pass
    conexao.close()
    return {"materiais": materiais, "descritores": descritores,
            "parametros": parametros, "relacoes": cruz.RELACOES_DESCRITORES,
            "catalogo": cruz.PARAMETROS_POR_CHAVE}



# ----------------------------------------------------------------- relatorio
def analisar(dados: dict, rotulos=("A", "B")) -> dict:
    relacoes = dados["relacoes"]
    catalogo = dados["catalogo"]
    materiais = {}
    for material in dossie.MATERIAIS:
        if material["rotulo"] not in rotulos:
            continue
        descritores = dados["descritores"].get(material["id"]) or {}
        completo = vetor(descritores, "completo")
        lastro = vetor(descritores, "lastro")
        parametros = (dados["parametros"].get(material["id"]) or {})
        materiais[material["rotulo"]] = {
            "nome": material["nome"], "id": material["id"],
            "descritores": descritores,
            "vetor_completo": completo, "vetor_lastro": lastro,
            "perfil": perfil_eixos(completo, relacoes),
            "perfil_lastro": perfil_eixos(lastro, relacoes),
            "adsorbato": perfil_adsorbato(
                parametros.get("adsorbato") or {}, catalogo),
            "parametros_adsorbato": parametros.get("adsorbato") or {},
        }
    resultado = {"materiais": materiais, "comparacoes": {}, "delta": []}
    esquerda, direita = rotulos[0], rotulos[1]
    if esquerda in materiais and direita in materiais:
        a, b = materiais[esquerda], materiais[direita]
        resultado["comparacoes"]["completo"] = cosseno(a["vetor_completo"],
                                                      b["vetor_completo"])
        resultado["comparacoes"]["lastro"] = cosseno(a["vetor_lastro"],
                                                     b["vetor_lastro"])
        resultado["comparacoes"]["perfil"] = cosseno(a["perfil"], b["perfil"])
        for codigo in sorted(set(a["vetor_completo"]) | set(b["vetor_completo"])):
            va = a["vetor_completo"].get(codigo)
            vb = b["vetor_completo"].get(codigo)
            if va is None or vb is None:
                continue
            resultado["delta"].append({
                "codigo": codigo, "a": round(va, 4), "b": round(vb, 4),
                "delta": round(va - vb, 4), "abs": round(abs(va - vb), 4)})
        resultado["delta"].sort(key=lambda item: -item["abs"])
        for rotulo, info in materiais.items():
            resultado["comparacoes"]["%s_x_adsorbato" % rotulo] = cosseno(
                info["perfil"], info["adsorbato"])
    return resultado


def imprimir(analise: dict) -> None:
    materiais = analise["materiais"]
    print("== vetor normalizado (0-1) por descritor ==")
    print("| cod | A | B | delta (A-B) |")
    print("|---|---|---|---|")
    for item in analise["delta"]:
        print("| %s | %.3f | %.3f | %+.3f |" % (item["codigo"], item["a"],
                                                item["b"], item["delta"]))
    print("\n== cosseno entre materiais ==")
    for nome in ("completo", "lastro", "perfil"):
        item = analise["comparacoes"].get(nome) or {}
        if item.get("valor") is None:
            print("  %-9s sem dimensao comum" % nome)
            continue
        print("  %-9s cos = %.4f   (n = %d: %s)" % (
            nome, item["valor"], item["n"], ", ".join(item["dimensoes"])))
    print("\n== perfil por eixo (0-1) ==")
    eixos = sorted({eixo for info in materiais.values()
                    for eixo in list(info["perfil"]) + list(info["adsorbato"])})
    print("| eixo | A | B | adsorbato |")
    print("|---|---|---|---|")
    for eixo in eixos:
        a = materiais.get("A", {}).get("perfil", {}).get(eixo)
        b = materiais.get("B", {}).get("perfil", {}).get(eixo)
        c = materiais.get("A", {}).get("adsorbato", {}).get(eixo)
        print("| %s | %s | %s | %s |" % (
            eixo, "-" if a is None else "%.3f" % a,
            "-" if b is None else "%.3f" % b,
            "-" if c is None else "%.3f" % c))
    print("\n== cosseno material x adsorbato ==")
    for rotulo in ("A", "B"):
        item = analise["comparacoes"].get("%s_x_adsorbato" % rotulo) or {}
        if item.get("valor") is None:
            print("  %s: sem eixo comum" % rotulo)
            continue
        print("  %s x adsorbato: cos = %.4f   (n = %d: %s)" % (
            rotulo, item["valor"], item["n"], ", ".join(item["dimensoes"])))


def principal() -> int:
    analisador = argparse.ArgumentParser(
        description="Semelhanca de cosseno da matriz 7Dx4")
    analisador.add_argument("--banco", default=None,
                            help="caminho do banco (padrao: copia _qa_matriz)")
    analisador.add_argument("--json", action="store_true",
                            help="escrever semelhanca_cosseno.json")
    argumentos = analisador.parse_args()
    banco = Path(argumentos.banco) if argumentos.banco else (
        BANCO_COPIA if BANCO_COPIA.is_file() else BANCO_REAL)
    if not banco.is_file():
        raise SystemExit("banco nao encontrado: %s" % banco)
    print("banco:", banco)
    dados = carregar(banco)
    analise = analisar(dados)
    imprimir(analise)
    if argumentos.json:
        with open(SAIDA_JSON, "w", encoding="utf-8") as arquivo:
            json.dump(analise, arquivo, ensure_ascii=False, indent=1,
                      default=str)
        print("\njson:", SAIDA_JSON.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())

