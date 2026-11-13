# -*- coding: utf-8 -*-
"""Adaptadores para os motores que ja existem no projeto.

Nada e' reimplementado aqui: cada funcao apenas localiza o modulo existente,
normaliza a chamada e devolve um dicionario com origem explicita
(`motor`, `estado`, `duracao_s`). Quando o motor nao esta carregado a resposta
diz qual foi o erro — nunca devolve lista vazia fingindo sucesso.

Motores conectados
    universal.py             113 simuladores (`SIMULADORES`)
    modelos_adsorcao_v2.py   Langmuir / Freundlich com validacao de parametros
    modelos_analiticos_v2.py isotermas analiticas fechadas
    pesquisa_cientifica.py   busca multi-base + dedup + estado por fonte
    bancos_rest.py           inventario e saude das bases
    bases_v5.py              fallback de busca bibliografica
"""
from __future__ import annotations

import importlib
import re
import threading
import time

from . import config

config.preparar_ambiente()

from . import motores_ambientais            # motores proprios deste backend

# Simuladores de `universal.py` cujo escopo e' ambiental. A lista e' curada a
# partir dos 113 registros existentes: sao os unicos cujo dominio declarado
# toca agua, solo, ar, residuo ou energia. Nada foi criado aqui.
SIMULADORES_AMBIENTAIS = (
    "agroeco", "biodiv", "catalise", "clima", "conserv", "ecologia",
    "eletroquimica", "eolica", "epi", "epidemia", "fluido", "hidro",
    "hidrogenio", "irriga", "metais", "micro", "nuclear_e", "poluicao",
    "recicla", "solar_e", "solo", "sustent", "superficie", "termo",
)

_PALAVRAS_SIMULADOR = {
    "metais": ("metal", "chumbo", "cobre", "cadmio", "cromo", "mercurio",
               "niquel", "zinco", "arsenio", "cation"),
    "poluicao": ("poluicao", "efluente", "contaminante", "esgoto", "rejeito",
                 "pollution", "wastewater"),
    "superficie": ("adsorcao", "isoterma", "carvao ativado", "adsorvente",
                   "superficie", "area superficial", "bet", "porosidade"),
    "solo": ("solo", "sorccao", "lixiviacao", "remediacao", "solo contaminado"),
    "hidro": ("agua", "hidrico", "rio", "reservatorio", "aquifero", "vazao"),
    "fluido": ("fluido", "escoamento", "reologia", "perda de carga",
               "coluna de leito"),
    "micro": ("microbiano", "bacteria", "biodegradacao", "biofilme",
              "micro-organismo"),
    "clima": ("clima", "temperatura", "chuva", "precipitacao", "seca"),
    "termo": ("termico", "calor", "energia termica", "entalpia"),
    "eletroquimica": ("eletroquimica", "eletrodo", "potencial", "eletrolise"),
    "catalise": ("catalise", "catalisador", "fotocatalise", "degradacao"),
    "recicla": ("reciclagem", "reuso", "residuo solido", "circularidade"),
    "sustent": ("sustentabilidade", "pegada", "ciclo de vida", "acoes"),
    "hidrogenio": ("hidrogenio", "h2", "eletrolisador"),
    "ecologia": ("ecossistema", "biodiversidade", "bioindicador"),
    "agroeco": ("agricultura", "agro", "fertilizante", "pesticida"),
    "biodiv": ("biodiversidade", "especie", "habitat"),
    "epi": ("epidemiologia", "exposicao", "saude publica"),
    "epidemia": ("epidemia", "surto", "contagio"),
    "irriga": ("irrigacao", "umidade do solo", "gotejamento"),
    "eolica": ("vento", "eolica", "aerogerador"),
    "solar_e": ("solar", "fotovoltaico", "radiacao solar"),
    "nuclear_e": ("nuclear", "radioativo", "rejeito radioativo"),
    "conserv": ("conservacao", "unidade de conservacao", "restauracao"),
}

_CACHE = {}


class MotorIndisponivel(RuntimeError):
    """O modulo do nucleo cientifico nao carregou neste ambiente."""


class SimuladorDesconhecido(KeyError):
    """Nome de simulador fora dos 113 registrados."""


def _modulo(nome: str):
    if nome in _CACHE:
        return _CACHE[nome]
    try:
        _CACHE[nome] = importlib.import_module(nome)
    except Exception as erro:                       # noqa: BLE001
        _CACHE[nome] = erro
    return _CACHE[nome]


def limpar_cache() -> None:
    _CACHE.clear()


def _erro(nome: str):
    valor = _modulo(nome)
    return valor if isinstance(valor, Exception) else None


def universal():
    modulo = _modulo("universal")
    if isinstance(modulo, Exception):
        raise MotorIndisponivel("universal.py: %s: %s"
                                % (type(modulo).__name__, modulo))
    return modulo


_MOTORES_SIMULACAO = None
_FUNCAO_PESQUISA = None


def definir_motores_simulacao(motores) -> None:
    """Injecao usada nos testes (e em adaptadores de outros ambientes)."""
    global _MOTORES_SIMULACAO
    _MOTORES_SIMULACAO = motores


def definir_funcao_pesquisa(funcao) -> None:
    """Injecao da funcao de busca bibliografica usada nos testes."""
    global _FUNCAO_PESQUISA
    _FUNCAO_PESQUISA = funcao


def _registro_simuladores() -> dict:
    """Motores proprios + `universal.SIMULADORES` (os proprios prevalecem).

    Os motores ambientais deste backend (PZC, TGA, Boehm, IAST competitivo,
    conformidade etc.) entram sempre; o catalogo de `universal.py` e' somado
    quando o modulo carrega. Assim a API funciona mesmo num ambiente onde o
    nucleo cientifico nao esta presente.
    """
    registro = dict(motores_ambientais.registro())
    if _MOTORES_SIMULACAO is not None:
        registro.update(_MOTORES_SIMULACAO)
        return registro
    modulo = _modulo("universal")
    if not isinstance(modulo, Exception):
        registro.update(getattr(modulo, "SIMULADORES", {}) or {})
    return registro


def nomes_disponiveis() -> set:
    """Nomes de simulador aceitos neste ambiente (sem importar o motor)."""
    if _MOTORES_SIMULACAO is not None:
        return set(motores_ambientais.registro()) | set(_MOTORES_SIMULACAO)
    modulo = _modulo("universal")
    extras = {} if isinstance(modulo, Exception) else \
        getattr(modulo, "SIMULADORES", {})
    return set(motores_ambientais.registro()) | set(extras or {})


def catalogo_simuladores() -> dict:
    """Catalogo real + recorte ambiental (sem inventar nomes)."""
    registro = _registro_simuladores()
    ambientais = [{"simulador": nome, "disponivel": nome in registro}
                  for nome in SIMULADORES_AMBIENTAIS]
    return {
        "total_registrados": len(registro),
        "total_ambientais": sum(1 for item in ambientais if item["disponivel"]),
        "ambientais": ambientais,
        "todos": sorted(registro),
        "motor": "universal.py",
    }


def selecionar_simuladores(pergunta: str, limite: int = 5) -> list:
    """Escolhe simuladores por dominio detectado e por vocabulario ambiental.

    `detectar_dominios` e' a mesma funcao que o app usa; o vocabulario abaixo
    apenas liga o texto da pergunta aos nomes ja registrados.
    """
    registro = _registro_simuladores()
    texto = (pergunta or "").lower()
    pontos = {}
    motivos = {}

    def marcar(nome, motivo, peso=1):
        if nome not in registro:
            return
        pontos[nome] = pontos.get(nome, 0) + peso
        motivos.setdefault(nome, [])
        if motivo not in motivos[nome]:
            motivos[nome].append(motivo)

    try:
        for dominio in universal().detectar_dominios(pergunta or ""):
            marcar(dominio, "dominio:%s" % dominio, 3)
    except MotorIndisponivel:
        pass

    for nome, palavras in _PALAVRAS_SIMULADOR.items():
        for palavra in palavras:
            if palavra in texto:
                marcar(nome, "termo:%s" % palavra, 2)

    ordenados = sorted(pontos.items(), key=lambda par: (-par[1], par[0]))
    if not ordenados:
        ordenados = [(nome, 0) for nome in SIMULADORES_AMBIENTAIS
                     if nome in registro][:limite]
    return [{
        "simulador": nome,
        "pontuacao": valor,
        "motivo": motivos.get(nome, ["padrao_ambiental"]),
        "disponivel": True,
    } for nome, valor in ordenados[:max(1, int(limite))]]


def executar_simulador(nome: str, pergunta: str = "", parametros: dict = None,
                       timeout_s: int = None) -> dict:
    """Executa um simulador real com prazo. Nunca deixa a requisicao pendurada."""
    registro = _registro_simuladores()
    if nome not in registro:
        raise SimuladorDesconhecido("simulador nao registrado: %s" % nome)
    funcao = registro[nome]
    motor = ("ambiental.analises_experimentais"
             if nome in motores_ambientais.MOTORES else "universal.py")
    prazo = int(timeout_s or config.timeout_simulador())
    caixa = {}

    def alvo():
        try:
            caixa["resultado"] = funcao(pergunta, dict(parametros or {}))
        except Exception as erro:                   # noqa: BLE001
            caixa["erro"] = "%s: %s" % (type(erro).__name__, erro)

    inicio = time.time()
    thread = threading.Thread(target=alvo, name="sim_%s" % nome, daemon=True)
    thread.start()
    thread.join(prazo)
    duracao = round(time.time() - inicio, 3)
    if thread.is_alive():
        return {"simulador": nome, "estado": "timeout", "resultado": None,
                "erro": "prazo de %ss excedido" % prazo, "duracao_s": duracao,
                "motor": motor}
    if "erro" in caixa:
        return {"simulador": nome, "estado": "erro", "resultado": None,
                "erro": caixa["erro"], "duracao_s": duracao, "motor": motor}
    return {"simulador": nome, "estado": "ok", "resultado": caixa.get("resultado"),
            "erro": None, "duracao_s": duracao, "motor": motor}


def modelo_adsorcao(pergunta: str, parametros: dict = None) -> dict:
    """Isotermas de adsorcao existentes (`modelos_adsorcao_v2`)."""
    modulo = _modulo("modelos_adsorcao_v2")
    if isinstance(modulo, Exception):
        raise MotorIndisponivel("modelos_adsorcao_v2.py: %s" % modulo)
    resultado = modulo.executar_modelo_adsorcao(pergunta or "",
                                                dict(parametros or {}))
    resultado.setdefault("motor", "modelos_adsorcao_v2.executar_modelo_adsorcao")
    return resultado


def isoterma(modelo: str, **parametros) -> dict:
    """Isoterma fechada de `modelos_analiticos_v2` (Langmuir / Freundlich)."""
    modulo = _modulo("modelos_analiticos_v2")
    if isinstance(modulo, Exception):
        raise MotorIndisponivel("modelos_analiticos_v2.py: %s" % modulo)
    nome = (modelo or "").strip().lower()
    if nome == "langmuir":
        saida = modulo.isoterma_langmuir(parametros.get("q_max"),
                                         parametros.get("K_L"),
                                         parametros.get("C_e"))
    elif nome == "freundlich":
        saida = modulo.isoterma_freundlich(parametros.get("K_F"),
                                           parametros.get("n"),
                                           parametros.get("C_e"))
    else:
        raise ValueError("modelo de isoterma desconhecido: %s" % modelo)
    saida["motor"] = "modelos_analiticos_v2.isoterma_%s" % nome
    return saida


_FUNCOES_ANALITICAS = {
    "cinetica_pfo": "cinetica_adsorcao_primeira_ordem",
    "area_esfera": "area_superficie_esfera",
    "decaimento": "decaimento_primeira_ordem",
    "arrhenius": "arrhenius",
}


def modelo_analitico(nome: str, **parametros) -> dict:
    """Chama uma funcao de `modelos_analiticos_v2` pelo nome curto.

    Mapa explicito para nao expor `**kwargs` arbitrarios ao motor:
    `cinetica_pfo`, `area_esfera`, `decaimento`, `arrhenius`.
    """
    modulo = _modulo("modelos_analiticos_v2")
    if isinstance(modulo, Exception):
        raise MotorIndisponivel("modelos_analiticos_v2.py: %s" % modulo)
    chave = (nome or "").strip().lower()
    funcao_nome = _FUNCOES_ANALITICAS.get(chave)
    if funcao_nome is None:
        raise ValueError("funcao analitica desconhecida: %s" % nome)
    funcao = getattr(modulo, funcao_nome, None)
    if funcao is None:
        raise MotorIndisponivel("modelos_analiticos_v2.%s ausente"
                                % funcao_nome)
    saida = funcao(**parametros)
    if isinstance(saida, dict):
        saida.setdefault("motor", "modelos_analiticos_v2.%s" % funcao_nome)
    return saida


def estado_motores() -> dict:
    """Disponibilidade dos modulos do nucleo, sem importar nada pesado."""
    import importlib.util

    nomes = ("universal", "modelos_adsorcao_v2", "modelos_analiticos_v2",
             "pesquisa_cientifica", "bancos_rest", "bases_v5",
             "nucleo_dados", "exportadores")
    estado = {}
    for nome in nomes:
        try:
            estado[nome] = "disponivel" if importlib.util.find_spec(nome) else "ausente"
        except (ImportError, ValueError):
            estado[nome] = "ausente"
    return estado


_UNIDADES = (
    ("mg/g", (r"mg\s*/\s*g\b", r"mg\s*g-?1", r"mg\s*g\^-1")),
    ("m2/g", (r"m2\s*/\s*g\b", r"m\u00b2\s*/\s*g\b", r"m2\s*g-?1")),
    ("mg/L", (r"mg\s*/\s*l\b", r"mg\s*l-?1")),
    ("L/mg", (r"l\s*/\s*mg\b",)),
    ("cmol/kg", (r"cmol\s*/\s*kg", r"meq\s*/\s*100")),
    ("m3/h", (r"m3\s*/\s*h", r"m\u00b3\s*/\s*h")),
    ("kWh/kg", (r"kwh\s*/\s*kg",)),
    ("nm", (r"nm\b",)),
    ("um", (r"um\b", r"\u00b5m\b")),
    ("%", (r"%",)),
)


def _funcao_pesquisa():
    global _FUNCAO_PESQUISA
    if _FUNCAO_PESQUISA is None:
        modulo = _modulo("pesquisa_cientifica")
        if isinstance(modulo, Exception):
            raise MotorIndisponivel("pesquisa_cientifica.py: %s" % modulo)
        _FUNCAO_PESQUISA = modulo.pesquisar
    return _FUNCAO_PESQUISA


def normalizar_unidade(unidade: str) -> str:
    return (str(unidade or "").strip().lower()
            .replace("\u00b2", "2").replace("\u00b5", "u").replace(" ", ""))


def buscar_evidencias(termo: str, bases=None, n: int = 3, max_bases: int = 4,
                      timeout: int = None) -> dict:
    """Busca real nas bases cientificas, com fallback e motivo medido.

    Primeiro `pesquisa_cientifica.pesquisar` (dedup + estado por fonte); se
    esse motor nao estiver utilizavel, cai para `bases_v5.buscar_multibase`.
    """
    prazo = int(timeout or config.timeout_evidencia())
    tentativas = []
    try:
        funcao = _funcao_pesquisa()
        dados = funcao(termo, bases=bases, n=max(1, int(n)),
                       max_bases=max(1, int(max_bases)), salvar=False,
                       timeout=min(prazo, 40))
        itens = dados.get("itens") or []
        if itens or dados.get("estado") == "OK":
            return {"motor": "pesquisa_cientifica.pesquisar",
                    "estado": dados.get("estado") or ("OK" if itens else "VAZIO"),
                    "termo": termo, "itens": itens,
                    "falhas": dados.get("falhas") or {},
                    "totais": dados.get("totais") or {},
                    "duplicados": dados.get("duplicados") or 0}
        tentativas.append("pesquisa_cientifica: %s (%s)"
                          % (dados.get("estado"), dados.get("motivo", "")))
    except Exception as erro:                       # noqa: BLE001
        tentativas.append("pesquisa_cientifica: %s: %s"
                          % (type(erro).__name__, erro))

    modulo = _modulo("bases_v5")
    if not isinstance(modulo, Exception):
        try:
            brutos = modulo.buscar_multibase(termo) or []
            itens = []
            for bruto in brutos:
                if not isinstance(bruto, dict):
                    continue
                itens.append({
                    "titulo": bruto.get("titulo", ""),
                    "resumo": bruto.get("resumo", ""),
                    "link": bruto.get("link", ""),
                    "ano": bruto.get("ano"),
                    "fonte": bruto.get("fonte", ""),
                    "base": bruto.get("fonte", ""),
                    "tipo": bruto.get("tipo", ""),
                    "autores": bruto.get("autores") or [],
                    "doi": "",
                })
            return {"motor": "bases_v5.buscar_multibase",
                    "estado": "OK" if itens else "VAZIO", "termo": termo,
                    "itens": itens, "falhas": {},
                    "totais": {"bases": len(itens), "itens": len(itens)},
                    "duplicados": 0, "tentativas": tentativas}
        except Exception as erro:                   # noqa: BLE001
            tentativas.append("bases_v5: %s: %s" % (type(erro).__name__, erro))
    else:
        tentativas.append("bases_v5: %s" % modulo)

    return {"motor": "indisponivel", "estado": "FALHOU", "termo": termo,
            "itens": [], "falhas": {"motores": tentativas},
            "totais": {"bases": 0, "itens": 0}, "duplicados": 0}


def fontes() -> dict:
    """Inventario das fontes/bases disponiveis no ambiente."""
    saida = {}
    modulo = _modulo("bancos_rest")
    if isinstance(modulo, Exception):
        saida["bancos_rest"] = {"erro": str(modulo)}
    else:
        try:
            saida["bancos_rest"] = modulo.saude()
        except Exception as erro:                   # noqa: BLE001
            saida["bancos_rest"] = {"erro": str(erro)}
    modulo = _modulo("bases_v5")
    if isinstance(modulo, Exception):
        saida["bases_v5"] = {"erro": str(modulo)}
    else:
        try:
            saida["bases_v5"] = modulo.info_bases()
        except Exception as erro:                   # noqa: BLE001
            saida["bases_v5"] = {"erro": str(erro)}
    return saida


def extrair_medidas(texto: str) -> list:
    """Numeros com unidade no texto (titulo/resumo de evidencia)."""
    conteudo = str(texto or "")
    achados, vistos = [], set()
    for unidade, padroes in _UNIDADES:
        for padrao in padroes:
            regex = r"(-?\d+(?:[.,]\d+)?)\s*(?:%s)" % padrao
            for achado in re.finditer(regex, conteudo, re.IGNORECASE):
                try:
                    valor = float(achado.group(1).replace(",", "."))
                except ValueError:
                    continue
                chave = (round(valor, 6), unidade, achado.start())
                if chave in vistos:
                    continue
                vistos.add(chave)
                achados.append({
                    "valor": valor, "unidade": unidade,
                    "trecho": conteudo[max(0, achado.start() - 60):
                                       achado.end() + 60].strip(),
                })
    return achados


def comparar_com_literatura(valor, unidade: str, itens, tolerancia: float = 0.2,
                            maximo: int = 5) -> list:
    """Compara um valor calculado com os numeros achados nas evidencias."""
    try:
        alvo = float(valor)
    except (TypeError, ValueError):
        return []
    unidade_alvo = normalizar_unidade(unidade)
    comparacoes = []
    for item in itens or []:
        if not isinstance(item, dict):
            continue
        texto = "%s %s" % (item.get("titulo") or "", item.get("resumo") or "")
        for medida in extrair_medidas(texto):
            if normalizar_unidade(medida["unidade"]) != unidade_alvo:
                continue
            if medida["valor"] == 0:
                continue
            desvio = abs(alvo - medida["valor"]) / abs(medida["valor"])
            if desvio <= tolerancia:
                veredito = "concordante"
            elif desvio <= 0.5:
                veredito = "proximo"
            else:
                veredito = "divergente"
            comparacoes.append({
                "valor_calculado": alvo,
                "unidade": unidade,
                "valor_literatura": medida["valor"],
                "desvio_relativo": round(desvio, 4),
                "veredito": veredito,
                "fonte_literatura": (item.get("titulo") or "")[:300],
                "doi": item.get("doi") or "",
                "ano": item.get("ano"),
                "trecho": medida["trecho"],
            })
    comparacoes.sort(key=lambda c: c["desvio_relativo"])
    return comparacoes[:max(1, int(maximo))]
