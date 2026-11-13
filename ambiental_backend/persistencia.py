# -*- coding: utf-8 -*-
"""Persistencia do backend ambiental.

Reusa a camada unica da plataforma (`nucleo_dados`): mesmo `Base`, mesmo
`ENGINE`, mesma tabela `schema_version`. Aqui so entram as tabelas novas da
aplicacao ambiental, com prefixo `amb_`, criadas de forma idempotente
(`create_all(checkfirst=True)` + registro de versao propria).

Nada de banco paralelo: se `nucleo_dados` esta disponivel, o backend grava no
mesmo `alef_tav.db` (ou no `ALEF_TAV_DATABASE_URL`/`DATABASE_URL` definido no
ambiente, inclusive o disco persistente do Space).
"""
from __future__ import annotations

import datetime
import json
import secrets

from . import config

config.preparar_ambiente()

try:                                            # pragma: no cover - integracao
    import nucleo_dados as _nucleo
    Base = _nucleo.Base
    ENGINE = _nucleo.ENGINE
    Sessao = _nucleo.Sessao
    URL_BANCO = _nucleo.URL_BANCO
    HERDADO = True
except Exception:                               # pragma: no cover - fallback
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import declarative_base, sessionmaker

    _URL = (config.url_banco()
            or "sqlite:///" + (config.diretorio_dados() / "ambiental.db").as_posix())
    ENGINE = create_engine(_URL, future=True,
                           connect_args={"check_same_thread": False}
                           if _URL.startswith("sqlite") else {})
    Sessao = sessionmaker(bind=ENGINE, future=True, expire_on_commit=False)
    Base = declarative_base()
    URL_BANCO = _URL
    HERDADO = False

from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, String,  # noqa: E402
                        Text, UniqueConstraint, inspect, text)

VERSAO_ESQUEMA = 4
PREFIXO = "amb_"


def _agora():
    return datetime.datetime.now(datetime.timezone.utc)


def agora_iso() -> str:
    return _agora().isoformat()


def novo_id(prefixo: str) -> str:
    return "%s_%s" % (prefixo, secrets.token_hex(8))


def json_dumps(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, default=str)


def json_loads(texto, padrao=None):
    if not texto:
        return padrao
    try:
        return json.loads(texto)
    except (TypeError, ValueError):
        return padrao


def sessao():
    return Sessao()


class Pesquisa(Base):
    __tablename__ = "amb_pesquisas"
    id = Column(String(40), primary_key=True)
    pergunta = Column(Text, nullable=False)
    titulo = Column(String(240))
    material = Column(String(240))
    contaminante = Column(String(160))
    aplicacao = Column(String(80))
    condicoes_json = Column(Text)
    estado = Column(String(24), nullable=False, default="criada")
    versao = Column(Integer, default=1)
    criado_em = Column(DateTime(timezone=True), default=_agora)
    atualizado_em = Column(DateTime(timezone=True), default=_agora)


class Protocolo(Base):
    __tablename__ = "amb_protocolos"
    id = Column(String(40), primary_key=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), nullable=False,
                         index=True)
    perguntas_json = Column(Text)
    propriedades_json = Column(Text)
    descritores_json = Column(Text)
    simuladores_json = Column(Text)
    criterios_json = Column(Text)
    criado_em = Column(DateTime(timezone=True), default=_agora)


class Material(Base):
    __tablename__ = "amb_materiais"
    id = Column(String(40), primary_key=True)
    nome = Column(String(240), nullable=False, index=True)
    formula = Column(String(160))
    cas = Column(String(40))
    classe = Column(String(120))
    origem_material = Column(String(200))
    observacao = Column(Text)
    criado_em = Column(DateTime(timezone=True), default=_agora)


class PesquisaMaterial(Base):
    __tablename__ = "amb_pesquisa_materiais"
    __table_args__ = (UniqueConstraint("pesquisa_id", "material_id"),)
    id = Column(Integer, primary_key=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), nullable=False,
                         index=True)
    material_id = Column(ForeignKey("amb_materiais.id"), nullable=False,
                         index=True)
    papel = Column(String(24), default="alvo")
    criado_em = Column(DateTime(timezone=True), default=_agora)


class Composicao(Base):
    __tablename__ = "amb_composicoes"
    id = Column(Integer, primary_key=True)
    material_id = Column(ForeignKey("amb_materiais.id"), nullable=False,
                         index=True)
    elemento = Column(String(120), nullable=False)
    fracao_massica = Column(Float)
    fracao_molar = Column(Float)
    origem = Column(String(200))
    criado_em = Column(DateTime(timezone=True), default=_agora)


class Propriedade(Base):
    __tablename__ = "amb_propriedades"
    id = Column(Integer, primary_key=True)
    material_id = Column(ForeignKey("amb_materiais.id"), nullable=False,
                         index=True)
    nome = Column(String(160), nullable=False)
    valor = Column(Float)
    valor_texto = Column(String(400))
    unidade = Column(String(60))
    origem = Column(String(200))
    metodo = Column(String(160))
    confianca = Column(Float)
    criado_em = Column(DateTime(timezone=True), default=_agora)


class Descritor(Base):
    __tablename__ = "amb_descritores"
    __table_args__ = (UniqueConstraint("material_id", "codigo"),)
    id = Column(Integer, primary_key=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), index=True)
    material_id = Column(ForeignKey("amb_materiais.id"), nullable=False,
                         index=True)
    codigo = Column(String(8), nullable=False)
    dimensao = Column(String(8), nullable=False)
    nome = Column(String(160), nullable=False)
    valor = Column(Float)
    valor_texto = Column(String(400))
    unidade = Column(String(60))
    estado = Column(String(20), nullable=False, default="ausente")
    fonte = Column(String(240))
    regra = Column(Text)
    dados_json = Column(Text)
    atualizado_em = Column(DateTime(timezone=True), default=_agora)


class Evidencia(Base):
    __tablename__ = "amb_evidencias"
    __table_args__ = (UniqueConstraint("pesquisa_id", "chave"),)
    id = Column(String(40), primary_key=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), nullable=False,
                         index=True)
    material_id = Column(ForeignKey("amb_materiais.id"), index=True)
    termo = Column(String(300))
    base = Column(String(60))
    fonte = Column(String(160))
    titulo = Column(Text)
    ano = Column(Integer)
    doi = Column(String(160))
    link = Column(String(400))
    resumo = Column(Text)
    tipo = Column(String(80))
    relevancia = Column(Float)
    chave = Column(String(64), nullable=False)
    bruto_json = Column(Text)
    criado_em = Column(DateTime(timezone=True), default=_agora)


class Referencia(Base):
    __tablename__ = "amb_referencias"
    id = Column(Integer, primary_key=True)
    evidencia_id = Column(ForeignKey("amb_evidencias.id"), nullable=False,
                          index=True)
    autores_json = Column(Text)
    veiculo = Column(String(240))
    volume = Column(String(40))
    paginas = Column(String(60))
    ano = Column(Integer)
    doi = Column(String(160))
    url = Column(String(400))


class Simulacao(Base):
    __tablename__ = "amb_simulacoes"
    id = Column(String(40), primary_key=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), nullable=False,
                         index=True)
    material_id = Column(ForeignKey("amb_materiais.id"), index=True)
    simulador = Column(String(120), nullable=False)
    motor = Column(String(160))
    parametros_json = Column(Text)
    estado = Column(String(24), nullable=False, default="enfileirada")
    resultado_json = Column(Text)
    erro = Column(Text)
    duracao_s = Column(Float)
    nivel_evidencia = Column(String(24), default="computacional")
    tarefa_id = Column(String(40), index=True)
    criado_em = Column(DateTime(timezone=True), default=_agora)
    concluido_em = Column(DateTime(timezone=True))


class Comparacao(Base):
    __tablename__ = "amb_comparacoes"
    id = Column(Integer, primary_key=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), nullable=False,
                         index=True)
    simulacao_id = Column(ForeignKey("amb_simulacoes.id"), index=True)
    descritor = Column(String(8))
    grandeza = Column(String(160))
    valor_calculado = Column(Float)
    unidade = Column(String(60))
    valor_literatura = Column(Float)
    fonte_literatura = Column(String(300))
    desvio_relativo = Column(Float)
    criterio = Column(String(60))
    veredito = Column(String(32))
    criado_em = Column(DateTime(timezone=True), default=_agora)


class Viabilidade(Base):
    __tablename__ = "amb_viabilidades"
    id = Column(String(40), primary_key=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), nullable=False,
                         index=True)
    pontuacao = Column(Float, nullable=False)
    classificacao = Column(String(40), nullable=False)
    criterios_json = Column(Text)
    lacunas_json = Column(Text)
    riscos_json = Column(Text)
    recomendacoes_json = Column(Text)
    criado_em = Column(DateTime(timezone=True), default=_agora)


class ProvaConceito(Base):
    __tablename__ = "amb_provas_conceito"
    id = Column(String(40), primary_key=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), nullable=False,
                         index=True)
    estado = Column(String(24), nullable=False, default="executada")
    passos_json = Column(Text)
    resultado_json = Column(Text)
    criado_em = Column(DateTime(timezone=True), default=_agora)


class Relatorio(Base):
    __tablename__ = "amb_relatorios"
    id = Column(String(40), primary_key=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), nullable=False,
                         index=True)
    tipo = Column(String(40), nullable=False)
    formato = Column(String(16), nullable=False)
    caminho = Column(String(400))
    conteudo = Column(Text)
    tamanho_bytes = Column(Integer)
    criado_em = Column(DateTime(timezone=True), default=_agora)


class Historico(Base):
    __tablename__ = "amb_historico"
    id = Column(Integer, primary_key=True)
    entidade = Column(String(40), nullable=False, index=True)
    entidade_id = Column(String(60), nullable=False, index=True)
    acao = Column(String(60), nullable=False)
    detalhe_json = Column(Text)
    quando = Column(DateTime(timezone=True), default=_agora)


class Tarefa(Base):
    __tablename__ = "amb_tarefas"
    id = Column(String(40), primary_key=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), index=True)
    tipo = Column(String(40), nullable=False)
    estado = Column(String(24), nullable=False, default="enfileirada")
    progresso = Column(Integer, default=0)
    mensagem = Column(String(300))
    resultado_json = Column(Text)
    erro = Column(Text)
    criada_em = Column(DateTime(timezone=True), default=_agora)
    concluida_em = Column(DateTime(timezone=True))


class Medicao(Base):
    """Medicao experimental de bancada (entrada de dado real no sistema).

    Cada linha e' uma grandeza medida com tecnica, instrumento, incerteza e
    replicatas. O descritor correspondente e' atualizado pelo modulo `medicoes`
    com `estado` de medicao — nunca com valor presumido.
    """
    __tablename__ = "amb_medicoes"
    id = Column(String(40), primary_key=True)
    material_id = Column(ForeignKey("amb_materiais.id"), nullable=False,
                         index=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), index=True)
    tipo = Column(String(60), nullable=False, index=True)
    descritor = Column(String(8), index=True)
    valor = Column(Float)
    valor_texto = Column(String(400))
    unidade = Column(String(40))
    metodo = Column(String(160))
    instrumento = Column(String(160))
    incerteza = Column(Float)
    replicatas_json = Column(Text)
    estatistica_json = Column(Text)
    condicoes_json = Column(Text)
    laboratorio = Column(String(160))
    operador = Column(String(120))
    data_medicao = Column(DateTime(timezone=True))
    origem = Column(String(40), default="medicao_experimental")
    estado = Column(String(20), default="presente")
    criado_em = Column(DateTime(timezone=True), default=_agora)


class Componente(Base):
    """Caracterizacao de um dos quatro componentes do sistema de adsorcao.

    Adsorbato, adsorvente, interface e meio tem parametros proprios (massa
    molar, pKa, energia de adsorcao, pH...) que nao sao descritores 7Dx4 mas
    alimentam regras e simuladores. Cada linha guarda valor, unidade, origem,
    metodo, referencia e estado de validacao.
    """
    __tablename__ = "amb_componentes"

    id = Column(String(40), primary_key=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), index=True)
    material_id = Column(ForeignKey("amb_materiais.id"), nullable=False,
                         index=True)
    componente = Column(String(24), nullable=False, index=True)
    chave = Column(String(60), nullable=False, index=True)
    nome = Column(String(160))
    valor = Column(Float)
    valor_texto = Column(String(400))
    unidade = Column(String(60))
    origem = Column(String(40), default="informado")
    metodo = Column(String(160))
    referencia = Column(String(300))
    estado = Column(String(20), default="presente")
    criado_em = Column(DateTime(timezone=True), default=_agora)
    atualizado_em = Column(DateTime(timezone=True), default=_agora)


class ConversaLuna(Base):
    """Historico da assistente Luna, isolado por pesquisa e por usuario.

    Uma linha por mensagem. `conversa_id` agrupa a pergunta e a resposta; o
    registro guarda o modelo que respondeu e as ferramentas consultadas, para
    a trilha provar de onde veio cada numero citado. A chave da OpenAI nunca
    entra nesta tabela — so' o nome do modelo e o consumo de tokens.
    """
    __tablename__ = "amb_luna_conversas"

    id = Column(String(60), primary_key=True)
    conversa_id = Column(String(40), nullable=False, index=True)
    pesquisa_id = Column(ForeignKey("amb_pesquisas.id"), index=True)
    material_id = Column(String(40), index=True)
    usuario = Column(String(80), nullable=False, default="publico", index=True)
    papel = Column(String(16), nullable=False)
    conteudo = Column(Text)
    modelo = Column(String(80))
    ferramentas_json = Column(Text)
    uso_json = Column(Text)
    criado_em = Column(DateTime(timezone=True), default=_agora)


TABELAS = [Pesquisa, Protocolo, Material, PesquisaMaterial, Composicao,
           Propriedade, Descritor, Evidencia, Referencia, Simulacao,
           Comparacao, Viabilidade, ProvaConceito, Relatorio, Historico,
           Tarefa, Medicao, Componente, ConversaLuna]


def garantir_esquema() -> dict:
    """Inicializacao idempotente do esquema ambiental.

    `create_all(checkfirst=True)` cria apenas o que falta, sem tocar nas tabelas
    da plataforma. A versao fica em `schema_version` (mesma tabela do
    `nucleo_dados`) e tambem em `amb_esquema`.
    """
    nomes = [modelo.__tablename__ for modelo in TABELAS]
    if HERDADO:
        Base.metadata.create_all(
            bind=ENGINE, checkfirst=True,
            tables=[modelo.__table__ for modelo in TABELAS])
    else:
        Base.metadata.create_all(bind=ENGINE, checkfirst=True)
    with ENGINE.begin() as conexao:
        existentes = set(inspect(conexao).get_table_names())
        if "amb_esquema" not in existentes:
            conexao.execute(text(
                "CREATE TABLE amb_esquema (versao INTEGER PRIMARY KEY, "
                "aplicada_em DATETIME)"))
        registrada = conexao.execute(text(
            "SELECT versao FROM amb_esquema WHERE versao = :v"),
            {"v": VERSAO_ESQUEMA}).first()
        if not registrada:
            conexao.execute(text(
                "INSERT INTO amb_esquema (versao, aplicada_em) "
                "VALUES (:v, :q)"),
                {"v": VERSAO_ESQUEMA, "q": _agora()})
    return {"versao": VERSAO_ESQUEMA, "tabelas": nomes,
            "motor": ENGINE.dialect.name, "url": URL_BANCO,
            "herdado_de_nucleo_dados": HERDADO}


def registrar_historico(sessao_db, entidade: str, entidade_id: str,
                        acao: str, detalhe=None) -> None:
    """Trilha de auditoria: quem mudou o que, em qual pesquisa."""
    sessao_db.add(Historico(entidade=entidade, entidade_id=str(entidade_id),
                            acao=acao, detalhe_json=json_dumps(detalhe or {})))


def contar(sessao_db, modelo) -> int:
    try:
        return int(sessao_db.query(modelo).count())
    except Exception:                                  # noqa: BLE001
        return 0


def resumo_esquema() -> dict:
    """Contagem por tabela + versao (usado no /api/health)."""
    from sqlalchemy import func, select

    dados = {}
    with ENGINE.connect() as conexao:
        for modelo in TABELAS:
            try:
                dados[modelo.__tablename__] = int(conexao.execute(
                    select(func.count()).select_from(modelo.__table__)).scalar())
            except Exception as erro:                  # noqa: BLE001
                dados[modelo.__tablename__] = "erro: %s" % erro
        try:
            versoes = [linha[0] for linha in conexao.execute(text(
                "SELECT versao FROM amb_esquema ORDER BY versao"))]
        except Exception:                              # noqa: BLE001
            versoes = []
    return {"versao_esquema": versoes, "registros": dados,
            "motor": ENGINE.dialect.name, "herdado_de_nucleo_dados": HERDADO}
