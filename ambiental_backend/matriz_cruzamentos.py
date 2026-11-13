# -*- coding: utf-8 -*-
"""Cruzamentos 7D x 4 da matriz ambiental.

Sete dimensoes informacionais (E, P, D, S, I, C, O) cruzadas com os quatro
componentes do sistema de adsorcao (adsorbato, adsorvente, interface, meio):
28 cruzamentos. Cada cruzamento recebe **todos** os descritores que o
informam, e nao um valor fixo por celula.

Regras que este modulo respeita, sem excecao:

* nao cria descritor: os elementos vem de `matriz_7d4.DESCRITORES` (28) e do
  catalogo de parametros de caracterizacao dos componentes (`PARAMETROS`);
* nao inventa valor nem preenche celula vazia com zero: descritor sem dado
  aparece como `ausente`, com peso 0 e listado em `lacunas`;
* nao usa peso universal por dimensao/componente (nada de 40/20/20/20): o peso
  sai dos criterios que ja existem no projeto (`selecionar`, `ESTADOS_DADO`,
  entropia das respostas, redundancia entre descritores);
* mantem rastreabilidade: cada peso traz os fatores que o produziram.

O modulo e' uma camada de leitura: nao altera `matriz_7d4`, `motor_pesquisa`
nem `persistencia`.
"""
from __future__ import annotations

import math

from . import matriz_7d4

# ---------------------------------------------------------------------------
# Eixos
# ---------------------------------------------------------------------------
DIMENSOES = [
    {"letra": "E", "nome": "Energetica",
     "pergunta": "Quanta energia o sistema exige, dissipa ou libera?"},
    {"letra": "P", "nome": "Eletronica",
     "pergunta": "Como os eletrons se distribuem nos componentes?"},
    {"letra": "D", "nome": "Estrutural",
     "pergunta": "O que o material e' e como esta organizado?"},
    {"letra": "S", "nome": "Superficial",
     "pergunta": "Qual a quimica da superficie em contato com o fluido?"},
    {"letra": "I", "nome": "Interacional",
     "pergunta": "Quanto e como adsorbato e adsorvente interagem?"},
    {"letra": "C", "nome": "Ambiental",
     "pergunta": "Que risco, residuo e emissao o sistema carrega?"},
    {"letra": "O", "nome": "Operacional",
     "pergunta": "O sistema funciona e se paga na escala real?"},
]

COMPONENTES = [
    {"chave": "adsorbato", "nome": "Adsorbato",
     "papel": "especie quimica que deve ser retirada do meio"},
    {"chave": "adsorvente", "nome": "Adsorvente",
     "papel": "material solido que retem o adsorbato"},
    {"chave": "interface", "nome": "Interface adsorvente-adsorbato",
     "papel": "regiao onde a interacao acontece"},
    {"chave": "meio", "nome": "Meio",
     "papel": "matriz aquosa e condicoes de operacao"},
]

DIMENSOES_POR_LETRA = {item["letra"]: item for item in DIMENSOES}
COMPONENTES_POR_CHAVE = {item["chave"]: item for item in COMPONENTES}

# ---------------------------------------------------------------------------
# Relacao descritor 7Dx4 -> (dimensao informacional, componente)
#
# Um descritor pode informar mais de um cruzamento; a primeira relacao e' a
# principal (usada no resumo) e as demais sao secundarias. `papel` explica a
# relacao em portugues e aparece na interface e no relatorio.
# ---------------------------------------------------------------------------
RELACOES_DESCRITORES = {
    "S1": [("D", "adsorvente", "composicao define a estrutura do solido")],
    "S2": [("D", "adsorvente", "fases cristalinas organizam a estrutura")],
    "S3": [("D", "adsorvente", "area especifica e' estrutura acessivel"),
           ("I", "interface", "area limita os sitios de contato")],
    "S4": [("D", "adsorvente", "volume e diametro de poro sao estrutura"),
           ("I", "interface", "poro condiciona o acesso do adsorbato")],
    "S5": [("D", "adsorvente", "granulometria e' estrutura particulada"),
           ("O", "meio", "particula fina dificulta separacao no processo")],
    "S6": [("S", "adsorvente", "grupos funcionais definem a superficie"),
           ("I", "interface", "grupos funcionalizados criam sitios de ligacao")],
    "S7": [("D", "adsorvente", "morfologia e agregacao definem a estrutura")],
    "P1": [("D", "adsorvente", "massa especifica e' propriedade estrutural"),
           ("O", "meio", "densidade define volume de leito e perda de carga")],
    "P2": [("S", "adsorvente", "PZC define a carga liquida da superficie"),
           ("I", "interface", "carga superficial decide atracao ou repulsao")],
    "P3": [("S", "adsorvente", "CTC mede cargas trocaveis da superficie")],
    "P4": [("S", "adsorvente", "molhabilidade descreve a superficie"),
           ("I", "interface", "hidrofobicidade governa a particao na interface")],
    "P5": [("E", "adsorvente", "estabilidade termica e' limite energetico"),
           ("O", "adsorvente", "limite termico restringe a operacao")],
    "P6": [("P", "adsorvente", "condutividade e gap sao estrutura eletronica"),
           ("I", "interface", "transferencia de carga na interface")],
    "P7": [("C", "adsorvente", "lixiviacao e' risco ambiental do solido"),
           ("C", "meio", "o lixiviado entra na matriz aquosa")],
    "D1": [("I", "interface", "qmax mede a capacidade de interacao")],
    "D2": [("I", "interface", "afinidade descreve a forca da interacao")],
    "D3": [("I", "interface", "cinetica revela o caminho de interacao"),
           ("O", "meio", "tempo de equilibrio define o tempo de contato")],
    "D4": [("I", "interface", "seletividade e' competicao pela interface"),
           ("I", "adsorbato", "preferencia depende do adsorbato")],
    "D5": [("O", "adsorvente", "regeneracao e' operacao do material"),
           ("C", "adsorvente", "reuso reduz residuo gerado")],
    "D6": [("I", "interface", "eficiencia mede a retencao na interface"),
           ("O", "meio", "eficiencia depende das condicoes do meio")],
    "D7": [("O", "meio", "faixa de pH e temperatura e' janela operacional"),
           ("I", "interface", "condicoes deslocam o equilibrio da interface")],
    "C1": [("C", "adsorvente", "toxicidade do proprio material"),
           ("C", "meio", "toxicidade se expressa na agua tratada")],
    "C2": [("O", "adsorvente", "custo especifico do material")],
    "C3": [("C", "adsorvente", "origem do residuo e' questao ambiental"),
           ("O", "adsorvente", "logistica de obtencao e' operacional")],
    "C4": [("E", "adsorvente", "energia e emissao do ciclo de vida"),
           ("C", "meio", "emissao entra no balanco ambiental")],
    "C5": [("C", "adsorvente", "fim de vida do material"),
           ("O", "adsorvente", "reciclabilidade e' decisao operacional")],
    "C6": [("C", "meio", "limite normativo do efluente tratado"),
           ("C", "adsorbato", "o analito e' o alvo da norma")],
    "C7": [("O", "adsorvente", "escala do material"),
           ("O", "meio", "hidraulica e tempo de residencia")],
}

# ---------------------------------------------------------------------------
# Parametros de caracterizacao dos quatro componentes.
#
# Estes valores nao sao descritores 7Dx4: sao entradas de caracterizacao que
# alimentam regras e simuladores. Entram nos cruzamentos como `parametros`,
# identificados por `chave`, para a matriz nao esconder o dado de entrada.
# `fonte` declara como o valor pode ser obtido: informado, importado,
# calculado ou medido. `descritor` liga o parametro ao descritor que ele
# alimenta, quando a regra correspondente existe no backend.
# ---------------------------------------------------------------------------
PARAMETROS = [
    # ---- Adsorbato -------------------------------------------------------
    {"chave": "formula_molecular", "nome": "Formula molecular", "tipo": "texto",
     "componente": "adsorbato", "dimensao": "D", "unidade": None,
     "fonte": "informado", "papel": "identificacao quimica do adsorbato"},
    {"chave": "massa_molar", "nome": "Massa molar", "tipo": "numero",
     "componente": "adsorbato", "dimensao": "D", "unidade": "g/mol",
     "fonte": "informado", "papel": "converte concentracao massica em molar"},
    {"chave": "pka", "nome": "pKa", "tipo": "numero",
     "componente": "adsorbato", "dimensao": "S", "unidade": "adimensional",
     "fonte": "importado", "papel": "define a especie ionica predominante"},
    {"chave": "log_kow", "nome": "log Kow", "tipo": "numero",
     "componente": "adsorbato", "dimensao": "S", "unidade": "adimensional",
     "fonte": "importado", "papel": "hidrofobicidade do adsorbato"},
    {"chave": "carga_ionica", "nome": "Carga ionica", "tipo": "numero",
     "componente": "adsorbato", "dimensao": "P", "unidade": "e",
     "fonte": "calculada", "papel": "carga efetiva em funcao do pH"},
    {"chave": "raio_ionico", "nome": "Raio ionico", "tipo": "numero",
     "componente": "adsorbato", "dimensao": "D", "unidade": "nm",
     "fonte": "importado", "papel": "tamanho do adsorbato frente ao poro"},
    {"chave": "momento_dipolar", "nome": "Momento dipolar", "tipo": "numero",
     "componente": "adsorbato", "dimensao": "P", "unidade": "debye",
     "fonte": "calculada", "papel": "polaridade molecular"},
    {"chave": "homo", "nome": "Energia HOMO", "tipo": "numero",
     "componente": "adsorbato", "dimensao": "P", "unidade": "eV",
     "fonte": "calculada",
     "papel": "doador de eletrons; exige motor quantico registrado"},
    {"chave": "lumo", "nome": "Energia LUMO", "tipo": "numero",
     "componente": "adsorbato", "dimensao": "P", "unidade": "eV",
     "fonte": "calculada",
     "papel": "receptor de eletrons; exige motor quantico registrado"},
    {"chave": "gap_homo_lumo", "nome": "Gap HOMO-LUMO", "tipo": "numero",
     "componente": "adsorbato", "dimensao": "P", "unidade": "eV",
     "fonte": "calculada", "papel": "reatividade eletronica do adsorbato"},
    {"chave": "energia_hidratacao", "nome": "Energia de hidratacao",
     "tipo": "numero", "componente": "adsorbato", "dimensao": "E",
     "unidade": "kJ/mol", "fonte": "importado",
     "papel": "energia para despir a esfera de solvatacao"},
    {"chave": "concentracao_trabalho", "nome": "Concentracao de trabalho",
     "tipo": "numero", "componente": "adsorbato", "dimensao": "O",
     "unidade": "mg/L", "fonte": "informado",
     "papel": "faixa de concentracao que o processo precisa atender"},
    {"chave": "concentracao_inicial", "nome": "Concentracao inicial",
     "tipo": "numero", "componente": "meio", "dimensao": "I", "unidade": "mg/L",
     "fonte": "informado", "papel": "C0 do ensaio de adsorcao"},
    {"chave": "concentracao_equilibrio", "nome": "Concentracao de equilibrio",
     "tipo": "numero", "componente": "meio", "dimensao": "I",
     "unidade": "mg/L", "fonte": "medido", "papel": "Ce do ensaio"},

    # ---- Adsorvente ------------------------------------------------------
    {"chave": "composicao", "nome": "Composicao quimica", "tipo": "texto",
     "componente": "adsorvente", "dimensao": "D", "unidade": None,
     "fonte": "informado", "papel": "composicao declarada do material"},
    {"chave": "densidade", "nome": "Massa especifica", "tipo": "numero",
     "componente": "adsorvente", "dimensao": "D", "unidade": "g/cm3",
     "fonte": "medido", "papel": "densidade real ou aparente"},
    {"chave": "porosidade", "nome": "Porosidade", "tipo": "numero",
     "componente": "adsorvente", "dimensao": "D", "unidade": "fracao",
     "fonte": "calculada", "papel": "fracao vazia do leito"},
    {"chave": "area_superficial", "nome": "Area superficial BET",
     "tipo": "numero", "componente": "adsorvente", "dimensao": "D",
     "unidade": "m2/g", "fonte": "medido", "papel": "area acessivel por massa",
     "descritor": "S3"},
    {"chave": "volume_poros", "nome": "Volume de poros", "tipo": "numero",
     "componente": "adsorvente", "dimensao": "D", "unidade": "cm3/g",
     "fonte": "medido", "papel": "volume de poro total", "descritor": "S4"},
    {"chave": "diametro_poro", "nome": "Diametro medio de poro",
     "tipo": "numero", "componente": "adsorvente", "dimensao": "D",
     "unidade": "nm", "fonte": "medido", "papel": "acesso do adsorbato ao poro",
     "descritor": "S4"},
    {"chave": "grupos_funcionais", "nome": "Grupos funcionais", "tipo": "texto",
     "componente": "adsorvente", "dimensao": "S", "unidade": None,
     "fonte": "medido", "papel": "quimica da superficie", "descritor": "S6"},
    {"chave": "densidade_sitios", "nome": "Densidade de sitios ativos",
     "tipo": "numero", "componente": "adsorvente", "dimensao": "S",
     "unidade": "mmol/g", "fonte": "medido", "papel": "sitios disponiveis",
     "descritor": "S6"},
    {"chave": "carga_superficial", "nome": "Carga superficial", "tipo": "numero",
     "componente": "adsorvente", "dimensao": "S", "unidade": "mV",
     "fonte": "medido", "papel": "potencial zeta na condicao do meio",
     "descritor": "P2"},
    {"chave": "pzc", "nome": "Ponto de carga zero", "tipo": "numero",
     "componente": "adsorvente", "dimensao": "S", "unidade": "pH",
     "fonte": "medido", "papel": "pH de carga liquida nula", "descritor": "P2"},
    {"chave": "funcionalizacao", "nome": "Funcionalizacao superficial",
     "tipo": "texto", "componente": "adsorvente", "dimensao": "S",
     "unidade": None, "fonte": "informado", "papel": "tratamento aplicado",
     "descritor": "S6"},
    {"chave": "capacidade_experimental", "nome": "Capacidade experimental",
     "tipo": "numero", "componente": "adsorvente", "dimensao": "I",
     "unidade": "mg/g", "fonte": "medido", "papel": "qmax medida",
     "descritor": "D1"},
    {"chave": "tratamento", "nome": "Tratamento do material", "tipo": "texto",
     "componente": "adsorvente", "dimensao": "D", "unidade": None,
     "fonte": "informado", "papel": "ativacao, lavagem, moagem"},

    # ---- Interface -------------------------------------------------------
    {"chave": "energia_adsorcao", "nome": "Energia de adsorcao",
     "tipo": "numero", "componente": "interface", "dimensao": "E",
     "unidade": "kJ/mol", "fonte": "calculada",
     "papel": "energia liberada na formacao do complexo"},
    {"chave": "energia_interacao", "nome": "Energia de interacao",
     "tipo": "numero", "componente": "interface", "dimensao": "I",
     "unidade": "kJ/mol", "fonte": "calculada",
     "papel": "soma dos termos de interacao"},
    {"chave": "distancia_contato", "nome": "Distancia de contato",
     "tipo": "numero", "componente": "interface", "dimensao": "I",
     "unidade": "angstrom", "fonte": "calculada", "papel": "geometria do complexo"},
    {"chave": "angulo_interacao", "nome": "Angulo de interacao",
     "tipo": "numero", "componente": "interface", "dimensao": "I",
     "unidade": "graus", "fonte": "calculada", "papel": "orientacao do adsorbato"},
    {"chave": "energia_eletrostatica", "nome": "Termo eletrostatico",
     "tipo": "numero", "componente": "interface", "dimensao": "E",
     "unidade": "kJ/mol", "fonte": "calculada", "papel": "atracao/repulsao de carga"},
    {"chave": "energia_hidrogenio", "nome": "Termo de ligacao de hidrogenio",
     "tipo": "numero", "componente": "interface", "dimensao": "I",
     "unidade": "kJ/mol", "fonte": "calculada", "papel": "ponte de hidrogenio"},
    {"chave": "energia_dispersao", "nome": "Termo dispersivo",
     "tipo": "numero", "componente": "interface", "dimensao": "E",
     "unidade": "kJ/mol", "fonte": "calculada", "papel": "van der Waals"},
    {"chave": "fukui", "nome": "Indice de Fukui", "tipo": "numero",
     "componente": "interface", "dimensao": "P", "unidade": "adimensional",
     "fonte": "calculada", "papel": "sitio reativo; exige motor quantico"},
    {"chave": "qtaim", "nome": "Analise QTAIM", "tipo": "texto",
     "componente": "interface", "dimensao": "P", "unidade": None,
     "fonte": "calculada", "papel": "topologia da densidade eletronica"},
    {"chave": "nci", "nome": "Analise NCI", "tipo": "texto",
     "componente": "interface", "dimensao": "P", "unidade": None,
     "fonte": "calculada", "papel": "interacoes nao covalentes"},
    {"chave": "elf", "nome": "Funcao ELF", "tipo": "texto",
     "componente": "interface", "dimensao": "P", "unidade": None,
     "fonte": "calculada", "papel": "localizacao de eletrons"},
    {"chave": "distribuicao_cargas", "nome": "Distribuicao de cargas",
     "tipo": "texto", "componente": "interface", "dimensao": "P",
     "unidade": None, "fonte": "calculada", "papel": "cargas parciais no complexo"},

    # ---- Meio ------------------------------------------------------------
    {"chave": "ph", "nome": "pH", "tipo": "numero",
     "componente": "meio", "dimensao": "O", "unidade": "pH",
     "fonte": "informado", "papel": "condicao que decide carga e competicao"},
    {"chave": "temperatura", "nome": "Temperatura", "tipo": "numero",
     "componente": "meio", "dimensao": "O", "unidade": "C",
     "fonte": "informado", "papel": "afeta equilibrio e cinetica"},
    {"chave": "forca_ionica", "nome": "Forca ionica", "tipo": "numero",
     "componente": "meio", "dimensao": "I", "unidade": "mol/L",
     "fonte": "informado", "papel": "competicao eletrostatica"},
    {"chave": "solvente", "nome": "Solvente", "tipo": "texto",
     "componente": "meio", "dimensao": "O", "unidade": None,
     "fonte": "informado", "papel": "matriz do fluido"},
    {"chave": "tempo_contato", "nome": "Tempo de contato", "tipo": "numero",
     "componente": "meio", "dimensao": "O", "unidade": "min",
     "fonte": "informado", "papel": "tempo de residencia", "descritor": "D3"},
    {"chave": "agitacao", "nome": "Velocidade de agitacao", "tipo": "numero",
     "componente": "meio", "dimensao": "O", "unidade": "rpm",
     "fonte": "informado", "papel": "regime de mistura"},
    {"chave": "volume", "nome": "Volume de solucao", "tipo": "numero",
     "componente": "meio", "dimensao": "O", "unidade": "mL",
     "fonte": "informado", "papel": "base de calculo de massa de adsorbato"},
    {"chave": "massa_adsorvente", "nome": "Massa de adsorvente",
     "tipo": "numero", "componente": "meio", "dimensao": "O",
     "unidade": "g", "fonte": "informado", "papel": "dose aplicada"},
    {"chave": "materia_organica", "nome": "Materia organica dissolvida",
     "tipo": "numero", "componente": "meio", "dimensao": "C",
     "unidade": "mg/L", "fonte": "medido", "papel": "competicao por sitios"},
    {"chave": "ions_competidores", "nome": "Ions competidores", "tipo": "texto",
     "componente": "meio", "dimensao": "I", "unidade": None,
     "fonte": "medido", "papel": "competicao ionica"},
    {"chave": "composicao_meio", "nome": "Composicao do meio", "tipo": "texto",
     "componente": "meio", "dimensao": "C", "unidade": None,
     "fonte": "informado", "papel": "natureza do efluente"},
    {"chave": "pressao", "nome": "Pressao", "tipo": "numero",
     "componente": "meio", "dimensao": "O", "unidade": "kPa",
     "fonte": "informado", "papel": "aplicavel a sistemas pressurizados"},
    {"chave": "consumo_energetico", "nome": "Consumo energetico do processo",
     "tipo": "numero", "componente": "meio", "dimensao": "E",
     "unidade": "kWh/m3", "fonte": "medido",
     "papel": "energia de bombeamento e mistura na matriz tratada",
     "descritor": "C4"},

    # ---- Parametros que completam os cruzamentos ainda sem candidato ------
    {"chave": "potencial_redox", "nome": "Potencial redox", "tipo": "numero",
     "componente": "meio", "dimensao": "P", "unidade": "mV",
     "fonte": "medido", "papel": "condicao eletronica da matriz aquosa"},
    {"chave": "turbidez_ou_solidos", "nome": "Solidos suspensos",
     "tipo": "numero", "componente": "meio", "dimensao": "D",
     "unidade": "mg/L", "fonte": "medido",
     "papel": "constituicao fisica da matriz que compete com o adsorbato"},
    {"chave": "tensoativos", "nome": "Surfactantes", "tipo": "numero",
     "componente": "meio", "dimensao": "S", "unidade": "mg/L",
     "fonte": "medido",
     "papel": "especies superficiais que alteram a interface"},
    {"chave": "espessura_camada", "nome": "Espessura da camada interfacial",
     "tipo": "numero", "componente": "interface", "dimensao": "D",
     "unidade": "nm", "fonte": "calculada",
     "papel": "extensao fisica da regiao de interacao"},
    {"chave": "tensao_superficial", "nome": "Tensao interfacial",
     "tipo": "numero", "componente": "interface", "dimensao": "S",
     "unidade": "mN/m", "fonte": "medido",
     "papel": "energia livre por area de contato"},
    {"chave": "destino_adsorbato", "nome": "Destino do adsorbato retido",
     "tipo": "texto", "componente": "interface", "dimensao": "C",
     "unidade": None, "fonte": "informado",
     "papel": "destinacao final do contaminante apos a dessorcao"},
    {"chave": "perda_de_carga", "nome": "Perda de carga no leito",
     "tipo": "numero", "componente": "interface", "dimensao": "O",
     "unidade": "kPa/m", "fonte": "calculada",
     "papel": "resistencia hidraulica imposta pela interface ao escoamento",
     "descritor": "C7"},
]

PARAMETROS_POR_CHAVE = {item["chave"]: item for item in PARAMETROS}

# ---------------------------------------------------------------------------
# Fatores de qualidade do dado.
#
# A ordem segue a hierarquia declarada em `matriz_7d4.ESTADOS_DADO`: um valor
# validado vale mais que um valor apenas presente, que vale mais que um valor
# calculado por regra, que vale mais que uma estimativa. `ausente` e
# `nao_aplicavel` valem zero: ausencia de dado nao recebe peso.
# ---------------------------------------------------------------------------
QUALIDADE = {
    "validado": 1.0,
    "presente": 0.85,
    "calculado": 0.6,
    "estimado": 0.4,
    "ausente": 0.0,
    "nao_aplicavel": 0.0,
}
COM_DADO = ("validado", "presente", "calculado", "estimado")

# Redundancia so' e' declarada com massa de dados suficiente para o teste de
# Pearson: abaixo disso a correlacao e' artefato de poucos pontos.
MINIMO_REDUNDANCIA = 4

# t de Student bicaudal a 95% por grau de liberdade (gl = n - 2).
_T_95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
         7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
         13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101,
         19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064,
         25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042}


def _r_critico(n: int) -> float:
    """|r| minimo para correlacao significativa a 95% com n materiais."""
    graus = max(1, int(n) - 2)
    t = _T_95.get(graus, 1.960)
    return t / math.sqrt(t * t + graus)


# ---------------------------------------------------------------------------
# Estrutura: os 28 cruzamentos e quem pode informa-los
# ---------------------------------------------------------------------------
def relacoes(codigo: str) -> list:
    """Relacoes (dimensao, componente) de um descritor 7Dx4."""
    codigo = str(codigo or "").strip().upper()
    saida = []
    for indice, (letra, componente, papel) in enumerate(
            RELACOES_DESCRITORES.get(codigo) or []):
        dimensao = DIMENSOES_POR_LETRA.get(letra) or {}
        comp = COMPONENTES_POR_CHAVE.get(componente) or {}
        saida.append({
            "dimensao": letra,
            "dimensao_nome": dimensao.get("nome"),
            "componente": componente,
            "componente_nome": comp.get("nome"),
            "papel": papel,
            "principal": indice == 0,
        })
    return saida


def descritores_do_cruzamento(letra: str, componente: str) -> list:
    """Codigos de descritor 7Dx4 que informam o cruzamento."""
    letra = str(letra or "").strip().upper()
    componente = str(componente or "").strip().lower()
    return [codigo for codigo, rels in sorted(RELACOES_DESCRITORES.items())
            if any(d == letra and c == componente for d, c, _ in rels)]


def parametros_do_cruzamento(letra: str, componente: str) -> list:
    """Chaves de parametro de caracterizacao do cruzamento."""
    letra = str(letra or "").strip().upper()
    componente = str(componente or "").strip().lower()
    return [item["chave"] for item in PARAMETROS
            if item["dimensao"] == letra and item["componente"] == componente]


def celulas() -> list:
    """Os 28 cruzamentos com os elementos que podem informa-los."""
    saida = []
    for dimensao in DIMENSOES:
        for componente in COMPONENTES:
            codigos = descritores_do_cruzamento(dimensao["letra"],
                                                componente["chave"])
            chaves = parametros_do_cruzamento(dimensao["letra"],
                                              componente["chave"])
            saida.append({
                "id": "%s-%s" % (dimensao["letra"], componente["chave"]),
                "dimensao": dimensao["letra"],
                "dimensao_nome": dimensao["nome"],
                "dimensao_pergunta": dimensao["pergunta"],
                "componente": componente["chave"],
                "componente_nome": componente["nome"],
                "descritores_possiveis": codigos,
                "parametros_possiveis": chaves,
            })
    return saida


def estrutura() -> dict:
    """Descricao completa do metodo: eixos, relacoes e catalogo de parametros."""
    cruzamentos = celulas()
    return {
        "dimensoes": [dict(item) for item in DIMENSOES],
        "componentes": [dict(item) for item in COMPONENTES],
        "total_cruzamentos": len(cruzamentos),
        "total_dimensoes": len(DIMENSOES),
        "total_componentes": len(COMPONENTES),
        "cruzamentos": cruzamentos,
        "relacoes": {codigo: relacoes(codigo)
                     for codigo in matriz_7d4.DESCRITORES_POR_CODIGO},
        "parametros": [dict(item) for item in PARAMETROS],
        "qualidade_por_estado": dict(QUALIDADE),
        "estados_com_dado": list(COM_DADO),
        "sem_cruzamento": sorted(
            set(matriz_7d4.DESCRITORES_POR_CODIGO) - set(RELACOES_DESCRITORES)),
    }


# ---------------------------------------------------------------------------
# Pesos: derivados dos dados, nunca de uma tabela fixa por dimensao
# ---------------------------------------------------------------------------
def _numero(valor):
    """Converte para float finito ou devolve None (nunca inventa zero)."""
    if isinstance(valor, dict):
        valor = valor.get("valor")
    if valor is None or isinstance(valor, bool):
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if math.isnan(numero) or math.isinf(numero):
        return None
    return numero


def _pertinencias(pergunta=None, aplicacao=None) -> dict:
    """Pertinencia relativa de cada descritor para a pergunta da pesquisa.

    Reaproveita a pontuacao de `matriz_7d4.selecionar` (+3 por sinonimo
    encontrado, +2 por aplicacao coberta, +1 se o descritor e' essencial).
    A base 1 impede que um descritor zere so' por nao casar com o texto: ele
    continua pertinente ao proprio cruzamento, apenas com menos peso.
    """
    escolhidos = matriz_7d4.selecionar(pergunta or "", aplicacao=aplicacao,
                                       incluir_essenciais=True)
    pontos = {str(item.get("codigo")).upper(): float(item.get("pontuacao") or 0.0)
              for item in escolhidos}
    for codigo in matriz_7d4.DESCRITORES_POR_CODIGO:
        pontos.setdefault(codigo, 0.0)
    teto = 1.0 + max(pontos.values() or [0.0])
    return {codigo: (1.0 + valor) / teto for codigo, valor in pontos.items()}


def _tabela(valores_por_material) -> dict:
    """`{material: {codigo: valor}}` -> `{codigo: {material: valor numerico}}`."""
    saida = {}
    for material, valores in (valores_por_material or {}).items():
        for codigo, valor in (valores or {}).items():
            numero = _numero(valor)
            if numero is None:
                continue
            saida.setdefault(str(codigo).upper(), {})[str(material)] = numero
    return saida


def _utilidades(tabela: dict) -> dict:
    """Utilidade entropica de Shannon: quanto o descritor discrimina.

    Os valores do descritor entre materiais sao levados a [0,1] (min-max) e a
    entropia normalizada `e` mede o quanto se repetem: `d = 1 - e`. Descritor
    constante nao discrimina (d = 0). Sem dois materiais com valor numerico a
    estatistica nao existe e o fator fica neutro (1,0) — nunca zero.
    """
    utilidades = {}
    for codigo, valores in tabela.items():
        lista = list(valores.values())
        if len(lista) < 2:
            continue
        minimo, maximo = min(lista), max(lista)
        if maximo <= minimo:
            utilidades[codigo] = 0.0
            continue
        normalizados = [(valor - minimo) / (maximo - minimo) for valor in lista]
        soma = sum(normalizados)
        if soma <= 0:
            utilidades[codigo] = 0.0
            continue
        proporcoes = [valor / soma for valor in normalizados]
        fator = 1.0 / math.log(len(proporcoes))
        entropia = -fator * sum(p * math.log(p) for p in proporcoes if p > 0)
        utilidades[codigo] = max(0.0, 1.0 - entropia)
    teto = max(utilidades.values() or [0.0])
    if teto > 0:
        utilidades = {codigo: valor / teto for codigo, valor in utilidades.items()}
    return utilidades



def _correlacao(a: dict, b: dict):
    """Pearson entre dois descritores nos materiais comuns (None se < 4)."""
    comuns = sorted(set(a) & set(b))
    if len(comuns) < MINIMO_REDUNDANCIA:
        return None
    xs = [a[chave] for chave in comuns]
    ys = [b[chave] for chave in comuns]
    media_x = sum(xs) / len(xs)
    media_y = sum(ys) / len(ys)
    variancia_x = sum((valor - media_x) ** 2 for valor in xs)
    variancia_y = sum((valor - media_y) ** 2 for valor in ys)
    if variancia_x <= 0 or variancia_y <= 0:
        return None
    covariacao = sum((x - media_x) * (y - media_y) for x, y in zip(xs, ys))
    correlacao = covariacao / math.sqrt(variancia_x * variancia_y)
    critico = _r_critico(len(comuns))
    if abs(correlacao) < critico:
        return None
    return correlacao


def _redundancias(tabela: dict) -> dict:
    """Maior |r| de cada descritor com outro descritor medido.

    So' existe com pelo menos tres materiais com os dois valores medidos. Sem
    isso a redundancia nao e' demonstravel e fica 0: o sistema nao presume
    que dois descritores sejam redundantes.
    """
    codigos = sorted(tabela)
    redundancias = {codigo: 0.0 for codigo in codigos}
    for indice, primeiro in enumerate(codigos):
        for segundo in codigos[indice + 1:]:
            correlacao = _correlacao(tabela[primeiro], tabela[segundo])
            if correlacao is None:
                continue
            forca = min(1.0, abs(correlacao))
            redundancias[primeiro] = max(redundancias[primeiro], forca)
            redundancias[segundo] = max(redundancias[segundo], forca)
    return redundancias


def _normalizados(tabela: dict) -> dict:
    """Min-max de cada descritor entre materiais (ausente quando constante)."""
    saida = {}
    for codigo, valores in tabela.items():
        if len(valores) < 2:
            continue
        minimo, maximo = min(valores.values()), max(valores.values())
        if maximo <= minimo:
            continue
        saida[codigo] = {material: (valor - minimo) / (maximo - minimo)
                         for material, valor in valores.items()}
    return saida


def _pesar(itens: list, pertinencias: dict, utilidades: dict,
           redundancias: dict):
    """Peso relativo dos itens dentro de um cruzamento.

    peso_bruto = qualidade(estado) x pertinencia(pergunta) x
                 utilidade(entropia) x (1 - redundancia)

    Se nenhum item tem variabilidade observada, o peso volta para
    qualidade x pertinencia (declarado no retorno) em vez de ficar todo zero.
    """
    brutos = []
    for item in itens:
        estado = (item.get("estado") or "ausente").strip().lower()
        qualidade = QUALIDADE.get(estado, 0.0)
        pertinencia = pertinencias.get(item["codigo"], 0.0)
        utilidade = utilidades.get(item["codigo"], 1.0)
        redundancia = redundancias.get(item["codigo"], 0.0)
        item["qualidade"] = round(qualidade, 4)
        item["pertinencia"] = round(pertinencia, 4)
        item["utilidade"] = round(utilidade, 4)
        item["redundancia"] = round(redundancia, 4)
        brutos.append(qualidade * pertinencia * utilidade * (1.0 - redundancia))
    total = sum(brutos)
    motivo = None
    if total <= 0:
        brutos = [item["qualidade"] * item["pertinencia"] for item in itens]
        total = sum(brutos)
        motivo = "sem variabilidade observada: peso por qualidade x pertinencia"
    if total <= 0:
        return [0.0 for _ in itens], "nenhum dado no cruzamento: sem peso"
    return [bruto / total for bruto in brutos], motivo



# ---------------------------------------------------------------------------
# Montagem dos 28 cruzamentos
# ---------------------------------------------------------------------------
def _item_parametro(chave: str, bruto) -> dict:
    meta = PARAMETROS_POR_CHAVE.get(chave) or {}
    if isinstance(bruto, dict):
        valor = bruto.get("valor")
        unidade = bruto.get("unidade") or meta.get("unidade")
        estado = str(bruto.get("estado") or "presente").strip().lower()
        origem = bruto.get("origem") or meta.get("fonte")
    elif bruto is None or bruto == "":
        valor, unidade, estado, origem = None, meta.get("unidade"), "ausente", None
    else:
        valor = bruto
        unidade = meta.get("unidade")
        estado = "presente"
        origem = meta.get("fonte")
    if estado not in QUALIDADE:
        estado = "ausente"
    return {
        "chave": chave,
        "nome": meta.get("nome"),
        "valor": valor,
        "unidade": unidade,
        "estado": estado,
        "origem": origem,
        "papel": meta.get("papel"),
        "descritor": meta.get("descritor"),
        "tipo": meta.get("tipo"),
    }


def montar(linhas=None, parametros=None, aplicacao=None, pergunta=None,
           valores_por_material=None, material_id=None) -> dict:
    """Monta os 28 cruzamentos 7Dx4 a partir do que existe de dado.

    `linhas`   descritores do material no formato de
               `motor_pesquisa.descritores_do_material()["descritores"]`.
    `parametros` caracterizacao dos componentes: `{chave: valor}` ou
               `{chave: {"valor","unidade","estado","origem"}}`.
    `valores_por_material` `{material_id: {codigo: valor}}` de todos os
               materiais da pesquisa: sem ele o peso usa so' qualidade x
               pertinencia (nao ha' entropia nem redundancia para medir).
    """
    por_codigo = {}
    for linha in linhas or []:
        codigo = str((linha or {}).get("codigo") or "").strip().upper()
        if matriz_7d4.obter(codigo) is not None:
            por_codigo[codigo] = linha
    parametros = {str(chave).strip().lower(): valor
                  for chave, valor in (parametros or {}).items()}

    tabela = _tabela(valores_por_material)
    if not tabela and material_id and por_codigo:
        tabela = _tabela({material_id: {codigo: linha.get("valor")
                                        for codigo, linha in por_codigo.items()}})
    utilidades = _utilidades(tabela)
    redundancias = _redundancias(tabela)
    normalizados = _normalizados(tabela)
    pertinencias = _pertinencias(pergunta, aplicacao)

    saida = []
    for celula in celulas():
        itens = []
        for codigo in celula["descritores_possiveis"]:
            descritor = matriz_7d4.obter(codigo) or {}
            linha = por_codigo.get(codigo) or {}
            estado = str(linha.get("estado") or "ausente").strip().lower()
            relacao = next((item for item in relacoes(codigo)
                            if item["dimensao"] == celula["dimensao"]), {})
            itens.append({
                "codigo": codigo,
                "nome": descritor.get("nome"),
                "definicao": descritor.get("definicao"),
                "unidade": linha.get("unidade") or descritor.get("unidade"),
                "valor": _numero(linha.get("valor")),
                "valor_texto": linha.get("valor_texto"),
                "estado": estado if estado in QUALIDADE else "ausente",
                "fonte": linha.get("fonte"),
                "essencial": bool(descritor.get("essencial")),
                "papel": relacao.get("papel"),
                "principal": bool(relacao.get("principal")),
            })
        pesos, motivo_peso = _pesar(itens, pertinencias, utilidades, redundancias)
        celula_parametros = [_item_parametro(chave, parametros.get(chave))
                             for chave in celula["parametros_possiveis"]]
        com_dado, lacunas, com_parametro = [], [], 0
        soma_qualidade = soma_indice = 0.0
        usados_indice = 0
        for item, peso in zip(itens, pesos):
            item["peso"] = round(peso, 6)
            mapa = normalizados.get(item["codigo"]) or {}
            normalizado = mapa.get(str(material_id)) if material_id else None
            item["valor_normalizado"] = (round(normalizado, 6)
                                         if normalizado is not None else None)
            item["contribuicao"] = (round(peso * normalizado, 6)
                                    if normalizado is not None else None)
            if item["estado"] in COM_DADO:
                com_dado.append(item)
                soma_qualidade += peso * QUALIDADE[item["estado"]]
                if normalizado is not None:
                    soma_indice += peso * normalizado
                    usados_indice += 1
            else:
                lacunas.append(item["codigo"])
        for parametro in celula_parametros:
            if parametro["valor"] not in (None, "") \
                    and parametro["estado"] in COM_DADO:
                com_parametro += 1
        if not com_dado:
            motivo_indice = "sem dado no cruzamento"
        elif not usados_indice:
            motivo_indice = ("indice comparativo exige o mesmo descritor em "
                             "pelo menos dois materiais")
        else:
            motivo_indice = None
        saida.append({
            "id": celula["id"],
            "dimensao": celula["dimensao"],
            "dimensao_nome": celula["dimensao_nome"],
            "dimensao_pergunta": celula["dimensao_pergunta"],
            "componente": celula["componente"],
            "componente_nome": celula["componente_nome"],
            "descritores": itens,
            "parametros": celula_parametros,
            "extras": {
                "total_descritores": len(itens),
                "com_dado": len(com_dado),
                "com_parametro": com_parametro,
                "lacunas": lacunas,
                "parametros_ausentes": [item["chave"] for item in celula_parametros
                                        if item["estado"] not in COM_DADO],
                "cobertura": round(sum(item["peso"] for item in com_dado), 4),
                "indice_qualidade": round(soma_qualidade, 4),
                "indice_comparativo": (round(soma_indice, 4)
                                       if usados_indice else None),
                "motivo_peso": motivo_peso,
                "motivo_indice": motivo_indice,
            },
        })
    return {
        "material_id": material_id,
        "aplicacao": aplicacao,
        "pergunta": pergunta,
        "dimensoes": [dict(item) for item in DIMENSOES],
        "componentes": [dict(item) for item in COMPONENTES],
        "cruzamentos": saida,
        "resumo": _resumo(saida, por_codigo),
        "preenchimento_7d4": matriz_7d4.avaliar_preenchimento(
            [{"codigo": codigo, "estado": linha.get("estado")}
             for codigo, linha in sorted(por_codigo.items())]),
        "metodo": _metodo(),
    }



# ---------------------------------------------------------------------------
# Resumo, metodo declarado e exportacao
# ---------------------------------------------------------------------------
def _resumo(cruzamentos: list, por_codigo: dict) -> dict:
    """Cobertura dos 28 cruzamentos: por dimensao, por componente e total."""
    com_dado, sem_dado = set(), set()
    por_dimensao, por_componente = {}, {}
    coberturas = []
    for celula in cruzamentos:
        for item in celula["descritores"]:
            alvo = com_dado if item["estado"] in COM_DADO else sem_dado
            alvo.add(item["codigo"])
        coberturas.append(celula["extras"]["cobertura"])
        for mapa, chave in ((por_dimensao, celula["dimensao"]),
                            (por_componente, celula["componente"])):
            registro = mapa.setdefault(chave, {"cruzamentos": 0, "com_dado": 0,
                                               "descritores": 0, "lacunas": 0})
            registro["cruzamentos"] += 1
            if celula["extras"]["com_dado"]:
                registro["com_dado"] += 1
            registro["descritores"] += celula["extras"]["total_descritores"]
            registro["lacunas"] += len(celula["extras"]["lacunas"])
    total = len(coberturas) or 1
    return {
        "cruzamentos": len(cruzamentos),
        "cruzamentos_com_dado": sum(1 for celula in cruzamentos
                                    if celula["extras"]["com_dado"]),
        "cobertura_media": round(sum(coberturas) / total, 4),
        "descritores_com_dado": sorted(com_dado),
        "descritores_ausentes": sorted(sem_dado - com_dado),
        "descritores_com_valor": sorted(
            codigo for codigo, linha in por_codigo.items()
            if str(linha.get("estado") or "").lower() in COM_DADO),
        "por_dimensao": por_dimensao,
        "por_componente": por_componente,
    }


def _metodo() -> dict:
    """Como cada numero do resultado foi obtido (vai para a interface e o DOCX)."""
    return {
        "formula_peso": ("qualidade(estado) x pertinencia(selecionar) x "
                         "utilidade(entropia) x (1 - redundancia)"),
        "normalizacao_peso": "peso = bruto / soma(bruto) dentro do cruzamento",
        "qualidade_por_estado": dict(QUALIDADE),
        "pertinencia": ("1 + pontuacao de matriz_7d4.selecionar (+3 sinonimo, "
                        "+2 aplicacao, +1 essencial), normalizada pelo maximo"),
        "utilidade": ("1 - entropia de Shannon dos valores min-max do descritor "
                      "entre materiais; neutra (1,0) quando nao ha' dois valores"),
        "redundancia": ("maior |r| de Pearson com outro descritor medido, "
                        "declarada apenas com >= %d materiais e |r| acima do "
                        "valor critico a 95%%; 0 quando nao demonstravel"
                        % MINIMO_REDUNDANCIA),
        "ausencia": ("descritor sem dado recebe peso 0 e entra em `lacunas`: "
                     "ausencia nunca vira zero nem peso artificial"),
        "cobertura": "soma dos pesos dos descritores que tem dado no cruzamento",
        "indice_qualidade": "media dos pesos pela qualidade do estado do dado",
        "indice_comparativo": ("soma de peso x valor normalizado (min-max entre "
                               "materiais); nulo quando nao ha' dois materiais"),
    }


def _campo_csv(valor) -> str:
    if valor is None:
        return ""
    texto = str(valor).replace(";", ",").replace("\n", " ").strip()
    return texto


def exportar_csv(resultado: dict) -> str:
    """Matriz plana em CSV (`;`) com valor, estado, origem, peso e contribuicao."""
    cabecalho = ["cruzamento", "dimensao", "componente", "tipo", "codigo",
                 "nome", "valor", "unidade", "estado", "origem", "peso",
                 "contribuicao", "papel"]
    linhas = [";".join(cabecalho)]
    for celula in resultado.get("cruzamentos") or []:
        for item in celula.get("descritores") or []:
            valor = item.get("valor")
            if valor is None:
                valor = item.get("valor_texto")
            linhas.append(";".join(_campo_csv(parte) for parte in (
                celula.get("id"), celula.get("dimensao_nome"),
                celula.get("componente_nome"), "descritor", item.get("codigo"),
                item.get("nome"), valor, item.get("unidade"), item.get("estado"),
                item.get("fonte"), item.get("peso"), item.get("contribuicao"),
                item.get("papel"))))
        for parametro in celula.get("parametros") or []:
            if parametro.get("valor") in (None, ""):
                continue
            linhas.append(";".join(_campo_csv(parte) for parte in (
                celula.get("id"), celula.get("dimensao_nome"),
                celula.get("componente_nome"), "parametro",
                parametro.get("chave"), parametro.get("nome"),
                parametro.get("valor"), parametro.get("unidade"),
                parametro.get("estado"), parametro.get("origem"), "", "",
                parametro.get("papel"))))
    return "\n".join(linhas) + "\n"

