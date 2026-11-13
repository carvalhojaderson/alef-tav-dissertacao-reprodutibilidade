# Citação do pacote na dissertação

Registro de como o repositório `alef-tav-dissertacao-reprodutibilidade` passou a
ser citado no texto da dissertação, para que a citação possa ser conferida e
reproduzida sem depender de memória do autor.

## 1. O que foi alterado

| Item | Valor |
|---|---|
| Documento editado | `dissertacao_final_corrigida_com_repositorio.docx` |
| Origem | `dissertacao_final_corrigida.docx` (preservado, não sobrescrito) |
| Data da inserção | 13/11/2026 |
| Parágrafos antes / depois | 494 / 497 |
| Ocorrências do endereço do repositório | 2 (corpo + referência) |

Foram feitas **três inserções**: dois parágrafos ao final da seção 3.11.6 e uma
entrada na lista de REFERÊNCIAS. Nenhum outro trecho do texto foi reescrito. A
única correção adicional foi em uma referência já existente (FOREST et al.,
2019), que trazia o fragmento corrompido `small data do subconjunto curadosets`
e passou a `small data sets` — correção textual, sem efeito sobre qualquer valor
numérico.

## 2. Citação no texto — seção 3.11.6 (*Rastreabilidade e reprodutibilidade*)

Primeiro parágrafo inserido:

> Disponibilização do pacote de reprodutibilidade. Além dos mecanismos internos
> de rastreabilidade, o material necessário à verificação independente dos
> resultados desta dissertação foi reunido em um repositório público denominado
> ALEF-TAV — material de reprodutibilidade da dissertação (CARVALHO, 2026),
> disponível em
> https://github.com/carvalhojaderson/alef-tav-dissertacao-reprodutibilidade,
> com a versão exata utilizada neste trabalho fixada na tag
> snapshot-2026-11-11. O pacote reúne o código-fonte dos módulos efetivamente
> executados, inclusive o bytecode CPython 3.10 do módulo recuperado, os 28
> descritores da matriz 7D×4, a base de dados de entrada, os resultados
> computacionais publicados, os scripts de cálculo do estudo de caso, a suíte de
> testes e o arquivo MANIFEST_SHA256.txt, que registra o hash SHA-256 de cada
> arquivo publicado.

Segundo parágrafo inserido:

> Verificação da integridade e da reprodutibilidade. A integridade do snapshot é
> conferida pelo script verificar_integridade.ps1, que recalcula os hashes
> SHA-256 e os compara com o manifesto publicado. A reprodutibilidade foi
> testada por reexecução dos cálculos em cópia limpa do repositório, obtendo-se
> semelhança de cosseno idêntica à publicada — 0,9981 no perfil completo, 0,9826
> no lastro, 0,9999 no perfil por componente, 0,7913 no adsorbato A e 0,7944 no
> adsorbato B — e coincidência nos valores da matriz KL-KOH, com uma única
> divergência conhecida e documentada no descritor P1 (densidade), atribuída à
> leitura do parâmetro de rede em unidade incorreta pelo simulador de
> cristalografia. Dessa forma, os cálculos desta dissertação podem ser
> reconferidos por terceiros sem dependência do ambiente computacional original.

## 3. Referência — lista de REFERÊNCIAS

Inserida em ordem alfabética, entre CALUS-MAKOWSKA (2024) e CAZETTA (2011):

> CARVALHO, J. P. ALEF-TAV: material de reprodutibilidade da dissertação de
> mestrado. Versão snapshot-2026-11-11. Curitiba: [s. n.], 2026. Disponível em:
> https://github.com/carvalhojaderson/alef-tav-dissertacao-reprodutibilidade.
> Acesso em: 13 nov. 2026.

A citação no texto usa a forma autor-data `(CARVALHO, 2026)`, coerente com a
entrada acima.

## 4. Como conferir no documento

1. Abrir `dissertacao_final_corrigida_com_repositorio.docx`.
2. Localizar `3.11.6` — os dois parágrafos novos são os últimos da seção, antes
   de `3.11.7 Verificação de software da v2`.
3. Buscar `carvalhojaderson` — duas ocorrências (parágrafo do corpo e referência).

## 5. Como citar o pacote em outros trabalhos

`CITACAO.bib` traz duas entradas:

* `carvalho2026aleftavreprod` — o pacote de reprodutibilidade (este repositório);
* `carvalho2026dissertacao` — a dissertação, com o endereço do pacote no campo
  `note`.

O `CITATION.cff` atende ao botão *Cite this repository* do GitHub e já traz o
nome completo do autor (Jáderson de Paula Carvalho) e a instituição (UTFPR,
Programa de Pós-Graduação em Ciência e Tecnologia Ambiental).
