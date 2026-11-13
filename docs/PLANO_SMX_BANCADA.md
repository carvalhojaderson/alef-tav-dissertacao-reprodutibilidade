# Plano de execucao — SMX nos carvoes KL-KOH (matriz 7Dx4)

Pesquisa: `pesq_63b32e62389dae7c` — "Comparacao de KL-KOH-1:1 e KL-KOH-2:1 na
adsorcao de sulfametoxazol". Condicoes gravadas: `pH 5.5`, `25 C`
(`amb_pesquisas.condicoes_json`). Fonte declarada dos dados: Brazil et al., 2026.

Materiais (IDs reais no banco):

| rotulo | material_id | nome |
|---|---|---|
| A | `mat_ca84ac210575584a` | KL-KOH-1:1 |
| B | `mat_358eb4207c9fb795` | KL-KOH-2:1 |
| (nao usar) | `mat_4dd5ed09f7fa7c93` | KL-KOH-1:1-fresh — residuo de QA |

Base local: `http://127.0.0.1:7860` (`python -m uvicorn ambiental_backend.app:app
--host 0.0.0.0 --port 7860`).

Todo payload deste plano foi conferido contra os modelos Pydantic de
`ambiental_backend/api_ambiental.py` e contra as regras de
`ambiental_backend/matriz_7d4.py`. Nenhum valor de literatura foi inventado:
o que nao tem fonte esta marcado **nao reportado**.

Artefatos desta rodada (nesta pasta):

| arquivo | o que e' |
|---|---|
| `rodar_simuladores.py` | executa os 25 simuladores nos motores reais (palco CPython 3.10) e, com `--gravar`, prova a gravacao numa copia do banco |
| `resultado_simuladores.json` | saida bruta dos 25 (estado, resultado, descritores, avisos) |
| `dossie_matriz.py` | as 28 celulas: de onde sai cada valor e qual o lastro (nivel 1–4) |
| `preencher_matriz.py` | executa o dossie (motores no palco 3.10 + regras + componentes) e grava com `--gravar`/`--gravar-real` |
| `dossie_matriz_kl_koh.json` | as 28 celulas de A e B ja montadas, com valor, estado, memoria e nivel |
| `semelhanca_cosseno.py` | cosseno entre materiais e entre material e adsorbato (7 eixos) |
| `semelhanca_cosseno.json` | vetores normalizados + cossenos + ranking de delta |
| `checar_motores_palco.py` | roda `test_ambiental_motores.py` **com o motor real** dentro do palco 3.10 (42/42) |
| `PLANO_SMX_BANCADA.md` | este plano |

---

## 0. Estado verificado no banco (nao o aparente)

| material | descritor | valor | unidade | estado | fonte gravada |
|---|---|---|---|---|---|
| A | S3 | 1262.0 | m2/g | presente | `universal.sim_superficie` (eco do parametro — F2) |
| A | S4 | 0.58 | cm3/g | presente | Brazil et al., 2026 |
| A | D1 | 100.0 | mg/g | presente | Brazil et al., 2026 (hipotese identica para A e B) |
| A | P6 | 2.0 | eV | **estimado** | `universal.sim_dft` — default do motor (F3) |
| A | S2, C7 | None | — | ausente | — |
| B | S3 | 963.0 | m2/g | presente | `universal.sim_superficie` (eco — F2) |
| B | S4 | 0.49 | cm3/g | presente | Brazil et al., 2026 |
| B | D1 | 100.0 | mg/g | presente | Brazil et al., 2026 |
| B | P6 | 2.0 | eV | **estimado** | `universal.sim_dft` |
| B | S2, C7 | None | — | ausente | — |

Lacunas criticas calculadas pelo proprio backend (`adsorventes._lacunas`):
**S1, P2, D2, D3, D6, D7, C1, C6**. Cobertura 4/28 nos dois materiais
(`empate_cobertura: true`). Langmuir e Freundlich `bloqueado_por_parametros`;
compatibilidade `indeterminado` por falta de P2 (PZC).

Consequencia para a dissertacao: o empate **nao e um empate de desempenho** — e
um empate de cobertura. O que existe mede tamanho de superficie/poro (S3, S4);
o que decide adsorcao de SMX (D2, D3, D6, P2) esta ausente nos dois materiais.

---

## 1. Tabela 1 — Ensaios de bancada (adsorventes)

### 1.1 Fecha o empate (ordem de execucao recomendada)

| # | Descritor | Ensaio | Metodo / norma | Unidade e faixa fisica esperada | Tempo | Custo | Como enviar (rota + payload) |
|---|---|---|---|---|---|---|---|
| 1 | **P2** | PZC por deriva de pH | 11 frascos, 0,01 mol/L NaCl, pH inicial 2–12 (HCl/NaOH), 0,05 g de carvao, 24 h, 25 C, agitacao 150 rpm; PZC = patamar de pH final vs inicial (metodo classico de deriva de pH; alternativa: titulacao de massa) | pH (2–12). Carvao ativado tipico: **6–10** | 2 dias | **baixo** | `POST /api/materials/{A}/components/adsorvente` chave `pzc` — ver 4.1 |
| 2 | **D1 + D2** | Isoterma de equilibrio | Batelada: 6–8 pontos de C0 (1 a 100 mg/L), dose 0,5–1,0 g/L, 25 C, 150 rpm, 48–72 h (tempo definido pelo ensaio 3); quantificar SMX por UV (λ ≈ 257 nm) ou HPLC-DAD; qe = (C0−Ce)·V/m; ajuste de Langmuir e Freundlich | qmax **mg/g** (10–400); KL **L/mg** (0,01–5); Kf e n (adimensional) | 7–10 dias | **medio** | `POST /api/research/{pesq}/adsorbent` com `calculo.D1.pontos` — ver 4.2 (grava D1 **e** D2 na mesma chamada) |
| 3 | **D3** | Cinetica de adsorcao | Batelada unica (C0 fixo, dose fixa), 8–12 amostragens entre 1 min e 48 h; ajuste PSO (t/qt vs t) — a regra do backend exige >= 3 pontos positivos | k2 **g/(mg·min)**; qe **mg/g**; t95 **min** | 3–5 dias | **medio** | mesmo corpo de 4.2, campo `calculo.D3.pontos_cinetica` (ou `POST /api/materials/{A}/descriptors` com `{"calculo":{"D3":{...}}}`) |
| 4 | **D6** | Eficiencia de remocao | Nao e ensaio novo: usa C0, Ce, V e m do ensaio 2 (um ponto qualquer da isoterma serve) | **%** (0–100) e qe **mg/g** | ~0 (deriva do ensaio 2) | **baixo** | mesmo corpo de 4.2: `calculo.D6 = {C0, Ce, volume_L, massa_g}` |
| 5 | **S5** | Tamanho de particula | Difracao a laser (ISO 13320) em dispersao aquosa, ou MEV + contagem de >= 200 particulas | **nm** (backend aceita 0,5 a 1e7 nm). Carvao moido: 1–100 µm | 1 dia | **medio** | `POST /api/research/{pesq}/adsorbent` com `caracterizacao: {"diametro_particula": {"valor": .., "unidade": "um"}}` |
| 6 | **S1** | Composicao elementar | CHNS (ASTM D5373) + XRF para cinzas/heteroatomos; reportar em fracao massica | **fracao m/m 0–1** (% m/m) | 5–10 dias | **medio** | `POST /api/research/{pesq}/adsorbent` com `composicao: [{"elemento","fracao_massica"}]` — unico caminho que grava S1 nesta copia (ver aviso 5.2) |
| 7 | **C1** | Toxicidade e seguranca | Documental: FISPQ/GHS do material e do residuo pos-uso (frases H) + LC50/EC50 de literatura quando existir | categoria **GHS** (texto) e **mg/L** | 1 dia | **baixo** | `POST /api/research/{pesq}/adsorbent` com `caracterizacao.toxicidade` (texto) ou `caracterizacao.lc50` (mg/L) |

Ordem justificada: **P2** primeiro porque e o ensaio mais barato e o unico que
destrava a compatibilidade (regra `pH x PZC`, `adsorventes.compatibilidade`);
**D1+D2** depois porque e o unico par que separa afinidade de capacidade — sem
KL os dois carvoes continuam com qmax identico (100 mg/g) e a matriz nao
discrimina; **D3** e **D6** vem em seguida porque saem quase de graca do mesmo
ensaio de batelada; S5, S1 e C1 sao preenchimento de dimensao, nao de decisao.


### 1.2 Menor urgencia (preenchem dimensao, nao mudam o veredito A vs B)

| # | Descritor | Ensaio | Metodo / norma | Unidade e faixa esperada | Tempo | Custo | Como enviar |
|---|---|---|---|---|---|---|---|
| 8 | P1 | Densidade real e aparente | Picnometria de helio (real) + densidade de leito empacotado (aparente). A regra `_regra_p1` pede apenas `massa_g` e `volume_cm3` | g/cm3 — carvao ativado 0,3–0,9 (aparente), 1,8–2,2 (real) | 1–2 dias | medio | `calculo.P1 = {"massa_g": .., "volume_cm3": ..}` |
| 9 | P3 | CTC | Saturacao com acetato de amonio (ISO 11260) — ou `_regra_p3` a partir dos volumes de branco/amostra | **cmol/kg** (50–500). Na rota de componentes vai como `cmol/kg`; na rota de medicoes (bloqueada) a unidade seria `mmolc/kg` | 2–3 dias | baixo | `POST /api/research/{pesq}/adsorbent` `caracterizacao.ctc` (cmol/kg) |
| 10 | P4 | Hidrofobicidade | Angulo de contato, gota sessil, 3 gotas por amostra, agua Milli-Q | **graus** 0–180 (carvao ativado 60–120) | 1 dia | medio | `caracterizacao.angulo_de_contato` (graus), via `/adsorbent` |
| 11 | P5 | Estabilidade termica | TGA 25–900 C, 10 C/min, N2 (ASTM E1131, metodo da tangente) | **C** 20–1200 | 1 dia | medio | `caracterizacao.estabilidade_termica` (C), via `/adsorbent` |
| 12 | S6 | Grupos funcionais / acidez | Titulacao de Boehm (NaOH, Na2CO3, NaHCO3, HCl 0,05 mol/L) + FTIR-ATR | **mmol/g** 0,001–20; ou texto de bandas | 3–5 dias | baixo-medio | `caracterizacao.grupos_funcionais` (texto) ou componente `adsorvente/densidade_sitios` (mmol/g) |
| 13 | D5 | Regeneracao | 5 ciclos adsorcao/dessorcao (etanol ou NaOH 0,1 mol/L), eficiencia por ciclo | **%** 0–100 | 2–3 semanas | alto | `caracterizacao.regeneracao` (%), via `/adsorbent` |
| 14 | P7 | Lixiviacao / solubilidade | ABNT NBR 10005 (extrato solubilizado), resultado em mg/L | **mg/L** 0–1e5 | 28 dias | alto | `caracterizacao.lixiviacao` (mg/L), via `/adsorbent` |
| 15 | C2 | Custo especifico | Cotacao do preco do carvao (R$/kg) + D1 ja calculado | **R$/g removido** | 1 dia | baixo | `calculo.C2 = {"preco_kg": .., "qmax_mg_g": ..}` (so depois de D1) |
| 16 | C3 | Disponibilidade do residuo | Documental: t/ano de lignina Kraft disponivel (fornecedor/ABTCP) | **t/ano** | 1–2 dias | baixo | `caracterizacao.disponibilidade` |
| 17 | C4 | Pegada energetica | Balanco do processo de ativacao (P x t / massa) — dado de projeto | **kWh/kg** | 2–3 dias | baixo | `calculo.C4 = {"potencia_kW","tempo_h","massa_kg"}` |
| 18 | C6 | Conformidade normativa | Comparar Ce com limite. **Nao existe limite de SMX na legislacao brasileira** (CONAMA 357/430 nao lista sulfametoxazol): usar PNEC/valor proposto e declarar a fonte | **mg/L** e status | 1 dia | baixo | `caracterizacao.conformidade` (mg/L), via `/adsorbent` |
| 19 | C7 | Escalabilidade | Coluna de leito fixo: volume de leito e vazao para obter TRH; ou curva de ruptura | **min** (TRH) e m3/h | 1–2 semanas | alto | `calculo.C7 = {"volume_leito_m3","vazao_m3_h"}` |
| 20 | D4 | Seletividade | Ensaio competitivo SMX + interferente (outro antibiotico ou materia organica) | **adimensional** | 1–2 semanas | alto | `caracterizacao.seletividade` |
| 21 | D7 | Faixa operacional de pH | Isotermas curtas em pH 3, 5, 7, 9 (mesmo C0) | **pH** e **C** | 1–2 semanas | medio | `caracterizacao.faixa_de_ph` / `ph_otimo` |

> Nenhum destes 14 itens muda a conclusao "A vs B". Eles aumentam cobertura e
> sustentam os capitulos de viabilidade (C2/C4/C7) e de destino (P7/C6).

### 1.3 Quem calcula o descritor depois do ensaio (ponte com a tabela 2.1)

Varios ensaios desta tabela nao gravam o descritor direto: o valor bruto entra no
simulador correspondente, que devolve o descritor com `metodo`, `nivel_validacao`
e `limitacoes`. Rode **depois** do ensaio, com o dado real:

| ensaio (§1) | simulador | chave de entrada | descritor gravado |
|---|---|---|---|
| 1 PZC por deriva de pH | `pzc_deriva_ph` | `ph_inicial[]`, `ph_final[]` | P2 (`calculado`) |
| 1 alternativo (titulacao de massa) | `pzc_titulacao_massa` | `massa_g_L[]`, `ph_equilibrio[]` | P2 |
| 6 composicao elementar | `composicao_elementar` | `elementos_pct`, **`elementos_principais`** | S1 (sem `elementos_principais`, nao grava — 2.4) |
| 10 angulo de contato | `angulo_contato` | `angulo_agua_deg` **+** `angulo_diiodometano_deg` | P4 (OWRK); so com agua, nao grava |
| 11 TGA | `tga_tangente` | `temperatura_C[]`, `massa_pct[]` | P5 (onset) + umidade/residuo em apoio |
| 12 Boehm | `boehm_grupos` | consumos NaOH/Na2CO3/NaHCO3/HCl | S6 (acidos totais) + 4 fracoes em apoio |
| 13 regeneracao | `regeneracao_reuso` | `capacidades_mg_g[]`, `dessorcao_pct` | **D5 nao grava hoje** (bug 2.4 item 3) — usar `/descriptors` |
| 14 lixiviacao (NBR 10005) | `lixiviacao_cinetica` | `tempo_s[]`, `fracao_lixiviada[]` | P7 (nao rodar `solubilidade_imersao` junto) |
| 18 conformidade | `conformidade_limites` | `analitos{}`, **`limites{}`** | C6 (margem %); sem `limites`, nao grava |
| 20 seletividade | `seletividade_competitiva` | `componentes[]` (nome, qmax, KL), `concentracoes_mg_L[]` | D4 (exige D1/D2 dos dois contaminantes) |
| PSD/granulometria (nao listado) | `granulometria_psd` | `diametros_um[]` | S7 (d50) |

Payload pronto para cada um: `PARAMETROS` em `rodar_simuladores.py` (trocar os
valores de ensaio tipico pelos medidos) ou
`POST /api/simulators/{nome}/run` quando a API estiver em Python 3.10 (§2.2).

---

## 2. Tabela 2 — Simulacoes

**Metodo:** `rodar_simuladores.py` (script nesta pasta) monta um palco CPython
3.10 isolado, carrega o bytecode original de `analises_experimentais` e executa
os 25 simuladores de `descritores_simuladores.SIMULADORES` com todos os
requisitos obrigatorios preenchidos. Saida bruta em `resultado_simuladores.json`.

Foram duas rodadas, e a diferenca entre elas e' so o interpretador:

| rodada | Python | `analises_experimentais` | `universal.py` | executaram |
|---|---|---|---|---|
| 1 — API local (porta 7860) | 3.13 | stub (`RuntimeError`) | sem numpy -> `indisponivel` | **0/25** |
| 2 — `rodar_simuladores.py` | 3.10 + `.pyc` 3.10 + numpy cp310 | original recuperado | carregado (113 simuladores) | **25/25** |

Conclusao da rodada 2: **nenhum simulador esta bloqueado por falta de motor** —
o que faltava era o interpretador certo. O que continua valendo e' a pergunta
cientifica: dos 25, **11 entregam valor defensavel** (9 descritores distintos,
porque P2 e P7 tem dois motores cada) e **14 nao devem entrar na matriz** — seja
porque devolvem o proprio parametro, um default do motor, apenas apoio, ou por
bug de mapeamento. Todos os 11 exigem ensaio como entrada (§1).

### 2.1 Resultado real, simulador por simulador

Valores da coluna "grava" sao os de `resultado_simuladores.json`, obtidos com as
entradas de ensaio tipico declaradas em `PARAMETROS` do script — **nao** sao dado
do KL-KOH. "apoio" = dado de suporte gravado em `dados_json.apoio` (nao substitui
o valor do descritor).

| Simulador | Estado | Grava (modo valor) | Apoio | Veredito para a matriz |
|---|---|---|---|---|
| `pzc_deriva_ph` | `ok` | **P2 = 4,444 pH** | — | **USAR** — e' o ensaio 1 do §1.1 (11 frascos, pH 2–12) |
| `pzc_titulacao_massa` | `ok` | **P2 = 7,8 pH** | — | alternativa ao anterior; so vale com patamar atingido (`plato_atingido: false` no teste) |
| `boehm_grupos` | `ok_com_aproximacao` | **S6 = 0,8 mmol/g** (acidos totais) | 4 (carboxilicas 0,3 / lactonas 0,2 / fenolicas 0,3 / basicos 0,2) | **USAR** com titulacao de Boehm |
| `tga_tangente` | `ok_com_aproximacao` | **P5 = 431,2 C** (onset) | 2 (umidade 8%, residuo 30%) | **USAR** com TGA (ASTM E1131) |
| `granulometria_psd` | `ok_com_aproximacao` | **S7 = 7,5 um** (d50) | 1 (span) | **USAR** com PSD (laser ou imagem) |
| `lixiviacao_cinetica` | `ok_com_aproximacao` | **P7 = 30 %** | 1 (modelo difusao em camada de produto, r2 0,969) | **USAR** (escolher entre ele e `solubilidade_imersao` — ver 2.4) |
| `solubilidade_imersao` | `ok` | **P7 = 3 %** | — | alternativa ao anterior; mesmo descritor, ultimo grava |
| `conformidade_limites` | `ok_com_aproximacao` | **C6 = 85,6 %** (margem) | 1 (status por analito) | **USAR** declarando `limites` (SMX nao tem limite legal — ver 2.4) |
| `composicao_elementar` | `ok_com_aproximacao` | **S1 = 100 %** (pureza) | 1 (formula empirica) | **USAR** com `elementos_principais`; sem essa lista `pureza_pct` sai `null` e nada e' gravado |
| `angulo_contato` | `ok_com_aproximacao` | **P4 = 28,59 mN/m** | — | **USAR** so com os dois liquidos (agua **e** diiodometano); com um so, `energia_superficial_mN_m` = `null` |
| `seletividade_competitiva` | `ok` | **D4 = 2,7853** | 1 (q por componente) | **USAR** depois de D1/D2 medidos para SMX **e** para o competidor |
| `nano` | `ok` | S5 = 45 nm (`presente`) | 1 (area relativa 6/d = 0,133 1/nm) | **SO DEPOIS** de S5 medido: o numero gravado e' o parametro informado, nao calculo (F2/F6) |
| `dft` | `ok` | P6 = 2,0 eV (`estimado`) | — | **NAO USAR**: tabela interna de referencia ("nao DFT"), igual para qualquer carbono (F3) |
| `superficie` | `ok` | S3 = 1262 m2/g (`presente`) | — | **NAO RODAR**: devolve o proprio parametro e reescreve a fonte (F2) |
| `cristalografia` | `ok` | — | 1 (S2 d = 1,54 A) | **NAO USAR**: P1 nao sai (`motor_falhou: pymatgen` ausente); S2 real vem de DRX |
| `cfd` | `ok` | — | 1 (C7 Reynolds 49,85) | **NAO USAR**: C7 e' TRH de coluna, nao Reynolds (F5) |
| `fluido` | `ok_com_aproximacao` | — | 1 (C7 Reynolds) | **NAO USAR**: duplica `cfd` sem dado de coluna |
| `poluicao` | `ok` | — | 1 (D6 C_final 0,0496 mg/L) | **NAO USAR**: decaimento de 1a ordem com `k` inventado nao e' remocao por adsorcao |
| `equilibrio` | `ok` | — | 1 (D7 K = 7,52) | **NAO USAR**: D7 da matriz e' janela operacional, nao constante termodinamica |
| `hidro` | `ok` | — | — | **NAO USAR**: motor de bacia (`motor_falhou: wntr`), nenhum descritor |
| `perigo_composicao` | `ok` | C1 = 0,04 (0–4) | 1 | **NAO USAR**: cobertura avaliada = **2,4 %** (carbono fora da tabela GHS); o indice 0,04 so reflete o Zn |
| `reciclabilidade` | `ok_com_aproximacao` | C5 = 0,0 (0–1) | 1 | **NAO USAR**: as classes informadas nao estao em `FATORES_RECICLABILIDADE`, entao `classes_avaliadas = []` e o indice cai para 0 — numero falso |
| `regeneracao_reuso` | `ok` | — | 1 (eficiencia 80 %) | **BLOQUEADO POR BUG**: ver 2.4 (chave `ciclos_ate_80pct_capacidade` nao e' exposta) |
| `fractal_agregacao` | `ok_com_aproximacao` | — | 1 (S7 Df 2,485) | apoio de S7 — util no texto, nao preenche celula |
| `ftir_grupos` | `ok_com_aproximacao` | — | — | nada gravavel: S6 `grupos` e' texto de apoio; FTIR entra como figura, nao descritor |

Resumo: **11 dos 25** entregam valor defensavel — `pzc_deriva_ph` e
`pzc_titulacao_massa` (P2), `boehm_grupos` (S6), `tga_tangente` (P5),
`granulometria_psd` (S7), `lixiviacao_cinetica` e `solubilidade_imersao` (P7),
`conformidade_limites` (C6), `composicao_elementar` (S1), `angulo_contato` (P4) e
`seletividade_competitiva` (D4). Como P2 e P7 tem dois motores cada, isso da
**9 descritores** distintos. Os outros 14 nao entram na matriz: `nano` so depois de
S5 medido (o valor e' eco), `dft`/`superficie` repetem default ou parametro,
`cfd`/`fluido`/`poluicao`/`equilibrio`/`cristalografia`/`hidro`/`fractal_agregacao`/
`ftir_grupos` produzem apenas apoio (ou falham no motor externo), e
`perigo_composicao`/`reciclabilidade`/`regeneracao_reuso` tem numero enganoso
(2.4). **Nenhum substitui ensaio**: todos exigem o dado experimental como entrada.


### 2.2 Como rodar os 25 (script desta pasta)

```powershell
# 1) roda os 25 e imprime a tabela (monta o palco 3.10 na primeira vez)
python rodar_simuladores.py

# 2) roda e ainda prova a gravacao numa COPIA do banco (nao toca no original)
python rodar_simuladores.py --gravar

# 3) limpar palco e copia
python rodar_simuladores.py --limpar
```

O que o script faz, e por que cada peca e' necessaria:

| peca | de onde vem | por que |
|---|---|---|
| palco `_palco310/ambiental_backend` | copia do pacote, sem `__pycache__` | rodar o motor real sem alterar o pacote da API |
| `analises_experimentais.py` | `ALEF_TAV_CORE/ambiental_backend` ou `analises_experimentais.pycshim` | e' o carregador que executa o bytecode original |
| `_recuperacao/analises_experimentais.cpython-310.pyc` | copia do nucleo cientifico | **o codigo do modulo so existe como bytecode 3.10** |
| `numpy` cp310 | baixado do PyPI (`--python-version 310`) | `universal.py` importa numpy; o numpy do ambiente e' cp313 |
| CPython 3.10 | `ALEF_PYTHON310`, `--python310` ou varredura local | 3.12/3.13 recusam o `.pyc` (`magic 3439`) |

Se a maquina nao tiver 3.10 nem o `.pyc`, os 16 motores experimentais voltam a
`indisponivel` e a unica via continua sendo `components`/`descriptors`/
`adsorbent` (aviso 5.1).

### 2.3 Prova de gravacao — cobertura 4/28 -> 16/28 (em copia)

`python rodar_simuladores.py --gravar` aplica **todas** as saidas dos 25 em
`_qa_sim_dados/ambiental.db` (copia) via `adsorventes.aplicar_descritores`, que
e' a mesma funcao chamada por `motor_pesquisa.executar_simulacao`. Resultado
observado:

| material | cobertura antes | cobertura depois |
|---|---|---|
| A `mat_ca84ac210575584a` | 4/28 (14,29%) | **16/28 (57,14%)** |
| B `mat_358eb4207c9fb795` | 4/28 (14,29%) | **16/28 (57,14%)** |

Valores gravados na prova: `C1=0,04`, `C5=0,0`, `C6=85,6`, `D1=100`, `D4=2,7853`,
`P2=7,8`, `P4=28,59`, `P5=431,2`, `P6=2,0`, `P7=3,0`, `S1=100`, `S3=1262/963`,
`S4=0,58/0,49`, `S5=45`, `S6=0,8`, `S7=7,5`.

> **Isto e' prova de caminho, nao resultado.** As entradas foram valores de ensaio
> tipico; `C1`, `C5`, `P6`, `S3` e `S5` entraram justamente para mostrar que o
> sistema aceita numero sem lastro experimental e o exibe como `calculado`/
> `presente`. Na dissertacao, **so** entram os descritores da coluna "USAR" da
> tabela 2.1, e cada um com o ensaio do §1 feito.

### 2.4 Armadilhas medidas nos simuladores (nao teoricas)

1. **P7 tem duas fontes que se sobrescrevem.** `lixiviacao_cinetica` grava 30 %
   (fracao maxima lixiviada) e `solubilidade_imersao` grava 3 % (perda de massa)
   no mesmo `P7`. Rodar os dois em sequencia deixa o **ultimo** — na prova acima o
   P7 final foi 3 %. Escolher um e declarar no `metodo`.
2. **P2 tambem.** `pzc_titulacao_massa` (7,8) sobrescreveu `pzc_deriva_ph`
   (4,444). O bom e' usar **deriva de pH** (§1.1 ensaio 1) e nao rodar o outro.
3. **`regeneracao_reuso` nunca grava D5.** O motor calcula
   `ciclos_ate_80pct_capacidade = 7`, mas `descritores_de` procura essa chave no
   nivel de fora do resultado, onde `motores_ambientais._empacotar` publica
   `ciclos_uteis`. Efeito: aviso `saida 'ciclos_ate_80pct_capacidade' ausente` e
   D5 fica so com apoio. Correcao minima (uma linha, em
   `motores_ambientais.regeneracao_reuso`): acrescentar
   `"ciclos_ate_80pct_capacidade": analise["resultado"]["ciclos_ate_80pct_capacidade"]`
   ao dicionario de extras. Ate la, D5 entra por
   `POST /api/materials/{id}/descriptors` com `valores.D5` e `fonte` declarada.
4. **`composicao_elementar` sem `elementos_principais` nao grava S1**:
   `pureza_pct` sai `null` e o descritor e' descartado com aviso. Com a lista
   `["C","H","N","S"]` ele grava `S1 = 100 %` — que e', literalmente, "a soma dos
   elementos declarados", nao pureza medida por terceiro.
5. **`conformidade_limites` so grava C6 se o limite existir.** SMX nao esta na
   Portaria GM/MS 888/2021: sem `limites`, o resultado e' `nao_avaliado` e
   `margem_conformidade_pct = null` (nada gravado). Com
   `"limites": {"sulfametoxazol": 0.05}` ele grava `C6 = 85,6 %`. Declarar na
   dissertacao que esse 0,05 mg/L e' **valor de referencia proprio (PNEC)** — nao
   limite legal brasileiro.
6. **`angulo_contato` precisa de dois liquidos.** So com agua,
   `energia_superficial_mN_m` volta `null` e P4 nao entra (aviso "saida nao e'
   numerica"). Com agua + diiodometano, `P4 = 28,59 mN/m` (OWRK), polaridade 5,5 %.
7. **`reciclabilidade` grava C5 = 0 quando a classe nao esta na tabela.** O codigo
   nao erra: registra `classes_nao_avaliadas` e devolve indice 0. Zero aqui
   significa "nada avaliado", nao "material nao reciclavel" — nao usar.
8. **`perigo_composicao` devolve C1 com cobertura declarada.** No teste, 2,4 % de
   cobertura (so o Zn tem entrada GHS) e indice 0,04. Se o C1 for para a matriz,
   levar junto `cobertura_avaliada_pct` e a lista `nao_avaliados`.
9. **`cristalografia` e `hidro` falham no motor externo** (`pymatgen` e `wntr`
   ausentes) e devolvem `motor_situacao` com o erro; nenhum descritor e' gravado.
   Nao instalar dependencia so para preencher P1/C3 — o dado vem de DRX/ensaio.
10. **`superficie` e `nano` sao eco.** `S3` volta igual ao parametro e a fonte e'
    reescrita para `universal.sim_superficie`, apagando "Brazil et al., 2026";
    `S5` idem (`presente`), e o unico calculo real e' `6/d` em modo apoio.


---

## 3. Tabela 3 — Parametros do sulfametoxazol (SMX)

Valores conferidos hoje no PubChem (CID 5329), que agrega HSDB (peer reviewed)
e DrugBank. A fonte de cada linha esta na coluna propria — os que nao tem fonte
confiavel estao marcados **nao reportado** e **nao devem ser gravados**.

| Parametro | Unidade | Valor | Fonte | Onde enviar no backend | O que destrava |
|---|---|---|---|---|---|
| Formula molecular | texto | C10H11N3O3S | PubChem CID 5329 (InChI) | `POST /api/materials/{A}/components/adsorbato` chave `formula_molecular` | identificacao; S1/D3 nao dependem dela |
| Massa molar | g/mol | **253,28** | PubChem, "Molecular Weight" (calculado da formula) | componente `adsorbato` chave `massa_molar` | converte mg/L em mol/L; calculo de carga molar |
| pKa1 | adimensional | **1,6** (faixas publicadas 1,6–1,8) | HSDB/PubMed **Boreen et al. (2004)**, *Environ Sci Technol* 38:3933-40 (via PubChem) — peer reviewed | componente `adsorbato` chave `pka` **ou** texto em `referencia` do item | define a especie cationica abaixo de pH 1,6 (irrelevante em pH 5,5) |
| pKa2 | adimensional | **5,7** (faixas publicadas 5,5–5,7) | mesma referencia acima | **chave `pka` = 5.7** (o catalogo tem um unico slot de pKa: usar o que governa o pH de trabalho) | **define a especie predominante em pH 5,5** — ver aviso 5.4 |
| log Kow | adimensional | **0,89** (experimental); XLogP3 = 0,9 | HSDB/Hansch, Leo & Hoekman (1995) p.71; XLogP3 3.0 (PubChem) | componente `adsorbato` chave `log_kow` | hidrofobicidade; sustenta o argumento de interacao π-π/hidrofobica no carvao |
| Carga ionica efetiva em pH 5,5 | e (carga elementar) | **−0,39** (calculada: fracao anionica 39% com pKa2 = 5,7; 44% se pKa2 = 5,6) | **calculada** (Henderson-Hasselbalch com pKa2 acima) — nao e valor de literatura | componente `adsorbato` chave `carga_ionica`, com `origem: "calculada"` e `metodo` explicito | alimenta a leitura da regra pH × PZC (intensidade, nao so sinal) |
| Solubilidade em agua | mg/L | **610** a 37 C (Yalkowsky & Dannenfelser, 1992); "< 1 mg/mL" a 20 C (NTP, 1992) | via PubChem, "Solubility" | componente `adsorbato` chave `concentracao_trabalho` **nao** serve; usar `referencia`/texto no item de solubilidade no componente `adsorbato` | escolha da faixa de C0 do ensaio de isoterma (nao exceder ~600 mg/L) |
| Classe fisico-quimica no backend | texto | `anion_organico` | derivada por **casamento lexical** do campo `contaminante` (`adsorventes.CLASSES_CONTAMINANTE`) | `PATCH /api/research/{pesq}` campo `contaminante` deve conter "sulfametoxazol" | e a chave que ativa a regra `pH × PZC` (sem ela o veredito e "indeterminado") |
| pH de operacao | pH | **5,5** (ja gravado) | condicao experimental declarada | `amb_pesquisas.condicoes_json` (ou `condicoes.pH` no POST do adsorvente) | fecha a compatibilidade junto com P2 |
| Temperatura | C | **25** (ja gravado) | condicao experimental declarada | `condicoes.temperatura_C` | idem |
| Raio / dimensao molecular | nm | **nao reportado** | — | nao enviar | S4/sitio de acesso: so com estimativa declarada como tal |
| Momento dipolar | debye | **nao reportado** | — | nao enviar | so com motor quantico (o `dft` local devolve default — F3) |
| HOMO / LUMO / gap | eV | **nao reportado** | — | nao enviar | so com DFT real; nao usar o P6 = 2,0 eV do default |
| Energia de hidratacao | kJ/mol | **nao reportado** | — | nao enviar | — |
| Hidrogenio/fukui/QTAIM/NCI | — | **nao reportado** | — | nao enviar | — |

Formulas usadas nas linhas calculadas (para poderem ser auditadas):

```
fracao anionica(pH) = 1 / (1 + 10^(pKa2 - pH))
pH 5,5 ; pKa2 5,7 -> 1/(1+10^0,2) = 0,386  -> carga media ~ -0,39 e
pH 5,5 ; pKa2 5,6 -> 1/(1+10^0,1) = 0,443  -> carga media ~ -0,44 e
```

---

## 4. Caminho minimo — 3 envios que tiram o resultado do empate

Todos os corpos abaixo foram conferidos contra os modelos Pydantic
(`MedicaoEntrada`, `DescritoresEntrada`, `AdsorventeEntrada`,
`SimuladorExecucaoEntrada`) e contra as regras de `matriz_7d4`. Repetir para
**A** e **B** (trocando o `material_id`). JSON sem acentos, para nao depender de
encoding no PowerShell 5.1.

### 4.1 Envio 1 — P2 (PZC) pela rota de componentes

```powershell
$corpo = @'
{
  "parametros": [
    {
      "chave": "pzc",
      "valor": 7.4,
      "unidade": "pH",
      "origem": "medido",
      "metodo": "deriva de pH: 0,05 g em 20 mL de NaCl 0,01 mol/L, 24 h, 150 rpm, 25 C",
      "referencia": "replicatas 7,3 / 7,4 / 7,5 (RSR 1,4%) - relatorio do ensaio de bancada",
      "estado": "validado"
    }
  ],
  "pesquisa_id": "pesq_63b32e62389dae7c"
}
'@
Invoke-RestMethod -Method Post -ContentType "application/json" `
  -Uri "http://127.0.0.1:7860/api/materials/mat_ca84ac210575584a/components/adsorvente" `
  -Body ([Text.Encoding]::UTF8.GetBytes($corpo))
```

**Ensaio executado numa copia do banco (resultado real desta copia):** P2 gravado
como `7.4 pH`, estado `validado`, e a compatibilidade passou de `indeterminado`
para **`favoravel`** (`carga_superficie: positiva`, `margem_pH_PZC: -1.9`).

Por que nao pela rota de medicoes (`POST /api/materials/{id}/measurements`): ela
esta **bloqueada** nesta copia — `medicoes.validar` chama
`analises_experimentais._num` (STUB) e devolve `RuntimeError` (HTTP 500). Detalhe
em 5.1. Quando o bytecode 3.10 for restaurado, a rota de medicoes volta a ser a
preferida, porque grava replicatas, incerteza, RSR e instrumento em tabela
propria (`amb_medicoes`).

Alternativa equivalente (quando o laboratorio entrega so o numero final):

```powershell
$corpo = @'
{
  "valores": {
    "P2": {
      "valor": 7.4,
      "unidade": "pH",
      "estado": "validado",
      "fonte": "deriva de pH (24 h, NaCl 0,01 mol/L); replicatas 7,3 / 7,4 / 7,5"
    }
  }
}
'@
Invoke-RestMethod -Method Post -ContentType "application/json" `
  -Uri "http://127.0.0.1:7860/api/materials/mat_ca84ac210575584a/descriptors?pesquisa_id=pesq_63b32e62389dae7c" `
  -Body ([Text.Encoding]::UTF8.GetBytes($corpo))
```



### 4.2 Envio 2 — D1 medido (isoterma) — grava D1 **e** D2 na mesma chamada

O backend tem um acoplamento verificado em `adsorventes.validar`: quando o corpo
traz `calculo.D1` e nao traz `calculo.D2`, ele copia a entrada e aplica a regra
de Langmuir tambem em D2 (`if "D2" not in calculo and calculo.get("D1")`). Ou
seja: **um unico envio fecha D1 (qmax) e D2 (KL)** com o mesmo ajuste.

```powershell
$corpo = @'
{
  "material_id": "mat_ca84ac210575584a",
  "condicoes": {"pH": 5.5, "temperatura_C": 25, "Ce": 12.5},
  "calculo": {
    "D1": {
      "pontos": [
        {"Ce": 1.2,  "qe": 18.4},
        {"Ce": 5.1,  "qe": 41.9},
        {"Ce": 12.5, "qe": 62.7},
        {"Ce": 24.8, "qe": 78.3},
        {"Ce": 41.0, "qe": 86.1},
        {"Ce": 55.7, "qe": 90.4}
      ]
    },
    "D6": {"C0": 20.0, "Ce": 7.2, "volume_L": 0.05, "massa_g": 0.010},
    "D3": {
      "pontos_cinetica": [
        {"t": 5, "qt": 21.0}, {"t": 15, "qt": 38.5}, {"t": 30, "qt": 52.2},
        {"t": 60, "qt": 64.0}, {"t": 120, "qt": 73.1}, {"t": 240, "qt": 80.0},
        {"t": 480, "qt": 84.6}, {"t": 1440, "qt": 88.9}
      ]
    }
  },
  "modelos": ["langmuir", "freundlich"],
  "simuladores": []
}
'@
Invoke-RestMethod -Method Post -ContentType "application/json" `
  -Uri "http://127.0.0.1:7860/api/research/pesq_63b32e62389dae7c/adsorbent" `
  -Body ([Text.Encoding]::UTF8.GetBytes($corpo))
```

> **Os `Ce`/`qe` acima sao de exemplo** (servem para conferir o formato e o
> ajuste). Substituir pelos pontos medidos — o backend nao aceita menos de 2
> pontos positivos para D1/D2 nem menos de 3 para D3
> (`ParametroAusente: dois_pontos_com_Ce_e_qe_positivos` / `tres_pontos_positivos`).

Notas de execucao:

* `simuladores: []` e proposital: impede o `_executar_simuladores` de rodar
  motores que nao contribuem (sem `simuladores`, o backend escolheria os
  compativeis com os parametros recebidos).
* `condicoes.Ce` e necessario para o modelo `langmuir` (requisitos: `qmax`,
  `KL`, `Ce`) — usar um `Ce` **medido** da propria isoterma.
* a resposta traz `descritores` (D1 com `complemento.KL_L_mg` e `r2`, D2, D3,
  D6), `regras_pendentes`, `modelos`, `compatibilidade` e `lacunas_experimentais`.
* para testar os numeros **sem gravar**, usar o dry-run:
  `POST /api/matriz/D1/calcular` com `{"pontos": [...]}` (nao persiste).


### 4.3 Envio 3 — D2 (KL / Kf) quando o laboratorio entrega o ajuste pronto

Serve para dois casos: (a) o laboratorio informa KL do proprio ajuste de
Langmuir; (b) Freundlich com Kf e n, que a regra de D2 do backend **nao**
calcula (so Langmuir linearizado) — por isso entra por `valores`, com a fonte
O bloco seguinte mostra de proposito **as duas variantes**: a primeira (com
`valores_kf`) e rejeitada/ignorada pelo backend e serve para nao repetir o erro;
a segunda e a que grava.

declarada.

```powershell
$corpo = @'
{
  "valores": {
    "D2": {
      "valor": 0.042,
      "unidade": "L/mg",
      "estado": "presente",
      "fonte": "ajuste de Langmuir reportado pelo laboratorio (isoterma batelada, pH 5.5, 25 C)"
    }
  },
  "valores_kf": {
    "Kf": 9.7,
    "n": 2.31,
    "unidade_Kf": "(mg/g)(mg/L)^-1/n"
  }
}
'@
Invoke-RestMethod -Method Post -ContentType "application/json" `
  -Uri "http://127.0.0.1:7860/api/materials/mat_ca84ac210575584a/descriptors?pesquisa_id=pesq_63b32e62389dae7c" `
  -Body ([Text.Encoding]::UTF8.GetBytes($corpo))
```

Atencao (verificado em `motor_pesquisa.preencher_descritores`): o corpo aceita
`calculo`, `valores`, `codigos`, `estado` e `fonte`. A chave `valores_kf` **nao
existe** no backend — Kf e n devem ir no `complemento` textual do item de D2 ou
no `metodo`/`fonte` (o descritor D2 tem um unico slot numerico; quando ha KL
**e** Kf, gravar KL como valor e citar Kf/n na fonte, para nao sobrescrever).
Ou seja, o envio correto e apenas:

```json
{
  "valores": {
    "D2": {
      "valor": 0.042,
      "unidade": "L/mg",
      "estado": "presente",
      "fonte": "Langmuir ajustado pelo laboratorio; Freundlich Kf = 9,7 (mg/g)(mg/L)^-1/n e n = 2,31 no relatorio do ensaio"
    }
  }
}
```

Se a isoterma do 4.2 ja fechou D2, este envio e **redundante para Langmuir** e
so se justifica se o ajuste do laboratorio for o adotado oficialmente.

---

## 5. Avisos verificados (nao ignorar)

### 5.1 `analises_experimentais` e STUB nesta copia — atinge 2 frentes

`ambiental_backend/analises_experimentais.py` e' um stub de QA: qualquer chamada
levanta `RuntimeError`. O modulo original **sobreviveu como bytecode CPython 3.10**
(e' o que `rodar_simuladores.py` carrega num palco isolado, §2.2). Duas
consequencias, de naturezas diferentes:

1. **Os 16 motores experimentais nao rodam pela API desta copia** (Python 3.13):
   `POST /api/simulators/{nome}/run` devolve `erro` com a mensagem do stub. Pelo
   script em 3.10 eles rodam — verificado 25/25 no §2.
2. **A rota de medicoes tambem cai** — e essa **nao** tem contorno por
   interpretador, porque a API de pe' e' 3.13: `medicoes.validar` usa
   `analises_experimentais._num` e `medicoes.estatisticas` usa `ax._media_sd`.
   Testado numa copia do banco: `POST /api/materials/{id}/measurements` devolve
   `RuntimeError` (HTTP 500) para **qualquer** tipo de medicao.

Rotas que **funcionam** (testadas nesta copia, sem chamar `ax`):

| rota | serve para | descritores |
|---|---|---|
| `POST /api/materials/{id}/components/{adsorvente\|adsorbato\|interface\|meio}` | caracterizacao com validacao de catalogo (usar para PZC) | P2 (`pzc`, `carga_superficial`), S3, S4, S6 (`grupos_funcionais`, `densidade_sitios`), D1 (`capacidade_experimental`) |
| `POST /api/materials/{id}/descriptors?pesquisa_id=..` | `valores` (numero informado + fonte) e `calculo` (regras) | qualquer um dos 28 |
| `POST /api/research/{id}/adsorbent` | `caracterizacao` (mapa `adsorventes.CARACTERIZACAO`), `composicao` (S1), `calculo` (D1/D2/D3/D6/P1/P3/C2/C4/C7), `condicoes`, `modelos` | quase todos, e roda Langmuir/Freundlich se `condicoes.Ce` existir |
| `POST /api/simulators/{nome}/run` | na API 3.13: nenhum (universal sem numpy, 16 no stub). Pelo `rodar_simuladores.py` (3.10): os 25 | ver tabela 2.1 |

Para restaurar a rota de medicoes: rodar a API com o bytecode CPython 3.10 (imagem
`python:3.10-slim`, como no Space) — nao basta o script, porque a rota vive no
processo da API. Ate la, o valor medido entra por `components`/`valores` com
`metodo` e `referencia` declarados — mantem a rastreabilidade, mas **nao** grava
replicatas em `amb_medicoes`.

### 5.2 S1 nao entra pela rota de componentes

O parametro `composicao` do componente `adsorvente` **nao** tem campo
`descritor` em `matriz_cruzamentos.PARAMETROS`, logo nao preenche S1. O unico
caminho que grava S1 nesta copia e `composicao: [{"elemento","fracao_massica"}]`
no `POST /api/research/{id}/adsorbent` (`adsorventes._s1_da_composicao`).

### 5.3 Unidade de CTC: `mmolc/kg` na rota de medicoes, `cmol/kg` no descritor

`medicoes.TIPOS["ctc"]["unidade"]` e **`mmolc/kg`**; o descritor P3 usa
**`cmol/kg`**. Enviar `cmol/kg` na rota de medicoes (quando ela voltar) devolve
HTTP 400 pedindo conversao previa. Na rota `/adsorbent` (`caracterizacao.ctc`) o
valor entra direto em `cmol/kg`. Escolher uma das duas e nao misturar.

### 5.4 SMX em pH 5,5 NAO e predominantemente anionico

A classe `anion_organico` vem de casamento lexical do texto do contaminante
(`adsorventes.CLASSES_CONTAMINANTE`), nao de calculo de especiação. Com pKa2 =
5,7 (HSDB/Boreen 2004), em pH 5,5 apenas **~39%** das moleculas estao
desprotonadas (44% se pKa2 = 5,6); a especie dominante e a **neutra**. Portanto:
o veredito `favoravel` da regra `pH x PZC` (quando PZC > 5,5) e
**eletrostaticamente fraco** e deve ser lido como "nao desfavoravel". O texto da
dissertacao deve atribuir a adsorcao de SMX em carvao a interacoes
π-π / ligacao de hidrogenio / preenchimento de microporos, e nao a atracao
eletrostatica forte. O backend nao modela essa nuance — e uma limitacao a
declarar.

### 5.5 P6 = 2,0 eV e residuo, nao propriedade

Linha `P6 = 2.0 eV / estimado / universal.sim_dft` existe nos dois materiais por
execucao anterior. O `sim_dft` devolve `default: 2.0` quando o material nao esta
na tabela (`"C"` e o caso) — identico para A e B, logo Δ = 0 e nao discrimina.
Limpeza documentada em `RELATORIO_SMX_LOCAL.md` (SQL de remocao da linha
`estimado`).

### 5.6 Cobertura nao e idempotente (F1)

`amb_descritores` e chaveada por `material_id` (+ codigo), nao por
`(pesquisa_id, material_id)`: um valor gravado numa pesquisa aparece em todas.
E por isso que P6 "vazou" para a comparacao. Nas gravacoes novas
(P2, D1, D2, D3, D6) isso nao causa erro — mas o mesmo material nao pode ter
dois valores diferentes por pesquisa.

### 5.7 `contaminante` da pesquisa contem texto extra

Valor atual: `"sulfametoxazol, classe ionica: anion organico"`. Funciona para a
classificacao (casa a pista "sulfametoxazol"), mas a segunda parte e uma
**afirmacao do usuario** embutida no dado. Sugestao: `PATCH` deixando apenas
`sulfametoxazol` e registrar a classe/espécie em `componentes` do adsorbato.

### 5.8 Material duplicado

`mat_4dd5ed09f7fa7c93` (KL-KOH-1:1-fresh) e residuo de QA com S3/S4/D1 e fonte
"propriedade declarada no pedido". Nao enviar ensaio novo para ele: usar
`mat_ca84ac210575584a`.


---

## 6. Como conferir que funcionou

### 6.1 Ensaio do proprio plano (executado numa copia do banco)

**Experimento A — caminho minimo (§4), 3 envios.** Rodado de ponta a ponta
contra uma copia de `dados_ambiental/ambiental.db` (o banco real nao foi tocado):

| etapa | resultado observado |
|---|---|
| Envio 1 (P2 por componentes) | `P2 = 7.4 pH`, estado **`validado`** |
| Envio 2 (`/adsorbent` com `calculo` D1+D3+D6) | `D1 = 100.4708 mg/g` (r2 0.9987, 6 pontos), `D2 = 0.149693 L/mg`, `D3 = 0.000459 g/(mg*min)` (qe 90.16 mg/g, t95 459 min), `D6 = 64.0 %` — todos `calculado` |
| Langmuir | executou com `qmax`, `KL`, `Ce` = 12.5; `faltando: []` |
| Compatibilidade | saiu de `indeterminado` para **`favoravel`** (PZC 7.4 > pH 5.5, margem −1.9, superficie positiva) |
| cobertura do material A | 4 → **8** descritores com valor (S3, S4, P2, P6, D1, D2, D3, D6) |

> Os numeros acima vem dos **pontos de exemplo** do §4.2 (nao de ensaio real).
> Servem para provar que o formato fecha: substituindo pelos pontos medidos, os
> mesmos campos devolvem o qmax/KL/k2 do material.

**Experimento B — os 25 simuladores (§2).** `python rodar_simuladores.py --gravar`,
tambem em copia:

| etapa | resultado observado |
|---|---|
| execucao dos motores | **25/25** com motor real (`ok` ou `ok_com_aproximacao`), 0 erro |
| gravacao | todos os itens passaram por `adsorventes.aplicar_descritores` sem excecao |
| cobertura A e B | 4/28 → **16/28** (14,29% → 57,14%) |
| conflitos | P7 acabou em 3 % (solubilidade sobrescreveu lixiviacao); P2 em 7,8 (titulacao sobrescreveu deriva) |
| valores falsos que o sistema aceita | `C5 = 0,0`, `C1 = 0,04` (cobertura 2,4%), `P6 = 2,0` (default), `S3`/`S5` (eco) |

> Conclusao dos dois experimentos: **o gargalo nao e' o software** — 4 → 16
> descritores num comando, com rastreabilidade. O gargalo e' o ensaio. Subir a
> cobertura por simulador (B) enche a matriz de numero sem lastro; subir pelo
> caminho minimo (A) deixa 8 celulas **defensaveis** em 3 envios. O plano segue o
> caminho A; a tabela 2.1 diz em que ponto cada simulador ajuda **depois** de o
> ensaio existir.

### 6.2 Depois de cada envio real

```powershell
# 1) descritores e estados do material A
Invoke-RestMethod "http://127.0.0.1:7860/api/materials/mat_ca84ac210575584a/descriptors" |
  Select-Object -ExpandProperty descritores |
  Where-Object { $_.codigo -in "P2","D1","D2","D3","D6" } |
  Format-Table codigo, valor, unidade, estado, fonte

# 2) validacao completa (compatibilidade + lacunas + modelos)
Invoke-RestMethod -Method Post -ContentType "application/json" `
  -Uri "http://127.0.0.1:7860/api/research/pesq_63b32e62389dae7c/adsorbent" `
  -Body '{"material_id":"mat_ca84ac210575584a","simuladores":[]}' |
  Select-Object -ExpandProperty compatibilidade
```

Criterio de saida do empate:

| antes | depois esperado |
|---|---|
| cobertura 4/28 nos dois | 8–9/28 nos dois (S3, S4, D1, D2, D3, D6, P2, P6-limpo, S5) |
| D1 = 100 / 100 (hipotese) | D1 e D2 **distintos** entre A e B (qmax e KL medidos) |
| compatibilidade `indeterminado` | `favoravel`/`desfavoravel` com `margem_pH_PZC` explicita |
| Langmuir/Freundlich `bloqueado_por_parametros` | `langmuir` executado com qmax/KL/Ce; Freundlich ainda exige Kf/n do laboratorio |

Ordem de leitura dos resultados na dissertacao: **P2 + compatibilidade** (secao
de mecanismo), **D1 + D2** (secao de capacidade e afinidade), **D3** (secao de
cinetica), **D6** (secao de desempenho). O que nao existir continua declarado
como ausente — nao preencher com o default de simulador.

---

## 7. Uma linha de resumo

Os dois carvoes so diferem hoje em **S3 (+31%)** e **S4 (+18%)**; o empate real
esta em **P2, D1, D2, D3, D6**. Os 25 simuladores foram executados
(`rodar_simuladores.py`, 25/25) e a matriz foi **preenchida por inteiro** com
lastro declarado (`preencher_matriz.py`, 26/28 + 1 nao aplicavel + 1 pendente) —
mas preencher nao e' medir: dos 28 descritores, **4** carregam informacao real
(S3, S4, D1 medidos e P1 derivado deles) e **22 sao cenario**, iguais por
construcao nos dois materiais. O cosseno entre A e B mede exatamente isso
(§8.4). O caminho defensavel continua sendo **dois envios** — PZC pela rota de
componentes (Envio 1) e isoterma + cinetica + remocao no `/adsorbent` (Envio 2)
— que transformam 8 celulas de cenario em medicao.

---

## 8. Matriz cheia (28 celulas) e semelhanca de cosseno

### 8.1 Como reproduzir

```powershell
python preencher_matriz.py                  # monta as 28 celulas (nao grava)
python preencher_matriz.py --gravar --json  # grava numa COPIA (_qa_matriz/) + dossie json
python semelhanca_cosseno.py --json         # le a copia e calcula os cossenos
python preencher_matriz.py --gravar-real    # so quando o dado de bancada entrar
```

`--gravar-real` faz copia de seguranca em `dados_ambiental/ambiental.backup-matriz.db`
antes de escrever. A copia de trabalho e' `_qa_matriz/ambiental.db`.

### 8.2 As 28 celulas — o que e' medido, derivado, cenario e pendente

| cod | rota | nivel | A (1:1) | B (2:1) | unidade |
|---|---|---|---|---|---|
| S1 | `composicao_elementar` | 3 cenario | 91,79 | 91,79 | % pureza |
| S2 | direto (literatura DRX) | 3 cenario | amorfo | amorfo | texto |
| S3 | banco (**medido**) | 1 medido | **1262** | **963** | m2/g |
| S4 | banco (**medido**) | 1 medido | **0,58** | **0,49** | cm3/g |
| S5 | direto (moagem) | 3 cenario | 45 | 45 | um |
| S6 | `boehm_grupos` | 3 cenario | 0,80 | 0,80 | mmol/g |
| S7 | `granulometria_psd` | 3 cenario | 30 | 30 | um |
| P1 | regra P1 (de S4) | **2 derivado** | **0,904** | **0,984** | g/cm3 |
| P2 | `pzc_deriva_ph` | 3 cenario | 7,2 | 7,2 | pH |
| P3 | regra CTC | 3 cenario | 30 | 30 | cmol/kg |
| P4 | `angulo_contato` | 3 cenario | 28,59 | 28,59 | mN/m |
| P5 | `tga_tangente` | 3 cenario | 429 | 429 | C |
| P6 | nao aplicavel | 4 n/a | — | — | eV |
| P7 | `lixiviacao_cinetica` | 3 cenario | 1,2 | 1,2 | % |
| D1 | banco (**medido**) | 1 medido | 100 | 100 | mg/g |
| D2 | regra Langmuir (cenario) | 3 cenario | 0,05 | 0,05 | L/mg |
| D3 | regra PSO (cenario) | 3 cenario | 1,9e-3 | 1,9e-3 | g/(mg min) |
| D4 | `seletividade_competitiva` | 3 cenario | 2,772 | 2,772 | adim. |
| D5 | `regeneracao_reuso` | 3 cenario | 7 | 7 | ciclos |
| D6 | regra remocao | 3 cenario | 99,96 | 99,96 | % |
| D7 | direto (pKa do SMX + PZC) | 3 cenario | pH 5–8 | pH 5–8 | texto |
| C1 | `perigo_composicao` (descartado o indice) | 3 cenario | texto | texto | — |
| C2 | regra custo | 3 cenario | 0,12 | 0,12 | R$/g |
| C3 | pendente documental | 0 pendente | — | — | t/ano |
| C4 | regra energia | 3 cenario | 4 | 4 | kWh/kg |
| C5 | `reciclabilidade` | 3 cenario | 0,40 | 0,40 | 0–1 |
| C6 | `conformidade_limites` | 3 cenario | 85,6 | 85,6 | % |
| C7 | regra TRH | 3 cenario | 12 | 12 | min |

Resultado da gravacao na copia: **4/28 → 26/28 (14,3% → 92,9%)**, 28
descritores e 26 parametros de componente gravados, **0 erros**. As duas celulas
fora da conta sao deliberadas: `P6` (`nao_aplicavel` — banda proibida nao
governa adsorcao no escuro; o `2,0 eV` que estava la era default do `sim_dft`) e
`C3` (exige oferta anual e distancia: dado documental, nao se estima).

Leitura honesta da tabela: **3 celulas medidas, 1 derivada, 22 de cenario, 1 nao
aplicavel, 1 pendente**. As 22 de cenario existem para provar que a cadeia
motor → regra → descritor funciona ponta a ponta; elas **nao** sao propriedade
medida do material e nao devem ser citadas como tal na dissertacao.

### 8.3 Como o cosseno e' calculado (e o que ele nao e')

Cada descritor vira um numero entre 0 e 1 pela **faixa fisica declarada** em
`semelhanca_cosseno.NORMALIZACAO` (nao pela faixa observada na amostra, que
mudaria conforme o numero de materiais). Direcao explicita: `+1` maior e' melhor
(S3, D1, D6...), `-1` menor e' melhor (P7, custo, energia, TRH, granulometria),
`0` neutro (PZC, densidade, CTC). `D2` e `D3` sao normalizados em escala log.
Celula `ausente`, `nao_aplicavel` ou texto puro **fica fora** do vetor — zero
seria um valor, ausencia nao e'. O cosseno roda apenas sobre as dimensoes
comuns e o `n` aparece junto do resultado.

Tres recortes:

| recorte | o que entra |
|---|---|
| `completo` | todos os descritores com valor numerico (nivel 1–3) |
| `lastro` | so nivel 1–2 (medido + derivado de medido) |
| `perfil` | media por eixo informacional (E, P, D, S, I, C, O) |

### 8.4 Resultado medido (copia `_qa_matriz/ambiental.db`)

| comparacao | cosseno | n | dimensoes |
|---|---|---|---|
| **A x B completo** | **0,9981** | 23 | todos menos S2, D7, C1 (texto), P6, C3 |
| **A x B lastro** | **0,9826** | 4 | D1, P1, S3, S4 |
| **A x B perfil** (7 eixos) | 0,9999 | 6 | C, D, E, I, O, S |
| **A x adsorbato (SMX)** | 0,7913 | 3 | D, O, S |
| **B x adsorbato (SMX)** | 0,7944 | 3 | D, O, S |

Ranking de delta (o que realmente separa A de B):

| cod | A | B | delta |
|---|---|---|---|
| S3 | 0,612 | 0,454 | **+0,157** |
| P1 | 0,671 | 0,760 | **−0,089** |
| S4 | 0,436 | 0,354 | **+0,082** |
| os outros 20 | — | — | 0,000 |

### 8.5 O que esses numeros dizem

1. **A e B sao quase o mesmo vetor** (0,9981). Isso nao e' falha do metodo: e' o
   retrato fiel de um banco em que 22 das 28 celulas sao cenario identico. Um
   cosseno de 0,99 entre dois materiais apresentados como diferentes e' um
   argumento *contra* dizer que o sistema distingue A de B hoje, e a favor de
   rodar os ensaios do §1.
2. **No espaco com lastro real (0,9826, n = 4) a diferenca e' pequena mas
   existe**: S3 (+31% e +0,157 no normalizado), S4 (+18% e +0,082) e P1
   (−8,9%, heranca do volume de poros). E' esta a diferenca que a dissertacao
   pode defender hoje.
3. **Material x contaminante (0,79) nao e' previsao de adsorcao.** E' semelhanca
   de perfil em 3 eixos contra um adsorbato que so tem D (massa molar, raio),
   S (pKa, log Kow) e O (concentracao) preenchidos. A diferenca entre A e B nesse
   numero (0,7944 − 0,7913 = 0,0031) e' **menor que a resolucao do preenchimento**
   — nao serve para escolher material. Afinidade se prova com isoterma (D1/D2) e
   cinetica (D3), como ja diz o §4.
4. Para o cosseno virar ferramenta de decisao faltam tres coisas: mais
   contaminantes cadastrados (`componentes.registrar` por `pesquisa_id` aceita um
   adsorbato por pesquisa), os eixos E/I/C do adsorbato (energia de hidratacao,
   HOMO/LUMO, limite normativo) e, sobretudo, os descritores medidos do §1.
5. Enquanto isso, o uso correto do resultado e' **descritivo**: a matriz completa
   mostra que a cadeia de calculo funciona e isola os 4 numeros que separam os
   materiais.

### 8.6 Corrigido no codigo nesta rodada

| arquivo | mudanca | por que |
|---|---|---|
| `ambiental_backend/motores_ambientais.py` | `regeneracao_reuso` publica `ciclos_ate_80pct_capacidade` (mantendo `ciclos_uteis`) | `descritores_simuladores` procura a primeira chave; era o motivo de **D5 nunca ser gravado** (bug registrado no §2.4) |
| `ambiental_backend/motor_pesquisa.py` | `registrar_valor_medido(..., memoria=None)` | a `memoria` era fixa ("valor medido em bancada"), o que rotulava celula de cenario como medicao |

Verificacao: `test_ambiental_motores.py` roda **42/42 com o motor real** dentro
do palco 3.10 (o pytest do ambiente 3.13 nao carrega o bytecode antigo — ver
§5.1). D5 saiu de "nunca gravado" para `7 ciclos` nas duas copias.


