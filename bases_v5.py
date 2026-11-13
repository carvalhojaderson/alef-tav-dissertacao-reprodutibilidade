# ============================================================
#   bases_v5.py - Orquestrador de bases cientificas
# ============================================================

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

TIMEOUT = 8
HEADERS = {"User-Agent": "ALEF-TAV/9.0 (mailto:alef@tav.br)"}
# CORE (core.ac.uk) so responde com chave. Guardar o NOME da variavel e' o
# suficiente: sem `CORE_API_KEY` a base fica registrada e marcada como inativa
# (`funcional = False`), em vez de sumir do inventario.
CORE_API_KEY = os.environ.get("CORE_API_KEY", "").strip()

BASES_REGISTRY = {}


def _registra(nome, grupo, modo="API"):
    """Decorator para registrar uma base."""
    def deco(fn):
        BASES_REGISTRY[nome] = {
            "fn": fn,
            "grupo": grupo,
            "modo": modo,
            "funcional": True,
        }
        return fn
    return deco


def _get(url, params=None, timeout=TIMEOUT, headers=None):
    try:
        import requests
        h = dict(HEADERS)
        if headers:
            h.update(headers)
        return requests.get(url, params=params, headers=h, timeout=timeout)
    except Exception:
        return None


def _post(url, json_data=None, timeout=TIMEOUT):
    try:
        import requests
        return requests.post(url, json=json_data, headers=HEADERS, timeout=timeout)
    except Exception:
        return None


def _mk(t, r="", l="", a=2024, f="", tp="", autores=None):
    return {
        "titulo": str(t),
        "resumo": str(r),
        "link": str(l),
        "ano": a if isinstance(a, int) else 2024,
        "fonte": f,
        "tipo": tp,
        "autores": autores or [],
    }


# ============================================================
# LITERATURA (6 bases principais)
# ============================================================

@_registra("arxiv", "literatura", "API")
def b_arxiv(q, n=4):
    try:
        import arxiv
        out = []
        for r in arxiv.Client().results(arxiv.Search(query=q, max_results=n)):
            autores = [au.name for au in r.authors] if r.authors else []
            out.append(_mk(r.title, r.summary, r.entry_id,
                           r.published.year, "arXiv", "artigo", autores))
        return out
    except Exception:
        return []


@_registra("core", "literatura", "API")
def b_core(q, n=4):
    """CORE (https://core.ac.uk) — API v3, exige `CORE_API_KEY`.

    Sem a chave a funcao devolve lista vazia e o registro fica `funcional=False`
    (ver abaixo). Nao ha chamada anonima: a API responde 401 sem credencial.
    """
    if not CORE_API_KEY:
        return []
    r = _get("https://api.core.ac.uk/v3/search/works",
             {"q": q, "limit": n},
             headers={"Authorization": "Bearer " + CORE_API_KEY})
    if not r:
        return []
    try:
        resultados = r.json().get("results", [])
    except ValueError:
        return []
    out = []
    for item in resultados:
        ano = item.get("yearPublished")
        links = item.get("links") or []
        link = ""
        if isinstance(links, list) and links:
            primeiro = links[0]
            link = primeiro.get("url", "") if isinstance(primeiro, dict) else str(primeiro)
        autores = [autor.get("name", "") for autor in (item.get("authors") or [])
                   if isinstance(autor, dict)][:5]
        out.append(_mk(item.get("title", ""), item.get("abstract", "") or "",
                       link, ano if isinstance(ano, int) else 2024,
                       "CORE", "artigo", autores))
    return out


# Registrada sempre; ATIVA so com chave. `info_bases()` conta `inativas`.
BASES_REGISTRY["core"]["funcional"] = bool(CORE_API_KEY)


@_registra("pubmed", "literatura", "API")
def b_pubmed(q, n=4):
    r = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
             {"db": "pubmed", "term": q, "retmax": n, "retmode": "json"})
    if not r:
        return []
    ids = r.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    r2 = _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
              {"db": "pubmed", "id": ",".join(ids), "retmode": "json"})
    if not r2:
        return []
    res = r2.json().get("result", {})
    out = []
    for p in ids:
        i = res.get(p, {})
        y = i.get("pubdate", "2024")[:4]
        autores = [au.get("name", "") for au in i.get("authors", [])][:5]
        out.append(_mk(i.get("title", p), "",
                       "https://pubmed.ncbi.nlm.nih.gov/" + p + "/",
                       int(y) if y.isdigit() else 2024,
                       "PubMed", "artigo", autores))
    return out


@_registra("openalex", "literatura", "API")
def b_openalex(q, n=4):
    r = _get("https://api.openalex.org/works",
             {"search": q, "per_page": n, "mailto": "alef@tav.br"})
    if not r:
        return []
    out = []
    for w in r.json().get("results", []):
        autores = [a.get("author", {}).get("display_name", "")
                   for a in w.get("authorships", [])][:5]
        out.append(_mk(w.get("title", ""), "", w.get("id", ""),
                       w.get("publication_year", 2024),
                       "OpenAlex", "artigo", autores))
    return out


@_registra("crossref", "literatura", "API")
def b_crossref(q, n=4):
    r = _get("https://api.crossref.org/works", {"query": q, "rows": n})
    if not r:
        return []
    out = []
    for w in r.json().get("message", {}).get("items", []):
        y = 2024
        try:
            y = w.get("published", {}).get("date-parts", [[2024]])[0][0]
        except Exception:
            pass
        autores = []
        for au in w.get("author", [])[:5]:
            nome = (au.get("given", "") + " " + au.get("family", "")).strip()
            if nome:
                autores.append(nome)
        out.append(_mk(w.get("title", [""])[0] if w.get("title") else "",
                       "", w.get("URL", ""), y,
                       "Crossref", "artigo", autores))
    return out


@_registra("semantic", "literatura", "API")
def b_semantic(q, n=4):
    r = _get("https://api.semanticscholar.org/graph/v1/paper/search",
             {"query": q, "limit": n, "fields": "title,abstract,url,year,authors"})
    if not r:
        return []
    out = []
    for p in r.json().get("data", []):
        autores = [au.get("name", "") for au in p.get("authors", [])][:5]
        out.append(_mk(p.get("title", ""),
                       (p.get("abstract") or "")[:400],
                       p.get("url", ""), p.get("year", 2024),
                       "Semantic", "artigo", autores))
    return out


@_registra("europepmc", "literatura", "API")
def b_europepmc(q, n=4):
    r = _get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
             {"query": q, "format": "json", "pageSize": n})
    if not r:
        return []
    out = []
    for p in r.json().get("resultList", {}).get("result", []):
        autores = []
        aut_str = p.get("authorString", "")
        if aut_str:
            autores = [a.strip() for a in aut_str.split(",")][:5]
        out.append(_mk(p.get("title", ""),
                       (p.get("abstractText") or "")[:400],
                       "https://europepmc.org/article/MED/" + p.get("pmid", ""),
                       int(p.get("pubYear", 2024)),
                       "EuropePMC", "artigo", autores))
    return out


@_registra("doaj", "literatura", "API")
def b_doaj(q, n=4):
    r = _get("https://doaj.org/api/search/articles/" + q, {"pageSize": n})
    if not r:
        return []
    out = []
    for item in r.json().get("results", []):
        b = item.get("bibjson", {})
        link = b["link"][0].get("url", "") if b.get("link") else ""
        autores = [au.get("name", "") for au in b.get("author", [])][:5]
        out.append(_mk(b.get("title", ""),
                       (b.get("abstract") or "")[:300],
                       link, int(b.get("year", 2024)) if b.get("year") else 2024,
                       "DOAJ", "artigo", autores))
    return out


@_registra("zenodo", "dados", "API")
def b_zenodo(q, n=4):
    r = _get("https://zenodo.org/api/records", {"q": q, "size": n})
    if not r:
        return []
    out = []
    for h in r.json().get("hits", {}).get("hits", []):
        m = h.get("metadata", {})
        autores = [c.get("name", "") for c in m.get("creators", [])][:5]
        out.append(_mk(m.get("title", ""),
                       (m.get("description", "") or "")[:200],
                       h.get("links", {}).get("self_html", ""),
                       int(m.get("publication_date", "2024")[:4]),
                       "Zenodo", "dataset", autores))
    return out


@_registra("pubchem", "quimica", "API")
def b_pubchem(q, n=4):
    r = _get("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/" +
             q + "/property/MolecularFormula,MolecularWeight/JSON")
    if not r or r.status_code != 200:
        return []
    return [_mk("CID " + str(p.get("CID", "")),
                "Peso: " + str(p.get("MolecularWeight", "")),
                "https://pubchem.ncbi.nlm.nih.gov/compound/" + str(p.get("CID", "")),
                2024, "PubChem", "quimica")
            for p in r.json().get("PropertyTable", {}).get("Properties", [])[:n]]


@_registra("clinicaltrials", "clinicos", "API")
def b_ct(q, n=4):
    r = _get("https://clinicaltrials.gov/api/v2/studies",
             {"query.term": q, "pageSize": n})
    if not r:
        return []
    out = []
    for s in r.json().get("studies", []):
        p = s.get("protocolSection", {})
        i = p.get("identificationModule", {})
        out.append(_mk(i.get("briefTitle", ""), "",
                       "https://clinicaltrials.gov/study/" + i.get("nctId", ""),
                       2024, "ClinicalTrials", "clinico"))
    return out


@_registra("orcid", "colaboracao", "API")
def b_orcid(q, n=4):
    r = _get("https://pub.orcid.org/v3.0/expanded-search/",
             {"q": q, "rows": n},
             headers={"Accept": "application/json"})
    if not r:
        return []
    out = []
    for p in r.json().get("expanded-result", []):
        name = p.get("credit-name", {}).get("value", "") if p.get("credit-name") else ""
        out.append(_mk(name, "ORCID: " + p.get("orcid-id", ""),
                       "https://orcid.org/" + p.get("orcid-id", ""),
                       2024, "ORCID", "pesquisador", [name] if name else []))
    return out


@_registra("ror", "colaboracao", "API")
def b_ror(q, n=4):
    r = _get("https://api.ror.org/organizations", {"query": q})
    if not r:
        return []
    return [_mk(o.get("name", ""), o.get("country", {}).get("country_name", ""),
                o.get("id", ""), 2024, "ROR", "instituicao")
            for o in r.json().get("items", [])[:n]]


# ============================================================
# ORQUESTRADOR
# ============================================================
def buscar_multibase(pergunta, tema="", relatorio=None):
    """Busca em todas as bases funcionais.

    ``relatorio`` (opcional) e um dict que o CHAMADOR passa para receber quais
    bases falharam. Antes, a excecao de cada base era engolida por
    ``except Exception: pass``, entao uma fonte fora do ar produzia exatamente o
    mesmo resultado de uma fonte sem artigos: o usuario lia "nenhum artigo" sem
    saber que a base estava indisponivel. Retrocompativel: sem ``relatorio`` o
    comportamento e o mesmo de antes.
    """
    q = pergunta
    resultados = {}
    falhas = {}
    funcs = [(n, i["fn"], i["grupo"])
             for n, i in BASES_REGISTRY.items() if i["funcional"]]

    with ThreadPoolExecutor(max_workers=15) as ex:
        futs = {ex.submit(fn, q, 4): (nome, grupo)
                for nome, fn, grupo in funcs}
        for fut in as_completed(futs):
            nome, grupo = futs[fut]
            try:
                r = fut.result() or []
                if r:
                    resultados.setdefault(grupo, []).extend(r)
            except Exception as exc:  # noqa: BLE001
                falhas[nome] = "%s: %s" % (type(exc).__name__, exc)
    if relatorio is not None:
        relatorio.update(falhas)
    return resultados


def contar_bases(dados):
    return {k: len(v) for k, v in dados.items() if isinstance(v, list)}


def info_bases():
    total = len(BASES_REGISTRY)
    func = sum(1 for i in BASES_REGISTRY.values() if i["funcional"])
    grupos = {}
    for nome, info in BASES_REGISTRY.items():
        grupos.setdefault(info["grupo"], []).append(nome)
    return {
        "total": total,
        "funcionais": func,
        "inativas": total - func,
        "grupos": grupos,
    }


if __name__ == "__main__":
    print("Total de bases:", len(BASES_REGISTRY))
    for nome, info in BASES_REGISTRY.items():
        print("  -", nome, "(" + info["grupo"] + ")")
    print()
    print("Testando arxiv...")
    r = b_arxiv("diamond", 2)
    for x in r:
        print("  -", x["titulo"][:60])
# 10/06/2026 13:14:58

# 10/06/2026 13:17:05

# 10/06/2026 13:29:22
