# Roteiro de validacao (estado em 31/10/2026)

Documento de continuidade: o que ja esta provado com medicao, o que foi corrigido
sem execucao (revisao estatica) e o comando exato que fecha cada pendencia.

Regra mantida em todo o projeto: **import != calculo**, **inventariado != imagem
construida != executado != validado != API aprovada**. Nenhum numero deste
documento foi inferido; quando algo nao foi medido, esta escrito "nao medido".

## 1. Como executar tudo

### 1.0 Procedimento vigente (01/11/2026) — uma chamada ao shell

O terminal desta sessao deixa de executar comandos por longos periodos
(`docs/DIAGNOSTICO_TERMINAL.md`). O caminho que funciona, e que faz validacao +
commit numa unica chamada:

```
powershell -NoProfile -Command "& 'C:\Users\PC\miniconda3\envs\holocine\python.exe' 'C:\Users\PC\hf_upload\auditoria\finalizar.py'"
```

`finalizar.py` roda as etapas `compileall`, `valida`, `antiloop`, `ui_bancos` e
`blocoB` pelo supervisor `auditoria/fila.py`, le `auditoria/fila_done.json` e
**so commita se tudo ficar verde** (relatorio em `auditoria/finalizacao.json`).
Se alguma etapa falhar, ele para, grava o motivo e nao toca no git.

`valida` = `pytest test_mcp_alef.py test_motor_real_prazo.py` (43 testes, 37,6 s):
e' o feedback curto antes do bloco longo. A rodada de 01/11 20:36-20:50 fechou as
cinco etapas verdes com **319 passed** no `blocoB` em **88,54 s**.

Para rodar so uma etapa: `python auditoria/desanexar.py <etapa>` (ex.: `probe`).

### 1.1 Roteiro detalhado (historico, ainda valido)

Um processo por etapa, saida em arquivo (`r4_*.txt`), sem `findstr`/`more`/pipe
para nenhum comando ficar esperando stdin:

```
cd /d C:\Users\PC\hf_upload
set PY=C:\Users\PC\miniconda3\envs\holocine\python.exe
set ALEF_SEM_PREAQUECER=1

%PY% -m compileall -q universal.py integracoes_reais.py teste_componentes_195.py ^
  test_motor_real_prazo.py test_universal_fluxo.py test_plataforma_ak.py ^
  infra\gerar_relatorio.py infra\rodar_suite_antiga.py

%PY% -m pytest test_motor_real_prazo.py test_universal_fluxo.py ^
  test_executor_isolado.py test_registro_componentes.py test_componentes_api.py -q

REM solido: coesao real via ASE+EMT (8 testes, 45,3 s medidos)
%PY% -m pytest test_solido_emt.py -q

REM suite completa em 2 blocos (21 arquivos; medicoes em auditoria\final_blocoB2.txt
REM e final_blocoA2.txt, rodada de 31/10/2026 — o bloco B mediu 301 passed em
REM 493,03 s ANTES dos ultimos 3 ajustes de /health; reconferir os numeros)
REM BLOCO A (pesado, import de nucleo_dados/api_dados):
%PY% -m pytest test_esg_issacar.py test_plataforma_ak.py -q
REM BLOCO B (todos os demais, incluindo os 2 novos):
%PY% -m pytest test_bancos_rest.py test_busca_multibase.py test_componentes_api.py ^
  test_e2e_http.py test_executor_isolado.py test_fermilink_bridge.py ^
  test_integracao_modelos_v2.py test_llm_client.py test_mcp_alef.py ^
  test_modelos_analiticos_v2.py test_motor_real_prazo.py test_orquestrador.py ^
  test_registro_componentes.py test_regressao_langmuir.py ^
  test_roteador_modelos_v2.py test_seguranca_credenciais.py test_solido_emt.py ^
  test_universal_fluxo.py test_voz.py -q

Neste host o terminal integrado encerra processos em foreground em ~200 ms
(medido: ver `docs/DIAGNOSTICO_TERMINAL.md`). Por isso a forma **recomendada**
de rodar tudo nao e' comando a comando, e sim pela fila supervisora, que roda
desanexada, tem limite por etapa e nao deixa uma etapa travada parar as outras:

```
cd /d C:\Users\PC\hf_upload
start "" /min C:\Users\PC\miniconda3\envs\holocine\python.exe auditoria\fila.py
REM progresso: auditoria\fila_progresso.json | log: auditoria\fila.log
REM saida de cada etapa: auditoria\fila\<etapa>.out.txt
REM etapas: python auditoria\fila.py --listar
```

Equivalente PowerShell (foi o que funcionou de fato nesta sessao):

```
Start-Process -FilePath 'C:\Users\PC\miniconda3\envs\holocine\python.exe' `
  -ArgumentList 'auditoria\fila.py' -NoNewWindow
```

A fila encerra automaticamente a execucao anterior (pid em
`auditoria\fila.pid`) e cada etapa tem `timeout` proprio (codigo 124 quando
estoura, sem travar a fila).


REM bancos cientificos: sonda REAL de cada base (grava CSV + JSON)
%PY% auditoria\probe_bancos.py --timeout 30
REM varredura de lacunas (stub, except silencioso, modulo sem teste, rota orfa)
%PY% auditoria\descobre_lacunas.py

REM inventario do motor `solido` (coesao real) e leitura auditavel da linha
%PY% infra\inventario_simuladores.py --somente solido --prazo 120 --acrescentar
%PY% auditoria\extrai_solido.py

%PY% infra\rodar_suite_antiga.py
%PY% teste_componentes_195.py

REM varredura dos 195 em blocos (cada bloco e' um processo; o mescla prova 195/195)
%PY% teste_componentes_195.py --inicio 0   --lote 40 --sem-rede --saida auditoria\h195_b1.json
%PY% teste_componentes_195.py --inicio 40  --lote 40 --sem-rede --saida auditoria\h195_b2.json
%PY% teste_componentes_195.py --inicio 80  --lote 40 --sem-rede --saida auditoria\h195_b3.json
%PY% teste_componentes_195.py --inicio 120 --lote 40 --sem-rede --saida auditoria\h195_b4.json
%PY% teste_componentes_195.py --inicio 160 --lote 40 --sem-rede --saida auditoria\h195_b5.json
%PY% auditoria\mescla_harness.py

REM boot real: uvicorn em socket TCP, nao TestClient
%PY% auditoria\boot_real.py

%PY% infra\gerar_relatorio.py

REM auditoria executavel (um simulador por vez, prova de que cada sim_* roda)
%PY% auditoria\checa_roteamento.py
%PY% auditoria\analisa_duplicacoes.py
%PY% auditoria\verifica_todos.py --inicio 0   --limite 20 --acrescentar
%PY% auditoria\verifica_todos.py --inicio 20  --limite 20 --acrescentar
%PY% auditoria\verifica_todos.py --inicio 40  --limite 20 --acrescentar
%PY% auditoria\verifica_todos.py --inicio 60  --limite 20 --acrescentar
%PY% auditoria\verifica_todos.py --inicio 80  --limite 20 --acrescentar
%PY% auditoria\verifica_todos.py --inicio 100 --limite 20 --acrescentar

git --no-pager status --porcelain
git --no-pager diff --stat
```

O mesmo roteiro esta em `EXECUTAR_AGORA.bat` (fora do repositorio), que grava
`r4_1_integridade.txt` ... `r4_7_e2e.txt`.

## 2. O que cada etapa prova

| Etapa | Prova | Sinal de sucesso |
|---|---|---|
| compileall | sintaxe dos modulos alterados | nenhuma saida, exit 0 |
| pytest do lote novo | prazos, proveniencia, executor isolado, APIs | tudo passed |
| `infra/rodar_suite_antiga.py` | isolamento real (1 processo por arquivo) | 10 arquivos, 0 com falha |
| harness 195 | os dez estados independentes, componente a componente | JSON regerado |
| `auditoria/mescla_harness.py` | a uniao dos 5 blocos cobre o catalogo exatamente uma vez | 195/195, 0 faltando, 0 duplicados, exit 0 |
| `auditoria/boot_real.py` | o app montado responde por HTTP em socket real | 8 sondas no status esperado, exit 0 |
| `auditoria/verifica_todos.py` | cada um dos 113 `sim_*` executa **e** muda quando um parametro muda | JSON com 113 OK, 0 constantes |
| `auditoria/checa_roteamento.py` | `DOMINIOS` x `SIMULADORES` nos dois sentidos | exit 0, 0 orfaos |
| `auditoria/prova_noop_limpeza.py` | a remocao do bloco duplicado nao mudou saida | 110/113 identicos, diferencas com causa declarada |
| gerar_relatorio | markdown a partir do JSON, sem numero inventado | exit 0 |
| git status/diff | nada foi commitado ou enviado | lista de arquivos alterados |

## 3. Valores medidos neste host (nao estimados)

| Medicao | Resultado |
|---|---|
| `compileall universal.py integracoes_reais.py` | exit 0 |
| `pytest test_universal_fluxo.py test_modelos_analiticos_v2.py` | 27 passed, 24,7 s |
| `pytest test_componentes_api.py` | 13 passed, 16,2 s |
| `pytest test_plataforma_ak.py` | 62 passed, 36,4 s |
| `pytest test_motor_real_prazo.py` | 18 passed, 3,0 s |
| `pytest test_e2e_http.py` | **34 passed**, 127,14 s na fila de 01/11 (2 novos: coesao real pelo HTTP e coerencia A/m; antes 24 passed/42,5 s e ~19 min por falso timeout) |
| `pytest test_ui_bancos.py` | **11 passed** (6 antigos + busca multi-base + 3 de exportacao). Medições: 321,95 s (17:14), 286,71 s (18:00), **160,18 s (18:41, fila, `auditoria/fila/ui_bancos.out.txt`)** — o `setup` que importa `app.py` responde por 60-66 s; a variacao restante era CPU dividida com o orfao (§8 de `docs/DIAGNOSTICO_TERMINAL.md`) |
| `auditoria/verifica_antiloop.py` (etapa `antiloop` da fila) | **codigo 0**: mesmo comando executado 3x pelo runner -> 9, 9, **5**, com `[antiloop]` explicando o bloqueio; 4,65 s (`auditoria/fila/antiloop.out.txt`) |
| bloco A (`test_esg_issacar.py test_plataforma_ak.py`) | **131 passed**, 493,74 s (fila 01/11, `auditoria/fila/blocoA.out.txt`) |
| `pytest test_mcp_alef.py test_motor_real_prazo.py` (etapa `valida`) | **43 passed, 37,63 s** (fila 01/11 20:47, `auditoria/fila/valida.out.txt`). Inclui os 6 testes novos: arranque lento x requisicao estourada, `FALHOU` != `BLOQUEADA`, prazo de arranque por ambiente e orcamento do motor |
| bloco B (20 arquivos, inclui `test_ui_bancos.py`) | **319 passed**, 85,81 s (fila 01/11 20:49, `auditoria/fila/blocoB.out.txt`); a rodada anterior, com os mesmos testes, mediu 193,26 s e antes disso **922,73 s com falha** (orfao dividindo CPU) |
| `probe_bancos.py --timeout 30` | 48 bases em 150,9 s: **OK=39**, VAZIO=1, FALHOU=4 (`semantic` 429, `simbad` timeout, `ensembl` read timeout, `oqmd` 502), BLOQUEADA=4 por credencial |
| `pytest test_solido_emt.py` | **8 passed, 45,3 s** em processo isolado (entrou nesta rodada; tambem roda dentro do bloco de 201 passed em 597,8 s) |
| `pytest` dos 8 arquivos restantes (bloco 2) | 131 passed, 122,3 s |
| suite completa (16 arquivos) | **332 passed, 0 failed** (dois blocos: 201 passed/597,8 s + 131 passed/122,3 s; antes 322 em ~390 s) |
| `pytest test_solido_emt.py test_universal_fluxo.py test_e2e_http.py` | 45 passed, 144,6 s |
| `infra/inventario_simuladores.py --somente solido --prazo 120 --acrescentar` | `solido` OK no motor **ASE + EMT (energia de coesao real)**, 4,20 s, sem `motor_situacao`; `E_coesao_eV_atomo = 3,5157` (era `-0,0049` com rotulo de coesao) e `parametro_rede_A = 3,61` |
| auditoria executavel dos simuladores | **113 OK, 0 falhas, 0 constantes** |
| roteamento SIMULADORES x DOMINIOS | 112 dominios, 113 simuladores, 113 alcancaveis, 0 orfaos |
| duplicacao de definicoes em `universal.py` | 60 nomes (66 defs) -> 0 apos limpeza |
| harness com `--ids ase,pymatgen` | 2 componentes `VALIDADO`; `aquecimento.modo=rapido`, 32,0 s, 13 modulos |
| harness dos 195 em 5 blocos + mescla | **195/195 componentes**, 0 faltando, 0 duplicados; 12 `VALIDADO`, **0 `EXECUTADO_SEM_VALIDACAO`**, 12 API aprovadas, 0 reprovadas, 154,5 s |
| `infra/rodar_suite_antiga.py` (10 arquivos, 1 processo cada) | **215 passed, 0 falhas**, 298 s |
| `auditoria/boot_real.py` (uvicorn real) | 8/8 sondas no status esperado: `/` 200 com interface Gradio montada, `/health` 200, catalogo 200, registro 200 (**195 componentes**), diagnostico-motores 200, adsorcao 200, universal 200, `diagnostico-montagem` **403**; boot 23,0 s nesta rodada (16,2 s com cache quente, 61,7 s a frio nas anteriores), exit 0 |
| `infra/gerar_relatorio.py` sobre esse JSON | "Aquecimento dos motores: 32.0 s, modo rapido, 13 modulos" |

Os 12 `VALIDADO` do harness completo sao exatamente os componentes com backend
local que rodam **e** conferem numero neste host: ase, brian2, cobrapy, flopy,
matminer, mesa, open-babel, pybamm, pymatgen, rasterio, rdkit, wntr. Os outros
183 se dividem em 119 `IMPLEMENTACAO_SEM_AMBIENTE`, 48 `APENAS_CATALOGADO` e 16
`DEPENDENCIAS_OK_SEM_EXECUCAO`. Duas promocoes nesta rodada, ambas com prova:

* `matminer` estava em `AMBIENTE_OK_SEM_CALCULO` ("importavel, sem caso
  cientifico registrado"). Passou a `VALIDADO` com a sonda de featurizacao:
  SiO2 -> fracao de Si 1/3, de O 2/3, norma 2 = 0,745356, e `p_list=(0, 2)`
  devolve exatamente `['0-norm', '2-norm']` (o parametro e' lido).
* `open-babel` estava em `EXECUTADO_SEM_VALIDACAO` porque toda sonda de CLI era
  `--version`, que prova ambiente e nao resultado. O executor passou a aceitar
  `avaliar(codigo, stdout, stderr)` da sonda, e a sonda do obabel agora roda
  `obabel -:CCO -osmi --append MW` e confere a massa molar do etanol
  (**46,0684 g/mol**). Nenhum componente ficou no estado "executou sem validar".



Custo de import por modulo, primeira importacao no host (a frio, com leitura de
disco a frio): pybamm 1337,8 s · wntr 1294,5 s · mesa 706,2 s · cobra 321,0 s ·
brian2 297,1 s · ase 64,1 s · flopy 43,9 s · rdkit 21,9 s · pymatgen 0,08 s ·
matminer `IMPORT_FALHOU`. Esses numeros **nao** sao custo de regime: com o
sistema de arquivos quente, `import pybamm` leva 7,0 s (medido em 31/10) e o
harness valida pybamm em 7,7 s. Use a coluna a frio para dimensionar o primeiro
boot de uma maquina nova, e a quente para tempo de execucao repetida.

## 4. Correcoes desta rodada (revisadas por leitura em 27/10, reexecutadas em 31/10)

1. `integracoes_reais.aquecer/_detalhado`: filtram submodulos pelas raizes
   pedidas. Antes `aquecer(("ase",))` custava 4 060 s.
2. `teste_componentes_195._aquecer_motores`: modo declarado
   (`ALEF_HARNESS_AQUECER`), padrao `rapido` (ase+rdkit+pymatgen, ~86 s).
   `completo` agora pede `MODULOS_DO_APP` (10 pacotes, inclui brian2/flopy);
   antes chamava `aquecer(None)` e deixava `neuro` frio.
3. `universal._com_motor_real`: fallback carrega `motor_situacao`
   (`prazo_excedido` / `motor_falhou: ...` / `motor_sem_resultado`) e
   `motor_prazo_s`.
4. `universal._rodar_simulacoes_com_bridge`: `fonte` deixou de ser sobrescrito
   com `"analitico"`. Agora `fonte == "motor_real"` quando o numero veio do
   motor e `"analitico"` quando veio da formula interna.
5. `test_plataforma_ak.sessao_login`: aceita 409 no registro e prova a
   credencial no login (eram os 38 errors do lote antigo, todos acoplamento de
   config resolvida no primeiro import do processo).
6. `infra/rodar_suite_antiga.py`: processa um arquivo por processo, com
   `encoding="utf-8", errors="replace"` na captura.
7. `infra/gerar_relatorio._aquecimento_txt`: JSON antigo sai como
   "nao medido (JSON anterior ao campo)", nunca `0,0 s`.

### 4.1 Extrator de parametros (bloqueava a auditoria inteira)

8. `universal._chaves_lidas_no_simulador`: o nome do dicionario de parametros
   vem agora da assinatura da funcao. Antes so reconhecia `p.get(`; os
   simuladores de Astronomia e Computacao declaram `def sim_x(p, q)` e leem
   `q.get(...)`, entao eram contados com **zero** chaves e nunca declaravam
   `parametros_padrao`. Prova: `auditoria/verifica_extrator.py` ->
   `auditoria/extrator_a1.txt`.

### 4.2 Defeitos cientificos encontrados por execucao

9. Cada item abaixo foi **medido**, nao revisado por leitura
   (`auditoria/verifica_todos.py`, resultado em `auditoria/verifica_todos.json`):

   | Simulador | Defeito | Correcao |
   |---|---|---|
   | `sim_solar` | saida constante `{"planetas": 8}` | Kepler III + zona habitavel (Terra: 1,000 ano, ZH 0,95–1,37 UA) |
   | `sim_cosmo` | `H0` ignorado (fixo em 70) | lido e propagado ao resultado |
   | `sim_ia` | `neuronios**2 * camadas` | pesos+vieses por camada (98 700 -> 277 600 ao ir de 3x100 para 4x200) |
   | `sim_cripto` | `log2(bits)*bits` (RSA-2048 = 22 528 "bits") | complexidade GNFS: RSA-2048 ~ 117 bits |
   | `sim_redes` | `n*k//2` com soma de graus impar | lema do handshake + recusa de `k >= n` |
   | `sim_grafos` | densidade sem paridade | paridade + densidade coerentes |
   | `sim_compil` | validacao sem numero | AST numerica (nos por instrucao) |
   | `sim_estatistica`, `sim_algebra` | RNG sem semente (mesma pergunta, resultado diferente) | `seed` declarado (padrao 42); `sim_algebra` devolve a norma do residuo `Ax-b` |
   | `sim_buraco` | perdeu `M_Sol` na refatoracao | restaurado |
   | `sim_cristalografia` | chave fora do padrao | `parametro_rede_m` canonico |

10. Motores reais (`integracoes_reais.py`), todos medidos por execucao:

   | Motor | Defeito | Correcao |
   |---|---|---|
   | `bateria_pybamm` | `capacidade_Ah` ignorado | injetado no conjunto do SPM; energia em Wh por integral de V dQ; `parametros_ignorados` declara `V` |
   | `cristalografia_pymatgen` | lia chaves que o simulador nao enviava e usava Bragg errado | aceita os dois nomes; `n*lambda = 2 d sin(theta)` (sem `theta/2`, com unidade convertida) |
   | `hidro_wntr` | `area_km2` e `precipitacao_mm` ignorados | metodo racional `Q = C*i*A`, devolve `vazao_escoamento_m3s` |
   | `micro_cobrapy` | objetivo era a propria captacao (fluxo otimo 0,0) | FBA com fonte de glicose, sink de biomassa e estequiometria de ATP; `N0`, `mu`, `t` entram em `N(t) = N0*exp(mu*t)` |

### 4.3 Limpeza de codigo morto

11. `universal.py` tinha o bloco "ASTRONOMIA ... TERRA EXPANDIDA" duplicado
    inteiro: 60 nomes (66 defs) redefinidos no mesmo modulo, 2 354 -> 1 979
    linhas. Antes da remocao foi gerada a prova mecanica de que toda funcao e
    toda chave de registro da copia tem substituta fora dela
    (`auditoria/remove_bloco_duplicado.py`, `auditoria/analisa_duplicacoes.py`);
    depois, `auditoria/snapshot_saidas.py` deu hashes identicos antes/depois
    (`auditoria/compara_snapshots.py`).

## 5. Bloqueios externos comprovados (nao sao tarefas adiadas)

| Bloqueio | Evidencia | Consequencia |
|---|---|---|
| Docker/wsl ausentes | `registro.FatosAmbiente(docker=False)` no host | 0 imagens construidas; os componentes com backend docker ficam `BLOQUEADO`, como o harness registra |
| credenciais LLM/bibliograficas ausentes | variaveis de ambiente vazias | camada conversacional provada com stubs; nenhum provedor externo chamado |
| ~~terminal integrado travado~~ | **nao e' mais bloqueio**: nesta sessao todos os comandos rodaram (compileall exit 0, 332 testes, auditoria dos 113 simuladores). O registro antigo vinha de processos presos no stdin | a validacao pode ser executada pelo agente; apenas nao usar paginadores (`more`/`findstr` sem arquivo) |
| chaves expostas em historico | decisao humana (rotacao) | nao automatizavel, nao reversivel |

## 6. Proximo passo concreto

O que ainda **nao** foi executado nesta sessao (nada aqui e' inferido):

1. ~~Boot real~~ **fechado**: `auditoria/boot_real.py` sobe o app em uvicorn real
   e deu **8/8 sondas OK** (`/` 200 com Gradio montado, `/health` 200, catalogo
   200, `/api/componentes/registro` 200 com 195 componentes,
   `diagnostico-motores` 200, adsorcao 200, universal 200,
   `diagnostico-montagem` 403), boot 23,0 s, exit 0
   (`auditoria/boot_real.json`; saida desta rodada em
   `auditoria/boot_pos_fix.txt`).
2. ~~Harness completo~~ **fechado**: `teste_componentes_195.py` rodou nos 5 blocos
   + `auditoria/mescla_harness.py` -> **195/195 componentes**, 0 faltando,
   0 duplicados, 12 `VALIDADO`, **0 `EXECUTADO_SEM_VALIDACAO`**, 12 API
   aprovadas / 0 reprovadas, 154,5 s (`auditoria/h195_total.json`).
3. ~~`infra/rodar_suite_antiga.py`~~ **fechado**: **215 passed, 0 falhas** nos 10
   arquivos antigos (1 processo por arquivo, 298 s). A suite nova (16 arquivos)
   soma **332 passed, 0 failed** em dois blocos.
4. Itens manuais: rotacao das chaves expostas em historico e instalacao de
   Docker/wsl (sem eles, 0 imagens construidas e os componentes de backend
   docker ficam `BLOQUEADO`, como o harness registra).

O que ja esta fechado e medido: ver secao 3 e `auditoria/LEIA-ME.md` (indice de
todas as provas geradas, com o comando que reproduz cada uma).

## 7. Lote 4 (31/10/2026): MCP real, voz, orquestrador e artefatos ausentes

Comandos exatos desta rodada (executados; saidas em `auditoria/`):

```
set PY=C:\Users\PC\miniconda3\envs\holocine\python.exe
set ALEF_SEM_PREAQUECER=1

REM 1. varredura estatica: imports quebrados x opcionais, routers, orfaos
%PY% auditoria\varre_imports.py                       -> auditoria\varredura_artefatos.json

REM 2. camada MCP (protocolo JSON-RPC 2.0) e ponte FermiLink
%PY% -m pytest test_mcp_alef.py test_fermilink_bridge.py -q
%PY% auditoria\smoke_mcp.py                           -> handshake, 4 ferramentas, soma=42

REM 3. voz e orquestrador
%PY% -m pytest test_voz.py test_orquestrador.py -q

REM 4. app montado com as rotas novas
%PY% -m pytest test_e2e_http.py -q

REM 5. bases cientificas: probe HTTP real + conector da plataforma
%PY% auditoria\gera_bases_pesquisa.py --rede          -> auditoria_bases_pesquisa.csv

REM 6. documento de arquitetura a partir do contrato vivo (usa banco temporario)
%PY% auditoria\mapa_arquitetura.py                     -> docs\ARQUITETURA.md

REM 7. coleta e suite (dois blocos: 396 testes no total)
%PY% -m pytest --collect-only -q
%PY% -m pytest test_esg_issacar.py test_plataforma_ak.py -q
%PY% -m pytest test_llm_client.py test_regressao_langmuir.py test_modelos_analiticos_v2.py ^
  test_integracao_modelos_v2.py test_roteador_modelos_v2.py test_solido_emt.py ^
  test_universal_fluxo.py test_seguranca_credenciais.py test_busca_multibase.py ^
  test_e2e_http.py test_registro_componentes.py test_executor_isolado.py ^
  test_componentes_api.py test_motor_real_prazo.py test_mcp_alef.py ^
  test_fermilink_bridge.py test_voz.py test_orquestrador.py -q
```

| Medicao | Resultado |
|---|---|
| coleta sem lista de arquivos | **396 tests collected**, 0 erros (antes: `Interrupted: 6 errors`) |
| `test_mcp_alef.py` | 19 passed, 27,83 s |
| `test_fermilink_bridge.py` | 8 passed, 5,35 s |
| `test_voz.py test_orquestrador.py` | 29 passed, 4,73 s |
| `test_e2e_http.py` | 29 passed, 53,65 s |
| bloco B (18 arquivos) | **265 passed**, 90,97 s |
| bloco A (ESG + plataforma) | **131 passed**, 285,40 s |
| **suite completa (19 arquivos)** | **396 passed, 0 failed** (285,40 s + 90,97 s = 376,37 s) |
| `auditoria_bases_pesquisa.csv` | 13 bases; **12 com item**, Semantic Scholar 429, CORE bloqueado sem chave |
| `docs/ARQUITETURA.md` | 85 caminhos / 92 operacoes / 105 modulos / 2 pacotes |
| `test_plataforma_ak.py` isolado | 62 passed, 20,44 s (prova de que as 4 falhas em processo unico sao acoplamento de import) |

Ressalva registrada: num **unico** processo com a arvore inteira, 4 testes de
`test_plataforma_ak.py` falham porque `nucleo_dados`/`api_dados` resolvem banco e
pastas no primeiro import do processo. Nao e' regressao do app: o mesmo arquivo
passa 62/62 sozinho. A validacao canonica continua em blocos (acima) ou um
processo por arquivo (`infra/rodar_suite_antiga.py`).
