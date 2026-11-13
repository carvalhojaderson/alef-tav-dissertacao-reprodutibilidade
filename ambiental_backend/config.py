# -*- coding: utf-8 -*-
"""Configuracao do backend ambiental ALEF-TAV.

Tudo vem do ambiente: nenhuma credencial, URL de Space ou dominio de
frontend fica escrita no codigo. O nucleo cientifico (`universal.py`,
`bancos_rest.py`, `nucleo_dados.py`, `modelos_adsorcao_v2.py`, ...) vive no
diretorio pai deste pacote; `ALEF_TAV_CORE` permite apontar para outro lugar
quando o backend roda como aplicacao separada.

Variaveis lidas aqui (todas opcionais em desenvolvimento):

    ALEF_TAV_CORE              diretorio do nucleo cientifico
    AMBIENTAL_DADOS            diretorio de dados persistentes
    ALEF_TAV_DATA_DIR          alternativa a AMBIENTAL_DADOS
    AMBIENTAL_BANCO_URL        URL SQLAlchemy do banco (tem prioridade)
    AMBIENTAL_BANCO_PERSISTENTE=1  move o banco da plataforma para
                               AMBIENTAL_DADOS (usa ALEF_TAV_DATABASE_URL)
    CORS_ORIGENS               lista separada por virgula; sem a variavel valem
                               as origens conhecidas do frontend (ver
                               `ORIGENS_PADRAO`), nunca `*` por omissao
    CORS_ORIGEM_REGEX          regex extra de origem permitida (padrao: cobre
                               ais-dev-*/ais-pre-* do Cloud Run e *.web.app)
    AMBIENTAL_MAX_TAREFAS      threads de simulacao em paralelo (padrao 4)
    AMBIENTAL_TIMEOUT_SIMULADOR  segundos por simulador (padrao 180)
    AMBIENTAL_TIMEOUT_EVIDENCIA  segundos por busca multi-base (padrao 45)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PACOTE = Path(__file__).resolve().parent
CORE = Path(os.environ.get("ALEF_TAV_CORE") or PACOTE.parent).resolve()
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

VERSAO = "1.0.0"
NOME_SERVICO = "ALEF-TAV Ambiental API"


def _bool(nome: str, padrao: bool = False) -> bool:
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "sim", "yes", "on"}


def _inteiro(nome: str, padrao: int, minimo: int = 1, maximo: int = 600) -> int:
    try:
        valor = int(str(os.environ.get(nome, padrao)).strip())
    except (TypeError, ValueError):
        return padrao
    return max(minimo, min(valor, maximo))


def _pasta_gravavel(caminho: Path) -> bool:
    try:
        caminho.mkdir(parents=True, exist_ok=True)
        teste = caminho / ".escrita_ok"
        teste.write_text("ok", encoding="utf-8")
        teste.unlink()
        return True
    except Exception:                                    # noqa: BLE001
        return False


def diretorio_dados() -> Path:
    """Diretorio de dados persistentes.

    Ordem: `AMBIENTAL_DADOS` -> `ALEF_TAV_DATA_DIR` -> `/data` (disco
    persistente do Hugging Face, quando montado) -> `CORE/dados_ambiental`.
    """
    candidatos = []
    for nome in ("AMBIENTAL_DADOS", "ALEF_TAV_DATA_DIR"):
        valor = os.environ.get(nome)
        if valor:
            candidatos.append(Path(valor).expanduser())
    if os.name != "nt":
        # `/data` e' o disco persistente do Hugging Face; no Windows a mesma
        # string viraria `C:\data` e criaria uma pasta na raiz do drive.
        candidatos.append(Path("/data"))
    candidatos.append(CORE / "dados_ambiental")
    for caminho in candidatos:
        if _pasta_gravavel(caminho):
            return caminho.resolve()
    return (CORE / "dados_ambiental").resolve()


def diretorio_relatorios() -> Path:
    caminho = diretorio_dados() / "relatorios"
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def url_banco() -> str:
    """URL do banco da plataforma (reusa `alef_tav.db` por padrao)."""
    explicita = (os.environ.get("AMBIENTAL_BANCO_URL")
                 or os.environ.get("ALEF_TAV_DATABASE_URL")
                 or os.environ.get("DATABASE_URL"))
    if explicita:
        return explicita
    if _bool("AMBIENTAL_BANCO_PERSISTENTE"):
        destino = diretorio_dados() / "alef_tav.db"
        os.environ["ALEF_TAV_DATABASE_URL"] = "sqlite:///" + destino.as_posix()
        return os.environ["ALEF_TAV_DATABASE_URL"]
    return ""


#: Origens liberadas quando `CORS_ORIGENS` nao esta definido. Sao os enderecos
#: reais do frontend (Google AI Studio publicado no Cloud Run) e o
#: desenvolvimento local — nunca `*`: liberar todas as origens em producao
#: permitiria que qualquer site chamasse a API em nome do usuario.
ORIGENS_PADRAO = (
    "https://ais-dev-762xvkh6mpwv73wh6pxb4n-17975995585.us-east1.run.app",
    "https://ais-pre-762xvkh6mpwv73wh6pxb4n-17975995585.us-east1.run.app",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
)

#: Rede de seguranca para as URLs efemeras do AI Studio (`ais-dev-*` /
#: `ais-pre-*` no Cloud Run) e para `*.web.app`. Cobre as previas que o AI Studio
#: recria com outro identificador sem abrir a API para a internet inteira.
REGEX_PADRAO = (r"^https://(ais-(dev|pre)-[a-z0-9-]+(\.[a-z0-9-]+)+\.run\.app"
                r"|[a-z0-9-]+\.web\.app)$")


def origens_cors() -> list:
    """Origens exatas permitidas.

    `CORS_ORIGENS` aceita lista separada por virgula. Sem a variavel valem as
    origens conhecidas do frontend (`ORIGENS_PADRAO`); o valor `*` continua
    aceito, mas so' quando escrito de proposito (desenvolvimento).
    """
    bruto = os.environ.get("CORS_ORIGENS", "").strip()
    if not bruto:
        return list(ORIGENS_PADRAO)
    origens = [parte.strip() for parte in bruto.split(",") if parte.strip()]
    return origens or list(ORIGENS_PADRAO)


def origem_regex() -> str:
    """Regex adicional de origem permitida (`CORS_ORIGEM_REGEX`)."""
    bruto = os.environ.get("CORS_ORIGEM_REGEX")
    if bruto is None:
        return REGEX_PADRAO
    return bruto.strip()


def max_tarefas() -> int:
    return _inteiro("AMBIENTAL_MAX_TAREFAS", 4, 1, 32)


def timeout_simulador() -> int:
    return _inteiro("AMBIENTAL_TIMEOUT_SIMULADOR", 180, 5, 3600)


def timeout_evidencia() -> int:
    return _inteiro("AMBIENTAL_TIMEOUT_EVIDENCIA", 45, 5, 600)


def preparar_ambiente() -> dict:
    """Ajusta o ambiente antes de importar o nucleo cientifico.

    `ALEF_SEM_PREAQUECER=1` e' obrigatorio para chamadas fora do fluxo do app:
    sem ele o pre-aquecimento dos motores contende no import lock e a chamada
    nao retorna (medido na auditoria, `universal.py:1871-1878`).
    """
    os.environ.setdefault("ALEF_SEM_PREAQUECER", "1")
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return {"url_banco": url_banco(), "dados": str(diretorio_dados())}


def instantaneo() -> dict:
    """Resumo da configuracao efetiva (para /api/health)."""
    return {
        "servico": NOME_SERVICO,
        "versao": VERSAO,
        "nucleo": str(CORE),
        "dados": str(diretorio_dados()),
        "relatorios": str(diretorio_relatorios()),
        "cors_origens": origens_cors(),
        "cors_regex": bool(origem_regex()),
        "max_tarefas": max_tarefas(),
        "timeout_simulador_s": timeout_simulador(),
        "timeout_evidencia_s": timeout_evidencia(),
        "banco_persistente": _bool("AMBIENTAL_BANCO_PERSISTENTE"),
    }
