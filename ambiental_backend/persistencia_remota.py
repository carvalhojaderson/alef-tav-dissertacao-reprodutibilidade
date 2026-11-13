# -*- coding: utf-8 -*-
"""Persistencia do banco fora do contÃªiner do Space.

O disco de um Space gratuito (`/data`) e' descartado a cada reinicializacao.
Medido nesta rodada: uma pesquisa criada antes do reinicio desapareceu do
`/api/history` depois dele. Para o historico sobreviver sem depender de disco
pago, o banco SQLite e' copiado (snapshot consistente via `sqlite3.backup`)
para um Dataset privado do Hugging Face e restaurado na inicializacao.

Variaveis:

    AMBIENTAL_BACKUP_REPO       dataset de destino, ex.: usuario/ambiental-dados
    HF_TOKEN                    token com escrita nesse dataset (Secret)
    AMBIENTAL_BACKUP_INTERVALO  segundos entre verificacoes (padrao 60)

Sem `AMBIENTAL_BACKUP_REPO` nada acontece: o modulo fica inerte e o
`/api/health` informa `persistencia_remota.configurado = false`.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

ARQUIVO = "alef_tav.db"
_TRAVA = threading.Lock()
_ESTADO = {
    "configurado": False,
    "repo": None,
    "restaurado_no_inicio": None,
    "ultimo_envio": None,
    "ultimo_erro": None,
    "envios": 0,
    "vigia_ativo": False,
}
_VIGIA = None


def _token():
    return (os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGINGFACE_API_KEY") or "").strip() or None


def _repo():
    return (os.environ.get("AMBIENTAL_BACKUP_REPO") or "").strip() or None


def _intervalo() -> int:
    try:
        return max(15, int(os.environ.get("AMBIENTAL_BACKUP_INTERVALO", "60")))
    except (TypeError, ValueError):
        return 60


def configurado() -> bool:
    return bool(_repo() and _token())


def banco_local():
    """Caminho do SQLite em uso (None quando o banco nao e' arquivo local)."""
    from . import config

    url = config.url_banco()
    if not url.startswith("sqlite"):
        return None
    caminho = url.split("sqlite:///", 1)[-1]
    return Path(caminho) if caminho else None


def _api():
    from huggingface_hub import HfApi

    return HfApi(token=_token())


def estado() -> dict:
    """Resumo para o /api/health (o que a interface mostra como persistencia)."""
    dados = dict(_ESTADO)
    dados["configurado"] = configurado()
    dados["repo"] = _repo()
    dados["banco_local"] = str(banco_local() or "")
    dados["intervalo_s"] = _intervalo()
    return dados


def restaurar() -> dict:
    """Baixa o snapshot do Dataset e o coloca no lugar do banco local."""
    if not configurado():
        return {"feito": False, "motivo": "persistencia remota nao configurada"}
    destino = banco_local()
    if destino is None:
        return {"feito": False, "motivo": "banco nao e' arquivo SQLite local"}
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import EntryNotFoundError

    try:
        baixado = hf_hub_download(repo_id=_repo(), filename=ARQUIVO,
                                  repo_type="dataset", token=_token())
    except EntryNotFoundError:
        return {"feito": False, "motivo": "sem copia anterior no dataset"}
    except Exception as erro:                              # noqa: BLE001
        _ESTADO["ultimo_erro"] = "restauracao: %s" % erro
        return {"feito": False, "motivo": str(erro)}
    tamanho = os.path.getsize(baixado)
    if tamanho == 0:
        return {"feito": False, "motivo": "copia remota vazia"}
    destino.parent.mkdir(parents=True, exist_ok=True)
    from . import persistencia as db

    db.ENGINE.dispose()
    temporario = destino.with_suffix(".restaurando")
    shutil.copy2(baixado, temporario)
    os.replace(temporario, destino)
    return {"feito": True, "bytes": tamanho, "destino": str(destino)}


def enviar(forcar: bool = False) -> dict:
    """Copia o banco (snapshot consistente) para o Dataset."""
    if not configurado():
        return {"enviado": False, "motivo": "persistencia remota nao configurada"}
    origem = banco_local()
    if origem is None or not origem.is_file():
        return {"enviado": False, "motivo": "banco local inexistente"}
    if not _TRAVA.acquire(blocking=False):
        return {"enviado": False, "motivo": "envio anterior em andamento"}
    temporario = None
    try:
        descritor, temporario = tempfile.mkstemp(suffix=".db")
        os.close(descritor)
        with sqlite3.connect(str(origem)) as fonte, \
                sqlite3.connect(temporario) as copia:
            fonte.backup(copia)
        api = _api()
        api.create_repo(_repo(), repo_type="dataset", private=True,
                        exist_ok=True)
        api.upload_file(path_or_fileobj=temporario, path_in_repo=ARQUIVO,
                        repo_id=_repo(), repo_type="dataset",
                        commit_message="backup do banco ambiental %s"
                                       % time.strftime("%Y-%m-%d %H:%M:%S"))
        _ESTADO["ultimo_envio"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _ESTADO["envios"] = int(_ESTADO["envios"]) + 1
        _ESTADO["ultimo_erro"] = None
        return {"enviado": True, "bytes": os.path.getsize(temporario)}
    except Exception as erro:                              # noqa: BLE001
        _ESTADO["ultimo_erro"] = "envio: %s" % erro
        return {"enviado": False, "motivo": str(erro)}
    finally:
        if temporario and os.path.exists(temporario):
            try:
                os.unlink(temporario)
            except OSError:
                pass
        _TRAVA.release()


def _vigiar():
    """Thread: envia o banco quando ele muda (nunca a cada requisicao)."""
    origem = banco_local()
    ultimo = None
    while True:
        time.sleep(_intervalo())
        try:
            if origem is None or not origem.is_file():
                continue
            marca = (os.path.getmtime(origem), os.path.getsize(origem))
            if marca == ultimo:
                continue
            resultado = enviar()
            if resultado.get("enviado"):
                ultimo = marca
        except Exception as erro:                          # noqa: BLE001
            _ESTADO["ultimo_erro"] = "vigia: %s" % erro


def preparar() -> dict:
    """Restaura o snapshot e liga o vigia. Chamado no startup da aplicacao."""
    if not configurado():
        return {"configurado": False,
                "motivo": "defina AMBIENTAL_BACKUP_REPO e HF_TOKEN"}
    restaurado = restaurar()
    _ESTADO["configurado"] = True
    _ESTADO["restaurado_no_inicio"] = restaurado
    global _VIGIA
    if _VIGIA is None:
        _VIGIA = threading.Thread(target=_vigiar, name="backup-banco",
                                  daemon=True)
        _VIGIA.start()
        _ESTADO["vigia_ativo"] = True
    return {"configurado": True, "restauracao": restaurado,
            "intervalo_s": _intervalo(), "repo": _repo()}
