"""Camada REAL de bases cientificas e de dados da ALEF-TAV.

Substitui os 109 stubs `def b_x(q, n=5): return []` de `bancos_completos.py`
por consulta HTTP de verdade, com estado explicito por base:

    OK        -> devolveu itens
    VAZIO     -> endpoint respondeu 200 sem itens para a consulta
    FALHOU    -> rede/HTTP/limite de taxa (o motivo vai junto)
    BLOQUEADA -> exige credencial que nao esta no ambiente (nome da variavel)
    SEM_API   -> a fonte existe, mas nao publica API de busca (so HTML/pago)

Duas formas de adaptador, ambas testaveis sem rede (monkeypatch de
`_requisitar`):

* declarativa (`Base`): URL, parametros com `{q}`/`{n}`, caminho dos itens e
  dos campos (notacao `a.b.0.c`);
* funcao (`Base.fn`): para as APIs de duas etapas (esearch -> esummary).

Regra de honestidade: nada devolve lista vazia escondendo falha. Quem chama
recebe `Resultado.estado` e `Resultado.motivo`.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

TIMEOUT_PADRAO = 15.0
TENTATIVAS = 2
PAUSA_RETENTATIVA = 0.8
UA = "ALEF-TAV/1.0 (plataforma de pesquisa; +https://alef-tav.local)"
STATUS_REPETIVEIS = {429, 500, 502, 503, 504}

# Prazo de CONEXAO separado do prazo de leitura. Medicao de 02/11/2026: SIMBAD
# gastou 67,6 s porque host inacessivel consome o timeout inteiro duas vezes.
# Com 8 s de conexao a mesma falha custa ~16 s e o motivo fica explicito.
CONECTAR_PADRAO = 8.0

# Circuit breaker: base que falha repetidamente deixa de ser tentada por um
# periodo. Sem isso, uma busca multi-base paga timeout em cada base quebrada
# toda vez. Limiares vem do ambiente (teste e operacao precisam variar).
FALHAS_PARA_ABRIR = int(os.environ.get("ALEF_BANCO_FALHAS_LIMITE", "3"))
COOLDOWN_CIRCUITO = float(os.environ.get("ALEF_BANCO_COOLDOWN_S", "300"))
_CIRCUITO: Dict[str, dict] = {}


def circuito_estado(base_id: str) -> dict:
    """Estado do circuito de uma base (aberto = nao insiste agora)."""
    dados = _CIRCUITO.get(base_id)
    if not dados:
        return {"aberto": False, "falhas": 0, "restante_s": 0.0, "motivo": ""}
    restante = max(0.0, float(dados.get("aberto_ate", 0.0)) - time.time())
    return {"aberto": restante > 0, "falhas": int(dados.get("falhas", 0)),
            "restante_s": round(restante, 1), "motivo": dados.get("motivo", "")}


def _registrar_resultado(base_id: str, estado: str, motivo: str = "") -> None:
    """Conta falha de transporte/HTTP e abre o circuito no limite."""
    if estado in ("OK", "VAZIO", "SEM_API", "BLOQUEADA", "INVALIDA"):
        _CIRCUITO.pop(base_id, None)
        return
    dados = _CIRCUITO.setdefault(base_id, {"falhas": 0, "aberto_ate": 0.0,
                                           "motivo": ""})
    dados["falhas"] += 1
    dados["motivo"] = (motivo or "")[:200]
    if dados["falhas"] >= FALHAS_PARA_ABRIR:
        dados["aberto_ate"] = time.time() + COOLDOWN_CIRCUITO


def reiniciar_circuitos() -> None:
    """Zera o estado dos circuitos (usado por teste e por reinicio manual)."""
    _CIRCUITO.clear()


def circuitos() -> Dict[str, dict]:
    """Fotografia dos circuitos, para diagnostico/API."""
    return {base: circuito_estado(base) for base in list(_CIRCUITO)}



class BaseDesconhecida(KeyError):
    """Pedido de base que nao esta no registro."""


class BaseIndisponivel(RuntimeError):
    """A base existe, mas nesta execucao nao respondeu."""

    def __init__(self, base: str, motivo: str, status: Optional[int] = None):
        super().__init__(f"{base}: {motivo}")
        self.base = base
        self.motivo = motivo
        self.status = status


class ConsultaInvalida(ValueError):
    """A base funciona, mas o formato da consulta nao serve para ela.

    Exemplo medido: BCB SGS indexa por codigo de serie numerico (433 = IPCA),
    nao por texto livre. Isso e' uso incorreto, nao falha da fonte.
    """


@dataclass
class Resultado:
    """Saida de uma consulta: itens + estado medido, nunca um [] mudo."""

    base: str
    itens: List[dict] = field(default_factory=list)
    segundos: float = 0.0
    estado: str = "OK"
    motivo: str = ""
    requisito: str = ""
    http: Optional[int] = None

    def dicionario(self) -> dict:
        return {
            "base": self.base,
            "itens": self.itens,
            "total": len(self.itens),
            "segundos": round(self.segundos, 3),
            "estado": self.estado,
            "motivo": self.motivo,
            "requisito": self.requisito,
            "http": self.http,
        }


@dataclass
class Base:
    """Descricao declarativa de uma fonte consultavel por HTTP."""

    id: str
    nome: str
    categoria: str
    url: str = ""
    metodo: str = "GET"
    params: Dict[str, Any] = field(default_factory=dict)
    corpo: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    chave: Optional[str] = None
    chave_header: str = ""
    chave_prefixo: str = ""
    chave_opcional: str = ""
    vazio_em_404: bool = False
    itens: str = ""
    unico: bool = False
    titulo: str = "title"
    link: str = ""
    link_tpl: str = ""
    ano: str = ""
    resumo: str = ""
    nota: str = ""
    exemplo: str = ""
    fn: Optional[Callable] = None
    espelhos: List[str] = field(default_factory=list)

    @property
    def consultavel(self) -> bool:
        return bool(self.fn or self.url)


def _requisitar(metodo: str, url: str, params: Optional[dict] = None,
                corpo: Optional[dict] = None, headers: Optional[dict] = None,
                timeout: float = TIMEOUT_PADRAO):
    """HTTP com UA, prazo e uma retentativa em 429/5xx. Devolve a resposta.

    O prazo vai como tupla `(conexao, leitura)`: sem isso, host que nao aceita
    conexao consome o orcamento inteiro e a falha demora ~60 s (medido no SIMBAD
    em 02/11/2026). A espera entre tentativas dobra (backoff), limitada a duas
    tentativas — retry infinito em fonte fora do ar so custaria tempo.
    """
    import requests

    cabecalhos = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        cabecalhos.update(headers)
    prazo = (min(CONECTAR_PADRAO, float(timeout)), float(timeout))
    ultimo = None
    for tentativa in range(TENTATIVAS):
        ultimo = requests.request(metodo, url, params=params, json=corpo,
                                  headers=cabecalhos, timeout=prazo)
        if ultimo.status_code not in STATUS_REPETIVEIS or tentativa == TENTATIVAS - 1:
            return ultimo
        time.sleep(PAUSA_RETENTATIVA * (2 ** tentativa))
    return ultimo



def _valor(obj: Any, caminho: str) -> Any:
    """Le `a.b.0.c` de um dicionario/lista aninhado (None se nao existir)."""
    if not caminho:
        return obj
    atual = obj
    for parte in caminho.split("."):
        if atual is None:
            return None
        if isinstance(atual, list):
            try:
                atual = atual[int(parte)]
            except (ValueError, IndexError):
                return None
        elif isinstance(atual, dict):
            atual = atual.get(parte)
        else:
            return None
    return atual


def _texto(obj: Any, caminho: str) -> str:
    valor = _valor(obj, caminho)
    if valor is None:
        return ""
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False)[:600]
    return str(valor)


def _ano(valor: Any) -> Optional[int]:
    if valor is None:
        return None
    if isinstance(valor, int):
        return valor
    m = re.search(r"(1[6-9]\d\d|20\d\d)", str(valor))
    return int(m.group(1)) if m else None


def _interpolar(valor: Any, q: str, n: int) -> Any:
    """Troca {q}/{n}; mantem o tipo int quando o valor e' so `{n}`."""
    if isinstance(valor, str):
        if valor == "{n}":
            return n
        if valor == "{q}":
            return q
        return valor.replace("{q}", q).replace("{n}", str(n))
    if isinstance(valor, dict):
        return {k: _interpolar(v, q, n) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_interpolar(v, q, n) for v in valor]
    return valor


def _normalizar(base: Base, item: Any) -> dict:
    """Converte um registro bruto da API no dicionario padrao do projeto."""
    alvo = item if isinstance(item, dict) else {"_valor": item}
    titulo = _texto(alvo, base.titulo) if isinstance(item, dict) else str(item)
    if not titulo and base.unico:
        titulo = _texto(alvo, base.titulo)
    link = _texto(alvo, base.link) if base.link else ""
    if base.link_tpl and link:
        link = base.link_tpl.format(id=link)
    item_final = {
        "titulo": titulo[:300],
        "resumo": _texto(alvo, base.resumo)[:600] if base.resumo else "",
        "link": link,
        "ano": _ano(_valor(alvo, base.ano)) if base.ano else None,
        "fonte": base.nome,
        "categoria": base.categoria,
        "base": base.id,
    }
    if not item_final["titulo"]:
        item_final["titulo"] = link or f"{base.nome}: registro sem titulo"
    return item_final


def _declarativo_em(base: Base, molde: str, q: str, n: int,
                    timeout: float) -> List[dict]:
    url = molde.replace("{q}", quote(q, safe=""))
    params = _interpolar(base.params, q, n) or None
    corpo = _interpolar(base.corpo, q, n) or None
    cabecalhos = dict(base.headers) if base.headers else {}
    for variavel in (base.chave, base.chave_opcional):
        if base.chave_header and variavel and os.environ.get(variavel):
            cabecalhos[base.chave_header] = (base.chave_prefixo
                                             + os.environ[variavel])
    resposta = _requisitar(base.metodo, url, params=params, corpo=corpo,
                           headers=cabecalhos or None, timeout=timeout)
    if resposta.status_code == 404 and base.vazio_em_404:
        return []
    if resposta.status_code >= 400:
        raise BaseIndisponivel(base.id, f"HTTP {resposta.status_code}",
                               resposta.status_code)
    try:
        dados = resposta.json()
    except ValueError as exc:
        raise BaseIndisponivel(base.id, f"resposta nao e JSON: {exc}") from exc
    bruto = _valor(dados, base.itens) if base.itens else dados
    if isinstance(bruto, dict):
        bruto = list(bruto.values())
    if base.unico and isinstance(bruto, (str, int, float)):
        bruto = [bruto]
    if not isinstance(bruto, list):
        bruto = []
    return [_normalizar(base, item) for item in bruto]


def _declarativo(base: Base, q: str, n: int, timeout: float) -> List[dict]:
    """Tenta o endereco principal e, em falha de transporte, os espelhos.

    Medicao de 02/11/2026: `rest.ensembl.org` respondeu em 13,6 s e estourou o
    prazo de 30 s em outra medicao, enquanto `grch37.rest.ensembl.org` respondeu
    em 1,2 s. Espelho so entra quando o erro e' de transporte ou 5xx: 4xx e'
    resposta legitima da fonte e repetir em outro host nao faria sentido.
    """
    candidatos = [base.url] + [espelho for espelho in (base.espelhos or [])
                              if espelho]
    ultimo_erro = None
    for molde in candidatos:
        try:
            return _declarativo_em(base, molde, q, n, timeout)
        except BaseIndisponivel as exc:
            ultimo_erro = exc
            if exc.status is not None and exc.status < 500:
                raise
        except Exception as exc:                   # transporte: DNS, TLS, prazo
            ultimo_erro = exc
        continue
    if isinstance(ultimo_erro, BaseIndisponivel):
        raise ultimo_erro
    raise BaseIndisponivel(base.id, "%s: %s" % (type(ultimo_erro).__name__,
                                                ultimo_erro))


def consultar(base_id: str, q: str, n: int = 5,
              timeout: float = TIMEOUT_PADRAO) -> Resultado:
    """Consulta uma base e devolve itens + estado medido (nunca `[]` mudo)."""
    if base_id not in BASES:
        raise BaseDesconhecida(base_id)
    q = (q or "").strip()
    if not q:
        raise ValueError("consulta vazia")
    base = BASES[base_id]
    if not base.consultavel:
        return Resultado(base=base_id, estado="SEM_API",
                         motivo=base.nota or "fonte sem API de busca")
    if base.chave and not os.environ.get(base.chave):
        return Resultado(base=base_id, estado="BLOQUEADA",
                         requisito=base.chave,
                         motivo=f"credencial {base.chave} ausente do ambiente")
    estado_circuito = circuito_estado(base_id)
    if estado_circuito["aberto"]:
        return Resultado(
            base=base_id, estado="CIRCUITO_ABERTO",
            motivo=("circuito aberto apos %d falha(s): %s (nova tentativa em %.0fs)"
                    % (estado_circuito["falhas"],
                       estado_circuito["motivo"] or "sem detalhe",
                       estado_circuito["restante_s"])))
    inicio = time.perf_counter()
    resultado = None
    try:
        if base.fn is not None:
            itens = list(base.fn(q, n, timeout) or [])
        else:
            itens = _declarativo(base, q, n, timeout)
    except ConsultaInvalida as exc:
        resultado = Resultado(base=base_id, segundos=time.perf_counter() - inicio,
                              estado="INVALIDA", motivo=str(exc))
    except BaseIndisponivel as exc:
        resultado = Resultado(base=base_id, segundos=time.perf_counter() - inicio,
                              estado="FALHOU", motivo=exc.motivo, http=exc.status)
    except Exception as exc:  # rede, DNS, TLS, parser: tudo vira estado medido
        resultado = Resultado(base=base_id, segundos=time.perf_counter() - inicio,
                              estado="FALHOU",
                              motivo=f"{type(exc).__name__}: {exc}"[:300])
    if resultado is None:
        segundos = time.perf_counter() - inicio
        for item in itens:
            item.setdefault("fonte", base.nome)
            item.setdefault("categoria", base.categoria)
            item.setdefault("base", base.id)
        itens = itens[:n]
        resultado = Resultado(base=base_id, itens=itens, segundos=segundos,
                              estado="OK" if itens else "VAZIO")
    _registrar_resultado(base_id, resultado.estado, resultado.motivo)
    return resultado


def estado_bancos() -> List[dict]:
    """Inventario consultavel pela API/UI: o que esta pronto, bloqueado, sem API."""
    saida = []
    for base in BASES.values():
        if not base.consultavel:
            estado = "SEM_API"
        elif base.chave and not os.environ.get(base.chave):
            estado = "BLOQUEADA"
        else:
            estado = "PRONTA"
        saida.append({
            "id": base.id,
            "nome": base.nome,
            "categoria": base.categoria,
            "estado": estado,
            "requisito": base.chave or "",
            "exemplo": base.exemplo,
            "nota": base.nota,
        })
    return sorted(saida, key=lambda x: (x["categoria"], x["id"]))


def saude() -> dict:
    """Contagem por estado e por categoria (para /api/bancos/saude)."""
    inventario = estado_bancos()
    por_estado: Dict[str, int] = {}
    por_categoria: Dict[str, Dict[str, int]] = {}
    for item in inventario:
        por_estado[item["estado"]] = por_estado.get(item["estado"], 0) + 1
        cat = por_categoria.setdefault(item["categoria"], {})
        cat[item["estado"]] = cat.get(item["estado"], 0) + 1
    return {
        "total": len(inventario),
        "por_estado": por_estado,
        "por_categoria": por_categoria,
        "prontas": sorted(i["id"] for i in inventario
                          if i["estado"] == "PRONTA"),
    }
def _item(titulo: str, link: str = "", ano: Any = None, resumo: str = "") -> dict:
    return {"titulo": (titulo or "")[:300], "link": link or "",
            "ano": _ano(ano), "resumo": (resumo or "")[:600]}


def _f_arxiv(q: str, n: int, timeout: float) -> List[dict]:
    """Atom XML do arXiv (o pacote `arxiv` existe, mas a API e' mais direta)."""
    import xml.etree.ElementTree as ET

    url = "http://export.arxiv.org/api/query"
    r = _requisitar("GET", url, params={"search_query": f"all:{q}",
                                        "max_results": n}, timeout=timeout)
    if r.status_code >= 400:
        raise BaseIndisponivel("arxiv", f"HTTP {r.status_code}", r.status_code)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    raiz = ET.fromstring(r.content)
    saida = []
    for entrada in raiz.findall("a:entry", ns):
        titulo = (entrada.findtext("a:title", "", ns) or "").strip().replace("\n", " ")
        link = entrada.findtext("a:id", "", ns)
        publicado = entrada.findtext("a:published", "", ns)
        resumo = (entrada.findtext("a:summary", "", ns) or "").strip()
        saida.append(_item(titulo, link, publicado, resumo))
    return saida


def _f_ncbi_pubmed(q: str, n: int, timeout: float) -> List[dict]:
    """E-utilities em duas etapas: esearch (ids) -> esummary (titulos)."""
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    r1 = _requisitar("GET", f"{base}/esearch.fcgi",
                     params={"db": "pubmed", "term": q, "retmax": n,
                             "retmode": "json"}, timeout=timeout)
    if r1.status_code >= 400:
        raise BaseIndisponivel("pubmed", f"esearch HTTP {r1.status_code}",
                               r1.status_code)
    ids = _valor(r1.json(), "esearchresult.idlist") or []
    if not ids:
        return []
    r2 = _requisitar("GET", f"{base}/esummary.fcgi",
                     params={"db": "pubmed", "id": ",".join(ids),
                             "retmode": "json"}, timeout=timeout)
    if r2.status_code >= 400:
        raise BaseIndisponivel("pubmed", f"esummary HTTP {r2.status_code}",
                               r2.status_code)
    resultado = _valor(r2.json(), "result") or {}
    saida = []
    for pmid in ids:
        reg = resultado.get(pmid) or {}
        saida.append(_item(reg.get("title", f"PubMed {pmid}"),
                           f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                           reg.get("pubdate")))
    return saida


def _f_pubchem(q: str, n: int, timeout: float) -> List[dict]:
    """PUG REST: nome -> propriedades. A consulta usa a primeira palavra."""
    alvo = (q.split() or [q])[0]
    url = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
           f"{quote(alvo, safe='')}/property/MolecularFormula,MolecularWeight,"
           "Title,IUPACName/JSON")
    r = _requisitar("GET", url, params={"name_type": "word"}, timeout=timeout)
    if r.status_code == 404:
        return []
    if r.status_code >= 400:
        raise BaseIndisponivel("pubchem", f"HTTP {r.status_code}", r.status_code)
    props = _valor(r.json(), "PropertyTable.Properties") or []
    saida = []
    for reg in props[:n]:
        cid = reg.get("CID", "")
        titulo = reg.get("Title") or reg.get("IUPACName") or f"CID {cid}"
        resumo = "formula={} peso={}".format(reg.get("MolecularFormula", "?"),
                                             reg.get("MolecularWeight", "?"))
        saida.append(_item(titulo,
                           f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                           None, resumo))
    return saida


def _f_ncbi_gene(q: str, n: int, timeout: float) -> List[dict]:
    """NCBI Gene: esearch (ids) -> esummary (nome, descricao, organismo)."""
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    r1 = _requisitar("GET", f"{base}/esearch.fcgi",
                     params={"db": "gene", "term": q, "retmax": n,
                             "retmode": "json"}, timeout=timeout)
    if r1.status_code >= 400:
        raise BaseIndisponivel("ncbi_eutils",
                               f"esearch HTTP {r1.status_code}", r1.status_code)
    ids = _valor(r1.json(), "esearchresult.idlist") or []
    if not ids:
        return []
    r2 = _requisitar("GET", f"{base}/esummary.fcgi",
                     params={"db": "gene", "id": ",".join(ids),
                             "retmode": "json"}, timeout=timeout)
    if r2.status_code >= 400:
        raise BaseIndisponivel("ncbi_eutils",
                               f"esummary HTTP {r2.status_code}", r2.status_code)
    resultado = _valor(r2.json(), "result") or {}
    saida = []
    for gid in ids:
        reg = resultado.get(gid) or {}
        resumo = " ".join(x for x in [reg.get("description", ""),
                                      reg.get("organism", {}).get("scientificname", "")]
                          if x)
        saida.append(_item(reg.get("name", f"Gene {gid}"),
                           f"https://www.ncbi.nlm.nih.gov/gene/{gid}",
                           None, resumo))
    return saida


def _f_bcb_serie(q: str, n: int, timeout: float) -> List[dict]:
    """BCB SGS: `q` e' o codigo da serie (ex.: 433 = IPCA)."""
    codigo = re.sub(r"\D", "", q)
    if not codigo:
        raise ConsultaInvalida(
            "informe o codigo SGS da serie (ex.: 433 para IPCA)")
    url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}"
           f"/dados/ultimos/{n}")
    r = _requisitar("GET", url, params={"formato": "json"}, timeout=timeout)
    if r.status_code >= 400:
        raise BaseIndisponivel("bcb", f"HTTP {r.status_code}", r.status_code)
    saida = []
    for reg in (r.json() or [])[:n]:
        saida.append(_item(f"SGS {codigo} em {reg.get('data', '')}",
                           f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados",
                           reg.get("data"), f"valor={reg.get('valor')}"))
    return saida


def _f_patentsview(q: str, n: int, timeout: float) -> List[dict]:
    """PatentsView v1 (exige PATENTSVIEW_API_KEY no cabecalho X-Api-Key)."""
    corpo = {"q": {"_text_any": {"patent_title": q}},
             "f": ["patent_id", "patent_title", "patent_date"],
             "o": {"per_page": n}}
    r = _requisitar("POST", "https://search.patentsview.org/api/v1/patent/",
                    corpo=corpo,
                    headers={"X-Api-Key": os.environ.get("PATENTSVIEW_API_KEY", "")},
                    timeout=timeout)
    if r.status_code >= 400:
        raise BaseIndisponivel("patentsview", f"HTTP {r.status_code}",
                               r.status_code)
    saida = []
    for reg in _valor(r.json(), "patents") or []:
        pid = reg.get("patent_id", "")
        saida.append(_item(reg.get("patent_title", ""),
                           f"https://patents.google.com/patent/US{pid}",
                           reg.get("patent_date")))
    return saida


def _f_orcid(q: str, n: int, timeout: float) -> List[dict]:
    """ORCID expanded-search: nome -> pesquisadores com ORCID."""
    r = _requisitar("GET", "https://pub.orcid.org/v3.0/expanded-search/",
                    params={"q": q, "rows": n},
                    headers={"Accept": "application/json"}, timeout=timeout)
    if r.status_code >= 400:
        raise BaseIndisponivel("orcid", f"HTTP {r.status_code}", r.status_code)
    saida = []
    for reg in _valor(r.json(), "expanded-result") or []:
        nome = " ".join(x for x in [reg.get("given-names"),
                                    reg.get("family-names")] if x).strip()
        oid = reg.get("orcid-id", "")
        inst = reg.get("institution-name") or []
        saida.append(_item(nome or oid, f"https://orcid.org/{oid}", None,
                           ", ".join(inst)[:200]))
    return saida


def _f_simbad(q: str, n: int, timeout: float) -> List[dict]:
    """SIMBAD via TAP (ADQL) em formato JSON."""
    consulta = ("SELECT TOP {} main_id, ra, dec FROM basic "
                "WHERE main_id LIKE '%{}%'".format(n, q.replace("'", "")))
    r = _requisitar("GET", "https://simbad.cds.unistra.fr/simbad/sim-tap/sync",
                    params={"request": "doQuery", "lang": "adql",
                            "format": "json", "query": consulta},
                    timeout=timeout)
    if r.status_code >= 400:
        raise BaseIndisponivel("simbad", f"HTTP {r.status_code}", r.status_code)
    saida = []
    for linha in _valor(r.json(), "data") or []:
        if not linha:
            continue
        nome = str(linha[0]).strip()
        saida.append(_item(nome,
                           "https://simbad.cds.unistra.fr/simbad/sim-id?Ident="
                           + quote(nome, safe=""), None,
                           "ra={} dec={}".format(linha[1], linha[2])))
    return saida


def _f_aflow(q: str, n: int, timeout: float) -> List[dict]:
    """AFLUX devolve texto com cabecalho '#'; converte em registros."""
    url = f"https://aflow.org/API/aflux/?species({quote(q, safe='')}),nspecies(1)"
    r = _requisitar("GET", url, headers={"Accept": "text/plain"},
                    timeout=timeout)
    if r.status_code >= 400:
        raise BaseIndisponivel("aflow", f"HTTP {r.status_code}", r.status_code)
    linhas = [l.strip() for l in r.text.splitlines() if l.strip()]
    if not linhas:
        return []
    cabecalho, dados = None, []
    for linha in linhas:
        if linha.startswith("#"):
            cabecalho = [c.strip() for c in linha.lstrip("#").split(",")]
            continue
        dados.append(linha)
    saida = []
    for linha in dados[:n]:
        partes = linha.split(",")
        reg = dict(zip(cabecalho or [], partes))
        auid = reg.get("auid") or (partes[0] if partes else "")
        saida.append(_item(f"AFLOW {auid}",
                           f"https://aflow.org/material/?id={auid}",
                           None, linha[:300]))
    return saida


def _b(**kw: Any) -> Base:
    base = Base(**kw)
    BASES[base.id] = base
    return base


BASES: Dict[str, Base] = {}

# ------------------------------------------------------------------ artigos
_b(id="openalex", nome="OpenAlex", categoria="artigos",
   url="https://api.openalex.org/works",
   params={"search": "{q}", "per_page": "{n}"},
   itens="results", titulo="title", link="id", ano="publication_year",
   nota="catalogo aberto da scholarly graph (sem chave)")
_b(id="crossref", nome="Crossref", categoria="artigos",
   url="https://api.crossref.org/works",
   params={"query": "{q}", "rows": "{n}"},
   itens="message.items", titulo="title.0", link="DOI",
   ano="issued.date-parts.0.0", link_tpl="https://doi.org/{id}",
   nota="registro de DOI; em producao o polite pool pede e-mail")
_b(id="europepmc", nome="Europe PMC", categoria="artigos",
   url="https://www.ebi.ac.uk/europepmc/webservices/rest/search",
   params={"query": "{q}", "format": "json", "pageSize": "{n}"},
   itens="resultList.result", titulo="title", link="pmid",
   link_tpl="https://europepmc.org/article/MED/{id}", ano="pubYear",
   resumo="abstractText")
_b(id="pubmed", nome="PubMed", categoria="artigos", fn=_f_ncbi_pubmed,
   nota="E-utilities em duas etapas (esearch + esummary)")
_b(id="arxiv", nome="arXiv", categoria="artigos", fn=_f_arxiv,
   nota="Atom XML; preprints de fisica/matematica/CS")
_b(id="doaj", nome="DOAJ", categoria="artigos",
   url="https://doaj.org/api/search/articles/{q}",
   params={"pageSize": "{n}"},
   itens="results", titulo="bibjson.title", link="id",
   link_tpl="https://doaj.org/article/{id}")
_b(id="semantic", nome="Semantic Scholar", categoria="artigos",
   url="https://api.semanticscholar.org/graph/v1/paper/search",
   params={"query": "{q}", "limit": "{n}",
           "fields": "title,abstract,url,year"},
   itens="data", titulo="title", link="url", ano="year", resumo="abstract",
   chave_opcional="SEMANTIC_API_KEY", chave_header="x-api-key",
   nota="sem chave devolve HTTP 429 com frequencia (medido); com "
        "SEMANTIC_API_KEY no ambiente a cota sobe")
_b(id="core", nome="CORE", categoria="artigos",
   url="https://api.core.ac.uk/v3/search/works",
   params={"q": "{q}", "limit": "{n}"},
   itens="results", titulo="title", link="downloadUrl", ano="year",
   chave="CORE_API_KEY", nota="repositorios institucionais; exige chave")
_b(id="inspire", nome="INSPIRE-HEP", categoria="fisica",
   url="https://inspirehep.net/api/literature",
   params={"q": "{q}", "size": "{n}", "fields": "titles,earliest_date"},
   itens="hits.hits", titulo="metadata.titles.0.title", link="id",
   link_tpl="https://inspirehep.net/literature/{id}", ano="metadata.earliest_date")
_b(id="pubchem", nome="PubChem", categoria="quimica", fn=_f_pubchem,
   nota="PUG REST por nome de composto")
_b(id="simbad", nome="SIMBAD", categoria="astronomia", fn=_f_simbad,
   nota="TAP/ADQL por identificador; inacessivel deste host em 31/10/2026 "
        "(ConnectTimeout em simbad.cds.unistra.fr e simbad.u-strasbg.fr)")
_b(id="pdb", nome="PDB (RCSB)", categoria="biologia",
   metodo="POST", url="https://search.rcsb.org/rcsbsearch/v2/query",
   corpo={"query": {"type": "terminal", "service": "full_text",
                    "parameters": {"value": "{q}"}},
          "return_type": "entry",
          "request_options": {"paginate": {"start": 0, "rows": "{n}"}}},
   itens="result_set", titulo="identifier", link="identifier",
   link_tpl="https://www.rcsb.org/structure/{id}",
   nota="busca textual de estruturas proteicas")



# ----------------------------------------------------------------- patentes
_b(id="patentsview", nome="PatentsView (USPTO)", categoria="patentes",
   fn=_f_patentsview, chave="PATENTSVIEW_API_KEY",
   nota="API v1 do USPTO; exige chave")
_b(id="epo", nome="EPO OPS", categoria="patentes",
   chave="EPO_OPS_KEY",
   nota="OPS exige OAuth2 (consumer key + secret) e cota")
_b(id="inpi", nome="INPI", categoria="patentes",
   nota="portal HTML sem API de busca publica")
_b(id="lens", nome="Lens.org", categoria="patentes", chave="LENS_API_TOKEN",
   nota="exige token pago")
_b(id="google_patents", nome="Google Patents", categoria="patentes",
   nota="so via BigQuery (projeto GCP + cobranca); sem endpoint REST")
_b(id="wipo", nome="WIPO PATENTSCOPE", categoria="patentes",
   nota="consulta apenas por formulario HTML")

# -------------------------------------------------------------- integridade
_b(id="retraction", nome="Retraction Watch (via Crossref)",
   categoria="integridade", url="https://api.crossref.org/works",
   params={"query": "{q}", "filter": "update-type:retraction",
           "rows": "{n}"},
   itens="message.items", titulo="title.0", link="DOI",
   link_tpl="https://doi.org/{id}", ano="issued.date-parts.0.0",
   nota="retratacoes via filtro update-type do Crossref (medido: 200)")
_b(id="pubpeer", nome="PubPeer", categoria="integridade",
   nota="sem API publica; consulta por DOI apenas na interface web")

# ---------------------------------------------------------------- clinicos
_b(id="clinicaltrials", nome="ClinicalTrials.gov", categoria="clinicos",
   url="https://clinicaltrials.gov/api/v2/studies",
   params={"query.term": "{q}", "pageSize": "{n}"},
   itens="studies",
   titulo="protocolSection.identificationModule.briefTitle",
   link="protocolSection.identificationModule.nctId",
   link_tpl="https://clinicaltrials.gov/study/{id}",
   resumo="protocolSection.descriptionModule.briefSummary")
_b(id="nih_reporter", nome="NIH RePORTER", categoria="clinicos",
   metodo="POST", url="https://api.reporter.nih.gov/v2/projects/search",
   corpo={"criteria": {"advanced_text_search": {
              "operator": "and", "search_field": "projecttitle",
              "search_text": "{q}"}},
          "limit": "{n}"},
   itens="results", titulo="project_title", link="project_num",
   link_tpl="https://reporter.nih.gov/project-details/{id}")
_b(id="who_ictrp", nome="WHO ICTRP", categoria="clinicos",
   nota="plataforma de busca HTML agregando registros nacionais")

# -------------------------------------------------------------------- dados
_b(id="zenodo", nome="Zenodo", categoria="dados",
   url="https://zenodo.org/api/records",
   params={"q": "{q}", "size": "{n}"},
   itens="hits.hits", titulo="metadata.title", link="links.self_html",
   ano="metadata.publication_date", resumo="metadata.description")
_b(id="figshare", nome="Figshare", categoria="dados", metodo="POST",
   url="https://api.figshare.com/v2/articles/search",
   corpo={"search_for": "{q}", "page_size": "{n}"},
   titulo="title", link="url_public_html", ano="published_date")
_b(id="dryad", nome="Dryad", categoria="dados",
   url="https://datadryad.org/api/v2/search",
   params={"q": "{q}", "per_page": "{n}"},
   itens="_embedded.stash:datasets", titulo="title", link="identifier",
   link_tpl="https://datadryad.org/dataset/doi:{id}")
_b(id="dataone", nome="DataONE", categoria="dados",
   url="https://cn.dataone.org/cn/v2/query/solr/",
   params={"q": "{q}", "wt": "json", "rows": "{n}"},
   itens="response.docs", titulo="title", link="id",
   link_tpl="https://search.dataone.org/view/{id}")
_b(id="re3data", nome="re3data", categoria="dados",
   nota="API lista repositorios por id, sem endpoint de busca textual")

# ------------------------------------------------------- recalls e alertas
_b(id="openfda", nome="openFDA (enforcement)", categoria="recalls",
   url="https://api.fda.gov/drug/enforcement.json",
   params={"search": "{q}", "limit": "{n}"},
   itens="results", titulo="product_description", link="recall_number",
   link_tpl=("https://api.fda.gov/drug/enforcement.json?search="
             "recall_number:%22{id}%22"),
   resumo="reason_for_recall", vazio_em_404=True,
   nota="recalls de medicamentos nos EUA; 404 com NOT_FOUND = sem resultado")
_b(id="cpsc", nome="CPSC (saferproducts)", categoria="recalls",
   url="https://www.saferproducts.gov/RestWebServices/Recall",
   params={"format": "json", "ProductName": "{q}"},
   titulo="Title", link="URL", ano="RecallDate", resumo="Description",
   nota="recalls de produtos de consumo nos EUA (campos Title/URL medidos)")
_b(id="nhtsa", nome="NHTSA", categoria="recalls",
   nota="API exige make/model/year; nao aceita busca textual livre")
_b(id="eu_safety", nome="EU Safety Gate (RAPEX)", categoria="recalls",
   nota="sem API publica; alertas publicados em HTML")

# ------------------------------------------------------ materiais e quimica
_b(id="optimade", nome="OPTIMADE (Materials Project)", categoria="materiais",
   url="https://optimade.materialsproject.org/v1/structures",
   params={"filter": 'elements HAS "{q}"', "page_limit": "{n}"},
   itens="data", titulo="attributes.chemical_formula_reduced", link="id",
   link_tpl="https://materialsproject.org/materials/{id}",
   nota="filtro por SIMBOLO de elemento (ex.: Al, C); texto livre devolve "
        "lista vazia porque a base indexa estrutura, nao assunto")
_b(id="nomad", nome="NOMAD", categoria="materiais",
   metodo="POST", url="https://nomad-lab.eu/prod/v1/api/v1/entries/query",
   corpo={"query": {"results.material.elements": "{q}"},
          "pagination": {"page_size": "{n}"}},
   itens="data", titulo="entry_id", link="entry_id",
   link_tpl="https://nomad-lab.eu/prod/v1/gui/search/entries/entry/id/{id}",
   nota="filtro por elemento quimico (ex.: C); body validado em 31/10/2026")
_b(id="aflow", nome="AFLOW", categoria="materiais", fn=_f_aflow,
   nota="AFLUX: texto com cabecalho; busca por especie quimica")
_b(id="oqmd", nome="OQMD", categoria="materiais",
   url="https://oqmd.org/oqmdapi/formationenergy",
   params={"filter": "element_set={q}", "fields": "name,entry_id,delta_e",
           "limit": "{n}"},
   itens="data", titulo="name", link="entry_id",
   link_tpl="https://oqmd.org/materials/entry/{id}",
   nota="formacao energetica por conjunto de elementos. Medicao de 02/11/2026: "
        "o caminho antigo (/oqml/qmpy) devolveu HTTP 404 e o documentado "
        "(/oqmdapi) devolveu 502, SSLError e ReadTimeout em tentativas "
        "seguidas — instabilidade do servidor, nao do cliente; por isso a base "
        "entra no circuit breaker depois de 3 falhas")
_b(id="materials_project", nome="Materials Project (API v2)",
   categoria="materiais", url="https://api.materialsproject.org/materials/summary/",
   params={"formula": "{q}", "_limit": "{n}"},
   itens="data", titulo="formula_pretty", link="material_id",
   link_tpl="https://materialsproject.org/materials/{id}",
   chave="MP_API_KEY", nota="exige chave da API v2")
_b(id="matbench", nome="Matbench", categoria="materiais",
   nota="benchmark publicado como dataset estatico (sem API de busca)")
_b(id="jarvis", nome="JARVIS-DFT", categoria="materiais",
   nota="dados distribuidos como dataset NIST (sem endpoint de busca)")
_b(id="materials_cloud", nome="Materials Cloud", categoria="materiais",
   nota="AiiDA archive sem endpoint de busca publico")

# ------------------------------------------------------------------ genomica
_b(id="ensembl", nome="Ensembl", categoria="genomica",
   url="https://rest.ensembl.org/xrefs/symbol/homo_sapiens/{q}",
   params={"content-type": "application/json"},
   itens="", titulo="id", link="id",
   link_tpl="https://www.ensembl.org/id/{id}", resumo="type",
   espelhos=["https://grch37.rest.ensembl.org/xrefs/symbol/homo_sapiens/{q}"],
   nota="simbolo de gene humano -> ids Ensembl. Medicao de 02/11/2026: host "
        "principal respondeu em 13,6 s numa consulta e estourou 30 s noutra, "
        "enquanto o espelho GRCh37 respondeu em 1,2 s — por isso o espelho "
        "entra quando o principal falha por transporte")
_b(id="ebi_search", nome="EBI Search (UniProt)", categoria="genomica",
   url="https://www.ebi.ac.uk/ebisearch/ws/rest/uniprot",
   params={"query": "{q}", "format": "json", "size": "{n}"},
   itens="entries", titulo="id", link="id",
   link_tpl="https://www.ebi.ac.uk/ebisearch/search?db=uniprot&query={id}",
   nota="indice EBI Search, dominio uniprot; HTTP 200 medido em 02/11/2026 "
        "(27.108 hits para 'p53'); troque o dominio na URL para consultar "
        "arrayexpress, sra-study, biostudies etc.")
_b(id="ncbi_eutils", nome="NCBI Gene", categoria="genomica", fn=_f_ncbi_gene,
   exemplo="TP53",
   nota="esearch + esummary do banco Gene (nome, descricao e organismo)")
_b(id="ena", nome="ENA (EBI)", categoria="genomica",
   url="https://www.ebi.ac.uk/ena/portal/api/search",
   params={"result": "study", "query": 'study_title="*{q}*"',
           "fields": "study_accession,study_title", "format": "json",
           "limit": "{n}"},
   titulo="study_title", link="study_accession",
   link_tpl="https://www.ebi.ac.uk/ena/browser/view/{id}",
   nota="estudos de sequenciamento; o endpoint portal/api/search devolve "
        "HTTP 500 em 31/10/2026 (falha do servidor, medida em 4 variantes "
        "de sintaxe) — use sra_study como alternativa funcional")
_b(id="sra_study", nome="SRA/ENA studies (EBI Search)", categoria="genomica",
   url="https://www.ebi.ac.uk/ebisearch/ws/rest/sra-study",
   params={"query": "{q}", "format": "json", "size": "{n}"},
   itens="entries", titulo="id", link="id",
   link_tpl="https://www.ebi.ac.uk/ena/browser/view/{id}",
   nota="indice EBI Search de estudos de sequenciamento (dominio sra-study); "
        "alternativa medida quando o portal ENA responde 500")
_b(id="gdc", nome="GDC (NCI)", categoria="genomica",
   url="https://api.gdc.cancer.gov/projects",
   params={"q": "{q}", "size": "{n}"},
   itens="data.hits", titulo="name", link="project_id",
   link_tpl="https://portal.gdc.cancer.gov/projects/{id}",
   nota="Genomic Data Commons: projetos de câncer")
_b(id="ucsc", nome="UCSC Genome Browser", categoria="genomica",
   nota="API de tracks por coordenada; nao ha busca textual de projeto")

# ------------------------------------------------------- dados do governo BR
_b(id="dados_gov", nome="dados.gov.br", categoria="dados_governo_br",
   url="https://dados.gov.br/api/3/action/package_search",
   params={"q": "{q}", "rows": "{n}"},
   itens="result.results", titulo="title", link="name",
   link_tpl="https://dados.gov.br/dados/conjuntos-dados/{id}",
   resumo="notes", chave="DADOS_GOV_TOKEN",
   chave_header="Authorization", chave_prefixo="Bearer ",
   nota="CKAN do portal brasileiro; HTTP 401 medido em 31/10/2026 — passou a "
        "exigir credencial, por isso a base fica BLOQUEADA sem token")
_b(id="bcb", nome="Banco Central (SGS)", categoria="dados_governo_br",
   fn=_f_bcb_serie,
   nota="series temporais por codigo SGS (ex.: 433 = IPCA mensal)")
_b(id="ipeadata", nome="IPEADATA", categoria="dados_governo_br",
   url="https://www.ipeadata.gov.br/api/odata4/Metadados",
   params={"$filter": "startswith(SERNOME,'{q}')", "$top": "{n}"},
   itens="value", titulo="SERNOME", link="SERCODIGO",
   link_tpl="https://www.ipeadata.gov.br/ExibeSerie.aspx?serid={id}",
   nota="OData4 aceita startswith (contains devolve HTTP 400, medido); o "
        "filtro comeca pelo inicio do nome da serie")
_b(id="transferegov", nome="TransfereGov", categoria="dados_governo_br",
   nota="dados servidos por arquivos/portal de download, sem API REST")
_b(id="obrasgov", nome="ObrasGov", categoria="dados_governo_br",
   nota="portal com API em migracao; sem endpoint publico estavel")
_b(id="tesouro", nome="Tesouro Transparente", categoria="dados_governo_br",
   nota="series divulgadas em planilhas e HTML")
_b(id="inde", nome="INDE (Infraestrutura Nacional de Dados Espaciais)",
   categoria="dados_governo_br",
   nota="catalogo geoespacial por servicos WMS/WFS, sem busca textual REST")

# ---------------------------------------------------- dados do governo intl
_b(id="data_gov_us", nome="Data.gov (EUA)", categoria="dados_governo_intl",
   nota="CKAN de catalog.data.gov/data.gov devolveu HTTP 404 em 31/10/2026 "
        "(portal trocou de contrato); sem endpoint estavel, nao ha consulta")
_b(id="data_gov_uk", nome="data.gov.uk", categoria="dados_governo_intl",
   url="https://data.gov.uk/api/3/action/package_search",
   params={"q": "{q}", "rows": "{n}"},
   itens="result.results", titulo="title", link="name",
   link_tpl="https://data.gov.uk/dataset/{id}", resumo="notes")
_b(id="govdata_de", nome="GovData (Alemanha)", categoria="dados_governo_intl",
   url="https://www.govdata.de/ckan/api/3/action/package_search",
   params={"q": "{q}", "rows": "{n}"},
   itens="result.results", titulo="title", link="name",
   link_tpl="https://www.govdata.de/web/guest/suchen/-/details/{id}",
   resumo="notes",
   nota="CKAN alemao; ConnectTimeout medido deste host em 31/10/2026")
_b(id="data_govt_nz", nome="data.govt.nz", categoria="dados_governo_intl",
   nota="CKAN responde 200 com pagina de bloqueio (Incapsula) em 31/10/2026; "
        "WAF impede a consulta automatica")
_b(id="data_gov_sg", nome="data.gov.sg", categoria="dados_governo_intl",
   nota="API v2 exige contrato de colecao; sem busca textual aberta")
_b(id="worldbank", nome="World Bank", categoria="dados_governo_intl",
   url="https://search.worldbank.org/api/v2/wds",
   params={"format": "json", "qterm": "{q}", "rows": "{n}"},
   itens="documents", titulo="display_title", link="docna",
   nota="documentos e indicadores do Banco Mundial")
_b(id="datos_es", nome="datos.gob.es", categoria="dados_governo_intl",
   nota="API apidata usa caminho por titulo exato, sem busca textual livre")
_b(id="datos_co", nome="datos.gov.co", categoria="dados_governo_intl",
   nota="Socrata sem endpoint de busca documentado para texto livre")


# -------------------------------------------------------------- financiamento
_b(id="nsf", nome="NSF Awards", categoria="financiamento",
   url="https://api.nsf.gov/services/v1/awards.json",
   params={"keyword": "{q}", "printFields": "id,title,awardeeName,startDate"},
   itens="response.award", titulo="title", link="id",
   link_tpl="https://www.nsf.gov/awardsearch/showAward?AWD_ID={id}",
   ano="startDate", nota="premios concedidos pela NSF (EUA)")
_b(id="cordis", nome="CORDIS (Horizon)", categoria="financiamento",
   url="https://cordis.europa.eu/api/search/results",
   params={"q": "{q}", "p": "1", "num": "{n}", "srt": "Relevance"},
   itens="payload.results", titulo="title", link="rcn",
   link_tpl="https://cordis.europa.eu/project/id/{id}",
   nota="projetos financiados pela UE (payload.results medido)")
_b(id="finep", nome="FINEP", categoria="financiamento",
   nota="sem API publica de projetos")
_b(id="cnpq", nome="CNPq", categoria="financiamento",
   nota="consulta publica em HTML (chamadas e bolsas)")
_b(id="fapesp", nome="FAPESP", categoria="financiamento",
   nota="BV-FAPESP sem API REST publica")
_b(id="fapemig", nome="FAPEMIG", categoria="financiamento",
   nota="sem API publica")
_b(id="bndes", nome="BNDES", categoria="financiamento",
   nota="dados abertos em arquivos CSV, sem API de busca")
_b(id="embrapii", nome="EMBRAPII", categoria="financiamento",
   nota="sem API publica")
_b(id="rota2030", nome="Rota 2030", categoria="financiamento",
   nota="sem API publica")
_b(id="horizon", nome="Horizon Europe", categoria="financiamento",
   nota="consultas via CORDIS (use a base cordis)")
_b(id="nih_funding", nome="NIH (financiamento)", categoria="financiamento",
   nota="use a base nih_reporter (RePORTER cobre financiamento)")
_b(id="darpa", nome="DARPA", categoria="financiamento",
   nota="sem API publica de programas")
_b(id="gates", nome="Gates Foundation", categoria="financiamento",
   nota="IATI dumps sem endpoint de busca")
_b(id="wellcome", nome="Wellcome Trust", categoria="financiamento",
   nota="Grant data via 360Giving dumps, sem API")
_b(id="erc", nome="ERC", categoria="financiamento",
   nota="projetos no CORDIS; sem API propria de busca")
_b(id="dfg", nome="DFG (GEPRIS)", categoria="financiamento",
   nota="GEPRIS apenas HTML")
_b(id="jsps", nome="JSPS (KAKEN)", categoria="financiamento",
   nota="KAKEN tem API XML; nao implementada nesta rodada")
_b(id="nsfc", nome="NSFC", categoria="financiamento",
   nota="sem API publica")
_b(id="conicet", nome="CONICET", categoria="financiamento",
   nota="sem API publica")
_b(id="conacyt", nome="CONACYT", categoria="financiamento",
   nota="sem API publica")
_b(id="anii", nome="ANII (Uruguai)", categoria="financiamento",
   nota="sem API publica")
_b(id="fondecyt", nome="FONDECYT", categoria="financiamento",
   nota="sem API publica")
_b(id="finep_inovacred", nome="Finep Inovacred", categoria="financiamento",
   nota="sem API publica")

# --------------------------------------------------------------- colaboracao
_b(id="orcid", nome="ORCID", categoria="colaboracao", fn=_f_orcid,
   nota="busca de pesquisadores por nome (expanded-search)")
_b(id="ror", nome="ROR", categoria="colaboracao",
   url="https://api.ror.org/organizations", params={"query": "{q}"},
   itens="items", titulo="name", link="id",
   nota="Research Organization Registry")
_b(id="crossref_funder", nome="Crossref Funder Registry",
   categoria="colaboracao",
   url="https://api.crossref.org/funders", params={"query": "{q}"},
   itens="message.items", titulo="name", link="id",
   link_tpl="https://doi.org/{id}",
   nota="identificadores de agencias financiadoras")
_b(id="openalex_inst", nome="OpenAlex (instituicoes)",
   categoria="colaboracao",
   url="https://api.openalex.org/institutions",
   params={"search": "{q}", "per_page": "{n}"},
   itens="results", titulo="display_name", link="id")
_b(id="grid", nome="GRID", categoria="colaboracao",
   nota="GRID foi descontinuado e fundido ao ROR (use ror)")
_b(id="researchgate", nome="ResearchGate", categoria="colaboracao",
   nota="sem API publica; proibe scraping")
_b(id="google_scholar", nome="Google Scholar", categoria="colaboracao",
   nota="sem API oficial (requer servico pago de terceiros)")
_b(id="dimensions", nome="Dimensions", categoria="colaboracao",
   chave="DIMENSIONS_KEY", nota="exige chave")
_b(id="mendeley", nome="Mendeley", categoria="colaboracao",
   chave="MENDELEY_TOKEN", nota="API OAuth apenas para dados do usuario")
_b(id="academia", nome="Academia.edu", categoria="colaboracao",
   nota="sem API publica")
_b(id="loop", nome="Loop (Frontiers)", categoria="colaboracao",
   nota="plataforma descontinuada pela Frontiers")
_b(id="sciprofiles", nome="SciProfiles (MDPI)", categoria="colaboracao",
   nota="sem API publica")
_b(id="inspire_authors", nome="INSPIRE (autores)", categoria="colaboracao",
   url="https://inspirehep.net/api/authors",
   params={"q": "{q}", "size": "{n}"},
   itens="hits.hits", titulo="metadata.name.value", link="id",
   link_tpl="https://inspirehep.net/authors/{id}")
_b(id="cordis_partners", nome="CORDIS (parceiros)", categoria="colaboracao",
   nota="parceiros vem embutidos na base cordis")


# ------------------------------------------------------------ infraestrutura
_b(id="embl", nome="EMBL-EBI (UniProt)", categoria="infraestrutura",
   url="https://www.ebi.ac.uk/ebisearch/ws/rest/uniprot",
   params={"query": "{q}", "size": "{n}", "format": "json"},
   itens="entries", titulo="id", link="id",
   link_tpl="https://www.ebi.ac.uk/uniprotkb/{id}",
   resumo="acc",
   nota="busca no dominio UniProt do EBI Search (o endpoint /all devolve "
        "dominios, nao entradas; medido)")
_b(id="lnls", nome="LNLS/SIRIUS", categoria="infraestrutura",
   nota="agendamento de feixe por sistema interno; sem API publica")
_b(id="ipen", nome="IPEN", categoria="infraestrutura",
   nota="sem API publica de instalacoes")
_b(id="eln", nome="ELN (generico)", categoria="infraestrutura",
   nota="caderno eletronico e' por fornecedor; sem API unificada")
_b(id="ilab", nome="iLAB", categoria="infraestrutura",
   nota="sistema pago por instituicao")
_b(id="scinote", nome="SciNote", categoria="infraestrutura",
   chave="SCINOTE_TOKEN", nota="exige token da instancia")
_b(id="labarchives", nome="LabArchives", categoria="infraestrutura",
   nota="acesso por contrato institucional")
_b(id="openbis", nome="openBIS", categoria="infraestrutura",
   nota="API por instancia (URL e credencial do laboratorio)")
_b(id="zenodo_labs", nome="Zenodo (laboratorios)", categoria="infraestrutura",
   nota="use a base zenodo comunitario")
_b(id="eu_openscreen", nome="EU-OPENSCREEN", categoria="infraestrutura",
   nota="sem API publica de compostos")
_b(id="instruct", nome="Instruct-ERIC", categoria="infraestrutura",
   nota="catalogo de servicos em HTML")
_b(id="ceric", nome="CERIC-ERIC", categoria="infraestrutura",
   nota="propostas por portal, sem API")

# ------------------------------------------------------ publicacoes abertas
_b(id="openaire", nome="OpenAIRE", categoria="publicacoes",
   fn=lambda q, n, t: _f_openaire(q, n, t),
   nota="agregador europeu (JSON aninhado); responde em 5-25 s, por isso o "
        "prazo padrao de 15 s pode estourar em consultas grandes")
_b(id="scielo", nome="SciELO", categoria="publicacoes",
   nota="busca apenas HTML (search.scielo.org); sem API publica")
_b(id="redalyc", nome="Redalyc", categoria="publicacoes",
   nota="sem API publica")
_b(id="latindex", nome="Latindex", categoria="publicacoes",
   nota="catalogo HTML")
_b(id="base", nome="BASE (Bielefeld)", categoria="publicacoes",
   chave="BASE_API_KEY", nota="exige registro/IP autorizado")
_b(id="jstage", nome="J-STAGE", categoria="publicacoes",
   nota="sem API de busca publica documentada")

# ------------------------------------------------------- seguranca quimica
_b(id="echa", nome="ECHA", categoria="seguranca_quimica",
   nota="dados de substancias por portal HTML")
_b(id="epa_comptox", nome="EPA CompTox", categoria="seguranca_quimica",
   chave="COMPTOX_API_KEY", nota="dashboard-api exige chave")
_b(id="nrc_erns", nome="NRC ERNS", categoria="seguranca_quimica",
   nota="relatorios de derramamento em FOIA/HTML")
_b(id="chemwatch", nome="Chemwatch", categoria="seguranca_quimica",
   nota="base comercial")

# ---------------------------------------------------------------- web search
def _primeiro_texto(obj: Any) -> str:
    """Primeiro texto nao vazio dentro de estrutura aninhada (OpenAIRE)."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        for chave in ("$", "content", "title", "value"):
            if chave in obj:
                achado = _primeiro_texto(obj[chave])
                if achado:
                    return achado
        for valor in obj.values():
            achado = _primeiro_texto(valor)
            if achado:
                return achado
    if isinstance(obj, list):
        for valor in obj:
            achado = _primeiro_texto(valor)
            if achado:
                return achado
    return ""


def _f_openaire(q: str, n: int, timeout: float) -> List[dict]:
    """OpenAIRE: JSON profundamente aninhado; extrai titulo e identificador."""
    r = _requisitar("GET", "https://api.openaire.eu/search/publications",
                    params={"title": q, "size": n, "format": "json"},
                    timeout=timeout)
    if r.status_code >= 400:
        raise BaseIndisponivel("openaire", f"HTTP {r.status_code}",
                               r.status_code)
    resultados = _valor(r.json(), "response.results.result") or []
    if isinstance(resultados, dict):
        resultados = [resultados]
    saida = []
    for reg in resultados[:n]:
        titulo = _primeiro_texto(
            _valor(reg, "metadata.oaf:entity.oaf:result.title"))
        pid = _primeiro_texto(
            _valor(reg, "metadata.oaf:entity.oaf:result.pid"))
        saida.append(_item(titulo or "OpenAIRE", pid))
    return saida


def _f_web(q: str, n: int, timeout: float) -> List[dict]:
    """DuckDuckGo HTML: extrai titulo/link dos resultados organicos."""
    import html as _html

    r = _requisitar("GET", "https://html.duckduckgo.com/html/",
                    params={"q": q}, headers={"Accept": "text/html"},
                    timeout=timeout)
    if r.status_code >= 400:
        raise BaseIndisponivel("web", f"HTTP {r.status_code}", r.status_code)
    saida = []
    for bruto in re.finditer(
            r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            r.text, re.DOTALL):
        if len(saida) >= n:
            break
        link = _html.unescape(bruto.group(1))
        titulo = re.sub(r"<[^>]+>", "", bruto.group(2)).strip()
        if titulo and link:
            saida.append(_item(_html.unescape(titulo), link))
    return saida


_b(id="web", nome="Web (DuckDuckGo HTML)", categoria="web", fn=_f_web,
   nota="busca web aberta via HTML (sem chave)")

# Consulta de exemplo por base: cada fonte indexa um tipo de coisa. O exemplo
# evita confundir "a base nao aceita esse texto" com "a base esta quebrada".
EXEMPLOS = {
    "optimade": "Al", "nomad": "C", "aflow": "H", "oqmd": "Fe",
    "materials_project": "Al2O3", "bcb": "433", "ipeadata": "PIB",
    "ensembl": "BRCA2", "ncbi_eutils": "TP53", "embl": "hemoglobin",
    "pdb": "hemoglobin", "cpsc": "stroller", "openfda": "metformin",
    "nih_reporter": "cancer", "simbad": "Sirius", "patentsview": "battery",
    "worldbank": "water", "data_gov_uk": "health", "govdata_de": "strom",
    "openaire": "graphene", "eni": "graphene",
}
for _id, _exemplo in EXEMPLOS.items():
    if _id in BASES:
        BASES[_id].exemplo = _exemplo

