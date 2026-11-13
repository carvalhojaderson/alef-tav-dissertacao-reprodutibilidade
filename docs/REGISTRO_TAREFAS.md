# Registro central de tarefas — ALEF-TAV (31/10/2026)

Pedido pela ordem permanente de desenvolvimento autonomo. Cada linha diz o
estado **medido**, o artefato que prova e o que falta. Nada aqui e' "concluido"
so porque existe arquivo: so entra em *Concluido e comprovado* o que tem
execucao registrada.

## 1. Concluido e comprovado

| Tarefa | Prova |
|---|---|
| 396 testes da suite anterior (19 arquivos) verdes | `auditoria/final_coleta.txt`, `auditoria/final_novos.txt`, bloco A 131 passed + bloco B 265 passed |
| Import quebrado `fermilink_bridge` corrigido com modulo real | `test_fermilink_bridge.py`: 8 passed |
| Protocolo MCP implementado (cliente JSON-RPC 2.0 + servidor de referencia) | `test_mcp_alef.py`: 19 passed; handshake real 0,49 s |
| Voz (TTS/STT) ligada ao app com estado por provedor | `test_voz.py`: 15 passed; `/api/voz/saude` 200 |
| `orquestrador_cientifico` reconstruido e exposto | `test_orquestrador.py`: 14 passed |
| Base CORE adicionada com trava de credencial | 3 testes novos; `CORE_API_KEY` exigida |
| Coleta do pytest destravada (`conftest.py` por caminho) | `--collect-only -q`: 396 coletados, 0 erros |
| CORS/rotas ESG, harness 195, motores reais | `auditoria/h195_total.json`, `boot_real.json` |
| **109 stubs de "187 bancos" eliminados** | `bancos_rest.py` + `bancos_completos.py` reescrito; `pytest test_bancos_rest.py`: **32 passed** |
| **44 bases cientificas consultando HTTP de verdade** | `probe_bancos.py`: 48 sondadas, **38 OK** nesta medicao (39 na anterior), 4 bloqueadas por credencial, 0 vazias; `auditoria_bases_reais.csv` |
| Rotas de bancos no app | `test_e2e_http.py`: 4 testes novos (inventario, saude, 404, bloqueio) + app montado; `docs/ARQUITETURA.md` com a area "Bancos cientificos" |
| `operationId` duplicado de `/health` eliminado do contrato | funcao `api_dados.health_dados`; `mapa_arquitetura.py` roda sem o aviso |
| Varredura de lacunas por AST (stub, except silencioso, modulo sem teste) | `auditoria/descobre_lacunas.py` -> `auditoria/lacunas.json` |
| Bloco B da suite (19 arquivos, com bancos + e2e) | **301 passed**, 493,03 s (`auditoria/final_blocoB2.txt`) |
| Terminal que abortava comandos longos diagnosticado e corrigido na raiz | `docs/DIAGNOSTICO_TERMINAL.md` com a tabela de medicoes; causa: processo em foreground encerrado em ~200 ms |
| Antiloop real (nao decorativo) | `auditoria/runner.py`: ledger `auditoria/execucoes/ledger.jsonl`, digest do comando + hash dos arquivos observados, codigo 3 reaproveitando resultado anterior, `--forcar` |
| Fila supervisora com limite por etapa e recuperacao | `auditoria/fila.py`: `fila_progresso.json`, `fila.log`, `fila_done.json`, `fila.pid` (encerra a fila anterior presa), codigo 124 em estouro de tempo |
| Aba Gradio "Bancos cientificos" (consulta unica + multi-base) | `app.py` + `test_ui_bancos.py`: **11 passed**, 160,18 s na fila de 01/11 18:41 (`auditoria/fila/ui_bancos.out.txt`) |
| Exportacao da ultima busca em JSON e CSV (reproduz inclusive falha) | 3 testes em `test_ui_bancos.py`; arquivo gravado em `auditoria/consultas/` (ignorado pelo git), conteudo conferido linha a linha no CSV e por `json.load` no JSON |
| Antiloop de **falha recorrente** provado por execucao, nao por leitura | `auditoria/verifica_antiloop.py` (etapa `antiloop`): o mesmo comando que falha com codigo 9 e' executado 3x -> **9, 9, 5**, com mensagem `[antiloop]` na terceira (`auditoria/fila/antiloop.out.txt`) |
| Supervisor que **confirma** a morte do processo | `fila.py`: `_vivo` (`tasklist`) + `_matar` (taskkill limitado + verificacao ativa); encerrou de fato o orfao pid 19124 que sobrevivia desde 16:29 (`fila.log` 18:32:55) |
| Transporte de shell que sobrevive a queda do terminal | `powershell -NoProfile -Command "\& '<python>' '<script>'"` + `auditoria/desanexar.py` (`DETACHED_PROCESS`); `auditoria/finalizar.py` faz fila + commit em uma chamada |
| **Prazo de arranque do MCP separado do prazo de requisicao** | `mcp_alef/protocolo.py`: `_prazo_de_arranque()` (60 s, `ALEF_MCP_PRAZO_INICIO`) so no `initialize`; requisicao continua 20 s. Teste `test_arranque_lento_nao_e_confundido_com_requisicao_estourada` (servidor que leva 2 s no handshake e 5 s na resposta) |
| **`FALHOU` deixou de ser `BLOQUEADA`** | `mcp_alef/registro.py`: falha medida (prazo, processo morto, erro JSON-RPC) grava `FALHOU` com `tentativas`; `BLOQUEADA` ficou reservada a pre-requisito ausente. Teste `test_servidor_que_falha_fica_falhou_e_nao_bloqueado` |
| **Orcamento do motor por medicao, nao constante** | `universal.py`: `TEMPO_POR_MOTOR = {"neuro": 70, "solido": 90}` + `_prazo_do_motor()` (env `ALEF_MOTOR_PRAZO_S_<MOTOR>` / `ALEF_MOTOR_PRAZO_S`); 3 testes em `test_motor_real_prazo.py` |

## 2. Em desenvolvimento

| Tarefa | Estado | Proximo passo |
|---|---|---|
| Aba Gradio "Bancos cientificos": busca multi-base + exportacao JSON/CSV | **pronta e medida e revalidada**: 11 passed sozinha e dentro de `blocoB` (01/11 20:49) | — |
| Antiloop: bloqueio de falha recorrente (codigo 5) em `auditoria/runner.py` | **provado por execucao** (`antiloop`: 9, 9, 5 em 2,44 s) | — |
| `auditoria/desanexar.py` (lancador DETACHED_PROCESS) | **validado no uso real** (pid 19124, 01/11 16:29 e 17:03) | — |
| `auditoria/fila.py`: orfao sobrevivente ao `taskkill` contaminava as etapas seguintes | **corrigido** (`_vivo`/`_matar`, aborta com codigo 6) | exercitar o caminho de aborto (nao forcado: depende de um estouro real) |
| MCP: arranque de processo cobrado no prazo de requisicao | **corrigido**: `_prazo_de_arranque()` (60 s) so no `initialize`; requisicao segue 20 s | — |
| MCP: falha medida aparecia como `BLOQUEADA` | **corrigido**: estado `FALHOU` com `tentativas`; `BLOQUEADA` so para pre-requisito | — |
| Motor `solido` com prazo fixo de 25 s (medicao real: 28,6 s) | **corrigido**: `TEMPO_POR_MOTOR` + `_prazo_do_motor()` (90 s para `solido`) | — |

Pendencia de execucao: entre 16:50 e 18:32 o terminal integrado ficou inerte.
O transporte que voltou a funcionar foi shell aninhado
(`powershell -NoProfile -Command "& '<python>' '<script>'"`, ver
`docs/DIAGNOSTICO_TERMINAL.md` §8). O script abaixo executa, em sequencia e
sozinho, tudo o que falta e so commita se a fila ficar verde:

```
python auditoria/finalizar.py     # auto-desacopla e retorna; acompanhar finalizacao.json
```

Etapas: `compileall` (inclui `mcp_alef/*.py` e `test_mcp_alef.py`), `valida`
(**43 passed**, 37,63 s — `test_mcp_alef.py` + `test_motor_real_prazo.py`, feedback
curto antes do bloco longo), `antiloop` (autoteste do antiloop, **medido 2x:
46,99 s e 4,65 s, codigo 0**), `ui_bancos` (**11 passed**, 21,09 s) e `blocoB`
(20 arquivos, **319 passed**, 85,81 s).

### 2.1 Rodada de 01/11/2026, 20:36-20:50 — verde de ponta a ponta

Fila completa pelo supervisor, sem orfao em disputa de CPU (o pid 19124 foi
encerrado as 18:32 com verificacao ativa):

| Etapa | Codigo | Duracao medida | Resultado |
|---|---|---|---|
| `compileall` (17 arquivos) | 0 | 0,97 s | inclui `mcp_alef/protocolo.py`, `mcp_alef/registro.py` |
| `antiloop` | 0 | 2,44 s | 9, 9, **5** com `[antiloop]` na terceira execucao |
| `valida` | 0 | 40,68 s (fila) / **37,63 s** (pytest) | **43 passed** |
| `ui_bancos` | 0 | 24,49 s (fila) / **21,09 s** (pytest) | **11 passed** |
| `blocoB` (20 arquivos) | 0 | **88,54 s** (fila) / **85,81 s** (pytest) | **319 passed** |

Commit: `35c7a67` (`bancos: busca multi-base ... MCP separa prazo de arranque
(60 s) ... motor solido com orcamento medido (90 s)`), gravado em
`auditoria/finalizacao.json` (`commitado: true`).

Antes desta rodada, o mesmo `blocoB` tinha medido 922,73 s e 811 s **com falha**.
A diferenca nao foi "mais uma tentativa": foram tres causas medidas, cada uma com
teste que a prende -- (1) orfao dividindo CPU (supervisor que confirma a morte),
(2) `initialize` cobrado no prazo de requisicao (arranque de processo custa
segundos), (3) motor `solido` com 25 s quando a medicao real era 28,6 s.

## 3. Concluido e comprovado nesta sessao (01/11/2026)

As tres correcoes de `/health` que estavam pendentes foram executadas e
medidas. Nenhum numero abaixo foi estimado: cada linha corresponde a saida de
`auditoria/fila/<etapa>.out.txt` (fila supervisionada, ver
`docs/DIAGNOSTICO_TERMINAL.md`).

| Etapa | Comando | Resultado medido |
|---|---|---|
| `compileall` | 14 arquivos, inclui `app.py`, `api_dados.py`, `bancos_rest.py`, `test_ui_bancos.py` | exit 0, 50,02 s |
| `bancos_unit` | `pytest test_bancos_rest.py -q` | **32 passed**, 39,96 s |
| `arquitetura` | `python auditoria/mapa_arquitetura.py` | 90 rotas / 97 operacoes; `/api/dados/health` presente; `/health` com `operationId` `health_dados_health_get` (sem duplicata); 4 operacoes em `bancos_rest` |
| `e2e` | `pytest test_e2e_http.py -q` | **34 passed**, 127,14 s (inclui `test_saude_do_banco_em_caminho_proprio`) |
| `ui_bancos` | `pytest test_ui_bancos.py -q` | **6 passed**, 30,32 s |

| Arquivo | Mudanca | Estado |
|---|---|---|
| `api_dados.py` | `health` -> `health_dados` (caminho `/health` mantido) para eliminar `operationId` duplicado | comprovado pelo mapa de arquitetura e pelo bloco A |
| `app.py` | nova rota `/api/dados/health` + aba Gradio "Bancos cientificos" (consulta unica e multi-base) | comprovado por `e2e` e `ui_bancos` |
| `test_e2e_http.py` | teste novo `test_saude_do_banco_em_caminho_proprio` | comprovado (34 passed) |
| `test_ui_bancos.py` | 6 testes do contrato da aba (sem rede) | comprovado (6 passed) |


## 4. Bloqueado por credencial, servico ou infraestrutura externa

| Item | Requisito |
|---|---|
| `CORE_API_KEY`, `DADOS_GOV_TOKEN`, `MP_API_KEY`, `PATENTSVIEW_API_KEY` | credencial no ambiente (as bases ficam `BLOQUEADA`, sem consulta) |
| `EPO_OPS_KEY`, `LENS_API_TOKEN`, `BASE_API_KEY`, `DIMENSIONS_KEY`, `MENDELEY_TOKEN`, `SCINOTE_TOKEN`, `COMPTOX_API_KEY` | idem (bases declaradas `BLOQUEADA`/`SEM_API` com o nome da variavel) |
| MCP externos (Mini Course Generator, NotebookLM, Obsidian) | comando real do servidor em `mcp_servers.json`; sem ele nao ha handshake |
| TTS/STT reais | `pip install edge-tts` e `pip install openai-whisper` |
| ElevenLabs / Groq | credencial + aprovacao da implementacao |
| 119 `IMPLEMENTACAO_SEM_AMBIENTE` / 48 `APENAS_CATALOGADO` (harness 195) | ambiente/Docker por componente, com prova individual |
| `simbad`, `oqmd`, `ena`, `ensembl`, EBI Search | falha do lado da fonte medida em 31/10/2026 (timeout, 502, 500, latencia); sem acao local que resolva |

## 5. Ainda nao implementado (escopo tecnico conhecido)

| Item | Por que nao entrou | Dificuldade |
|---|---|---|
| Busca textual de `scielo`, `redalyc`, `latindex`, `jstage`, `pubpeer`, `echa` | fontes so publicam HTML/planilha; exigiria parser dedicado e fragil, e nenhuma delas bloqueia uma funcionalidade da plataforma | media |
| KAKEN (JSPS), `datos_es`, `datos_co`, `data_gov_sg` | API existe mas com contrato por colecao/ID, nao por texto livre | media |
| 73 bases `SEM_API` | decisao registrada: nao inventar endpoint; cada uma tem nota explicando o porque | — |
| Consolidar `/health` num caminho unico | hoje `api_dados` publica `/health` (usado quando o router roda sozinho) e o app publica `/api/dados/health`; unificar exige atualizar `test_plataforma_ak` | baixa |
| Traducao automatica dos 73 `SEM_API` para parser HTML | cada fonte exigiria parser proprio e fragil; so entra com prova de necessidade | media |

## 6. Ordem de retomada

| Passo | O que fazer | Estado |
|---|---|---|
| 1 | fila supervisionada (`auditoria/fila.py`): compileall, `test_bancos_rest`, mapa de arquitetura, `test_e2e_http`, `test_ui_bancos` | **feito** (5/5 verdes) |
| 2 | bloco A e bloco B completos, gravados em `auditoria/fila/*.out.txt` | **feito** (bloco A 131 passed; bloco B **319 passed** em 85,81 s) |
| 3 | `python auditoria/probe_bancos.py --timeout 30` para atualizar `auditoria_bases_reais.csv` | **feito** (48 sondadas, OK=39; `auditoria_bases_reais.csv`) |
| 4 | `git add -A` + commit do lote (bancos + aba Gradio + antiloop + MCP/motor) | **feito**: `35c7a67`, verde de ponta a ponta (`auditoria/finalizacao.json`) |
| 5 | Proxima funcionalidade: promover as bases `BLOQUEADA` quando houver credencial e ligar o resultado da aba ao orquestrador | pendente |

