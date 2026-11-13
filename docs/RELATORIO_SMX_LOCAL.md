# Relatório — teste SMX local (dois carvões KL-KOH, sem HF, sem HTTP)

Execução local do fluxo de pesquisa → validação de adsorvente → simuladores → modelos →
viabilidade → prova de conceito → relatório, usando `ambiental_backend` direto (sem uvicorn,
sem Hugging Face, sem internet).

- **Contaminante:** sulfametoxazol (SMX), informado como `sulfametoxazol, classe ionica: anion organico`
- **Materiais (literatura):** KL-KOH-1:1 (S_BET 1262 m²/g, V_p 0,58 cm³/g) e KL-KOH-2:1 (963 m²/g, 0,49 cm³/g)
- **PZC e KL:** ausentes de propósito (não reportados na fonte) — o sistema **não** deve inventá-los
- **Regras respeitadas:** sem internet, sem `HF_TOKEN`, sem `AMBIENTAL_BACKUP_REPO`, nenhum valor fabricado
- Data: 2026-11-10

---

## Etapa 0 — Ambiente

| Item | Resultado |
|---|---|
| `python --version` | **3.13.9** (miniconda base) |
| Versões alternativas | `py -0p` → 3.12 (`AppData\Local\Programs\Python\Python312`); **não há CPython 3.10** |
| `ALEF_SEM_PREAQUECER` | `1` |
| `PYTHONDONTWRITEBYTECODE` | `1` |
| `HF_TOKEN` / `AMBIENTAL_BACKUP_REPO` | vazio (persistência remota reporta `configurado: False`) |
| `adaptadores.estado_motores()` (sem núcleo) | `universal`, `modelos_adsorcao_v2`, `modelos_analiticos_v2`, `pesquisa_cientifica`, `bancos_rest`, `bases_v5`, `nucleo_dados`, `exportadores` → todos **`ausente`** |
| `adaptadores.nomes_disponiveis()` (sem núcleo) | **16** nomes (só os motores próprios do backend: `pzc_deriva_ph`, `tga_tangente`, `boehm_grupos`, `seletividade_competitiva`, ...) |
| `analises_experimentais` | **STUB LOCAL** ativo (`[QA] analises_experimentais: STUB LOCAL ativo`) |

**Desvio registrado (D-A):** o ambiente-alvo pedido era CPython 3.10; a máquina só tem 3.13.9 e 3.12.
`analises_experimentais.py` depende de bytecode 3.10 e foi substituído por um stub que levanta
`RuntimeError` no uso (comportamento anterior já documentado em `RELATORIO_TESTE_SMX_API.md`).
Os 16 motores do backend que dependem desse módulo ficam **bloqueados por indisponibilidade**, não
por falta de dado — e o teste segue, registrando o motivo.

---

## Etapa 1 — Núcleo científico localizado

### Onde procurei (busca local, sem rede)
`C:\Users\PC\Desktop` (recursivo), `Documents`, `Downloads`, `OneDrive`, `C:\alef`, `D:\`,
`C:\Users\PC\projects`, `miniconda_alef`, `.alef_tav_cache`, `dissertação`, `chatbot`, `Ativvvv`.

### O que existe

| Arquivo | Situação |
|---|---|
| `C:\Users\PC\shiryon_deploy\universal.py` (72.300 B) | **encontrado** — "BANCO UNIVERSAL DE SIMULADORES"; só depende de `numpy` (2.5.3 instalado) |
| `bases_v5.py`, `exportadores.py` (mesma pasta) | encontrados |
| `modelos_adsorcao_v2.py` | **não existe** na máquina |
| `modelos_analiticos_v2.py` | **não existe** na máquina |
| `pesquisa_cientifica.py`, `bancos_rest.py`, `nucleo_dados.py` | **não existem** na máquina |
| `analises_experimentais*.pyc` | **não existe** em `C:\Users\PC` (nada para carregar) |

### Configuração usada
```powershell
$env:ALEF_TAV_CORE      = "C:\Users\PC\shiryon_deploy"
$env:AMBIENTAL_DADOS    = "C:\Users\PC\Desktop\Projetos\Nova pasta\dados_ambiental"
$env:ALEF_SEM_PREAQUECER = "1"
$env:AMBIENTAL_BACKUP_REPO = ""; $env:HF_TOKEN = ""
```

`estado_motores()` com o núcleo apontado:

```json
{ "universal": "disponivel", "modelos_adsorcao_v2": "ausente",
  "modelos_analiticos_v2": "ausente", "pesquisa_cientifica": "ausente",
  "bancos_rest": "ausente", "bases_v5": "disponivel",
  "nucleo_dados": "ausente", "exportadores": "disponivel" }
```
`nomes_disponiveis()` → **129** simuladores, incluindo `superficie`, `nano`, `cristalografia`, `cfd`, `dft`.

### Dois efeitos colaterais que precisaram de correção de ambiente
1. **`ALEF_TAV_CORE` muda o diretório de dados.** `config.diretorio_dados()` devolve `CORE/dados_ambiental`,
   então o banco passou a ser um arquivo novo e vazio → `sqlite3.OperationalError: no such table: amb_historico`.
   Corrigido fixando `AMBIENTAL_DADOS` no projeto **e** chamando `persistencia.garantir_esquema()` uma vez.
2. **`analises_experimentais.pycshim` NÃO foi restaurado.** A instrução de restaurar vale quando o `.pyc`
   CPython 3.10 existe; aqui não existe (Python 3.13), então restaurar reintroduziria o `ImportError`.
   O stub foi mantido e o desvio registrado.

---

## Etapa 2 — Os três bugs

### Inspeção prévia (antes de editar)
- `CARACTERIZACAO` **já** mapeia `qmax` → `D1` **e** `capacidadeadsorcao` → `D1`.
- `volumedeporos` → `S4` **já** existia; o problema era só a grafia `volume_poros`, que normaliza
  para `volumeporos` (sem `de`) e caía em `nao_mapeadas`.
- `CLASSES_CONTAMINANTE["anion_organico"]` não tinha SMX (e `organico_neutro` tem `"antibiotico"`,
  o que classificaria o fármaco como neutro se a classe aniônica não fosse reconhecida).

### Edições feitas em `ambiental_backend/adsorventes.py` (2 linhas)

```diff
     "volumedeporos": {"codigo": "S4", "unidade": "cm3/g"},
+    "volumeporos": {"codigo": "S4", "unidade": "cm3/g"},
```
```diff
     "anion_organico": ("alaranjado de metila", "corante anionico", "eosina",
-                       "acido humico", "tensoativo anionico"),
+                       "acido humico", "tensoativo anionico",
+                       "sulfametoxazol", "sulfa", "antibiotico anionico"),
```

### Bug #1 (qmax só como propriedade) — corrigido no cliente, sem tocar no backend
O script envia o qmax **na caracterização** (`capacidade_adsorcao`), que é o caminho que grava `D1`:

```python
"caracterizacao": {
    "area_superficial":    {"valor": 1262.0, "unidade": "m2/g",  "metodo": "BET N2", "origem": "Brazil et al., 2026"},
    "volume_de_poros":     {"valor": 0.58,   "unidade": "cm3/g", "origem": "Brazil et al., 2026"},
    "capacidade_adsorcao": {"valor": 100.0,  "unidade": "mg/g",  "origem": "Brazil et al., 2026"},
}
```

| Antes (só `POST /materials`) | Agora (via caracterização) |
|---|---|
| `D1` ausente; Langmuir `faltando: ['qmax', 'KL']` | `D1 = 100,0 mg/g` **`presente`**; Langmuir `faltando: ['KL']` |

### Bug #2 (`volume_poros`) — corrigido nos dois lados
Cliente usa `volume_de_poros` (→ `volumedeporos`, já mapeado) **e** o alias `volumeporos` foi
acrescentado para a grafia antiga não cair mais em `nao_mapeadas`.
Evidência: `S4 = 0,58` (A) e `0,49` (B) cm³/g, estado **`presente`**.

### Bug #3 (classe aniônica) — corrigido

| Antes | Agora |
|---|---|
| `classe_contaminante = "nao_classificado"`; `compatibilidade.faltando = ['P2 (PZC)', 'classe do contaminante']` | `classe_contaminante = "anion_organico"`; `compatibilidade.faltando = ['P2 (PZC)']` |

**Risco verificado (sem regressão):** `"sulfa"` é substring de `"sulfato"`, mas `oxianion` é avaliado
**antes** de `anion_organico` na ordem do dicionário, então `"sulfato"` continua oxianiônio; e a pista
`"antibiotico anionico"` é frase completa, então `"antibiotico"` isolado continua em `organico_neutro`.

### Verificação de não-regressão
```
python -m pytest -q test_ambiental_simuladores.py -k "classe or contaminante or caracteriza or mapea or descritor"
→ 3 passed, 10 deselected
```


---

## Etapa 3 — `smx_local.py` e execuções

Script criado na raiz (`smx_local.py`, na forma pedida): pesquisa → 2 materiais → validação de cada
adsorvente → comparação → viabilidade → prova de conceito → relatório `.md`, gravando
`resultado_smx_local.json`. Três execuções registradas (a primeira serve de linha de base, antes de
qualquer núcleo; as duas últimas são as oficiais):

| Execução | `ALEF_TAV_CORE` | pesquisa_id | Simuladores executados | Cobertura |
|---|---|---|---|---|
| **S1** (histórico limpo, `_smx_local_log.txt`) | ausente | `pesq_e3479602c6e6d81f` | nenhum | **3/28 (10,71 %)** |
| **S2** oficial sem núcleo | ausente | `pesq_b3392d1e023dd4b1` | nenhum | **4/28 (14,29 %)** |
| **S3** oficial com núcleo | `C:\Users\PC\shiryon_deploy` | `pesq_84dbc8b31c8a40a5` | `superficie`, `cristalografia`, `cfd`, `dft` | **4/28 (14,29 %)** |

> A diferença S1×S2 **não** vem do núcleo: é o achado **F1** (descritor `P6` herdado do material
> reutilizado). O ganho real do núcleo é **1 descritor** (`P6`, `estimado`).

### Resultado por material (execução com núcleo, `pesq_84dbc8b31c8a40a5`)

| Descritor | KL-KOH-1:1 (A) | KL-KOH-2:1 (B) | Estado | Fonte |
|---|---|---|---|---|
| S3 (área superficial) | 1262,0 m²/g | 963,0 m²/g | `presente` | Brazil et al., 2026 |
| S4 (volume de poros) | 0,58 cm³/g | 0,49 cm³/g | `presente` | Brazil et al., 2026 |
| D1 (capacidade) | 100,0 mg/g | 100,0 mg/g | `presente` | Brazil et al., 2026 |
| P6 (bandgap) | 2,0 eV | 2,0 eV | `estimado` | simulador `dft` (ver F3) |

| Item | Material A | Material B |
|---|---|---|
| Langmuir | `bloqueado_por_parametros` — `faltando: ['KL']`, `qe: null` | idem |
| Freundlich | `bloqueado_por_parametros` — `faltando: ['Kf', 'n']`, `qe: null` | idem |
| Compatibilidade | `indeterminado` — `faltando: ['P2 (PZC)']`, classe `anion_organico`, pH 5,5 | idem |
| Cobertura | 4/28 (14,29 %) — presente 3, estimado 1, ausente 24 | idem |
| Lacunas | `S1, P2, D2, D3, D6, D7, C1, C6` | idem |

### Simuladores (execução com núcleo)

| Simulador | Estado | Descritor alimentado | Observação |
|---|---|---|---|
| `superficie` | `ok` (0,114 s) | S3 | devolve `area_m2g` **igual ao parâmetro recebido** (F2) |
| `cristalografia` | `ok_com_aproximacao` | S2 (não gravado) | `parametro_rede` interpretado em **metros** (F4) |
| `cfd` | `ok` | C7 (não gravado) | `Re = 50`, regime `laminar` (F5) |
| `dft` | `ok` | P6 = 2,0 eV | veio de `bandgaps["default"]`, não do material "C" (F3) |
| `nano` | `bloqueado_por_parametros` | — | `faltando: ['diametro_nm']` (F6) |

Sem núcleo, os cinco ficam `indisponivel` com `executado = False` — nenhum valor fabricado.

### Fechamento do fluxo

| Artefato | Resultado |
|---|---|
| Comparação | **empate** — cobertura A = B = 4; "sem D1/D2 medido, nenhum dos dois pode ser declarado melhor" |
| Viabilidade | pontuação **29,57**, classificação **`requer_dados`**; lacunas: `24 descritores sem dado na matriz`, `evidências insuficientes (0; mínimo 3)`, `risco e conformidade incompletos (P7, C1, C6)` |
| Prova de conceito | estado **`parcial`**, `demonstravel = False` |
| Relatório | `dados_ambiental\relatorios\viabilidade_pesq_84dbc8b31c8a40a5_rel_1eb644f6afbf4f28.md` (17,9 kB) |

**Veredito do QA:** o empate é o resultado honesto — os dois carvões só têm S3/S4/D1, o `D1` é
hipótese idêntica (100 mg/g) para ambos, e faltam `D2` (KL) e `P2` (PZC) para qualquer discriminação
físico-química.


---

## Achados do QA

### F1 — Cobertura da matriz não é idempotente (crítico)
Descritores são gravados por `material_id` (`amb_descritores`), e `_resolver_material` **reutiliza**
o material pelo nome (`criado = False`). Logo, `_preenchimento_matriz(sessao, material.id)` conta
descritores de **execuções anteriores**, inclusive de simuladores que já não rodam.

Prova (mesmo código, mesmo banco, sem núcleo, mesma caracterização):

| Material | `criado` | por_estado | Cobertura |
|---|---|---|---|
| `KL-KOH-1:1` (já existia) | `False` | presente 3, **estimado 1**, ausente 24 | **4/28** |
| `KL-KOH-1:1-fresh` (novo) | `True` | presente 3, **estimado 0**, ausente 25 | **3/28** |

O `estimado 1` herdado é `P6 = 2,0 eV`, que só existiu na execução **com** núcleo. Bancos de QA
recriados (`--limpar`) não resolvem: o dado vive no material, não na pesquisa.
**Correção sugerida:** escopar descritores derivados de simulação por `(pesquisa_id, material_id)`
ou marcar/invalidar descritores de simulação quando o motor não executar.

### F2 — `sim_superficie` apenas ecoa o parâmetro (não valida nada)
```python
def sim_superficie(pergunta, p):
    return {"simulador":"Superficie", "dominio":"Quimica - Superficie",
            "area_m2g": p.get("area_m2g", 500), "validacao":"Area superficial"}
```
`area_m2g = 1262.0` no `resultado_json` é o **valor de entrada de volta**. Sem `area_m2g`, devolveria
`500` (default) e o S3 passaria a ter um valor que a fonte não reportou — o `default` é o risco aqui.

### F3 — `sim_dft` devolve bandgap de dicionário fixo (`default: 2.0`)
```python
bandgaps = {"Si":1.12, "Ge":0.66, "GaAs":1.42, "diamond":5.47,
            "graphene":0.0, "MoS2":1.8, "TiO2":3.2, "default":2.0}
bg = bandgaps.get(material, bandgaps["default"])
```
`material = "C"` **não está** no dicionário → `P6 = 2,0 eV`, gravado como `estimado`.
Não é cálculo DFT nem valor de literatura: é o *default* do núcleo legado. O rótulo `estimado`
é honesto, mas esse número não deve ser usado em conclusão. (Sem `material`, cairia em `"Si"` = 1,12 eV,
igualmente arbitrário.)

### F4 — `sim_cristalografia` espera `parametro_rede` em **metros**
Default `3.57e-10`; o script passou `3.5` (Å). Resultado: `d_espacamento = 1,54e-10 m` fisicamente
sem sentido e **S2 não é gravado** (`estado = ausente`, `valor = None`), apesar de o simulador
reportar `ok_com_aproximacao`. Falta contrato de unidade explícito (`parametro_rede_m`).

### F5 — `sim_cfd` roda, mas C7 não é gravado
Saída real: `Re = 50`, `regime = laminar` (0,001 s). O descritor `C7` ("Escalabilidade e operação")
fica `ausente` — não há mapeamento saída→descritor. Ou seja: o simulador "ok" não melhora a matriz.

### F6 — Nomes de parâmetro divergentes entre backend e núcleo
`nano` exige `diametro_nm`; o backend/script envia `diametro` (em metros) → `bloqueado_por_parametros`.
O bloqueio é o comportamento correto (não inventou diâmetro), mas o contrato é ambíguo: dois nomes
para a mesma grandeza, com unidades diferentes.

### F7 — Simulador `indisponivel` não diz o motivo na lista de faltantes
Sem núcleo: `superficie`, `cristalografia`, `cfd`, `dft` retornam `estado = indisponivel`,
`executado = False` e **`faltando = []`**. A causa (`universal` ausente) só aparece em
`adaptadores.estado_motores()`, não no item. `nano` é o único que informa (`['diametro_nm']`).

### F8 — Ambiente sem CPython 3.10 (bloqueia 16 motores)
Suíte completa: **93 passed, 40 failed**. Todas as 40 falhas rastreiam para
`RuntimeError` do stub (`analises_experimentais`) ou para `modelos_adsorcao_v2`/`modelos_analiticos_v2`
ausentes — nada relacionado às duas linhas editadas. Destaque: `test_validacao_adsorvente_completa`
(`langmuir` = `erro` em vez de `calculado`) e `test_prova_de_conceito_por_material`
(`modelos_adsorcao` = `ausente`) falham **por falta do núcleo**, não por regressão.

### F9 — `ALEF_TAV_CORE` troca o diretório de dados
`config.diretorio_dados()` = `CORE/dados_ambiental`. Apontar o núcleo para fora do projeto cria
banco vazio → `no such table: amb_historico` na primeira gravação. Operacionalmente é preciso
`AMBIENTAL_DADOS` + `persistencia.garantir_esquema()`; isso deveria estar no README/`preparar_espaco`.

### O que o sistema fez certo
- Nada foi inventado: Langmuir/Freundlich `bloqueado_por_parametros` com `qe = null`; PZC e KL
  ausentes permaneceram ausentes; `compatibilidade` = `indeterminado`.
- Nível de evidência declarado por artefato (dado do operador × resultado computacional × cálculo).
- `nano` bloqueou em vez de assumir 5 nm (default do núcleo).
- Versão do esquema registrada (`amb_esquema`) e histórico auditável (`amb_historico`).


---

## Reprodução

```powershell
cd "C:\Users\PC\Desktop\Projetos\Nova pasta"

# ambiente (sem rede, sem HF)
$env:ALEF_SEM_PREAQUECER   = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:AMBIENTAL_BACKUP_REPO = ""
$env:HF_TOKEN              = ""
$env:PYTHONIOENCODING      = "utf-8"

# banco no projeto (obrigatório quando ALEF_TAV_CORE aponta para fora)
$env:AMBIENTAL_DADOS = "C:\Users\PC\Desktop\Projetos\Nova pasta\dados_ambiental"
python -c "from ambiental_backend import persistencia; persistencia.garantir_esquema()"

# núcleo científico (opcional: sem ele os simuladores ficam "indisponivel")
$env:ALEF_TAV_CORE = "C:\Users\PC\shiryon_deploy"

# teste SMX: dois carvões KL-KOH
python smx_local.py
```

Resultado esperado: `resultado_smx_local.json` na raiz, relatório `.md` em
`dados_ambiental\relatorios\`, comparação `empate`, viabilidade `requer_dados`, prova `parcial`.

---

## Artefatos gerados

| Arquivo | Conteúdo |
|---|---|
| `smx_local.py` | script do teste (pesquisa → 2 materiais → comparação → viabilidade → prova → relatório) |
| `resultado_smx_local.json` | saída da última execução (com núcleo) |
| `resultado_smx_local_com_nucleo.json` | execução S3 (`pesq_84dbc8b31c8a40a5`) |
| `resultado_smx_local_sem_nucleo.json` | execução S2 (`pesq_b3392d1e023dd4b1`) |
| `_smx_local_com_nucleo.txt` | log UTF-8 da execução S3 |
| `_smx_local_sem_nucleo.txt` | log UTF-8 da execução S2 |
| `_smx_local_log.txt` | log da primeira execução (histórico limpo, 3/28) |
| `_probe_descritores.py` | sonda que comprova F1 (material novo × reutilizado) |
| `_probe_db.py` | inspeção do banco (materiais, vínculos, descritores por material) |
| `dados_ambiental\relatorios\viabilidade_pesq_*.md` | relatórios de viabilidade produzidos |
| `RELATORIO_SMX_LOCAL.md` | este relatório |

## Estado do banco (dados de teste)

`dados_ambiental\ambiental.db` — 19 tabelas `amb_*`. Contém resíduos de QA:
11 pesquisas (`pesq_32e6b57abd164fb8`, `pesq_3b0bc00178637e58`, `pesq_429bc370fefd1da7`,
`pesq_531f88b620d18602`, `pesq_54dcc16380758a81`, `pesq_650c3f54408eece2`,
`pesq_84dbc8b31c8a40a5`, `pesq_b3392d1e023dd4b1`, `pesq_c541a5d1ba3d7321`,
`pesq_c93b73b90feeaeac`, `pesq_e3479602c6e6d81f`) e 3 materiais
(`KL-KOH-1:1`, `KL-KOH-2:1`, `KL-KOH-1:1-fresh`).

Para zerar o efeito de F1 sem apagar as pesquisas:

```sql
DELETE FROM amb_descritores WHERE codigo = 'P6' AND valor = 2.0 AND estado = 'estimado';
```

## Pendências / recomendações

1. **F1** — escopar descritores derivados de simulação por pesquisa (ou invalidar quando o motor não roda).
2. **F2/F3** — `sim_superficie` não deve ter `default 500`; `sim_dft` deve **recusar** material fora do
   dicionário em vez de devolver `default: 2.0`.
3. **F4/F6** — unificar unidades (`parametro_rede_m`, `diametro_nm`) e exigir unidade explícita.
4. **F5** — mapear saídas de `cfd`→C7 e `cristalografia`→S2, ou não anunciá-las como descritores.
5. **F7** — preencher `faltando` com o motivo da indisponibilidade (`motor universal ausente`).
6. **F8** — instalar CPython 3.10 (ou portar `analises_experimentais`) para liberar os 16 motores do
   backend; obter `modelos_adsorcao_v2.py` e `modelos_analiticos_v2.py` (não existem nesta máquina),
   o que hoje impede `langmuir`/`freundlich` de saírem de `bloqueado_por_parametros`.
7. **F9** — documentar que `ALEF_TAV_CORE` move o diretório de dados.
8. Dados reais que faltam para decidir entre os carvões: **KL** (D2), **PZC** (P2) e isoterma medida
   (D1/D3). Sem isso, "empate" é a única conclusão defensável.

