# Relatorio de viabilidade — ALEF-TAV Ambiental

- **Pesquisa:** `pesq_c93b73b90feeaeac`
- **Material:** KL-KOH-1:1
- **Contaminante:** sulfametoxazol, classe ionica: anion organico
- **Aplicacao:** agua
- **Estado:** prova_executada
- **Gerado em:** 2026-11-10T04:06:24.309656+00:00

## 1. Pergunta

**Adsorcao de sulfametoxazol (SMX) em carvoes ativados KL-KOH. Qual o melhor material?**

Qual material remove o contaminante de interesse de o meio estudado com desempenho demonstravel, custo e conformidade verificaveis? (origem: Adsorcao de sulfametoxazol (SMX) em carvoes ativados KL-KOH. Qual o melhor material?)

## 2. Material

### KL-KOH-1:1

| Propriedade | Valor | Unidade | Origem | Metodo |
|---|---|---|---|---|
| area_superficial | 1262 | m2/g | Brazil et al., 2026 | - |
| volume_poros | 0.58 | cm3/g | Brazil et al., 2026 | - |
| qmax | 100 | mg/g | Brazil et al., 2026 | - |
| PZC | - | pH | Não reportado | - |
| KL | - | L/mg | Não reportado | - |
| area_superficial | 1262 | m2/g | - | BET N2 |
| volume_poros | 0.58 | cm3/g | - | - |
| area_superficial | 1262 | m2/g | Brazil et al., 2026 | - |
| volume_poros | 0.58 | cm3/g | Brazil et al., 2026 | - |
| qmax | 100 | mg/g | Brazil et al., 2026 | - |
| PZC | - | pH | Não reportado | - |
| KL | - | L/mg | Não reportado | - |
| area_superficial | 1262 | m2/g | - | BET N2 |
| volume_poros | 0.58 | cm3/g | - | - |
| area_superficial | 1262 | m2/g | Brazil et al., 2026 | BET N2 |
| volume_de_poros | 0.58 | cm3/g | Brazil et al., 2026 | - |
| capacidade_adsorcao | 100 | mg/g | Brazil et al., 2026 | - |
| area_superficial | 1262 | m2/g | Brazil et al., 2026 | BET N2 |
| volume_de_poros | 0.58 | cm3/g | Brazil et al., 2026 | - |
| capacidade_adsorcao | 100 | mg/g | Brazil et al., 2026 | - |

### KL-KOH-2:1

| Propriedade | Valor | Unidade | Origem | Metodo |
|---|---|---|---|---|
| area_superficial | 963 | m2/g | Brazil et al., 2026 | - |
| volume_poros | 0.49 | cm3/g | Brazil et al., 2026 | - |
| qmax | 100 | mg/g | Brazil et al., 2026 | - |
| PZC | - | pH | Não reportado | - |
| KL | - | L/mg | Não reportado | - |
| area_superficial | 963 | m2/g | - | BET N2 |
| volume_poros | 0.49 | cm3/g | - | - |
| area_superficial | 963 | m2/g | Brazil et al., 2026 | - |
| volume_poros | 0.49 | cm3/g | Brazil et al., 2026 | - |
| qmax | 100 | mg/g | Brazil et al., 2026 | - |
| PZC | - | pH | Não reportado | - |
| KL | - | L/mg | Não reportado | - |
| area_superficial | 963 | m2/g | - | BET N2 |
| volume_poros | 0.49 | cm3/g | - | - |
| area_superficial | 963 | m2/g | Brazil et al., 2026 | BET N2 |
| volume_de_poros | 0.49 | cm3/g | Brazil et al., 2026 | - |
| capacidade_adsorcao | 100 | mg/g | Brazil et al., 2026 | - |
| area_superficial | 963 | m2/g | Brazil et al., 2026 | BET N2 |
| volume_de_poros | 0.49 | cm3/g | Brazil et al., 2026 | - |
| capacidade_adsorcao | 100 | mg/g | Brazil et al., 2026 | - |

## 3. Matriz 7Dx4

| Codigo | Dim. | Descritor | Valor | Unidade | Estado | Fonte |
|---|---|---|---|---|---|---|
| C7 | D4 | Escalabilidade e operacao | - | - | ausente | - |
| C7 | D4 | Escalabilidade e operacao | - | - | ausente | - |
| D1 | D3 | Capacidade maxima de adsorcao (qmax) | 100 | mg/g | presente | Brazil et al., 2026 |
| D1 | D3 | Capacidade maxima de adsorcao (qmax) | 100 | mg/g | presente | Brazil et al., 2026 |
| P6 | D2 | Condutividade / banda proibida | 2 | eV | estimado | universal.sim_dft (saida bandgap_eV) |
| P6 | D2 | Condutividade / banda proibida | 2 | eV | estimado | universal.sim_dft (saida bandgap_eV) |
| S2 | D1 | Fase cristalina / estrutura | - | - | ausente | - |
| S2 | D1 | Fase cristalina / estrutura | - | - | ausente | - |
| S3 | D1 | Area superficial especifica (BET) | 1262 | m2/g | presente | universal.sim_superficie (saida area_m2g) |
| S3 | D1 | Area superficial especifica (BET) | 963 | m2/g | presente | universal.sim_superficie (saida area_m2g) |
| S4 | D1 | Volume e distribuicao de poros | 0.58 | cm3/g | presente | Brazil et al., 2026 |
| S4 | D1 | Volume e distribuicao de poros | 0.49 | cm3/g | presente | Brazil et al., 2026 |

Cobertura: 8 de 12 descritores com dado (66.67%).

## 3.1 Cruzamentos 7 dimensoes x 4 componentes

| Cruzamento | Dimensao | Componente | Com dado | Cobertura | Indice qualidade | Indice comparativo | Lacunas |
|---|---|---|---|---|---|---|---|
| E-adsorbato | E Energetica | Adsorbato | 0/0 | 0 | 0 | - | - |
| E-adsorvente | E Energetica | Adsorvente | 0/2 | 0 | 0 | - | C4, P5 |
| E-interface | E Energetica | Interface adsorvente-adsorbato | 0/0 | 0 | 0 | - | - |
| E-meio | E Energetica | Meio | 0/0 | 0 | 0 | - | - |
| P-adsorbato | P Eletronica | Adsorbato | 0/0 | 0 | 0 | - | - |
| P-adsorvente | P Eletronica | Adsorvente | 1/1 | 1 | 0.4 | - | - |
| P-interface | P Eletronica | Interface adsorvente-adsorbato | 0/0 | 0 | 0 | - | - |
| P-meio | P Eletronica | Meio | 0/0 | 0 | 0 | - | - |
| D-adsorbato | D Estrutural | Adsorbato | 0/0 | 0 | 0 | - | - |
| D-adsorvente | D Estrutural | Adsorvente | 2/7 | 1 | 0.85 | 1 | P1, S1, S2, S5, S7 |
| D-interface | D Estrutural | Interface adsorvente-adsorbato | 0/0 | 0 | 0 | - | - |
| D-meio | D Estrutural | Meio | 0/0 | 0 | 0 | - | - |
| S-adsorbato | S Superficial | Adsorbato | 0/0 | 0 | 0 | - | - |
| S-adsorvente | S Superficial | Adsorvente | 0/4 | 0 | 0 | - | P2, P3, P4, S6 |
| S-interface | S Superficial | Interface adsorvente-adsorbato | 0/0 | 0 | 0 | - | - |
| S-meio | S Superficial | Meio | 0/0 | 0 | 0 | - | - |
| I-adsorbato | I Interacional | Adsorbato | 0/1 | 0 | 0 | - | D4 |
| I-adsorvente | I Interacional | Adsorvente | 0/0 | 0 | 0 | - | - |
| I-interface | I Interacional | Interface adsorvente-adsorbato | 4/12 | 1 | 0.85 | 1 | D2, D3, D4, D6, D7, P2, P4, S6 |
| I-meio | I Interacional | Meio | 0/0 | 0 | 0 | - | - |
| C-adsorbato | C Ambiental | Adsorbato | 0/1 | 0 | 0 | - | C6 |
| C-adsorvente | C Ambiental | Adsorvente | 0/5 | 0 | 0 | - | C1, C3, C5, D5, P7 |
| C-interface | C Ambiental | Interface adsorvente-adsorbato | 0/0 | 0 | 0 | - | - |
| C-meio | C Ambiental | Meio | 0/4 | 0 | 0 | - | C1, C4, C6, P7 |
| O-adsorbato | O Operacional | Adsorbato | 0/0 | 0 | 0 | - | - |
| O-adsorvente | O Operacional | Adsorvente | 0/6 | 0 | 0 | - | C2, C3, C5, C7, D5, P5 |
| O-interface | O Operacional | Interface adsorvente-adsorbato | 0/0 | 0 | 0 | - | - |
| O-meio | O Operacional | Meio | 0/6 | 0 | 0 | - | C7, D3, D6, D7, P1, S5 |

Cobertura media dos 28 cruzamentos: 0.1071. Cruzamentos com dado: 3 de 28. Ausencia de dado nao recebe peso: a celula fica sem indice.

## 3.2 Peso dos descritores

| Codigo | Descritor | Cruzamento | Estado | Valor | Unidade | Peso | Qualidade | Pertinencia | Utilidade | Redundancia |
|---|---|---|---|---|---|---|---|---|---|---|
| P6 | Condutividade / banda proibida | P-adsorvente | estimado | 2 | eV | 1 | 0.4 | 0.4286 | 0 | 0 |
| S3 | Area superficial especifica (BET) | D-adsorvente | presente | 1262 | m2/g | 0.5714 | 0.85 | 0.5714 | 1 | 0 |
| S4 | Volume e distribuicao de poros | D-adsorvente | presente | 0.58 | cm3/g | 0.4286 | 0.85 | 0.4286 | 1 | 0 |
| S3 | Area superficial especifica (BET) | I-interface | presente | 1262 | m2/g | 0.5714 | 0.85 | 0.5714 | 1 | 0 |
| S4 | Volume e distribuicao de poros | I-interface | presente | 0.58 | cm3/g | 0.4286 | 0.85 | 0.4286 | 1 | 0 |

Metodo: peso = qualidade(estado) x pertinencia(selecionar) x utilidade(entropia) x (1 - redundancia); peso = bruto / soma(bruto) dentro do cruzamento. descritor sem dado recebe peso 0 e entra em `lacunas`: ausencia nunca vira zero nem peso artificial.

## 3.3 Caracterizacao dos quatro componentes

_Nenhum parametro de componente registrado._

## 4. Descritores selecionados

_Protocolo nao montado._

## 5. Dados e origens

### KL-KOH-1:1

| Propriedade | Valor | Unidade | Origem | Metodo |
|---|---|---|---|---|
| area_superficial | 1262 | m2/g | Brazil et al., 2026 | - |
| volume_poros | 0.58 | cm3/g | Brazil et al., 2026 | - |
| qmax | 100 | mg/g | Brazil et al., 2026 | - |
| PZC | - | pH | Não reportado | - |
| KL | - | L/mg | Não reportado | - |
| area_superficial | 1262 | m2/g | - | BET N2 |
| volume_poros | 0.58 | cm3/g | - | - |
| area_superficial | 1262 | m2/g | Brazil et al., 2026 | - |
| volume_poros | 0.58 | cm3/g | Brazil et al., 2026 | - |
| qmax | 100 | mg/g | Brazil et al., 2026 | - |
| PZC | - | pH | Não reportado | - |
| KL | - | L/mg | Não reportado | - |
| area_superficial | 1262 | m2/g | - | BET N2 |
| volume_poros | 0.58 | cm3/g | - | - |
| area_superficial | 1262 | m2/g | Brazil et al., 2026 | BET N2 |
| volume_de_poros | 0.58 | cm3/g | Brazil et al., 2026 | - |
| capacidade_adsorcao | 100 | mg/g | Brazil et al., 2026 | - |
| area_superficial | 1262 | m2/g | Brazil et al., 2026 | BET N2 |
| volume_de_poros | 0.58 | cm3/g | Brazil et al., 2026 | - |
| capacidade_adsorcao | 100 | mg/g | Brazil et al., 2026 | - |

### KL-KOH-2:1

| Propriedade | Valor | Unidade | Origem | Metodo |
|---|---|---|---|---|
| area_superficial | 963 | m2/g | Brazil et al., 2026 | - |
| volume_poros | 0.49 | cm3/g | Brazil et al., 2026 | - |
| qmax | 100 | mg/g | Brazil et al., 2026 | - |
| PZC | - | pH | Não reportado | - |
| KL | - | L/mg | Não reportado | - |
| area_superficial | 963 | m2/g | - | BET N2 |
| volume_poros | 0.49 | cm3/g | - | - |
| area_superficial | 963 | m2/g | Brazil et al., 2026 | - |
| volume_poros | 0.49 | cm3/g | Brazil et al., 2026 | - |
| qmax | 100 | mg/g | Brazil et al., 2026 | - |
| PZC | - | pH | Não reportado | - |
| KL | - | L/mg | Não reportado | - |
| area_superficial | 963 | m2/g | - | BET N2 |
| volume_poros | 0.49 | cm3/g | - | - |
| area_superficial | 963 | m2/g | Brazil et al., 2026 | BET N2 |
| volume_de_poros | 0.49 | cm3/g | Brazil et al., 2026 | - |
| capacidade_adsorcao | 100 | mg/g | Brazil et al., 2026 | - |
| area_superficial | 963 | m2/g | Brazil et al., 2026 | BET N2 |
| volume_de_poros | 0.49 | cm3/g | Brazil et al., 2026 | - |
| capacidade_adsorcao | 100 | mg/g | Brazil et al., 2026 | - |

## 6. Evidencias e referencias

_Nenhuma evidencia recuperada._

## 7. Simuladores

| Simulador | Estado | Duracao (s) | Observacao |
|---|---|---|---|
| superficie | ok | 0.114 | - |
| nano | bloqueado_por_parametros | - | - |
| cristalografia | ok_com_aproximacao | 0.124 | - |
| cfd | ok | 0.001 | - |
| dft | ok | 0.001 | - |
| superficie | ok | 0.001 | - |
| nano | bloqueado_por_parametros | - | - |
| cristalografia | ok_com_aproximacao | 0.001 | - |
| cfd | ok | 0.001 | - |
| dft | ok | 0.001 | - |

## 8. Parametros de entrada

| Simulador | Parametro | Valor |
|---|---|---|
| superficie | parametro_rede | 3.5 |
| superficie | densidade | 1000 |
| superficie | velocidade | 0.01 |
| superficie | diametro | 0.005 |
| superficie | viscosidade | 0.001 |
| superficie | material | C |
| superficie | area_m2g | 1262 |
| nano | parametro_rede | 3.5 |
| nano | densidade | 1000 |
| nano | velocidade | 0.01 |
| nano | diametro | 0.005 |
| nano | viscosidade | 0.001 |
| nano | material | C |
| nano | area_m2g | 1262 |
| cristalografia | parametro_rede | 3.5 |
| cristalografia | densidade | 1000 |
| cristalografia | velocidade | 0.01 |
| cristalografia | diametro | 0.005 |
| cristalografia | viscosidade | 0.001 |
| cristalografia | material | C |
| cristalografia | area_m2g | 1262 |
| cfd | parametro_rede | 3.5 |
| cfd | densidade | 1000 |
| cfd | velocidade | 0.01 |
| cfd | diametro | 0.005 |
| cfd | viscosidade | 0.001 |
| cfd | material | C |
| cfd | area_m2g | 1262 |
| dft | parametro_rede | 3.5 |
| dft | densidade | 1000 |
| dft | velocidade | 0.01 |
| dft | diametro | 0.005 |
| dft | viscosidade | 0.001 |
| dft | material | C |
| dft | area_m2g | 1262 |
| superficie | parametro_rede | 3.5 |
| superficie | densidade | 1000 |
| superficie | velocidade | 0.01 |
| superficie | diametro | 0.005 |
| superficie | viscosidade | 0.001 |
| superficie | material | C |
| superficie | area_m2g | 963 |
| nano | parametro_rede | 3.5 |
| nano | densidade | 1000 |
| nano | velocidade | 0.01 |
| nano | diametro | 0.005 |
| nano | viscosidade | 0.001 |
| nano | material | C |
| nano | area_m2g | 963 |
| cristalografia | parametro_rede | 3.5 |
| cristalografia | densidade | 1000 |
| cristalografia | velocidade | 0.01 |
| cristalografia | diametro | 0.005 |
| cristalografia | viscosidade | 0.001 |
| cristalografia | material | C |
| cristalografia | area_m2g | 963 |
| cfd | parametro_rede | 3.5 |
| cfd | densidade | 1000 |
| cfd | velocidade | 0.01 |
| cfd | diametro | 0.005 |
| cfd | viscosidade | 0.001 |
| cfd | material | C |
| cfd | area_m2g | 963 |
| dft | parametro_rede | 3.5 |
| dft | densidade | 1000 |
| dft | velocidade | 0.01 |
| dft | diametro | 0.005 |
| dft | viscosidade | 0.001 |
| dft | material | C |
| dft | area_m2g | 963 |

## 9. Resultados

### superficie

```json
{
  "simulador": "Superficie",
  "dominio": "Quimica - Superficie",
  "area_m2g": 1262.0,
  "validacao": "Area superficial"
}
```

### cristalografia (aproximado: padrao interno do motor)

```json
{
  "simulador": "Cristalografia (Bragg)",
  "dominio": "Materiais - Cristalografia",
  "parametro_rede_m": 3.5,
  "angulo_graus": 29.999999999999996,
  "d_espacamento_m": 1.5400000000000004e-10,
  "lambda_X_nm": 0.154,
  "validacao": "Espacamento interplanar: 1.540 A"
}
```

### cfd

```json
{
  "simulador": "CFD (OpenFOAM)",
  "dominio": "Engenharia - Fluidos",
  "densidade_kgm3": 1000,
  "velocidade_ms": 0.01,
  "diametro_m": 0.005,
  "viscosidade_Pas": 0.001,
  "Reynolds": 50.0,
  "regime": "laminar",
  "validacao": "Reynolds: 50 (laminar)"
}
```

### dft

```json
{
  "simulador": "DFT (Quantum ESPRESSO)",
  "dominio": "Materiais - DFT",
  "material": "C",
  "bandgap_eV": 2.0,
  "tipo": "indireto",
  "validacao": "Bandgap de 2.0 eV para C"
}
```

### superficie

```json
{
  "simulador": "Superficie",
  "dominio": "Quimica - Superficie",
  "area_m2g": 963.0,
  "validacao": "Area superficial"
}
```

### cristalografia (aproximado: padrao interno do motor)

```json
{
  "simulador": "Cristalografia (Bragg)",
  "dominio": "Materiais - Cristalografia",
  "parametro_rede_m": 3.5,
  "angulo_graus": 29.999999999999996,
  "d_espacamento_m": 1.5400000000000004e-10,
  "lambda_X_nm": 0.154,
  "validacao": "Espacamento interplanar: 1.540 A"
}
```

### cfd

```json
{
  "simulador": "CFD (OpenFOAM)",
  "dominio": "Engenharia - Fluidos",
  "densidade_kgm3": 1000,
  "velocidade_ms": 0.01,
  "diametro_m": 0.005,
  "viscosidade_Pas": 0.001,
  "Reynolds": 50.0,
  "regime": "laminar",
  "validacao": "Reynolds: 50 (laminar)"
}
```

### dft

```json
{
  "simulador": "DFT (Quantum ESPRESSO)",
  "dominio": "Materiais - DFT",
  "material": "C",
  "bandgap_eV": 2.0,
  "tipo": "indireto",
  "validacao": "Bandgap de 2.0 eV para C"
}
```

### Prova de conceito

```json
{
  "demonstravel": false,
  "passos_ok": 2,
  "passos_total": 6,
  "lacunas": [
    "protocolo",
    "calculo_isoterma",
    "evidencias",
    "comparacao"
  ],
  "calculo": null
}
```

## 10. Comparacao com a literatura

_Nenhuma comparacao com a literatura registrada._

## 11. Avaliacao de viabilidade

**Pontuacao:** 29.57 (requer_dados)

| Criterio | Peso | Fracao | Contribuicao |
|---|---|---|---|
| dados_descritores | 25 | 0.143 | 3.57 |
| evidencia_cientifica | 20 | 0 | 0 |
| simulacao_executada | 20 | 0.8 | 16 |
| validacao_externa | 15 | 0 | 0 |
| caracterizacao_material | 10 | 1 | 10 |
| risco_e_conformidade | 10 | 0 | 0 |

**Lacunas:** 24 descritores sem dado na matriz; evidencias insuficientes (0; minimo 3); risco e conformidade incompletos (P7, C1, C6)

**Riscos:** lixiviacao/solubilidade nao avaliada; toxicidade do material nao declarada; conformidade normativa nao verificada

**Recomendacoes:** priorizar ensaios de desempenho (dimensao D3); executar busca bibliografica antes de concluir viabilidade

## 12. Limitacoes

- 4 descritores da matriz sem dado medido.
- Nenhuma evidencia bibliografica recuperada.
- Simuladores sem resultado: nano, cristalografia, nano, cristalografia.
- Sem comparacao numerica com a literatura.
- Resultados computacionais nao substituem ensaio experimental.

## 13. Conclusao

A pesquisa esta classificada como **requer_dados** com pontuacao 29.57 de 100. Prova de conceito computacional: parcial.

## 14. Recomendacoes

- priorizar ensaios de desempenho (dimensao D3)
- executar busca bibliografica antes de concluir viabilidade
