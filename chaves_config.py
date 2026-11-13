# chaves_config.py - Le chaves de env (HF Spaces)
import os


def _get(nome, default=""):
    return os.environ.get(nome, default)


CHAVES = {
    "NVIDIA_API_KEY": _get("NVIDIA_API_KEY"),
    "GROQ_API_KEY": _get("GROQ_API_KEY"),
    "SCOPUS_API_KEY": _get("SCOPUS_API_KEY") or _get("ELSEVIER_API_KEY"),
    "GOOGLE_API_KEY": _get("GOOGLE_API_KEY"),
    "INSTITUTIONAL_EMAIL": _get("INSTITUTIONAL_EMAIL", "alef@tav.br"),
}


def get(nome, default=""):
    return CHAVES.get(nome, default)
# 10/06/2026 11:39:30

# 10/06/2026 11:46:12

# 10/06/2026 11:56:54

# 10/06/2026 12:01:03

# 10/06/2026 13:14:58

# 10/06/2026 13:17:05

# 10/06/2026 13:29:22
