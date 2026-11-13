# -*- coding: utf-8 -*-
"""Camada UNICA de persistencia (SQLAlchemy) da plataforma ALEF-TAV.

Perfil LOCAL: sqlite em arquivo, sem credencial.
Perfil NUVEM: definir DATABASE_URL (postgresql+psycopg://...) — nenhuma
credencial e inventada aqui; o valor vem apenas do ambiente.
"""
from __future__ import annotations

import datetime
import os

from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, String,
                        Text, UniqueConstraint, create_engine, func, inspect,
                        text)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

URL_BANCO = (os.environ.get("ALEF_TAV_DATABASE_URL")
             or os.environ.get("DATABASE_URL")
             or "sqlite:///" + os.path.join(
                 os.path.dirname(os.path.abspath(__file__)), "alef_tav.db"))

_CONECTAR = {"check_same_thread": False} if URL_BANCO.startswith("sqlite") else {}
ENGINE = create_engine(URL_BANCO, future=True, connect_args=_CONECTAR,
                       pool_pre_ping=True)
Sessao = sessionmaker(bind=ENGINE, future=True, expire_on_commit=False)
Base = declarative_base()

# Escada de estados ESG — transicao avanca um degrau (ou vai p/ BLOQUEADA)
ESTADOS_ESG = ["MENCIONADA", "CONFIGURADA", "CONECTADA", "TESTADA",
               "INTEGRADA", "BLOQUEADA"]


def _agora():
    return datetime.datetime.now(datetime.timezone.utc)


class SchemaVersion(Base):
    __tablename__ = "schema_version"
    versao = Column(Integer, primary_key=True)
    aplicada_em = Column(DateTime(timezone=True), default=_agora)


class Empresa(Base):
    __tablename__ = "empresas"
    id = Column(Integer, primary_key=True)
    nome = Column(String(160), nullable=False)
    cnpj = Column(String(32), unique=True)
    setor = Column(String(120))
    criado_em = Column(DateTime(timezone=True), default=_agora)
    usuarios = relationship("Usuario", back_populates="empresa")


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    nome = Column(String(160), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    senha_hash = Column(String(256), nullable=False)
    salt = Column(String(64), nullable=False)
    empresa_id = Column(ForeignKey("empresas.id"))
    criado_em = Column(DateTime(timezone=True), default=_agora)
    empresa = relationship("Empresa", back_populates="usuarios")


class SessaoUsuario(Base):
    __tablename__ = "sessoes"
    token = Column(String(128), primary_key=True)
    usuario_id = Column(ForeignKey("usuarios.id"), nullable=False)
    criada_em = Column(DateTime(timezone=True), default=_agora)
    expira_em = Column(DateTime(timezone=True), nullable=False)
    ativa = Column(Integer, default=1)


class Experimento(Base):
    __tablename__ = "experimentos"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(ForeignKey("empresas.id"))
    usuario_id = Column(ForeignKey("usuarios.id"))
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text)
    criado_em = Column(DateTime(timezone=True), default=_agora)
    atualizado_em = Column(DateTime(timezone=True), default=_agora)


class ParametroSimulacao(Base):
    __tablename__ = "parametros_simulacao"
    __table_args__ = (UniqueConstraint("experimento_id", "chave"),)
    id = Column(Integer, primary_key=True)
    experimento_id = Column(ForeignKey("experimentos.id"), nullable=False)
    chave = Column(String(120), nullable=False)
    valor = Column(String(400))


class ResultadoSimulacao(Base):
    __tablename__ = "resultados_simulacao"
    id = Column(Integer, primary_key=True)
    experimento_id = Column(ForeignKey("experimentos.id"))
    empresa_id = Column(ForeignKey("empresas.id"))
    simulador = Column(String(120), nullable=False)
    entrada_json = Column(Text)
    saida_json = Column(Text)
    metrica = Column(Float)
    criado_em = Column(DateTime(timezone=True), default=_agora)


class EsgEstado(Base):
    __tablename__ = "esg_estado"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(ForeignKey("empresas.id"), nullable=False, unique=True)
    estado = Column(String(32), nullable=False, default="MENCIONADA")
    atualizado_em = Column(DateTime(timezone=True), default=_agora)


class EsgTransicao(Base):
    __tablename__ = "esg_transicoes"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(ForeignKey("empresas.id"), nullable=False)
    de = Column(String(32))
    para = Column(String(32), nullable=False)
    motivo = Column(Text)
    quando = Column(DateTime(timezone=True), default=_agora)


class Relatorio(Base):
    __tablename__ = "relatorios"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(ForeignKey("empresas.id"))
    usuario_id = Column(ForeignKey("usuarios.id"))
    tipo = Column(String(40), nullable=False)
    formato = Column(String(16), nullable=False)
    caminho = Column(String(400))
    criado_em = Column(DateTime(timezone=True), default=_agora)


class CacheExterno(Base):
    __tablename__ = "cache_dados_externos"
    id = Column(Integer, primary_key=True)
    chave = Column(String(300), nullable=False, unique=True)
    valor_json = Column(Text)
    obtido_em = Column(DateTime(timezone=True), default=_agora)
    expira_em = Column(DateTime(timezone=True))


class TarefaAssincrona(Base):
    __tablename__ = "tarefas"
    id = Column(Integer, primary_key=True)
    nome = Column(String(200), nullable=False)
    estado = Column(String(24), nullable=False, default="iniciada")
    progresso = Column(Integer, default=0)
    resultado_json = Column(Text)
    erro = Column(Text)
    iniciada_em = Column(DateTime(timezone=True), default=_agora)
    concluida_em = Column(DateTime(timezone=True))


def _v1(conexao):
    """v1 — schema inicial (usuarios, empresas, experimentos, resultados)."""
    Base.metadata.create_all(bind=conexao)


def _v2(conexao):
    """v2 — coluna setor em empresas."""
    colunas = {c["name"] for c in inspect(conexao).get_columns("empresas")}
    if "setor" not in colunas:
        conexao.execute(text(
            "ALTER TABLE empresas ADD COLUMN setor VARCHAR(120)"))


def _v3(conexao):
    """v3 — estado ESG por empresa + historico de transicoes."""
    existentes = set(inspect(conexao).get_table_names())
    if "esg_estado" not in existentes:
        conexao.execute(text(
            "CREATE TABLE esg_estado (id INTEGER PRIMARY KEY, "
            "empresa_id INTEGER NOT NULL UNIQUE, estado VARCHAR(32) NOT NULL, "
            "atualizado_em DATETIME)"))
    if "esg_transicoes" not in existentes:
        conexao.execute(text(
            "CREATE TABLE esg_transicoes (id INTEGER PRIMARY KEY, "
            "empresa_id INTEGER NOT NULL, de VARCHAR(32), "
            "para VARCHAR(32) NOT NULL, motivo TEXT, quando DATETIME)"))


MIGRACOES = [(1, "schema_inicial", _v1), (2, "empresa_setor", _v2),
             (3, "esg_estado_e_transicoes", _v3)]


def versao_schema():
    try:
        with ENGINE.connect() as conexao:
            linhas = list(conexao.execute(text(
                "SELECT versao FROM schema_version ORDER BY versao")))
        return [linha[0] for linha in linhas]
    except Exception:  # banco ainda nao migrado
        return []


def aplicar_migracoes():
    """Aplica as migracoes pendentes em ordem e registra cada versao."""
    with ENGINE.begin() as conexao:
        conexao.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_version "
            "(versao INTEGER PRIMARY KEY, aplicada_em DATETIME)"))
        aplicadas = {linha[0] for linha in conexao.execute(
            text("SELECT versao FROM schema_version"))}
    novas = []
    for versao, nome, funcao in MIGRACOES:
        if versao in aplicadas:
            continue
        with ENGINE.begin() as conexao:
            funcao(conexao)
            conexao.execute(text(
                "INSERT INTO schema_version (versao, aplicada_em) "
                "VALUES (:v, :q)"), {"v": versao, "q": _agora()})
        novas.append({"versao": versao, "nome": nome})
    return {"url_banco": URL_BANCO, "migracoes_aplicadas": novas,
            "total_migracoes": len(MIGRACOES),
            "versoes_no_banco": versao_schema()}


def sessao():
    return Sessao()


def saude_banco():
    """Estado real do banco para o /health."""
    try:
        with ENGINE.connect() as conexao:
            conexao.execute(text("SELECT 1"))
        return {"conectado": True, "url": URL_BANCO,
                "versao_schema": versao_schema(),
                "tabelas": sorted(inspect(ENGINE).get_table_names()),
                "hora": _agora().isoformat(),
                "motor": ENGINE.dialect.name}
    except Exception as erro:  # pragma: no cover - caminho de falha real
        return {"conectado": False, "url": URL_BANCO, "erro": str(erro)}
