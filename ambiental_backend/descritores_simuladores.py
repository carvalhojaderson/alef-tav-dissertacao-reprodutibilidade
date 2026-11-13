# -*- coding: utf-8 -*-
"""Mapa descritor 7Dx4 -> fontes que realmente produzem cada valor.

Tres tipos de fonte, todos ja existentes no nucleo cientifico:

    regra       `matriz_7d4.REGRAS` — algoritmo proprio do descritor
    simulador   `universal.SIMULADORES` — motor registrado (113 no catalogo)
    modelo      `modelos_adsorcao_v2` / `modelos_analiticos_v2` — isotermas

Regras de honestidade aplicadas aqui:

* so entra no descritor o que o motor devolveu ou o operador informou;
* simulador que apenas repete o parametro recebido (`superficie`, `nano`)
  grava o descritor como `presente` (dado informado), nunca como `calculado`;
* quando o motor roda com parametro padrao, a execucao e' `aproximada` e o
  valor padrao **nao** e' gravado no descritor;
* descritor sem fonte computacional aparece como `sem_simulador` e exige
  ensaio — nunca recebe numero inventado.
"""
from __future__ import annotations

from . import adaptadores, matriz_7d4, motores_ambientais

# ---------------------------------------------------------------------------
# Requisitos de entrada por simulador, medidos em
# `auditoria/inventario_simuladores.json` (113 registros, 31/10/2026), e o que
# cada saida alimenta na matriz.
#
# `tipo`:
#   calculo    — o motor calcula a grandeza a partir das entradas
#   parametro  — o motor devolve o proprio parametro (eco), com padrao interno
#   motor_real — integracao com motor externo (ASE, solver, etc.)
#
# `modo`:
#   valor — grava numero no descritor
#   apoio — registra dado de suporte, sem substituir o valor do descritor
# ---------------------------------------------------------------------------
SIMULADORES = {
    "superficie": {
        "motor": "universal.sim_superficie",
        "dominio": "Quimica - Superficie",
        "tipo": "parametro",
        "le_chaves": ["area_m2g"],
        "requisitos": [
            {"chave": "area_m2g", "unidade": "m2/g", "obrigatorio": True,
             "descricao": "area superficial BET medida do adsorvente"},
        ],
        "produz": [
            {"codigo": "S3", "chave": "area_m2g", "unidade": "m2/g",
             "modo": "valor", "estado": "presente",
             "memoria": ("area devolvida pelo simulador a partir do parametro "
                         "informado; nao e' calculo BET")},
        ],
    },
    "nano": {
        "motor": "universal.sim_nano",
        "dominio": "Materiais - Nano",
        "tipo": "calculo",
        "le_chaves": ["diametro_nm"],
        "requisitos": [
            {"chave": "diametro_nm", "unidade": "nm", "obrigatorio": True,
             "descricao": "diametro medio de particula (esfera equivalente)"},
        ],
        "produz": [
            {"codigo": "S5", "chave": "diametro_nm", "unidade": "nm",
             "modo": "valor", "estado": "presente",
             "origem": "parametro",
             "memoria": ("diametro informado pelo operador; o motor devolve "
                         "6/d (1/nm) e nao ecoa o diametro")},
            {"codigo": "S3", "chave": "area_relativa", "unidade": "1/nm",
             "modo": "apoio",
             "memoria": ("area relativa 6/d de esfera ideal; nao substitui "
                         "BET em m2/g")},
        ],
    },
    "cristalografia": {
        "motor": "universal.sim_cristalografia",
        "dominio": "Materiais - Cristalografia",
        "tipo": "motor_real",
        "le_chaves": ["angulo", "n", "parametro_rede", "parametro_rede_m"],
        "equivalentes": [["parametro_rede", "parametro_rede_m"]],
        "requisitos": [
            {"chave": "parametro_rede", "unidade": "angstrom",
             "obrigatorio": True,
             "descricao": "parametro de rede da fase cristalina"},
            {"chave": "n", "unidade": "adimensional", "obrigatorio": False,
             "descricao": "ordem de difracao (padrao 1)"},
            {"chave": "angulo", "unidade": "graus", "obrigatorio": False,
             "descricao": "angulo de difracao (padrao 90)"},
        ],
        "produz": [
            {"codigo": "P1", "chave": "densidade_g_cm3", "unidade": "g/cm3",
             "modo": "valor", "estado": "calculado",
             "memoria": ("densidade calculada pelo motor de cristalografia a "
                         "partir da rede e do elemento")},
            {"codigo": "S2", "chave": "d_espacamento_m", "unidade": "m",
             "modo": "apoio",
             "memoria": "espacamento interplanar calculado (Lei de Bragg)"},
        ],
    },
}


SIMULADORES.update({
    "dft": {
        "motor": "universal.sim_dft",
        "dominio": "Materiais - DFT",
        "tipo": "calculo",
        "le_chaves": ["material"],
        "requisitos": [
            {"chave": "material", "unidade": "texto", "obrigatorio": True,
             "descricao": "nome da fase/material consultado na base do motor"},
        ],
        "produz": [
            {"codigo": "P6", "chave": "bandgap_eV", "unidade": "eV",
             "modo": "valor", "estado": "estimado",
             "memoria": ("band gap de referencia interna do simulador "
                         "(declarado pelo proprio motor como 'nao DFT'); nao e' "
                         "medicao do material em estudo")},
        ],
    },
    "cfd": {
        "motor": "universal.sim_cfd",
        "dominio": "Fisica - Fluidos",
        "tipo": "calculo",
        "le_chaves": ["densidade", "diametro", "velocidade", "viscosidade"],
        "requisitos": [
            {"chave": "densidade", "unidade": "kg/m3", "obrigatorio": True,
             "descricao": "massa especifica do fluido"},
            {"chave": "velocidade", "unidade": "m/s", "obrigatorio": True,
             "descricao": "velocidade superficial no leito"},
            {"chave": "diametro", "unidade": "m", "obrigatorio": True,
             "descricao": "diametro caracteristico do leito/particula"},
            {"chave": "viscosidade", "unidade": "Pa.s", "obrigatorio": False,
             "descricao": "viscosidade dinamica (padrao 1e-3)"},
        ],
        "produz": [
            {"codigo": "C7", "chave": "Reynolds", "unidade": "adimensional",
             "modo": "apoio",
             "memoria": ("numero de Reynolds do escoamento no leito; apoia a "
                         "avaliacao de escalonamento, nao e' TRH")},
        ],
    },
    "fluido": {
        "motor": "universal.sim_fluido",
        "dominio": "Fisica - Fluidos",
        "tipo": "calculo",
        "le_chaves": ["densidade", "diametro", "velocidade", "viscosidade"],
        "requisitos": [
            {"chave": "densidade", "unidade": "kg/m3", "obrigatorio": True,
             "descricao": "massa especifica do fluido"},
            {"chave": "velocidade", "unidade": "m/s", "obrigatorio": True,
             "descricao": "velocidade do escoamento"},
            {"chave": "diametro", "unidade": "m", "obrigatorio": True,
             "descricao": "diametro da coluna"},
        ],
        "produz": [
            {"codigo": "C7", "chave": "Reynolds", "unidade": "adimensional",
             "modo": "apoio",
             "memoria": "regime hidraulico (laminar/turbulento) do leito"},
        ],
    },
})

# ---------------------------------------------------------------------------
# Requisitos das regras matematicas de `matriz_7d4.REGRAS` (algoritmo proprio de
# cada descritor). Chaves conferidas nas funcoes `_regra_*` do modulo.
# ---------------------------------------------------------------------------
REGRAS = {
    "S4": {
        "motor": "matriz_7d4._regra_s4", "unidade": "cm3/g",
        "requisitos": [
            {"chave": "rho_aparente", "unidade": "g/cm3", "obrigatorio": True,
             "descricao": "densidade aparente do leito"},
            {"chave": "rho_verdadeira", "unidade": "g/cm3", "obrigatorio": True,
             "descricao": "densidade real do solido (picnometria)"},
        ],
        "observacao": "V_p = 1/rho_aparente - 1/rho_verdadeira; devolve porosidade",
    },
    "P1": {
        "motor": "matriz_7d4._regra_p1", "unidade": "g/cm3",
        "requisitos": [
            {"chave": "massa_g", "unidade": "g", "obrigatorio": True,
             "descricao": "massa da amostra"},
            {"chave": "volume_cm3", "unidade": "cm3", "obrigatorio": True,
             "descricao": "volume deslocado/do leito"},
        ],
        "observacao": "rho = m/V",
    },
    "P3": {
        "motor": "matriz_7d4._regra_p3", "unidade": "cmol/kg",
        "requisitos": [
            {"chave": "volume_branco_mL", "unidade": "mL", "obrigatorio": True,
             "descricao": "volume gasto no branco"},
            {"chave": "volume_amostra_mL", "unidade": "mL", "obrigatorio": True,
             "descricao": "volume gasto na amostra"},
            {"chave": "concentracao_mol_L", "unidade": "mol/L",
             "obrigatorio": True, "descricao": "concentracao do extrator"},
            {"chave": "massa_g", "unidade": "g", "obrigatorio": True,
             "descricao": "massa de solo/material"},
            {"chave": "fator_extrator", "unidade": "adimensional",
             "obrigatorio": False, "descricao": "fator do extrator (padrao 1)"},
        ],
        "observacao": "CTC = (V_branco - V_amostra) x C x f x 100 / m",
    },
    "D1": {
        "motor": "matriz_7d4._regra_d1", "unidade": "mg/g",
        "requisitos": [
            {"chave": "pontos", "unidade": "lista[{Ce, qe}]",
             "obrigatorio": True,
             "descricao": ("pontos da isoterma; alternativa: C0_lista + "
                           "Ce_lista + volume_L + massa_g")},
        ],
        "observacao": "Langmuir linearizado Ce/qe = 1/(qmax*KL) + Ce/qmax",
    },
    "D2": {
        "motor": "matriz_7d4._regra_d2", "unidade": "L/mg",
        "requisitos": [
            {"chave": "pontos", "unidade": "lista[{Ce, qe}]",
             "obrigatorio": True,
             "descricao": "mesmos pontos usados em D1"},
            {"chave": "C0", "unidade": "mg/L", "obrigatorio": False,
             "descricao": "concentracao inicial para calcular RL"},
        ],
        "observacao": "KL = angular/intercepto; RL = 1/(1+KL*C0)",
    },
    "D3": {
        "motor": "matriz_7d4._regra_d3", "unidade": "g/(mg*min)",
        "requisitos": [
            {"chave": "pontos_cinetica", "unidade": "lista[{t, qt}]",
             "obrigatorio": True,
             "descricao": "minimo de 3 pontos positivos de cinetica"},
        ],
        "observacao": "PSO t/qt = 1/(k2*qe^2) + t/qe; devolve qe e t95",
    },
    "D6": {
        "motor": "matriz_7d4._regra_d6", "unidade": "%",
        "requisitos": [
            {"chave": "C0", "unidade": "mg/L", "obrigatorio": True,
             "descricao": "concentracao inicial"},
            {"chave": "Ce", "unidade": "mg/L", "obrigatorio": True,
             "descricao": "concentracao de equilibrio"},
            {"chave": "volume_L", "unidade": "L", "obrigatorio": False,
             "descricao": "volume do ensaio (para qe)"},
            {"chave": "massa_g", "unidade": "g", "obrigatorio": False,
             "descricao": "massa de adsorvente (para qe)"},
        ],
        "observacao": "R = (C0-Ce)/C0 x 100; qe = (C0-Ce)*V/m",
    },
    "C2": {
        "motor": "matriz_7d4._regra_c2", "unidade": "R$/g removido",
        "requisitos": [
            {"chave": "preco_kg", "unidade": "R$/kg", "obrigatorio": True,
             "descricao": "preco unitario do material"},
            {"chave": "qmax_mg_g", "unidade": "mg/g", "obrigatorio": True,
             "descricao": "capacidade maxima (D1)"},
        ],
        "observacao": "custo = preco_kg/qmax",
    },
    "C4": {
        "motor": "matriz_7d4._regra_c4", "unidade": "kWh/kg",
        "requisitos": [
            {"chave": "potencia_kW", "unidade": "kW", "obrigatorio": True,
             "descricao": "potencia do processo"},
            {"chave": "tempo_h", "unidade": "h", "obrigatorio": True,
             "descricao": "duracao do processo"},
            {"chave": "massa_kg", "unidade": "kg", "obrigatorio": True,
             "descricao": "massa de material processada"},
        ],
        "observacao": "E = P*t/m",
    },
    "C7": {
        "motor": "matriz_7d4._regra_c7", "unidade": "min",
        "requisitos": [
            {"chave": "volume_leito_m3", "unidade": "m3", "obrigatorio": True,
             "descricao": "volume do leito"},
            {"chave": "vazao_m3_h", "unidade": "m3/h", "obrigatorio": True,
             "descricao": "vazao de operacao"},
        ],
        "observacao": "TRH = V_leito/Q (h) convertido para min",
    },
}

SIMULADORES.update({
    "hidro": {
        "motor": "universal.sim_hidro",
        "dominio": "Terra - Hidro",
        "tipo": "motor_real",
        "le_chaves": ["area_km2", "precipitacao_mm"],
        "requisitos": [
            {"chave": "area_km2", "unidade": "km2", "obrigatorio": True,
             "descricao": "area da bacia hidrografica"},
            {"chave": "precipitacao_mm", "unidade": "mm/ano",
             "obrigatorio": True, "descricao": "precipitacao media anual"},
        ],
        "produz": [
            {"codigo": "C3", "chave": "vazao_m3s", "unidade": "m3/s",
             "modo": "apoio",
             "memoria": ("vazao media calculada pelo motor hidrologico; "
                         "contexto de disponibilidade hidrica")},
        ],
    },
    "poluicao": {
        "motor": "universal.sim_poluicao",
        "dominio": "Ambiente - Poluicao",
        "tipo": "calculo",
        "le_chaves": ["C0", "k", "t"],
        "requisitos": [
            {"chave": "C0", "unidade": "mg/L", "obrigatorio": True,
             "descricao": "concentracao inicial do contaminante"},
            {"chave": "k", "unidade": "1/tempo", "obrigatorio": True,
             "descricao": "constante de decaimento de primeira ordem"},
            {"chave": "t", "unidade": "tempo", "obrigatorio": True,
             "descricao": "tempo de contato"},
        ],
        "produz": [
            {"codigo": "D6", "chave": "C_final", "unidade": "mg/L",
             "modo": "apoio",
             "memoria": ("decaimento de primeira ordem C=C0*exp(-k*t); nao e' "
                         "remocao por adsorcao")},
        ],
    },
    "equilibrio": {
        "motor": "universal.sim_equilibrio",
        "dominio": "Quimica - Equilibrio",
        "tipo": "calculo",
        "le_chaves": ["T", "dG0"],
        "requisitos": [
            {"chave": "dG0", "unidade": "J/mol", "obrigatorio": True,
             "descricao": ("energia livre padrao da interacao "
                           "adsorvente-adsorbato")},
            {"chave": "T", "unidade": "K", "obrigatorio": True,
             "descricao": "temperatura absoluta"},
        ],
        "produz": [
            {"codigo": "D7", "chave": "K_equilibrio",
             "unidade": "adimensional", "modo": "apoio",
             "memoria": ("constante termodinamica K=exp(-dG0/RT); indica "
                         "espontaneidade, nao faixa de pH")},
        ],
    },
})

# ---------------------------------------------------------------------------
# Modelos de adsorcao (motores analiticos existentes) e o que cada um exige.
# Nenhum deles substitui medicao experimental: `natureza` viaja na resposta.
# ---------------------------------------------------------------------------
MODELOS = {
    "langmuir": {
        "motor": "modelos_adsorcao_v2.executar_modelo_adsorcao",
        "requisitos": [
            {"chave": "qmax", "unidade": "mg/g", "obrigatorio": True,
             "descricao": "capacidade maxima (descritor D1)"},
            {"chave": "KL", "unidade": "L/mg", "obrigatorio": True,
             "descricao": "constante de afinidade (descritor D2)"},
            {"chave": "Ce", "unidade": "mg/L", "obrigatorio": True,
             "descricao": "concentracao de equilibrio avaliada"},
        ],
        "descritores": ["D1", "D2"],
        "natureza": "calculo analitico do modelo; nao e' validacao experimental",
    },
    "freundlich": {
        "motor": "modelos_adsorcao_v2.executar_modelo_adsorcao",
        "requisitos": [
            {"chave": "Kf", "unidade": "(mg/g)(mg/L)^-1/n", "obrigatorio": True,
             "descricao": "constante de Freundlich"},
            {"chave": "n", "unidade": "adimensional", "obrigatorio": True,
             "descricao": "expoente de Freundlich"},
            {"chave": "Ce", "unidade": "mg/L", "obrigatorio": True,
             "descricao": "concentracao de equilibrio avaliada"},
        ],
        "descritores": ["D2"],
        "natureza": "calculo analitico do modelo; nao e' validacao experimental",
    },
    "langmuir_curva": {
        "motor": "modelos_analiticos_v2.isoterma_langmuir",
        "requisitos": [
            {"chave": "q_max", "unidade": "mg/g", "obrigatorio": True,
             "descricao": "capacidade maxima ajustada"},
            {"chave": "K_L", "unidade": "L/mg", "obrigatorio": True,
             "descricao": "constante de afinidade ajustada"},
            {"chave": "C_e", "unidade": "mg/L", "obrigatorio": True,
             "descricao": "concentracao de equilibrio avaliada"},
        ],
        "descritores": ["D1", "D2"],
        "natureza": "isoterma fechada; curva teorica, nao dado medido",
    },
    "freundlich_curva": {
        "motor": "modelos_analiticos_v2.isoterma_freundlich",
        "requisitos": [
            {"chave": "K_F", "unidade": "(mg/g)(mg/L)^-1/n", "obrigatorio": True,
             "descricao": "constante de Freundlich ajustada"},
            {"chave": "n", "unidade": "adimensional", "obrigatorio": True,
             "descricao": "expoente de Freundlich ajustado"},
            {"chave": "C_e", "unidade": "mg/L", "obrigatorio": True,
             "descricao": "concentracao de equilibrio avaliada"},
        ],
        "descritores": ["D2"],
        "natureza": "isoterma fechada; curva teorica, nao dado medido",
    },
    "pfo_cinetica": {
        "motor": "modelos_analiticos_v2.cinetica_adsorcao_primeira_ordem",
        "requisitos": [
            {"chave": "q_e_equilibrio", "unidade": "mg/g", "obrigatorio": True,
             "descricao": "qt de equilibrio"},
            {"chave": "k1", "unidade": "1/min", "obrigatorio": True,
             "descricao": "constante de pseudo-primeira ordem"},
            {"chave": "tempo", "unidade": "min", "obrigatorio": True,
             "descricao": "tempo avaliado"},
        ],
        "descritores": ["D3"],
        "natureza": "modelo analitico de cinetica; ajuste experimental necessario",
    },
}

# Motores proprios deste backend (analises_experimentais -> motores_ambientais):
# cobrem os 12 descritores que nenhum simulador do nucleo atendia (S1, S6, S7,
# P2, P4, P5, P7, D4, D5, C1, C5, C6). Entram no mesmo mapa de requisitos, para
# o painel do frontend mostrar exigencias de entrada identicas as dos outros.
SIMULADORES.update(motores_ambientais.mapa_simuladores())


def simuladores_do_descritor(codigo: str) -> list:
    """Simuladores cujo resultado alimenta (valor ou apoio) o descritor."""
    alvo = str(codigo or "").strip().upper()
    saida = []
    for nome, meta in SIMULADORES.items():
        for item in meta.get("produz") or []:
            if item.get("codigo") == alvo:
                saida.append({"simulador": nome, "motor": meta.get("motor"),
                              "tipo": meta.get("tipo"),
                              "modo": item.get("modo"),
                              "chave": item.get("chave"),
                              "unidade": item.get("unidade")})
    return saida


def modelos_do_descritor(codigo: str) -> list:
    alvo = str(codigo or "").strip().upper()
    return [{"modelo": nome, "motor": meta.get("motor"),
             "natureza": meta.get("natureza")}
            for nome, meta in MODELOS.items()
            if alvo in (meta.get("descritores") or [])]


def mapa() -> dict:
    """Os 28 descritores com as fontes que podem preenche-los ou apoia-los."""
    linhas = []
    for descritor in matriz_7d4.DESCRITORES:
        codigo = descritor["codigo"]
        regra = REGRAS.get(codigo)
        simuladores = simuladores_do_descritor(codigo)
        modelos = modelos_do_descritor(codigo)
        com_valor = [item for item in simuladores if item["modo"] == "valor"]
        if regra or com_valor:
            cobertura = "calculo_automatico"
        elif simuladores or modelos:
            cobertura = "apoio_ou_entrada_confirmada"
        else:
            cobertura = "sem_simulador"
        linhas.append({
            "codigo": codigo,
            "dimensao": descritor["dimensao"],
            "nome": descritor["nome"],
            "unidade": descritor["unidade"],
            "cobertura": cobertura,
            "regra": ({"motor": regra["motor"], "unidade": regra["unidade"],
                       "requisitos": regra["requisitos"],
                       "observacao": regra["observacao"]} if regra else None),
            "simuladores": simuladores,
            "modelos": modelos,
            "lacuna": ("exige ensaio/medicao: nenhum simulador ou regra "
                       "preenche este descritor"
                       if cobertura == "sem_simulador" else None),
        })
    return {
        "total": len(linhas),
        "com_regra_matematica": sum(1 for l in linhas if l["regra"]),
        "com_simulador": sum(1 for l in linhas if l["simuladores"]),
        "sem_simulador": sum(1 for l in linhas
                             if l["cobertura"] == "sem_simulador"),
        "descritores": linhas,
    }


# ---------------------------------------------------------------- disponibilidade
def _nomes_registrados() -> set:
    try:
        return set(adaptadores.nomes_disponiveis())
    except Exception:                                   # noqa: BLE001
        return set()


def disponibilidade() -> dict:
    """O motor de simuladores esta carregado neste processo?"""
    nomes = _nomes_registrados()
    estado = adaptadores.estado_motores()
    return {
        "motor": "universal.SIMULADORES",
        "carregado": bool(nomes),
        "total_registrados": len(nomes),
        "universal": estado.get("universal"),
        "motores": estado,
    }


def requisitos_de(nome: str) -> dict:
    """Requisitos de entrada declarados para um simulador ou modelo."""
    nome = str(nome or "").strip()
    if nome in SIMULADORES:
        meta = SIMULADORES[nome]
        return {"tipo": "simulador", "simulador": nome,
                "motor": meta.get("motor"), "tipo_fonte": meta.get("tipo"),
                "dominio": meta.get("dominio"),
                "requisitos": meta.get("requisitos"),
                "le_chaves": meta.get("le_chaves")}
    if nome in MODELOS:
        meta = MODELOS[nome]
        return {"tipo": "modelo", "modelo": nome, "motor": meta.get("motor"),
                "requisitos": meta.get("requisitos"),
                "descritores": meta.get("descritores"),
                "natureza": meta.get("natureza")}
    return {"tipo": "desconhecido", "nome": nome,
            "erro": "sem requisitos declarados para %s" % nome,
            "requisitos": []}


def _faltando(requisitos, parametros) -> list:
    faltando = []
    for item in requisitos or []:
        if not item.get("obrigatorio"):
            continue
        chave = item.get("chave")
        if parametros.get(chave) in (None, ""):
            faltando.append(chave)
    return faltando


def _padroes(meta, parametros) -> list:
    """Chaves que o motor le mas nao foram informadas (rodam com padrao)."""
    grupos = meta.get("equivalentes") or []
    faltando = []
    for chave in (meta.get("le_chaves") or []):
        if parametros.get(chave) not in (None, ""):
            continue
        grupo = next((g for g in grupos if chave in g), None)
        if grupo and any(parametros.get(outra) not in (None, "") for outra in grupo):
            continue
        faltando.append(chave)
    return faltando


def _faltando_grupos(meta, parametros) -> list:
    """Chaves em que o motor aceita 'um de' varios; nenhum informado = falta."""
    faltando = []
    for grupo in meta.get("precisa_um_de") or []:
        if not any(parametros.get(chave) not in (None, "", [], {})
                   for chave in grupo):
            faltando.append("um de: %s" % ", ".join(grupo))
    return faltando


def requisitos_pendentes(nome: str, parametros: dict = None) -> list:
    """Entradas obrigatorias que faltam para executar o simulador."""
    meta = SIMULADORES.get(str(nome or "").strip())
    if meta is None:
        return []
    parametros = dict(parametros or {})
    return (_faltando(meta.get("requisitos"), parametros)
            + _faltando_grupos(meta, parametros))


def classificar(nome: str, parametros: dict = None) -> dict:
    """Estado antes de executar: pronto, aproximado, bloqueado ou sem mapa."""
    nome = str(nome or "").strip()
    parametros = dict(parametros or {})
    meta = SIMULADORES.get(nome)
    if meta is None:
        return {"estado": "sem_mapeamento", "faltando": [], "padroes": [],
                "motivo": "sem requisitos declarados em descritores_simuladores"}
    faltando = _faltando(meta.get("requisitos"), parametros)
    faltando += _faltando_grupos(meta, parametros)
    padroes = _padroes(meta, parametros)
    if faltando:
        return {"estado": "bloqueado_por_parametros", "faltando": faltando,
                "padroes": padroes,
                "motivo": "faltam entradas obrigatorias: %s"
                          % ", ".join(faltando)}
    if padroes:
        return {"estado": "ok_com_aproximacao", "faltando": [],
                "padroes": padroes,
                "motivo": "o motor usa padrao interno para: %s"
                          % ", ".join(padroes)}
    return {"estado": "pronto", "faltando": [], "padroes": [], "motivo": None}


def descritores_de(nome: str, parametros: dict = None,
                   resultado=None) -> dict:
    """Traduz saidas do simulador em atualizacoes de descritores da matriz.

    `modo="valor"` devolve numero para gravar; `modo="apoio"` devolve dado de
    suporte (nao substitui o valor do descritor). Saida ausente vira aviso.
    """
    nome = str(nome or "").strip()
    meta = SIMULADORES.get(nome)
    parametros = dict(parametros or {})
    resultado = resultado if isinstance(resultado, dict) else {}
    if meta is None:
        return {"descritores": [],
                "avisos": ["simulador %s nao tem descritores mapeados" % nome]}
    valores, avisos = [], []
    for item in meta.get("produz") or []:
        chave = item.get("chave")
        codigo = item.get("codigo")
        de_parametro = item.get("origem") == "parametro"
        fonte_dado = parametros if de_parametro else resultado
        if chave not in fonte_dado:
            avisos.append("saida '%s' ausente no %s de %s"
                          % (chave, "parametro" if de_parametro else
                             "resultado", nome))
            continue
        saida = fonte_dado.get(chave)
        registro = {
            "codigo": codigo, "modo": item.get("modo"),
            "chave": chave,
            "unidade": item.get("unidade"),
            "fonte": "%s (saida %s)" % (meta.get("motor"), chave),
            "memoria": item.get("memoria"),
        }
        if item.get("modo") == "apoio":
            registro.update({"valor": None, "valor_apoio": saida})
            valores.append(registro)
            continue
        if not isinstance(saida, (int, float)):
            avisos.append("saida '%s' de %s nao e' numerica" % (chave, nome))
            continue
        if (meta.get("tipo") == "parametro"
                and parametros.get(chave) in (None, "")):
            avisos.append("'%s' veio do padrao interno do motor; descritor %s "
                          "nao foi gravado" % (chave, codigo))
            continue
        registro.update({"valor": float(saida),
                         "estado": item.get("estado") or "calculado"})
        valores.append(registro)
    return {"descritores": valores, "avisos": avisos}





# ------------------------------------------------------------------- execucao
def executar(nome: str, parametros: dict = None, pergunta: str = "",
             requer_completo: bool = True, timeout_s: int = None) -> dict:
    """Executa o simulador real e traduz o resultado em descritores.

    `requer_completo=True` (padrao) nao executa quando falta entrada
    obrigatoria: devolve `bloqueado_por_parametros` com a lista do que falta.
    Com `requer_completo=False` (execucao manual do painel) roda mesmo assim e
    marca `ok_com_aproximacao` quando o motor usa padroes internos.
    """
    nome = str(nome or "").strip()
    parametros = dict(parametros or {})
    previo = classificar(nome, parametros)
    base = {
        "simulador": nome,
        "parametros": parametros,
        "requisitos": requisitos_de(nome),
        "faltando": previo.get("faltando") or [],
        "parametros_padrao": previo.get("padroes") or [],
        "motivo": previo.get("motivo"),
        "descritores": [],
        "avisos": [],
        "resultado": None,
        "erro": None,
        "executado": False,
        "duracao_s": None,
    }
    if nome not in _nomes_registrados():
        base.update({"estado": "indisponivel",
                     "erro": "simulador nao registrado no motor universal"})
        return base
    if requer_completo and previo["estado"] == "bloqueado_por_parametros":
        base.update({"estado": "bloqueado_por_parametros"})
        return base
    saida = adaptadores.executar_simulador(nome, pergunta or "", parametros,
                                           timeout_s=timeout_s)
    base.update({
        "estado_motor": saida.get("estado"),
        "resultado": saida.get("resultado"),
        "erro": saida.get("erro"),
        "duracao_s": saida.get("duracao_s"),
        "executado": saida.get("estado") == "ok",
        "motor": saida.get("motor"),
    })
    if saida.get("estado") != "ok":
        base["estado"] = ("erro" if saida.get("estado") == "erro"
                          else saida.get("estado") or "erro")
        return base
    mapeado = descritores_de(nome, parametros, saida.get("resultado"))
    base["descritores"] = mapeado["descritores"]
    base["avisos"] = mapeado["avisos"]
    if previo["estado"] == "sem_mapeamento":
        base["estado"] = "ok_sem_descritor"
    elif previo["estado"] == "pronto":
        base["estado"] = "ok"
    else:
        base["estado"] = "ok_com_aproximacao"
    return base


def catalogo(historico=None, somente_mapeados: bool = False) -> dict:
    """Painel operacional: requisitos, descritores e ultima execucao.

    `historico` e' a lista de execucoes lida de `amb_simulacoes`; o modulo com
    acesso ao banco monta essa lista e passa aqui.
    """
    historico = list(historico or [])
    por_simulador = {}
    for item in historico:
        nome = item.get("simulador")
        if not nome:
            continue
        registro = por_simulador.setdefault(
            nome, {"total": 0, "sucessos": 0, "falhas": 0,
                   "ultima": None, "erros": []})
        registro["total"] += 1
        estado = (item.get("estado") or "").strip()
        if estado in ("ok", "ok_com_aproximacao", "ok_sem_descritor"):
            registro["sucessos"] += 1
        else:
            registro["falhas"] += 1
            if item.get("erro"):
                registro["erros"].append({"quando": item.get("quando"),
                                          "erro": str(item["erro"])[:300]})
        if registro["ultima"] is None:
            registro["ultima"] = item
    registrados = _nomes_registrados()
    nomes = list(SIMULADORES)
    for nome in adaptadores.SIMULADORES_AMBIENTAIS:
        if nome not in nomes:
            nomes.append(nome)
    linhas = []
    for nome in nomes:
        meta = SIMULADORES.get(nome) or {}
        hist = por_simulador.get(nome) or {}
        item = {
            "simulador": nome,
            "motor": meta.get("motor") or "universal.SIMULADORES",
            "dominio": meta.get("dominio"),
            "tipo": meta.get("tipo") or "nao_mapeado",
            "disponivel": nome in registrados,
            "estado_operacional": ("disponivel" if nome in registrados
                                   else "indisponivel"),
            "requisitos": meta.get("requisitos") or [],
            "le_chaves": meta.get("le_chaves") or [],
            "descritores": [{"codigo": p.get("codigo"),
                             "modo": p.get("modo"),
                             "chave": p.get("chave"),
                             "unidade": p.get("unidade")}
                            for p in (meta.get("produz") or [])],
            "total_execucoes": hist.get("total", 0),
            "sucessos": hist.get("sucessos", 0),
            "falhas": hist.get("falhas", 0),
            "ultima_execucao": hist.get("ultima"),
            "erros": hist.get("erros") or [],
        }
        if somente_mapeados and not item["descritores"]:
            continue
        linhas.append(item)
    return {
        "motor": "universal.SIMULADORES",
        "total": len(linhas),
        "disponiveis": sum(1 for l in linhas if l["disponivel"]),
        "com_descritor": sum(1 for l in linhas if l["descritores"]),
        "simuladores": linhas,
    }

