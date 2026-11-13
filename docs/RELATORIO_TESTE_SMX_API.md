# Relatório do teste de API — fluxo SMX (sulfametoxazol)

- **Data:** 09/11/2026
- **Script:** `teste_smx_api.py` (648 linhas, `requests`, ASCII-safe no console do Windows)
- **API:** `http://127.0.0.1:7860` (`ambiental_backend.app:app`, uvicorn, SQLite)
- **Comando:** `python teste_smx_api.py --json _smx_resultado.json`
- **Código de saída:** 0 (todas as chamadas HTTP respondidas)
- **Artefatos:** `_smx_log.txt` (saída completa), `_smx_resultado.json` (resultado estruturado)

## Fluxo executado

| Passo | Rota | Resultado |
|---|---|---|
| 0 | `GET /api/health` | estado ok, serviço v1.0.0, banco sqlite, matriz 4 dimensões × 28 descritores |
| 1 | `POST /api/research` | pesquisa criada (`pesq_531f88b620d18602`), pH 5,5 e 25 °C persistidos |
| 2 | `POST /api/research/{id}/materials` | KL-KOH-1:1 → `mat_...` (5 propriedades gravadas) |
| 3 | `POST /api/research/{id}/materials` | KL-KOH-2:1 → `mat_...` (5 propriedades gravadas) |
| 4 | `POST /api/research/{id}/adsorbent` (A) | S3 = 1262 m²/g; modelos bloqueados; compatibilidade indeterminada |
| 5 | `POST /api/research/{id}/adsorbent` (B) | S3 = 963 m²/g; modelos bloqueados; compatibilidade indeterminada |
| 6 | resumo comparativo | empate: 1 de 28 descritores com dado em cada material |

## O que o sistema devolveu (e estava certo em devolver)

1. **Langmuir → `bloqueado_por_parametros`** (`faltando: qmax, KL`). Freundlich → `bloqueado_por_parametros` (`faltando: Kf, n`). Nenhum valor foi inventado.
2. **S3 preenchido com o dado declarado** (1262 e 963 m²/g, estado `presente`, fonte "propriedade declarada no pedido").
3. **Compatibilidade `indeterminado`**, com `faltando: P2 (PZC), classe do contaminante` — PZC não reportado na fonte, como no pedido.
4. **Lacunas** (iguais nos dois materiais): S1, P2, D1, D2, D3, D6, D7, C1, C6.
5. **Cobertura 7D×4:** D1 = 1/7, D2 = D3 = D4 = 0/7 → 1/28 (3,57 %) em ambos. Sem D1/D2 não há base para declarar um material melhor.

## Achados de QA (divergências e pontos de atenção)

1. **`qmax` cadastrado em `POST /materials` não chega ao modelo.** A propriedade fica registrada em `amb_propriedades`, mas o modelo lê o descritor `D1`, que só é preenchido por `caracterizacao`/`propriedades` no corpo do `POST /adsorbent`. Por isso o Langmuir acusa falta de **qmax e KL**, e não só de KL. O script sinaliza isso como `[ATENCAO]`.
2. **`volume_poros` não mapeia para o descritor S4.** O mapa `CARACTERIZACAO` usa a chave `volumedeporos`; o nome normalizado de `volume_poros` é `volumeporos`, que não existe. Resultado: S4 fica ausente e a propriedade cai em `nao_mapeadas` (sinalizado como `[ATENCAO]`).
3. **A classe iônica declarada no texto do contaminante é ignorada.** `classe_contaminante()` usa vocabulário fechado (`anion_organico` ← "corante anionico", "eosina", "acido humico"...), então `"...classe iônica: ânion orgânico"` retorna `nao_classificado`. A compatibilidade fica indeterminada por dois motivos (PZC e classe), não por um.
4. **Simuladores reportaram `indisponivel`** nesta cópia local porque o núcleo `universal.py` não está presente (`motores do nucleo: universal: ausente`). Com o núcleo no lugar, `superficie` executaria e regravaria S3 a partir de `area_m2g`; `nano`, `cristalografia` e `dft` continuariam bloqueados por falta de `diametro_nm`, `parametro_rede` e `material` — comportamento correto, e o script imprime cada `faltando`.

## Ajustes de ambiente necessários para subir a API nesta máquina

1. Os arquivos do backend estavam soltos na pasta, três com nome quebrado (`__init__txt.py`, `adsorventes.txt.py`, `.txt.py`). Foi criado o pacote `ambiental_backend/` com cópia fiel e nomes corrigidos (`__init__.py`, `adsorventes.py`, `adaptadores.py`); nenhum original foi editado.
2. `analises_experimentais.py` é um carregador de bytecode CPython 3.10 e o `.pyc` não existe nesta cópia, o que impedia o import da aplicação inteira. Para o teste, o módulo foi substituído por um stub local (não reimplementa nenhuma análise: qualquer uso levanta `RuntimeError`). O carregador original está preservado em `ambiental_backend/analises_experimentais.pycshim`:

   ```powershell
   Copy-Item ambiental_backend\analises_experimentais.pycshim `
             ambiental_backend\analises_experimentais.py -Force
   ```

3. O banco usado foi o fallback SQLite do próprio backend (`dados_ambiental/ambiental.db`), porque `nucleo_dados` não está disponível nesta cópia; as 19 tabelas `amb_*` foram criadas de forma idempotente.
