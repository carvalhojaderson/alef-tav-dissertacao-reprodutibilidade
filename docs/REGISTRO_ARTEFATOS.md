# Registro de artefatos da ALEF-TAV (31/10/2026)

Registro pedido pela instrucao de continuidade: o que **existia**, o que foi
**corrigido**, o que foi **construido** nesta rodada e o que continua
**pendente/bloqueado**. Cada linha abaixo tem arquivo, prova e numero — nenhum
item entra como "pronto" sem execucao.

## 1. Como esta rodada comecou (medicao, nao impressao)

`auditoria/varre_imports.py` (novo) varreu os 107 modulos vivos e mostrou:

| Sintoma | Medicao inicial | Estado final |
|---|---|---|
| `from fermilink_bridge import ...` em `universal.py:1686` | modulo **inexistente**; `except ImportError` mascarava a ausencia | `fermilink_bridge.py` construido, contrato cumprido, 8 testes |
| protocolo MCP | **nenhum** cliente/servidor no repositorio (so geradores locais com nome "mcp") | `mcp_alef/` + `api_mcp.py`, 19 testes, tool call real |
| `tts.py` / `voz_stt.py` | existiam e **nenhum** modulo do app os importava | `voz.py` + `api_voz.py`, 4 rotas, 15 testes |
| `orquestrador_cientifico.py` | orfao; corpo duplicado; 75 caracteres `?` no lugar de acentos | reconstruido + `api_orquestrador.py`, 14 testes |
| `auditoria_bases_pesquisa.csv` (Etapa G) | **ausente** | gerado por execucao real: 13 bases, 12 com item |
| documento de arquitetura | **ausente** (sem diagrama) | `docs/ARQUITETURA.md` gerado do `openapi()`: 85 caminhos / 92 operacoes |
| `python -m pytest` sem lista de arquivos | abortava com 6 erros `import file mismatch` (`_deploy_stage/`) | `conftest.py` com `pytest_ignore_collect`: 396 testes coletados |
| CORE (base citada na Etapa G) | nao existia no `bases_v5` | `b_core` com trava de credencial (`CORE_API_KEY`) |

## 2. Construido nesta rodada

| Artefato | O que faz de verdade | Prova |
|---|---|---|
| `mcp_alef/protocolo.py` | cliente JSON-RPC 2.0 sobre stdio: `initialize` -> `notifications/initialized`, `tools/list` (com `nextCursor`), `tools/call`, prazo e erro sanitizado | `pytest test_mcp_alef.py`: 19 passed |
| `mcp_alef/servidor_eco.py` | servidor MCP de referencia (4 ferramentas: 3 de leitura, 1 de escrita desativada) | handshake real em processo separado, 0,49 s |
| `mcp_alef/registro.py` | catalogo de servidores, maquina de estados `MENCIONADA -> ... -> INTEGRADA` / `BLOQUEADA`, recusa de escrita | `somar(2,40) = 42`; `gravar_nota` recusada com motivo |
| `api_mcp.py` | 5 rotas: `saude`, `servidores`, `ferramentas`, `testar` (login), `chamar` (login + so leitura) | 12 testes de rota, 401/403 provados |
| `voz.py` | estado por provedor, `VozIndisponivel` com `requisito`, limites de texto/audio | 15 testes (stubs rotulados + caminho "sem provedor") |
| `api_voz.py` | `/api/voz/saude`, `/vozes`, `/tts` (audio/mpeg), `/stt` (upload) | 503 com motivo quando falta provedor; 200 com stub |
| `api_orquestrador.py` | plano por area + inventario por AST + analise local | `"adsorção de metais"` -> `ambiental` |
| `api_mcp` / `api_voz` / `api_orquestrador` no `app.py` | montados com o padrao try/except + `MONTAGEM` | e2e: `/api/mcp/servidores` 200, `/api/voz/saude` 200, `/api/orquestrador/plano` 200 |
| `auditoria/varre_imports.py` | varredura estatica: imports quebrados x opcionais, routers montados, orfaos | `auditoria/varredura_artefatos.json` |
| `auditoria/gera_bases_pesquisa.py` | probe HTTP real + chamada do conector de cada base | `auditoria_bases_pesquisa.csv` |
| `auditoria/mapa_arquitetura.py` | gera `docs/ARQUITETURA.md` do contrato OpenAPI | 85 caminhos / 92 operacoes |

## 3. Corrigido nesta rodada (defeito -> causa -> prova)

1. **`fermilink_bridge` ausente** (`universal.py:1686`). O `except ImportError`
   escondia a inexistencia: `_BRIDGE_OK=False` e o caminho acelerado nunca era
   tentado, sem registro. Agora ha um adaptador de descoberta honesto
   (`ALEF_FERMILINK=0` desliga; plugin quebrado e recusado) e 8 testes provam as
   duas rotas, inclusive *plugin levanta excecao -> fallback analitico*.
2. **`orquestrador_cientifico.py`**: (a) o arquivo continha o modulo **duas
   vezes**; (b) 75 `?` substituiam acentos, entao `"adsorção"` nunca casava com
   `"adsor??o"` e a resposta era `multidisciplinar`; (c) ninguem importava o
   modulo. Reconstruido com normalizacao NFKD, leitura `utf-8-sig` (BOM) e
   contagem por `ast.walk`; backup em
   `orquestrador_cientifico.backup_pre_reconstrucao_20261031.py`.
3. **`bases_v5` sem CORE**: base citada na Etapa G nao existia. `b_core`
   adicionado com `CORE_API_KEY`; sem chave fica `funcional=False` e
   `info_bases()` conta como inativa (3 testes novos). Backup em
   `bases_v5.backup_pre_core_20261031.py`.
4. **Coleta do pytest**: `python -m pytest` seco abortava (6 erros) porque
   `_deploy_stage/` tem os mesmos nomes de teste. `conftest.py` passou a ignorar
   por caminho. Antes: `Interrupted: 6 errors during collection`. Depois:
   `396 tests collected`.
5. **`arxiv` declarado e nao instalado**: `requirements.txt` listava `arxiv` e
   `lxml`, mas o ambiente nao os tinha; `b_arxiv` devolvia `[]` em silencio.
   Instalado (`arxiv 4.0.2`, `lxml 6.1.3`) e provado: consulta "graphene" ->
   1 item em 1,68 s.

## 4. Pendente ou bloqueado (com requisito, nao com promessa)

| Item | Estado | Requisito / proximo passo |
|---|---|---|
| `mini-curso-generator`, `notebooklm`, `obsidian` como MCP | `BLOQUEADA` em `mcp_alef.registro` | informar o **comando real** do servidor em `mcp_servers.json`; sem ele nao ha handshake e nenhuma capacidade e' presumida |
| TTS/STT | bloqueado neste host | `pip install edge-tts` (TTS) e `pip install openai-whisper` (STT); sem eles `/api/voz/*` responde 503 com `requisito` |
| ElevenLabs / Groq | `BLOQUEADA` | credencial + aprovacao da implementacao (nenhum endpoint foi inventado) |
| CORE | `BLOQUEADO` | `CORE_API_KEY` no ambiente |
| Semantic Scholar | `FALHOU` (HTTP 429 na medicao) | limite de taxa da fonte; o conector ja devolve mensagem amigavel e as outras bases seguem |
| `catalogo_api_server.py` | servico separado (tem `app` proprio) | decidir se vira router do app ou fica como microservico |
| 119 `IMPLEMENTACAO_SEM_AMBIENTE` / 48 `APENAS_CATALOGADO` (harness) | inalterado | dependencia/imagem por componente, com prova individual |
| `melhorias_panel.py` | orfao com `import streamlit` no topo (painel legado de UI; o app usa Gradio) | instalar `streamlit` ou aposentar o modulo — decisao do pesquisador |
| `api_dados` publica `/health` e o app publica `/api/dados/health` | dois caminhos para o mesmo status (o `/health` do router so e' alcancado quando ele roda sozinho) | unificar exige atualizar `test_plataforma_ak.py`; registrado em `docs/REGISTRO_TAREFAS.md` §5 |

## 5. Indice dos artefatos de auditoria

| Arquivo | Origem | O que contem |
|---|---|---|
| `auditoria_113_funcoes.csv` | `gerar_auditorias.py` | estado de cada `sim_` |
| `auditoria_195_componentes.csv` | harness | estado de cada componente externo |
| `auditoria_endpoints.csv` | medicao HTTP | rotas ESG chamadas |
| `auditoria_integracoes_ferramentas.csv` | Etapa I/J | fontes, credencial (nome), estado |
| `auditoria_bases_pesquisa.csv` | **novo** | 13 bases: HTTP, itens, segundos, bloqueio |
| `auditoria/varredura_artefatos.json` | **novo** | imports quebrados, routers, orfaos |
| `docs/ARQUITETURA.md` | **novo** | contrato vivo + diagrama Mermaid |
| `docs/REGISTRO_ARTEFATOS.md` | **novo** | este arquivo |

## 6. Validacao final desta rodada

| Prova | Resultado medido |
|---|---|
| `python -m pytest --collect-only -q` | **396 tests collected**, 0 erros |
| bloco A (`test_esg_issacar.py test_plataforma_ak.py`) | **131 passed**, 285,40 s |
| bloco B (18 arquivos, inclui os 4 novos) | **265 passed**, 90,97 s |
| **suite completa** | **396 passed, 0 failed** (376,37 s somados) |
| `test_plataforma_ak.py` isolado | 62 passed, 20,44 s |
| `compileall` nos 14 arquivos novos/alterados | exit 0 |
| `app` montado com as rotas novas | `/api/mcp/servidores` 200, `/api/voz/saude` 200, `/api/orquestrador/plano` 200 |
| `auditoria/varredura_artefatos.json` | 1 import quebrado (legado Streamlit), 12 dependencias de motor lazy, 9 opcionais protegidas, 0 `from-import` invalido |
## 7. Rodada 2 (31/10/2026, continuacao): os 109 stubs de "187 bancos"

A varredura nova (`auditoria/descobre_lacunas.py`) olhou o que a anterior nao
olhava — **corpo de funcao**. Resultado: **111 funcoes stub**, sendo **109** em
`bancos_completos.py`, todas `return []`, e **nenhum** modulo do app importava
esse arquivo. O modulo anunciava "187 bancos" e nao entregava nenhum.

| Medicao | Antes | Depois |
|---|---|---|
| bases que fazem HTTP real | 12 (as que tinham `requests`) | **44** (39 medidas OK nesta rodada) |
| funcoes que devolvem `[]` sem motivo | 109 | **0** |
| consumidores do modulo | 0 | `api_bancos` (4 rotas) + `bancos_completos` compat |
| estado por base | inexistente | `PRONTA` / `BLOQUEADA` / `SEM_API` + `OK` / `VAZIO` / `FALHOU` / `INVALIDA` na consulta |

Construido:

| Artefato | O que faz | Prova |
|---|---|---|
| `bancos_rest.py` | motor declarativo (URL, `{q}`, `{n}`, caminho dos itens ate `a.b.0.c`) + 11 adaptadores de duas etapas (arXiv Atom, PubMed, NCBI Gene, PubChem, BCB SGS, PatentsView, ORCID, SIMBAD TAP, AFLOW texto, OpenAIRE, DuckDuckGo HTML) | `pytest test_bancos_rest.py`: **32 passed** |
| `api_bancos.py` | `GET /api/bancos`, `/saude`, `/{id}`, `POST /{id}/consultar` | 404 para base inexistente, 400 para `consulta` ausente ou `limite` invalido, 200 com `estado` medido |
| `bancos_completos.py` | reescrito como camada de compatibilidade (172 entradas com alias legado `arXiv` → `arxiv`), sem stub | `auditoria/verifica_compat_bancos.py` |
| `auditoria/probe_bancos.py` | sonda real de cada base com a **consulta de exemplo da propria base** | `auditoria_bases_reais.csv` + `auditoria/bases_reais.json` |
| `auditoria/descobre_lacunas.py` | varredura de stubs, `except` silencioso, modulo sem teste e rota chamada sem contrato | `auditoria/lacunas.json` |

Correcoes com causa medida (nao chute):

1. **Crossref `filter=type:retraction`** → HTTP 400. O filtro correto e'
   `update-type:retraction` (medido 200, 81.265 registros).
2. **EBI Search `/ws/rest/all`** → HTTP 400: `/all` nao e' dominio; o dominio
   real e' `uniprot`. Corrigido e medido 200.
3. **ENA `portal/api/search`** → HTTP 500 em 4 variantes de sintaxe (falha do
   servidor). Base mantida com o motivo registrado e alternativa funcional
   `sra_study` (EBI Search, dominio `sra-study`, medido 200).
4. **Ensembl `lookup/symbol`** → 400 para simbolo desconhecido. Trocado por
   `xrefs/symbol`, que devolve lista vazia (estado `VAZIO`) em vez de erro.
5. **NOMAD** `{"query": {"query": ...}}` → 422 "query is not a doc quantity".
   Corpo valido medido: `{"query": {"results.material.elements": "C"}}` → 200.
6. **CORDIS** `payload.results.project` nao existia; o caminho real e'
   `payload.results` (medido 200 com `title`/`rcn`).
7. **IPEADATA** `contains(...)` → 400 "query specified in the URI is not valid";
   OData4 aceita `startswith(SERNOME,'PIB')` → 200.
8. **openFDA** devolve **404 com `code: NOT_FOUND`** quando nao ha resultado —
   isso e' ausencia, nao falha. Base declara `vazio_em_404=True` e o estado
   passa a `VAZIO` (sem esconder 404 de outras bases).
9. **BCB SGS** indexa por codigo numerico de serie; texto livre virou estado
   `INVALIDA` (uso incorreto), separado de `FALHOU` (fonte indisponivel).
10. **dados.gov.br** respondeu **401** em dois endpoints (CKAN e API v2): passou
    a exigir credencial; a base ficou `BLOQUEADA` com `DADOS_GOV_TOKEN`.
11. **data.gov (EUA)** 404 nos tres endpoints testados e **data.govt.nz**
    devolve HTML de WAF (Incapsula): ambas viraram `SEM_API` com o motivo.
12. **Semantic Scholar** 429 persistente sem chave: `SEMANTIC_API_KEY` agora e'
    opcional e, quando presente, vai no cabecalho `x-api-key`.

Pendencias medidas nesta rodada (nada foi maquiado):

| Base | Estado medido | Causa |
|---|---|---|
| `simbad` | FALHOU | ConnectTimeout em `simbad.cds.unistra.fr` e `simbad.u-strasbg.fr` (bloqueio de rede do host) |
| `ensembl` | FALHOU (30,9 s) | host responde em ~20-25 s; timeout de 30 s estourou nesta medicao |
| `oqmd` | FALHOU 502 | erro do servidor do OQMD |
| `ena` | FALHOU 500 | erro do servidor do ENA portal |
| `semantic` | FALHOU 429 | cota sem chave |
| `core`, `dados_gov`, `materials_project`, `patentsview` | BLOQUEADA | `CORE_API_KEY`, `DADOS_GOV_TOKEN`, `MP_API_KEY`, `PATENTSVIEW_API_KEY` |
| 73 bases | SEM_API | fonte sem API de busca (HTML, paga ou descontinuada), com nota propria |



## 8. Rodada 2 — validacao medida

| Prova | Resultado medido |
|---|---|
| `pytest test_bancos_rest.py` | **32 passed**, 27,30 s (import frio) e 9,33 s (cache quente) |
| bloco B (19 arquivos, inclui `test_bancos_rest` e `test_e2e_http`) | **301 passed**, 493,03 s |
| `probe_bancos.py --timeout 30` | **48 bases sondadas**: 38 `OK`, 6 `FALHOU`, 4 `BLOQUEADA`, 0 `VAZIO`; 219,3 s |
| `probe_bancos.py` (rodada anterior, mesma lista) | 39 `OK`, 5 `FALHOU`, 4 `BLOQUEADA`; 140,6 s — a diferenca e' latencia de EBI/Semantic, nao regressao |
| `mapa_arquitetura.py` | **90 caminhos / 97 operacoes**, sem `operationId` duplicado; area "Bancos cientificos" = 4 caminhos |
| `verifica_compat_bancos.py` | 172 entradas em `BANCOS`, alias `arXiv` -> `arxiv`, `b_*` chamavel, `SEM_API` devolve `[]` com motivo em `ultimo_estado()` |
| `descobre_lacunas.py` | 119 modulos varridos, 0 erro de sintaxe, **0** funcao stub em `bancos_completos` (antes 109), 0 rota `/api` sem contrato |

Correcao de contrato achada ao gerar a arquitetura: `/health` estava publicado
**duas vezes** (`app.py` e `api_dados.py`, ambas com a funcao `health`),
produzindo `operationId` duplicado (`health_health_get`) e sombreando a rota de
`api_dados` no app principal. A funcao de `api_dados` passou a se chamar
`health_dados` — o caminho `/health` e' mantido porque `test_plataforma_ak`
monta esse router sozinho e ali ele e' a rota de saude do servico — e o app
principal publica o mesmo status em `/api/dados/health`, agora alcancavel, com
teste e2e proprio.
