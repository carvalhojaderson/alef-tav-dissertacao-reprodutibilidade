# Segurança, privacidade e licenças

## 1. Auditoria executada antes da publicação

Data: 11/11/2026. Escopo varrido:

* `C:\Users\PC\hf_upload` (raiz, `docs/`, `ambiental_backend/`);
* `C:\Users\PC\Desktop\Projetos\Nova pasta` (raiz, pacote, bancos SQLite);
* o próprio snapshot publicado (verificação final antes do *push*).

Padrões procurados: tokens `hf_`, `ghp_`, `github_pat_`, `sk-`, `AIza`,
`AKIA`, `xoxb-`, cabeçalhos `BEGIN ... PRIVATE KEY`, além de nomes de variáveis
com `token`, `secret`, `senha`, `password`, `api_key`, `chave`, `credential`.

## 2. Achados

| # | Achado | Tratamento |
|---|---|---|
| 1 | `hf_upload\.env` contém **chaves reais** (linhas 7 e 37), incluindo `DEEPSEEK_API_KEY` e `HUGGINGFACE_API_KEY` | arquivo **não publicado**; apenas `.env.example` (sem valores) foi incluído; `.gitignore` bloqueia `.env*` |
| 2 | Oito scripts de rascunho na raiz de `hf_upload` têm credenciais literais no código (`SENHA = "..."`, `TOKEN = "..."`): `test_llm_client.py`, `test_mcp_alef.py`, `test_plataforma_ak.py`, `_continuidade_v4.py`, `_evidencias_j_esg.py`, `_prova_ia_app.py`, `_prova_llm_real.py`, `_smoke_esg.py` | **não publicados** (não integram o cálculo da dissertação) |
| 3 | Bancos `ambiental.db` (2 arquivos, 20 tabelas cada) | auditados: nenhuma coluna de credencial; colunas chamadas `chave` guardam códigos de descritor (S3, P2…); varredura de valores textuais sem padrões de segredo |
| 4 | Documentos técnicos (13 arquivos `.md`) | sem segredos e sem endereços de e-mail |
| 5 | `chaves_config.py` | lê apenas `os.environ` (`NVIDIA_API_KEY`, `GROQ_API_KEY`, `SCOPUS_API_KEY`, `GOOGLE_API_KEY`); nenhum valor embutido |
| 6 | Dados pessoais | não há nome de paciente, CPF, e-mail de terceiro, endereço ou dado sensível nos arquivos publicados |

## 3. Recomendações ao autor

1. **Rotacionar** as chaves que estavam no `.env` (DEEPSEEK e HUGGING FACE) —
   elas nunca foram publicadas aqui, mas circularam em cópias locais.
2. Manter `.env` fora de qualquer repositório e de qualquer ZIP compartilhado.
3. Se o Space for tornado público, revisar os *Secrets* e as variáveis do
   ambiente antes.
4. Antes de reutilizar os scripts de rascunho, remover as credenciais
   embutidas e trocá-las por leitura de ambiente.

## 4. Licenças

O detalhamento está em `LICENCA.md`:

* **código**: autoria do autor da dissertação; publicado com permissão expressa
  para leitura, execução e verificação acadêmica; reutilização comercial não
  autorizada por este documento;
* **dados de entrada**: valores de literatura atribuídos a *Brazil et al.,
  2026* (citados no código e nos relatórios) e propriedades de referência do
  sulfametoxazol; nenhum dado proprietário redistribuído;
* **dependências**: não redistribuídas, apenas declaradas em
  `requirements*.txt`;
* **condição vigente**: não há licença aberta; as condições de uso são as de
  `LICENCA.md` (permissão para leitura, execução e verificação acadêmica). Se o
  autor adotar MIT / CC BY 4.0 no futuro, `LICENCA.md` é o único arquivo a
  alterar.
