# Licenças e condições de uso

Este repositório reúne material produzido pelo autor da dissertação para fins de
**verificação e reprodução acadêmica**. Ele não é um produto de software
distribuído e não substitui a versão operacional da plataforma ALEF-TAV.

## 1. Código-fonte (`*.py`, `Dockerfile`, scripts de execução)

- Autoria: o autor da dissertação (conta GitHub `carvalhojaderson`, Space
  `Jaderson32/alef-tav-backend`).
- Não havia arquivo de licença no material original. Este repositório é
  publicado com **permissão expressa do autor para leitura, execução e
  verificação dos cálculos** por pesquisadores, avaliadores e revisores.
- Reutilização do código em outros produtos, redistribuição comercial ou
  publicação derivada **não estão autorizadas** por este documento.
- Condição vigente, sem item em aberto: **não há licença aberta** e este arquivo
  é a única fonte das condições de uso. Caso o autor decida adotar licença
  aberta formal (por exemplo, MIT para código e CC BY 4.0 para texto), basta
  substituir esta seção — nenhum outro arquivo precisa mudar.

## 2. Dados de entrada

- Os valores de caracterização usados no estudo de caso (área BET 1262 m²/g e
  963 m²/g; volume de poros 0,58 cm³/g e 0,49 cm³/g; qmax 100 mg/g) são
  **dados publicados na literatura**, atribuídos à fonte citada nos scripts e
  nos relatórios como *Brazil et al., 2026*. O uso aqui é de citação e
  comparação científica; a licença dos dados originais é a da publicação de
  origem.
- As propriedades do sulfametoxazol (fórmula C10H11N3O3S, massa molar
  253,28 g/mol, pKa 1,6 e 5,7, log Kow 0,89) são valores de referência
  consolidados, declarados como `importado` no código.
- Não há dados pessoais, dados de terceiros sob confidencialidade, dados
  proprietários ou bases pagas redistribuídas neste repositório.

## 3. Resultados computacionais

- Os arquivos de resultado (`*.json`, `*.csv`, `*.md`, bancos SQLite e logs)
  são **saídas originais** das execuções descritas em
  `docs/VERSAO_E_RASTREABILIDADE.md`. Foram copiados sem edição; nenhum valor
  foi recalculado, arredondado ou corrigido à mão.

## 4. Dependências de terceiros

As bibliotecas listadas em `requirements.txt` e `requirements-nucleo.txt`
(FastAPI, SQLAlchemy, NumPy, SciPy, entre outras) **não são redistribuídas**
aqui; cada uma mantém a própria licença, e a instalação ocorre pelo gestor de
pacotes do usuário.

## 5. Como citar

Ver `CITATION.cff` e a seção "Como citar" do `README.md`.
