# -*- coding: utf-8 -*-
"""Cadastro, acesso e protecao de rotas (B) — sem dependencia externa.

Hash de senha: hashlib.scrypt (stdlib). Sessao: token opaco gravado no banco.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import os
import re
import secrets

from fastapi import Header, HTTPException

import nucleo_dados as nd

PARAMETROS_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 64}
HORAS_SESSAO = int(os.environ.get("ALEF_TAV_HORAS_SESSAO", "12"))
EMAIL_VALIDO = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def _derivar(senha, salt):
    return hashlib.scrypt(senha.encode("utf-8"), salt=salt.encode("utf-8"),
                          **PARAMETROS_SCRYPT).hex()


def gerar_hash_senha(senha):
    """Retorna (hash, salt) com salt aleatorio por usuario."""
    salt = secrets.token_hex(16)
    return _derivar(senha, salt), salt


def conferir_senha(senha, senha_hash, salt):
    return hmac.compare_digest(_derivar(senha, salt), senha_hash)


def _agora():
    return datetime.datetime.now(datetime.timezone.utc)


def _validar_email(email):
    if not isinstance(email, str) or not EMAIL_VALIDO.match(email.strip()):
        raise HTTPException(status_code=400, detail="E-mail invalido.")


def _validar_senha(senha):
    if not isinstance(senha, str) or len(senha) < 6:
        raise HTTPException(status_code=400,
                            detail="A senha deve ter ao menos 6 caracteres.")


def registrar_usuario(email, senha, nome=None, empresa=None, cnpj=None,
                      setor=None):
    """Cria empresa (se informada) + usuario. E-mail duplicado = 409."""
    _validar_email(email)
    _validar_senha(senha)
    email = email.strip().lower()
    sessao = nd.sessao()
    try:
        if sessao.query(nd.Usuario).filter_by(email=email).first():
            raise HTTPException(status_code=409, detail="E-mail ja cadastrado.")
        empresa_id = None
        if empresa:
            existente = None
            if cnpj:
                existente = sessao.query(nd.Empresa).filter_by(cnpj=cnpj).first()
            if existente is None:
                existente = nd.Empresa(nome=empresa.strip(), cnpj=cnpj,
                                       setor=setor)
                sessao.add(existente)
                sessao.commit()
                sessao.add(nd.EsgEstado(empresa_id=existente.id,
                                        estado="MENCIONADA"))
                sessao.add(nd.EsgTransicao(empresa_id=existente.id, de=None,
                                           para="MENCIONADA",
                                           motivo="empresa cadastrada"))
                sessao.commit()
            empresa_id = existente.id
        senha_hash, salt = gerar_hash_senha(senha)
        usuario = nd.Usuario(nome=(nome or email.split("@")[0]).strip(),
                             email=email, senha_hash=senha_hash, salt=salt,
                             empresa_id=empresa_id)
        sessao.add(usuario)
        sessao.commit()
        return {"status": "criado", "usuario_id": usuario.id,
                "email": usuario.email, "empresa_id": empresa_id}
    finally:
        sessao.close()


def autenticar(email, senha):
    """Confere credenciais e devolve o usuario (ou 401 amigavel)."""
    if not isinstance(email, str) or not isinstance(senha, str):
        raise HTTPException(status_code=400, detail="Informe e-mail e senha.")
    sessao = nd.sessao()
    try:
        usuario = sessao.query(nd.Usuario).filter_by(
            email=email.strip().lower()).first()
        if usuario is None or not conferir_senha(senha, usuario.senha_hash,
                                                 usuario.salt):
            raise HTTPException(status_code=401, detail="Credenciais invalidas.")
        return {"id": usuario.id, "nome": usuario.nome, "email": usuario.email,
                "empresa_id": usuario.empresa_id}
    finally:
        sessao.close()


def abrir_sessao(usuario_id):
    """Cria token de sessao com validade configuravel."""
    token = secrets.token_urlsafe(32)
    sessao = nd.sessao()
    try:
        sessao.add(nd.SessaoUsuario(
            token=token, usuario_id=usuario_id,
            expira_em=_agora() + datetime.timedelta(hours=HORAS_SESSAO)))
        sessao.commit()
        return {"token": token, "expira_em_horas": HORAS_SESSAO}
    finally:
        sessao.close()


def fechar_sessao(token):
    sessao = nd.sessao()
    try:
        linha = sessao.get(nd.SessaoUsuario, token)
        if linha is None:
            raise HTTPException(status_code=404, detail="Sessao inexistente.")
        linha.ativa = 0
        sessao.commit()
        return {"status": "encerrada", "token": token}
    finally:
        sessao.close()


def usuario_do_token(token):
    if not token:
        return None
    sessao = nd.sessao()
    try:
        linha = sessao.get(nd.SessaoUsuario, token)
        if linha is None or not linha.ativa:
            return None
        expira = linha.expira_em
        if expira is not None and expira.tzinfo is None:
            expira = expira.replace(tzinfo=datetime.timezone.utc)
        if expira is not None and expira < _agora():
            linha.ativa = 0
            sessao.commit()
            return None
        usuario = sessao.get(nd.Usuario, linha.usuario_id)
        if usuario is None:
            return None
        return {"id": usuario.id, "nome": usuario.nome, "email": usuario.email,
                "empresa_id": usuario.empresa_id}
    finally:
        sessao.close()


def usuario_atual(authorization: str = Header(default=None), token: str = None):
    """Dependencia FastAPI: exige token valido (protege rotas privadas)."""
    valor = token
    if not valor and authorization:
        partes = authorization.split()
        valor = (partes[1] if len(partes) == 2 and partes[0].lower() == "bearer"
                 else authorization)
    usuario = usuario_do_token(valor)
    if usuario is None:
        raise HTTPException(status_code=401,
                            detail="Acesso restrito: faca login em "
                                   "/api/auth/login e envie o token.")
    return usuario
