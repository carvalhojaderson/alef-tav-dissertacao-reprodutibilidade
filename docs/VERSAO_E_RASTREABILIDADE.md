# Versão do código e rastreabilidade

## 1. De onde veio cada arquivo

O projeto da dissertação não tinha versionamento por tag nem número de versão
semântica. A identificação é feita por **três âncoras**:

| Âncora | Valor |
|---|---|
| Repositório de origem | Space Hugging Face `Jaderson32/alef-tav-backend` (`https://huggingface.co/spaces/Jaderson32/alef-tav-backend`), clonado em `C:\Users\PC\hf_upload` |
| Commit base | `7ccec1c9f1ffa101c1b34a8f0015fdcf61db2729` — 2026-11-01 21:00:17 −03:00 — branch `checkpoint/diagnostico-20261021` |
| Estado efetivamente executado | *working tree* do mesmo clone com **76 alterações não commitadas** (02–04/11/2026) + cópia de execução `C:\Users\PC\Desktop\Projetos\Nova pasta` (02–10/11/2026) |
| Snapshot publicado | 2026-11-11, hashes em `MANIFEST_SHA256.txt` |

O núcleo científico foi copiado do *working tree* de `hf_upload` (não do
commit), porque as versões usadas nos cálculos de 31/10 a 03/11 estão
justamente nas alterações pendentes (por exemplo `bancos_rest.py` 02/11 15:58,
`pesquisa_cientifica.py` 02/11 16:36, `universal.py` 01/11 20:23).

## 2. Duas cópias do backend e por que uma foi escolhida

Em `Nova pasta` o pacote `ambiental_backend/` (02–03/11) convive com cópias
soltas dos mesmos módulos na raiz (02–03/11). As duas árvores **não são
idênticas**:

| Arquivo | Pacote (`ambiental_backend/`) | Cópia da raiz | Situação publicada |
|---|---|---|---|
| `api_ambiental.py`, `app.py`, `config.py`, `matriz_7d4.py`, `matriz_cruzamentos.py`, `persistencia.py`, `relatorios.py`, `medicoes.py`, `componentes.py`, `descritores_simuladores.py`, `adaptadores.py`, `luna.py`, `tarefas.py`, `preparar_espaco.py`, `persistencia_remota.py`, `adsorventes.py` | idênticos | idênticos (ou ausentes) | pacote |
| `motor_pesquisa.py` | 92 456 B (com `memoria=` em `registrar_valor_medido`) | 92 458 B, **sem** `memoria=` | pacote (mais completo) |
| `motores_ambientais.py` | 30 273 B | 29 958 B | pacote |
| `analises_experimentais.py` | *stub* de 1 865 B | carregador de 3 722 B | **os dois**: stub no pacote, carregador na raiz |

Critério: publicar a árvore que contém a superfície completa de API e de
regras (o pacote) e manter o carregador do bytecode na raiz, onde
`rodar_simuladores.py` o procura. Nenhum arquivo foi editado; a comparação é
por SHA-256 no manifesto.

## 3. Resultados e datas de produção

| Artefato | Data/hora | Origem |
|---|---|---|
| `dossie_matriz_kl_koh.json` | 10/11/2026 00:40 | `dossie_matriz.py` |
| `semelhanca_cosseno.json` | 10/11/2026 00:53 | `semelhanca_cosseno.py --json` |
| `comparacao_kl_koh.{json,csv,md}` | 10/11/2026 00:57 | `comparar_candidatos.py` |
| `resultado_simuladores.json` | 10/11/2026 01:18 | `rodar_simuladores.py` (palco CPython 3.10) |
| `resultado_smx_local*.json` + `logs/` | 09–10/11/2026 | `smx_local.py` (com e sem núcleo) |
| `dados_ambiental/ambiental.db` | 10/11/2026 00:26 | banco da plataforma (20 tabelas `amb_*`) |
| `_qa_matriz/ambiental.db` | 10/11/2026 00:40 | banco de QA da matriz (59 descritores, 52 componentes) |


## 4. O que **não** foi publicado (e por quê)

| Item | Motivo |
|---|---|
| `.env` do Space | contém chaves reais (`DEEPSEEK_API_KEY`, `HUGGINGFACE_API_KEY`, entre outras) |
| Scripts de rascunho da raiz de `hf_upload` com `SENHA = "..."`/`TOKEN = "..."` gravados no código | credenciais embutidas; não fazem parte do cálculo da dissertação |
| `_palco310/` (≈56 MB) | ambiente Python 3.10 pré-montado (interpretador + numpy + wheels); é **regenerado** por `rodar_simuladores.py` |
| `__pycache__/`, `.pytest_cache/`, `_qa_sim_dados/` (vazia), `Novo(a) Documento do Microsoft Word.docx` (0 B) | artefatos de execução / vazios |
| Bases pagas e dados de terceiros | não são redistribuíveis; o código lê as chaves do ambiente |
| Texto da dissertação, DOCX e PDF | não fazem parte do escopo científico deste repositório |

## 5. Requisitos de ambiente

| Componente | Versão | Observação |
|---|---|---|
| Python | 3.13 (scripts, API, testes) | foi o interpretador das execuções de 10/11 |
| CPython 3.10 | 3.10.x | **obrigatório** para o bytecode de `analises_experimentais` e para o palco dos simuladores |
| NumPy | 2.x | `rodar_simuladores.py` baixa a roda `cp310` do NumPy 2.2.6 para o palco (exige rede na primeira execução) |
| SQLite | via SQLAlchemy 2.x | bancos incluídos em `dados_ambiental/` e `_qa_matriz/` |
| SO de referência | Windows 10/11 | os caminhos são relativos ao diretório do repositório |

## 6. Limitações conhecidas da reprodução

1. **Bytecode obrigatório**: sem CPython 3.10, os 16 motores de bancada e as
   rotas de medição falham com `RuntimeError` explícito (37 casos de teste).
2. **Redes**: os conectores científicos (`pesquisa_cientifica.py`,
   `bancos_rest.py`) dependem de serviços externos e de chaves; os cálculos
   reproduzíveis aqui **não** dependem deles (as bases são desligadas nos
   scripts com `AMBIENTAL_BACKUP_REPO=""` e `HF_TOKEN=""`).
3. **Simuladores opcionais**: RDKit, ASE, pymatgen, OpenMM e scikit-learn não
   são dependências obrigatórias; sem eles, parte dos 113 simuladores reporta
   indisponibilidade em vez de resultado.
4. **Valores dependentes de tempo**: campos como `motor_prazo_s` medem
   duração de execução e variam entre máquinas; não são resultados científicos.
5. **Divergência de um descritor** na reexecução de `comparar_candidatos.py`
   (P1 = 0 g/cm³) — ver `docs/RESULTADOS_E_VERIFICACAO.md`, seção 4.
