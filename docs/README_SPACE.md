---
title: ALEF-TAV Backend
emoji: 🧪
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 8020
pinned: false
---

# ALEF-TAV BIO FARMA ENGINE - backend unificado

Backend Python do assistente cientifico ALEF-TAV: busca bibliografica
multibase, 16 motores de simulacao (`/api/simuladores/universal`), catalogo de
195 componentes cientificos, modelos de adsorcao (Langmuir e Freundlich),
plataforma ESG, entrada/saida de dados e interface Gradio - **tudo no mesmo
processo e na mesma porta**.

## Como este Space roda (SDK Docker)

| Item | Valor |
|---|---|
| SDK | `docker` (campo `sdk` no topo deste README) |
| Porta publica | `8020` (`app_port: 8020`) |
| Imagem base | `python:3.10-slim-bookworm` |
| Comando | `uvicorn app:app --host 0.0.0.0 --port 8020` |
| Dockerfile | `Dockerfile` (raiz do repositorio) |
| Usuario do container | `user` (UID 1000, exigencia do runtime do HF) |

`app.py` publica a interface Gradio **e** a API FastAPI no mesmo ASGI
(`gr.mount_gradio_app`), exatamente como validado na maquina local. Por isso o
container sobe com `uvicorn app:app`: se subisse apenas a interface (o
comportamento do SDK `gradio`), as rotas `/api/*` ficariam mortas.

> O runtime do SDK `gradio` usa Python 3.13. Varios motores do catalogo nao
> publicam wheels para 3.13. Python **3.10** e a versao onde os motores foram
> medidos (`IMPORT_OK` real), por isso a imagem Docker fixa 3.10.

## Camadas de dependencia (o que entra na imagem)

| Camada | Arquivo | Natureza |
|---|---|---|
| 1 | `requirements.txt` | deps do app - **obrigatoria** |
| 2 | `requirements-motores-nucleo.txt` | motores **provados** (import real OK) - **obrigatoria** |
| 3 | `requirements-motores-simulacao.txt` | 31 componentes INTEGRADOS - best-effort, com teto de tempo |
| 4 | `requirements-motores-bloqueados.txt` | deps dos bloqueados - OFF (`COM_BLOQUEADOS=0`) |

### Por que a camada 3 tem teto de tempo
Alguns pacotes arrastam stacks enormes (`chgnet` -> `torch`; `napari` e
`activity-browser` -> Qt). O build do Space tem tempo limitado, entao a camada
3 instala **um pacote por vez** com `timeout` por pacote e um orcamento global
(`ORCAMENTO_EXTRAS_SEG=900`). Assim a imagem **sempre termina de construir** e
o Build log diz exatamente quais pacotes entraram e quais ficaram de fora.

### Build-args (Variables do Space viram build-args no HF)

| Variable | Padrao | Efeito |
|---|---|---|
| `COM_MOTORES_EXTRA` | `1` | `0` = imagem enxuta (so o nucleo provado) |
| `COM_BLOQUEADOS` | `0` | `1` = instala as deps dos componentes bloqueados |
| `ORCAMENTO_EXTRAS_SEG` | `900` | teto global de tempo da camada 3 |
| `TIMEOUT_POR_PACOTE_SEG` | `240` | teto de tempo por pacote |

Nenhum build-arg e obrigatorio: sem nenhuma Variable o build usa os padroes
acima e nao falha.

## Endpoints de verificacao

| Rota | O que prova |
|---|---|
| `GET /health` | processo no ar (`{"status":"ok","bases":true,"ia":true,"sims":true}`) |
| `GET /api/simuladores/diagnostico-motores` | ambiente real da imagem, catalogo de 195 e import de cada motor |
| `POST /api/simuladores/universal` | motor de simulacao (`{"simulador":"md","pergunta":"md"}`) |
| `POST /api/simuladores/adsorcao` | Langmuir/Freundlich com numero calculado |
| `GET /api/catalogo/simuladores` | catalogo completo (195 componentes) + filtros |
| `GET /api/esg/saude` | modulo ESG |
| `GET /api/buscar?pergunta=...` | busca bibliografica multibase |
| `GET /api/mcp/servidores` | servidores MCP com estado medido (`CONFIGURADA`... ou `BLOQUEADA` + requisito) |
| `GET /api/mcp/servidores/eco/ferramentas` | handshake + `tools/list` reais no servidor de referencia |
| `POST /api/mcp/servidores/{id}/ferramentas/{nome}/chamar` | `tools/call` real (login obrigatorio, **so leitura**) |
| `GET /api/voz/saude` | provedores de TTS/STT, o que falta e os limites |
| `POST /api/voz/tts` / `POST /api/voz/stt` | sintese (MP3) e transcricao; 503 com `requisito` sem provedor |
| `POST /api/orquestrador/plano` | areas da pergunta + funcoes reais de cada modulo (AST) |

## Escopo honesto do que esta integrado

O catalogo tem 195 componentes. Cada um tem um `estado` medido e gravado em
`componentes_195_estado.json`:

* **INTEGRADO** - o componente foi executado (calculo real ou resposta HTTP
  real de API/banco de dados) e a prova esta no proprio registro;
* **BLOQUEADO** - exige container, binario externo, licenca ou middleware que
  este runtime nao oferece. `integration_status` e `blocking_reason` dizem o
  motivo. Nenhum componente bloqueado e anunciado como operacional.

Promover um componente de BLOQUEADO para INTEGRADO exige **resultado
calculado**, nao apenas `import` bem-sucedido (`_retestar_libs.py`).

## Execucao isolada por grupo (registro + executor + Docker)

O catalogo deixou de ser uma lista: agora existe um **registro central** que
resolve, para cada um dos 195 ids, onde ele pode rodar NESTE host.

| Arquivo | Papel |
|---|---|
| `registro_componentes.py` | metadados + `resolver(id)` -> backend, grupo e motivo. Modulo puro: nao importa motor, nao chama rede |
| `executor_isolado.py` | despacha para `local`, `subprocesso`, `docker` ou `remoto`, com limites, timeout, limpeza e mascaramento de credenciais |
| `sondas_componentes.py` | prova cientifica pequena por componente (o numero tem de conferir, nao so importar) |
| `api_componentes.py` | rotas de registro, ambiente, detalhe, execucao, lote e construcao de imagem |
| `infra/gerar_dockerfiles.py` | gera `infra/docker/Dockerfile.<grupo>` + `grupos.json` a partir do registro |
| `teste_componentes_195.py` | percorre o catalogo e grava as 10 evidencias por componente |

### Grupos de imagem (uma imagem atende varios componentes)

| Grupo | Componentes | Base |
|---|---|---|
| `sci-leve` | 24 | `python:3.12-slim-bookworm` + wntr, mesa, pysb, flopy, pybamm, cantera... |
| `sci-pesado` | 12 | `python:3.12-slim-bookworm` + chgnet, matgl, atomate2 (torch) |
| `cli-bio` | 32 | `debian:bookworm-slim` + samtools, blast, hmmer, mafft, minimap2 |
| `cli-hidro` | 13 | `debian:bookworm-slim` + epanet, swmm |
| `cli-quim` | 7 | `debian:bookworm-slim` + openbabel, vina |
| `cli-geo` | 6 | `debian:bookworm-slim` + gdal, grass |
| `r-stats` | 6 | `rocker/r-ver:4.4` + Bioconductor |
| `servico` | 12 | `debian:bookworm-slim` (APSIM, OpenModelica, COPASI) |
| `build` | 41 | `python:3.12-slim-bookworm` + `build-essential/cmake/gfortran` |
| `worker-gui` | 10 | `debian:bookworm-slim` + `xvfb` |
| `nucleo` / `remoto` / `revisao` | 3 / 26 / 3 | sem imagem (processo, HTTP, decisao humana) |

A tag da imagem e o **hash do conteudo do grupo** (`alef-tav/<grupo>:<hash>`):
mudar um pacote muda a tag, entao imagem antiga nao e reaproveitada por engano e
imagem inalterada nao e reconstruida.

### O que este host NAO conseguiu construir (bloqueio, nao aprovacao)

Medido em 26/10/2026 neste Windows: `docker` nao existe no PATH,
`C:\Program Files\Docker` nao existe, `wsl --status` nao responde, e
`podman`/`nerdctl`/`buildah`/`vagrant`/`multipass` tambem nao. Consequencia
registrada no relatorio dos 195:

* `imagem_construida = 0` para **todos** os 195 componentes (nenhuma imagem foi
  construida, porque nao ha runtime de container);
* os 29 componentes com `ambiente_iniciado` iniciaram em **processo local**,
  nao em container;
* `executor_isolado` recusa construir/rodar sem Docker (`INDISPONIVEL`,
  "docker nao encontrado no host") em vez de fingir execucao.

Os Dockerfiles e `infra/docker/grupos.json` sao **artefatos prontos**, gerados a
partir do registro (`python infra/gerar_dockerfiles.py`). Gerar Dockerfile nao e
construir imagem, e construir imagem nao e executar componente: os tres estados
ficam separados no relatorio. Para sair do bloqueio e' preciso instalar um
runtime de containers (Docker Desktop + WSL2, ou Docker Engine em Linux) numa
maquina com virtualizacao habilitada - decisao e instalacao de sistema, fora do
que este repositorio pode fazer sozinho.

### Garantias aplicadas no despacho

* o id precisa existir no catalogo -> `argv` vindo de fora **nunca** e executado;
* `docker run --rm` sem `--privileged`, sem socket, `--network none` por padrao,
  `--read-only`, `--cap-drop ALL`, `no-new-privileges`, usuario 1000:1000;
* memoria, cpus, pids e tempo sempre limitados; timeout mata o conteiner e
  confirma que ele saiu (`docker ps -a --filter`);
* toda saida passa por mascaramento (`sk-`, `hf_`, `gsk_`, `nvapi-`, `AIza`,
  `Bearer`, `api_key=`).

### Estados que nunca sao confundidos

`teste_componentes_195.py` grava, por componente, `inventariado`,
`implementacao_identificada`, `dependencias_resolvidas`, `imagem_construida`,
`ambiente_iniciado`, `simulacao_executada`, `resultado_validado`,
`integracao_api_aprovada`, `teste_falha_timeout` e `situacao`. Um componente
"catalogado" nao aparece como "executado", e "executado" nao aparece como
"validado" sem o numero conferir.

```
python teste_componentes_195.py                      # catalogo inteiro -> JSON
python teste_componentes_195.py --lote 25            # lote limitado
python teste_componentes_195.py --inicio 40 --lote 40 --saida auditoria/h195_b2.json  # bloco
python teste_componentes_195.py --sem-rede           # nao consulta APIs publicas
python auditoria/mescla_harness.py                   # junta os blocos e prova 195/195
python infra/gerar_dockerfiles.py                    # Dockerfiles + grupos.json
```

Varredura completa registrada em 31/10/2026 (cinco blocos de 40, um processo
cada, `--sem-rede`): **195/195 componentes cobertos, 0 faltando, 0 duplicados,
154,5 s somados**. Resultado: 12 `VALIDADO` (ase, brian2, cobrapy, flopy,
matminer, mesa, open-babel, pybamm, pymatgen, rasterio, rdkit, wntr), 119
`IMPLEMENTACAO_SEM_AMBIENTE`, 48 `APENAS_CATALOGADO`, 16
`DEPENDENCIAS_OK_SEM_EXECUCAO`. Nenhum componente ficou em "executou sem
validar": quem executa, confere numero.
`auditoria/mescla_harness.py` derruba o exit code se faltar id, se houver id
repetido ou se algum `VALIDADO` nao tiver prova de API -- os tres numeros acima
sao conferidos por codigo, nao por leitura.


## Variaveis de ambiente de operacao


Credenciais nao ficam no codigo: `chaves_config.py` so le do ambiente
(`NVIDIA_API_KEY`, `GROQ_API_KEY`, `SCOPUS_API_KEY` ou `ELSEVIER_API_KEY`,
`GOOGLE_API_KEY`), `gemini.py` le `GEMINI_API_KEY` / `GOOGLE_API_KEY` /
`GOOGLE_KEY` e `conectores_academicos.py` usa `UNPAYWALL_EMAIL`. Sem a
variavel o recurso correspondente fica indisponivel e o app continua no ar com
o fallback analitico - nada quebra e nada e inventado.

| Variable | Padrao | Efeito |
|---|---|---|
| `DIAGNOSTICO_PUBLICO` | ausente (fechado) | `1` libera `GET /api/diagnostico-montagem`; sem ela a rota responde **403** e nao expoe caminhos, usuario e ambiente do host |
| `IA_CONVERSA_ATIVA` | `0` (desligado) | `1` liga a camada conversacional do `ia_conversa` no chat (consome provedor de LLM); desligada, a resposta do chat e 100% deterministica |
| `ALEF_TAV_PORTA` | `8020` | porta usada quando o app sobe via `python app.py` |
| `ALEF_SEM_PREAQUECER` | ausente (aquece) | `1` desliga o pre-aquecimento dos motores na thread principal (import de ~10 motores). Usado pelos testes; o boot de producao aquece |
| `ALEF_SO_ANALITICO` | ausente (motores ligados) | `1` desliga os motores reais e usa so a formula analitica. **Nunca em producao**: existe para provas de contrato HTTP (e2e) nao pagarem o custo de uma simulacao real |
| `ALEF_HARNESS_AQUECER` | `rapido` | aquecimento do harness dos 195: `rapido` = `ase`+`rdkit`+`pymatgen` (~86 s medidos neste host), `completo` = pilha toda (~4 060 s medidos), `desligado` = nao aquece (volta o falso timeout por importacao) |

## Suite de testes

15 arquivos `test_*.py` + 1 novo de prazos (16 no total; `test_solido_emt.py`
entrou nesta rodada), todos executaveis offline (bases bibliograficas e
provedores de IA sao substituidos por stubs/mocks nos testes de integracao):

```
python -m pytest test_esg_issacar.py test_plataforma_ak.py ^
  test_llm_client.py test_regressao_langmuir.py test_modelos_analiticos_v2.py ^
  test_integracao_modelos_v2.py test_roteador_modelos_v2.py ^
  test_universal_fluxo.py test_seguranca_credenciais.py ^
  test_solido_emt.py test_busca_multibase.py test_e2e_http.py ^
  test_registro_componentes.py test_executor_isolado.py ^
  test_componentes_api.py test_motor_real_prazo.py -q
```

Os quatro ultimos cobrem a arquitetura de execucao isolada e **nao precisam de
Docker**: o `Executor` aceita um runner injetado, entao os testes provam a
construcao dos argumentos (`--cap-drop ALL`, `--read-only`, `--network none`,
limites de memoria/cpu/pids), o tratamento de timeout com remocao do conteiner,
o mascaramento de credenciais e o 404 para id fora do catalogo.
`test_motor_real_prazo.py` trava o defeito medido em 26/10/2026: o prazo do
motor real media a **importacao** (85 s para `ase.build` + `ase.calculators.emt`)
e reprovava motor instalado, devolvendo a formula analitica em silencio. Ele
cresceu de 10 para 18 testes nesta rodada: 3 travam a **proveniencia do
fallback** (`motor_situacao`), 3 travam o **modo de aquecimento do harness** e 2
travam o **filtro de submodulos** em `aquecer()`/`aquecer_detalhado()`.

```
python -m pytest test_registro_componentes.py test_executor_isolado.py ^
  test_componentes_api.py test_motor_real_prazo.py -q
```

Esse conjunto tinha **75 testes** antes desta rodada; com os 8 testes novos de
`test_motor_real_prazo.py` passa a **83** (o numero medido sai na ultima linha da
execucao - o comando esta no roteiro de validacao, etapa 2).


`test_e2e_http.py` sobe o app real (`gr.Blocks` + FastAPI via `TestClient`) e
verifica `/health`, o catalogo, `/api/simuladores/universal`,
`/api/simuladores/adsorcao` (Langmuir), a trava do diagnostico (403/200) e o
fluxo do `responder` com a camada conversacional desligada e ligada. Dois testes
entraram nesta rodada para o `solido`: o payload HTTP tem de trazer coesao real
(`~3,51 eV/atomo` no Cu, `|E_cristal| < 0,05`) e o `a` em angstrom e em metro
tem de descrever a mesma celula:

```
python -m pytest test_e2e_http.py -v   # 24 testes com ALEF_SO_ANALITICO=1
```

Ultima execucao registrada neste ambiente (`C:\Users\PC\miniconda3\envs\holocine\python.exe`,
Python 3.10.19, gradio 5.50.0, pytest 9.1.1): **332 passed, 0 failed** somando os
**16 arquivos** de teste, em dois blocos medidos -- 201 passed em 597,8 s
(8 arquivos, inclui `test_solido_emt.py`) + 131 passed em 122,3 s (8 arquivos,
inclui `test_e2e_http.py`). Antes desta rodada eram 322 passed em ~390 s e, antes
disso, 234 passed em 851 s. Nenhum teste foi desativado;
os testes que dependem de motor externo ausente (`pybamm`, `brian2`, `wntr`,
`mesa`, `cobra`) verificam o fallback analitico e o rotulo `fonte: "analitico"`,
nao uma simulacao que nao aconteceu.

O detalhamento por arquivo, o resultado da auditoria executavel dos 113
simuladores (113 OK, 0 parametros constantes) e o indice de todas as provas
estao em `auditoria/LEIA-ME.md`; `docs/ROTEIRO_VALIDACAO.md`, secao 3, traz a
mesma tabela de medicoes.

Duas provas de boot completam a suite: `python infra/rodar_suite_antiga.py`
(um processo por arquivo) deu **215 passed, 0 falhas** nos 10 arquivos antigos,
e `python auditoria/boot_real.py` sobe o app montado em uvicorn real e confere
8 sondas HTTP -- `/` 200 com interface Gradio montada, `/health` 200, catalogo
200, `/api/componentes/registro` 200 com **195 componentes**,
`diagnostico-motores` 200, adsorcao 200, universal 200 e
`/api/diagnostico-montagem` **403** sem a flag de ambiente. Boot medido: 16,2 s
com cache quente, 61,7 s a frio.

### Lote 2 (26/10/2026): numeros medidos, nao estimados

Execucao em sequencia neste host (saidas em `r2_1_e2e.txt` ... `r2_4_rel.txt`):

| Medicao | Resultado |
|---|---|
| `test_e2e_http.py` com `ALEF_SO_ANALITICO=1` | 22 passed, ~6 min |
| 10 arquivos antigos num unico `pytest` | 1 failed, 174 passed, 38 errors, 1 700 s |
| pre-aquecimento da pilha inteira na thread principal | 4 144,9 s (69 min) |
| `infra/gerar_relatorio.py` | `EXIT_REL=0` (markdown regerado) |

Custo do aquecimento, modulo por modulo (mesmo processo, thread principal):

| modulo | segundos | modulo | segundos |
|---|---|---|---|
| pybamm | 1337,8 | ase | 64,1 |
| wntr | 1294,5 | flopy | 43,9 |
| mesa | 706,2 | rdkit | 21,9 |
| cobra | 321,0 | pymatgen | 0,08 |
| brian2 | 297,1 | matminer | `IMPORT_FALHOU` |

O custo e' de **ambiente** (import), nao de ciencia: e' ordens de grandeza maior
que o calculo. Consequencias aplicadas:

* `aquecer()` e `aquecer_detalhado()` importam os submodulos **so dos motores
  pedidos** - antes, pedir `ase` arrastava pybamm/wntr/mesa/cobra;
* o harness declara o modo em `aquecimento.modo` no proprio JSON
  (`ALEF_HARNESS_AQUECER`, ver tabela de variaveis); o modo `completo` pede
  `integracoes_reais.MODULOS_DO_APP` (10 pacotes, inclui brian2/flopy/matminer).
  Antes ele chamava `aquecer(None)`, cujo default sao **7** pacotes: `neuro`
  (brian2, 297 s medidos) ficava frio e os 4 060 s acima nao eram reproduziveis
  por esse caminho. Corrigido em 27/10/2026, com teste;
* os 9 submotores reportaram `IMPORT_OK` nos seus submodulos (9/9 chaves, 21/21
  imports), o que **nao** e' o mesmo que calculo correto.

Sonda de motores depois do aquecimento (entrada `"teste"`, sem parametros):

| motor | tempo | motor real? | por que |
|---|---|---|---|
| `cristalografia` | 4,9 s | sim (pymatgen) | calculo pequeno |
| `epidemia` | 8,9 s | sim (Mesa ABM) | calculo pequeno |
| `solido` | 28,6 s | nao | 28,6 s > prazo de 25 s entao; a causa real era o `MemoryError` da unidade, ver Lote 3 |

Nota (31/10/2026): a coluna `motor real?` desta tabela e' o que a sonda de 26/10
mediu com prazo de 25 s. Depois das correcoes do Lote 3 o `solido` executa no
motor ASE+EMT em **4,20 s** e sem `motor_situacao` (`infra/inventario_simuladores.py
--somente solido --prazo 120`); a linha continua aqui como registro do defeito,
nao como estado atual.
| `hidro` | 26,9 s | nao | idem |
| `micro` | 25,8 s | nao | idem |
| `molecular` | 1,0 s | nao | entrada sem SMILES |

Por isso `universal._com_motor_real` passou a marcar o fallback com
`motor_situacao` (`prazo_excedido`, `motor_falhou: ...` ou
`motor_sem_resultado`) e `motor_prazo_s`. Antes, "motor instalado e lento" e
"componente sem motor" devolviam o **mesmo** dicionario - dois estados
diferentes com a mesma cara.

O campo `fonte` tambem estava contraditorio: `_rodar_simulacoes_com_bridge`
sobrescrevia `fonte = "analitico"` **sempre**, entao o payload saia com
`motor: "pymatgen (rede cristalina real)"` e `fonte: "analitico"` juntos. Agora
`fonte` diz a origem do numero: `motor_real` quando veio do motor,
`analitico` quando veio da formula interna (e `motor_situacao` explica a queda,
quando houve). O teste que exigia `fonte == "analitico"` passava sem provar
nada; agora ele exige coerencia entre `fonte` e `motor`, e ha dois testes
diretos em `test_universal_fluxo.py`.

### Os 38 erros do lote antigo nao sao defeito do app

Todos vinham do mesmo fixture (`sessao_login`) recebendo 409 "E-mail ja
cadastrado". Cada arquivo fixa `ALEF_TAV_DATABASE_URL`/`ALEF_TAV_DIR_DADOS` no
topo do modulo, mas `nucleo_dados`/`api_dados` resolvem a configuracao **no
import**: so o primeiro arquivo importado no processo vale, e os demais herdam o
banco e as pastas dele. O mesmo acoplamento reprovou
`test_k_diretorios_respeitam_variavel_de_ambiente` (que exige
`api_dados.DIR_DADOS` vindo do env daquele arquivo). Correcoes aplicadas:

* `sessao_login` aceita 409 e prova a credencial pelo login; o caminho de erro
  continua coberto explicitamente em `test_b_email_duplicado_409`;
* `infra/rodar_suite_antiga.py` roda **um processo por arquivo**, que e' o
  isolamento que esses testes sempre presumiram:

```
python infra/rodar_suite_antiga.py                       # os 10 arquivos
python infra/rodar_suite_antiga.py --somente test_plataforma_ak.py
```

### Lote 3 (31/10/2026): o `solido` publicava a energia do cristal como coesao

Dois defeitos no caminho **real** do simulador `solido`
(`integracoes_reais.solido_emt`, ASE + EMT), ambos medidos e corrigidos nesta
rodada -- nao sao revisao estatica: cada um tem teste e numero.

1. **Convencao do EMT.** O `ase.calculators.emt` subtrai `E0` de cada atomo
   (convencao ASAP), entao um cristal perfeito devolve ~0 eV/atomo e o atomo
   isolado devolve `+E0`. O codigo publicava `get_potential_energy()` com o
   rotulo `E_coesao_eV_atomo`: no Cu saia `-0,0049 eV/atomo` onde a coesao real
   e' `3,5157` -- sinal trocado e erro de ~700x. Agora o campo e'
   `E_coesao = E_atomo_isolado - E_cristal`, e o payload publica tambem
   `E_cristal_eV_atomo` e `E_atomo_isolado_eV`, para a conta ser auditavel:

   | metal | `E_coesao_eV_atomo` medido | `E0` do EMT | desvio |
   |---|---|---|---|
   | Cu | 3,5157 | 3,51 | +0,16 % |
   | Ag | 2,9584 | 2,96 | -0,05 % |
   | Al | 3,2815 | 3,28 | +0,05 % |
   | Ni | 4,4488 | 4,44 | +0,20 % |

2. **Unidade do parametro de rede.** O default era `5,43e-10` **metro** (o
   diamante do Si) lido como angstrom: `bulk()` recebia uma celula de
   5,43e-10 angstrom, o ASE estourava `MemoryError` e a camada de motores caia
   no fallback analitico **em silencio** -- o inventario antigo registrava
   `motor_falhou` no `solido`. Agora `_rede_em_angstrom()` normaliza (metro ou
   angstrom; `a < 1e-8` significa metro), o default de cada elemento vem do
   proprio ASE (`bulk(simbolo, "fcc", cubic=True)`) e ha um limite explicito de
   faixa util (1,5-15 angstrom) que levanta `ValueError` legivel em vez de
   `MemoryError`. `universal.sim_solido` foi alinhado: `a` em angstrom (default
   3,615 do Cu fcc), aceita metro e devolve `parametro_rede_A` **e**
   `parametro_rede_m`.

Provas medidas nesta rodada:

| Prova | Resultado |
|---|---|
| `pytest test_solido_emt.py -q` | **8 passed, 45,3 s**: coesao vs `E0` (2 % de tolerancia, Cu/Ag/Ni/Al com rede de equilibrio do ASE), compressao monotonica da coesao, metro = angstrom, `ValueError` fora da faixa, default vindo do ASE |
| `pytest test_solido_emt.py test_universal_fluxo.py test_e2e_http.py -q` | 45 passed, 144,6 s |
| `python infra/inventario_simuladores.py --somente solido --prazo 120 --acrescentar` | `solido` OK, motor `ASE + EMT (energia de coesao real)`, 4,20 s, **sem** `motor_situacao` (nenhum fallback) |
| cenario `sem_parametros` do inventario | `E_coesao_eV_atomo = 3,5157`, `E_cristal_eV_atomo = -0,0057`, `parametro_rede_m = 3,61e-10` (= 3,61 angstrom) |
| cenario `com_defaults` do inventario | `E_coesao_eV_atomo = 3,5149`, `parametro_rede_A = 3,615`, `parametro_rede_m = 3,615e-10` |
| `test_e2e_http.py` (2 testes novos) | coesao real pelo HTTP (`~3,51 eV/atomo`, `|E_cristal| < 0,05`) e coerencia angstrom/metro no mesmo payload |
| `pytest` completo (16 arquivos) | 332 passed, 0 failed |
| `python auditoria/boot_real.py` | 8/8 sondas OK, 195 componentes, boot 23,0 s |

Armadilha registrada junto: `bulk(sim, "fcc")` **sem** `cubic=True` devolve a
celula primitiva, cujo `cell[0][0]` e' 0 -- o `a` lido virava 0, caia no default
3,615 e comprimia Ag/Al/Ni, derrubando a coesao em ~30 %. Toda rede de
referencia no teste usa `cubic=True`.


### Lote 4 (31/10/2026): artefatos que faltavam, e o que a ausencia escondia

Ponto de partida: `auditoria/varre_imports.py` (novo) leu o AST dos **107**
modulos vivos e respondeu quatro perguntas. Duas respostas mudaram o escopo:

1. `universal.py:1686` importa `fermilink_bridge` — e o modulo **nao existia**.
   O `except ImportError` transformava ausencia em `_BRIDGE_OK = False`, sem
   nenhum registro: o caminho acelerado nunca era tentado e ninguem sabia por que.
2. Nao havia **nenhum** cliente ou servidor MCP no repositorio. As rotas
   `/api/mcp/minicurso`, `/api/mcp/obsidian` e `/api/mcp/notebooklm/exportar`
   geram arquivo local — nao falam o protocolo. "MCP integrado" era, ate aqui,
   um nome.

O que foi construido (codigo + teste, nao andaime):

| Artefato | O que faz | Prova |
|---|---|---|
| `mcp_alef/protocolo.py` | cliente JSON-RPC 2.0 sobre stdio: `initialize` -> `notifications/initialized`, `tools/list` com `nextCursor`, `tools/call`, prazo e erro sanitizado | 19 testes em `test_mcp_alef.py` |
| `mcp_alef/servidor_eco.py` | servidor MCP de referencia: 3 ferramentas de leitura + 1 de escrita (desativada) | handshake real em processo separado, 0,49 s |
| `mcp_alef/registro.py` | catalogo + maquina de estados `MENCIONADA -> CONFIGURADA -> CONECTADA -> TESTADA -> INTEGRADA` / `BLOQUEADA` + recusa de escrita | `somar(2,40) = 42`; `gravar_nota` recusada |
| `api_mcp.py` | 5 rotas (saude, servidores, ferramentas, testar, chamar) | 401 sem login, 403 para escrita, 404 para id invalido |
| `voz.py` + `api_voz.py` | TTS/STT com estado por provedor e `requisito`; 503 em vez de 200 vazio | 15 testes (`test_voz.py`) |
| `api_orquestrador.py` | plano por area + inventario por AST | `"adsorção de metais"` -> `ambiental` |

Correcoes com causa declarada:

* **`orquestrador_cientifico.py`** continha o modulo **duas vezes** e tinha 75
  caracteres `?` no lugar de acentos: `classificar_pergunta("adsorção ...")`
  respondia `multidisciplinar`, porque o termo gravado era `"adsor??o"`. Agora
  normaliza por NFKD e le `utf-8-sig` (23 arquivos do projeto tem BOM).
* **`bases_v5` sem CORE**, base citada na Etapa G. `b_core` entra com
  `CORE_API_KEY`; sem chave fica `funcional=False` e `info_bases()` conta como
  inativa — nao some do inventario e nao finge funcionar.
* **`pytest` sem lista de arquivos abortava**: `_deploy_stage/` tem os mesmos
  `test_*.py` da raiz, e a coleta morria com 6 `import file mismatch`. O
  `conftest.py` passou a ignorar por caminho. Antes: `Interrupted: 6 errors`;
  depois: **396 tests collected**.
* **`arxiv` declarado e nao instalado** (`requirements.txt` ja listava `arxiv` e
  `lxml`): `b_arxiv` devolvia `[]` em silencio. Instalados (`arxiv 4.0.2`,
  `lxml 6.1.3`); a consulta "graphene" passou a devolver 1 item em 1,68 s.

Artefatos de auditoria que faltavam:

| Artefato | Estado |
|---|---|
| `auditoria_bases_pesquisa.csv` (Etapa G) | **novo** — 13 bases medidas com HTTP real: **12 devolveram item**, Semantic Scholar respondeu **429** (limite da fonte) e CORE ficou `BLOQUEADO` sem chave |
| `docs/ARQUITETURA.md` | **novo** — gerado de `app.api.openapi()`: **85 caminhos / 92 operacoes**, diagrama Mermaid e inventario de rotas |
| `auditoria/varredura_artefatos.json` | **novo** — **1** import quebrado (`melhorias_panel` -> `streamlit`: painel legado de UI, orfao; o app e' Gradio), **12** dependencias de motor com import lazy, **9** dependencias opcionais protegidas, 0 `from-import` invalido, routers montados 11/12 (o 12º e' servico separado), orfaos da plataforma 13 |
| `docs/REGISTRO_ARTEFATOS.md` | **novo** — existentes, corrigidos, construidos e pendentes, com requisito por item |

Medicoes desta rodada:

| Prova | Resultado |
|---|---|
| `pytest test_mcp_alef.py` | **19 passed**, 27,83 s |
| `pytest test_fermilink_bridge.py` | **8 passed**, 5,35 s |
| `pytest test_voz.py test_orquestrador.py` | **29 passed**, 4,73 s |
| `pytest test_e2e_http.py` | **29 passed**, 53,65 s (5 novos: MCP, voz e orquestrador no app montado) |
| bloco B (18 arquivos) | **265 passed**, 90,97 s |
| bloco A (`test_esg_issacar.py test_plataforma_ak.py`) | **131 passed**, 285,40 s |
| **suite completa (19 arquivos)** | **396 passed, 0 failed** (285,40 s + 90,97 s = 376,37 s) |
| `python -m pytest --collect-only -q` | **396 tests collected**, 0 errors |
| smoke MCP (`auditoria/smoke_mcp.py`) | handshake 0,49 s; 4 ferramentas; `soma = 42`; escrita recusada em 0,31 s |
| `python auditoria/mapa_arquitetura.py` | 85 caminhos, 92 operacoes, 105 modulos, 2 pacotes |
| `python auditoria/varre_imports.py` | **1** import quebrado (`melhorias_panel` -> `streamlit`, painel legado de UI que o app nao usa), **12** dependencias de motor em import lazy, **9** opcionais protegidas, **0** `from-import` invalido |

Acoplamento conhecido (nao e' regressao desta rodada): num **unico processo**
com a arvore inteira, 4 testes de `test_plataforma_ak.py` falham porque
`nucleo_dados`/`api_dados` resolvem banco e pastas no primeiro import. Cada
arquivo sozinho passa (**62 passed**, 20,44 s). Por isso a validacao canonica
continua em blocos (A e B) ou um processo por arquivo
(`infra/rodar_suite_antiga.py`).
### Lote 5 (31/10/2026, continuacao): os 109 stubs de "187 bancos"

A varredura anterior olhava **imports**; esta olhou **corpo de funcao**
(`auditoria/descobre_lacunas.py`, novo). Achado: **109** funcoes eram
`return []` dentro de `bancos_completos.py`, e **nenhum** modulo do app
importava esse arquivo (`auditoria/quem_usa.py bancos_completos` -> 0
ocorrencias). O modulo anunciava "187 bancos de dados" e nao entregava nenhum.

O que passou a existir:

| Artefato | O que faz | Prova |
|---|---|---|
| `bancos_rest.py` | motor declarativo (URL, `{q}`, `{n}`, caminho dos itens `a.b.0.c`, chave opcional/obrigatoria) + 11 adaptadores de duas etapas (arXiv Atom, PubMed, NCBI Gene, PubChem, BCB SGS, PatentsView, ORCID, SIMBAD TAP, AFLUX texto, OpenAIRE, DuckDuckGo HTML) | 32 testes em `test_bancos_rest.py` |
| `api_bancos.py` | `GET /api/bancos`, `/saude`, `/{id}`, `POST /{id}/consultar` | e2e no app montado: 4 testes novos em `test_e2e_http.py`; 404/400 provados |
| `bancos_completos.py` | camada de compatibilidade (172 entradas com alias `arXiv` -> `arxiv`), sem nenhum stub | `auditoria/verifica_compat_bancos.py` |
| `auditoria/probe_bancos.py` | consulta real de **cada** base com a consulta de exemplo dela | `auditoria_bases_reais.csv` (48 linhas: 38 OK, 6 FALHOU, 4 BLOQUEADA) |

Estado medido das 121 bases declaradas: **44 PRONTAS** (chamam HTTP de
verdade), **4 BLOQUEADAS** por credencial (`CORE_API_KEY`,
`DADOS_GOV_TOKEN`, `MP_API_KEY`, `PATENTSVIEW_API_KEY`) e **73 SEM_API**
(fonte sem busca programatica — HTML, paga ou descontinuada), cada uma com
nota propria explicando o porque.

Nenhuma falha foi maquiada. As seis que nao responderam nesta medicao:

| Base | Medido | Causa raiz |
|---|---|---|
| `simbad` | ConnectTimeout 21,8 s | rede do host nao alcanca `simbad.cds.unistra.fr` (tambem testado `simbad.u-strasbg.fr`) |
| `ensembl` | ReadTimeout 31,0 s | host responde em ~20-25 s; nesta medicao passou do prazo |
| `embl`, `sra_study` | ReadTimeout 30,7 s | EBI Search ficou lento nesta janela (nas duas medidias anteriores: 1,4 s e 1,0 s, com itens) |
| `ena` | HTTP 500 | erro do servidor do ENA portal (4 variantes de sintaxe testadas) |
| `oqmd` | HTTP 502 | erro do servidor do OQMD |

Correcoes com causa medida (nao chute): `type:retraction` -> `update-type:retraction`
no Crossref (400 -> 200); `/ws/rest/all` -> `/ws/rest/uniprot` no EBI Search
(400 -> 200); ENA trocado por `sra_study` como alternativa funcional;
`/xrefs/symbol` no lugar de `/lookup/symbol` no Ensembl (400 -> lista vazia);
corpo do NOMAD `{"query": {"results.material.elements": "C"}}` (422 -> 200);
CORDIS `payload.results` (vazio -> 200); IPEADATA `startswith` (400 -> 200);
openFDA 404 `NOT_FOUND` tratado como `VAZIO`, nao como falha; BCB com estado
`INVALIDA` (uso errado) separado de `FALHOU` (fonte fora); dados.gov.br 401
virou `BLOQUEADA`; data.gov (EUA) 404 e data.govt.nz com WAF (Incapsula)
viraram `SEM_API`; Semantic Scholar aceita `SEMANTIC_API_KEY` opcional.

Defeito de contrato encontrado de quebra: `api_dados.py` publicava `/health`,
o **mesmo** caminho e o mesmo nome de funcao do `/health` do `app.py` — o
OpenAPI saia com `operationId` duplicado (`health_health_get`) e a rota de
`api_dados` nunca era alcancada. A funcao virou `health_dados` (o caminho
`/health` fica, porque `test_plataforma_ak` monta esse router sozinho) e o app
publica o status do banco em **`/api/dados/health`**, com teste e2e.
Depois disso `docs/ARQUITETURA.md` foi **regenerado**: **90 caminhos / 97
operacoes** (antes 85/92), com a area "Bancos cientificos" no inventario.

Medicoes desta rodada:

| Prova | Resultado |
|---|---|
| `pytest test_bancos_rest.py` | **32 passed** (27,30 s com import frio; 9,33 s depois) |
| bloco B (19 arquivos) | **301 passed**, 493,03 s |
| `probe_bancos.py --timeout 30` | 48 bases em 219,3 s: **38 OK**, 6 FALHOU, 4 BLOQUEADA |
| `python auditoria/mapa_arquitetura.py` | 90 caminhos / 97 operacoes, sem `operationId` duplicado |
| `python auditoria/descobre_lacunas.py` | 119 modulos, 0 erro de sintaxe, 0 stub em `bancos_completos` |



## Como subir e validar

```
# Docker / Space (mesma porta da API e da interface)
uvicorn app:app --host 0.0.0.0 --port 8020

# local (escolhe a primeira porta livre entre 7860, GRADIO_SERVER_PORT,
# PORT, ALEF_TAV_PORTA e 7861-7865)
python app.py
```

Validacao rapida (sem consumir credito de provedor nenhum):

```
curl http://127.0.0.1:8020/health
curl -X POST http://127.0.0.1:8020/api/simuladores/adsorcao \
     -H "Content-Type: application/json" \
     -d "{\"pergunta\":\"langmuir\",\"parametros\":{\"qmax\":100,\"KL\":0.05,\"Ce\":2}}"
```


