# ALEF-TAV — reprodutibilidade da dissertação

Material de verificação da versão da plataforma **ALEF-TAV** usada na
dissertação de mestrado: código-fonte dos módulos efetivamente executados,
algoritmos e descritores da matriz 7D×4, scripts de cálculo, dados de entrada,
resultados computacionais, testes e evidências de validação.

O objetivo é permitir que pesquisadores, avaliadores e revisores **confiram os
cálculos** sem depender do ambiente original. Nada aqui foi reimplementado: os
arquivos são cópias fiéis do projeto, com SHA-256 registrado em
`MANIFEST_SHA256.txt`.

> **Não é uma segunda aplicação.** Não há instalação de serviço, banco novo nem
> simulador novo. A API existe apenas como o código que já existia.

## Estado da verificação

| Verificação | Resultado |
|---|---|
| Semelhança de cosseno (`semelhanca_cosseno.py`) | **reproduzido exatamente** (5 de 5 valores) |
| Simuladores (`rodar_simuladores.py`, CPython 3.10) | **25 de 25 executados**, 24 registros idênticos |
| Matriz KL-KOH (`comparar_candidatos.py`) | 4 de 4 valores idênticos; 1 descritor extra (P1 = 0) |
| Estudo de caso SMX (`smx_local.py`) | estrutura e veredito idênticos; mesma divergência de P1 |
| Suíte de testes | 133 casos; 96 aprovados / 37 recusados pelo *stub* do bytecode |
| Varredura de segredos | nenhum arquivo com credencial publicado |
| Citação na dissertação | §3.11.6 + referência ABNT `CARVALHO, 2026` — `docs/CITACAO_E_DISSERTACAO.md` |

Detalhes, comandos e tabelas comparativas: `docs/RESULTADOS_E_VERIFICACAO.md`.

## Estrutura

```
.
├─ README.md                          este arquivo
├─ LICENCA.md                         condições de uso
├─ CITATION.cff                       citação sugerida (Citation File Format)
├─ CITACAO.bib                        citação em BibTeX (pacote + dissertação)
├─ MANIFEST_SHA256.txt                hash de todos os arquivos publicados
├─ verificar_integridade.ps1          confere o manifesto
├─ .gitattributes                     preserva CRLF (bytes idênticos ao original)
├─ requirements.txt                   dependências do backend
├─ requirements-nucleo.txt            dependências do núcleo/Space
├─ Dockerfile                         imagem de referência (python:3.10)
├─ .env.example                       variáveis (sem valores)
├─ universal.py                       113 simuladores (núcleo científico)
├─ modelos_adsorcao_v2.py             Langmuir / Freundlich
├─ modelos_analiticos_v2.py           isotermas analíticas
├─ nucleo_dados.py                    persistência SQLAlchemy
├─ pesquisa_cientifica.py             busca multi-base (não usada offline)
├─ bancos_rest.py, bases_v5.py, conectores_academicos.py
├─ integracoes_reais.py, exportadores.py, doc_export.py
├─ registro_componentes.py, catalogo_registry.py
├─ chaves_config.py, seguranca.py, cache_busca.py
├─ analises_experimentais.py          carregador do bytecode CPython 3.10
├─ ambiental_backend/                 matriz 7D×4, orquestração, motores, API
│   ├─ matriz_7d4.py                  28 descritores
│   ├─ matriz_cruzamentos.py          7 dimensões × 4 componentes
│   ├─ descritores_simuladores.py     mapa descritor → simulador/regra
│   ├─ motores_ambientais.py          16 motores de bancada
│   ├─ motor_pesquisa.py              pergunta → protocolo → resultado
│   ├─ adsorventes.py, componentes.py, medicoes.py
│   ├─ persistencia.py, relatorios.py, tarefas.py, api_ambiental.py, app.py
│   └─ _recuperacao/analises_experimentais.cpython-310.pyc   bytecode original
├─ smx_local.py                       estudo de caso SMX (dois carvões)
├─ comparar_candidatos.py             matriz KL-KOH-1:1 × KL-KOH-2:1
├─ semelhanca_cosseno.py              cosseno entre perfis normalizados
├─ dossie_matriz.py, preencher_matriz.py
├─ rodar_simuladores.py               executa os simuladores no palco 3.10
├─ checar_motores_palco.py, validar_adsorventes.py, validar_integracao.py
├─ conftest.py, test_ambiental_*.py, teste_smx_api.py
├─ resultado_simuladores.json         saída dos simuladores
├─ semelhanca_cosseno.json            saída do cosseno
├─ comparacao_kl_koh.{json,csv,md}    comparação dos dois carvões
├─ dossie_matriz_kl_koh.json          dossiê da matriz
├─ resultado_smx_local*.json          estudo de caso SMX (3 variantes)
├─ logs/                              transcrições das execuções
├─ dados_ambiental/                   banco da plataforma + 4 relatórios
├─ _qa_matriz/ambiental.db            banco de QA da matriz (59 descritores)
└─ docs/                              metodologia, versão, verificação, segurança, citação
```

## Versão identificada

| Âncora | Valor |
|---|---|
| Space de origem | `Jaderson32/alef-tav-backend` |
| Commit base | `7ccec1c9f1ffa101c1b34a8f0015fdcf61db2729` (2026-11-01 21:00 −03) |
| Branch | `checkpoint/diagnostico-20261021` |
| Estado usado | *working tree* com 76 alterações pendentes + cópia de execução de 02–10/11/2026 |
| Snapshot | 2026-11-11 |
| Tag deste repositório | `snapshot-2026-11-11` |

## Como citar

**Na dissertação** o pacote é citado na seção 3.11.6 (*Rastreabilidade e
reprodutibilidade*), como `(CARVALHO, 2026)`, e referenciado em ABNT na lista
final:

```
CARVALHO, J. P. ALEF-TAV: material de reprodutibilidade da dissertação de
mestrado. Versão snapshot-2026-11-11. Curitiba: [s. n.], 2026. Disponível em:
https://github.com/carvalhojaderson/alef-tav-dissertacao-reprodutibilidade.
Acesso em: 13 nov. 2026.
```

**Em trabalhos que usem este material**, use `CITATION.cff` (a página do
repositório mostra o botão *Cite this repository*) ou `CITACAO.bib` (BibTeX):

```
@misc{carvalho2026aleftavreprod,
  author       = {Carvalho, Jáderson de Paula},
  title        = {{ALEF-TAV}: material de reprodutibilidade da dissertação de mestrado},
  year         = {2026},
  version      = {snapshot-2026-11-11},
  howpublished = {GitHub},
  url          = {https://github.com/carvalhojaderson/alef-tav-dissertacao-reprodutibilidade}
}
```

O texto integral dos trechos inseridos na dissertação, com a localização exata
(seção e posição na lista de referências), está em
`docs/CITACAO_E_DISSERTACAO.md`. A identificação do snapshot continua
detalhada em `docs/VERSAO_E_RASTREABILIDADE.md`.

## Como reproduzir

```powershell
# 1) dependências dos scripts de estudo e dos testes
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) banco da plataforma (as rotas leem ALEF_TAV_DATABASE_URL)
$db = (Resolve-Path .\dados_ambiental\ambiental.db).Path.Replace('\','/')
$env:ALEF_TAV_DATABASE_URL = "sqlite:///$db"

# 3) cálculos do estudo de caso
python semelhanca_cosseno.py --json      # -> semelhanca_cosseno.json
python comparar_candidatos.py            # -> comparacao_kl_koh.{json,csv,md}
python smx_local.py                      # -> resultado_smx_local*.json
python dossie_matriz.py                  # -> dossie_matriz_kl_koh.json

# 4) simuladores no palco CPython 3.10 (interpretador 3.10 informado por argumento)
python rodar_simuladores.py --python310 C:\caminho\para\python3.10.exe

# 5) testes
python -m pytest -q -p no:cacheprovider

# 6) integridade do snapshot
powershell -ExecutionPolicy Bypass -File .\verificar_integridade.ps1
```

Os valores esperados de cada passo estão em `docs/RESULTADOS_E_VERIFICACAO.md`.
A reprodução deve ser feita em **cópia** do repositório, para que os arquivos
de resultado publicados permaneçam intactos.

## Requisitos e limites conhecidos da reprodução independente

Itens abaixo são **condições do material**, não tarefas abertas: descrevem o que
é preciso ter para reexecutar os cálculos e o que não é reproduzível fora do
contexto original.

1. **CPython 3.10 é obrigatório** para `analises_experimentais` (bytecode) e para
   o palco dos simuladores. Sem ele, 16 motores de bancada e 37 casos de teste
   terminam em `RuntimeError` explícito — o código se recusa a inventar número.
2. **Rede na primeira execução** de `rodar_simuladores.py`: o script monta o
   palco baixando a roda `cp310` do NumPy (`numpy 2.2.6`). O palco tem ~56 MB e
   por isso não é versionado.
3. **Divergência de um descritor (P1 densidade)** na reexecução de
   `comparar_candidatos.py` e `smx_local.py`: o defeito é de unidade em
   `sim_cristalografia` (`parametro_rede` em metro em vez de angstrom), descrito
   em `docs/RESULTADOS_E_VERIFICACAO.md` §4. Os artefatos originais de 03–10/11
   foram preservados como estavam; nada foi recalculado nem sobrescrito.
4. **Sem versão semântica no projeto de origem**: a identificação é por commit
   base + estado do *working tree* + tag do snapshot, conforme
   `docs/VERSAO_E_RASTREABILIDADE.md`.
5. **Serviços pagos e dados de terceiros** não são redistribuídos; os
   conectores leem chaves do ambiente e ficam desligados nos scripts de estudo.
6. **Dependências opcionais** (RDKit, ASE, pymatgen, OpenMM, scikit-learn) não
   são obrigatórias; sem elas parte dos 113 simuladores reporta
   indisponibilidade.
7. **Durações** (`motor_prazo_s` e afins) variam por máquina e não são
   resultado científico.
8. **Licença**: o material é publicado com permissão expressa para leitura,
   execução e verificação acadêmica, sem licença aberta (`LICENCA.md`). Se o
   autor adotar MIT/CC BY, `LICENCA.md` é o único arquivo a alterar.

