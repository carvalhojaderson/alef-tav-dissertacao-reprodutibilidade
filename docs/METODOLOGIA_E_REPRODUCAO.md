# Metodologia e protocolo de reprodução

Este documento descreve **o que o código faz** e **como conferir cada número**
relatado na dissertação. Ele não substitui os capítulos metodológicos do texto:
descreve a implementação que produziu os resultados.

## 1. Objeto

A plataforma ALEF-TAV é composta por duas camadas publicadas aqui:

| Camada | Arquivos | Papel |
|---|---|---|
| Núcleo científico | `universal.py` (113 simuladores), `modelos_adsorcao_v2.py`, `modelos_analiticos_v2.py`, `nucleo_dados.py`, `pesquisa_cientifica.py`, `bancos_rest.py`, `bases_v5.py`, `conectores_academicos.py`, `integracoes_reais.py`, `exportadores.py`, `doc_export.py`, `registro_componentes.py`, `catalogo_registry.py`, `chaves_config.py`, `seguranca.py`, `cache_busca.py` | cálculo, persistência e acesso a bases |
| Backend ambiental | `ambiental_backend/` (matriz 7D×4, orquestração, motores, API) | organiza a pergunta em protocolo, executa simuladores, grava descritores e emite relatórios |
| Scripts de estudo | `smx_local.py`, `comparar_candidatos.py`, `semelhanca_cosseno.py`, `dossie_matriz.py`, `preencher_matriz.py`, `rodar_simuladores.py`, `checar_motores_palco.py`, `validar_adsorventes.py`, `validar_integracao.py` | reproduzem os cálculos do estudo de caso |

## 2. Matriz de 28 descritores (7D×4)

`ambiental_backend/matriz_7d4.py` declara **4 dimensões × 7 descritores = 28**:

| Dimensão | Prefixo | Descritores |
|---|---|---|
| D1 Estrutura | `S` | S1 composição e pureza; S2 fase cristalina; S3 área BET; S4 volume/distribuição de poros; S5 tamanho de partícula; S6 grupos funcionais; S7 morfologia e agregação |
| D2 Propriedades | `P` | P1 densidade; P2 PZC; P3 CTC; P4 hidrofobicidade; P5 estabilidade térmica; P6 condutividade/bandgap; P7 solubilidade e lixiviação |
| D3 Desempenho | `D` | D1 qmax; D2 afinidade (KL, Kf); D3 cinética; D4 seletividade; D5 regeneração; D6 eficiência de remoção; D7 faixa operacional |
| D4 Contexto | `C` | C1 toxicidade; C2 custo; C3 disponibilidade; C4 pegada energética; C5 reciclabilidade; C6 conformidade; C7 escalabilidade |

Cada descritor traz definição, unidade, **regra matemática** e sinônimos de
busca. A matriz é declarativa: o que não pode ser calculado a partir do dado
recebido permanece como ausência explícita — **nunca zero e nunca estimativa
silenciosa**.

### 2.1 Cruzamentos 7×4

`ambiental_backend/matriz_cruzamentos.py` cruza **7 dimensões informacionais**
(E energética, P eletrônica, D estrutural, S superficial, I interacional,
C ambiental, O operacional) com **4 componentes** (adsorbato, adsorvente,
interface, meio) = **28 cruzamentos**. Cada cruzamento recebe todos os
descritores que o informam (`RELACOES_DESCRITORES`, 28 chaves, com relação
principal e secundárias).

Regras implementadas no módulo:

* não cria descritor nem valor: descritor sem dado aparece como `ausente`,
  com peso 0 e listado em `lacunas`;
* **não usa peso universal por dimensão** (o código explicita a rejeição de
  "40/20/20/20"): o peso vem dos critérios existentes (seleção, estado do
  dado, entropia das respostas, redundância entre descritores);
* cada peso carrega os fatores que o produziram (rastreabilidade).

### 2.2 Parâmetros de caracterização

`PARAMETROS` reúne **59** entradas de caracterização dos quatro componentes
(fórmula molecular, massa molar, pKa, log Kow, carga iônica, área BET, volume
de poros, PZC, energia de adsorção, etc.). Cada entrada declara `fonte`
(informado, importado, calculado, medido) e, quando existe regra, o descritor
que alimenta.

## 3. Estados do dado

`presente` (informado/medido e disponível), `calculado` (produzido por regra
ou simulador), `estimado` (referência interna, não medição), `ausente`
(faltando, com a lista do que falta) e `nao_aplicavel` (o descritor não se
aplica àquele material/condição). O estado acompanha o valor em todas as
saídas — é o que impede ler um valor de simulador como dado experimental.

## 4. Cobertura

`preenchimento.com_dado` conta descritores com valor sobre **28**. Os números
do estudo de caso:

* execução sem núcleo científico: **3/28 = 10,71 %**;
* execução com núcleo (simuladores ativos): **4/28 = 14,29 %**.

O salto de 0 % para 57,14 % de cobertura relatado na dissertação **não** vem
do esforço computacional: vem da caracterização (dados de bancada/literatura
que preenchem os descritores S, P e D de entrada).


## 5. Semelhança de cosseno

`semelhanca_cosseno.py` compara perfis normalizados:

1. cada descritor é normalizado por faixa física declarada em `NORMALIZACAO`
   (ex.: S3 entre 100 e 2000 m²/g; D2 em escala log entre 0,005 e 1 L/mg),
   com clip em [0, 1] e inversão quando "menor é melhor";
2. ausência **não** entra como zero: o vetor só contém descritores com valor
   e estado diferente de `ausente`/`nao_aplicavel`;
3. o cosseno é calculado **apenas sobre as dimensões comuns** aos dois
   vetores, e `n` (número de dimensões usadas) acompanha o resultado:

   cos(u, v) = Σ uᵢvᵢ / (‖u‖ ‖v‖), arredondado a 6 casas;

4. há dois recortes: `lastro` (nível 1–2: medido + derivado) e `completo`
   (inclui nível 3: cenário). Se o resultado muda entre recortes, a diferença
   é do cenário, não do material;
5. `perfil` compara os vetores agregados por eixo (média dos descritores de
   cada eixo).

Limite declarado no próprio módulo: cosseno alto entre material e contaminante
**não** é previsão de adsorção — é semelhança de perfil nos eixos medidos.

## 6. Simuladores e motores

* `universal.py` cataloga **113** funções `sim_*` (verificado por contagem no
  arquivo). Nem todas são executáveis no ambiente: módulos opcionais
  (RDKit, ASE, pymatgen, OpenMM, scikit-learn …) não são dependências
  obrigatórias.
* `ambiental_backend/motores_ambientais.py` reúne **16 motores próprios** de
  bancada → descritor (ângulo de contato, Boehm, composição elementar,
  conformidade, fractal, FTIR, granulometria, lixiviação, perigo,
  PZC por deriva, PZC por titulação, reciclabilidade, regeneração,
  seletividade, solubilidade, TGA).
* `ambiental_backend/descritores_simuladores.py` é o mapa
  descritor → simuladores/motores/regra. É ele que decide qual saída vira
  qual descritor (e com que estado).

## 7. `analises_experimentais` e o bytecode de 2026-11-03

O arquivo-fonte original desse módulo foi perdido por corrupção de disco. O
bytecode CPython 3.10 sobreviveu e é preservado em
`ambiental_backend/_recuperacao/analises_experimentais.cpython-310.pyc`.
O carregador `analises_experimentais.py` (raiz) executa esse bytecode e exige
**CPython 3.10**; em outra versão ele levanta `RuntimeError` explícito em vez
de devolver número inventado. A cópia dentro do pacote
(`ambiental_backend/analises_experimentais.py`) é um *stub* que recusa a
execução — é o que o repositório publica como estado fiel da cópia local.

## 8. Protocolo de verificação usado na publicação

1. cópia integral do snapshot para um diretório temporário;
2. execução dos scripts de estudo **na cópia** (nunca no snapshot publicado);
3. comparação campo a campo das saídas com os arquivos de resultado
   publicados (ver `docs/RESULTADOS_E_VERIFICACAO.md`);
4. cálculo de SHA-256 de todos os arquivos (`MANIFEST_SHA256.txt`) e
   conferência por `verificar_integridade.ps1`;
5. verificação de segredos antes do commit (`docs/SEGURANCA_E_LICENCAS.md`).
