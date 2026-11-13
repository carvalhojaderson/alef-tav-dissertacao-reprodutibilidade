# Integração da plataforma Tecnologia Ambiental com o backend — entrega

Data: 03/11/2026 · Backend: `https://jaderson32-api-ambiental.hf.space`
Frontend publicado: `https://ais-dev-762xvkh6mpwv73wh6pxb4n-17975995585.us-east1.run.app`

---

## 1. Causa identificada da falha de conexão

Não era hibernação. **O endereço usado pelo frontend não existe.**

| Verificação | Resultado medido |
|---|---|
| `GET https://api-ambiental.hf.space/api/health` | **404 com a página HTML do próprio Hugging Face** |
| `GET https://huggingface.co/api/spaces/api-ambiental` | `404 {"error": "Sorry, we can't find the page..."}` |
| Busca de Spaces com "ambiental" na API do HF | 9 Spaces, nenhum com esse nome |
| Space real do projeto | `Jaderson32/alef-tav-backend` — *RUNNING*, `jaderson32-alef-tav-backend.hf.space` |
| `GET .../alef-tav-backend.hf.space/api/health` | `404 {"detail":"Not Found"}` (FastAPI, rota inexistente) |
| `GET .../alef-tav-backend.hf.space/openapi.json` | 65 rotas da plataforma (`/api/auth`, `/api/esg`, `/api/simuladores`…) — **nenhuma rota ambiental** |

Conclusão: (a) `api-ambiental.hf.space` não é um domínio válido — no Hugging
Face o endereço de um Space é sempre `<dono>-<nome>.hf.space`;
(b) o backend ambiental **nunca havia sido publicado**: o código estava só no
ambiente local. O Space da plataforma não monta o router ambiental.

## 2. Correção aplicada no Hugging Face

1. Space **novo e dedicado**: `Jaderson32/api-ambiental` (Docker, público,
   cpu-basic) → **`https://jaderson32-api-ambiental.hf.space`**.
   O Space da plataforma **não foi alterado** (preservado como estava).
2. Conteúdo publicado por `ambiental_backend/preparar_espaco.py` (pacote +
   núcleo científico + `Dockerfile` + `uvicorn app:app` na porta 7860).
3. Variáveis do Space:

   | Variável | Valor |
   |---|---|
   | `CORS_ORIGENS` | `https://ais-dev-762xvkh6mpwv73wh6pxb4n-17975995585.us-east1.run.app` |
   | `AMBIENTAL_BANCO_PERSISTENTE` | `1` |
   | `AMBIENTAL_DADOS` | `/data` |
   | `ALEF_SEM_PREAQUECER` | `1` |
   | `ALEF_TAV_CORE` | `/app` |
   | `AMBIENTAL_BACKUP_REPO` | `Jaderson32/ambiental-dados` (dataset privado) |
   | `AMBIENTAL_BACKUP_INTERVALO` | `30` |
   | Secret `HF_TOKEN` | token com escrita nesse dataset |

4. Estado verificado: `stage: RUNNING`, `/api/ready` e `/api/health` em `200`.

## 3. Configuração CORS

- **Lista explícita** (`CORS_ORIGENS`) + regex (`CORS_ORIGEM_REGEX`) cobrindo
  `ais-dev-*`/`ais-pre-*.run.app` e `*.web.app`; **nunca `*`** por omissão
  (antes o padrão do código era `*`).
- Métodos liberados: `GET, POST, PUT, PATCH, DELETE, OPTIONS`;
  `Access-Control-Allow-Headers: *`; `max_age=600`;
  `Expose-Headers: Content-Disposition, Content-Length, X-Relatorio-Id`.
- **Problema encontrado e corrigido:** o proxy do Hugging Face acrescenta
  `Access-Control-Allow-Origin` **ecoado para qualquer origem** (medido: uma
  origem intrusa recebia `200` com o cabeçalho). Só o `CORSMiddleware` era,
  portanto, decorativo. Foi adicionado um middleware na aplicação que responde
  **`403 origem_nao_autorizada`** antes da rota. Medido depois da correção:

  ```
  origem https://ais-dev-...run.app      -> 200  (ACAO ecoado)
  origem https://site-nao-autorizado...  -> 403  {"erro":{"codigo":"origem_nao_autorizada"}}
  sem Origin (curl/script)               -> 200
  ```

## 4. URL efetivamente utilizada

`VITE_API_BASE_URL=https://jaderson32-api-ambiental.hf.space`
(ou o mesmo valor no campo "Configurações de conexão" da plataforma).

> Ponto que depende do dono do frontend: o código do app do AI Studio **não
> está nesta máquina** (o Cloud Run responde com a tela de login do Google e a
> página de *cookie check* do AI Studio), então a troca do valor não pôde ser
> aplicada por aqui. É **um valor de configuração**, não uma reescrita:
> `api-ambiental.hf.space` é inalcançável por definição (ver §1), qualquer que
> seja o código.

## 5. Módulos conectados

| Tela do frontend | Função da camada nova (`integracao_frontend/api_ambiental.ts`) | Rotas |
|---|---|---|
| Dashboard | `dashboard.estatisticas()` | `/api/stats`, `/api/health` |
| Pesquisas | `pesquisas.criar/listar/obter/editar` | `/api/research`, `/api/research/{id}` (PATCH) |
| Protocolo | `pesquisas.protocolo.*` | `/api/research/{id}/protocol` |
| Materiais | `materiais.cadastrar/obter/editar/listar` | `/api/materials`, `/api/research/{id}/materials` |
| Matriz 7D×4 | `matriz.completa()`, `materiais.matriz()` | `/api/matriz`, `/api/materials/{id}/descriptors` |
| Simuladores | `simuladores.painel/detalhe/requisitos/executar` | `/api/simulators*` |
| Adsorção | `adsorcao.validar()` | `/api/research/{id}/adsorbent` |
| Prova de conceito | `provaDeConceito.executar()` | `/api/research/{id}/proof-of-concept` |
| Viabilidade | `viabilidade.avaliar()` | `/api/research/{id}/viability` |
| Relatórios | `relatorios.gerar/listar/obter/baixar` | `/api/reports*` |
| Histórico | `historico.geral/simulacoes/tarefas` | `/api/history`, `/api/tasks` |
| Evidências | `pesquisas.evidencias.buscar()` | `/api/research/{id}/evidence/search` |
| Conexão | `verificarConexao()` | `/api/ready` (com repetição para hibernação) |

## 6. Endpoints utilizados na validação (todos medidos no Space)

```
GET    /api/ready                        200
GET    /api/health                       200
OPTIONS /api/research                    200   (preflight do frontend)
GET    /api/matriz                       200   (origem intrusa: 403)
POST   /api/research                     201
PATCH  /api/research/{id}                200
POST   /api/research/{id}/materials      201
GET    /api/research/{id}                200
POST   /api/research/{id}/protocol       201
GET    /api/materials/{id}/descriptors   200   (28 linhas)
GET    /api/simulators                   200   (29 disponíveis, 9 com descritor)
POST   /api/simulators/{nome}/run        200
GET    /api/research/{id}/simulations    200
POST   /api/research/{id}/adsorbent      201   (3 modelos aplicados)
POST   /api/research/{id}/viability      200   (52,08 → viável com restrições)
POST   /api/research/{id}/proof-of-concept 200 (executada, demonstrável)
POST   /api/research/{id}/reports        201   (md, json, pdf, docx)
GET    /api/reports/{id}/arquivo         200   (4 formatos baixados)
GET    /api/history                      200
GET    /api/stats                        200
POST   /api/persistence/sync             200   (snapshot enviado)
```

## 7. Dados demonstrativos

- Nenhum contador foi deixado fixo no backend: `GET /api/stats` calcula tudo no
  banco e devolve `dados_demonstracao: false` com a fonte declarada. Os números
  da tela atual (2 pesquisas, 4 materiais, 8/8 simuladores, 3 execuções,
  5 evidências, 28/28 descritores, 1 prova, 1 relatório) são **do componente**,
  não da API — os valores reais hoje são: 1 pesquisa, 1 material, 5 simulações
  (`ok`), 0 evidências (a busca bibliográfica não foi executada), matriz
  **75 % de cobertura** (21 de 28 linhas com valor, todas `presente`),
  1 prova de conceito e 5 relatórios.
- A matriz **não** tem 28/28 preenchidos: 12 descritores não têm simulador
  (`exige_ensaio: true`) e continuam `ausente`. O endpoint informa isso linha a
  linha, para a interface mostrar a lacuna em vez de um número inventado.
- A pesquisa criada pela validação chama-se **"Validacao de integracao
  (frontend -> backend)"** — identificada como tal, não como pesquisa de
  usuário. Ficaram duas (uma por execução de validação, 03/11 17:38 e 17:48).
  Para zerar o banco publicado:

  ```python
  from huggingface_hub import HfApi
  HfApi().delete_file("Jaderson32/ambiental-dados", "alef_tav.db",
                      repo_type="dataset")          # apaga o snapshot
  # depois: Settings do Space > Restart (o esquema e' recriado vazio)
  ```

  Nenhuma outra pesquisa foi apagada.

## 8. Testes realizados

| Teste | Resultado |
|---|---|
| Suíte automatizada (`pytest ambiental_backend`) | **44 passed** (31 API + 13 adendo) |
| Validação HTTP local (uvicorn) | **20/20** passos |
| Validação HTTP no Space publicado | **21/21** passos |
| Preflight CORS da origem real | 200, ACAO ecoado |
| Origem não autorizada | 403 `origem_nao_autorizada` |
| Relatórios nos 4 formatos | md 12,8 kB · json 66,8 kB · pdf 16,4 kB · docx 40,3 kB |
| Persistência após reinício do Space | **OK** — `restaurado_no_inicio: {feito: true, bytes: 262144}`, 16 tabelas com as mesmas contagens |

Fluxo coberto pelo `validar_integracao.py` (o mesmo da interface): acordar →
health → CORS → criar pesquisa → editar → cadastrar material novo com composição
e propriedades → conferir persistência → protocolo → matriz 28 → matriz do
material → inventário de simuladores → executar simulador real → recuperar
simulações → avaliação de adsorção (Langmuir, Freundlich, PFO) → viabilidade →
prova de conceito → relatório + download → histórico/stats → reinício e
releitura.

## 9. Problemas encontrados e corrigidos

1. **Domínio inexistente** `api-ambiental.hf.space` → Space dedicado publicado.
2. **Backend ambiental nunca publicado** (rotas ausentes no Space existente).
3. **CORS irrestrito por omissão (`*`)** → lista explícita + regex.
4. **Proxy do HF ecoa `Allow-Origin` para qualquer origem** → middleware de
   aplicação devolvendo 403 (o CORS sozinho não bastava).
5. **Métodos PUT/PATCH/DELETE ausentes** no CORS → incluídos (edição da
   pesquisa e do material exige).
6. **Edição de pesquisa e de material não existia** na API → `PATCH` novo com
   versão incrementada, trilha em `amb_historico` e merge de
   propriedades/composição.
7. **Dashboard sem endpoint de indicadores** → `GET /api/stats` calculado no
   banco; `GET /api/history` para a tela de histórico.
8. **`/data` do Space gratuito é apagado no reinício** (medido: pesquisa
   desapareceu) → snapshot SQLite (`sqlite3.backup`) para dataset privado +
   restauração no startup + `POST /api/persistence/sync`.
9. **Hibernação tratada como falha definitiva na UI** → `/api/ready` leve,
   repetição com espera crescente em `requisitar()` e três estados de conexão
   (`online`/`acordando`/`offline`).
10. **`formato=docx` indisponível** (faltava `python-docx` no ambiente) →
    funciona no Space publicado (40,3 kB gerados e baixados).

## 10. Pendências que dependem de credenciais/publicação

1. **Trocar a URL no frontend** (um valor, ver §4). O código do app do AI Studio
   não está nesta máquina e o Cloud Run exige login Google; nada mais depende
   dele — CORS, dados e persistência já estão do lado do backend.
2. **Token de escrita**: a persistência usa o Secret `HF_TOKEN` do Space (token
   da conta). Recomenda-se substituí-lo por um token de escopo restrito ao
   dataset `Jaderson32/ambiental-dados`.
3. Se o app for publicado com outro domínio (`ais-pre-*`, `*.web.app`), o regex
   padrão já cobre; domínio próprio exige acrescentar a origem em
   `CORS_ORIGENS`.

