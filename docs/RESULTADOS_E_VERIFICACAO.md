# Resultados publicados e verificação de reprodutibilidade

Todas as verificações foram executadas em **cópia temporária** do snapshot
(`%TEMP%\alef_verif`), nunca sobre os arquivos publicados. Comando base:

```powershell
$db = (Resolve-Path .\dados_ambiental\ambiental.db).Path.Replace('\','/')
$env:ALEF_TAV_DATABASE_URL = "sqlite:///$db"
```

## 1. Semelhança de cosseno — reproduzido exatamente

`python semelhanca_cosseno.py --json`

| Comparação | Publicado (`semelhanca_cosseno.json`) | Reexecutado em 11/11/2026 | n |
|---|---|---|---|
| A × B (`completo`) | 0,998137 | **0,998137** | 23 |
| A × B (`lastro`) | 0,982615 | **0,982615** | 4 |
| A × B (`perfil`) | 0,999899 | **0,999899** | 6 |
| A × adsorbato (SMX) | 0,791282 | **0,791282** | 3 |
| B × adsorbato (SMX) | 0,794409 | **0,794409** | 3 |

Diferença A−B frente ao adsorbato: 0,794409 − 0,791282 = **0,003127**
(0,0031). Veredito mantido: `empate` — sem D1/D2 medido, nenhum dos dois
materiais pode ser declarado melhor.

## 2. Simuladores e motores — 25/25 reproduzidos

`python rodar_simuladores.py --python310 <caminho-do-python3.10>`

* 25 simuladores executados: **14 `ok`** + **11 `ok_com_aproximacao`**;
* comparação campo a campo com `resultado_simuladores.json`: **24 de 25
  registros idênticos**;
* única diferença: `regeneracao_reuso` passou a devolver também
  `ciclos_ate_80pct_capacidade = 7` (chave **adicional**, mesma informação já
  contida em `ciclos_uteis = 7`). Nenhum valor existente mudou;
* `dft` devolve `bandgap_eV = 2,0` — valor de **referência interna**, não
  cálculo DFT ab initio (o próprio núcleo rotula a saída assim);
* `superficie` devolve `area_m2g = 1262` (eco do dado de entrada).

Os motores de bancada (16) rodaram porque o palco de CPython 3.10 inclui
`_recuperacao/analises_experimentais.cpython-310.pyc`, por exemplo
`pzc_deriva_ph → P2 = 4,444`, `tga_tangente → P5 = 431,2 °C`,
`boehm_grupos → S6 = 0,8 mmol/g`.

## 3. Suíte de testes — 133 casos, 96 aprovados na cópia local

`python -m pytest -q -p no:cacheprovider`

```
96 passed, 37 failed, 3 warnings in 104.44s
```

* **133 casos coletados** (7 arquivos `test_*.py` com 103 funções de teste,
  várias parametrizadas);
* as **37 falhas** são todas `RuntimeError` do *stub*
  `ambiental_backend/analises_experimentais.py`:
  *"esta copia nao contem o bytecode CPython 3.10 do modulo original; o motor
  nao foi executado e nenhum resultado foi inventado"*;
* com o bytecode presente e CPython 3.10, esses motores executam (ver seção 2);
* os testes de API, adsorção (Langmuir/Freundlich), matriz, componentes,
  interface e deduplicação passam na cópia local.

## 4. Matriz KL-KOH — 4 de 4 valores idênticos, 1 descritor a mais

`python comparar_candidatos.py`

| Descritor | Publicado (03–10/11) | Reexecutado | Situação |
|---|---|---|---|
| S3 área BET | A = 1262 m²/g, B = 963 m²/g | idêntico | ✔ |
| S4 volume de poros | A = 0,58 cm³/g, B = 0,49 cm³/g | idêntico | ✔ |
| P6 bandgap (`dft`) | A = B = 2 eV, estado `estimado` | idêntico | ✔ |
| D1 qmax | A = B = 100 mg/g | idêntico | ✔ |
| P1 densidade | ausente (4/28 descritores) | **P1 = 0 g/cm³ (5/28)** | ✖ divergência |

**Causa identificada (defeito de unidade, não de dado).** O registro em
`descritores_simuladores.py` declara `parametro_rede` em **angstrom**, mas a
variante ativa de `universal.sim_cristalografia` ("Bragg + pymatgen") lê o
valor como **metro**: com `parametro_rede = 3,5` ela calcula
`volume_A3 ≈ 4,3 × 10³¹` e devolve `densidade_g_cm3 = 0,0`, que a regra P1
aceita como valor `calculado`. O artefato publicado em 03/11 **não** traz P1,
o que indica que a versão então em uso descartava o zero. Nenhum resultado
publicado foi alterado; a divergência está registrada aqui e na seção de
requisitos e limites conhecidos do `README.md`.

## 5. Estudo de caso SMX — estrutura idêntica, mesma divergência de P1

`python smx_local.py`

| Item | Publicado (10/11) | Reexecutado | Situação |
|---|---|---|---|
| S3 | A = 1262, B = 963 m²/g | idêntico | ✔ |
| D1 | A = B = 100 mg/g, `presente` | idêntico | ✔ |
| compatibilidade | `indeterminado`, faltando `P2 (PZC)` | idêntico | ✔ |
| modelos | Langmuir e Freundlich `bloqueado_por_parametros` | idêntico | ✔ |
| simuladores ok | superficie, cristalografia, cfd, dft | idêntico | ✔ |
| lacunas | S1, P2, D2, D3, D6, D7, C1, C6 | idêntico | ✔ |
| cobertura | 4/28 (14,29 %) | 5/28 (17,86 %) | ✖ por causa de P1 |
| veredito | `empate` | `empate` | ✔ |

## 6. Dossiê da matriz

`dossie_matriz_kl_koh.json` traz, para A e B, os blocos `antes`, `depois`,
`celulas` e `relatorio`, com **23 valores numéricos por material**. O dossiê é
o registro do que a matriz recebeu de caracterização e do que os simuladores
acrescentaram — é a base do número de cobertura usado na dissertação.

## 7. Bancos de dados

| Banco | Tabelas `amb_*` | Conteúdo principal |
|---|---|---|
| `dados_ambiental/ambiental.db` | 20 | 15 pesquisas, 3 materiais, 15 descritores, 90 simulações, 4 viabilidades, 76 propriedades |
| `_qa_matriz/ambiental.db` | 20 | 59 descritores, 52 componentes, 90 simulações, 135 eventos de histórico |

## 8. Citação na dissertação

O pacote passou a ser citado no próprio texto da dissertação, como evidência de
reprodutibilidade e não apenas como endereço externo:

| Item | Onde | Conteúdo |
|---|---|---|
| Citação no texto | seção 3.11.6 — *Rastreabilidade e reprodutibilidade* | `(CARVALHO, 2026)` + URL do repositório + tag `snapshot-2026-11-11` |
| Referência | lista de REFERÊNCIAS, ordem alfabética entre CALUS-MAKOWSKA (2024) e CAZETTA (2011) | entrada ABNT do pacote |

Texto integral dos trechos e arquivo editado: `docs/CITACAO_E_DISSERTACAO.md`.
O documento-fonte da dissertação não é redistribuído neste repositório; apenas
o trecho inserido é transcrito na documentação.

## 9. Verificação pós-publicação (clone do GitHub)

Executada em 11/11/2026 sobre um `git clone` do repositório público, na tag
`snapshot-2026-11-11`, em diretório temporário separado do snapshot:

| Passo | Resultado |
|---|---|
| `git clone --branch snapshot-2026-11-11` | 106 arquivos versionados |
| `verificar_integridade.ps1` | 105 conferem, 0 divergentes, 0 ausentes — **INTEGRIDADE OK** |
| `python semelhanca_cosseno.py --json` | 0,9981 / 0,9826 / 0,9999 / 0,7913 / 0,7944; JSON regerado **byte-idêntico** ao publicado (mesmo SHA-256) |
| `python comparar_candidatos.py` | 27 das 28 linhas da tabela idênticas; única diferença é P1 (publicado `ausente`, regerado `0,0` `calculado`) — a divergência de unidade da seção 4 |

A verificação foi repetida em 13/11/2026, depois da atualização de documentação
e da citação na dissertação, com o mesmo resultado: 106 arquivos, 105 conferem,
JSON regerado byte-idêntico e `git status` limpo após a execução.

Conclusão: o conteúdo publicado no GitHub reproduz o snapshot e reexecuta os
cálculos do estudo de caso sem ajuste manual. Os arquivos de resultado
publicados continuam sendo os originais de 03–10/11/2026.

### Comandos usados

```powershell
git clone --branch snapshot-2026-11-11 https://github.com/carvalhojaderson/alef-tav-dissertacao-reprodutibilidade.git
cd alef-tav-dissertacao-reprodutibilidade
powershell -ExecutionPolicy Bypass -File .\verificar_integridade.ps1
python semelhanca_cosseno.py --json
python comparar_candidatos.py
```

