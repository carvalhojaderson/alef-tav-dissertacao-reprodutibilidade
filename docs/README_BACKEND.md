# Backend ALEF-TAV Ambiental

Backend HTTP da aplicação ambiental. Recebe uma pergunta de pesquisa, mantém a
matriz metodológica **7D×4** (28 descritores) de cada material, recupera
evidências nas bases científicas que já existem no projeto, executa os
simuladores já registrados, compara com a literatura, avalia viabilidade,
gera prova de conceito computacional e emite relatórios.

Nada foi reimplementado: o backend é **camada de orquestração + persistência +
API** sobre `universal.py` (113 simuladores), `bancos_rest.py` /
`pesquisa_cientifica.py` (bases científicas), `modelos_adsorcao_v2.py` /
`modelos_analiticos_v2.py` (isotermas), `nucleo_dados.py` (SQLAlchemy) e
`exportadores.py` (DOCX/PPTX/BibTeX/RIS).

## 1. Estrutura

```
ambiental_backend/
    app.py               FastAPI (CORS, erros padronizados, /docs, /openapi.json)
    api_ambiental.py     rotas /api/*
    motor_pesquisa.py    pergunta -> protocolo -> dados -> evidências -> simulação
                         -> comparação -> viabilidade -> prova
    matriz_7d4.py        matriz 7D×4: 28 descritores com unidade e regra
    matriz_cruzamentos.py  7 dimensões informacionais (E,P,D,S,I,C,O) ×
                         4 componentes = 28 cruzamentos; pesos, índices e CSV
    componentes.py       caracterização de adsorbato/adsorvente/interface/meio
                         (tabela `amb_componentes`) e ponte para os simuladores
    persistencia.py      tabelas `amb_*` sobre o mesmo `Base`/`ENGINE` da plataforma
    adaptadores.py       ponte para os motores/bases existentes
    analises_experimentais.py  cálculos de bancada (PZC, Boehm, FTIR, TGA,
                         lixiviação, granulometria, GHS, conformidade, ...)
                         — **módulo recuperado do bytecode, ver §13**
    motores_ambientais.py 16 motores próprios: análise experimental -> descritor
    medicoes.py          recebimento de medições de bancada (tabela `amb_medicoes`)
    descritores_simuladores.py  mapa descritor -> simuladores/modelos/regra
    relatorios.py        relatório MD/JSON/PDF/DOCX + armazenamento
    tarefas.py           execução em segundo plano com estado consultável
    validar_integracao.py  validação E2E por HTTP (25 passos, sem dublês)
    frontend/            interface web (SPA sem build) servida em `/` e `/app/`
        index.html       uma página: navegação, cabeçalho, modal e toasts
        estilos.css      todo o visual (sem framework de CSS)
        js/api.js        cliente HTTP das rotas `/api/*`
        js/estado.js     pesquisa ativa, cache e observadores
        js/ui.js         criacao de elementos, campos, tabelas, cartoes, toasts
        js/app.js        roteador por hash (#/painel, #/pesquisas, ...)
        js/telas/*.js    10 telas: painel, pesquisas, materiais, caracterizacao,
                         componentes, matriz, simuladores, comparacao,
                         relatorios, historico
    conftest.py          banco de teste temporário + dublês (sem rede)
    test_ambiental_api.py, test_ambiental_simuladores.py,
    test_ambiental_motores.py, test_ambiental_medicoes.py,
    test_ambiental_cruzamentos.py, test_ambiental_interface.py   suíte de testes
```

## 2. Como subir

### 2.1 No Space principal (recomendado — sem duplicar nada)

O `app.py` da raiz já monta o router no mesmo FastAPI do Space:

```python
from ambiental_backend.api_ambiental import router as ambiental_router
api.include_router(ambiental_router)
```

Os endpoints ficam disponíveis na **URL do próprio Space**, em `/api/...`
(o `/docs` do FastAPI montado continua em `/docs`).

### 2.2 Como aplicação independente (local ou Space separado)

```bash
cd <raiz do projeto>
python -m uvicorn ambiental_backend.app:app --host 0.0.0.0 --port 7860
```

- `GET /` — a interface web (`index.html`); sem `frontend/` cai no índice JSON
- `GET /app/...` — a mesma interface (arquivos estáticos, `html=True`)
- `GET /docs` — Swagger UI
- `GET /openapi.json` — contrato OpenAPI 3.1

## 3. Variáveis de ambiente e Secrets

| Variável | Uso | Padrão |
|---|---|---|
| `AMBIENTAL_BANCO_URL` | URL SQLAlchemy do banco | vazio (usa `alef_tav.db`) |
| `ALEF_TAV_DATABASE_URL` / `DATABASE_URL` | já usadas pela plataforma | sqlite `alef_tav.db` |
| `AMBIENTAL_BANCO_PERSISTENTE` | `1` move o banco para `AMBIENTAL_DADOS` | desligado |
| `AMBIENTAL_DADOS` / `ALEF_TAV_DATA_DIR` | diretório persistente | `/data` se existir, senão `dados_ambiental/` |
| `CORS_ORIGENS` | origens permitidas, separadas por vírgula | `*` |
| `CORS_ORIGEM_REGEX` | regex extra (ex.: domínios do AI Studio) | vazio |
| `AMBIENTAL_MAX_TAREFAS` | threads de simulação | `4` |
| `AMBIENTAL_TIMEOUT_SIMULADOR` | prazo por simulador (s) | `180` |
| `AMBIENTAL_TIMEOUT_EVIDENCIA` | prazo por busca (s) | `45` |
| `ALEF_SEM_PREAQUECER` | obrigatório fora do fluxo do app | `1` (o pacote já define) |

Chaves de API (bases pagas, LLM) continuam **nos Secrets do Space**; o backend
apenas lê o ambiente. Nenhuma credencial é exposta ao frontend.

### 3.1 Persistência entre reinícios

O Space grava em disco efêmero por padrão. Para persistir:

1. ative **Persistent Storage** no Space (monta `/data`);
2. defina `AMBIENTAL_BANCO_PERSISTENTE=1` (o pacote aponta o banco para
   `<AMBIENTAL_DADOS>/alef_tav.db`) **ou** aponte `ALEF_TAV_DATABASE_URL` para
   um Postgres (`postgresql+psycopg://...`) nos Secrets;
3. relatórios vão para `<AMBIENTAL_DADOS>/relatorios/`.

Sem isso, as tabelas `amb_*` são recriadas a cada reinício (a criação é
idempotente, mas o conteúdo se perde com o filesystem efêmero).

## 4. Banco: tabelas criadas (18) e reuso

Mesmo `Base`/`ENGINE` de `nucleo_dados.py` — nada de banco paralelo. A criação
usa `create_all(checkfirst=True)` só nas tabelas `amb_*` e registra a versão em
`amb_esquema` (e em `schema_version`, herdada da plataforma).

| Tabela | Conteúdo |
|---|---|
| `amb_pesquisas` | pergunta, material, contaminante, aplicação, condições, estado, versão |
| `amb_protocolos` | pergunta estruturada, descritores, simuladores, critérios |
| `amb_materiais` | cadastro do material (nome, fórmula, CAS, classe, origem) |
| `amb_pesquisa_materiais` | vínculo pesquisa↔material (papel: alvo/comparação) |
| `amb_composicoes` | elemento + fração mássica/molar + origem |
| `amb_propriedades` | nome, valor, unidade, método, confiança, origem |
| `amb_descritores` | 28 códigos (S1…C7) por material, com estado e memória de cálculo |
| `amb_evidencias` | item bibliográfico normalizado + relevância + base de origem |
| `amb_referencias` | autores, veículo, volume, DOI, URL |
| `amb_simulacoes` | simulador, parâmetros, estado, resultado, erro, duração |
| `amb_comparacoes` | valor calculado × literatura, desvio relativo, veredito |
| `amb_viabilidades` | pontuação, classificação, critérios, lacunas, riscos |
| `amb_provas_conceito` | passos executados e resultado da prova |
| `amb_relatorios` | tipo, formato, caminho, conteúdo, tamanho |
| `amb_historico` | trilha de auditoria (entidade, ação, detalhe) |
| `amb_tarefas` | tarefas de background (estado, progresso, erro) |
| `amb_medicoes` | medição de bancada: tipo, valor, unidade, réplicas, estatística (média/desvio/RSR/Grubbs), método, instrumento, incerteza, condições, laboratório, operador |
| `amb_componentes` | caracterização de adsorbato/adsorvente/interface/meio: chave, valor, unidade, origem, método, referência, estado de validação |

Valores ausentes são registrados como `ausente` (com a lista do que falta) —
nunca como zero ou estimativa silenciosa.

## 5. Endpoints

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/health` | estado, banco, motores, contagem por tabela |
| GET | `/api/matriz` | matriz 7D×4 completa (28 descritores) |
| GET | `/api/matriz/estrutura` | 7 dimensões informacionais × 4 componentes: relações e catálogo de parâmetros (54) |
| GET | `/api/matriz/cruzamentos` | 28 cruzamentos do material: descritores, valores, origem, pesos, índices e lacunas |
| GET | `/api/matriz/exportar` | matriz plana em CSV (`formato=json` devolve o objeto) |
| GET | `/api/matriz/{codigo}` | definição/unidade/regra de um descritor |
| POST | `/api/matriz/{codigo}/calcular` | aplica a regra (ex.: D6, D1, P3) |
| GET | `/api/componentes` | catálogo de adsorbato/adsorvente/interface/meio |
| GET | `/api/materials/{id}/components` | caracterização dos quatro componentes do material |
| POST | `/api/materials/{id}/components/{componente}` | grava parâmetros (valor, unidade, origem, método, estado) |
| DELETE | `/api/materials/{id}/components/{componente}/{chave}` | remove um parâmetro |
| GET | `/api/simulators/{nome}/parameters` | preenche os requisitos do motor com o dado já cadastrado |
| POST | `/api/research` | cria a pesquisa |
| GET | `/api/research` | lista pesquisas |
| GET | `/api/research/{id}` | pesquisa agregada |
| POST | `/api/research/{id}/protocol` | monta protocolo |
| GET | `/api/research/{id}/protocol` | protocolo vigente |
| POST | `/api/research/{id}/materials` | cadastra material (+composição/propriedades) |
| GET | `/api/materials` | catálogo de materiais |
| GET | `/api/materials/{id}` | material + composição + propriedades + matriz |
| GET | `/api/materials/{id}/descriptors` | 28 linhas com estado |
| POST | `/api/research/{id}/materials/{material_id}/descriptors` | preenche/atualiza descritores |
| POST | `/api/materials/{id}/descriptors?pesquisa_id=...` | atalho do anterior |
| GET | `/api/research/{id}/evidence` | evidências persistidas |
| POST | `/api/research/{id}/evidence/search` | busca nas bases + dedup + persistência |
| POST | `/api/research/{id}/simulations` | enfileira (202) ou executa (`sincrono=true`) |
| GET | `/api/research/{id}/simulations` | lista com estado |
| GET | `/api/research/{id}/simulations/{sim_id}` | resultado/erro/duração |
| POST | `/api/research/{id}/viability` | compara com a literatura + pontua 6 critérios |
| GET | `/api/research/{id}/viability` | última avaliação |
| POST | `/api/research/{id}/proof-of-concept` | prova de conceito computacional |
| GET | `/api/research/{id}/proof-of-concept` | última prova |
| POST | `/api/research/{id}/reports` | gera relatório (md/json/pdf/docx) |
| GET | `/api/research/{id}/reports` | relatórios da pesquisa |
| GET | `/api/reports/{report_id}` | metadados + conteúdo |
| GET | `/api/reports/{report_id}/arquivo` | download do arquivo |
| GET | `/api/tasks/{task_id}` | estado da tarefa |
| GET | `/api/tasks` | lista de tarefas |
| GET | `/api/simulators/catalog` | 113 registrados + recorte ambiental |
| GET | `/api/simulators` | painel: requisitos, descritores, estado, última execução, erros |
| GET | `/api/simulators/{nome}` | detalhe + requisitos + estado atual |
| GET | `/api/simulators/{nome}/requirements` | entradas obrigatórias com unidade |
| POST | `/api/simulators/{nome}/run` | executa agora (grava se houver `pesquisa_id`) |
| GET | `/api/descritores/simuladores` | mapa descritor → simuladores/modelos/regra |
| GET | `/api/descritores/{codigo}/fontes` | fontes de um descritor |
| POST | `/api/research/{id}/adsorbent` | valida adsorvente (simuladores + matriz + modelos + lacunas) |
| GET | `/api/research/{id}/adsorbent` | última validação gravada |
| GET | `/api/research/{id}/adsorbent/{material_id}` | validação de um material |
| GET | `/api/evidence/sources` | inventário das bases |
| GET | `/api/engines` | 16 motores ambientais próprios (método, natureza, nível de validação, referências) |
| GET | `/api/measurements/types` | tipos de medição aceitos (unidade, faixa física, descritor) |
| POST | `/api/materials/{id}/measurements` | registra medição de bancada e preenche o descritor |
| POST | `/api/materials/{id}/measurements/batch` | lote (erro em uma não derruba as demais) |
| GET | `/api/materials/{id}/measurements` | medições do material |
| GET | `/api/materials/{id}/measurements/summary` | cobertura de medição por descritor |
| GET | `/api/measurements` · `/api/measurements/{id}` | listagem geral e detalhe (estatística, condições) |
| DELETE | `/api/measurements/{id}` | remove a medição (o descritor permanece) |

### 5.1 Erros

```json
{"erro": {"codigo": "entrada_invalida", "mensagem": "...", "detalhes": null}}
```

| HTTP | `codigo` | Quando |
|---|---|---|
| 400 | `entrada_invalida` | pergunta curta, descritor/formato inexistente |
| 404 | `nao_encontrado` / `protocolo_ausente` / `simulador_desconhecido` | id ou nome inválido |
| 422 | `validacao` | corpo fora do schema (Pydantic) |
| 503 | `motor_indisponivel` | módulo do núcleo não carregou |
| 500 | `erro_interno` | falha inesperada (mensagem com tipo) |

## 6. Fluxo completo (exemplo real de uso)

```bash
BASE="https://<seu-space>.hf.space"      # URL do Space que você publicou

# 1. pesquisa
curl -s -X POST "$BASE/api/research" -H "Content-Type: application/json" -d '{
  "pergunta": "adsorcao de chumbo em agua com biochar de casca de arroz",
  "material": "biochar de casca de arroz",
  "contaminante": "chumbo", "aplicacao": "agua",
  "condicoes": {"Ce": 10.0, "C0": 100.0, "volume_L": 0.1, "massa_g": 0.05}
}'

# 2. protocolo (descritores 7Dx4 + simuladores + critérios)
curl -s -X POST "$BASE/api/research/$ID/protocol" -H "Content-Type: application/json" -d '{}'

# 3. material
curl -s -X POST "$BASE/api/research/$ID/materials" -H "Content-Type: application/json" -d '{
  "nome": "biochar de casca de arroz", "classe": "adsorvente",
  "composicao": [{"elemento": "C", "fracao_massica": 0.72}],
  "propriedades": [{"nome": "area_bet", "valor": 640, "unidade": "m2/g"}]
}'

# 4. descritores (cálculo a partir dos dados, ou valor informado)
curl -s -X POST "$BASE/api/research/$ID/materials/$MAT/descriptors" \
  -H "Content-Type: application/json" -d '{
  "calculo": {
    "D1": {"pontos": [{"Ce": 5, "qe": 20}, {"Ce": 10, "qe": 30}, {"Ce": 20, "qe": 42}]},
    "D6": {"C0": 100, "Ce": 20}},
  "valores": {"S3": {"valor": 640, "unidade": "m2/g", "estado": "presente",
                     "fonte": "ensaio BET"}}}'

# 5. evidências (bases reais; devolve novas/repetidas e falhas por base)
curl -s -X POST "$BASE/api/research/$ID/evidence/search" \
  -H "Content-Type: application/json" -d '{"n": 3, "max_bases": 4}'

# 6. simulação assíncrona -> 202 + tarefa_id
curl -s -X POST "$BASE/api/research/$ID/simulations" \
  -H "Content-Type: application/json" -d '{"simuladores": ["superficie"], "parametros": {"area_m2g": 640}}'
curl -s "$BASE/api/tasks/<tarefa_id>"

# 7. viabilidade (compara com a literatura e pontua)
curl -s -X POST "$BASE/api/research/$ID/viability" -d '{"tolerancia": 0.2}' -H "Content-Type: application/json"

# 8. prova de conceito
curl -s -X POST "$BASE/api/research/$ID/proof-of-concept"

# 9. relatório
curl -s -X POST "$BASE/api/research/$ID/reports" -H "Content-Type: application/json" -d '{"tipo": "viabilidade", "formato": "pdf"}'
curl -s -OJ "$BASE/api/reports/<report_id>/arquivo"
```

## 7. Consumo pelo frontend do Google AI Studio

O frontend chama a URL do Space diretamente (não há proxy):

```js
const API = "https://<seu-space>.hf.space";

async function criarPesquisa(pergunta) {
  const r = await fetch(`${API}/api/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pergunta })
  });
  if (!r.ok) throw await r.json();      // { erro: { codigo, mensagem } }
  return r.json();                      // { id, estrutura_da_pergunta, ... }
}

// simulação: 202 + tarefa_id, polling até estado final
async function simular(id, simuladores) {
  const r = await fetch(`${API}/api/research/${id}/simulations`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ simuladores })
  });
  const { tarefa_ids } = await r.json();
  for (let i = 0; i < 120; i++) {
    const t = await (await fetch(`${API}/api/tasks/${tarefa_ids[0]}`)).json();
    if (["concluida", "falhou"].includes(t.estado)) return t;
    await new Promise(res => setTimeout(res, 1000));
  }
}
```

**CORS:** a política de origem é aplicada em dois níveis.

1. `CORSMiddleware` responde o preflight para as origens permitidas
   (`GET/POST/PUT/PATCH/DELETE/OPTIONS`, cabeçalhos livres, `max_age=600`).
2. Um middleware próprio recusa com **403 `origem_nao_autorizada`** qualquer
   requisição cujo `Origin` não esteja na lista — isso é necessário porque o
   proxy do Hugging Face acrescenta `Access-Control-Allow-Origin` à resposta
   (medido: uma origem intrusa recebia `200` com o cabeçalho ecoado). Sem essa
   checagem, a restrição de CORS seria apenas decorativa.

Sem `CORS_ORIGENS`, valem as origens conhecidas do frontend (`ORIGENS_PADRAO`
em `config.py`: `ais-dev-*`/`ais-pre-*` do Cloud Run e `localhost`), e o regex
padrão cobre `ais-dev-*`/`ais-pre-*.run.app` e `*.web.app`. Nunca há `*` por
omissão. Em produção, fixe a lista:

```
CORS_ORIGENS=https://ais-dev-762xvkh6mpwv73wh6pxb4n-17975995585.us-east1.run.app
CORS_ORIGEM_REGEX=^https://(ais-(dev|pre)-[a-z0-9-]+(\.[a-z0-9-]+)+\.run\.app|[a-z0-9-]+\.web\.app)$
```

Vale para as duas formas de execução: o `app.py` da raiz passou a ler
`CORS_ORIGENS`/`CORS_ORIGEM_REGEX` (antes era `["*"]` fixo), então a restrição
funciona igual quando o router é montado no Space principal.

Nunca coloque chaves no JavaScript: o frontend fala só com estas rotas; as
credenciais ficam nos Secrets do backend.

## 8. Testes executados

```bash
python -m pytest ambiental_backend -q
# 125 passed em ~1min
#   44 de API/simuladores + 42 de motores + 10 de medicoes
#   + 16 de cruzamentos/pesos/componentes + 13 de interface
```

Cobrem: 28 descritores e regras (D1/D6), ciclo da pesquisa, protocolo,
material reaproveitado, descritores calculados/informados/desconhecidos,
evidências com dedup, simulação síncrona e assíncrona (tarefa conclui),
simulador inexistente, isolamento entre pesquisas, viabilidade, prova de
conceito, relatórios md/json (conteúdo e download) e formato inválido.

`test_ambiental_motores.py` (42) prova, para cada um dos 16 motores próprios:
registro completo (função, nível, domínio, descritores), envelope padrão de
saída, `EntradaInvalida` quando falta entrada obrigatória (nenhum valor
inventado), descritores de saída existentes na matriz 7D×4 e as relações
físicas esperadas (PZC dentro da faixa, D50 entre extremos, perigo cresce com
metal pesado, conformidade acusa falha acima do limite).

`test_ambiental_medicoes.py` (10) prova o caminho de caracterização: catálogo
de tipos, medição com réplicas que vira `validado` (RSR ≤ 10%), uma réplica que
fica `presente` com motivo, unidade errada/valor fora da faixa/tipo
desconhecido recusados com 400, FTIR por texto, lote com falha parcial,
listagem, resumo por descritor, detalhe e remoção.

O adendo acrescenta (`test_ambiental_simuladores.py`): mapa descritor→fonte,
`/api/matriz` com simuladores por descritor, painel com requisitos e histórico,
execução manual com e sem persistência, bloqueio por falta de parâmetro
(vs. execução forçada com aproximação), validação completa de adsorvente
(Langmuir 20/0,5, PZC, lacunas, compatibilidade), validação mínima sem invenção,
propriedade não mapeada que não vira descritor, prova de conceito por material
e a regra `pH × PZC` com fronteira de palavra para siglas.

Além disso, prova de integração real (sem dublês): `universal.py` carregou
**113** simuladores e `superficie`, `metais` e `poluicao` responderam `ok`
através de `adaptadores.executar_simulador`, e o teste do §7 está em §11.4.

`test_ambiental_interface.py` (13) prova a interface publicada: `index.html`
existe com as 10 telas do fluxo, `/` e `/app/` respondem HTML, todo `src`/`href`
do `index.html` é servido, os `.js` saem com `javascript` e o `.css` com
`text/css`, arquivo inexistente dá 404 sem derrubar `/api/ready`, todo `import`
relativo aponta para módulo existente, cada tela exporta `meta` e `render`, o
roteador importa as 10 telas, `/api` anuncia `interface: /app/` e
`preparar_espaco.montar` leva a SPA para a pasta publicada (sem testes nem
`conftest.py`). Ver §14.

`test_ambiental_cruzamentos.py` (16) prova a camada 7×4: os 28 cruzamentos,
todo descritor classificado, célula vazia sem zero, pesos normalizados com
qualidade por estado, entropia e índice comparativo apenas com dois materiais,
redundância só com quatro e significativa, parâmetros dentro do cruzamento,
CSV e o contrato das rotas novas. Ver §15.

## 9. Limitações conhecidas

- O recorte ambiental do catálogo é curado (24 dos 113); simuladores fora do
  recorte continuam executáveis por nome.
- A comparação com a literatura extrai números de título/resumo; sem abstract
  numérico o veredito fica sem comparação (e o relatório diz isso).
- `pdf` exige `reportlab`; `docx` exige `python-docx` (via `exportadores.py`).
  Sem a biblioteca a rota responde 400 `entrada_invalida` com o motivo.
- Busca bibliográfica depende de rede/credenciais das bases; falha de base vem
  em `falhas` com estado e motivo, sem derrubar a pesquisa.
- A dissertação não é usada como dependência nem citada nos relatórios.

## 10. Execução real medida (03/11/2026)

Servidor: `uvicorn ambiental_backend.app:app --port 8093` sobre o banco do
próprio projeto (`alef_tav.db`), sem dublês.

| Passo | Medida |
|---|---|
| `GET /api/health` | 200, `estado=ok`, `matriz={4 dimensões, 28 descritores}` |
| `GET /openapi.json` | 200, **25 rotas** documentadas |
| `POST /api/research` | 201, `pesq_...`, contaminante `chumbo`, aplicação `agua` |
| `POST .../protocol` | 201, 28 descritores com pontuação e motivo |
| `POST .../materials` | 201, 1 composição + 1 propriedade |
| `POST .../descriptors` | D1 calculado: `qmax = 66,8182 mg/g`, `KL = 0,0838 L/mg`, `r² = 0,9985` |
| `POST .../simulations` | 202, `superficie` e `poluicao` → `ok` (motor `universal.py`) |
| `POST .../evidence/search` | 200, 3 bases consultadas, 2 OK, **4 novos** itens, 0 repetidos |
| `POST .../viability` | 200, **66,0** → `viavel_com_restricoes` |
| `POST .../proof-of-concept` | 200, `estado=executada`, `qe = 30,4664 mg/g` em `Ce = 10 mg/L` |
| `POST .../reports` (pdf) | 201, **9.575 bytes**, download 200 `application/pdf` |

Observações medidas:

- `dados_ambiental/` é o diretório de dados local (relatórios e, se
  `AMBIENTAL_BANCO_PERSISTENTE=1`, o banco). No Linux do Space o padrão é
  `/data`.
- As tabelas `amb_*` foram criadas no `alef_tav.db` existente na primeira
  execução; nenhuma tabela da plataforma foi alterada ou removida.

## 11. Adendo: simuladores ligados aos descritores e validação de adsorventes

O adendo exige que cada descritor indique **quais simuladores** podem calculá-lo
e que o material adsorvente seja efetivamente avaliado. Isso é implementado em
dois módulos novos, sem reimplementar nenhum motor:

| Arquivo | Papel |
|---|---|
| `ambiental_backend/descritores_simuladores.py` | mapa descritor → regra/simulador/modelo, requisitos de entrada, execução e tradução do resultado em descritor |
| `ambiental_backend/adsorventes.py` | fluxo §3/§4: caracterização → descritores → simuladores → modelos → literatura → compatibilidade → lacunas |
| `ambiental_backend/validar_adsorventes.py` | teste do §7 com motores reais (material de referência + material diferente) |

### 11.1 Mapa descritor → fonte (medido no núcleo)

| Descritor | Regra da matriz | Simulador (saída usada) | Modo |
|---|---|---|---|
| S2 fase cristalina | — | `cristalografia` → `d_espacamento_m` (pymatgen real) | apoio |
| S3 BET | — | `superficie` → `area_m2g` | valor (dado informado) |
| S5 partícula | — | `nano` → `diametro_nm` (motor devolve 6/d) | valor (dado informado) |
| S4 volume de poros | `S4` (ρ aparente/real) | — | calculado |
| P1 densidade | `P1` (m/V) | `cristalografia` → `densidade_g_cm3` | calculado |
| P3 CTC | `P3` (branco/amostra) | — | calculado |
| P6 band gap | — | `dft` → `bandgap_eV` (referência interna do motor) | estimado |
| D1 qmax | `D1` (Langmuir) | modelos `langmuir*` | calculado |
| D2 KL/RL | `D2` | modelos `langmuir*`/`freundlich*` | calculado |
| D3 cinética | `D3` (PSO) | modelo `pfo_cinetica` | calculado |
| D6 remoção | `D6` (C0/Ce) | `poluicao` → `C_final` | calculado / apoio |
| D7 janela pH/T | — | `equilibrio` → `K_equilibrio` | apoio |
| C2 custo | `C2` | — | calculado |
| C4 energia | `C4` | — | calculado |
| C7 TRH | `C7` | `cfd`/`fluido` → `Reynolds`; `hidro` → vazão | calculado / apoio |
| C3 disponibilidade | — | `hidro` → `vazao_m3s` | apoio |

Os demais descritores (S1, S6, S7, P2, P4, P5, P7, D4, D5, C1, C5, C6) não têm
fonte computacional: `GET /api/matriz` devolve `exige_ensaio: true` e
`GET /api/descritores/simuladores` devolve `cobertura: "sem_simulador"` com a
lacuna declarada. Nada é preenchido com número inventado.

### 11.2 Estados que o painel expõe

| Estado | Significado |
|---|---|
| `ok` | executado com todas as entradas lidas informadas |
| `ok_com_aproximacao` | executado, mas o motor usou padrão interno em alguma chave |
| `ok_sem_descritor` | executado; não há descritor mapeado para a saída |
| `bloqueado_por_parametros` | não executado: faltam entradas obrigatórias (`faltando`) |
| `indisponivel` | simulador fora do registro `universal.SIMULADORES` |
| `erro` / `timeout` | falha do motor, com `erro` e `duracao_s` gravados |

`GET /api/simulators` devolve, por simulador: `requisitos`, `le_chaves`,
`descritores`, `disponivel`, `estado_operacional`, `total_execucoes`,
`sucessos`, `falhas`, `ultima_execucao` e `erros` — todos lidos de
`amb_simulacoes` (nada em memória).


### 11.3 Contrato de `POST /api/research/{id}/adsorbent`

```json
{
  "material": "zeolita 4A modificada",
  "formula": "Na12Al12Si12O48",
  "composicao": [{"elemento": "Si", "fracao_massica": 0.21}],
  "caracterizacao": {
    "area_superficial": {"valor": 620, "unidade": "m2/g", "metodo": "BET N2"},
    "pzc": {"valor": 6.8, "unidade": "pH"},
    "diametro_particula": {"valor": 90, "unidade": "nm"}
  },
  "condicoes": {"pH": 5.0, "Ce": 10.0, "temperatura_C": 25.0},
  "calculo": {"D1": {"pontos": [{"Ce": 1, "qe": 9.3}]},
              "D6": {"C0": 50, "Ce": 12.5, "volume_L": 0.1, "massa_g": 0.1}},
  "simuladores": ["superficie", "nano", "cfd", "dft"],
  "parametros_simulador": {"densidade": 1000, "velocidade": 0.01,
                            "diametro": 0.005, "material": "Si"},
  "modelos": ["langmuir", "pfo_cinetica"],
  "parametros_modelo": {"pfo_cinetica": {"k1": 0.08, "tempo": 30}}
}
```

Resposta (resumida): `material`, `caracterizacao` (gravadas, `nao_mapeadas`,
`sem_valor`), `descritores`, `simuladores[]` (estado, resultado, descritores
atualizados, avisos), `modelos[]` (estado, `qe`, `faltando`, `natureza`),
`comparacao_literatura`, `compatibilidade`, `lacunas_experimentais`,
`preenchimento` e `nivel_evidencia`.

Regras aplicadas:

* propriedade sem descritor oficial vai para `nao_mapeadas` — **não** vira
  descritor (o adendo §3 proíbe inventar parâmetro como descritor);
* simulador só executa com as entradas obrigatórias; sem elas o item volta
  `bloqueado_por_parametros` com `faltando`;
* modelo de adsorção só roda com os requisitos completos (Langmuir exige
  `qmax`, `KL`, `Ce`); `D2` reaproveita os pontos de `D1` (mesmo ajuste);
* compatibilidade usa regra explícita `pH × PZC` (ver `REGRA_COMPATIBILIDADE`)
  e devolve `favoravel` / `desfavoravel` / `neutro` / `indeterminado` com
  motivos e o que falta;
* `preenchimento` é calculado sobre os 28 descritores (ausente conta como
  ausente), não sobre o subconjunto preenchido.

### 11.4 Teste obrigatório (§7) — execução real medida (03/11/2026)

`python ambiental_backend/validar_adsorventes.py` (motores reais, banco real,
limpeza automática no fim):

| Etapa | Medido |
|---|---|
| referência interna | `qmax = 20,0 mg/g`, `KL = 0,5 L/mg` (experimento 4 do banco da plataforma) |
| evidências | 4 novas em bases reais (`estado: OK`) |
| material A (referência) | D1 = 20,0 mg/g, D2 = 0,5 L/mg, D6 = 80 %; Langmuir qe = 16,6667 mg/g; Freundlich qe = 15,0713 mg/g |
| material B (zeolita 4A) | 4 simuladores `ok` (`superficie`→S3, `nano`→S5+S3, `cfd`→C7, `dft`→P6); D1 = 38,0 mg/g, D2 = 0,35 L/mg, D3 = PSO, D6 = 75 %, C7 = 14,4 min, C4 = 0,3 kWh/kg, C2 = 1,1842 R$/g |
| modelos | Langmuir qe = 29,5556 mg/g; PFO qt = 34,0981 mg/g (`estado: calculado`) |
| compatibilidade | `desfavoravel` (pH 5,0 < PZC 6,8, contaminante catiônico) |
| lacunas | S1, D7, C1, C6 |
| preenchimento da matriz | A: 10,71 % (3 de 28); B: 53,57 % (15 de 28) |
| prova de conceito | `executada`, 9 de 13 passos `ok`, `demonstravel: true` |
| viabilidade | 59,39 → `viavel_com_restricoes` |
| relatórios | md 15.777 bytes; pdf 20.307 bytes (variam com o corpus recuperado) |
| painel | 29 simuladores no recorte, 29 disponíveis, 9 com descritor mapeado |

Suíte automatizada: **44 testes** (`test_ambiental_api.py` 31 +
`test_ambiental_simuladores.py` 13), sem rede, com dublês de simulador.

### 11.5 Como ler o resultado

* `nivel_evidencia` acompanha cada bloco: propriedade = dado declarado,
  simulador = resultado computacional, modelo = cálculo analítico,
  comparação = texto de evidência recuperada;
* valor de simulador **não** é capacidade experimental medida;
* `dft` devolve referência interna do próprio motor (ele se declara
  "não DFT") e entra como `estimado`;
* `superficie`/`nano` devolvem o parâmetro informado — por isso entram como
  `presente`, nunca como `calculado`;
* quando o motor roda com padrão interno, o valor padrão **não** é gravado no
  descritor e a execução é marcada `ok_com_aproximacao`.

## 12. Integração com a plataforma publicada (03/11/2026)

### 12.1 URL publicada

```
https://jaderson32-api-ambiental.hf.space
```

O frontend apontava para `https://api-ambiental.hf.space`, que **não existe**:
no Hugging Face o domínio de um Space é sempre `<dono>-<nome>.hf.space`
(verificado — `api-ambiental` devolve o 404 do próprio HF, não é hibernação).
A correção do lado do frontend é **um valor**: `VITE_API_BASE_URL` ou o campo
de "Configurações de conexão" da própria plataforma.

### 12.2 Endpoints novos desta rodada

| Rota | Para quê |
|---|---|
| `GET /api/ready` | resposta imediata, sem tocar no banco: serve para acordar/verificar |
| `GET /api/stats` | contadores reais do dashboard (`dados_demonstracao: false`) |
| `PUT/PATCH /api/research/{id}` | edição da pesquisa (campo ausente não muda; versão incrementa) |
| `PATCH /api/materials/{id}` | edição do material + merge de propriedades/composição |
| `GET /api/history` | trilha de auditoria + pesquisas + simulações + relatórios |
| `POST /api/persistence/sync` | grava o snapshot do banco no dataset de backup |

### 12.3 Persistência

O disco `/data` de um Space gratuito é descartado no reinício (medido: a
pesquisa criada antes do reinício desapareceu de `/api/history`). Para não
depender de disco pago, `persistencia_remota.py` copia o SQLite com
`sqlite3.backup` (snapshot consistente, não cópia de arquivo aberto) para o
dataset privado configurado em `AMBIENTAL_BACKUP_REPO` a cada 30 s quando o
banco muda, e restaura no startup. Medido depois do reinício do Space:
`restaurado_no_inicio: {feito: true, bytes: 262144}` e as 16 tabelas com as
mesmas contagens de antes.

Variáveis: `AMBIENTAL_BACKUP_REPO`, `AMBIENTAL_BACKUP_INTERVALO` (padrão 60 s) e
o Secret `HF_TOKEN` (token com escrita nesse dataset). Sem elas o módulo fica
inerte e `/api/health` informa `persistencia_remota.configurado = false`.

### 12.4 Validação de ponta a ponta

`validar_integracao.py` reproduz pela API o fluxo da interface (25 passos,
`Origin` do frontend em todas as chamadas) e grava um JSON em
`dados_ambiental/`. Inclui a caracterização (medições de bancada → descritor) e
a execução de **todos os 16 motores ambientais próprios**, além de um simulador
do núcleo:

```bash
python ambiental_backend/validar_integracao.py \
    --base https://jaderson32-api-ambiental.hf.space     # 25/25 passos OK
python ambiental_backend/validar_integracao.py \
    --base https://jaderson32-api-ambiental.hf.space --reiniciar --evidencias
```

Resultado medido em **02/11/2026**, a partir da pasta de publicação
(`_deploy_ambiental_v1`, `uvicorn app:app --port 7862`): **25/25 passos
aprovados** — inclusive `403` para origem intrusa, caracterização com 6
medições gravadas (S3/S4/S5/P2/S6 preenchidos), 16/16 motores ambientais
executando, cobertura da matriz subindo de 17,9% para 75%, viabilidade
`viavel_com_restricoes` (58,75), prova de conceito `demonstravel=true` e
relatório de 34.612 bytes baixado por HTTP.


## 13. Recuperação de `analises_experimentais.py` (02/11/2026)

O arquivo-fonte desse módulo foi destruído por corrupção de disco: ficou com
71.825 bytes, **todos NUL**. Não havia backup, git, cópia em outro diretório
nem cópia no histórico das sessões — tudo isso foi verificado antes de decidir
o caminho. Também não existe descompilador disponível para CPython 3.10 nesta
máquina (nem `uncompyle6`/`decompyle3`, nem `pycdc` executável, nem compilador,
nem distro WSL).

O que sobreviveu foi o bytecode compilado pelo CPython 3.10 em
`__pycache__/analises_experimentais.cpython-310.pyc` (cabeçalho
`source_size=71166`, mtime 03/11/2026 18:28). Ele foi copiado para
`_recuperacao/` e é o que o módulo carrega hoje:

```python
_MAGIC_310 = b"\x6f\x0d\x0d\x0a"          # CPython 3.10 (magic 3439)
exec(marshal.loads(dados[16:]), globals())   # código original, sem reescrita
```

Consequências, sem meias palavras:

- **o comportamento é o original**: nada foi reescrito, então nenhum resultado
  científico foi inventado, arredondado ou reinterpretado;
- **não é código editável**: `inspect.getsource` não funciona, não há depuração
  passo a passo e qualquer mudança de fórmula exige a reescrita da função;
- **exige Python 3.10** — a versão do `.pyc` e da imagem `python:3.10-slim` do
  `Dockerfile`. Em outra versão o módulo levanta `RuntimeError` explicando o
  problema, em vez de falhar em silêncio;
- a especificação extraída do `pyc` (assinaturas, docstrings, constantes e
  tabelas curadas) está em `_recuperacao/_analises_full.txt`,
  `_analises_simbolos.txt` e `_consts.txt`; os arquivos corrompidos ficaram em
  `_recuperacao/*.corrompido.bin` como prova do incidente.

Dívida técnica registrada para a v1.1: reimplementar cada função em Python
legível a partir dessa especificação e conferir o resultado **contra o `.pyc`,
usado como oráculo numérico** (mesma entrada, mesma saída). Enquanto a
equivalência não estiver provada por teste, o bytecode continua sendo a fonte.

`preparar_espaco.py` copia `_recuperacao/*.pyc` para a pasta publicada — sem
isso o Space subiria sem os 16 motores ambientais.


## 14. Interface web (SPA sem build)

A interface vive em `ambiental_backend/frontend/` e é publicada pelo próprio
`app.py`: `GET /` devolve `index.html` e `GET /app/*` serve os estáticos. Não há
etapa de build, bundler, `node_modules` nem CDN — só `index.html`, `estilos.css`
e módulos ES (`js/*.js`), o que mantém a imagem Docker sem Node.

| Rota (hash) | Tela | O que faz de verdade |
| --- | --- | --- |
| `#/painel` | Painel | contadores do banco (pesquisas, materiais, viabilidades, provas, relatórios), cobertura da matriz e atalhos |
| `#/pesquisas` | Pesquisas | cria/listá pesquisas, seleciona a ativa, monta o protocolo 7D×4 e busca evidências nas bases |
| `#/materiais` | Materiais | cadastro do material (origem, classe, área superficial, PZC, pH) por pesquisa |
| `#/caracterizacao` | Caracterização | catálogo de tipos de medição, envio de medição com réplicas (RSR), lote e resumo |
| `#/componentes` | Componentes | caracteriza adsorbato, adsorvente, interface e meio (valor, unidade, origem, método, estado) e mostra o que falta |
| `#/matriz` | Matriz 7D×4 | 28 descritores por material **+** a grade dos 28 cruzamentos 7×4 (clique abre descritores, origem, pesos e lacunas) e exportação CSV |
| `#/simuladores` | Simuladores | lista os motores executáveis, lê os requisitos, executa e valida adsorvente |
| `#/comparacao` | Comparação | compara material × literatura (qmax, área, remoção) e mostra o veredito |
| `#/relatorios` | Relatórios | gera MD/JSON/PDF/DOCX, vê o conteúdo, baixa e exclui |
| `#/historico` | Histórico | eventos reais da pesquisa e sincronização da persistência |

Como usar: suba o backend (§2.2) e abra `http://127.0.0.1:7860/` — a interface
fala com as mesmas rotas `/api/*` documentadas em §5, com `fetch` relativo (nada
de URL fixa: funciona no Space, no proxy do Hugging Face e no localhost).

Comportamento em falha, igual ao do backend: nenhum número é preenchido no
cliente. Sem pesquisa ativa cada tela mostra "selecione uma pesquisa"; erro de
API vira `.erro-caixa` com a mensagem do envelope `{"erro": {...}}`; campo
ausente na resposta aparece como `—`, nunca `NaN`/`undefined`.

### 14.1 Validação de ponta a ponta da interface (03/11/2026)

Além dos testes de pytest, a SPA foi exercitada de verdade: um `uvicorn` em
`127.0.0.1:7861` com banco SQLite temporário, e o `index.html` carregado em
**jsdom** (`runScripts: "outside-only"`, `scrollIntoView`/`confirm`/`alert`
stubados, `URL.createObjectURL` falso para o download). O harness importou
`js/app.js` como módulo ES — sem build — semeou pela API uma pesquisa,
protocolo, material, medições, descritores, viabilidade, prova de conceito e
relatório DOCX, e então clicou nos botões reais de cada tela.

Resultado: 10 rotas renderizadas com o cabeçalho e o conteúdo esperados, sem
`.erro-caixa`, sem `.carregando` preso e sem `undefined`/`NaN`/`[object Object]`
no texto; e 14 ações concluídas com o toast correto — montar protocolo,
avaliar viabilidade, prova de conceito, registrar medição, gravar parâmetro de
componente, gravar descritor pelo modal da matriz, abrir um dos 28 cruzamentos,
executar simulador pelo modal, validar adsorvente, gerar relatório, atualizar o
histórico e sincronizar a persistência.

Dois defeitos reais foram encontrados e corrigidos por esse caminho:

1. `telas/painel.js` lia contadores planos; a API devolve objetos aninhados
   (`estatisticas.viabilidades.total`, ...) e a cobertura da matriz em
   `linhas_possiveis`/`descritores_por_material`/`cobertura_pct` — o painel
   mostrava `undefined` nos cartões;
2. `ui.campo()` criava `<input>`/`<select>` com o atributo `nome` em vez de
   `name`: nenhum formulário era lido por `ui.lerFormulario()` (que percorre
   `[name]`) nem alcançado por `[name="..."]`, então medição, descritor e
   simulador subiam vazios. Agora todo campo sai com `name`.

O harness fica fora da suíte (precisa de `node` + `jsdom` e de um servidor
real); o que ele garante de forma permanente está em
`test_ambiental_interface.py` (§8).


## 15. Matriz 7×4: os 28 cruzamentos e a ponderação (04/11/2026)

A matriz declarada em `matriz_7d4.py` (28 descritores, 4 dimensões de
diagnóstico) continua sendo a fonte dos descritores. Sobre ela,
`matriz_cruzamentos.py` organiza os **28 cruzamentos** entre as sete dimensões
informacionais e os quatro componentes do sistema de adsorção:

| Letra | Dimensão informacional | Pergunta |
| --- | --- | --- |
| E | Energética | Quanta energia o sistema exige, dissipa ou libera? |
| P | Eletrônica | Como os elétrons se distribuem nos componentes? |
| D | Estrutural | O que o material é e como está organizado? |
| S | Superficial | Qual a química da superfície em contato com o fluido? |
| I | Interacional | Quanto e como adsorbato e adsorvente interagem? |
| C | Ambiental | Que risco, resíduo e emissão o sistema carrega? |
| O | Operacional | O sistema funciona e se paga na escala real? |

Componentes: **adsorbato**, **adsorvente**, **interface** e **meio** — 7 × 4 =
28 cruzamentos. Cada cruzamento recebe **todos** os descritores que o informam
(S3 informa D-adsorvente e I-interface, por exemplo), e nenhum descritor foi
criado para preencher célula: `estrutura()["sem_cruzamento"]` é vazio porque
todo descritor do catálogo tem relação declarada.

### 15.1 Formação dinâmica

`matriz_cruzamentos.montar()` recebe os descritores do material, a
caracterização dos quatro componentes (`componentes.parametros_de`), a pergunta
e a aplicação da pesquisa, e devolve as 28 células. A célula que não tem dado
volta com `com_dado=0`, `cobertura=0`, `indice_*` nulo e a lista `lacunas` —
nunca com zero.

### 15.2 Ponderação (sem 40/20/20/20)

O peso de cada descritor **dentro do seu cruzamento** vem de critérios que já
existiam no projeto:

```
peso_bruto = qualidade(estado) × pertinência(selecionar) ×
             utilidade(entropia) × (1 − redundância)
peso       = peso_bruto / Σ peso_bruto do cruzamento
```

- **qualidade** — hierarquia de `ESTADOS_DADO`: validado 1,00; presente 0,85;
  calculado 0,60; estimado 0,40; ausente e não aplicável 0.
- **pertinência** — `matriz_7d4.selecionar()` (+3 sinônimo, +2 aplicação,
  +1 essencial) com base 1, normalizada pelo máximo.
- **utilidade** — 1 − entropia de Shannon dos valores (min-max) do descritor
  entre os materiais da pesquisa; descritor constante = 0; sem dois materiais,
  fator neutro 1,0.
- **redundância** — maior |r| de Pearson com outro descritor medido, declarada
  só com **≥ 4 materiais** e |r| acima do valor crítico a 95 %.

Indicadores por cruzamento: `cobertura` (soma dos pesos com dado),
`indice_qualidade` (peso × qualidade) e `indice_comparativo` (peso × valor
min-max entre materiais; nulo quando não há dois materiais). O método inteiro
viaja na resposta (`metodo`) e vai para o DOCX/PDF.

### 15.3 Caracterização dos componentes

`amb_componentes` (esquema v3) guarda, por material e componente, `chave`,
`valor`, `unidade`, `origem` (informado/importado/medido/calculado/simulado),
`método`, `referência` e `estado`. O catálogo tem 54 parâmetros — do adsorbato
(massa molar, pKa, HOMO/LUMO, energia de hidratação) ao meio (pH, temperatura,
força iônica, C0, tempo de contato, perda de carga). Quando o parâmetro declara
um descritor 7D×4 (área BET → S3, PZC → P2, qmax → D1), o valor entra na matriz
pela via oficial (`motor_pesquisa.registrar_valor_medido`), com fonte e
detecção de conflito — sem duplicar dado. `GET /api/simulators/{nome}/parameters`
lê essa caracterização e pré-preenche os requisitos do motor.

### 15.4 Testes desta camada

`test_ambiental_cruzamentos.py` (16 testes) cobre: 28 cruzamentos e cobertura
dos 28 descritores; célula vazia sem valor nem zero; normalização dos pesos em
1; qualidade por estado; ausência sem peso; entropia e índice comparativo só
com dois materiais; redundância exigindo 4 materiais e correlação
significativa; parâmetros no cruzamento; CSV; e o contrato das rotas novas
(inclusive 400 para componente/parâmetro inválido e o pré-preenchimento do
simulador).


## 16. Publicação de 04/11/2026 (matriz 7×4 + quatro componentes)

Pacote regenerado com `python ambiental_backend/preparar_espaco.py
_deploy_ambiental` e publicado no Space `Jaderson32/api-ambiental` por
`_publicar_espaco.py` (lê o token do `.env`, nunca imprime).

| Item | Valor |
| --- | --- |
| URL funcional | `https://jaderson32-api-ambiental.hf.space` |
| Estado | `stage=RUNNING`, `GET /api/ready` → `{"estado":"pronto"}` |
| Interface | `/` responde a SPA com as 10 telas; `/app/js/telas/componentes.js` e `/app/js/telas/matriz.js` servidos |
| Catálogo de componentes | `GET /api/componentes` → 59 parâmetros |
| Contrato | 51 rotas em `/openapi.json` |

### 16.1 Bug de publicação encontrado e corrigido

O `preparar_espaco.py` gerava um `.gitignore` com `*.pyc`, e o
`upload_folder` do `huggingface_hub` também ignora `.pyc`. Resultado: o
bytecode recuperado de `analises_experimentais` (CPython 3.10) **não subia** e
o Space morria no import com
`RuntimeError: ... bytecode original preservado: ausente`. Correção dupla:

1. `.gitignore` do pacote agora tem `!ambiental_backend/_recuperacao/*.pyc`;
2. `_publicar_espaco.py` envia esse arquivo explicitamente, depois do
   `upload_folder` (o filtro do cliente não é configurável por argumento).

Depois disso o Space subiu e a verificação `_smoke_publicado.py` passou inteira
(13 checagens): pesquisa e material criados, caracterização do adsorvente
alimentando S3/P2/S6, meio gravado sem aviso, 28 cruzamentos montados com a
área BET e peso, lacunas sem virarem zero, simulador pré-preenchido
(`area_m2g = 750`), execução `ok`, CSV com 55 linhas e relatório com as seções
3.1/3.2/3.3.
### 16.2 Republicação verificada (build e API conferidos no Hub e por HTTP)

> **Estado atual do Space: `PAUSED` por cota da conta.** O Hugging Face recusa
> religar com `403 You've reached your cpu-basic quota limit` — e os três
> Spaces da conta (`api-ambiental`, `alef-tav-backend`, `Empower-minds`) estão
> pausados, ou seja, não há o que pausar para liberar espaço. O repositório
> publicado continua íntegro (65 arquivos, `Dockerfile`, `app.py`, bytecode
> recuperado, 10 telas) e volta a subir assim que houver cota:
>
> ```
> python _religar_espaco.py          # detecta PAUSED, pede restart e espera RUNNING
> ```
>
> Enquanto isso a aplicação foi verificada **localmente**, com o mesmo código:
> `uvicorn ambiental_backend.app:app` + `_smoke_publicado.py http://127.0.0.1:7872`
> → 13/13. O bloqueio é de hospedagem, não de código.

Rodada de controle sobre o mesmo Space, sem alterar módulos científicos:

* o pacote foi regenerado (`preparar_espaco.py _deploy_ambiental`, 64 arquivos,
  `sdk: docker`, `app_port: 7860`, `CMD uvicorn app:app --port 7860`) e o
  `upload_folder` respondeu *"No files have been modified"* — o que está no
  Space é idêntico ao pacote local, inclusive `README-BACKEND.md` com esta
  seção;
* `space_info` → `stage=RUNNING`, `sdk=docker`, público, `cpu-basic`; o
  bytecode recuperado está no repo (`ambiental_backend/_recuperacao/
  analises_experimentais.cpython-310.pyc`);
* `/api/ready` 200, `/docs` 200, `/openapi.json` 200 com **51 rotas / 66
  operações** — conjunto idêntico ao de `_integracao_ai_studio/contrato_api.json`;
* preflight CORS responde com `access-control-allow-origin` refletido para
  `https://aistudio.google.com` e `http://localhost:5173`;
* `_smoke_publicado.py` → 13/13 (material, caracterização alimentando
  S3/P2/S6, 28 cruzamentos com peso, lacunas sem virar zero, simulador
  pré-preenchido e executado, CSV com 55 linhas, relatório com 3.1/3.2/3.3);
* varredura de segredos no pacote: nenhum token e nenhum `.env`.

`https://api-ambiental.hf.space` continua **inexistente** (404 do HF): o
endereço direto de um Space é `<dono>-<nome>.hf.space`. A conta é PRO, então
"custom domain" está disponível, mas ele aponta para um domínio do
proprietário — não cria subdomínio de `hf.space`. A base efetiva é
`https://jaderson32-api-ambiental.hf.space`.


### 16.3 Integração com o frontend do AI Studio

O pacote `_integracao_ai_studio/` reúne o contrato real (`contrato_api.json`,
gerado do código), o mapa `tela → endpoint` (`telas.md`), as variáveis
(`VITE_BACKEND_URL` / `VITE_API_BASE_URL`) e um prompt pronto
(`prompt_frontend.md`). **O projeto do AI Studio não foi alterado por este
ambiente** — não há credencial dele aqui; o que existe é o pacote para a
atualização, com o backend já publicado e verificado.

---

## 17. Luna — assistente conversacional (OpenAI)

A Luna é a assistente da plataforma e roda **no backend**. O navegador manda a
pergunta; o backend consulta o banco pelas ferramentas e devolve a resposta com
a lista do que foi consultado. O modelo não calcula nada: a matriz 7D×4, os
pesos, os simuladores e os relatórios continuam sendo os mesmos módulos.

### 17.1 Onde está cada peça

| Peça | Arquivo |
| --- | --- |
| Motor da conversa (chamada OpenAI + *function calling*) | `ambiental_backend/luna.py` |
| Rotas | `api_ambiental.py`: `GET /api/luna/status`, `POST /api/luna/chat`, `GET`/`DELETE /api/luna/historico` |
| Histórico | tabela `amb_luna_conversas` (`persistencia.py`, esquema v4) |
| Tela | `frontend/js/telas/luna.js`, registrada em `js/app.js` (11ª tela) e `js/api.js` |
| Testes | `test_ambiental_luna.py` (8 testes, sem rede) |
| Verificação real | `_smoke_luna.py` (contra o Space) · `_e2e_dom/e2e.mjs` (DOM) |

### 17.2 As 16 ferramentas (todas de leitura)

`estado_plataforma`, `listar_pesquisas`, `obter_pesquisa`, `listar_materiais`,
`descritores_material`, `caracterizacao_componentes`, `catalogo_parametros`,
`explicar_descritor`, `estrutura_matriz`, `matriz_montada`, `simuladores`,
`requisitos_simulador`, `resultados_simulacoes`, `relatorios_pesquisa`,
`resumo_pesquisa`, `historico_recente`.

Nenhuma escreve no banco e nenhuma executa simulador: execução e gravação
continuam nas telas e nas rotas que já existiam.

### 17.3 Modelo

Ordem de escolha, sem inventar nome: `OPENAI_MODEL` (variável/Secret) e, sem
ela, `GET /v1/models` na conta → primeiro id que casar com a lista de
preferência (`gpt-6`, `gpt-6-mini`, `gpt-5.1`, `gpt-5`, `gpt-5-mini`,
`gpt-4.1`, `gpt-4.1-mini`, `gpt-4o`, `gpt-4o-mini`). A resposta sempre informa
`modelo` e `modelo_origem` (`OPENAI_MODEL` ou `descoberto na conta`). Se nenhum
modelo da lista estiver autorizado, a rota responde 502 explicando quais ids
existem — não há fallback silencioso.

### 17.4 Segurança da chave

- `OPENAI_API_KEY` vive só no ambiente do backend (Secret do Space). Não há
  caminho de código que a devolva: `/api/luna/status` mostra `configurada`, não
  a chave; `luna._redigir()` apaga a chave de qualquer mensagem de erro; e o
  teste `test_redige_a_chave_em_mensagem_de_erro` prova isso com um 401 real
  simulado.
- O pacote publicado não leva `.env`; a varredura de segredos do
  `_publicar_espaco.py` continua rodando antes do upload.

### 17.5 Configurar e verificar

```bash
# 1. grava o Secret no Space e reinicia (nunca imprime a chave)
python _configurar_luna.py                 # le OPENAI_API_KEY do .env / ambiente
python _configurar_luna.py --modelo gpt-6  # opcional: fixa o modelo

# 2. confere de fora, contra a URL publica
python _smoke_luna.py
```

Sem a chave, `/api/luna/status` responde `configurada: false` com o aviso e
`POST /api/luna/chat` responde **503** `luna_nao_configurada`. A tela mostra o
passo a passo do Secret, desabilita o campo e **não simula resposta** — o
`_e2e_dom/e2e.mjs` verifica exatamente isso.

### 17.6 Estado desta entrega (sem confundir as etapas)

| Etapa | Situação |
| --- | --- |
| Implementado | **sim**: motor, 16 ferramentas, 4 rotas, tabela `amb_luna_conversas` (esquema v4), tela (11ª), 8 testes |
| Testado de verdade | **sim, no que não depende da chave**: `pytest ambiental_backend` → **133 passed**; E2E de DOM (`_e2e_dom/e2e.mjs`) → **11 telas, tudo passou**, incluindo `#/luna` renderizando, `/api/luna/status` e `/api/luna/historico` realmente chamados, campo desabilitado e nenhuma resposta fingida; `_smoke_publicado.py` local → **13/13** |
| Pacote preparado | **sim**: `_deploy_ambiental` com **66 arquivos**, `ambiental_backend/luna.py` e `frontend/js/telas/luna.js` presentes, nenhum `test_*.py`/`conftest.py`, varredura de segredos limpa (sem `.env`, sem `sk-`) |
| Publicado no Space | **sim**: commit `df09ddb` — *"luna (openai): assistente com 16 ferramentas de leitura, tela de conversa e historico por pesquisa/usuario (11 telas, 133 testes)"*. Conferido pelo próprio Hub: `ambiental_backend/luna.py` (43,3 kB), `frontend/js/telas/luna.js` (9,5 kB), `api_ambiental.py`, `app.py`, `persistencia.py` e `README-BACKEND.md` no mesmo commit; `13 commits`, nenhum `.env` no repositório |
| Configurado (chave) | **não**: não existe `OPENAI_API_KEY` neste ambiente (nem no `.env`, nem nos Secrets do Space) |
| Diálogo real com a OpenAI | **não testado** — sem credencial aqui. Não há afirmação de teste que não aconteceu |
| Runtime público | **`PAUSED` por cota**: `/api/luna/status` responde 503 enquanto a conta estiver sem `cpu-basic` (ver §16.2) |

Falta apenas o Secret (a publicação já está no Space). Um comando por etapa:

```bash
python _configurar_luna.py   # grava OPENAI_API_KEY nos Secrets e reinicia o Space
python _smoke_luna.py        # conversa real: status -> chat -> historico
```

Se o Space estiver `PAUSED` por cota, `python _religar_espaco.py` antes do
`_smoke_luna.py`.

Para republicar depois de qualquer mudança: `python _publicar_tudo.py`
(remonta o pacote, roda a varredura de credenciais e envia com 3 tentativas por
chamada de rede). Em terminal que trata silêncio como travamento, use
`python _publicar_com_progresso.py`, que imprime um ponto a cada 300 ms
enquanto o upload roda — foi assim que este commit subiu.



