import math
import re
import unicodedata


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _numero(padroes, texto):
    for padrao in padroes:
        m = re.search(padrao, texto)
        if m:
            return float(m.group(1).replace(",", "."))
    return None


def executar_modelo_adsorcao(pergunta, parametros=None):
    """Calculadora analitica isolada para isotermas de adsorcao."""
    texto = normalizar(pergunta)

    if not any(p in texto for p in (
        "adsorcao", "adsorvente", "isoterma", "langmuir", "freundlich"
    )):
        return {
            "status": "nao_reconhecido",
            "mensagem": "A consulta nao parece ser sobre isotermas de adsorcao."
        }

    p = dict(parametros or {})

    if "langmuir" in texto:
        modelo = "langmuir"
    elif "freundlich" in texto:
        modelo = "freundlich"
    else:
        return {
            "status": "modelo_ausente",
            "mensagem": "Informe se deseja Langmuir ou Freundlich."
        }

    if modelo == "langmuir":
        p.setdefault("qmax", _numero([
            r"(?:capacidade maxima|qmax|q max)\s*(?:de|=|:)?\s*(-?\d+(?:[.,]\d+)?)"
        ], texto))
        p.setdefault("KL", _numero([
            r"(?:constante de langmuir|constante|kl)\s*(?:de|=|:)?\s*(-?\d+(?:[.,]\d+)?)"
        ], texto))
    else:
        p.setdefault("Kf", _numero([
            r"(?:kf|constante de freundlich)\s*(?:de|=|:)?\s*(-?\d+(?:[.,]\d+)?)"
        ], texto))
        p.setdefault("n", _numero([
            r"(?:expoente|parametro n|n)\s*(?:de|=|:)?\s*(-?\d+(?:[.,]\d+)?)"
        ], texto))

    concentracao = _numero([
        r"(?:concentracao(?: de equilibrio)?|ce)\s*(?:de|=|:)?\s*(-?\d+(?:[.,]\d+)?)"
    ], texto)

    if concentracao is None:
        concentracao = _numero([
            r"para concentracao\s+(-?\d+(?:[.,]\d+)?)"
        ], texto)

    # C0 e Ce sao grandezas distintas.
    # Identificar C0 nao autoriza usa-lo automaticamente como Ce.
    concentracao_inicial = _numero([
        r"(?:concentracao inicial|concentracao de entrada|c0)\s*(?:de|=|:)?\s*(-?\d+(?:[.,]\d+)?)"
    ], texto)

    if concentracao_inicial is not None:
        p.setdefault("C0", concentracao_inicial)

    p.setdefault("Ce", concentracao)

    obrigatorios = ["qmax", "KL", "Ce"] if modelo == "langmuir" else ["Kf", "n", "Ce"]
    faltantes = [k for k in obrigatorios if p.get(k) is None]

    if faltantes:
        return {
            "status": "parametro_ausente",
            "modelo": modelo,
            "parametros_necessarios": obrigatorios,
            "parametros_ausentes": faltantes,
            "parametros_recebidos": p,
            "fonte": "analitico"
        }

    try:
        valores = {k: float(p[k]) for k in obrigatorios}
    except (TypeError, ValueError):
        return {"status": "parametro_invalido", "modelo": modelo}

    if any(not math.isfinite(v) for v in valores.values()):
        return {"status": "parametro_invalido", "modelo": modelo}

    if valores["Ce"] < 0:
        return {"status": "parametro_invalido", "mensagem": "Ce nao pode ser negativo."}

    if modelo == "langmuir":
        if valores["qmax"] <= 0 or valores["KL"] <= 0:
            return {
                "status": "parametro_invalido",
                "mensagem": "qmax e KL devem ser positivos."
            }
        q = valores["qmax"] * valores["KL"] * valores["Ce"] / (
            1 + valores["KL"] * valores["Ce"]
        )
        equacao = "qe = qmax * KL * Ce / (1 + KL * Ce)"
    else:
        if valores["Kf"] <= 0 or valores["n"] <= 0:
            return {
                "status": "parametro_invalido",
                "mensagem": "Kf e n devem ser positivos."
            }
        q = valores["Kf"] * valores["Ce"] ** (1 / valores["n"])
        equacao = "qe = Kf * Ce ** (1/n)"

    return {
        "status": "calculado",
        "modelo": modelo,
        "equacao": equacao,
        "parametros": valores,
        "qe_mg_g": q,
        "fonte": "analitico",
        "nota": (
            "Calculo matematico do modelo; nao representa validacao "
            "experimental nem garante ajuste aos dados reais."
        )
    }
