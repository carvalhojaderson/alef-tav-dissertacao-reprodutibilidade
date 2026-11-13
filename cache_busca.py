# ============================================================
#   ALEF-TAV - CACHE DE BUSCAS (economiza APIs)
# ============================================================
import os
import json
import hashlib
import time

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".alef_tav_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

TTL = 3600  # 1 hora


def _hash_query(query):
    return hashlib.md5(query.lower().strip().encode("utf-8")).hexdigest()[:16]


def _caminho(query):
    return os.path.join(CACHE_DIR, _hash_query(query) + ".json")


def get(query):
    """Recupera resultado do cache se existir e nao expirou."""
    c = _caminho(query)
    if not os.path.isfile(c):
        return None
    try:
        with open(c, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if time.time() - dados.get("ts", 0) > TTL:
            os.unlink(c)
            return None
        return dados.get("resultado")
    except Exception:
        return None


def set(query, resultado):
    """Salva resultado no cache."""
    try:
        with open(_caminho(query), "w", encoding="utf-8") as f:
            json.dump({
                "ts": time.time(),
                "query": query,
                "resultado": resultado,
            }, f, ensure_ascii=False)
    except Exception:
        pass


def limpar():
    """Remove todo o cache."""
    for f in os.listdir(CACHE_DIR):
        if f.endswith(".json"):
            try:
                os.unlink(os.path.join(CACHE_DIR, f))
            except Exception:
                pass


def tamanho():
    """Quantos itens no cache."""
    try:
        return len([f for f in os.listdir(CACHE_DIR) if f.endswith(".json")])
    except Exception:
        return 0


if __name__ == "__main__":
    print("Cache dir:", CACHE_DIR)
    print("Itens:", tamanho())
# 10/06/2026 13:14:58

# 10/06/2026 13:17:05

# 10/06/2026 13:29:22
