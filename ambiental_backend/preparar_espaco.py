# -*- coding: utf-8 -*-
"""Monta uma pasta pronta para publicar como Space INDEPENDENTE.

Uso (a partir da raiz do projeto):

    python ambiental_backend/preparar_espaco.py [_deploy_ambiental]

A pasta gerada contem:

    app.py                  entrada do Space ( `uvicorn app:app` )
    ambiental_backend/      este pacote (sem testes)
    <modulos do nucleo>     universal.py, bancos_rest.py, ...
    requirements.txt        dependencias extras do backend
    requirements-nucleo.txt dependencias do nucleo (copiadas da raiz)
    Dockerfile              sdk docker, porta 7860
    README.md               cartao do Space (front-matter do Hugging Face)

Nada e' inventado: se um modulo do nucleo nao existir na raiz, o script avisa e
segue — a ausencia aparece depois no `/api/health` (campo `motores`).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

PACOTE = Path(__file__).resolve().parent
RAIZ = PACOTE.parent

NUCLEO = (
    "universal.py", "integracoes_reais.py", "bancos_rest.py", "bases_v5.py",
    "conectores_academicos.py", "pesquisa_cientifica.py",
    "modelos_adsorcao_v2.py", "modelos_analiticos_v2.py", "nucleo_dados.py",
    "exportadores.py", "doc_export.py", "registro_componentes.py",
    "catalogo_registry.py", "chaves_config.py", "seguranca.py",
    "cache_busca.py",
)

SHIM = '''# -*- coding: utf-8 -*-
"""Entrada do Space independente: uvicorn app:app."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ambiental_backend.app import app  # noqa: E402,F401
'''

CARTAO = """---
title: ALEF-TAV Ambiental API
emoji: "\U0001F331"
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# ALEF-TAV Ambiental API

Backend de pesquisa ambiental: pergunta -> matriz 7Dx4 -> evidencias ->
simuladores -> viabilidade -> prova de conceito -> relatorio.

- Interface web (SPA sem build): `/`
- Documentacao interativa: `/docs`
- Contrato OpenAPI: `/openapi.json`
- Estado: `/api/health`

Consulte `README-BACKEND.md` para o fluxo completo, variaveis de ambiente e
consumo pelo frontend. Credenciais ficam em Settings > Secrets.
"""


def montar(destino) -> Path:
    destino = Path(destino).resolve()
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)

    shutil.copytree(
        PACOTE, destino / "ambiental_backend",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "test_*.py",
                                      "conftest.py", "preparar_espaco.py"))
    ausentes = []
    for nome in NUCLEO:
        origem = RAIZ / nome
        if origem.is_file():
            shutil.copy2(origem, destino / nome)
        else:
            ausentes.append(nome)

    # O bytecode original de `analises_experimentais` vive em `_recuperacao/` e
    # e' o que o modulo recuperado carrega; o filtro acima descarta cache
    # (`*.pyc`), entao essa pasta e' copiada a parte. Sem ela o Space sobe sem
    # os motores ambientais.
    origem_recuperacao = PACOTE / "_recuperacao"
    if origem_recuperacao.is_dir():
        destino_recuperacao = destino / "ambiental_backend" / "_recuperacao"
        destino_recuperacao.mkdir(parents=True, exist_ok=True)
        for arquivo in origem_recuperacao.glob("*.pyc"):
            shutil.copy2(arquivo, destino_recuperacao / arquivo.name)
        # as evidencias da recuperacao (.bin/.txt) ficam no repositorio de
        # trabalho: o Space precisa apenas do bytecode que o modulo carrega
        for arquivo in list(destino_recuperacao.glob("*.bin")) + \
                list(destino_recuperacao.glob("*.txt")):
            arquivo.unlink()
    else:                                     # pragma: no cover
        ausentes.append("_recuperacao/analises_experimentais.cpython-310.pyc")

    (destino / "app.py").write_text(SHIM, encoding="utf-8")
    (destino / "README.md").write_text(CARTAO, encoding="utf-8")
    shutil.copy2(PACOTE / "README.md", destino / "README-BACKEND.md")
    shutil.copy2(PACOTE / "requirements.txt", destino / "requirements.txt")
    shutil.copy2(PACOTE / "Dockerfile", destino / "Dockerfile")
    raiz_requirements = RAIZ / "requirements.txt"
    if raiz_requirements.is_file():
        shutil.copy2(raiz_requirements, destino / "requirements-nucleo.txt")
    (destino / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n"
        "!ambiental_backend/_recuperacao/*.pyc\n"
        "*.db\ndados_ambiental/\nrelatorios/\n",
        encoding="utf-8")
    return {"destino": destino, "modulos_ausentes": ausentes}


if __name__ == "__main__":                          # pragma: no cover
    alvo = sys.argv[1] if len(sys.argv) > 1 else str(RAIZ / "_deploy_ambiental")
    resultado = montar(alvo)
    print("pasta montada:", resultado["destino"])
    if resultado["modulos_ausentes"]:
        print("modulos do nucleo ausentes na raiz:",
              ", ".join(resultado["modulos_ausentes"]))
    print("publique esta pasta com: hf upload <space_id> . --repo-type space")
