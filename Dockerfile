# Imagem para rodar o backend ambiental como Space INDEPENDENTE.
#
# Contexto de build esperado: esta pasta na raiz do novo Space, com o nucleo
# cientifico ao lado (universal.py, bancos_rest.py, pesquisa_cientifica.py,
# modelos_adsorcao_v2.py, modelos_analiticos_v2.py, nucleo_dados.py,
# exportadores.py, ...) — a pasta e' montada por `preparar_espaco.py`.
#
# Se preferir manter o nucleo em outro diretorio, defina ALEF_TAV_CORE no build.
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ALEF_SEM_PREAQUECER=1 \
    PORT=7860

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Dependencias do nucleo cientifico: `preparar_espaco.py` copia o
# requirements.txt da raiz do projeto para `requirements-nucleo.txt`.
COPY requirements*.txt /app/
RUN if [ -f /app/requirements-nucleo.txt ]; then \
        pip install --no-cache-dir -r /app/requirements-nucleo.txt; \
    fi

COPY . /app

# diretorio de dados persistente (o Space monta /data quando o storage esta ativo)
RUN mkdir -p /data

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
