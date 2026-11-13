# -*- coding: utf-8 -*-
"""Matriz metodologica 7D x 4 do ALEF-TAV Ambiental.

28 descritores = 4 dimensoes x 7 descritores. Cada descritor traz definicao,
unidade, regra matematica e sinonimos usados na selecao dinamica. A matriz e'
declarativa: o que nao pode ser calculado a partir dos dados recebidos fica
como `parametro_ausente`, nunca como zero ou como estimativa silenciosa.

Dimensoes
    D1 ESTRUTURA   (S1..S7)  o que o material e'
    D2 PROPRIEDADES(P1..P7)  como o material se comporta
    D3 DESEMPENHO  (D1..D7)  quanto ele entrega na aplicacao
    D4 CONTEXTO    (C1..C7)  se vale a pena usa-lo
"""
from __future__ import annotations

import math
import re
import unicodedata

DIMENSOES = [
    {"codigo": "D1", "nome": "Estrutura", "prefixo": "S",
     "pergunta_guia": "O que o material e' e de que ele e' feito?"},
    {"codigo": "D2", "nome": "Propriedades", "prefixo": "P",
     "pergunta_guia": "Como o material se comporta fisica e quimicamente?"},
    {"codigo": "D3", "nome": "Desempenho", "prefixo": "D",
     "pergunta_guia": "Quanto o material entrega na aplicacao ambiental?"},
    {"codigo": "D4", "nome": "Contexto", "prefixo": "C",
     "pergunta_guia": "Vale a pena usar esse material nesse contexto?"},
]

_ESTRUTURA = [
    {
        "codigo": "S1", "nome": "Composicao elementar e pureza",
        "definicao": ("Fracao massica dos elementos/fases declarados e teor de "
                      "impurezas do material."),
        "unidade": "fracao m/m (0-1) e % m/m",
        "tipo": "numerico", "essencial": True,
        "regra": ("Soma das fracoes declaradas = 1 +- 0,02; pureza = "
                  "100 - soma das impurezas (% m/m)."),
        "sinonimos": ["composicao", "composition", "pureza", "elementar",
                      "formula", "fases", "teor"],
        "aplicacoes": ["agua", "efluente", "solo", "ar", "residuo"],
    },
    {
        "codigo": "S2", "nome": "Fase cristalina / estrutura",
        "definicao": ("Fases identificadas por difracao (XRD/DRX) e grau de "
                      "cristalinidade relativo."),
        "unidade": "fases (texto) e % de cristalinidade",
        "tipo": "categorico", "essencial": False,
        "regra": ("Cristalinidade = A_cristalina / (A_cristalina + A_amorfa) x "
                  "100, integrando as areas dos picos e do halo."),
        "sinonimos": ["xrd", "drx", "cristal", "fase", "difracao",
                      "cristalinidade", "amorfo"],
        "aplicacoes": ["agua", "efluente", "solo", "residuo"],
    },
    {
        "codigo": "S3", "nome": "Area superficial especifica (BET)",
        "definicao": ("Area acessivel por unidade de massa obtida pelo metodo "
                      "BET a partir da isoterma de N2."),
        "unidade": "m2/g",
        "tipo": "numerico", "essencial": True,
        "regra": ("A_BET = (V_m x N_A x sigma) / m, com sigma(N2) = 0,162 nm2; "
                  "V_m vem do coeficiente linear de P/[V(P0-P)] vs P/P0."),
        "sinonimos": ["bet", "area superficial", "surface area", "porosidade",
                      "mesoporo", "microporo"],
        "aplicacoes": ["agua", "efluente", "ar", "solo"],
    },
    {
        "codigo": "S4", "nome": "Volume e distribuicao de poros",
        "definicao": ("Volume total de poros e fracao micro/meso/macro, com "
                      "diametro medio de poro."),
        "unidade": "cm3/g e nm",
        "tipo": "numerico", "essencial": False,
        "regra": ("V_p = 1/rho_aparente - 1/rho_verdadeira (cm3/g); "
                  "epsilon = V_p / (V_p + 1/rho_verdadeira)."),
        "sinonimos": ["volume de poros", "pore volume", "diametro de poro",
                      "microporo", "mesoporo", "macroporo"],
        "aplicacoes": ["agua", "efluente", "ar"],
    },
    {
        "codigo": "S5", "nome": "Tamanho de particula",
        "definicao": ("Distribuicao granulometrica (D10/D50/D90) e diametro "
                      "medio de Sauter."),
        "unidade": "um ou nm",
        "tipo": "numerico", "essencial": False,
        "regra": ("d32 = 6 / (rho x A_BET); D50 lido da curva acumulada de "
                  "difracao a laser em 50% do volume."),
        "sinonimos": ["tamanho de particula", "granulometria", "d50", "d10",
                      "particula", "moagem", "peneira"],
        "aplicacoes": ["agua", "efluente", "solo", "ar"],
    },
    {
        "codigo": "S6", "nome": "Grupos funcionais de superficie",
        "definicao": ("Natureza e densidade dos grupos superficiais "
                      "(carboxila, hidroxila, amina, tiol)."),
        "unidade": "mmol/g e classe quimica",
        "tipo": "categorico", "essencial": False,
        "regra": ("Densidade acida = (V_branco - V_amostra) x C_NaOH / m; "
                  "densidade basica pelo mesmo balanco com HCl (metodo Boehm)."),
        "sinonimos": ["grupo funcional", "ftir", "carboxila", "hidroxila",
                      "amina", "funcionalizacao", "superficie quimica"],
        "aplicacoes": ["agua", "efluente", "ar"],
    },
    {
        "codigo": "S7", "nome": "Morfologia e agregacao",
        "definicao": ("Forma das particulas/aglomerados observada por MEV/TEM "
                      "e tendencia a agregacao."),
        "unidade": "descritivo (texto) + tamanho de aglomerado (um)",
        "tipo": "categorico", "essencial": False,
        "regra": ("Indice de agregacao = d_aglomerado / d_primario; "
                  "> 1 indica agregacao."),
        "sinonimos": ["mev", "sem", "tem", "morfologia", "aglomerado",
                      "esferico", "lamelar", "fibra"],
        "aplicacoes": ["agua", "efluente", "solo"],
    },
]

_PROPRIEDADES = [
    {
        "codigo": "P1", "nome": "Densidade real e aparente",
        "definicao": ("Massa especifica do solido (picnometria) e densidade do "
                      "leito empacotado."),
        "unidade": "g/cm3",
        "tipo": "numerico", "essencial": True,
        "regra": "rho = m / V; rho_aparente = m_leito / V_leito.",
        "sinonimos": ["densidade", "density", "massa especifica",
                      "densidade aparente", "picnometro"],
        "aplicacoes": ["agua", "efluente", "solo", "ar", "residuo"],
    },
    {
        "codigo": "P2", "nome": "Ponto de carga zero (PZC)",
        "definicao": ("pH em que a carga liquida da superficie e' nula; define "
                      "a faixa de atraccao de cations/anions."),
        "unidade": "pH (adimensional)",
        "tipo": "numerico", "essencial": True,
        "regra": ("PZC = pH_final em que delta_pH = pH_final - pH_inicial = 0 "
                  "(metodo de drift); carga efetiva ~ (PZC - pH)."),
        "sinonimos": ["pzc", "ponto de carga zero", "carga zero",
                      "potencial zeta", "carga superficial"],
        "aplicacoes": ["agua", "efluente", "solo"],
    },
    {
        "codigo": "P3", "nome": "Capacidade de troca ionica (CTC)",
        "definicao": ("Quantidade de cargas trocaveis por unidade de massa do "
                      "material."),
        "unidade": "cmol/kg (meq/100 g)",
        "tipo": "numerico", "essencial": False,
        "regra": ("CTC = (V_branco - V_amostra) x C x f x 100 / m, f = fator do "
                  "extrator; conversao 1 cmol/kg = 1 meq/100 g."),
        "sinonimos": ["ctc", "cec", "troca ionica", "cation exchange",
                      "capacidade de troca"],
        "aplicacoes": ["solo", "agua", "efluente"],
    },
    {
        "codigo": "P4", "nome": "Hidrofobicidade / molhabilidade",
        "definicao": ("Afinidade da superficie pela agua, medida por angulo de "
                      "contato ou particao octanol-agua."),
        "unidade": "graus (angulo) ou log Kow",
        "tipo": "numerico", "essencial": False,
        "regra": ("cos(theta) de Young-Dupre; theta < 90 graus = hidrofilico, "
                  "theta > 90 graus = hidrofobico."),
        "sinonimos": ["angulo de contato", "hidrofobicidade", "hidrofilico",
                      "molhabilidade", "kow", "logp"],
        "aplicacoes": ["agua", "efluente", "solo"],
    },
    {
        "codigo": "P5", "nome": "Estabilidade termica",
        "definicao": ("Temperatura de inicio de decomposicao e perda de massa "
                      "sob aquecimento."),
        "unidade": "graus C e % de perda",
        "tipo": "numerico", "essencial": False,
        "regra": ("T_5% = temperatura em que a perda acumulada de massa atinge "
                  "5% na curva TGA; rampa declarada obrigatoria."),
        "sinonimos": ["tga", "estabilidade termica", "decomposicao",
                      "termogravimetria", "temperatura"],
        "aplicacoes": ["agua", "efluente", "ar", "residuo"],
    },
    {
        "codigo": "P6", "nome": "Condutividade / banda proibida",
        "definicao": ("Condutividade eletrica do material ou gap optico quando "
                      "o uso for fotocatalise/adsorcao eletroassistida."),
        "unidade": "S/m ou eV",
        "tipo": "numerico", "essencial": False,
        "regra": ("sigma = 1/rho_eletrica; Eg por Tauc: (alpha h nu)^2 vs h nu "
                  "com extrapolacao linear."),
        "sinonimos": ["condutividade", "banda proibida", "band gap", "eg",
                      "fotocatalise", "semiconductor"],
        "aplicacoes": ["agua", "efluente", "ar"],
    },
    {
        "codigo": "P7", "nome": "Solubilidade e lixiviacao",
        "definicao": ("Fracao do material que solubiliza ou lixivia nas "
                      "condicoes de uso, comparada ao limite normativo."),
        "unidade": "mg/L e % m/m",
        "tipo": "numerico", "essencial": True,
        "regra": ("S = m_dissolvido / V_ensaio; lixiviacao = m_lixiviado / "
                  "m_total x 100; comparar com o limite do ensaio aplicavel."),
        "sinonimos": ["lixiviacao", "solubilidade", "tclp", "diluicao",
                      "liberacao", "perda de massa"],
        "aplicacoes": ["agua", "solo", "residuo"],
    },
]

_DESEMPENHO = [
    {
        "codigo": "D1", "nome": "Capacidade maxima de adsorcao (qmax)",
        "definicao": ("Massa de contaminante retida por massa de material no "
                      "patamar da isoterma."),
        "unidade": "mg/g",
        "tipo": "numerico", "essencial": True,
        "regra": ("Langmuir linearizado Ce/qe = 1/(qmax*KL) + Ce/qmax: "
                  "qmax = 1/coeficiente angular; qe medido = (C0-Ce)*V/m."),
        "sinonimos": ["qmax", "capacidade de adsorcao", "adsorption capacity",
                      "isoterma", "langmuir", "mg/g"],
        "aplicacoes": ["agua", "efluente", "solo", "ar"],
    },
    {
        "codigo": "D2", "nome": "Afinidade (KL, Kf) e fator de separacao",
        "definicao": ("Constante de afinidade do modelo de isoterma e fator de "
                      "separacao adimensional RL."),
        "unidade": "L/mg e adimensional",
        "tipo": "numerico", "essencial": True,
        "regra": ("KL = angular/intercepto do ajuste de Langmuir; "
                  "RL = 1/(1+KL*C0): 0<RL<1 favoravel."),
        "sinonimos": ["kl", "kf", "afinidade", "freundlich", "fator de separacao",
                      "rl"],
        "aplicacoes": ["agua", "efluente", "solo"],
    },
    {
        "codigo": "D3", "nome": "Cinetica de adsorcao",
        "definicao": ("Velocidade de remocao ao longo do tempo e tempo para "
                      "atingir o equilibrio."),
        "unidade": "1/min e min",
        "tipo": "numerico", "essencial": True,
        "regra": ("PFO: ln(qe-qt) = ln qe - k1*t; PSO: t/qt = 1/(k2*qe^2) + "
                  "t/qe; t95 estimado a partir do modelo ajustado."),
        "sinonimos": ["cinetica", "pso", "pseudo-segunda", "pseudo-primeira",
                      "k1", "k2", "tempo de equilibrio"],
        "aplicacoes": ["agua", "efluente"],
    },
    {
        "codigo": "D4", "nome": "Seletividade entre contaminantes",
        "definicao": ("Preferencia do material por um contaminante na presenca "
                      "de outros."),
        "unidade": "adimensional",
        "tipo": "numerico", "essencial": False,
        "regra": ("alpha_ij = (q_i/C_i) / (q_j/C_j); alpha > 1 indica "
                  "preferencia por i."),
        "sinonimos": ["seletividade", "competicao", "multicomponente",
                      "alpha", "preferencia"],
        "aplicacoes": ["agua", "efluente", "solo"],
    },
    {
        "codigo": "D5", "nome": "Regeneracao e reuso",
        "definicao": ("Manutencao da capacidade apos ciclos de dessorcao e "
                      "numero de ciclos uteis."),
        "unidade": "% por ciclo e ciclos",
        "tipo": "numerico", "essencial": False,
        "regra": ("R_n = q_n / q_1 x 100; perda por ciclo = (q_1 - q_n)/(n-1)."),
        "sinonimos": ["regeneracao", "reuso", "ciclo", "dessorcao",
                      "reutilizacao"],
        "aplicacoes": ["agua", "efluente", "residuo"],
    },
    {
        "codigo": "D6", "nome": "Eficiencia de remocao",
        "definicao": ("Percentual de contaminante retirado do meio nas "
                      "condicoes declaradas."),
        "unidade": "% e mg/g",
        "tipo": "numerico", "essencial": True,
        "regra": ("R = (C0 - Ce)/C0 x 100; qe = (C0 - Ce)*V/m."),
        "sinonimos": ["remocao", "eficiencia", "percentual", "tratamento",
                      "reducao de concentracao"],
        "aplicacoes": ["agua", "efluente", "solo", "ar"],
    },
    {
        "codigo": "D7", "nome": "Faixa operacional de pH/temperatura",
        "definicao": ("Janela de pH e temperatura em que o desempenho se "
                      "mantem proximo do maximo."),
        "unidade": "pH e graus C",
        "tipo": "numerico", "essencial": False,
        "regra": ("Faixa com R(pH) >= 0,9 x R_max; largura = pH_sup - pH_inf."),
        "sinonimos": ["ph otimo", "faixa de ph", "temperatura", "janela",
                      "condicao operacional"],
        "aplicacoes": ["agua", "efluente", "solo"],
    },
]

_CONTEXTO = [
    {
        "codigo": "C1", "nome": "Toxicidade e seguranca",
        "definicao": ("Perigo do material e do residuo pos-uso para saude "
                      "humana e ecossistemas."),
        "unidade": "categoria (GHS) e mg/L (LC50/EC50)",
        "tipo": "categorico", "essencial": True,
        "regra": ("Classificacao GHS declarada; quando houver EC50, comparar "
                  "com o limite do corpo receptor."),
        "sinonimos": ["toxicidade", "tossicidade", "ecotoxicidade", "lc50",
                      "ec50", "ghs", "perigo", "seguranca"],
        "aplicacoes": ["agua", "efluente", "solo", "ar", "residuo"],
    },
    {
        "codigo": "C2", "nome": "Custo especifico",
        "definicao": ("Custo do material por massa e por massa de contaminante "
                      "removido."),
        "unidade": "R$/kg e R$/g removido",
        "tipo": "numerico", "essencial": True,
        "regra": ("Custo_especifico = preco_unitario / qmax; comparar apenas "
                  "quando as duas grandezas tiverem a mesma base."),
        "sinonimos": ["custo", "preco", "economico", "custo-beneficio",
                      "viabilidade economica"],
        "aplicacoes": ["agua", "efluente", "solo", "ar", "residuo"],
    },
    {
        "codigo": "C3", "nome": "Disponibilidade e origem do residuo",
        "definicao": ("Volume/oferta do material ou do residuo precursor e "
                      "distancia ate o ponto de uso."),
        "unidade": "t/ano e km",
        "tipo": "numerico", "essencial": False,
        "regra": ("Oferta util = oferta anual x fracao aproveitavel; indice de "
                  "circularidade = massa de residuo reusada / massa gerada."),
        "sinonimos": ["disponibilidade", "oferta", "residuo", "precursor",
                      "biomassa", "escala", "logistica"],
        "aplicacoes": ["residuo", "solo", "agua", "efluente"],
    },
    {
        "codigo": "C4", "nome": "Pegada energetica e emissoes",
        "definicao": ("Energia e emissao associadas a producao e uso do "
                      "material por massa tratada."),
        "unidade": "kWh/kg e kg CO2e/kg",
        "tipo": "numerico", "essencial": False,
        "regra": ("E_especifica = P * t / m; emissao = E_especifica x fator de "
                  "emissao da matriz eletrica declarada."),
        "sinonimos": ["energia", "pegada", "emissao", "co2", "carbon",
                      "consumo energetico", "sustentabilidade"],
        "aplicacoes": ["agua", "efluente", "ar", "residuo"],
    },
    {
        "codigo": "C5", "nome": "Reciclabilidade e fim de vida",
        "definicao": ("Destino do material saturado: regeneracao, "
                      "coprocessamento ou disposicao final."),
        "unidade": "ciclos uteis e % de massa reaproveitada",
        "tipo": "categorico", "essencial": False,
        "regra": ("Ciclos uteis = maior n com R_n >= 0,8 x R_1; massa "
                  "reaproveitada = m_reuso / m_total x 100."),
        "sinonimos": ["reciclagem", "fim de vida", "disposicao",
                      "reaproveitamento", "circularidade", "descarte"],
        "aplicacoes": ["residuo", "agua", "efluente"],
    },
    {
        "codigo": "C6", "nome": "Conformidade normativa",
        "definicao": ("Atendimento aos limites legais do meio tratado apos o "
                      "uso do material."),
        "unidade": "mg/L (limite) e status",
        "tipo": "categorico", "essencial": True,
        "regra": ("Atende se C_final <= C_limite da norma aplicavel; registrar "
                  "norma, versao e data de consulta."),
        "sinonimos": ["norma", "conama", "legislacao", "limite", "padrao",
                      "conformidade", "regulatorio"],
        "aplicacoes": ["agua", "efluente", "solo", "ar", "residuo"],
    },
    {
        "codigo": "C7", "nome": "Escalabilidade e operacao",
        "definicao": ("Adaptacao do desempenho de bancada para vazao real, com "
                      "tempo de residencia e perda de carga."),
        "unidade": "m3/h, min e kPa/m",
        "tipo": "numerico", "essencial": True,
        "regra": ("TRH = V_leito / Q; Q = m_tratada / t; comparar com a vazao "
                  "de projeto do sistema."),
        "sinonimos": ["escala", "escalonamento", "vazao", "trh", "leito",
                      "coluna", "operacao", "piloto"],
        "aplicacoes": ["agua", "efluente", "solo"],
    },
]

DESCRITORES = []
for _codigo_dim, _lista in (("D1", _ESTRUTURA), ("D2", _PROPRIEDADES),
                            ("D3", _DESEMPENHO), ("D4", _CONTEXTO)):
    _nome_dim = next(d["nome"] for d in DIMENSOES if d["codigo"] == _codigo_dim)
    for _indice, _item in enumerate(_lista, start=1):
        _registro = dict(_item)
        _registro["dimensao"] = _codigo_dim
        _registro["dimensao_nome"] = _nome_dim
        _registro["ordem"] = _indice
        DESCRITORES.append(_registro)

DESCRITORES_POR_CODIGO = {d["codigo"]: d for d in DESCRITORES}

ESTADOS_DADO = ("presente", "calculado", "estimado", "ausente", "nao_aplicavel",
                "validado")


def _sem_acento(texto) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def listar(incluir_regras: bool = True) -> dict:
    """Matriz completa: 4 dimensoes e 28 descritores."""
    descritores = []
    for descritor in DESCRITORES:
        item = {
            "codigo": descritor["codigo"],
            "dimensao": descritor["dimensao"],
            "dimensao_nome": descritor["dimensao_nome"],
            "nome": descritor["nome"],
            "definicao": descritor["definicao"],
            "unidade": descritor["unidade"],
            "tipo": descritor["tipo"],
            "essencial": descritor["essencial"],
        }
        if incluir_regras:
            item["regra"] = descritor["regra"]
            item["sinonimos"] = list(descritor["sinonimos"])
            item["aplicacoes"] = list(descritor["aplicacoes"])
        descritores.append(item)
    return {
        "total": len(descritores),
        "dimensoes": [dict(d) for d in DIMENSOES],
        "descritores": descritores,
        "estados_possiveis": list(ESTADOS_DADO),
    }


def obter(codigo: str):
    """Descritor pelo codigo (S1..S7, P1..P7, D1..D7, C1..C7)."""
    if not codigo:
        return None
    return DESCRITORES_POR_CODIGO.get(str(codigo).strip().upper())


def selecionar(pergunta: str, aplicacao: str = None, contaminante: str = None,
               material: str = None, limite: int = None,
               incluir_essenciais: bool = True) -> list:
    """Selecao dinamica dos descritores relevantes para a pergunta.

    Pontuacao: +3 por sinonimo encontrado na pergunta; +2 quando o descritor
    cobre a aplicacao ambiental; +1 quando cobre o contaminante citado por
    classe; +1 para descritores essenciais da dimensao. A matriz pode ser
    usada parcialmente: nada aqui exige preencher os 28.
    """
    texto = " ".join(_sem_acento(parte) for parte in
                     (pergunta, aplicacao, contaminante, material) if parte)
    escolhidos = []
    for descritor in DESCRITORES:
        motivos = []
        pontos = 0
        for sinonimo in descritor["sinonimos"]:
            termo = _sem_acento(sinonimo)
            if termo and re.search(r"\b%s" % re.escape(termo), texto):
                pontos += 3
                motivos.append("termo:%s" % sinonimo)
        if aplicacao and _sem_acento(aplicacao) in [
                _sem_acento(a) for a in descritor["aplicacoes"]]:
            pontos += 2
            motivos.append("aplicacao:%s" % aplicacao)
        if descritor["essencial"]:
            pontos += 1
            motivos.append("essencial")
        if pontos <= 1 and not incluir_essenciais:
            continue
        escolhidos.append({
            "codigo": descritor["codigo"],
            "dimensao": descritor["dimensao"],
            "nome": descritor["nome"],
            "unidade": descritor["unidade"],
            "tipo": descritor["tipo"],
            "regra": descritor["regra"],
            "essencial": descritor["essencial"],
            "pontuacao": pontos,
            "motivo": motivos,
            "estado": "ausente",
        })
    escolhidos.sort(key=lambda item: (-item["pontuacao"], item["codigo"]))
    if limite:
        escolhidos = escolhidos[:max(1, int(limite))]
    return escolhidos


# ---------------------------------------------------------------------------
# Regras de calculo
#
# Cada regra recebe um dicionario de dados brutos e devolve
# {"valor", "unidade", "memoria"}. Se faltar dado, levanta ParametroAusente
# com a lista do que falta: nunca devolve zero nem chute.
# ---------------------------------------------------------------------------
class ParametroAusente(ValueError):
    """Dados insuficientes para aplicar a regra matematica do descritor."""

    def __init__(self, faltando):
        self.faltando = list(faltando)
        super().__init__("faltando: %s" % ", ".join(self.faltando))


def _num(dados: dict, chave: str) -> float:
    valor = dados.get(chave)
    if valor is None or valor == "":
        raise ParametroAusente([chave])
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ParametroAusente([chave])
    if not math.isfinite(numero):
        raise ParametroAusente([chave])
    return numero


def _faltando(dados: dict, chaves) -> list:
    return [c for c in chaves
            if dados.get(c) is None or dados.get(c) == ""]


def _ajuste_linear(xs, ys):
    """Minimos quadrados y = a*x + b -> (a, b, r2)."""
    n = len(xs)
    if n < 2 or n != len(ys):
        raise ParametroAusente(["pelo_menos_dois_pontos"])
    media_x = sum(xs) / n
    media_y = sum(ys) / n
    sxx = sum((x - media_x) ** 2 for x in xs)
    if abs(sxx) < 1e-15:
        raise ParametroAusente(["variacao_em_x"])
    sxy = sum((x - media_x) * (y - media_y) for x, y in zip(xs, ys))
    a = sxy / sxx
    b = media_y - a * media_x
    syy = sum((y - media_y) ** 2 for y in ys)
    r2 = 0.0 if syy < 1e-15 else (sxy ** 2) / (sxx * syy)
    return a, b, r2


def _regra_s4(dados):
    rho_ap = _num(dados, "rho_aparente")
    rho_ver = _num(dados, "rho_verdadeira")
    if rho_ap <= 0 or rho_ver <= 0:
        raise ParametroAusente(["densidades_positivas"])
    volume_poros = 1.0 / rho_ap - 1.0 / rho_ver
    epsilon = volume_poros / (volume_poros + 1.0 / rho_ver)
    return {"valor": round(volume_poros, 6), "unidade": "cm3/g",
            "memoria": "V_p = 1/rho_ap - 1/rho_ver = %.6f; epsilon = %.4f"
                       % (volume_poros, epsilon),
            "complemento": {"porosidade": round(epsilon, 4)}}


def _regra_p1(dados):
    massa = _num(dados, "massa_g")
    volume = _num(dados, "volume_cm3")
    if volume <= 0:
        raise ParametroAusente(["volume_cm3_positivo"])
    return {"valor": round(massa / volume, 6), "unidade": "g/cm3",
            "memoria": "rho = m/V = %.4f/%.4f" % (massa, volume)}


def _regra_p3(dados):
    v_branco = _num(dados, "volume_branco_mL")
    v_amostra = _num(dados, "volume_amostra_mL")
    concentracao = _num(dados, "concentracao_mol_L")
    massa = _num(dados, "massa_g")
    fator = float(dados.get("fator_extrator") or 1.0)
    if massa <= 0:
        raise ParametroAusente(["massa_g_positiva"])
    ctc = (v_branco - v_amostra) * concentracao * fator * 100.0 / massa
    return {"valor": round(ctc, 4), "unidade": "cmol/kg",
            "memoria": ("CTC = (%.3f-%.3f) x %.4f x %.2f x 100 / %.4f"
                        % (v_branco, v_amostra, concentracao, fator, massa))}


def _regra_d6(dados):
    c0 = _num(dados, "C0")
    ce = _num(dados, "Ce")
    if c0 <= 0:
        raise ParametroAusente(["C0_positivo"])
    remocao = (c0 - ce) / c0 * 100.0
    saida = {"valor": round(remocao, 4), "unidade": "%",
             "memoria": "R = (C0-Ce)/C0 x 100 = (%.4f-%.4f)/%.4f x 100"
                        % (c0, ce, c0)}
    if dados.get("volume_L") is not None and dados.get("massa_g") is not None:
        volume = _num(dados, "volume_L")
        massa = _num(dados, "massa_g")
        if massa > 0:
            qe = (c0 - ce) * volume / massa
            saida["complemento"] = {"qe_mg_g": round(qe, 4)}
    return saida


def _regra_c2(dados):
    preco = _num(dados, "preco_kg")
    qmax = _num(dados, "qmax_mg_g")
    if qmax <= 0:
        raise ParametroAusente(["qmax_mg_g_positivo"])
    custo = preco / qmax
    return {"valor": round(custo, 6), "unidade": "R$/g removido",
            "memoria": "custo = preco/qmax = %.4f/%.4f (1 g = 1000 mg)"
                       % (preco, qmax)}


def _regra_c4(dados):
    potencia = _num(dados, "potencia_kW")
    tempo = _num(dados, "tempo_h")
    massa = _num(dados, "massa_kg")
    if massa <= 0:
        raise ParametroAusente(["massa_kg_positiva"])
    energia = potencia * tempo / massa
    return {"valor": round(energia, 6), "unidade": "kWh/kg",
            "memoria": "E = P*t/m = %.4f x %.4f / %.4f"
                       % (potencia, tempo, massa)}


def _regra_c7(dados):
    volume = _num(dados, "volume_leito_m3")
    vazao = _num(dados, "vazao_m3_h")
    if vazao <= 0:
        raise ParametroAusente(["vazao_m3_h_positiva"])
    trh_h = volume / vazao
    return {"valor": round(trh_h * 60.0, 4), "unidade": "min",
            "memoria": "TRH = V/Q = %.6f/%.6f h -> min" % (volume, vazao)}


def _pontos_isoterma(dados: dict):
    """Pares (Ce, qe) a partir de `pontos` ou de C0/Ce com V e m."""
    pontos = dados.get("pontos")
    if isinstance(pontos, list) and len(pontos) >= 2:
        pares = []
        for ponto in pontos:
            if not isinstance(ponto, dict):
                raise ParametroAusente(["pontos_com_Ce_e_qe"])
            pares.append((_num(ponto, "Ce"), _num(ponto, "qe")))
        return pares
    c0_lista = dados.get("C0_lista")
    ce_lista = dados.get("Ce_lista")
    volume = dados.get("volume_L")
    massa = dados.get("massa_g")
    if isinstance(c0_lista, list) and isinstance(ce_lista, list):
        if len(c0_lista) != len(ce_lista) or len(c0_lista) < 2:
            raise ParametroAusente(["listas_de_mesmo_tamanho"])
        if volume is None or massa is None:
            raise ParametroAusente(["volume_L", "massa_g"])
        volume = float(volume)
        massa = float(massa)
        if massa <= 0:
            raise ParametroAusente(["massa_g_positiva"])
        return [(float(ce), (float(c0) - float(ce)) * volume / massa)
                for c0, ce in zip(c0_lista, ce_lista)]
    raise ParametroAusente(["pontos", "C0_lista/Ce_lista+volume_L+massa_g"])


def _regra_d1(dados):
    pares = [(ce, qe) for ce, qe in _pontos_isoterma(dados)
             if ce > 0 and qe > 0]
    if len(pares) < 2:
        raise ParametroAusente(["dois_pontos_com_Ce_e_qe_positivos"])
    xs = [ce for ce, _ in pares]
    ys = [ce / qe for ce, qe in pares]
    a, b, r2 = _ajuste_linear(xs, ys)
    if a <= 0:
        raise ParametroAusente(["ajuste_com_angular_positiva"])
    qmax = 1.0 / a
    saida = {"valor": round(qmax, 4), "unidade": "mg/g",
             "memoria": ("Langmuir Ce/qe = 1/(qmax*KL) + Ce/qmax; "
                         "a=%.6f b=%.6f r2=%.4f" % (a, b, r2)),
             "complemento": {"r2": round(r2, 4), "pontos": len(pares)}}
    if b:
        saida["complemento"]["KL_L_mg"] = round(a / b, 6)
    return saida


def _regra_d2(dados):
    pares = [(ce, qe) for ce, qe in _pontos_isoterma(dados)
             if ce > 0 and qe > 0]
    if len(pares) < 2:
        raise ParametroAusente(["dois_pontos_com_Ce_e_qe_positivos"])
    xs = [ce for ce, _ in pares]
    ys = [ce / qe for ce, qe in pares]
    a, b, _ = _ajuste_linear(xs, ys)
    if not b:
        raise ParametroAusente(["intercepto_nao_nulo"])
    kl = a / b
    if kl <= 0:
        raise ParametroAusente(["KL_positiva"])
    saida = {"valor": round(kl, 6), "unidade": "L/mg",
             "memoria": "KL = a/b do ajuste linearizado de Langmuir"}
    c0 = dados.get("C0")
    if c0 is not None:
        rl = 1.0 / (1.0 + kl * float(c0))
        saida["complemento"] = {"RL": round(rl, 6),
                                "favoravel": bool(0 < rl < 1)}
    return saida


def _regra_d3(dados):
    pontos = dados.get("pontos_cinetica")
    if not isinstance(pontos, list) or len(pontos) < 3:
        raise ParametroAusente(["pontos_cinetica_com_t_e_qt"])
    xs, ys = [], []
    for ponto in pontos:
        if not isinstance(ponto, dict):
            raise ParametroAusente(["pontos_cinetica_com_t_e_qt"])
        t = _num(ponto, "t")
        qt = _num(ponto, "qt")
        if t > 0 and qt > 0:
            xs.append(t)
            ys.append(t / qt)
    if len(xs) < 3:
        raise ParametroAusente(["tres_pontos_positivos"])
    a, b, r2 = _ajuste_linear(xs, ys)
    if a <= 0 or b <= 0:
        raise ParametroAusente(["ajuste_PSO_valido"])
    qe = 1.0 / a
    k2 = a ** 2 / b
    complemento = {"r2": round(r2, 4), "qe_mg_g": round(qe, 4)}
    if k2 > 0:
        complemento["t95_min"] = round(19.0 / (k2 * qe), 3)
    return {"valor": round(k2, 6), "unidade": "g/(mg*min)",
            "memoria": ("PSO t/qt = 1/(k2*qe^2) + t/qe; a=%.6f b=%.6f"
                        % (a, b)),
            "complemento": complemento}


REGRAS = {
    "S4": _regra_s4,
    "P1": _regra_p1,
    "P3": _regra_p3,
    "D1": _regra_d1,
    "D2": _regra_d2,
    "D3": _regra_d3,
    "D6": _regra_d6,
    "C2": _regra_c2,
    "C4": _regra_c4,
    "C7": _regra_c7,
}


def aplicar(codigo: str, dados: dict) -> dict:
    """Aplica a regra do descritor. Nunca inventa valor.

    Retorna `estado="calculado"` apenas quando a conta fecha com os dados
    recebidos; caso contrario `estado="ausente"` com a lista do que falta.
    """
    descritor = obter(codigo)
    if descritor is None:
        raise KeyError("descritor desconhecido: %s" % codigo)
    regra = REGRAS.get(descritor["codigo"])
    if regra is None:
        return {"codigo": descritor["codigo"], "estado": "manual",
                "regra": descritor["regra"],
                "motivo": "sem dados suficientes para automatizar"}
    try:
        resultado = regra(dict(dados or {}))
    except ParametroAusente as erro:
        return {"codigo": descritor["codigo"], "estado": "ausente",
                "regra": descritor["regra"], "faltando": erro.faltando}
    resultado["codigo"] = descritor["codigo"]
    resultado["estado"] = "calculado"
    resultado["regra"] = descritor["regra"]
    return resultado


def avaliar_preenchimento(itens) -> dict:
    """Cobertura da matriz: por dimensao e por estado do dado."""
    preenchidos = {"presente", "calculado", "estimado", "validado"}
    contagem = {estado: 0 for estado in ESTADOS_DADO}
    por_dimensao = {d["codigo"]: {"preenchidos": 0, "total": 0,
                                  "percentual": 0.0} for d in DIMENSOES}
    total = 0
    for item in itens or []:
        descritor = obter(item.get("codigo"))
        if descritor is None:
            continue
        total += 1
        estado = (item.get("estado") or "ausente").strip().lower()
        if estado not in contagem:
            estado = "ausente"
        contagem[estado] += 1
        dimensao = por_dimensao[descritor["dimensao"]]
        dimensao["total"] += 1
        if estado in preenchidos:
            dimensao["preenchidos"] += 1
    for dimensao in por_dimensao.values():
        if dimensao["total"]:
            dimensao["percentual"] = round(
                100.0 * dimensao["preenchidos"] / dimensao["total"], 2)
    com_dado = sum(contagem[e] for e in preenchidos)
    return {
        "total_avaliado": total,
        "com_dado": com_dado,
        "sem_dado": total - com_dado,
        "percentual_com_dado": (round(100.0 * com_dado / total, 2)
                                if total else 0.0),
        "por_estado": contagem,
        "por_dimensao": por_dimensao,
    }
