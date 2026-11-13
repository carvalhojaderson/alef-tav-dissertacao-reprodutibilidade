import os
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

def limpar_resumo(valor):
    """Remove marcacoes HTML simples e normaliza espacos."""
    import html
    import re

    if not valor:
        return ""
    texto = html.unescape(str(valor))
    texto = re.sub(r"<[^>]*>", " ", texto)
    return " ".join(texto.split())


def reconstruir_resumo_openalex(indice):
    """Reconstr?i o resumo a partir do indice invertido do OpenAlex."""
    if not isinstance(indice, dict):
        return ""

    palavras_por_posicao = {}
    for palavra, posicoes in indice.items():
        if not isinstance(posicoes, (list, tuple)):
            continue
        for posicao in posicoes:
            if isinstance(posicao, int) and posicao >= 0:
                palavras_por_posicao[posicao] = str(palavra)

    return " ".join(
        palavras_por_posicao[pos]
        for pos in sorted(palavras_por_posicao)
    )


from fastapi import APIRouter, Query

router = APIRouter(tags=["Fontes academicas"])

EMAIL = os.getenv("UNPAYWALL_EMAIL", "").strip()
TIMEOUT = 8

def requisicao_json(url, headers=None):
    cabecalhos = {
        "User-Agent": "ALEF-TAV/1.0 (academic research)"
    }
    if headers:
        cabecalhos.update(headers)
    req = urllib.request.Request(url, headers=cabecalhos)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))

def requisicao_texto(url, headers=None):
    cabecalhos = {
        "User-Agent": "ALEF-TAV/1.0 (academic research)"
    }
    if headers:
        cabecalhos.update(headers)
    req = urllib.request.Request(url, headers=cabecalhos)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")

def registro(titulo="", autores=None, ano=None, doi="", link="",
             resumo="", fonte="", tipo_documento=""):
    autores_limpos = [
        str(a).strip() for a in (autores or [])
        if str(a or "").strip()
    ]
    return {
        "titulo": titulo or "",
        "autores": autores_limpos,
        "ano": ano,
        "doi": doi or "",
        "link": link or "",
        "resumo": resumo or "",
        "fonte": fonte,
        "tipo_documento": tipo_documento or ""
    }

def buscar_openalex(q, limite):
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({
        "search": q, "per-page": limite
    })
    dados = requisicao_json(url)
    saida = []
    for x in dados.get("results", []):
        doi = (x.get("doi") or "").replace("https://doi.org/", "")
        autores = [
            a.get("author", {}).get("display_name", "")
            for a in x.get("authorships", [])
        ]
        saida.append(registro(
            x.get("title"), autores, x.get("publication_year"),
            doi, x.get("doi") or x.get("id", ""),
            resumo=reconstruir_resumo_openalex(
                x.get("abstract_inverted_index")
            ),
            fonte="OpenAlex",
            tipo_documento=x.get("type", "")
        ))
    return saida

def buscar_crossref(q, limite):
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({
        "query": q, "rows": limite
    })
    dados = requisicao_json(url)
    saida = []
    for x in dados.get("message", {}).get("items", []):
        titulos = x.get("title") or []
        if not titulos or not str(titulos[0]).strip():
            continue
        autores = [
            " ".join(filter(None, [
                str(a.get("given") or "").strip(),
                str(a.get("family") or "").strip()
            ])).strip()
            for a in x.get("author", [])
        ]
        autores = [a for a in autores if a]
        ano = None
        for campo_data in (
            "published", "published-print", "published-online", "issued"
        ):
            metadados_data = x.get(campo_data) or {}
            partes_data = metadados_data.get("date-parts") or []
            if not partes_data or not partes_data[0]:
                continue
            valor_ano = partes_data[0][0]
            try:
                ano = int(valor_ano)
            except (TypeError, ValueError):
                continue
            if 1000 <= ano <= 2100:
                break
            ano = None
        doi = x.get("DOI", "")
        saida.append(registro(
            titulos[0], autores, ano, doi,
            x.get("URL", ""),
            resumo=limpar_resumo(x.get("abstract", "")),
            fonte="Crossref",
            tipo_documento=x.get("type", "")
        ))
    return saida

def buscar_semantic_scholar(q, limite):
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode({
        "query": q,
        "limit": limite,
        "fields": "title,authors,year,abstract,externalIds,url"
    })
    dados = requisicao_json(url)
    saida = []
    for x in dados.get("data", []):
        ids = x.get("externalIds") or {}
        autores = [a.get("name", "") for a in x.get("authors", [])]
        saida.append(registro(
            x.get("title"), autores, x.get("year"),
            ids.get("DOI", ""), x.get("url", ""),
            x.get("abstract", ""), "Semantic Scholar"
        ))
    return saida

def buscar_pubmed(q, limite):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    busca = requisicao_json(base + "esearch.fcgi?" + urllib.parse.urlencode({
        "db": "pubmed", "term": q, "retmax": limite, "retmode": "json"
    }))
    ids = busca.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    xml = requisicao_texto(base + "efetch.fcgi?" + urllib.parse.urlencode({
        "db": "pubmed", "id": ",".join(ids), "retmode": "xml"
    }))
    raiz = ET.fromstring(xml)
    saida = []
    for artigo in raiz.findall(".//PubmedArticle"):
        titulo = artigo.findtext(".//ArticleTitle", default="")
        resumo = " ".join(
            e.text or "" for e in artigo.findall(".//Abstract/AbstractText")
        )
        autores = []
        for a in artigo.findall(".//Author"):
            nome = " ".join(filter(None, [
                a.findtext("ForeName"), a.findtext("LastName")
            ]))
            if nome:
                autores.append(nome)
        # Prioriza a data de publicacao do fasciculo.
        ano_txt = artigo.findtext(".//JournalIssue/PubDate/Year")
        if not ano_txt:
            ano_txt = artigo.findtext(".//PubDate/Year")

        # Alternativa: data eletronica de publicacao, se faltar o ano acima.
        if not ano_txt:
            ano_txt = artigo.findtext(".//ArticleDate/Year")

        # MedlineDate pode conter apenas texto, como "2024 Jan-Feb".
        if not ano_txt:
            medline_date = artigo.findtext(".//PubDate/MedlineDate") or ""
            import re
            correspondencia = re.search(r"\b(?:19|20)\d{2}\b", medline_date)
            if correspondencia:
                ano_txt = correspondencia.group(0)

        ano = int(ano_txt) if ano_txt and ano_txt.isdigit() else None
        tipos_pubmed = [
            (e.text or "").strip()
            for e in artigo.findall(".//PublicationTypeList/PublicationType")
            if (e.text or "").strip()
        ]
        tipo_documento = "; ".join(tipos_pubmed)
        doi = ""
        for ident in artigo.findall(".//ArticleId"):
            if ident.attrib.get("IdType") == "doi":
                doi = ident.text or ""
        pmid = artigo.findtext(".//PMID", default="")
        saida.append(registro(
            titulo, autores, ano,
            doi, "https://pubmed.ncbi.nlm.nih.gov/" + pmid + "/",
            resumo, "PubMed",
            tipo_documento=tipo_documento
        ))
    return saida

def buscar_arxiv(q, limite):
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "search_query": "all:" + q,
        "start": 0, "max_results": limite
    })
    xml = requisicao_texto(url)
    raiz = ET.fromstring(xml)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    saida = []
    for x in raiz.findall("a:entry", ns):
        titulo = " ".join(
            (x.findtext("a:title", default="", namespaces=ns)).split()
        )
        resumo = " ".join(
            (x.findtext("a:summary", default="", namespaces=ns)).split()
        )
        link = x.findtext("a:id", default="", namespaces=ns)
        autores = [
            a.findtext("a:name", default="", namespaces=ns)
            for a in x.findall("a:author", ns)
        ]
        data = x.findtext("a:published", default="", namespaces=ns)
        ano = int(data[:4]) if data[:4].isdigit() else None
        saida.append(registro(
            titulo, autores, ano, "", link, resumo, "arXiv",
            tipo_documento="preprint"
        ))
    return saida

FONTES = {
    "openalex": buscar_openalex,
    "crossref": buscar_crossref,
    "semantic_scholar": buscar_semantic_scholar,
    "pubmed": buscar_pubmed,
    "arxiv": buscar_arxiv
}

@router.get("/api/fontes/status")
def status_fontes():
    return {
        "status": "ok",
        "fontes": list(FONTES.keys()),
        "unpaywall_configurado": bool(EMAIL)
    }

@router.get("/api/fontes/buscar")
def buscar_fontes(
    q: str = Query(..., min_length=2),
    limite: int = Query(5, ge=1, le=20),
    fontes: str = Query("todas")
):
    selecionadas = list(FONTES) if fontes == "todas" else [
        x.strip().lower() for x in fontes.split(",")
        if x.strip().lower() in FONTES
    ]
    resultados = []
    situacao = {}

    for nome in selecionadas:
        try:
            itens = FONTES[nome](q, limite)
            resultados.extend(itens)
            situacao[nome] = {"status": "ok", "quantidade": len(itens)}
        except Exception as exc:
            codigo_http = getattr(exc, "code", None)
            if codigo_http == 429:
                mensagem = (
                    "Limite de requisicoes da fonte atingido (HTTP 429). "
                    "As demais fontes continuam disponiveis; tente novamente "
                    "mais tarde."
                )
                situacao[nome] = {
                    "status": "limite",
                    "codigo_http": 429,
                    "mensagem": mensagem
                }
            else:
                situacao[nome] = {
                    "status": "erro",
                    "codigo_http": codigo_http,
                    "mensagem": str(exc)[:250]
                }

    # Deduplicacao robusta: DOI ou titulo normalizado.
    import unicodedata
    import re

    def normalizar_titulo(valor):
        valor = " ".join(str(valor or "").lower().split())
        valor = unicodedata.normalize("NFKD", valor)
        valor = "".join(
            c for c in valor
            if not unicodedata.combining(c)
        )
        return re.sub(r"[^a-z0-9]+", " ", valor).strip()

    def normalizar_doi(valor):
        valor = str(valor or "").strip().lower()
        for prefixo in (
            "https://doi.org/",
            "http://doi.org/",
            "https://dx.doi.org/",
            "http://dx.doi.org/",
            "doi:"
        ):
            if valor.startswith(prefixo):
                valor = valor[len(prefixo):].strip()
                break
        return valor.rstrip(" .;,") 

    unicos = []
    por_doi = {}
    por_titulo = {}

    for item_original in resultados:
        item = dict(item_original)
        titulo_original = str(item.get("titulo") or "").strip()
        titulo_chave = normalizar_titulo(titulo_original)
        doi = normalizar_doi(item.get("doi"))

        # Nao publicar registros sem titulo identificavel.
        if not titulo_chave:
            continue

        indice = None
        if doi:
            indice = por_doi.get(doi)
        if indice is None:
            indice = por_titulo.get(titulo_chave)

        fonte = str(item.get("fonte") or "").strip()

        if indice is None:
            item["fontes_encontradas"] = [fonte] if fonte else []
            indice = len(unicos)
            unicos.append(item)
        else:
            existente = unicos[indice]

            # Completa campos ausentes sem sobrescrever dados existentes.
            for campo in (
                "titulo", "autores", "ano", "doi", "link",
                "resumo", "tipo_documento"
            ):
                atual = existente.get(campo)
                recebido = item.get(campo)
                vazio = (
                    atual is None
                    or atual == ""
                    or atual == []
                )
                preenchido = (
                    recebido is not None
                    and recebido != ""
                    and recebido != []
                )
                if vazio and preenchido:
                    existente[campo] = recebido

            fontes_existentes = existente.setdefault(
                "fontes_encontradas", []
            )
            if fonte and fonte not in fontes_existentes:
                fontes_existentes.append(fonte)

        # Registra ambas as chaves para unir itens com DOI e sem DOI.
        item_final = unicos[indice]
        doi_final = normalizar_doi(item_final.get("doi")) or doi
        titulo_final = normalizar_titulo(item_final.get("titulo"))

        if doi_final:
            por_doi[doi_final] = indice
        if titulo_final:
            por_titulo[titulo_final] = indice
        por_titulo[titulo_chave] = indice

    # Auditoria conservadora de completude dos metadados.
    import re as _re_auditoria

    marcadores_codificacao = (
        chr(0xFFFD),
        chr(0x00C3) + chr(0x00A1),  # sequ?ncia suspeita: ??
        chr(0x00C3) + chr(0x00A9),  # sequ?ncia suspeita: ??
        chr(0x00C3) + chr(0x00AD),  # sequ?ncia suspeita: ??
        chr(0x00C3) + chr(0x00B3),  # sequ?ncia suspeita: ??
        chr(0x00C3) + chr(0x00BA),  # sequ?ncia suspeita: ??
        chr(0x00C3) + chr(0x00A3),  # sequ?ncia suspeita: ??
        chr(0x00C3) + chr(0x00B5),  # sequ?ncia suspeita: ??
        chr(0x00C3) + chr(0x00A7),  # sequ?ncia suspeita: ??
        chr(0x00C2) + chr(0x00A0),  # sequ?ncia suspeita: espa?o corrompido
        chr(0x00E2) + chr(0x20AC),
        chr(0x00EF) + chr(0x00BF) + chr(0x00BD),
    )

    for item in unicos:
        titulo = str(item.get("titulo") or "").strip()
        resumo = str(item.get("resumo") or "").strip()
        autores = item.get("autores") or []
        ano = item.get("ano")
        doi = str(item.get("doi") or "").strip()
        link = str(item.get("link") or "").strip()

        pendencias = list(item.get("pendencias_metadados") or [])

        verificacoes = [
            ("resumo_ausente", bool(resumo)),
            ("ano_ausente", ano is not None and ano != ""),
            ("autores_ausentes", bool(autores)),
            ("doi_ausente", bool(doi)),
            ("link_ausente", bool(link)),
        ]

        for codigo, preenchido in verificacoes:
            if not preenchido and codigo not in pendencias:
                pendencias.append(codigo)

        # Sinais conservadores de poss?vel perda de caracteres no t?tulo.
        # S?o alertas para revis?o, n?o corre??es autom?ticas.
        titulo_normalizado = normalizar_titulo(titulo)
        padroes_titulo_suspeito = (
            r"\bremoo\b",
            r"\bseparao\b",
            r"\bauxlio\b",
            r"\bpetroqumicos?\b",
            r"\bsintticos?\b",
            r"\bnoinico\b",
        )

        marcador_explicito = any(
            marca in titulo for marca in marcadores_codificacao
        )
        padrao_suspeito = any(
            _re_auditoria.search(padrao, titulo_normalizado)
            for padrao in padroes_titulo_suspeito
        )

        if (
            (marcador_explicito or padrao_suspeito)
            and "revisar_integridade_titulo" not in pendencias
        ):
            pendencias.append("revisar_integridade_titulo")

        campos_presentes = sum([
            bool(titulo),
            bool(autores),
            ano is not None and ano != "",
            bool(doi),
            bool(link),
            bool(resumo),
        ])

        item["pendencias_metadados"] = pendencias
        item["completude_metadados_percentual"] = round(
            campos_presentes / 6 * 100
        )

        if campos_presentes == 6:
            item["status_completude_metadados"] = "completo"
        elif campos_presentes >= 4:
            item["status_completude_metadados"] = "parcial"
        else:
            item["status_completude_metadados"] = "limitado"

    # Auditoria e triagem: normaliza acentos em consultas, titulos e resumos.
    import re
    import unicodedata

    def normalizar_texto_triagem(valor):
        texto = unicodedata.normalize("NFKD", str(valor or "").casefold())
        return "".join(
            c for c in texto if not unicodedata.combining(c)
        )

    stopwords = {
        "the", "and", "for", "with", "from", "com", "para",
        "de", "da", "do", "das", "dos", "em", "no", "na",
        "nos", "nas", "por", "uma", "uns", "umas", "que",
        "and", "the", "of", "to", "in", "on", "via"
    }

    consulta_normalizada = normalizar_texto_triagem(q)
    termos_consulta = [
        t for t in re.findall(r"[a-z0-9-]{3,}", consulta_normalizada)
        if t not in stopwords
    ]
    termos = list(dict.fromkeys(
        re.findall(r"[a-z0-9]+", " ".join(termos_consulta))
    ))

    # Aliases normalizados sem acentos, em portugues e ingles.
    familias = {
        "material_adsorvente": {
            "adsorbent", "adsorbents", "sorbent", "sorbents",
            "adsorvente", "adsorventes", "biossorvente",
            "biossorventes"
        },
        "processo_adsorcao": {
            "adsorption", "adsorptive", "adsorbing", "adsorbed",
            "adsorcao", "adsorver", "adsorvida", "adsorvido",
            "adsorvidas", "adsorvidos"
        },
        "material": {
            "material", "materials", "materialis"
        },
        "efluente_agua_residual": {
            "effluent", "effluents", "wastewater", "wastewaters",
            "efluente", "efluentes", "agua", "aguas",
            "residual", "residuais", "aquoso", "aquosa",
            "aquosos", "aquosas"
        },
        "tratamento_remocao": {
            "treatment", "treatments", "treated", "treating",
            "removal", "removing", "purification", "remediation",
            "tratamento", "tratamentos", "remocao", "remover",
            "removido", "removida", "removidos", "removidas",
            "purificacao", "descontaminacao"
        },
        "poluente_contaminante": {
            "pollutant", "pollutants", "contaminant", "contaminants",
            "poluente", "poluentes", "contaminante", "contaminantes",
            "poluicao", "contaminacao"
        },
        "contaminante_emergente": {
            "emergent", "emergents", "emerging",
            "emergente", "emergentes"
        },
        "carvao_ativado": {
            "charcoal", "activated", "carbon",
            "carvao", "ativado", "ativada", "ativados", "ativadas"
        }
    }

    mapa_familias = {
        alias: nome
        for nome, aliases in familias.items()
        for alias in aliases
    }
    conceitos_consulta = list(dict.fromkeys(
        mapa_familias.get(t, "termo:" + t) for t in termos
    ))
    aliases_por_conceito = {
        nome: aliases for nome, aliases in familias.items()
    }
    for conceito in conceitos_consulta:
        if conceito.startswith("termo:"):
            aliases_por_conceito[conceito] = {conceito[5:]}

    for item in unicos:
        titulo = str(item.get("titulo") or "")
        resumo = str(item.get("resumo") or "")
        tipo = str(item.get("tipo_documento") or "").strip().lower()
        tokens_titulo = set(re.findall(r"[a-z0-9]+", normalizar_texto_triagem(titulo)))
        tokens_resumo = set(re.findall(r"[a-z0-9]+", normalizar_texto_triagem(resumo)))

        encontrados_titulo = [t for t in termos if t in tokens_titulo]
        encontrados_resumo = [t for t in termos if t in tokens_resumo]
        total_termos = len(termos)
        cobertura_titulo = (
            len(encontrados_titulo) / total_termos if total_termos else 0.0
        )
        cobertura_resumo = (
            len(encontrados_resumo) / total_termos if total_termos else 0.0
        )

        conceitos_titulo = [
            c for c in conceitos_consulta
            if aliases_por_conceito[c] & tokens_titulo
        ]
        conceitos_resumo = [
            c for c in conceitos_consulta
            if aliases_por_conceito[c] & tokens_resumo
        ]
        total_conceitos = len(conceitos_consulta)
        cobertura_conceitual_titulo = (
            len(conceitos_titulo) / total_conceitos
            if total_conceitos else 0.0
        )
        cobertura_conceitual_resumo = (
            len(conceitos_resumo) / total_conceitos
            if total_conceitos else 0.0
        )

        resumo_disponivel = bool(resumo.strip())
        if total_termos:
            if resumo_disponivel:
                pontuacao = 0.7 * cobertura_titulo + 0.3 * cobertura_resumo
            else:
                pontuacao = cobertura_titulo
        else:
            pontuacao = 0.0

        if total_conceitos:
            if resumo_disponivel:
                pontuacao_conceitual = (
                    0.7 * cobertura_conceitual_titulo
                    + 0.3 * cobertura_conceitual_resumo
                )
            else:
                pontuacao_conceitual = cobertura_conceitual_titulo
        else:
            pontuacao_conceitual = 0.0

        pendencias = list(item.get("pendencias_metadados") or [])
        if not resumo_disponivel:
            pendencias.append("resumo_ausente")
        if not titulo.strip():
            pendencias.append("sem_titulo")
        if not str(item.get("ano") or "").strip():
            pendencias.append("ano_ausente")
        if (
            not str(item.get("link") or "").strip()
            and not str(item.get("doi") or "").strip()
        ):
            pendencias.append("sem_link_ou_doi")
        if not tipo:
            pendencias.append("tipo_ausente")

        tipos_para_revisao = (
            "dataset", "dissertation", "thesis", "book",
            "book-chapter", "report", "posted-content"
        )
        if any(t in tipo for t in tipos_para_revisao):
            pendencias.append("revisar_tipo_documental")

        if resumo_disponivel:
            revisar_lexical = (
                pontuacao < 0.60
                or (
                    cobertura_titulo < 0.50
                    and cobertura_resumo < 0.80
                )
            )
            revisar_relevancia = (
                pontuacao_conceitual < 0.60
                or (
                    cobertura_conceitual_titulo < 0.50
                    and cobertura_conceitual_resumo < 0.80
                )
            )
        else:
            revisar_lexical = cobertura_titulo < 0.60
            revisar_relevancia = cobertura_conceitual_titulo < 0.60

        pendencias = list(dict.fromkeys(pendencias))
        item["pendencias_metadados"] = pendencias
        item["pontuacao_relevancia_textual"] = round(pontuacao * 100, 1)
        item["cobertura_termos_titulo"] = round(cobertura_titulo * 100, 1)
        item["cobertura_termos_resumo"] = round(cobertura_resumo * 100, 1)
        item["revisao_relevancia_lexical_recomendada"] = bool(revisar_lexical)
        item["pontuacao_cobertura_conceitual"] = round(
            pontuacao_conceitual * 100, 1
        )
        item["cobertura_conceitual_titulo"] = round(
            cobertura_conceitual_titulo * 100, 1
        )
        item["cobertura_conceitual_resumo"] = round(
            cobertura_conceitual_resumo * 100, 1
        )
        item["termos_conceituais_encontrados"] = list(dict.fromkeys(
            conceitos_titulo + conceitos_resumo
        ))
        item["revisao_relevancia_recomendada"] = bool(revisar_relevancia)
        item["revisao_recomendada"] = (
            bool(pendencias) or bool(revisar_relevancia)
        )
        item["termos_consulta_encontrados"] = list(dict.fromkeys(
            encontrados_titulo + encontrados_resumo
        ))
        item["classificacao_triagem_conceitual"] = (
            "revisao_manual_recomendada"
            if revisar_relevancia
            else "cobertura_conceitual_suficiente_para_triagem"
        )

        if resumo_disponivel:
            item["criterio_triagem"] = (
                "cobertura lexical original e conceitual por familias; "
                "70% titulo e 30% resumo; heuristica preliminar, "
                "nao valida relevancia cientifica nem qualidade metodologica"
            )
        else:
            item["criterio_triagem"] = (
                "cobertura lexical original e conceitual somente pelo titulo; "
                "resumo ausente; heuristica preliminar, nao valida relevancia "
                "cientifica nem qualidade metodologica"
            )

    # Preserva a contagem completa e aplica limite ao conjunto deduplicado.
    total_encontrado = len(unicos)
    resultados_limitados = unicos[:limite]
    resultados_resposta = {
        str(i): item for i, item in enumerate(resultados_limitados)
    }

    return {
        "consulta": q,
        "total": len(resultados_resposta),
        "total_encontrado": total_encontrado,
        "limite_aplicado": limite,
        "fontes": situacao,
        "resultados": list(resultados_resposta.values())
    }

@router.get("/api/fontes/unpaywall")
def consultar_unpaywall(doi: str = Query(..., min_length=3)):
    if not EMAIL:
        return {
            "status": "configuracao_necessaria",
            "mensagem": "Configure a variavel de ambiente UNPAYWALL_EMAIL."
        }
    url = "https://api.unpaywall.org/v2/" + urllib.parse.quote(doi, safe="") + "?" + urllib.parse.urlencode({
        "email": EMAIL
    })
    try:
        return requisicao_json(url)
    except Exception as exc:
        return {"status": "erro", "mensagem": str(exc)[:250]}
