# -*- coding: utf-8 -*-
"""Dossie de preenchimento da matriz 7Dx4 para KL-KOH-1:1 (A) e KL-KOH-2:1 (B).

O que este arquivo e'
=====================

Um dicionario de dados, sem logica de escrita: para cada um dos 28 descritores
ele diz **de onde sai o valor** e **qual o lastro** desse valor. Quem executa e'
`preencher_matriz.py`.

Niveis de lastro (`nivel`)
==========================

    1  medido       ensaio de bancada publicado (Brazil et al., 2026)
    2  derivado     conta fechada sobre dado medido + constante declarada
    3  cenario      motor/regra do sistema alimentado com entrada declarada
    4  n/a          descritor que nao governa o processo em estudo

Nada aqui e' apresentado como medicao do material: o nivel viaja junto com o
valor e vai para `amb_descritores.dados_json.complemento.nivel`.

Rotas (`rota`)
==============

    banco:CODIGO          valor ja existente no banco (so rotula a fonte)
    motor:NOME/chave      saida de um dos 25 simuladores (roda no palco 3.10)
    regra:CODIGO          `matriz_7d4.REGRAS[CODIGO]` sobre `dados`
    direto                valor/texto declarado no proprio dossie

Constantes declaradas
=====================

`RHO_VERDADEIRA` (1,90 g/cm3) e a densidade do esqueleto carbonoso usada para
converter o volume de poros medido (S4) em densidade aparente (P1). Trocar a
constante muda P1; ela esta isolada aqui de proposito e aparece na memoria do
descritor.
"""
from __future__ import annotations

PESQUISA = "pesq_63b32e62389dae7c"

MATERIAIS = [
    {"rotulo": "A", "id": "mat_ca84ac210575584a", "nome": "KL-KOH-1:1"},
    {"rotulo": "B", "id": "mat_358eb4207c9fb795", "nome": "KL-KOH-2:1"},
]

#: Densidade do esqueleto carbonoso (g/cm3) - constante declarada, nao medida.
RHO_VERDADEIRA = 1.90

#: Dado de bancada disponivel (Brazil et al., 2026).  Unica ancora real.
ANCORAS = {
    "A": {"S3": 1262.0, "S4": 0.58, "D1": 100.0},
    "B": {"S3": 963.0, "S4": 0.49, "D1": 100.0},
}
FONTE_ANCORA = "Brazil et al., 2026 (ensaio de bancada)"

#: Condicao de ensaio declarada na pesquisa (pH 5,5; 25 C).
FONTE_ENSAIO = "condicao de ensaio da pesquisa (pH 5,5; 25 C)"

#: C0 do ensaio de adsorcao e Ce medido no lote de conformidade, em mg/L.
C0_MG_L = 20.0
CE_MG_L = 0.0072


def derivados(rotulo: str) -> dict:
    """Grandezas que saem do dado medido sem nenhuma entrada nova."""
    ancora = ANCORAS[rotulo]
    volume = ancora["S4"]
    area = ancora["S3"]
    rho_aparente = 1.0 / (volume + 1.0 / RHO_VERDADEIRA)
    diametro_nm = 4.0 * volume / area * 1000.0  # 4V/S em nm (modelo cilindrico)
    porosidade = volume / (volume + 1.0 / RHO_VERDADEIRA)
    return {
        "rho_aparente": rho_aparente,
        "diametro_poro_nm": diametro_nm,
        "porosidade": porosidade,
        "area": area,
        "volume": volume,
        "qmax": ancora["D1"],
    }



def entradas_motores(rotulo: str) -> dict:
    """Parametros declarados por simulador (nivel 3 - cenario).

    Os valores descrevem um carvao ativado quimicamente com KOH produzido a
    partir de lignina Kraft: carbono majoritario, superficie basica, pouca
    lixiviacao, particula micrometrica.  Onde o dado medido do material existe
    (S3, S4, D1) ele e' usado; o resto e' entrada declarada, igual para A e B
    porque nao ha medicao que os diferencie.
    """
    base = derivados(rotulo)
    return {
        "pzc_deriva_ph": {
            "ph_inicial": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0],
            "ph_final": [3.6, 5.4, 6.9, 7.4, 8.6, 10.6],
        },
        "boehm_grupos": {"naoh_mmol_g": 0.80, "na2co3_mmol_g": 0.50,
                         "nahco3_mmol_g": 0.30, "hcl_mmol_g": 0.20},
        "tga_tangente": {
            "temperatura_C": [30, 100, 200, 400, 500, 600, 700, 800],
            "massa_pct": [96.0, 93.0, 90.0, 84.0, 76.0, 64.0, 48.0, 33.0],
            "taxa_aquecimento_C_min": 10.0,
        },
        "granulometria_psd": {"diametros_um": [5.0, 10.0, 20.0, 30.0, 45.0,
                                               63.0, 90.0]},
        "angulo_contato": {"angulo_agua_deg": 95.0,
                           "angulo_diiodometano_deg": 60.0},
        "lixiviacao_cinetica": {
            "tempo_s": [3600, 7200, 14400, 28800, 86400],
            "fracao_lixiviada": [0.002, 0.004, 0.006, 0.008, 0.012],
        },
        "solubilidade_imersao": {"massa_inicial_g": 1.0, "massa_final_g": 0.998},
        "composicao_elementar": {
            "elementos_pct": {"C": 85.0, "H": 1.6, "N": 0.4, "S": 0.2,
                              "O": 7.8},
            "elementos_principais": ["C", "H", "N", "S"],
        },
        "conformidade_limites": {
            "analitos": {"sulfametoxazol": CE_MG_L},
            "limites": {"sulfametoxazol": 0.05},
        },
        "regeneracao_reuso": {
            "capacidades_mg_g": [base["qmax"], 0.95 * base["qmax"],
                                 0.91 * base["qmax"], 0.87 * base["qmax"],
                                 0.84 * base["qmax"], 0.80 * base["qmax"]],
            "desorcao_pct": 92.0,
        },
        "seletividade_competitiva": {
            "componentes": [
                {"nome": "sulfametoxazol", "qmax_mg_g": base["qmax"],
                 "K_L_L_mg": 0.1497},
                {"nome": "ibuprofeno", "qmax_mg_g": 1.2 * base["qmax"],
                 "K_L_L_mg": 0.045},
            ],
            "concentracoes_mg_L": [C0_MG_L, C0_MG_L],
        },
        "reciclabilidade": {"composicao": [{"classe": "carvao ativado",
                                           "fracao": 1.0}],
                            "ciclos_uteis": 4,
                            "massa_reuso_kg": 930.0,
                            "massa_total_kg": 1000.0},
        "perigo_composicao": {"composicao": [
            {"substancia": "carbono", "fracao": 0.85},
            {"substancia": "zinco", "fracao": 0.002},
            {"substancia": "cobre", "fracao": 0.001},
        ]},
    }


def dados_regras(rotulo: str) -> dict:
    """Entradas das regras de `matriz_7d4` que o motor nao cobre."""
    base = derivados(rotulo)
    # Isoterma e cinetica: cenarios coerentes com o qmax medido.  Nao sao
    # ajuste de dado experimental - servem para exercitar a regra e ficam
    # marcados como nivel 3 no descritor.
    qmax = base["qmax"]
    kl = 0.05
    pontos = []
    for ce in (1.0, 5.0, 10.0, 20.0, 40.0, 80.0):
        pontos.append({"Ce": ce,
                       "qe": round(qmax * kl * ce / (1.0 + kl * ce), 4)})
    k2 = 1.9e-3
    cinetica = []
    for tempo in (5, 10, 20, 40, 80, 120, 180):
        qt = (k2 * qmax ** 2 * tempo) / (1.0 + k2 * qmax * tempo)
        cinetica.append({"t": float(tempo), "qt": round(qt, 4)})
    return {
        "S4": {"rho_aparente": round(base["rho_aparente"], 6),
               "rho_verdadeira": RHO_VERDADEIRA},
        "P1": {"massa_g": round(base["rho_aparente"], 6), "volume_cm3": 1.0},
        "P3": {"volume_branco_mL": 25.0, "volume_amostra_mL": 23.5,
               "concentracao_mol_L": 0.1, "massa_g": 0.5,
               "fator_extrator": 1.0},
        "D1": {"pontos": pontos, "C0": C0_MG_L},
        "D2": {"pontos": pontos, "C0": C0_MG_L},
        "D3": {"pontos_cinetica": cinetica},
        "D6": {"C0": C0_MG_L, "Ce": CE_MG_L, "volume_L": 0.05,
               "massa_g": 0.01},
        "C2": {"preco_kg": 12.0, "qmax_mg_g": qmax},
        "C4": {"potencia_kW": 2.0, "tempo_h": 2.0, "massa_kg": 1.0},
        "C7": {"volume_leito_m3": 0.002, "vazao_m3_h": 0.010},
    }

# ---------------------------------------------------------------------------
# As 28 celulas.  `rota` diz como o valor entra; `nivel` diz quanto ele vale.
# ---------------------------------------------------------------------------
CELULAS = [
    {"codigo": "S1", "rota": "motor:composicao_elementar/pureza_pct",
     "nivel": 3, "base": "CHNS declarado; pureza = fracao da fase carbonosa",
     "fonte": "composicao_elementar sobre CHNS declarado"},
    {"codigo": "S2", "rota": "direto", "nivel": 3,
     "valor_texto": ("amorfo: halo largo em 2-theta ~ 24 graus e banda em "
                     "~ 43 graus, sem reflexoes de grafite cristalino"),
     "unidade": "texto", "estado": "estimado",
     "base": "padrao de DRX de carvao ativado; nao ha difratograma do material",
     "fonte": "literatura: DRX tipico de carbono ativado (sem difratograma)"},
    {"codigo": "S3", "rota": "banco:S3", "nivel": 1, "base": "BET medido"},
    {"codigo": "S4", "rota": "banco:S4", "nivel": 1,
     "base": "volume de poros medido"},
    {"codigo": "S5", "rota": "direto", "nivel": 3, "valor": 45.0,
     "unidade": "um", "estado": "estimado",
     "base": "po moido e peneirado; d50 da faixa < 75 um",
     "fonte": "granulometria declarada do processo de moagem"},
    {"codigo": "S6", "rota": "motor:boehm_grupos/acidos_totais_mmol_g",
     "nivel": 3, "base": "titulacao de Boehm declarada",
     "fonte": "boehm_grupos sobre consumos declarados"},
    {"codigo": "S7", "rota": "motor:granulometria_psd/d50_um", "nivel": 3,
     "base": "d50 da distribuicao declarada",
     "fonte": "granulometria_psd sobre diametros declarados"},
    {"codigo": "P1", "rota": "regra:P1", "nivel": 2,
     "base": ("rho_ap = 1/(V_p + 1/rho_verdadeira) com V_p medido (S4) e "
              "rho_verdadeira = 1,90 g/cm3 declarada"),
     "fonte": "derivado de S4 (medido) + densidade do esqueleto declarada"},
    {"codigo": "P2", "rota": "motor:pzc_deriva_ph/pzc", "nivel": 3,
     "base": "deriva de pH declarada",
     "fonte": "pzc_deriva_ph sobre serie de pH declarada"},
    {"codigo": "P3", "rota": "regra:P3", "nivel": 3,
     "base": "titulacao de CTC declarada",
     "fonte": "regra CTC sobre volumes declarados"},
    {"codigo": "P4", "rota": "motor:angulo_contato/energia_superficial_mN_m",
     "nivel": 3, "unidade": "mN/m",
     "base": "energia superficial por Owens-Wendt com angulos declarados",
     "fonte": "angulo_contato (agua 95 graus, diiodometano 60 graus)"},
    {"codigo": "P5", "rota": "motor:tga_tangente/onset_C", "nivel": 3,
     "base": "onset da tangente na curva TGA declarada",
     "fonte": "tga_tangente sobre curva declarada (10 C/min)"},
    {"codigo": "P6", "rota": "na", "nivel": 4, "estado": "nao_aplicavel",
     "base": ("adsorcao no escuro sem fotocatalise/eletroassistencia: banda "
              "proibida nao governa o processo; o valor 2,0 eV que estava na "
              "matriz era o padrao interno do sim_dft, nao propriedade do "
              "material"),
     "fonte": "nao aplicavel ao uso em estudo (ver PLANO §2.4)"},
    {"codigo": "P7", "rota": "motor:lixiviacao_cinetica/lixiviacao_pct",
     "nivel": 3, "base": "lixiviacao acumulada declarada",
     "fonte": "lixiviacao_cinetica sobre serie declarada"},
    {"codigo": "D1", "rota": "banco:D1", "nivel": 1, "base": "qmax medido"},
    {"codigo": "D2", "rota": "regra:D2", "nivel": 3, "estado": "estimado",
     "base": ("KL de Langmuir sobre isoterma de cenario coerente com o qmax "
              "medido (KL = 0,05 L/mg declarado) - nao e' ajuste de dado"),
     "fonte": "regra de Langmuir sobre isoterma de cenario"},
    {"codigo": "D3", "rota": "regra:D3", "nivel": 3, "estado": "estimado",
     "base": ("k2 do PSO sobre cinetica de cenario coerente com o qmax medido "
              "(k2 = 1,9e-3 g/mg/min declarado) - nao e' ajuste de dado"),
     "fonte": "regra PSO sobre cinetica de cenario"},
    {"codigo": "D4", "rota": "motor:seletividade_competitiva/seletividade_alfa",
     "nivel": 3, "base": "alfa de Langmuir entre SMX e ibuprofeno declarados",
     "fonte": "seletividade_competitiva sobre qmax/KL declarados"},
    {"codigo": "D5",
     "rota": "motor:regeneracao_reuso/ciclos_ate_80pct_capacidade",
     "nivel": 3, "base": "ciclos ate 80% da capacidade inicial",
     "fonte": "regeneracao_reuso sobre capacidades declaradas"},
    {"codigo": "D6", "rota": "regra:D6", "nivel": 3,
     "base": "R = (C0-Ce)/C0 com C0 = 20 mg/L e Ce = 0,0072 mg/L declarados",
     "fonte": "regra de remocao sobre C0/Ce do lote declarado"},
    {"codigo": "D7", "rota": "direto", "nivel": 3,
     "valor_texto": ("pH 5,0-8,0 (SMX anionico a partir de pKa2 5,7; superficie "
                     "basica com PZC ~ 7,4) e 20-40 C"),
     "unidade": "texto", "estado": "estimado",
     "base": "janela operacional derivada de pKa do SMX e do PZC",
     "fonte": "janela derivada de pKa (SMX) e PZC (carvao)"},
    {"codigo": "C1", "rota": "motor:perigo_composicao/indice_perigo",
     "nivel": 3, "cobertura_minima": 0.5,
     "fallback": {"valor_texto": ("carvao ativado nao e' classificado como "
                                  "perigoso pelo GHS na forma solida; po "
                                  "respiravel/combustivel no manuseio"),
                  "estado": "estimado",
                  "fonte": ("classificacao GHS textual (indice numerico "
                            "descartado: cobertura baixa da composicao "
                            "declarada)")},
     "base": "indice GHS ponderado pela composicao declarada",
     "fonte": "perigo_composicao sobre composicao declarada"},
    {"codigo": "C2", "rota": "regra:C2", "nivel": 3,
     "base": "custo = preco declarado (R$ 12/kg) / qmax medido",
     "fonte": "regra de custo com preco declarado"},
    {"codigo": "C3", "rota": "na", "nivel": 0, "estado": "ausente",
     "faltando": ["oferta_anual_t_ano", "distancia_km"],
     "base": ("exige dado documental do fornecedor de lignina Kraft ou "
              "levantamento de oferta regional; nao ha numero defensavel"),
     "fonte": "pendente: dado documental (nao estimar)"},
    {"codigo": "C4", "rota": "regra:C4", "nivel": 3,
     "base": "E = P*t/m com 2 kW, 2 h, 1 kg declarados",
     "fonte": "regra energetica com potencia declarada"},
    {"codigo": "C5", "rota": "motor:reciclabilidade/indice_reciclabilidade",
     "nivel": 3, "base": "fator de fim de vida do carvao ativado (0,40)",
     "fonte": "reciclabilidade sobre classe 'carvao ativado'"},
    {"codigo": "C6",
     "rota": "motor:conformidade_limites/margem_conformidade_pct",
     "nivel": 3,
     "complemento": {"norma": "limite declarado 0,05 mg/L",
                     "aviso": ("MS 888/2021 nao fixa limite para "
                               "sulfametoxazol; a margem e' contra limite de "
                               "referencia declarado")},
     "base": "margem contra limite de referencia declarado",
     "fonte": "conformidade_limites (limite declarado, nao normativo)"},
    {"codigo": "C7", "rota": "regra:C7", "nivel": 3,
     "base": "TRH = V/Q com leito de 2 L e vazao de 10 L/h declarados",
     "fonte": "regra de TRH com volume e vazao declarados"},
]

CELULAS_POR_CODIGO = {item["codigo"]: item for item in CELULAS}


def celulas() -> list:
    """Copia das 28 celulas (para consumir sem alterar o modulo)."""
    return [dict(item) for item in CELULAS]


# ---------------------------------------------------------------------------
# Caracterizacao dos componentes (alimenta o cruzamento 7D x 4 pelo caminho
# oficial: `componentes.registrar`).  Nao preenche descritor automatico -
# quem grava descritor aqui e' `preencher_matriz.py`, para nao duplicar valor
# com lastro diferente.
# ---------------------------------------------------------------------------
FONTE_SMX = ("literatura do sulfametoxazol (C10H11N3O3S, M = 253,28 g/mol; "
             "pKa1 1,6 e pKa2 5,7; log Kow 0,89)")


def dados_componentes(rotulo: str, valores: dict) -> dict:
    """Itens de `componentes.registrar` por componente, para o material."""
    base = derivados(rotulo)
    celulas = valores or {}

    def _valor(codigo):
        linha = celulas.get(codigo) or {}
        return linha.get("valor")

    adsorvente = [
        {"chave": "composicao", "valor_texto": (
            "carvao ativado de lignina Kraft (black liquor) ativado "
            "quimicamente com KOH na razao %s (m/m)" % rotulo),
         "origem": "informado", "estado": "presente",
         "referencia": FONTE_ANCORA},
        {"chave": "densidade", "valor": round(base["rho_aparente"], 4),
         "origem": "calculado", "estado": "calculado",
         "metodo": "rho_ap = 1/(V_p + 1/rho_verdadeira), rho_verdadeira = "
                   "1,90 g/cm3",
         "referencia": "derivado de S4 (Brazil et al., 2026)"},
        {"chave": "porosidade", "valor": round(base["porosidade"], 4),
         "origem": "calculado", "estado": "calculado",
         "metodo": "epsilon = V_p / (V_p + 1/rho_verdadeira)"},
        {"chave": "area_superficial", "valor": base["area"],
         "origem": "medido", "estado": "presente", "metodo": "BET (N2)",
         "referencia": FONTE_ANCORA},
        {"chave": "volume_poros", "valor": base["volume"],
         "origem": "medido", "estado": "presente",
         "metodo": "volume total de poros", "referencia": FONTE_ANCORA},
        {"chave": "diametro_poro", "valor": round(base["diametro_poro_nm"], 3),
         "origem": "calculado", "estado": "calculado",
         "metodo": "d_p = 4V_p/A_BET (modelo cilindrico)"},
    ]
    if _valor("P2") is not None:
        adsorvente.append({"chave": "pzc", "valor": _valor("P2"),
                           "origem": "calculado", "estado": "calculado",
                           "metodo": "deriva de pH (pzc_deriva_ph)"})
    if _valor("S6") is not None:
        adsorvente.append({"chave": "densidade_sitios", "valor": _valor("S6"),
                           "origem": "informado", "estado": "estimado",
                           "metodo": "titulacao de Boehm declarada"})
    adsorvente.append({"chave": "grupos_funcionais", "valor_texto": (
        "acidos carboxilicos, fenolicos e lactonas (Boehm) + sitios "
        "basicos; superficie basica (PZC > 7)"),
        "origem": "informado", "estado": "estimado"})

    adsorbato = [
        {"chave": "formula_molecular", "valor_texto": "C10H11N3O3S",
         "origem": "importado", "estado": "presente",
         "referencia": FONTE_SMX},
        {"chave": "massa_molar", "valor": 253.28, "origem": "importado",
         "estado": "presente", "referencia": FONTE_SMX},
        {"chave": "pka", "valor": 5.7, "valor_texto": "pKa1 1,6; pKa2 5,7",
         "origem": "importado", "estado": "presente",
         "referencia": FONTE_SMX},
        {"chave": "log_kow", "valor": 0.89, "origem": "importado",
         "estado": "presente", "referencia": FONTE_SMX},
        {"chave": "carga_ionica", "valor": -0.39,
         "valor_texto": "fracao anionica ~39% em pH 5,5 (entre pKa1 e pKa2)",
         "origem": "calculado", "estado": "calculado",
         "metodo": "fracao ionizada por Henderson-Hasselbalch"},
        {"chave": "raio_ionico", "valor": 0.45,
         "valor_texto": "raio efetivo ~0,45 nm (molecula ~0,9 nm)",
         "origem": "importado", "estado": "estimado"},
        {"chave": "concentracao_trabalho", "valor": C0_MG_L,
         "origem": "informado", "estado": "presente"},
    ]

    meio = [
        {"chave": "ph", "valor": 5.5, "origem": "informado",
         "estado": "presente"},
        {"chave": "temperatura", "valor": 25.0, "origem": "informado",
         "estado": "presente"},
        {"chave": "volume", "valor": 50.0, "origem": "informado",
         "estado": "presente"},
        {"chave": "massa_adsorvente", "valor": 0.01, "origem": "informado",
         "estado": "presente"},
        {"chave": "tempo_contato", "valor": 120.0, "origem": "informado",
         "estado": "presente"},
        {"chave": "agitacao", "valor": 150.0, "origem": "informado",
         "estado": "presente"},
        {"chave": "concentracao_inicial", "valor": C0_MG_L,
         "origem": "informado", "estado": "presente"},
        {"chave": "concentracao_equilibrio", "valor": CE_MG_L,
         "origem": "medido", "estado": "presente"},
        {"chave": "forca_ionica", "valor": 0.01, "origem": "informado",
         "estado": "presente"},
        {"chave": "solvente", "valor_texto": "agua ultrapura (Milli-Q)",
         "origem": "informado", "estado": "presente"},
    ]
    return {"adsorvente": adsorvente, "adsorbato": adsorbato, "meio": meio}

