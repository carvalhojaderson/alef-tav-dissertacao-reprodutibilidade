# -*- coding: utf-8 -*-
"""Testes dos motores ambientais proprios (`motores_ambientais.MOTORES`).

O que se prova aqui:

    - o registro tem os 16 motores, cada um com funcao, nivel de validacao e
      descritores de saida que existem na matriz 7Dx4;
    - todo motor devolve o envelope padrao (metodo, versao, nivel, resultado,
      limitacoes) para que o painel e o relatorio possam exibir a origem;
    - entrada obrigatoria ausente levanta `EntradaInvalida` — nenhum motor
      preenche lacuna com valor padrao inventado;
    - os resultados respeitam as relacoes fisicas que os definem (PZC dentro da
      faixa medida, D50 entre o menor e o maior diametro, perigo crescendo com
      metal pesado).

Nenhum teste usa rede: os motores sao calculo puro sobre as entradas.
"""
from __future__ import annotations

import pytest

from ambiental_backend import analises_experimentais as ax
from ambiental_backend import matriz_7d4
from ambiental_backend import motores_ambientais as ma

NIVEIS = (ax.NIVEL_ANALITICO, ax.NIVEL_AJUSTE, ax.NIVEL_TABELA,
          ax.NIVEL_INDICE)

#: Entrada minima de cada motor, com valores coerentes com a faixa fisica.
ENTRADAS = {
    "pzc_deriva_ph": {"ph_inicial": [3.0, 5.0, 7.0, 9.0, 11.0],
                      "ph_final": [4.1, 6.2, 7.0, 7.6, 8.3]},
    "pzc_titulacao_massa": {"massa_g_L": [0.5, 1.0, 2.0, 4.0],
                            "ph_equilibrio": [5.2, 6.0, 6.9, 7.8]},
    "boehm_grupos": {"naoh_mmol_g": 0.85, "na2co3_mmol_g": 0.42,
                     "nahco3_mmol_g": 0.18, "hcl_mmol_g": 0.35},
    "ftir_grupos": {"bandas_cm1": [3420, 2920, 1700, 1590, 1450, 1100]},
    "granulometria_psd": {"diametros_um": [12.5, 25.0, 45.0, 63.0, 90.0],
                          "metodo": "analise_de_imagem"},
    "fractal_agregacao": {
        "diametros_um": [12.5, 25.0, 45.0, 63.0, 90.0, 125.0],
        "massas_acumuladas_pct": [2.0, 9.0, 24.0, 45.0, 66.0, 83.0]},
    "angulo_contato": {"angulo_agua_deg": 78.5,
                       "angulo_diiodometano_deg": 45.2},
    "tga_tangente": {"temperatura_C": [30.0, 100.0, 200.0, 300.0, 400.0,
                                       500.0, 600.0],
                     "massa_pct": [99.5, 97.0, 93.0, 84.0, 62.0, 34.0, 21.0]},
    "lixiviacao_cinetica": {
        "tempo_s": [60.0, 300.0, 900.0, 1800.0, 3600.0, 7200.0],
        "concentracao_mg_L": [0.4, 1.8, 3.1, 3.9, 4.2, 4.3],
        "volume_L": 0.5, "massa_amostra_g": 2.0, "teor_inicial_mg_kg": 2000.0},
    "solubilidade_imersao": {"massa_inicial_g": 5.0, "massa_final_g": 4.62},
    "seletividade_competitiva": {
        "componentes": [{"nome": "chumbo", "qmax_mg_g": 118.0,
                         "K_L_L_mg": 0.42},
                        {"nome": "cobre", "qmax_mg_g": 74.0,
                         "K_L_L_mg": 0.21}],
        "concentracoes_mg_L": [10.0, 10.0]},
    "regeneracao_reuso": {"capacidades_mg_g": [118.0, 106.0, 97.0, 88.0],
                          "desorcao_pct": [94.0, 91.0, 88.0, 85.0]},
    "perigo_composicao": {"composicao": [
        {"substancia": "chumbo", "fracao": 0.15},
        {"substancia": "celulose", "fracao": 0.85}]},
    "reciclabilidade": {"composicao": [{"classe": "casca", "fracao": 0.85},
                                       {"classe": "celulose", "fracao": 0.15}],
                        "ciclos_uteis": 4, "massa_reuso_kg": 0.85,
                        "massa_total_kg": 1.0},
    "conformidade_limites": {"analitos": {"chumbo": 0.004, "pH": 7.2},
                             "norma": "ms_888_2021"},
    "composicao_elementar": {"elementos_pct": {"C": 78.4, "H": 2.1, "O": 17.9,
                                               "N": 0.9, "Si": 0.7},
                             "elementos_principais": ["C", "O"],
                             "formula_declarada": "C"},
}


# ------------------------------------------------------------------- registro
def test_registro_completo():
    assert len(ma.MOTORES) == 16
    assert set(ma.MOTORES) == set(ENTRADAS)
    for nome, meta in ma.MOTORES.items():
        assert callable(meta["funcao"]), nome
        assert meta["nivel_validacao"] in NIVEIS, nome
        assert meta["dominio"] and meta["natureza"], nome
        assert meta["requisitos"] and meta["produz"], nome


def test_descritores_produzidos_existem_na_matriz():
    conhecidos = set(matriz_7d4.DESCRITORES_POR_CODIGO)
    for nome, meta in ma.MOTORES.items():
        for item in meta["produz"]:
            assert item["codigo"] in conhecidos, (nome, item["codigo"])
            assert item["chave"] and item["unidade"], (nome, item["chave"])


@pytest.mark.parametrize("nome", sorted(ma.MOTORES))
def test_envelope_padrao(nome):
    saida = ma.MOTORES[nome]["funcao"]("pergunta de teste",
                                       dict(ENTRADAS[nome]))
    for chave in ("simulador", "motor", "metodo", "versao_metodo",
                  "nivel_validacao", "resultado", "limitacoes", "pergunta"):
        assert chave in saida, (nome, chave)
    assert saida["motor"] == "ambiental.analises_experimentais"
    assert saida["metodo"], nome
    assert saida["limitacoes"], nome
    assert isinstance(saida["resultado"], dict) and saida["resultado"], nome


@pytest.mark.parametrize("nome", sorted(ma.MOTORES))
def test_entrada_ausente_nao_inventa_valor(nome):
    with pytest.raises(ax.EntradaInvalida):
        ma.MOTORES[nome]["funcao"]("", {})


# -------------------------------------------------------------- resultados
def test_pzc_fica_dentro_da_faixa_medida():
    saida = ma.pzc_deriva_ph("", dict(ENTRADAS["pzc_deriva_ph"]))
    assert 3.0 <= saida["pzc"] <= 11.0
    assert saida["extrapolado"] in (True, False)


def test_boehm_acidos_totais_nao_menor_que_carboxilicas():
    res = ma.boehm_grupos("", dict(ENTRADAS["boehm_grupos"]))["resultado"]
    total = res.get("acidos_totais_mmol_g")
    carboxilicas = res.get("carboxilicas_mmol_g")
    if total is not None and carboxilicas is not None:
        assert total >= carboxilicas


def test_granulometria_d50_entre_extremos():
    saida = ma.granulometria_psd("", dict(ENTRADAS["granulometria_psd"]))
    diametros = ENTRADAS["granulometria_psd"]["diametros_um"]
    assert min(diametros) <= saida["d50_um"] <= max(diametros)


def test_conformidade_aponta_falha_acima_do_limite():
    entrada = {"analitos": {"chumbo": 0.5}, "norma": "ms_888_2021"}
    res = ma.conformidade_limites("", entrada)["resultado"]
    assert res["falhas"], res
    assert res["status_geral"] in ("nao_conforme", "nao_atende", "falha")


def test_perigo_sobe_com_metal_pesado():
    leve = {"composicao": [{"substancia": "celulose", "fracao": 1.0}]}
    pesado = {"composicao": [{"substancia": "chumbo", "fracao": 1.0}]}
    a = ma.perigo_composicao("", leve)["resultado"]
    b = ma.perigo_composicao("", pesado)["resultado"]
    assert b["indice_perigo"] > a["indice_perigo"]


def test_solubilidade_calculada():
    saida = ma.solubilidade_imersao("", dict(ENTRADAS["solubilidade_imersao"]))
    assert 0.0 <= saida["solubilidade_pct"] <= 100.0


def test_composicao_elementar_normaliza():
    saida = ma.composicao_elementar("", dict(ENTRADAS["composicao_elementar"]))
    assert saida["pureza_pct"] is not None
    assert 90.0 <= saida["pureza_pct"] <= 100.0
    assert saida["formula_empirica"]
    molar = saida["massa_molar_g_mol"]
    assert molar is None or molar > 0


def test_regeneracao_conta_ciclos_validos():
    saida = ma.regeneracao_reuso("", dict(ENTRADAS["regeneracao_reuso"]))
    ciclos = saida["ciclos_uteis"]
    assert ciclos is None or 0 <= ciclos <= 4
