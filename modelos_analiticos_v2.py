"""Modelos analiticos v2 para simulacoes cientificas.

Os resultados sao teoricos e dependem das hipoteses e unidades informadas.
Este modulo nao representa validacao experimental nem simulacao atomistica.
"""

import math

R_GAS = 8.314462618  # J/(mol K)
G_PADRAO = 9.80665   # m/s^2


def _finito(nome, valor):
    valor = float(valor)
    if not math.isfinite(valor):
        raise ValueError(f"{nome} deve ser um numero finito.")
    return valor


def _nao_negativo(nome, valor):
    valor = _finito(nome, valor)
    if valor < 0:
        raise ValueError(f"{nome} nao pode ser negativo.")
    return valor


def energia_cinetica(massa_kg, velocidade_m_s):
    massa = _nao_negativo("massa_kg", massa_kg)
    velocidade = _finito("velocidade_m_s", velocidade_m_s)
    return {
        "modelo": "energia_cinetica_classica",
        "energia_J": 0.5 * massa * velocidade**2,
        "unidade": "J",
        "natureza": "analitico"
    }


def energia_potencial_gravitacional(massa_kg, altura_m, g=G_PADRAO):
    massa = _nao_negativo("massa_kg", massa_kg)
    altura = _finito("altura_m", altura_m)
    gravidade = _nao_negativo("g", g)
    return {
        "modelo": "energia_potencial_gravitacional",
        "energia_J": massa * gravidade * altura,
        "unidade": "J",
        "referencia": "nivel de altura zero definido pelo usuario",
        "natureza": "analitico"
    }


def quantidade_movimento(massa_kg, velocidade_m_s):
    massa = _nao_negativo("massa_kg", massa_kg)
    velocidade = _finito("velocidade_m_s", velocidade_m_s)
    return {
        "modelo": "quantidade_de_movimento",
        "momento_kg_m_s": massa * velocidade,
        "unidade": "kg m/s",
        "natureza": "analitico"
    }


def isoterma_langmuir(q_max, K_L, C_e):
    q_max = _nao_negativo("q_max", q_max)
    K_L = _nao_negativo("K_L", K_L)
    C_e = _nao_negativo("C_e", C_e)
    q_e = q_max * K_L * C_e / (1.0 + K_L * C_e)
    return {
        "modelo": "Langmuir",
        "q_max": q_max,
        "K_L": K_L,
        "C_e": C_e,
        "q_e": q_e,
        "natureza": "modelo analitico; nao validado experimentalmente"
    }


def isoterma_freundlich(K_F, n, C_e):
    K_F = _nao_negativo("K_F", K_F)
    n = _finito("n", n)
    C_e = _nao_negativo("C_e", C_e)
    if n <= 0:
        raise ValueError("n deve ser maior que zero.")
    q_e = K_F * C_e**(1.0 / n)
    return {
        "modelo": "Freundlich",
        "K_F": K_F,
        "n": n,
        "C_e": C_e,
        "q_e": q_e,
        "natureza": "modelo analitico; nao validado experimentalmente"
    }


def cinetica_adsorcao_primeira_ordem(q_e_equilibrio, k1, tempo):
    q_e = _nao_negativo("q_e_equilibrio", q_e_equilibrio)
    k1 = _nao_negativo("k1", k1)
    tempo = _nao_negativo("tempo", tempo)
    qt = q_e * (1.0 - math.exp(-k1 * tempo))
    return {
        "modelo": "adsorcao_pseudo_primeira_ordem",
        "q_t": qt,
        "q_e_equilibrio": q_e,
        "k1": k1,
        "tempo": tempo,
        "natureza": "modelo analitico; ajuste experimental nao realizado"
    }


def arrhenius(k0, Ea_J_mol, T_K):
    k0 = _nao_negativo("k0", k0)
    Ea = _nao_negativo("Ea_J_mol", Ea_J_mol)
    T = _finito("T_K", T_K)
    if T <= 0:
        raise ValueError("T_K deve ser maior que zero.")
    k = k0 * math.exp(-Ea / (R_GAS * T))
    return {
        "modelo": "Arrhenius",
        "k": k,
        "k0": k0,
        "Ea_J_mol": Ea,
        "T_K": T,
        "unidade_k": "mesma unidade de k0",
        "natureza": "analitico"
    }


def decaimento_primeira_ordem(C0, k, tempo):
    C0 = _nao_negativo("C0", C0)
    k = _nao_negativo("k", k)
    tempo = _nao_negativo("tempo", tempo)
    concentracao = C0 * math.exp(-k * tempo)
    return {
        "modelo": "decaimento_primeira_ordem",
        "C_t": concentracao,
        "C0": C0,
        "k": k,
        "tempo": tempo,
        "natureza": "modelo analitico; nao implica eficacia real de tratamento"
    }


def area_superficie_esfera(diametro_m, densidade_kg_m3=None):
    diametro = _finito("diametro_m", diametro_m)
    if diametro <= 0:
        raise ValueError("diametro_m deve ser maior que zero.")

    resultado = {
        "modelo": "esfera_ideal",
        "diametro_m": diametro,
        "area_m2": math.pi * diametro**2,
        "volume_m3": math.pi * diametro**3 / 6.0,
        "natureza": "geometria ideal; nao representa porosidade real"
    }

    if densidade_kg_m3 is not None:
        densidade = _finito("densidade_kg_m3", densidade_kg_m3)
        if densidade <= 0:
            raise ValueError("densidade_kg_m3 deve ser maior que zero.")
        resultado["area_especifica_m2_kg"] = 6.0 / (
            densidade * diametro
        )

    return resultado
