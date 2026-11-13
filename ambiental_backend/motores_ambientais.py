# -*- coding: utf-8 -*-
"""Motores ambientais proprios: analise experimental -> descritor da matriz.

Este modulo e' a ponte entre `analises_experimentais` (calculo) e o resto do
backend (registro de simuladores, `/api/simulators`, execucao em pesquisa,
gravacao dos descritores). Cada motor:

* declara as entradas obrigatorias em `requisitos` (o painel bloqueia a execucao
  quando falta dado — nao existe execucao silenciosa com padrao inventado);
* declara o que produz: `codigo` do descritor 7Dx4, `chave` do resultado,
  unidade, `modo` (`valor` grava no descritor, `apoio` so registra suporte) e
  `estado` (`calculado`, `estimado`, `presente`);
* informa `natureza`, `nivel_validacao`, `limitacoes` e `referencias`, para que
  ninguem confunda indice ponderado com medicao experimental.

Os 12 descritores que estavam sem fonte passam a ter motor: S1, S6, S7, P2, P4,
P5, P7, D4, D5, C1, C5, C6.
"""
from __future__ import annotations

from . import analises_experimentais as ax

VERSAO_REGISTRO = "1.0.0"


def _empacotar(nome, analise, extras, pergunta):
    saida = {
        "simulador": nome,
        "motor": "ambiental.analises_experimentais",
        "metodo": analise["metodo"],
        "versao_metodo": analise["versao"],
        "nivel_validacao": analise["nivel_validacao"],
        "resultado": analise["resultado"],
        "limitacoes": analise["limitacoes"],
        "pergunta": pergunta or "",
    }
    saida.update(extras)
    return saida


def _precisa(params, chave):
    if params.get(chave) in (None, "", [], {}):
        raise ax.EntradaInvalida("informe '%s' (ver requisitos do motor)"
                                 % chave)
    return params[chave]


# ------------------------------------------------------------------- P2
def pzc_deriva_ph(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.pzc_por_deriva(_precisa(params, "ph_inicial"),
                                _precisa(params, "ph_final"))
    return _empacotar("pzc_deriva_ph", analise,
                      {"pzc": analise["resultado"]["pzc"],
                       "extrapolado": analise["resultado"]["extrapolado"]},
                      pergunta)


def pzc_titulacao_massa(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.pzc_por_titulacao_massa(_precisa(params, "massa_g_L"),
                                         _precisa(params, "ph_equilibrio"))
    return _empacotar("pzc_titulacao_massa", analise,
                      {"pzc": analise["resultado"]["pzc"]}, pergunta)


# ------------------------------------------------------------------- S6
def boehm_grupos(pergunta="", parametros=None):
    params = dict(parametros or {})
    if not any(params.get(k) not in (None, "")
               for k in ("naoh_mmol_g", "na2co3_mmol_g", "nahco3_mmol_g")):
        raise ax.EntradaInvalida("informe ao menos um consumo de Boehm "
                                 "(naoh_mmol_g, na2co3_mmol_g, nahco3_mmol_g) "
                                 "ou concentracao_mol_L + volume_mL + massa_g")
    analise = ax.boehm_titulacao(
        naoh_mmol_g=params.get("naoh_mmol_g"),
        na2co3_mmol_g=params.get("na2co3_mmol_g"),
        nahco3_mmol_g=params.get("nahco3_mmol_g"),
        hcl_mmol_g=params.get("hcl_mmol_g"),
        massa_g=params.get("massa_g"),
        concentracao_mol_L=params.get("concentracao_mol_L"),
        volume_mL=params.get("volume_mL"),
        consumos_mmol=params.get("consumos_mmol"))
    res = analise["resultado"]
    return _empacotar("boehm_grupos", analise, {
        "acidos_totais_mmol_g": res["acidos_totais_mmol_g"],
        "sitios_basicos_mmol_g": res["sitios_basicos_mmol_g"],
        "carboxilicas_mmol_g": res["carboxilicas_mmol_g"],
        "fenolicas_mmol_g": res["fenolicas_mmol_g"],
        "lactonas_mmol_g": res["lactonas_mmol_g"]}, pergunta)


def ftir_grupos(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.ftir_atribuicao(_precisa(params, "bandas_cm1"),
                                 params.get("tolerancia_cm1") or 15.0)
    return _empacotar("ftir_grupos", analise,
                      {"grupos_funcionais": analise["resultado"]["grupos"]},
                      pergunta)



# ------------------------------------------------------------------- S7
def granulometria_psd(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.granulometria(_precisa(params, "diametros_um"),
                               params.get("metodo") or "analise_de_imagem")
    res = analise["resultado"]
    return _empacotar("granulometria_psd", analise, {
        "d50_um": res["d50_um"], "d10_um": res["d10_um"],
        "d90_um": res["d90_um"], "span": res["span"]}, pergunta)


def fractal_agregacao(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.dimensao_fractal_agregacao(
        _precisa(params, "diametros_um"), params.get("massas_acumuladas_pct"))
    return _empacotar("fractal_agregacao", analise, {
        "dimensao_fractal": analise["resultado"]["dimensao_fractal"],
        "agregacao_valida": analise["resultado"]["valido"]}, pergunta)


# ------------------------------------------------------------------- P4
def angulo_contato(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.molhabilidade(
        _precisa(params, "angulo_agua_deg"),
        params.get("angulo_diiodometano_deg"),
        params.get("gama_agua"), params.get("gama_diiodometano"))
    res = analise["resultado"]
    return _empacotar("angulo_contato", analise, {
        "energia_superficial_mN_m": res["energia_superficial_mN_m"],
        "trabalho_adesao_mJ_m2": res["trabalho_adesao_agua_mJ_m2"],
        "classe_molhabilidade": res["classe"]}, pergunta)


# ------------------------------------------------------------------- P5
def tga_tangente(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.tga_estabilidade(_precisa(params, "temperatura_C"),
                                  _precisa(params, "massa_pct"),
                                  params.get("taxa_aquecimento_C_min"))
    res = analise["resultado"]
    return _empacotar("tga_tangente", analise, {
        "onset_C": res["onset_C"], "tmax_C": res["tmax_C"],
        "residuo_pct": res["residuo_pct"], "umidade_pct": res["umidade_pct"]},
        pergunta)


# ------------------------------------------------------------------- P7
def lixiviacao_cinetica(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.lixiviacao_cinetica(
        _precisa(params, "tempo_s"), params.get("fracao_lixiviada"),
        params.get("concentracao_mg_L"), params.get("volume_L"),
        params.get("massa_amostra_g"), params.get("teor_inicial_mg_kg"))
    res = analise["resultado"]
    res["lixiviacao_pct"] = round(100.0 * res["fracao_final"], 3)
    return _empacotar("lixiviacao_cinetica", analise, {
        "lixiviacao_pct": res["lixiviacao_pct"],
        "modelo_lixiviacao": res["modelo_escolhido"],
        "k_lixiviacao_por_s": res["k_por_s"],
        "r2_lixiviacao": res["r2_melhor"]}, pergunta)


def solubilidade_imersao(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.solubilidade_agua(_precisa(params, "massa_inicial_g"),
                                   _precisa(params, "massa_final_g"))
    return _empacotar("solubilidade_imersao", analise,
                      {"solubilidade_pct":
                       analise["resultado"]["solubilidade_pct"]}, pergunta)


# ------------------------------------------------------------------- D4
def seletividade_competitiva(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.seletividade_langmuir(_precisa(params, "componentes"),
                                       _precisa(params, "concentracoes_mg_L"))
    res = analise["resultado"]
    pares = res["seletividade"]
    res["seletividade_alfa"] = pares[0]["alfa"] if pares else None
    res["componente_preferido"] = pares[0]["preferido"] if pares else None
    return _empacotar("seletividade_competitiva", analise, {
        "seletividade_alfa": res["seletividade_alfa"],
        "par_avaliado": pares[0]["par"] if pares else None,
        "componente_preferido": res["componente_preferido"],
        "capacidade_total_mg_g": res["capacidade_total_mg_g"]}, pergunta)


# ------------------------------------------------------------------- D5
def regeneracao_reuso(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.regeneracao_ciclos(_precisa(params, "capacidades_mg_g"),
                                    params.get("desorcao_pct"))
    res = analise["resultado"]
    return _empacotar("regeneracao_reuso", analise, {
        # `ciclos_ate_80pct_capacidade` e' a chave que `descritores_simuladores`
        # le para gravar D5; `ciclos_uteis` fica como sinonimo historico para
        # nao quebrar quem ja consome a saida (ex.: test_ambiental_motores).
        "ciclos_ate_80pct_capacidade": res["ciclos_ate_80pct_capacidade"],
        "ciclos_uteis": res["ciclos_ate_80pct_capacidade"],
        "eficiencia_regeneracao_pct": res["eficiencia_regeneracao_pct"],
        "perda_capacidade_pct": res["perda_capacidade_pct"]}, pergunta)


# ------------------------------------------------------------------- C1
def perigo_composicao(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.perigo_ghs(_precisa(params, "composicao"))
    return _empacotar("perigo_composicao", analise, {
        "indice_perigo": analise["resultado"]["indice_perigo"],
        "classificacao_perigo": analise["resultado"]["classificacao"],
        "frases_h": analise["resultado"]["frases_h_relevantes"]}, pergunta)


# ------------------------------------------------------------------- C5
def reciclabilidade(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.fim_de_vida(_precisa(params, "composicao"),
                             params.get("ciclos_uteis"),
                             params.get("massa_reuso_kg"),
                             params.get("massa_total_kg"))
    return _empacotar("reciclabilidade", analise, {
        "indice_reciclabilidade":
            analise["resultado"]["indice_reciclabilidade"],
        "massa_reaproveitada_pct":
            analise["resultado"].get("massa_reaproveitada_pct")}, pergunta)


# ------------------------------------------------------------------- C6
def conformidade_limites(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.conformidade_normativa(_precisa(params, "analitos"),
                                        params.get("norma") or "ms_888_2021",
                                        params.get("limites"))
    res = analise["resultado"]
    margens = [r["margem_pct"] for r in res["resultados"]
               if r.get("margem_pct") is not None]
    res["margem_conformidade_pct"] = min(margens) if margens else None
    return _empacotar("conformidade_limites", analise, {
        "margem_conformidade_pct": res["margem_conformidade_pct"],
        "status_conformidade": res["status_geral"],
        "falhas_conformidade": res["falhas"]}, pergunta)


# ------------------------------------------------------------------- S1
def composicao_elementar(pergunta="", parametros=None):
    params = dict(parametros or {})
    analise = ax.composicao_elementar(_precisa(params, "elementos_pct"),
                                      params.get("formula_declarada"),
                                      params.get("elementos_principais"),
                                      params.get("tolerancia_pct") or 0.2)
    res = analise["resultado"]
    return _empacotar("composicao_elementar", analise, {
        "pureza_pct": res["pureza_pct"],
        "formula_empirica": res["formula_empirica"],
        "massa_molar_g_mol": res["massa_molar_formula_empirica_g_mol"]},
        pergunta)


# ------------------------------------------------------- metadados do registro
def _req(chave, unidade, descricao, obrigatorio=True):
    return {"chave": chave, "unidade": unidade, "obrigatorio": obrigatorio,
            "descricao": descricao}


def _prod(codigo, chave, unidade, modo="valor", estado="calculado",
          memoria=None):
    return {"codigo": codigo, "chave": chave, "unidade": unidade, "modo": modo,
            "estado": estado, "memoria": memoria}


MOTORES = {
    "pzc_deriva_ph": {
        "funcao": pzc_deriva_ph,
        "dominio": "Quimica de superficie - PZC",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_ANALITICO,
        "natureza": "calculo analitico sobre pH medido antes/depois do solido",
        "referencias": ["Fiol & Villaescusa (2006) Environ. Chem. Lett. 4:267"],
        "le_chaves": ["ph_inicial", "ph_final"],
        "requisitos": [
            _req("ph_inicial", "pH", "pH inicial (branco) de cada frasco"),
            _req("ph_final", "pH", "pH apos equilibrio, na mesma ordem"),
        ],
        "produz": [_prod("P2", "pzc", "pH", memoria=(
            "PZC por interpolacao da deriva de pH (dPH=0)") )],
    },
    "pzc_titulacao_massa": {
        "funcao": pzc_titulacao_massa,
        "dominio": "Quimica de superficie - PZC",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_AJUSTE,
        "natureza": "pH de equilibrio em funcao da dose de solido (patamar)",
        "referencias": ["Noh & Schwarz (1989) J. Colloid Interface Sci. 130:157"],
        "le_chaves": ["massa_g_L", "ph_equilibrio"],
        "requisitos": [
            _req("massa_g_L", "g/L", "doses crescentes de solido"),
            _req("ph_equilibrio", "pH", "pH final em cada dose"),
        ],
        "produz": [_prod("P2", "pzc", "pH", estado="calculado", memoria=(
            "pH do maior carregamento com checagem de patamar"))],
    },
    "boehm_grupos": {
        "funcao": boehm_grupos,
        "dominio": "Quimica de superficie - grupos funcionais",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_ANALITICO,
        "natureza": "estequiometria de titulacao acido-base (Boehm)",
        "referencias": ["Boehm (1964) Carbon 2:169"],
        "le_chaves": ["naoh_mmol_g", "na2co3_mmol_g", "nahco3_mmol_g",
                      "hcl_mmol_g", "massa_g", "concentracao_mol_L",
                      "volume_mL", "consumos_mmol"],
        "precisa_um_de": [["naoh_mmol_g", "na2co3_mmol_g", "nahco3_mmol_g",
                           "consumos_mmol"]],
        "requisitos": [
            _req("nahco3_mmol_g", "mmol/g", "consumo de NaHCO3 (carboxilicos)",
                 False),
            _req("na2co3_mmol_g", "mmol/g", "consumo de Na2CO3 (carboxilicos + "
                 "lactonas)", False),
            _req("naoh_mmol_g", "mmol/g", "consumo de NaOH (acidez total)",
                 False),
            _req("hcl_mmol_g", "mmol/g", "consumo de HCl (sitios basicos)",
                 False),
            _req("massa_g", "g", "massa quando se informa volume consumido",
                 False),
            _req("concentracao_mol_L", "mol/L", "titulante em mol/L", False),
            _req("volume_mL", "mL", "volume de titulante consumido", False),
        ],
        "produz": [
            _prod("S6", "acidos_totais_mmol_g", "mmol/g", memoria=(
                "acidez total de superficie por NaOH")),
            _prod("S6", "sitios_basicos_mmol_g", "mmol/g", modo="apoio",
                  memoria="sitios basicos (HCl) como suporte"),
            _prod("S6", "carboxilicas_mmol_g", "mmol/g", modo="apoio"),
            _prod("S6", "fenolicas_mmol_g", "mmol/g", modo="apoio"),
            _prod("S6", "lactonas_mmol_g", "mmol/g", modo="apoio"),
        ],
    },
    "ftir_grupos": {
        "funcao": ftir_grupos,
        "dominio": "Espectroscopia - FTIR",
        "tipo": "parametro",
        "nivel_validacao": ax.NIVEL_TABELA,
        "natureza": "atribuicao qualitativa por faixas de literatura",
        "referencias": ["Silverstein, Spectrometric Identification 8a ed.",
                        "Socrates, Infrared and Raman Characteristic "
                        "Frequencies 3a ed."],
        "le_chaves": ["bandas_cm1", "tolerancia_cm1"],
        "requisitos": [
            _req("bandas_cm1", "cm-1", "bandas observadas no espectro"),
            _req("tolerancia_cm1", "cm-1", "tolerancia de casamento (15)",
                 False),
        ],
        "produz": [_prod("S6", "grupos", "texto", modo="apoio", estado=None,
                         memoria=("grupos atribuidos; qualitativo, sem "
                                  "quantificacao"))],
    },
}


MOTORES.update({
    "granulometria_psd": {
        "funcao": granulometria_psd,
        "dominio": "Materiais - granulometria",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_ANALITICO,
        "natureza": "estatistica de diametros medidos por imagem/difracao",
        "referencias": ["ISO 13320 (difracao a laser): tratamento estatistico "
                        "da distribuicao"],
        "le_chaves": ["diametros_um", "metodo"],
        "requisitos": [
            _req("diametros_um", "um", "diametros individuais medidos"),
            _req("metodo", "texto", "tecnica (analise_de_imagem, laser)", False),
        ],
        "produz": [
            _prod("S7", "d50_um", "um", memoria="D50 por interpolacao da "
                  "distribuicao acumulada"),
            _prod("S7", "span", "adimensional", modo="apoio"),
        ],
    },
    "fractal_agregacao": {
        "funcao": fractal_agregacao,
        "dominio": "Materiais - agregacao",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_AJUSTE,
        "natureza": "dimensao fractal por inclinacao log-log da distribuicao",
        "referencias": ["Meakin (1998) Fractals, Scaling and Growth far from "
                        "Equilibrium"],
        "le_chaves": ["diametros_um", "massas_acumuladas_pct"],
        "requisitos": [
            _req("diametros_um", "um", "diametros da distribuicao"),
            _req("massas_acumuladas_pct", "%", "massa acumulada opcional",
                 False),
        ],
        "produz": [
            _prod("S7", "dimensao_fractal", "adimensional", modo="apoio",
                  memoria="Df de agregacao como suporte a morfologia"),
        ],
    },
    "angulo_contato": {
        "funcao": angulo_contato,
        "dominio": "Quimica de superficie - molhabilidade",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_ANALITICO,
        "natureza": "Young-Dupre + Owens-Wendt-Rabel-Kaelble sobre angulos "
                    "medidos",
        "referencias": ["Owens & Wendt (1969) J. Appl. Polym. Sci. 13:1741",
                        "Strom et al. (1987) J. Colloid Interface Sci. "
                        "119:352"],
        "le_chaves": ["angulo_agua_deg", "angulo_diiodometano_deg",
                      "gama_agua", "gama_diiodometano"],
        "requisitos": [
            _req("angulo_agua_deg", "graus", "angulo de contato com agua"),
            _req("angulo_diiodometano_deg", "graus", "angulo com diiodometano "
                 "(necessario para energia superficial)", False),
            _req("gama_agua", "mN/m", "tensao da agua medida (padrao 72,8)",
                 False),
            _req("gama_diiodometano", "mN/m", "tensao do diiodometano "
                 "(padrao 50,8)", False),
        ],
        "produz": [
            _prod("P4", "energia_superficial_mN_m", "mN/m", memoria=(
                "energia superficial total por OWRK com dois liquidos")),
            _prod("P4", "trabalho_adesao_agua_mJ_m2", "mJ/m2", modo="apoio"),
        ],
    },
    "tga_tangente": {
        "funcao": tga_tangente,
        "dominio": "Analise termica - TGA",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_AJUSTE,
        "natureza": "metodo da tangente sobre a curva de massa medida",
        "referencias": ["ASTM E1131", "ISO 11358 (TGA de polimeros)"],
        "le_chaves": ["temperatura_C", "massa_pct", "taxa_aquecimento_C_min"],
        "requisitos": [
            _req("temperatura_C", "C", "temperaturas da curva (crescente)"),
            _req("massa_pct", "%", "massa relativa em cada temperatura"),
            _req("taxa_aquecimento_C_min", "C/min", "taxa do ensaio", False),
        ],
        "produz": [
            _prod("P5", "onset_C", "C", memoria="onset de decomposicao por "
                  "tangente no pico de dTG"),
            _prod("P5", "residuo_pct", "%", modo="apoio"),
            _prod("P5", "umidade_pct", "%", modo="apoio"),
        ],
    },
})


MOTORES.update({
    "lixiviacao_cinetica": {
        "funcao": lixiviacao_cinetica,
        "dominio": "Destino ambiental - lixiviacao",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_AJUSTE,
        "natureza": "ajuste dos modelos de nucleo encolhendo sobre dados "
                    "medidos",
        "referencias": ["Levenspiel, Chemical Reaction Engineering 3a ed.",
                        "ABNT NBR 10005 (extrato solubilizado)"],
        "le_chaves": ["tempo_s", "fracao_lixiviada", "concentracao_mg_L",
                      "volume_L", "massa_amostra_g", "teor_inicial_mg_kg"],
        "requisitos": [
            _req("tempo_s", "s", "tempos de amostragem"),
            _req("fracao_lixiviada", "fracao 0-1", "X medido (ou informe "
                 "concentracao, volume, massa e teor)", False),
            _req("concentracao_mg_L", "mg/L", "concentracao no likiviado "
                 "(alternativa a X)", False),
            _req("volume_L", "L", "volume do ensaio", False),
            _req("massa_amostra_g", "g", "massa de solido", False),
            _req("teor_inicial_mg_kg", "mg/kg", "teor inicial do constituinte",
                 False),
        ],
        "produz": [
            _prod("P7", "lixiviacao_pct", "%", memoria=(
                "fracao lixiviada final ajustada por nucleo encolhendo")),
            _prod("P7", "modelo_lixiviacao", "texto", modo="apoio", estado=None),
        ],
    },
    "solubilidade_imersao": {
        "funcao": solubilidade_imersao,
        "dominio": "Destino ambiental - solubilidade",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_ANALITICO,
        "natureza": "balanco de massa entre pesagens antes/depois da imersao",
        "referencias": ["ABNT NBR 10006 (solubilizacao) para a condicao de "
                        "ensaio"],
        "le_chaves": ["massa_inicial_g", "massa_final_g"],
        "requisitos": [
            _req("massa_inicial_g", "g", "massa seca antes da imersao"),
            _req("massa_final_g", "g", "massa seca depois da imersao"),
        ],
        "produz": [_prod("P7", "solubilidade_pct", "%", memoria=(
            "perda de massa por imersao em agua"))],
    },
    "seletividade_competitiva": {
        "funcao": seletividade_competitiva,
        "dominio": "Desempenho - seletividade",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_ANALITICO,
        "natureza": "Langmuir competitivo estendido (modelo de competicao)",
        "referencias": ["Yang (1987) Gas Separation by Adsorption Processes",
                        "Myers & Prausnitz (1965) AIChE J. - IAST (nao "
                        "implementado)"],
        "le_chaves": ["componentes", "concentracoes_mg_L"],
        "requisitos": [
            _req("componentes", "lista", "cada item com nome, qmax_mg_g e "
                 "K_L_L_mg"),
            _req("concentracoes_mg_L", "mg/L", "concentracao de equilibrio de "
                 "cada componente (lista ou dict)"),
        ],
        "produz": [
            _prod("D4", "seletividade_alfa", "adimensional", estado="calculado",
                  memoria="coeficiente de seletividade do primeiro par "
                          "avaliado (Langmuir competitivo)"),
            _prod("D4", "componente_preferido", "texto", modo="apoio",
                  estado=None),
        ],
    },
    "regeneracao_reuso": {
        "funcao": regeneracao_reuso,
        "dominio": "Desempenho - regeneracao",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_AJUSTE,
        "natureza": "ajuste exponencial sobre capacidades medidas por ciclo",
        "referencias": ["Patel (2021) review de regeneracao de adsorventes, "
                        "J. Environ. Chem. Eng."],
        "le_chaves": ["capacidades_mg_g", "desorcao_pct"],
        "requisitos": [
            _req("capacidades_mg_g", "mg/g", "capacidade medida em cada ciclo"),
            _req("desorcao_pct", "%", "eficiencia de dessorcao por ciclo",
                 False),
        ],
        "produz": [
            _prod("D5", "ciclos_ate_80pct_capacidade", "ciclos", memoria=(
                "ciclos ate a capacidade cair a 80% da inicial (ajuste "
                "exponencial)")),
            _prod("D5", "eficiencia_regeneracao_pct", "%", modo="apoio"),
        ],
    },
})


MOTORES.update({
    "perigo_composicao": {
        "funcao": perigo_composicao,
        "dominio": "Contexto - toxicidade e seguranca",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_INDICE,
        "natureza": "indice ponderado pela categoria GHS dos constituintes",
        "referencias": ["GHS/CLP anexo VI (frases H harmonizadas)",
                        "ABNT NBR 14725 (FISPQ)"],
        "le_chaves": ["composicao"],
        "requisitos": [
            _req("composicao", "lista", "itens com substancia/elemento e "
                 "fracao ou percentual"),
        ],
        "produz": [
            _prod("C1", "indice_perigo", "0-4", estado="estimado", memoria=(
                "indice ponderado da tabela GHS curada; nao e' ensaio de "
                "toxicidade")),
            _prod("C1", "classificacao_perigo", "texto", modo="apoio",
                  estado=None),
        ],
    },
    "reciclabilidade": {
        "funcao": reciclabilidade,
        "dominio": "Contexto - fim de vida",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_INDICE,
        "natureza": "indice ponderado por classe de material",
        "referencias": ["Diretiva-Quadro 2008/98/CE (hierarquia de residuos)",
                        "ABNT NBR 10004 (classificacao de residuos)"],
        "le_chaves": ["composicao", "ciclos_uteis", "massa_reuso_kg",
                      "massa_total_kg"],
        "requisitos": [
            _req("composicao", "lista", "itens com classe/substancia e "
                 "fracao ou percentual"),
            _req("ciclos_uteis", "ciclos", "vida util medida (D5)", False),
            _req("massa_reuso_kg", "kg", "massa reaproveitada", False),
            _req("massa_total_kg", "kg", "massa total gerada", False),
        ],
        "produz": [
            _prod("C5", "indice_reciclabilidade", "0-1", estado="calculado",
                  memoria="media ponderada dos fatores por classe"),
            _prod("C5", "massa_reaproveitada_pct", "%", modo="apoio"),
        ],
    },
    "conformidade_limites": {
        "funcao": conformidade_limites,
        "dominio": "Contexto - conformidade normativa",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_TABELA,
        "natureza": "comparacao de analitos medidos com limites da norma",
        "referencias": ["Portaria GM/MS 888/2021", "CONAMA 430/2011"],
        "le_chaves": ["analitos", "norma", "limites"],
        "requisitos": [
            _req("analitos", "mg/L", "dict nome -> valor medido"),
            _req("norma", "texto", "ms_888_2021 (padrao) ou conama_430_2011",
                 False),
            _req("limites", "dict", "limites proprios (sobrescreve a tabela)",
                 False),
        ],
        "produz": [
            _prod("C6", "margem_conformidade_pct", "%", memoria=(
                "menor margem percentual entre os analitos avaliados")),
            _prod("C6", "status_conformidade", "texto", modo="apoio",
                  estado=None),
        ],
    },
    "composicao_elementar": {
        "funcao": composicao_elementar,
        "dominio": "Estrutura - composicao elementar",
        "tipo": "calculo",
        "nivel_validacao": ax.NIVEL_ANALITICO,
        "natureza": "normalizacao elementar e formula empirica",
        "referencias": ["IUPAC, massas atomicas padrao",
                        "ISO 21587 (analise por XRF de aluminossilicatos)"],
        "le_chaves": ["elementos_pct", "formula_declarada",
                      "elementos_principais"],
        "requisitos": [
            _req("elementos_pct", "dict", "simbolo -> percentual massico"),
            _req("elementos_principais", "lista", "elementos que compoem a "
                 "fase principal (define a pureza)", False),
            _req("formula_declarada", "texto", "formula esperada para "
                 "comparacao (ex.: Fe2O3)", False),
        ],
        "produz": [
            _prod("S1", "pureza_pct", "%", memoria=(
                "soma normalizada dos elementos principais")),
            _prod("S1", "formula_empirica", "texto", modo="apoio", estado=None),
        ],
    },
})


def registro() -> dict:
    """Nome -> funcao(pergunta, parametros). Usado por `adaptadores`."""
    return {nome: meta["funcao"] for nome, meta in MOTORES.items()}


def nomes() -> list:
    return sorted(MOTORES)


def mapa_simuladores() -> dict:
    """`SIMULADORES` no formato de `descritores_simuladores` (sem funcao)."""
    return {nome: {chave: valor for chave, valor in meta.items()
                   if chave != "funcao"}
            for nome, meta in MOTORES.items()}
