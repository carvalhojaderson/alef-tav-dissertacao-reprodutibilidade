# -*- coding: utf-8 -*-
"""Corpus de pesquisa cientifica: normalizacao, deduplicacao e historico.

O que existia e o que faltava
-----------------------------
`bancos_rest.consultar()` responde por base e a aba "Bancos cientificos" ja
agrega varias bases numa lista. O que **nao** existia era o elo seguinte: os
itens vinham crus (`{"titulo","link","ano","resumo"}` + `base`/`fonte`), sem
identificador, sem deduplicacao entre bases, sem historico e sem nada que o
`orquestrador_cientifico` pudesse consumir. Cada busca morria na tela.

Este modulo fecha esse elo e **nao** e' um segundo orquestrador:

    bancos_rest (HTTP por base)
        -> normalizar_item()        registro canonico, com id e origem
        -> consolidar()             dedup por DOI/identificador e por titulo+ano
        -> Repositorio.salvar()     historico em SQLite (auditoria/consultas)
        -> contexto_para_orquestrador()  corpus pronto para o orquestrador
        -> exportar()               JSON/CSV do que foi medido

Regras de honestidade (as mesmas do resto do projeto)
-----------------------------------------------------
* item sem link e sem DOI entra marcado `incompleto=True` com `campos_faltando`;
  nada e' descartado em silencio e nada e' completado por adivinhacao;
* falha de base vira `fontes[base] = {estado, motivo, http}` — uma busca com
  falha parcial continua valida e diz exatamente qual fonte falhou e por que;
* `duplicados` registra qual item foi fundido em qual, para auditoria;
* o corpus nunca afirma resultado cientifico: ele organiza referencias.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA_PADRAO = os.path.join(RAIZ, "auditoria", "consultas")
BANCO_PADRAO = os.path.join(PASTA_PADRAO, "pesquisas.db")

# Quantos itens por base na busca multi-base e prazo de cada consulta.
ITENS_POR_BASE = 3
PRAZO_PADRAO = 12.0
MAX_BASES = 6

# Alvos que o Empower Minds usa para pendurar um corpus cientifico. A lista e'
# a mesma dos modulos de dominio: um corpus pode servir a um projeto, a um
# desafio, a um territorio, a um living lab, a uma organizacao etc.
TIPOS_ALVO = ("projeto", "desafio", "territorio", "living_lab", "organizacao",
              "ecossistema", "parceiro", "infraestrutura", "experimento",
              "evidencia", "validacao", "transferencia", "indicador")

ROTULOS_ALVO = {
    "projeto": "Projetos",
    "desafio": "Desafios",
    "territorio": "Territorios",
    "living_lab": "Living Labs",
    "organizacao": "Organizacoes",
    "ecossistema": "Ecossistemas",
    "parceiro": "Parceiros",
    "infraestrutura": "Infraestrutura",
    "experimento": "Experimentacao",
    "evidencia": "Evidencias",
    "validacao": "Validacao",
    "transferencia": "Transferencia tecnologica",
    "indicador": "Indicadores",
}

RE_DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
RE_ARXIV = re.compile(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(v\d+)?")
RE_PMID = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)")
RE_ISBN = re.compile(r"isbn[:\s]*((?:97[89])?[0-9\-]{9,17})", re.IGNORECASE)


def agora() -> str:
    """Carimbo UTC sem microssegundos (mesmo formato do resto do projeto)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sem_acento(texto) -> str:
    """'Adsorção' -> 'adsorcao'; tambem colapsa espacos e baixa a caixa."""
    if texto is None:
        return ""
    decomposto = unicodedata.normalize("NFKD", str(texto))
    limpo = "".join(ch for ch in decomposto if not unicodedata.combining(ch))
    return " ".join(limpo.casefold().split())


def _so_digitos_ano(valor):
    """Ano plausivel (1500..2100) a partir de 2024, '2024-05-01' ou '2024'."""
    if valor is None:
        return None
    if isinstance(valor, int):
        return valor if 1500 <= valor <= 2100 else None
    achado = re.search(r"(1[5-9]\d{2}|20\d{2}|2100)", str(valor))
    return int(achado.group(1)) if achado else None


def _texto(valor, limite=600) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (list, tuple)):
        valor = "; ".join(str(parte) for parte in valor if parte)
    elif isinstance(valor, dict):
        valor = valor.get("name") or json.dumps(valor, ensure_ascii=False)
    return " ".join(str(valor).split())[:limite]


def extrair_doi(*textos) -> str:
    """Primeiro DOI plausivel encontrado nos textos (normalizado, sem URL)."""
    for texto in textos:
        if not texto:
            continue
        achado = RE_DOI.search(str(texto))
        if achado:
            return achado.group(0).rstrip(".,;)").lower()
    return ""


def detectar_identificadores(item: dict) -> dict:
    """Identificadores persistentes do item: doi, arxiv, pmid, isbn, url."""
    item = item or {}
    link = _texto(item.get("link") or item.get("url") or item.get("id"), 400)
    bruto = item.get("identificadores") if isinstance(
        item.get("identificadores"), dict) else {}
    identificadores = {}

    doi = (item.get("doi") or bruto.get("doi") or extrair_doi(link,
                                                             item.get("titulo"),
                                                             item.get("resumo")))
    if doi:
        identificadores["doi"] = doi

    arxiv = RE_ARXIV.search(link) or RE_ARXIV.search(_texto(item.get("id"), 200))
    if arxiv:
        identificadores["arxiv"] = arxiv.group(1)
    pmid = RE_PMID.search(link) or (bruto.get("pmid") or "")
    if pmid:
        identificadores["pmid"] = _texto(pmid, 20)
    isbn = RE_ISBN.search(_texto(item.get("resumo"), 600))
    if isbn:
        identificadores["isbn"] = isbn.group(1)
    if link:
        identificadores["url"] = link
    for chave in ("pmcid", "eid", "nct", "patent"):
        if bruto.get(chave):
            identificadores[chave] = _texto(bruto[chave], 60)
    return identificadores


def chave_deduplicacao(registro: dict) -> str:
    """Chave estavel: identificador persistente > titulo+ano > link > hash."""
    identificadores = registro.get("identificadores") or {}
    for chave in ("doi", "pmid", "arxiv", "pmcid", "patent", "isbn"):
        if identificadores.get(chave):
            return "%s:%s" % (chave, sem_acento(identificadores[chave]))
    titulo = sem_acento(registro.get("titulo"))
    ano = registro.get("ano") or ""
    if titulo:
        return "titulo:%s|%s" % (titulo, ano)
    url = sem_acento(identificadores.get("url"))
    if url:
        return "url:%s" % url
    base = registro.get("base") or ""
    digesto = hashlib.sha1(
        (base + "|" + _texto(registro.get("resumo"), 200)).encode("utf-8")
    ).hexdigest()[:16]
    return "hash:%s" % digesto


def normalizar_item(item, base_id="", fonte="", categoria="") -> dict:
    """Converte um item cru de qualquer base no registro canonico do corpus."""
    item = item if isinstance(item, dict) else {"titulo": item}
    titulo = _texto(item.get("titulo") or item.get("title")
                    or item.get("nome") or item.get("name"), 300)
    link = _texto(item.get("link") or item.get("url"), 400)
    ano = _so_digitos_ano(item.get("ano") or item.get("year")
                          or item.get("publicado") or item.get("data"))
    resumo = _texto(item.get("resumo") or item.get("abstract")
                    or item.get("descricao"), 600)
    autores = item.get("autores") or item.get("authors") or []
    if isinstance(autores, str):
        autores = [parte.strip() for parte in autores.split(";") if parte.strip()]
    autores = [_texto(nome, 120) for nome in autores if nome][:20]

    registro = {
        "base": _texto(item.get("base") or base_id, 40),
        "fonte": _texto(item.get("fonte") or fonte, 120),
        "categoria": _texto(item.get("categoria") or categoria, 60),
        "titulo": titulo,
        "ano": ano,
        "resumo": resumo,
        "link": link,
        "autores": autores,
        "tipo": _texto(item.get("tipo") or item.get("type"), 60),
    }
    registro["identificadores"] = detectar_identificadores(
        dict(item, link=link, titulo=titulo, resumo=resumo))
    registro["doi"] = registro["identificadores"].get("doi", "")

    # Chave de origem preservada: de qual base veio e o id nativo, se houver.
    registro["origem"] = {
        "base": registro["base"],
        "id_nativo": _texto(item.get("id") or registro["identificadores"].get(
            "url"), 200),
        "nota": _texto(item.get("nota"), 200),
    }

    faltando = []
    if not registro["titulo"]:
        faltando.append("titulo")
    if not registro["link"] and not registro["doi"]:
        faltando.append("link_ou_doi")
    if not registro["ano"]:
        faltando.append("ano")
    registro["campos_faltando"] = faltando
    registro["incompleto"] = bool(faltando)

    semente = chave_deduplicacao(registro) + "|" + registro["base"]
    registro["id"] = "ref_" + hashlib.sha1(semente.encode("utf-8")).hexdigest()[:12]
    registro["chave"] = chave_deduplicacao(registro)
    registro["bases"] = [registro["base"]] if registro["base"] else []
    registro["duplicados_de"] = []
    registro["consultado_em"] = agora()
    return registro


def _recalcular_faltando(registro):
    faltando = []
    if not registro.get("titulo"):
        faltando.append("titulo")
    if not registro.get("link") and not registro.get("doi"):
        faltando.append("link_ou_doi")
    if not registro.get("ano"):
        faltando.append("ano")
    registro["campos_faltando"] = faltando
    registro["incompleto"] = bool(faltando)
    return registro


def _fundir(alvo: dict, novo: dict) -> None:
    """Funde o duplicado no registro mantido, sem perder a origem dele."""
    for campo in ("titulo", "resumo", "link", "ano", "doi", "tipo", "fonte"):
        if not alvo.get(campo) and novo.get(campo):
            alvo[campo] = novo[campo]
    for base in novo.get("bases") or []:
        if base and base not in alvo["bases"]:
            alvo["bases"].append(base)
    identificadores = alvo.setdefault("identificadores", {})
    for chave, valor in (novo.get("identificadores") or {}).items():
        identificadores.setdefault(chave, valor)
    if not alvo.get("autores") and novo.get("autores"):
        alvo["autores"] = novo["autores"]
    alvo.setdefault("duplicados_de", []).append(novo.get("id"))
    _recalcular_faltando(alvo)


def _pode_fundir_por_titulo(alvo: dict, novo: dict) -> bool:
    """Mesma obra? Exige titulo+ano iguais e identificador ausente num dos lados.

    Dois registros com DOIs diferentes nao sao fundidos, mesmo com titulo igual:
    sao publicacoes distintas (artigo e errata, por exemplo).
    """
    if sem_acento(alvo.get("titulo")) != sem_acento(novo.get("titulo")):
        return False
    if (alvo.get("ano") or None) != (novo.get("ano") or None):
        return False
    return not alvo.get("doi") or not novo.get("doi")


def consolidar(resultados: dict) -> dict:
    """Normaliza, deduplica e resume varios `Resultado` (um por base).

    `resultados` aceita `bancos_rest.Resultado` ou o dicionario equivalente
    (`{"estado","itens","motivo",...}`), que e' o formato da UI/API.
    """
    fontes = {}
    por_estado = {}
    por_chave = {}
    por_titulo = {}
    ordem = []
    duplicados = []

    for base_id, bruto in (resultados or {}).items():
        if hasattr(bruto, "dicionario"):
            dados = bruto.dicionario()
        elif isinstance(bruto, dict):
            dados = dict(bruto)
        else:
            dados = {"estado": "FALHOU", "motivo": "resultado em formato invalido"}
        estado = dados.get("estado") or "OK"
        itens = dados.get("itens") or []
        fontes[base_id] = {
            "estado": estado,
            "total": int(dados.get("total", len(itens)) or 0),
            "segundos": dados.get("segundos", 0.0),
            "motivo": _texto(dados.get("motivo"), 300),
            "requisito": _texto(dados.get("requisito"), 60),
            "http": dados.get("http"),
        }
        por_estado[estado] = por_estado.get(estado, 0) + 1

        fonte_nome = dados.get("fonte") or ""
        for item in itens:
            registro = normalizar_item(item, base_id=base_id, fonte=fonte_nome)
            chave = registro["chave"]
            titulo_ano = (sem_acento(registro.get("titulo")), registro.get("ano"))
            alvo = chave if chave in por_chave else None
            if alvo is None:
                candidato = por_titulo.get(titulo_ano)
                if candidato and _pode_fundir_por_titulo(por_chave[candidato],
                                                         registro):
                    alvo = candidato
            if alvo is None:
                por_chave[chave] = registro
                ordem.append(chave)
                por_titulo.setdefault(titulo_ano, chave)
            else:
                _fundir(por_chave[alvo], registro)
                duplicados.append({"mantido": por_chave[alvo]["id"],
                                   "fundido": registro["id"],
                                   "chave": alvo,
                                   "base": registro["base"]})
                por_titulo.setdefault(titulo_ano, alvo)


    itens_finais = [por_chave[chave] for chave in ordem]
    incompletos = [item["id"] for item in itens_finais if item["incompleto"]]
    falhas = {base: {"estado": dados["estado"], "motivo": dados["motivo"],
                     "http": dados["http"]}
              for base, dados in fontes.items()
              if dados["estado"] not in ("OK", "VAZIO")}
    return {
        "itens": itens_finais,
        "fontes": fontes,
        "duplicados": duplicados,
        "falhas": falhas,
        "totais": {
            "bases": len(fontes),
            "bases_ok": sum(1 for dados in fontes.values()
                            if dados["estado"] == "OK"),
            "itens": len(itens_finais),
            "duplicados": len(duplicados),
            "incompletos": len(incompletos),
            "por_estado": por_estado,
        },
    }


DDL = """
CREATE TABLE IF NOT EXISTS pesquisas (
    id TEXT PRIMARY KEY,
    termo TEXT NOT NULL,
    criada_em TEXT NOT NULL,
    projeto_id TEXT,
    total_bases INTEGER NOT NULL,
    total_itens INTEGER NOT NULL,
    duplicados INTEGER NOT NULL,
    incompletos INTEGER NOT NULL,
    resumo TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS itens (
    pesquisa_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    ordem INTEGER NOT NULL,
    base TEXT,
    fonte TEXT,
    categoria TEXT,
    titulo TEXT,
    ano INTEGER,
    resumo TEXT,
    link TEXT,
    doi TEXT,
    identificadores TEXT,
    autores TEXT,
    bases TEXT,
    incompleto INTEGER NOT NULL,
    campos_faltando TEXT,
    consultado_em TEXT,
    PRIMARY KEY (pesquisa_id, item_id)
);
CREATE TABLE IF NOT EXISTS fontes (
    pesquisa_id TEXT NOT NULL,
    base TEXT NOT NULL,
    estado TEXT NOT NULL,
    total INTEGER NOT NULL,
    segundos REAL,
    motivo TEXT,
    requisito TEXT,
    http INTEGER,
    PRIMARY KEY (pesquisa_id, base)
);
CREATE TABLE IF NOT EXISTS projetos (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entidades (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    nome TEXT NOT NULL,
    atributos TEXT,
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vinculos (
    pesquisa_id TEXT NOT NULL,
    alvo_tipo TEXT NOT NULL,
    alvo_id TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    PRIMARY KEY (pesquisa_id, alvo_tipo, alvo_id)
);
CREATE INDEX IF NOT EXISTS idx_itens_pesquisa ON itens (pesquisa_id, ordem);
CREATE INDEX IF NOT EXISTS idx_pesquisas_projeto ON pesquisas (projeto_id);
CREATE INDEX IF NOT EXISTS idx_entidades_tipo ON entidades (tipo);
"""


class Repositorio:
    """Historico de pesquisas em SQLite (mesmo padrao do modulo ESG)."""

    def __init__(self, caminho=None):
        self.caminho = caminho or BANCO_PADRAO
        self._criar()

    # ------------------------------------------------------------ infraestrutura
    def _conectar(self):
        import sqlite3

        if self.caminho != ":memory:":
            pasta = os.path.dirname(os.path.abspath(self.caminho))
            if pasta and not os.path.isdir(pasta):
                os.makedirs(pasta)
        con = sqlite3.connect(self.caminho, timeout=15)
        con.row_factory = sqlite3.Row
        return con

    def _criar(self):
        with self._conectar() as con:
            con.executescript(DDL)

    # ------------------------------------------------------------ escrita
    def salvar_pesquisa(self, termo, consolidado, projeto_id=None,
                        pesquisa_id=None, criada_em=None):
        """Grava a pesquisa inteira (itens + estado de cada fonte) e devolve o id."""
        totais = consolidado.get("totais") or {}
        identificador = pesquisa_id or ("pesq_" + hashlib.sha1(
            ("%s|%s|%s" % (termo, agora(), os.urandom(6).hex())).encode("utf-8")
        ).hexdigest()[:16])
        resumo = {
            "termo": termo,
            "totais": totais,
            "falhas": consolidado.get("falhas") or {},
        }
        with self._conectar() as con:
            con.execute(
                "INSERT INTO pesquisas (id, termo, criada_em, projeto_id, "
                "total_bases, total_itens, duplicados, incompletos, resumo) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (identificador, termo, criada_em or agora(), projeto_id,
                 int(totais.get("bases", 0)), int(totais.get("itens", 0)),
                 int(totais.get("duplicados", 0)),
                 int(totais.get("incompletos", 0)),
                 json.dumps(resumo, ensure_ascii=False)))
            for ordem, item in enumerate(consolidado.get("itens") or []):
                con.execute(
                    "INSERT OR REPLACE INTO itens (pesquisa_id, item_id, ordem, "
                    "base, fonte, categoria, titulo, ano, resumo, link, doi, "
                    "identificadores, autores, bases, incompleto, campos_faltando, "
                    "consultado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (identificador, item["id"], ordem, item.get("base"),
                     item.get("fonte"), item.get("categoria"), item.get("titulo"),
                     item.get("ano"), item.get("resumo"), item.get("link"),
                     item.get("doi"),
                     json.dumps(item.get("identificadores") or {}, ensure_ascii=False),
                     json.dumps(item.get("autores") or [], ensure_ascii=False),
                     json.dumps(item.get("bases") or [], ensure_ascii=False),
                     1 if item.get("incompleto") else 0,
                     json.dumps(item.get("campos_faltando") or [], ensure_ascii=False),
                     item.get("consultado_em")))
            for base, dados in (consolidado.get("fontes") or {}).items():
                con.execute(
                    "INSERT OR REPLACE INTO fontes (pesquisa_id, base, estado, "
                    "total, segundos, motivo, requisito, http) VALUES (?,?,?,?,?,?,?,?)",
                    (identificador, base, dados.get("estado", "FALHOU"),
                     int(dados.get("total", 0)), dados.get("segundos"),
                     dados.get("motivo", ""), dados.get("requisito", ""),
                     dados.get("http")))
            if projeto_id:
                con.execute(
                    "INSERT OR IGNORE INTO vinculos (pesquisa_id, alvo_tipo, "
                    "alvo_id, criado_em) VALUES (?,?,?,?)",
                    (identificador, "projeto", str(projeto_id), agora()))
        return identificador

    # ------------------------------------------------------------ leitura
    def obter_pesquisa(self, pesquisa_id):
        """Pesquisa completa: cabecalho + itens + estado das fontes + vinculos."""
        with self._conectar() as con:
            linha = con.execute("SELECT * FROM pesquisas WHERE id = ?",
                                (str(pesquisa_id),)).fetchone()
            if linha is None:
                return None
            itens = []
            for registro in con.execute(
                    "SELECT * FROM itens WHERE pesquisa_id = ? ORDER BY ordem",
                    (str(pesquisa_id),)):
                item = dict(registro)
                item["identificadores"] = json.loads(item["identificadores"] or "{}")
                item["autores"] = json.loads(item["autores"] or "[]")
                item["bases"] = json.loads(item["bases"] or "[]")
                item["campos_faltando"] = json.loads(item["campos_faltando"] or "[]")
                item["incompleto"] = bool(item["incompleto"])
                itens.append(item)
            fontes = {registro["base"]: dict(registro) for registro in
                      con.execute("SELECT * FROM fontes WHERE pesquisa_id = ?",
                                  (str(pesquisa_id),))}
            vinculos = [dict(registro) for registro in con.execute(
                "SELECT alvo_tipo, alvo_id, criado_em FROM vinculos "
                "WHERE pesquisa_id = ? ORDER BY criado_em", (str(pesquisa_id),))]
        dados = dict(linha)
        dados["resumo"] = json.loads(dados["resumo"] or "{}")
        dados["itens"] = itens
        dados["fontes"] = fontes
        dados["vinculos"] = vinculos
        return dados

    def listar_pesquisas(self, projeto_id=None, alvo_tipo=None, alvo_id=None,
                         limite=20):
        """Historico (mais recente primeiro), filtrável por projeto ou alvo."""
        sql = ("SELECT p.* FROM pesquisas p")
        args = []
        if alvo_tipo and alvo_id:
            sql += (" JOIN vinculos v ON v.pesquisa_id = p.id "
                    "WHERE v.alvo_tipo = ? AND v.alvo_id = ?")
            args.extend([str(alvo_tipo), str(alvo_id)])
        elif projeto_id:
            sql += " WHERE p.projeto_id = ?"
            args.append(str(projeto_id))
        sql += " ORDER BY p.criada_em DESC LIMIT ?"
        args.append(max(1, int(limite)))
        with self._conectar() as con:
            saida = []
            for linha in con.execute(sql, args):
                dados = dict(linha)
                dados["resumo"] = json.loads(dados["resumo"] or "{}")
                saida.append(dados)
            return saida

    # ------------------------------------------------------------ alvos (Empower)
    def criar_projeto(self, nome, projeto_id=None):
        identificador = projeto_id or ("proj_" + hashlib.sha1(
            (str(nome) + agora()).encode("utf-8")).hexdigest()[:12])
        with self._conectar() as con:
            con.execute("INSERT OR IGNORE INTO projetos (id, nome, criado_em) "
                        "VALUES (?,?,?)", (identificador, str(nome), agora()))
        return identificador

    def listar_projetos(self):
        with self._conectar() as con:
            return [dict(linha) for linha in
                    con.execute("SELECT * FROM projetos ORDER BY criado_em DESC")]

    def associar(self, pesquisa_id, alvo_tipo, alvo_id):
        """Pendura a pesquisa num alvo (projeto, desafio, territorio, living lab...)."""
        if alvo_tipo not in TIPOS_ALVO:
            raise ValueError("tipo de alvo nao suportado: %s (validos: %s)"
                             % (alvo_tipo, ", ".join(TIPOS_ALVO)))
        if not str(alvo_id or "").strip():
            raise ValueError("informe o identificador do alvo")
        with self._conectar() as con:
            existe = con.execute("SELECT 1 FROM pesquisas WHERE id = ?",
                                 (str(pesquisa_id),)).fetchone()
            if existe is None:
                raise KeyError("pesquisa inexistente: %s" % pesquisa_id)
            con.execute("INSERT OR IGNORE INTO vinculos (pesquisa_id, alvo_tipo, "
                        "alvo_id, criado_em) VALUES (?,?,?,?)",
                        (str(pesquisa_id), alvo_tipo, str(alvo_id), agora()))
            if alvo_tipo == "projeto":
                con.execute("UPDATE pesquisas SET projeto_id = ? WHERE id = ?",
                            (str(alvo_id), str(pesquisa_id)))
        return {"pesquisa_id": pesquisa_id, "alvo_tipo": alvo_tipo,
                "alvo_id": str(alvo_id)}

    def vinculos_da_pesquisa(self, pesquisa_id):
        with self._conectar() as con:
            return [dict(linha) for linha in con.execute(
                "SELECT alvo_tipo, alvo_id, criado_em FROM vinculos "
                "WHERE pesquisa_id = ?", (str(pesquisa_id),))]

    # ------------------------------------------------------------ entidades
    def registrar_entidade(self, tipo, nome, atributos=None, entidade_id=None):
        """Cadastra uma entidade de dominio (organizacao, territorio, living lab...)."""
        if tipo not in TIPOS_ALVO:
            raise ValueError("tipo de entidade nao suportado: %s (validos: %s)"
                             % (tipo, ", ".join(TIPOS_ALVO)))
        if not str(nome or "").strip():
            raise ValueError("informe o nome da entidade")
        identificador = entidade_id or ("ent_" + hashlib.sha1(
            ("%s|%s|%s" % (tipo, nome, agora())).encode("utf-8")).hexdigest()[:12])
        with self._conectar() as con:
            con.execute(
                "INSERT OR IGNORE INTO entidades (id, tipo, nome, atributos, "
                "criado_em) VALUES (?,?,?,?,?)",
                (identificador, tipo, str(nome).strip(),
                 json.dumps(atributos or {}, ensure_ascii=False), agora()))
        return {"id": identificador, "tipo": tipo, "nome": str(nome).strip()}

    def listar_entidades(self, tipo=None):
        sql = "SELECT * FROM entidades"
        args = []
        if tipo:
            if tipo not in TIPOS_ALVO:
                raise ValueError("tipo de entidade nao suportado: %s" % tipo)
            sql += " WHERE tipo = ?"
            args.append(tipo)
        sql += " ORDER BY criado_em DESC"
        with self._conectar() as con:
            saida = []
            for linha in con.execute(sql, args):
                dados = dict(linha)
                dados["atributos"] = json.loads(dados.get("atributos") or "{}")
                saida.append(dados)
            return saida

    def obter_entidade(self, entidade_id):
        with self._conectar() as con:
            linha = con.execute("SELECT * FROM entidades WHERE id = ?",
                                (str(entidade_id),)).fetchone()
        if linha is None:
            return None
        dados = dict(linha)
        dados["atributos"] = json.loads(dados.get("atributos") or "{}")
        return dados


# ---------------------------------------------------------------------------
# Orquestracao da busca (injecao de dependencia: `consultar` e' substituivel)
# ---------------------------------------------------------------------------
def _consultar_padrao():
    import bancos_rest

    return bancos_rest.consultar


def bases_prontas():
    """Ids das bases que estao PRONTA no ambiente atual (credencial presente)."""
    import bancos_rest

    return [item["id"] for item in bancos_rest.estado_bancos()
            if item.get("estado") == "PRONTA"]


def _uma_base(consultar, base_id, termo, n, timeout):
    """Consulta uma base e devolve (base, estado medido) — nunca levanta."""
    try:
        resultado = consultar(base_id, termo, n=n, timeout=timeout)
    except TypeError:
        # Adaptador sem `timeout` (ex.: dublê de teste): tenta a assinatura curta.
        try:
            resultado = consultar(base_id, termo, n=n)
        except Exception as exc:                   # noqa: BLE001
            return base_id, {"estado": "FALHOU",
                             "motivo": "%s: %s" % (type(exc).__name__, exc)}
    except Exception as exc:                       # noqa: BLE001
        return base_id, {"estado": "FALHOU",
                         "motivo": "%s: %s" % (type(exc).__name__, exc)}
    if hasattr(resultado, "dicionario"):
        return base_id, resultado.dicionario()
    return base_id, resultado


def pesquisar(termo, bases=None, n=ITENS_POR_BASE, timeout=PRAZO_PADRAO,
              consultar=None, repositorio=None, projeto_id=None,
              max_bases=MAX_BASES, salvar=True):
    """Busca multi-base -> normalizacao -> dedup -> historico. Devolve o corpus.

    `consultar` existe para teste e para adaptadores: por padrao e'
    `bancos_rest.consultar`. Uma base que falha nao derruba a pesquisa: entra em
    `falhas` com estado e motivo medidos.
    """
    termo = (termo or "").strip()
    if not termo:
        raise ValueError("informe um termo de pesquisa nao vazio")

    consultar = consultar or _consultar_padrao()
    alvos = list(bases) if bases else bases_prontas()
    if not alvos:
        return {"estado": "SEM_BASES_PRONTAS", "termo": termo,
                "motivo": "nenhuma base PRONTA no ambiente atual",
                "consultadas": 0, "itens": [], "totais": {"bases": 0, "itens": 0}}
    alvos = alvos[:max(1, int(max_bases))]
    n = max(1, int(n))

    resultados = {}
    if len(alvos) == 1:
        base, dados = _uma_base(consultar, alvos[0], termo, n, timeout)
        resultados[base] = dados
    else:
        with ThreadPoolExecutor(max_workers=min(MAX_BASES, len(alvos))) as pool:
            futuros = [pool.submit(_uma_base, consultar, base, termo, n, timeout)
                       for base in alvos]
            for futuro in as_completed(futuros):
                base, dados = futuro.result()
                resultados[base] = dados

    consolidado = consolidar(resultados)
    totais = consolidado["totais"]
    saida = {
        "estado": "OK" if totais["itens"] else "VAZIO",
        "termo": termo,
        "bases": alvos,
        "consultadas": len(alvos),
        "totais": totais,
        "falhas": consolidado["falhas"],
        "duplicados": consolidado["duplicados"],
        "itens": consolidado["itens"],
        "fontes": consolidado["fontes"],
        "projeto_id": projeto_id,
    }
    if salvar:
        repo = repositorio or Repositorio()
        saida["pesquisa_id"] = repo.salvar_pesquisa(termo, consolidado,
                                                    projeto_id=projeto_id)
    return saida


def registrar_da_ui(dados, projeto_id=None, repositorio=None):
    """Registra o resultado agregado da aba "Bancos cientificos" no corpus.

    A aba devolve `{"termo","bases":{id:{estado,total,motivo}},"itens":[...]}`.
    Aqui os itens sao reagrupados por base de origem (o item carrega `base`) e a
    pesquisa entra no historico com o mesmo formato de `pesquisar()`.
    """
    if not isinstance(dados, dict) or not dados:
        raise ValueError("nada para registrar: rode uma busca primeiro")
    if dados.get("estado") in ("ENTRADA_INVALIDA", "BASE_DESCONHECIDA",
                               "SEM_BASES_PRONTAS"):
        raise ValueError("a ultima execucao terminou em %s: %s"
                         % (dados.get("estado"), dados.get("motivo", "")))
    termo = _texto(dados.get("termo"), 300)
    fontes = dados.get("bases") if isinstance(dados.get("bases"), dict) else {}
    resultados = {}
    for base_id, ficha in fontes.items():
        resultados[base_id] = {
            "estado": ficha.get("estado", "FALHOU"),
            "total": ficha.get("total", 0),
            "segundos": ficha.get("segundos", 0.0),
            "motivo": ficha.get("motivo", ""),
            "itens": [],
        }
    for item in dados.get("itens") or []:
        base_id = item.get("base") or "desconhecida"
        resultados.setdefault(base_id, {"estado": "OK", "itens": []})
        resultados[base_id].setdefault("itens", []).append(item)

    consolidado = consolidar(resultados)
    repo = repositorio or Repositorio()
    pesquisa_id = repo.salvar_pesquisa(termo, consolidado, projeto_id=projeto_id)
    totais = consolidado["totais"]
    return {
        "pesquisa_id": pesquisa_id,
        "termo": termo,
        "estado": "OK" if totais["itens"] else "VAZIO",
        "totais": totais,
        "falhas": consolidado["falhas"],
        "duplicados": consolidado["duplicados"],
        "itens": consolidado["itens"],
        "projeto_id": projeto_id,
    }


# ---------------------------------------------------------------------------
# Corpo para o orquestrador e exportacao
# ---------------------------------------------------------------------------
def contexto_para_orquestrador(pesquisa_id, repositorio=None):
    """Corpus no formato que o orquestrador consome (sem refazer a busca)."""
    repo = repositorio or Repositorio()
    pesquisa = repo.obter_pesquisa(pesquisa_id)
    if pesquisa is None:
        raise KeyError("pesquisa inexistente: %s" % pesquisa_id)
    itens = pesquisa.get("itens") or []
    referencias = [{
        "id": item["item_id"],
        "titulo": item.get("titulo") or "",
        "ano": item.get("ano"),
        "doi": item.get("doi") or "",
        "link": item.get("link") or "",
        "bases": item.get("bases") or [],
        "incompleto": bool(item.get("incompleto")),
    } for item in itens]
    return {
        "pesquisa_id": pesquisa["id"],
        "termo": pesquisa.get("termo") or "",
        "criada_em": pesquisa.get("criada_em"),
        "projeto_id": pesquisa.get("projeto_id"),
        "itens": itens,
        "referencias": referencias,
        "fontes": pesquisa.get("fontes") or {},
        "falhas": (pesquisa.get("resumo") or {}).get("falhas") or {},
        "totais": (pesquisa.get("resumo") or {}).get("totais") or {},
        "vinculos": pesquisa.get("vinculos") or [],
    }


def exportar(pesquisa_id, formato="JSON", pasta=None, repositorio=None):
    """Grava a pesquisa em disco e devolve o caminho. Nao inventa dado."""
    repo = repositorio or Repositorio()
    pesquisa = repo.obter_pesquisa(pesquisa_id)
    if pesquisa is None:
        raise KeyError("pesquisa inexistente: %s" % pesquisa_id)
    destino = pasta or PASTA_PADRAO
    if not os.path.isdir(destino):
        os.makedirs(destino)
    carimbo = re.sub(r"[^0-9]", "", str(pesquisa.get("criada_em") or ""))[:14]
    carimbo = carimbo or datetime.now().strftime("%Y%m%d%H%M%S")
    if (formato or "").upper().startswith("CSV"):
        caminho = os.path.join(destino, "corpus_%s_%s.csv" % (pesquisa_id, carimbo))
        with io.open(caminho, "w", encoding="utf-8", newline="") as fh:
            escritor = csv.writer(fh, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            escritor.writerow(["pesquisa_id", "item_id", "base", "bases", "fonte",
                               "categoria", "titulo", "ano", "doi", "link",
                               "incompleto"])
            for item in pesquisa.get("itens") or []:
                escritor.writerow([
                    pesquisa_id, item.get("item_id"), item.get("base") or "",
                    ",".join(item.get("bases") or []), item.get("fonte") or "",
                    item.get("categoria") or "", item.get("titulo") or "",
                    item.get("ano") or "", item.get("doi") or "",
                    item.get("link") or "",
                    "sim" if item.get("incompleto") else "nao",
                ])
        return caminho
    caminho = os.path.join(destino, "corpus_%s_%s.json" % (pesquisa_id, carimbo))
    with io.open(caminho, "w", encoding="utf-8") as fh:
        json.dump(pesquisa, fh, ensure_ascii=False, indent=2)
    return caminho


def historico(projeto_id=None, alvo_tipo=None, alvo_id=None, limite=20,
              repositorio=None):
    """Lista resumida do historico (para API/UI)."""
    repo = repositorio or Repositorio()
    return repo.listar_pesquisas(projeto_id=projeto_id, alvo_tipo=alvo_tipo,
                                 alvo_id=alvo_id, limite=limite)





