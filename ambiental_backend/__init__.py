# -*- coding: utf-8 -*-
"""Backend ALEF-TAV Ambiental.

Camada de orquestracao e API sobre os servicos que ja existem no projeto:
`universal.py` (113 simuladores), `bancos_rest.py` / `pesquisa_cientifica.py`
(bases cientificas), `modelos_adsorcao_v2.py` e `modelos_analiticos_v2.py`
(modelos de adsorcao), `nucleo_dados.py` (persistencia SQLAlchemy) e
`exportadores.py` (DOCX/PPTX/BibTeX/RIS).

Modulos
    config        ambiente, caminhos persistentes e CORS
    matriz_7d4    matriz metodologica 7D x 4 (28 descritores)
    persistencia  tabelas `amb_*` + inicializacao idempotente
    adaptadores   ponte para os motores/bases/relatorios existentes
    motor_pesquisa orquestracao da pergunta ate a viabilidade
    tarefas       execucao em segundo plano com estado consultavel
    relatorios    geracao e armazenamento dos relatorios
    api_ambiental rotas REST
    app           aplicacao FastAPI (entrada do Space)
"""
from .config import NOME_SERVICO, VERSAO

__all__ = ["NOME_SERVICO", "VERSAO"]
