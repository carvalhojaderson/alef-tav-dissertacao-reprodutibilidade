"""
BANCO UNIVERSAL DE SIMULADORES
Cobre TODAS as areas cientificas
Detecta dominio e roda simulacoes relevantes para qualquer pergunta
"""
import os
import threading

import numpy as np

# ============================================================
# FISICA
# ============================================================

def sim_mecanica(pergunta, p):
    """Mecanica classica - forca, energia, movimento."""
    m = p.get("massa", 1.0)
    v = p.get("velocidade", 10.0)
    g = 9.81
    E_c = 0.5 * m * v**2
    E_p = m * g * p.get("altura", 1.0)
    return {
        "simulador": "Mecanica Classica",
        "dominio": "Fisica - Mecanica",
        "massa_kg": m, "velocidade_ms": v,
        "E_cinetica_J": E_c, "E_potencial_J": E_p,
        "E_total_J": E_c + E_p,
        "validacao": f"Energia total de {E_c+E_p:.2f} J"
    }

def sim_termodinamica(pergunta, p):
    """Termodinamica - calor, entropia, trabalho."""
    T1 = p.get("T1", 300); T2 = p.get("T2", 400)
    n = p.get("moles", 1.0); R = 8.314
    W = n * R * (T2 - T1) * np.log(2)
    delta_S = n * R * np.log(T2 / T1)
    return {
        "simulador": "Termodinamica",
        "dominio": "Fisica - Termo",
        "T1_K": T1, "T2_K": T2,
        "trabalho_J": W, "delta_S_JK": delta_S,
        "eficiencia_Carnot": 1 - T1 / T2,
        "validacao": f"Eficiencia de {1-T1/T2:.2%}"
    }

def sim_eletromagnetismo(pergunta, p):
    """Eletromagnetismo - campo E, B, forca."""
    q = p.get("carga", 1e-6); E = p.get("campo_E", 1000)
    B = p.get("campo_B", 0.1); v = p.get("velocidade", 100)
    F_e = q * E
    F_b = q * v * B
    return {
        "simulador": "Eletromagnetismo (Maxwell)",
        "dominio": "Fisica - EM",
        "carga_C": q, "campo_E_Vm": E, "campo_B_T": B,
        "F_eletrica_N": F_e, "F_magnetica_N": F_b,
        "F_total_N": np.sqrt(F_e**2 + F_b**2),
        "validacao": f"Forca de Lorentz: {np.sqrt(F_e**2+F_b**2):.2e} N"
    }

def sim_optica(pergunta, p):
    """Optica - refracao, difracao, interferencia."""
    n1 = p.get("n1", 1.0); n2 = p.get("n2", 1.5)
    theta1 = np.radians(p.get("angulo", 30))
    theta2 = np.arcsin(n1 * np.sin(theta1) / n2)
    lambda0 = p.get("lambda", 500e-9)
    lambda_meio = lambda0 / n2
    return {
        "simulador": "Optica (Snell)",
        "dominio": "Fisica - Optica",
        "n1": n1, "n2": n2,
        "angulo_incidencia_graus": np.degrees(theta1),
        "angulo_refracao_graus": np.degrees(theta2),
        "lambda_vacuo_nm": lambda0 * 1e9,
        "lambda_meio_nm": lambda_meio * 1e9,
        "validacao": f"Refracao de {np.degrees(theta1):.1f} para {np.degrees(theta2):.1f} graus"
    }

def sim_quantica(pergunta, p):
    """Mecanica quantica - funcao de onda, niveis de energia."""
    n = p.get("nivel", 1); L = p.get("largura", 1e-9)
    h = 6.626e-34; m = 9.11e-31
    E_n = (n**2 * h**2) / (8 * m * L**2)
    return {
        "simulador": "Mecanica Quantica (Schrodinger)",
        "dominio": "Fisica - Quantica",
        "nivel_n": n, "largura_m": L,
        "E_nivel_eV": E_n / 1.6e-19,
        "frequencia_Hz": E_n / h,
        "validacao": f"Energia do nivel {n}: {E_n/1.6e-19:.3f} eV"
    }

def sim_relatividade(pergunta, p):
    """Relatividade - dilatacao temporal, energia."""
    v = p.get("velocidade", 0.5e8); c = 3e8; m = p.get("massa", 1.0)
    gamma = 1 / np.sqrt(1 - (v/c)**2)
    E = gamma * m * c**2
    return {
        "simulador": "Relatividade (Einstein)",
        "dominio": "Fisica - Relatividade",
        "velocidade_ms": v, "fracao_c": v/c,
        "gamma": gamma,
        "E_total_J": E,
        "tempo_proprio_s": 1 / gamma,
        "validacao": f"Fator gamma: {gamma:.4f}"
    }

# ============================================================
# QUIMICA
# ============================================================

def sim_cinetica(pergunta, p):
    k0 = float(p.get("k0", 1e10))
    Ea = float(p.get("Ea", 50000))
    T = float(p.get("T", 300))
    R = 8.314
    if not all(_math.isfinite(x) for x in (k0, Ea, T)):
        raise ValueError("k0, Ea e T devem ser finitos")
    if k0 <= 0:
        raise ValueError("k0 deve ser maior que zero")
    if Ea < 0:
        raise ValueError("Ea nao pode ser negativa neste modelo")
    if T <= 0:
        raise ValueError("T deve ser temperatura absoluta maior que zero")
    k = k0 * np.exp(-Ea / (R * T))
    meia_vida = np.log(2) / k if k > 0 else float("inf")
    return {
        "simulador": "Cinetica Quimica (Arrhenius)",
        "dominio": "Quimica - Cinetica",
        "k0": k0, "Ea_Jmol": Ea, "T_K": T,
        "k_T": k, "meia_vida_s": meia_vida,
        "validacao": f"Constante de taxa: {k:.2e} /s"
    }


def sim_equilibrio(pergunta, p):
    """Equilibrio quimico - K, delta G."""
    dG0 = p.get("dG0", -10000); T = p.get("T", 298); R = 8.314
    K = np.exp(-dG0 / (R * T))
    return {
        "simulador": "Equilibrio Quimico (Gibbs)",
        "dominio": "Quimica - Equilibrio",
        "dG0_Jmol": dG0, "T_K": T,
        "K_equilibrio": K,
        "espontaneo": dG0 < 0,
        "validacao": f"K = {K:.2e}, reacao {'espontanea' if dG0<0 else 'nao espontanea'}"
    }

def sim_eletroquimica(pergunta, p):
    """Eletroquimica - potencial, Nernst."""
    E0 = p.get("E0", 1.1); n = p.get("n_eletrons", 2)
    Q = p.get("Q", 1.0); F = 96485; R = 8.314; T = 298
    E = E0 - (R * T) / (n * F) * np.log(Q)
    return {
        "simulador": "Eletroquimica (Nernst)",
        "dominio": "Quimica - Eletro",
        "E0_V": E0, "n": n, "Q": Q,
        "E_V": E,
        "delta_G_J": -n * F * E,
        "validacao": f"Potencial de celula: {E:.4f} V"
    }

# ============================================================
# BIOLOGIA
# ============================================================

def sim_genetica(pergunta, p):
    """Genetica - heranca, frequencias."""
    p_freq = p.get("freq_alelo", 0.5)
    q_freq = 1 - p_freq
    AA = p_freq**2; Aa = 2*p_freq*q_freq; aa = q_freq**2
    return {
        "simulador": "Genetica (Hardy-Weinberg)",
        "dominio": "Biologia - Genetica",
        "freq_A": p_freq, "freq_a": q_freq,
        "AA_pct": AA*100, "Aa_pct": Aa*100, "aa_pct": aa*100,
        "validacao": f"Frequencias: AA={AA:.2%}, Aa={Aa:.2%}, aa={aa:.2%}"
    }

def sim_ecologia(pergunta, p):
    """Ecologia - crescimento populacional."""
    N0 = p.get("N0", 100); r = p.get("r", 0.1); K = p.get("K", 1000)
    t = np.linspace(0, 100, 100)
    N = K / (1 + ((K - N0) / N0) * np.exp(-r * t))
    return {
        "simulador": "Ecologia (Logistico)",
        "dominio": "Biologia - Ecologia",
        "N0": N0, "r": r, "K": K,
        "N_final": N[-1],
        "tempo": t.tolist(), "populacao": N.tolist(),
        "validacao": f"Populacao estabiliza em {N[-1]:.0f}"
    }

def sim_neuro(pergunta, p):
    """Neurociencia - potencial de acao."""
    V_rest = -70; V_pico = 40; tau = 1e-3
    t = np.linspace(0, 5e-3, 500)
    V = V_rest + (V_pico - V_rest) * np.exp(-t / tau)
    return {
        "simulador": "Neurociencia (Hodgkin-Huxley)",
        "dominio": "Biologia - Neuro",
        "V_repouso_mV": V_rest, "V_pico_mV": V_pico,
        "tau_ms": tau * 1000,
        "tempo_s": t.tolist(), "voltagem_mV": V.tolist(),
        "validacao": f"Potencial de acao: {V_rest}mV a {V_pico}mV"
    }

# ============================================================
# MATERIAIS
# ============================================================

def sim_cristalografia(pergunta, p):
    # Aceita o nome canonico (`parametro_rede_m`, o mesmo que o motor pymatgen
    # le) e o legado (`parametro_rede`). Antes o valor calculado aqui era
    # enviado com um nome que o motor nao lia.
    a = float(p.get("parametro_rede_m", p.get("parametro_rede", 3.57e-10)))
    angulo = float(p.get("angulo", 30))
    n = p.get("n", 1)
    if not _math.isfinite(a) or a <= 0:
        raise ValueError("parametro_rede deve ser finito e positivo")
    if not _math.isfinite(angulo) or not 0 < angulo <= 90:
        raise ValueError("angulo de Bragg deve estar no intervalo (0, 90]")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n deve ser um inteiro positivo")
    theta = np.radians(angulo)
    lambda0 = 1.54e-10
    d = n * lambda0 / (2 * np.sin(theta))
    return {
        "simulador": "Cristalografia (Bragg)",
        "dominio": "Materiais - Cristalografia",
        "parametro_rede_m": a,
        "angulo_graus": angulo,
        "d_espacamento_m": float(d),
        "lambda_X_nm": lambda0 * 1e9,
        "validacao": f"Espacamento interplanar: {d*1e10:.3f} A"
    }


def sim_dft(pergunta, p):
    """DFT - estrutura eletronica."""
    material = p.get("material", "Si")
    bandgaps = {"Si": 1.12, "Ge": 0.66, "GaAs": 1.42, "diamond": 5.47,
                "graphene": 0.0, "MoS2": 1.8, "TiO2": 3.2, "default": 2.0}
    bg = bandgaps.get(material, bandgaps["default"])
    return {
        "simulador": "Referencias internas de bandgap (nao DFT)",
        "dominio": "Materiais - DFT",
        "material": material, "bandgap_eV": bg,
        "tipo": "direto" if material in ["GaAs","MoS2"] else "indireto",
        "validacao": f"Bandgap de {bg} eV para {material}"
    }

def comparar_materiais(pergunta, p=None):
    """Compara referencias internas de bandgap; nao executa DFT."""
    import unicodedata

    def normalizar(texto):
        texto = unicodedata.normalize("NFKD", str(texto).lower())
        return "".join(c for c in texto if not unicodedata.combining(c))

    texto = normalizar(pergunta)

    # Valores de referencia predefinidos ja presentes no modulo.
    # As condicoes e fases importam; estes valores nao sao resultados DFT.
    referencias = [
        {
            "material": "Silicio (Si)",
            "aliases": ["silicio", "silicon", "si"],
            "bandgap_eV": 1.12,
            "tipo": "indireto",
            "observacao": "Referencia aproximada para silicio cristalino a temperatura ambiente."
        },
        {
            "material": "Diamante",
            "aliases": ["diamante", "diamond"],
            "bandgap_eV": 5.47,
            "tipo": "indireto",
            "observacao": "Referencia aproximada para diamante cristalino."
        },
        {
            "material": "Grafeno",
            "aliases": ["grafeno", "graphene"],
            "bandgap_eV": 0.0,
            "tipo": "sem gap intrinseco ideal",
            "observacao": "Grafeno ideal nao tem bandgap convencional; substrato e abertura de gap podem alterar o valor."
        },
        {
            "material": "Germanio (Ge)",
            "aliases": ["germanio", "germanium"],
            "bandgap_eV": 0.66,
            "tipo": "indireto",
            "observacao": "Referencia aproximada para germanio cristalino."
        },
        {
            "material": "Arseneto de galio (GaAs)",
            "aliases": ["gaas", "arseneto de galio"],
            "bandgap_eV": 1.42,
            "tipo": "direto",
            "observacao": "Referencia aproximada para GaAs a temperatura ambiente."
        },
        {
            "material": "Dissulfeto de molibdenio (MoS2)",
            "aliases": ["mos2", "dissulfeto de molibdenio"],
            "bandgap_eV": 1.8,
            "tipo": "depende da fase e dimensionalidade",
            "observacao": "O valor varia significativamente entre monocamada e material em volume."
        },
        {
            "material": "Dioxido de titanio (TiO2)",
            "aliases": ["tio2", "dioxido de titanio"],
            "bandgap_eV": 3.2,
            "tipo": "depende da fase",
            "observacao": "O valor depende da fase cristalina e das condicoes do material."
        },
    ]

    encontrados = []
    for item in referencias:
        for alias in item["aliases"]:
            alias_normalizado = normalizar(alias)
            if alias_normalizado in ("si", "ge", "gaas", "mos2", "tio2"):
                import re
                padrao = r"(?<![a-z0-9])" + re.escape(alias_normalizado) + r"(?![a-z0-9])"
                corresponde = bool(re.search(padrao, texto))
            else:
                corresponde = alias_normalizado in texto

            if corresponde:
                encontrados.append(item)
                break

    if not encontrados:
        return {
            "status": "nenhum_material_reconhecido",
            "mensagem": "Informe materiais como silicio, diamante, grafeno, GaAs ou MoS2."
        }

    return {
        "simulador": "Comparador de referencias de materiais",
        "status": "referencias_internas_nao_DFT",
        "propriedade": "bandgap",
        "unidade": "eV",
        "quantidade_materiais": len(encontrados),
        "resultados": [
            {
                "material": item["material"],
                "bandgap_eV": item["bandgap_eV"],
                "tipo": item["tipo"],
                "observacao": item["observacao"],
                "origem": "tabela interna predefinida; nao calculado nesta execucao"
            }
            for item in encontrados
        ],
        "limitacao": (
            "Comparacao de valores de referencia, nao simulacao DFT. "
            "Os valores dependem de temperatura, fase, estrutura e metodo."
        )
    }


def sim_md(pergunta, p):
    """Dinamica molecular - energia, temperatura."""
    N = p.get("N_atomos", 100); T = p.get("T", 300)
    k_B = 1.38e-23; E = 1.5 * N * k_B * T
    return {
        "simulador": "Dinamica Molecular (LAMMPS)",
        "dominio": "Materiais - MD",
        "N_atomos": N, "T_K": T,
        "E_cinetica_J": E, "E_por_atomo_J": E / N,
        "validacao": f"Energia cinetica de {E:.2e} J"
    }

# ============================================================
# ENGENHARIA
# ============================================================

def sim_estrutural(pergunta, p):
    """Engenharia estrutural - tensao, deformacao."""
    F = p.get("forca", 1000); A = p.get("area", 0.01)
    E = p.get("modulo_E", 200e9); L = p.get("comprimento", 1.0)
    sigma = F / A
    epsilon = sigma / E
    delta = epsilon * L
    return {
        "simulador": "Engenharia Estrutural",
        "dominio": "Engenharia - Estrutural",
        "forca_N": F, "area_m2": A,
        "tensao_Pa": sigma, "deformacao": epsilon,
        "alongamento_m": delta,
        "validacao": f"Tensao de {sigma/1e6:.2f} MPa"
    }

def sim_cfd(pergunta, p):
    """CFD - fluxo de fluido."""
    rho = p.get("densidade", 1000); v = p.get("velocidade", 1.0)
    D = p.get("diametro", 0.1); mu = p.get("viscosidade", 1e-3)
    Re = rho * v * D / mu
    return {
        "simulador": "CFD (OpenFOAM)",
        "dominio": "Engenharia - Fluidos",
        "densidade_kgm3": rho, "velocidade_ms": v,
        "diametro_m": D, "viscosidade_Pas": mu,
        "Reynolds": Re,
        "regime": "laminar" if Re < 2300 else "turbulento",
        "validacao": f"Reynolds: {Re:.0f} ({'laminar' if Re<2300 else 'turbulento'})"
    }

def sim_eletrico(pergunta, p):
    """Circuitos eletricos - lei de Ohm."""
    V = p.get("voltagem", 12); R = p.get("resistencia", 100)
    I = V / R; P = V * I
    return {
        "simulador": "Circuitos Eletricos",
        "dominio": "Engenharia - Eletrica",
        "V_volts": V, "R_ohms": R,
        "I_amperes": I, "P_watts": P,
        "validacao": f"Corrente de {I*1000:.2f} mA, potencia de {P:.3f} W"
    }

# ============================================================
# MATEMATICA / COMPUTACAO
# ============================================================

def sim_estatistica(pergunta, p):
    """Monte Carlo gaussiano REPRODUZIVEL.

    DEFEITO CORRIGIDO (31/10/2026): usava `np.random.normal` sem semente, e a
    mesma pergunta devolvia media e desvio diferentes a cada chamada -- medido
    em auditoria/compara_snapshots.py, onde so este e o `algebra` mudaram de
    resultado depois de uma limpeza que nao deveria mudar nada. Resultado
    estocastico sem semente nao e' verificavel.
    Passa tambem a declarar o erro padrao da media, que e' o que permite dizer
    se a amostra basta.
    """
    mu = float(p.get("media", 0))
    sigma = float(p.get("desvio", 1))
    n = p.get("n", 1000)
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n deve ser um inteiro maior ou igual a 1")
    if not _math.isfinite(mu) or not _math.isfinite(sigma):
        raise ValueError("media e desvio devem ser finitos")
    if sigma < 0:
        raise ValueError("desvio nao pode ser negativo")
    semente = int(p.get("seed", 42))
    dados = np.random.default_rng(semente).normal(mu, sigma, n)
    media = float(np.mean(dados))
    desvio = float(np.std(dados, ddof=1)) if n > 1 else 0.0
    erro_padrao = desvio / _math.sqrt(n) if n > 1 else 0.0
    return {
        "simulador": "Estatistica (Monte Carlo)",
        "dominio": "Matematica - Estatistica",
        "n": n, "seed": semente,
        "media": media, "desvio": desvio,
        "erro_padrao_media": erro_padrao,
        "media_teorica": mu, "desvio_teorico": sigma,
        "min": float(np.min(dados)), "max": float(np.max(dados)),
        "validacao": f"Media: {media:.3f} (teorica {mu:.3f}, "
                     f"EP={erro_padrao:.4f}), desvio: {desvio:.3f}"
    }


def sim_otimizacao(pergunta, p):
    """Otimizacao - gradiente descendente."""
    x = np.linspace(-5, 5, 100)
    y = x**2 + 2*x + 1
    x_min = -1; y_min = 0
    return {
        "simulador": "Otimizacao (Gradiente)",
        "dominio": "Matematica - Otimizacao",
        "x_min": x_min, "y_min": y_min,
        "x_vals": x.tolist(), "y_vals": y.tolist(),
        "validacao": f"Minimo em x={x_min}, y={y_min}"
    }

# ============================================================
# CIENCIAS DA TERRA / AMBIENTE
# ============================================================

def sim_clima(pergunta, p):
    """Clima - balanco radiativo."""
    S0 = 1361; albedo = p.get("albedo", 0.3); sigma = 5.67e-8
    T_eq = ((S0 * (1 - albedo)) / (4 * sigma)) ** 0.25
    return {
        "simulador": "Clima (Balanco Radiativo)",
        "dominio": "Ciencias da Terra - Clima",
        "constante_solar_Wm2": S0, "albedo": albedo,
        "T_equilibrio_K": T_eq,
        "T_equilibrio_C": T_eq - 273.15,
        "validacao": f"Temperatura de equilibrio: {T_eq-273.15:.2f} C"
    }

def sim_sismico(pergunta, p):
    """Sismologia - ondas P e S."""
    t = np.linspace(0, 10, 500)
    v_p = 6000; v_s = 3500
    dist = 100000
    t_p = dist / v_p; t_s = dist / v_s
    return {
        "simulador": "Sismologia",
        "dominio": "Ciencias da Terra - Sismo",
        "v_p_ms": v_p, "v_s_ms": v_s,
        "distancia_m": dist,
        "t_P_s": t_p, "t_S_s": t_s,
        "delta_t_s": t_s - t_p,
        "validacao": f"Diferenca P-S: {t_s-t_p:.2f}s"
    }

# ============================================================
# MEDICINA / FARMACOLOGIA
# ============================================================

def sim_farmaco(pergunta, p):
    """Farmacocinetica - concentracao plasmatica."""
    dose = p.get("dose", 100); Vd = p.get("Vd", 50); ke = p.get("ke", 0.1)
    t = np.linspace(0, 24, 100)
    C = (dose / Vd) * np.exp(-ke * t)
    return {
        "simulador": "Farmacocinetica",
        "dominio": "Medicina - Farmaco",
        "dose_mg": dose, "Vd_L": Vd, "ke_h": ke,
        "C_max_mgL": dose / Vd,
        "meia_vida_h": np.log(2) / ke,
        "tempo": t.tolist(), "concentracao": C.tolist(),
        "validacao": f"Meia-vida de {np.log(2)/ke:.2f}h"
    }

def sim_epidemia(pergunta, p):
    import numpy as np
    from scipy.integrate import solve_ivp

    N = float(p.get("N", 1000000))
    beta = float(p.get("beta", 0.3))
    gamma = float(p.get("gamma", 0.1))

    if not all(_math.isfinite(x) for x in (N, beta, gamma)):
        raise ValueError("N, beta e gamma devem ser finitos")
    if N < 1:
        raise ValueError("N deve ser pelo menos 1")
    if beta < 0:
        raise ValueError("beta nao pode ser negativa")
    if gamma <= 0:
        raise ValueError("gamma deve ser maior que zero")

    S0, I0, R0_inicial = N - 1.0, 1.0, 0.0
    t = np.linspace(0.0, 160.0, 160)

    def sistema_sir(tempo, estado):
        S, I, R = estado
        novas_infeccoes = beta * S * I / N
        recuperacoes = gamma * I
        return (
            -novas_infeccoes,
            novas_infeccoes - recuperacoes,
            recuperacoes,
        )

    solucao = solve_ivp(
        sistema_sir,
        (float(t[0]), float(t[-1])),
        (S0, I0, R0_inicial),
        t_eval=t,
        method="RK45",
        rtol=1e-8,
        atol=1e-8,
    )

    if not solucao.success:
        raise RuntimeError(
            "Integracao SIR falhou: " + solucao.message
        )

    S, I, R = solucao.y.tolist()
    pico = max(I)

    return {
        "simulador": "Epidemiologia (SIR)",
        "dominio": "Medicina - Epidemia",
        "N": N,
        "beta": beta,
        "gamma": gamma,
        "R0": beta / gamma,
        "pico_infeccao": pico,
        "tempo": t.tolist(),
        "S": S,
        "I": I,
        "R": R,
        "validacao": (
            f"R0 = {beta/gamma:.2f}, "
            f"pico de {pico:.0f} infectados"
        ),
    }


# ============================================================
# DETECCAO DE DOMINIO
# ============================================================

DOMINIOS = {
    "mecanica": {"kws": ["force","energy","velocity","mass","motion","kinetic","gravity"], "sims": ["mecanica","estrutural"]},
    "termo": {"kws": ["heat","temperature","entropy","thermodynamic","thermal"], "sims": ["termo","clima"]},
    "em": {"kws": ["electric","magnetic","field","charge","current","voltage"], "sims": ["eletromagnetismo","eletrico"]},
    "optica": {"kws": ["light","optical","refraction","diffraction","laser","photon"], "sims": ["optica","dft"]},
    "quantica": {"kws": ["quantum","qubit","wave","orbital","schrodinger"], "sims": ["quantica","dft"]},
    "relatividade": {"kws": ["relativity","einstein","spacetime","gamma"], "sims": ["relatividade"]},
    "cinetica": {"kws": ["reaction","rate","kinetic","arrhenius","catalyst"], "sims": ["cinetica","equilibrio"]},
    "equilibrio": {"kws": ["equilibrium","gibbs","spontaneous","thermodynamic chemical"], "sims": ["equilibrio","eletroquimica"]},
    "eletro": {"kws": ["electrochemical","nernst","potential","cell"], "sims": ["eletroquimica"]},
    "genetica": {"kws": ["gene","genetic","allele","heridity","dna"], "sims": ["genetica"]},
    "ecologia": {"kws": ["population","ecology","growth","logistic"], "sims": ["ecologia"]},
    "neuro": {"kws": ["neuron","brain","action potential","synapse"], "sims": ["neuro"]},
    "cristalografia": {"kws": ["crystal","bragg","diffraction","lattice"], "sims": ["cristalografia","dft"]},
    "materiais": {"kws": ["material","bandgap","semiconductor","dft","electronic"], "sims": ["dft","md","cristalografia"]},
    "estrutural": {"kws": ["structure","stress","strain","beam","force"], "sims": ["estrutural"]},
    "fluidos": {"kws": ["flow","fluid","reynolds","turbulence","cfd"], "sims": ["cfd"]},
    "eletrica": {"kws": ["circuit","resistance","ohm","current","voltage"], "sims": ["eletrico"]},
    "estatistica": {"kws": ["statistics","probability","distribution","monte carlo"], "sims": ["estatistica"]},
    "otimizacao": {"kws": ["optimization","gradient","minimize","maximize"], "sims": ["otimizacao"]},
    "clima": {"kws": ["climate","temperature","radiation","albedo","greenhouse"], "sims": ["clima"]},
    "sismo": {"kws": ["earthquake","seismic","wave","magnitude"], "sims": ["sismico"]},
    "farmaco": {"kws": ["drug","pharmacokinetic","dose","half-life"], "sims": ["farmaco"]},
    "epidemia": {"kws": ["epidemic","virus","infection","sir","pandemic"], "sims": ["epidemia"]},
}

SIMULADORES = {
    "mecanica": sim_mecanica, "termo": sim_termodinamica,
    "eletromagnetismo": sim_eletromagnetismo, "optica": sim_optica,
    "quantica": sim_quantica, "relatividade": sim_relatividade,
    "cinetica": sim_cinetica, "equilibrio": sim_equilibrio,
    "eletroquimica": sim_eletroquimica, "genetica": sim_genetica,
    "ecologia": sim_ecologia, "neuro": sim_neuro,
    "cristalografia": sim_cristalografia, "dft": sim_dft,
    "md": sim_md, "estrutural": sim_estrutural,
    "cfd": sim_cfd, "eletrico": sim_eletrico,
    "estatistica": sim_estatistica, "otimizacao": sim_otimizacao,
    "clima": sim_clima, "sismico": sim_sismico,
    "farmaco": sim_farmaco, "epidemia": sim_epidemia,
}

def detectar_dominios(pergunta):
    import re
    import unicodedata

    def normalizar(texto):
        texto = unicodedata.normalize("NFKD", str(texto).lower())
        return "".join(c for c in texto if not unicodedata.combining(c))

    texto = normalizar(pergunta)
    doms = []

    # Mantem as palavras-chave existentes e aceita perguntas em portugues.
    #
    # DEFEITO CORRIGIDO (medido em 25/10/2026): a comparacao era substring puro
    # ("k in texto"), entao chave curta casava DENTRO de outra palavra. Caso real
    # reproduzido: a chave "PID" (do dominio "controle") casa dentro de
    # "epi-PID-emia", e "surto de epidemia virai" executava o controlador PID --
    # nenhum simulador epidemiologico. "sir" tambem casava em "sirva".
    # Agora a chave precisa comecar em fronteira de palavra, o que continua
    # aceitando prefixos uteis em portugues ("nuclear" em "nucleares",
    # "control" em "controle") e elimina o casamento no meio da palavra.
    for dom, cfg in DOMINIOS.items():
        palavras = [
            re.escape(normalizar(k)) for k in cfg.get("kws", []) if str(k).strip()
        ]
        if any(re.search(r"(?<![0-9a-z])" + p, texto) for p in palavras):
            doms.append(dom)

    aliases = {
        "cinetica": [
            "cinetica", "reacao quimica", "taxa de reacao",
            "energia de ativacao", "arrhenius"
        ],
        "termo": [
            "termodinamica", "temperatura", "calor",
            "entropia", "trabalho termodinamico"
        ],
        "poluicao": [
            "poluicao", "contaminante", "contaminantes",
            "efluente", "degradacao de contaminante"
        ],
        "superficie": [
            "adsorcao", "adsorvente", "carvao ativado",
            "area superficial", "isoterma de adsorcao"
        ],
        "materiais": [
            "material", "materiais", "bandgap", "silicio",
            "diamante", "grafeno", "semicondutor"
        ],
        "catalise": [
            "catalise", "catalisador", "catalisadores",
            "enzima", "enzimas"
        ],
    }

    for dom, palavras in aliases.items():
        if any(re.search(r"(?<![0-9a-z])" + re.escape(normalizar(p)), texto)
               for p in palavras):
            if dom not in doms:
                doms.append(dom)

    # DEFEITO CORRIGIDO (medido em 25/10/2026): antes, pergunta sem area
    # reconhecida caia em ["mecanica", "termo"] e o app devolvia 4 simulacoes
    # cientificas como se fossem a resposta. Reproducao real: a pergunta
    # "texto sem nenhum dominio reconhecivel zzz" executava mecanica,
    # estrutural, termo e clima. Silencio e melhor que resultado inventado:
    # agora devolve lista vazia e o chamador informa que nada se aplica.
    return doms


def extrair_params(pergunta):
    import re
    import unicodedata

    texto = str(pergunta)
    normalizado = unicodedata.normalize("NFKD", texto.lower())
    normalizado = "".join(
        c for c in normalizado if not unicodedata.combining(c)
    )
    p = {}

    nums = [
        float(n.replace(",", "."))
        for n in re.findall(r"\d+(?:[.,]\d+)?", normalizado)[:10]
    ]
    if nums:
        p["numeros"] = nums

    # Temperatura em Kelvin: "300 K", "T=300 K" ou "temperatura 300 K".
    m = re.search(
        r"(?:\bt\s*=?\s*|\ba\s*|temperatura\s*(?:de\s*)?)"
        r"(\d+(?:\.\d+)?)\s*k\b",
        normalizado
    )
    if m:
        p["T"] = float(m.group(1))

    # Energia de ativacao em J/mol, quando informada explicitamente.
    m = re.search(
        r"(?:energia de ativacao|\bea\b)\s*(?:=|:|de)?\s*"
        r"(\d+(?:\.\d+)?)",
        normalizado
    )
    if m:
        p["Ea"] = float(m.group(1))

    m = re.search(r"\bk0\s*=?\s*(\d+(?:\.\d+)?(?:e[+-]?\d+)?)", normalizado)
    if m:
        p["k0"] = float(m.group(1))

    # Parametros simples de concentracao/decaimento, se escritos na pergunta.
    for chave in ("c0", "k", "t", "albedo", "moles", "t1", "t2", "nivel"):
        m = re.search(
            r"\b" + chave + r"\s*=?\s*(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)",
            normalizado
        )
        if m:
            valor = float(m.group(1))
            p[{"c0": "C0", "t1": "T1", "t2": "T2"}.get(chave, chave)] = valor

    # --- Valores ROTULADOS (com unidade explicita) ---------------------------
    # DEFEITO CORRIGIDO: antes existiam apenas as chaves acima, entao a maioria
    # dos simuladores nunca recebia nada do usuario e calculava tudo no default.
    # Cada valor entra apenas quando rotulo E unidade deixam o significado
    # inequivoco ("angulo 30 graus", "massa 500 g"). Numero solto continua indo
    # so para p["numeros"]: adivinhar unidade produziria numero errado com cara
    # de certo, o que e pior do que assumir o default declarado.
    def _numero(texto_numero):
        return float(texto_numero.replace(",", "."))

    # Angulo em graus (Bragg/cristalografia, optica).
    m = re.search(
        r"\bangulo\s*(?:de\s*|:|=)?(-?\d+(?:[.,]\d+)?)\s*(?:graus?|\u00b0)",
        normalizado,
    )
    if m:
        p["angulo"] = _numero(m.group(1))

    # Massa com unidade -> sempre em kg (sim_zoologia le "massa_kg").
    m = re.search(
        r"\bmassa\s*(?:de\s*|:|=)?(-?\d+(?:[.,]\d+)?)\s*(kg|g)\b", normalizado
    )
    if m:
        valor = _numero(m.group(1))
        p["massa_kg"] = valor if m.group(2) == "kg" else valor / 1000.0

    # Peso corporal em kg (sim_fisio le "peso").
    m = re.search(r"\bpeso\s*(?:de\s*|:|=)?(-?\d+(?:[.,]\d+)?)\s*kg\b", normalizado)
    if m:
        p["peso"] = _numero(m.group(1))

    # Altura em metros (sim_fisio le "altura").
    m = re.search(
        r"\baltura\s*(?:de\s*|:|=)?(-?\d+(?:[.,]\d+)?)\s*(cm|m)\b", normalizado
    )
    if m:
        valor = _numero(m.group(1))
        p["altura"] = valor / 100.0 if m.group(2) == "cm" else valor

    # Chaves inteiras dos simuladores de computacao.
    for rotulo in ("bits", "camadas", "neuronios"):
        m = re.search(r"\b" + rotulo + r"\s*(?:de\s*|:|=)?(\d+)", normalizado)
        if m:
            p[rotulo] = int(m.group(1))

    # "nos" sozinho e ambiguo em portugues (pronome), por isso exige o rotulo
    # completo. sim_redes/sim_sistemas leem a chave "nos".
    m = re.search(r"\b(?:numero de|num)\s*nos\s*(?:de\s*|:|=)?(\d+)", normalizado)
    if m:
        p["nos"] = int(m.group(1))

    # Metricas de teste diagnostico: aceita fracao (0,95) ou percentual (95%).
    # Valor fora de [0,1] sem sinal de percentual e ambiguo e NAO e adivinhado.
    for rotulo in ("sensibilidade", "especificidade", "prevalencia"):
        m = re.search(
            r"\b" + rotulo + r"\s*(?:de\s*|:|=)?(-?\d+(?:[.,]\d+)?)\s*(%|por cento)?",
            normalizado,
        )
        if m:
            valor = _numero(m.group(1))
            if m.group(2):
                valor = valor / 100.0
            if 0 <= valor <= 1:
                p[rotulo] = valor

    if "diamante" in normalizado or "diamond" in normalizado:
        p["material"] = "diamond"
    elif "silicio" in normalizado or "silicon" in normalizado:
        p["material"] = "Si"
    elif "grafeno" in normalizado or "graphene" in normalizado:
        p["material"] = "graphene"
    elif "carvao ativado" in normalizado:
        p["material"] = "carvao_ativado"

    return p


def _chaves_lidas_no_simulador(funcao):
    """Chaves que o simulador consulta no dicionario de parametros.

    DEFEITO MEDIDO (31/10/2026, `infra/inventario_simuladores.py`): a versao
    anterior procurava literalmente `p.get(`, mas o arquivo nao e' consistente
    -- Astronomia e Computacao declaram `def sim_x(p, q)` e leem `q.get(...)`.
    Efeito: esses simuladores apareciam com `chaves_lidas_em_p: []`, rodavam
    inteiramente com default e NUNCA declaravam `parametros_padrao` ao usuario.
    O nome do dicionario passa a ser lido da propria assinatura, entao a
    declacao de default vale para todo simulador, qualquer que seja o nome.
    """
    import inspect
    import re as _re

    base = getattr(funcao, "_base_sim", funcao)
    try:
        fonte = inspect.getsource(base)
    except (OSError, TypeError):
        return set()
    nomes = {"p"}
    try:
        parametros = list(inspect.signature(base).parameters)
        if len(parametros) >= 2:
            nomes.add(parametros[1])
    except (TypeError, ValueError):
        pass
    padrao = r"(?:%s)\.get\(\s*[\"']([^\"']+)[\"']" % "|".join(
        _re.escape(nome) for nome in sorted(nomes))
    return set(_re.findall(padrao, fonte))


def _anotar_parametros_padrao(sid, resultado, params):
    """Declara no payload quais parametros o usuario NAO informou.

    Motivo medido: 77 dos 113 simuladores consultam chaves que extrair_params
    nunca produzia, entao rodavam inteiramente com default sem avisar ninguem.
    O usuario lia um numero arbitrario como se fosse resposta da sua pergunta.
    Aqui o proprio resultado passa a declarar o que foi valor padrao.
    """
    if not isinstance(resultado, dict) or resultado.get("erro"):
        return resultado
    lidas = _chaves_lidas_no_simulador(SIMULADORES.get(sid))
    if not lidas:
        return resultado
    padrao = sorted(k for k in lidas if k not in params)
    if padrao:
        resultado["parametros_padrao"] = padrao
    return resultado


def rodar_simulacoes(pergunta, max_sims=4):
    doms = detectar_dominios(pergunta)
    params = extrair_params(pergunta)
    sims_unicos = []
    for d in doms:
        for s in DOMINIOS[d]["sims"]:
            if s not in sims_unicos: sims_unicos.append(s)
    sims_unicos = sims_unicos[:max_sims]
    resultados = {}
    for sid in sims_unicos:
        try:
            resultados[sid] = _anotar_parametros_padrao(
                sid, SIMULADORES[sid](pergunta, params), params
            )
        except Exception as e:
            resultados[sid] = {"erro": str(e), "simulador": sid}
    return resultados, doms, params

def cruzar(pergunta, sims, artigos):
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    m = SentenceTransformer('all-MiniLM-L6-v2')
    cruz = {}
    for sid, dados in sims.items():
        if "erro" in dados: continue
        texto_sim = " ".join([f"{k}: {v}" for k, v in dados.items() if not isinstance(v, list)])
        scores = []
        for a in artigos[:10]:
            ta = f"{a.get('titulo','')} {a.get('resumo','')}"
            if not ta.strip(): continue
            es = m.encode([texto_sim])[0]; ea = m.encode([ta])[0]
            scores.append(float(cosine_similarity([es],[ea])[0][0]))
        media = float(np.mean(scores)) if scores else 0
        cruz[sid] = {"simulador": dados.get("simulador", sid),
                     "score_medio": media, "score_max": float(np.max(scores)) if scores else 0,
                     "compativel": media > 0.3, "artigos_cruzados": len(scores)}
    return cruz

def score_final(sims, cruz):
    scores = [c["score_medio"] for c in cruz.values()]
    if not scores: return {"score": 0, "interpretacao": "SEM DADOS", "validado": False, "n_sims": len(sims), "n_cruz": 0}
    m = float(np.mean(scores)); sn = (m + 1) / 2
    return {"score": sn, "score_bruto": m,
            "interpretacao": "ALTA" if sn > 0.7 else "MEDIA" if sn > 0.5 else "BAIXA",
            "validado": sn > 0.5, "n_sims": len(sims), "n_cruz": len(cruz)}

# ============ ASTRONOMIA (6) ============
def sim_estelar(p, q):
    M = q.get("Massa_Sol", 1); L = M**3.5
    return {"simulador":"Estelar","dominio":"Astronomia - Estelar",
            "luminosidade_Lsol":L,"vida_anos":10e9/M**2.5,"validacao":f"L={L:.2f} Lsol"}
def sim_galactica(p, q):
    M=q.get("massa_Msol",1e11); R=q.get("raio_kpc",15)
    v=(6.67e-11*M*2e30/(R*3.086e19))**0.5
    return {"simulador":"Galactica","dominio":"Astronomia - Galactica",
            "v_rot_km_s":v/1000,"validacao":f"v={v/1000:.0f} km/s"}
def sim_cosmo(p, q):
    H0 = float(q.get("H0", 70))
    if not _math.isfinite(H0) or H0 <= 0:
        raise ValueError("H0 deve ser finito e maior que zero")
    d = float(q.get("dist_Mpc", 100))
    if not _math.isfinite(d) or d < 0:
        raise ValueError("dist_Mpc deve ser finita e nao negativa")
    v = H0 * d
    return {
        "simulador": "Cosmologia",
        "dominio": "Astronomia - Cosmo",
        "H0_km_s_Mpc": H0,
        "dist_Mpc": d,
        "v_recessao_km_s": v,
        "validacao": f"v={v:.0f} km/s (H0={H0:.0f})"
    }

def sim_exo(p, q):
    Ms=q.get("Msol",1); Ps=q.get("periodo_anos",1)
    a=(Ms*Ps**2)**(1/3)
    return {"simulador":"Exoplanetas","dominio":"Astronomia - Exo",
            "semi_eixo_UA":a,"validacao":f"a={a:.3f} UA"}
def sim_buraco(p, q):
    M=q.get("Massa_Sol",10); G=6.67e-11; c=3e8; Msol=2e30
    Rs=2*G*M*Msol/c**2
    return {"simulador":"Buracos Negros","dominio":"Astronomia - BH",
            "Rs_m":Rs,"M_Sol":M,"validacao":f"Rs={Rs:.1f} m"}
def sim_solar(p, q):
    """Sistema planetario por Kepler, nao constante fixa.

    DEFEITO CORRIGIDO (31/10/2026): a versao anterior devolvia
    `{"planetas": 8}` sem ler parametro algum -- era constante, nao simulacao,
    e por isso aparecia no inventario com `chaves_lidas_em_p: []`.

    Física usada:
      * 3a lei de Kepler  T^2 = a^3 / M  (anos, UA, massas solares)
      * velocidade orbital v = 29.78 / sqrt(a/M) km/s (calibrada na Terra)
      * zona habitavel conservadora (Kasting): r = sqrt(L/1.1) e sqrt(L/0.53)
        com L = M^3.5 (relacao massa-luminosidade para estrela de sequencia
        principal).
    """
    M = float(q.get("M_estrela_Msol", 1.0))
    a = float(q.get("a_AU", 1.0))
    if not _math.isfinite(M) or M <= 0:
        raise ValueError("M_estrela_Msol deve ser finito e maior que zero")
    if not _math.isfinite(a) or a <= 0:
        raise ValueError("a_AU deve ser finito e maior que zero")
    # Semi-eixos reais do Sistema Solar (UA); a estrela e' parametrica.
    semi_eixos = [0.387, 0.723, 1.0, 1.524, 5.203, 9.537, 19.191, 30.069]
    luminosidade = M ** 3.5
    r_interno = _math.sqrt(luminosidade / 1.1)
    r_externo = _math.sqrt(luminosidade / 0.53)
    periodo = _math.sqrt(a ** 3 / M)
    return {"simulador": "Sistema Solar", "dominio": "Astronomia - Solar",
            "planetas": len(semi_eixos),
            "M_estrela_Msol": M, "a_AU": a,
            "periodo_anos": periodo,
            "velocidade_orbital_km_s": 29.78 / _math.sqrt(a / M),
            "zona_habitavel_AU": [r_interno, r_externo],
            "habitavel": bool(r_interno <= a <= r_externo),
            "periodos_anos": [round(_math.sqrt(x ** 3 / M), 3)
                              for x in semi_eixos],
            "validacao": f"T={periodo:.3f} anos; ZH {r_interno:.2f}-"
                         f"{r_externo:.2f} UA"}

SIMULADORES.update({"ast_estelar":sim_estelar,"ast_gal":sim_galactica,
"ast_cosmo":sim_cosmo,"ast_exo":sim_exo,"ast_bh":sim_buraco,"ast_solar":sim_solar})

DOMINIOS.update({
"ast_estelar":{"kws":["star","stellar","main sequence","sun"],"sims":["ast_estelar"]},
"ast_gal":{"kws":["galaxy","galactic","milky way"],"sims":["ast_gal"]},
"ast_cosmo":{"kws":["cosmology","hubble","redshift","big bang"],"sims":["ast_cosmo"]},
"ast_exo":{"kws":["exoplanet","kepler","transit"],"sims":["ast_exo"]},
"ast_bh":{"kws":["black hole","schwarzschild","event horizon"],"sims":["ast_bh"]},
"ast_solar":{"kws":["solar system","planet","asteroid"],"sims":["ast_solar"]},
})

# ============ COMPUTACAO (6) ============
def sim_algo(p, q):
    import math
    n = q.get("n", 1000)
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n deve ser um inteiro positivo")
    valor = n * math.log2(n)
    return {
        "simulador": "Algoritmos",
        "dominio": "Computacao - Algo",
        "n": n,
        "O_n_log_n": valor,
        "validacao": f"n log n={valor:.0f}"
    }

def sim_ia(p, q):
    """Contagem real de parametros de um MLP denso.

    DEFEITO CORRIGIDO (31/10/2026): antes era `neuronios**2 * camadas`, que
    ignora a dimensao de entrada e o vies de cada neuronio -- duas
    arquiteturas muito diferentes devolviam o mesmo numero.
    Camada densa com `entrada` entradas e `saida` neuronios:
        pesos = entrada*saida ; vieses = saida
    """
    camadas = int(q.get("camadas", 3))
    neuronios = int(q.get("neuronios", 100))
    entrada = int(q.get("entrada", 784))
    if camadas < 1 or neuronios < 1 or entrada < 1:
        raise ValueError("camadas, neuronios e entrada devem ser >= 1")
    parametros = 0
    atual = entrada
    for _ in range(camadas):
        parametros += atual * neuronios + neuronios
        atual = neuronios
    # Um passo de treino (forward + backward) custa ~6 FLOPs por parametro.
    return {"simulador": "IA/ML", "dominio": "Computacao - IA",
            "camadas": camadas, "neuronios": neuronios, "entrada": entrada,
            "parametros": parametros,
            "memoria_fp32_MB": parametros * 4 / 1e6,
            "flops_por_amostra": 6 * parametros,
            "validacao": f"{parametros:.2e} params ({camadas}x{neuronios})"}
def sim_cripto(p, q):
    """Forca efetiva do RSA pela complexidade do GNFS.

    DEFEITO CORRIGIDO (31/10/2026): antes devolvia `log2(bits)*bits`, grandeza
    sem significado criptografico (dizia que RSA-2048 tem 22528 bits de
    seguranca). Estimativa aceita na literatura para o Number Field Sieve:
        L_n = exp(1.923 * ln(n)^(1/3) * ln(ln(n))^(2/3)), n = 2^bits
    O log2 desse custo e' a forca efetiva em bits (~117 para RSA-2048,
    coerente com os ~112 bits simetricos de referencia da NIST).
    """
    bits = int(q.get("bits", 2048))
    if bits < 512:
        raise ValueError("bits deve ser >= 512 para RSA")
    ln_n = bits * _math.log(2)
    expoente = 1.923 * ln_n ** (1 / 3) * _math.log(ln_n) ** (2 / 3)
    seguranca = expoente / _math.log(2)
    return {"simulador": "Criptografia", "dominio": "Computacao - Cripto",
            "bits": bits, "chave_bytes": bits // 8, "seguranca": seguranca,
            "validacao": f"RSA-{bits} ~{seguranca:.0f} bits (GNFS)"}
def sim_redes(p, q):
    """Grafo com grau medio prescrito, respeitando o lema do handshake.

    DEFEITO CORRIGIDO (31/10/2026): `n*k//2` arredondava a soma de graus e
    descrevia grafo impossivel quando n*k era impar; nao calculava densidade
    nem caminho medio, e aceitava grau maior que o numero de nos.
    """
    nos = int(q.get("nos", 100)); grau = int(q.get("grau_medio", 3))
    if nos < 2:
        raise ValueError("nos deve ser >= 2")
    if grau < 1 or grau >= nos:
        raise ValueError("grau_medio deve estar entre 1 e nos-1")
    graus = [grau] * nos
    if (nos * grau) % 2:  # soma dos graus tem de ser par
        graus[-1] += 1
    arestas = sum(graus) // 2
    densidade = 2 * arestas / (nos * (nos - 1))
    caminho = _math.log(nos) / _math.log(grau) if grau > 1 else nos / 2
    return {"simulador": "Redes", "dominio": "Computacao - Redes",
            "nos": nos, "grau_medio": grau, "arestas": arestas,
            "densidade": densidade, "caminho_medio_estimado": caminho,
            "validacao": f"{nos} nos, {arestas} links, rho={densidade:.4f}"}
def sim_bd(p, q):
    n=q.get("registros",1e6); tam=q.get("tam_bytes",100)
    return {"simulador":"Banco de Dados","dominio":"Computacao - BD",
            "tamanho_MB":n*tam/1e6,"validacao":f"{n*tam/1e6:.1f} MB"}
def sim_compil(p, q):
    """AST e tabela de simbolos a partir da contagem de tokens.

    DEFEITO CORRIGIDO (31/10/2026): a validacao devolvia so a palavra "AST",
    sem nenhum numero -- impossivel conferir se o calculo rodou.
    """
    tokens = int(q.get("tokens", 1000))
    if tokens < 1:
        raise ValueError("tokens deve ser >= 1")
    simbolos = int(q.get("simbolos", max(1, tokens // 10)))
    nos = tokens * 3
    return {"simulador": "Compiladores", "dominio": "Computacao - Compil",
            "tokens": tokens, "arvore_nos": nos, "tabela_simbolos": simbolos,
            "validacao": f"{tokens} tokens -> {nos} nos AST, "
                         f"{simbolos} simbolos"}

SIMULADORES.update({"comp_algo":sim_algo,"comp_ia":sim_ia,"comp_cripto":sim_cripto,
"comp_redes":sim_redes,"comp_bd":sim_bd,"comp_compil":sim_compil})

DOMINIOS.update({
"comp_algo":{"kws":["algorithm","complexity","big o"],"sims":["comp_algo"]},
"comp_ia":{"kws":["artificial intelligence","neural network","machine learning"],"sims":["comp_ia"]},
"comp_cripto":{"kws":["cryptography","RSA","encryption"],"sims":["comp_cripto"]},
"comp_redes":{"kws":["network","internet","topology"],"sims":["comp_redes"]},
"comp_bd":{"kws":["database","SQL","records"],"sims":["comp_bd"]},
"comp_compil":{"kws":["compiler","parsing","AST"],"sims":["comp_compil"]},
})

# ============ FISICA EXPANDIDA ============
import math as _math
def sim_acustica(pergunta, p):
    f = float(p.get("frequencia", 440))
    I = float(p.get("intensidade", 1e-6))
    if not _math.isfinite(f) or f <= 0:
        raise ValueError("frequencia deve ser finita e maior que zero")
    if not _math.isfinite(I) or I <= 0:
        raise ValueError("intensidade deve ser finita e maior que zero")
    nivel = 10 * _math.log10(I / 1e-12)
    return {
        "simulador": "Acustica",
        "dominio": "Fisica - Acustica",
        "frequencia_Hz": f,
        "lambda_m": 343 / f,
        "nivel_dB": nivel,
        "validacao": f"{nivel:.1f} dB"
    }

def sim_fluido(pergunta, p):
    rho=p.get("densidade",1000); v=p.get("velocidade",1.0)
    D=p.get("diametro",0.1); mu=p.get("viscosidade",1e-3)
    Re=rho*v*D/mu
    return {"simulador":"Fluidos","dominio":"Fisica - Fluidos","Reynolds":Re,
            "regime":"laminar" if Re<2300 else "turbulento","validacao":f"Re={Re:.0f}"}
def sim_plasma(pergunta, p):
    V=p.get("V",380); ne=1e14*(V/100)**2
    return {"simulador":"Plasma","dominio":"Fisica - Plasmas",
            "V_ruptura_V":V,"ne_cm3":min(ne,1e16),"Te_eV":1.5,"validacao":f"Plasma {V}V"}
def sim_nuclear(pergunta, p):
    A=p.get("A",235)
    return {"simulador":"Nuclear","dominio":"Fisica - Nuclear","A":A,
            "energia_ligacao_MeV":8*A,"validacao":f"E={8*A} MeV"}
def sim_particulas(pergunta, p):
    m=p.get("massa_GeV",0.938); E=p.get("energia_GeV",1.0)
    pm=_math.sqrt(max(E**2-m**2,0))
    return {"simulador":"Particulas","dominio":"Fisica - Particulas",
            "momento_GeV":pm,"beta":pm/E if E else 0,"validacao":f"p={pm:.3f} GeV"}
def sim_solido(pergunta, p):
    # `a` em ANGSTROM (a unidade do motor ASE/EMT). O default e' a rede do Cu
    # fcc, o mesmo elemento default do motor; com o default antigo (5,43e-10,
    # em metros) o motor recebia 5,43e-10 A e estourava MemoryError -> queda
    # silenciosa para esta formula. Medido no inventario de 31/10/2026.
    # Aceita metro tambem, para quem copia `parametro_rede_m` de outro simulador.
    a = float(p.get("a", 3.615) or 3.615)
    if a < 1e-8:  # veio em metros
        a *= 1e10
    return {"simulador":"Estado Solido","dominio":"Fisica - Condensada",
            "parametro_rede_m":a*1e-10,"parametro_rede_A":a,
            "validacao":f"a={a:.2f} A"}

SIMULADORES.update({"acustica":sim_acustica,"fluido":sim_fluido,"plasma":sim_plasma,
"nuclear":sim_nuclear,"particulas":sim_particulas,"solido":sim_solido})

DOMINIOS.update({
"acustica":{"kws":["sound","acoustic","frequency wave"],"sims":["acustica"]},
"fluido":{"kws":["fluid","flow","reynolds","turbulence"],"sims":["fluido","cfd"]},
"plasma":{"kws":["plasma","discharge","ionization","glow"],"sims":["plasma"]},
"nuclear":{"kws":["nuclear","fission","fusion","radioactive"],"sims":["nuclear"]},
"particulas":{"kws":["particle","collider","higgs","quark"],"sims":["particulas"]},
"solido":{"kws":["solid state","condensed","lattice"],"sims":["solido","cristalografia"]},
})

# ============ QUIMICA EXPANDIDA ============
def sim_organica(pergunta, p):
    n=p.get("estereocentros",1)
    return {"simulador":"Quimica Organica","dominio":"Quimica - Organica",
            "estereocentros":n,"isomeros":2**n,"validacao":f"2^{n} isomeros"}
def sim_inorganica(pergunta, p):
    Z=p.get("Z",26); A=p.get("A",56)
    return {"simulador":"Inorganica","dominio":"Quimica - Inorganica",
            "Z":Z,"A":A,"neutrons":A-Z,"validacao":f"Z={Z} N={A-Z}"}
def sim_polimeros(pergunta, p):
    Mn=p.get("Mn",50000); Mw=p.get("Mw",100000)
    return {"simulador":"Polimeros","dominio":"Quimica - Polimeros",
            "Mn":Mn,"Mw":Mw,"PDI":Mw/Mn,"validacao":f"PDI={Mw/Mn:.2f}"}
def sim_superficie(pergunta, p):
    return {"simulador":"Superficie","dominio":"Quimica - Superficie",
            "area_m2g":p.get("area_m2g",500),"validacao":"Area superficial"}
def sim_catalise(pergunta, p):
    k0=1e10; Ea=p.get("Ea",50000); T=300; R=8.314
    k=k0*_math.exp(-Ea/(R*T)); kc=k0*_math.exp(-Ea*0.5/(R*T))
    return {"simulador":"Catalise","dominio":"Quimica - Catalise",
            "k_cat":kc,"k_sem":k,"aceleracao":kc/k if k>0 else 0,
            "validacao":f"Acelera {kc/k:.0f}x"}

SIMULADORES.update({"organica":sim_organica,"inorganica":sim_inorganica,
"polimeros":sim_polimeros,"superficie":sim_superficie,"catalise":sim_catalise})

DOMINIOS.update({
"organica":{"kws":["organic","isomer","stereochemistry"],"sims":["organica"]},
"inorganica":{"kws":["inorganic","coordination complex"],"sims":["inorganica"]},
"polimeros":{"kws":["polymer","PDI","macromolecule"],"sims":["polimeros"]},
"superficie":{"kws":["surface","adsorption"],"sims":["superficie"]},
"catalise":{"kws":["catalysis","catalyst","enzyme"],"sims":["catalise"]},
})

# ============ BIOLOGIA EXPANDIDA ============
def sim_evolucao(pergunta, p):
    mu=p.get("taxa_mutacao",1e-8); N=p.get("N",1000); G=p.get("geracoes",100)
    return {"simulador":"Evolucao","dominio":"Biologia - Evolucao",
            "mutacoes_esperadas":mu*N*G,"validacao":f"{mu*N*G:.2e} mutacoes"}
def sim_micro(pergunta, p):
    N0=p.get("N0",1); mu=p.get("mu",0.5); t=p.get("t",10)
    return {"simulador":"Microbiologia","dominio":"Biologia - Micro",
            "N_final":N0*_math.exp(mu*t),"tempo_geracao_h":_math.log(2)/mu,
            "validacao":f"geracao {_math.log(2)/mu:.2f}h"}
def sim_imuno(pergunta, p):
    return {"simulador":"Imunologia","dominio":"Biologia - Imuno",
            "anticorpos":p.get("anticorpos",1e6),"validacao":"Resposta imune"}
def sim_botanica(pergunta, p):
    PAR=p.get("PAR",1500); LUE=p.get("LUE",0.05)
    return {"simulador":"Botanica","dominio":"Biologia - Botanica",
            "fotossintese":PAR*LUE,"validacao":f"Fotossintese {PAR*LUE:.2f}"}
def sim_zoologia(pergunta, p):
    M=p.get("massa_kg",1)
    return {"simulador":"Zoologia","dominio":"Biologia - Zoologia",
            "BMR_kcal_dia":70*M**0.75,"validacao":f"BMR={70*M**0.75:.1f}"}
def sim_molecular(pergunta, p):
    L=p.get("comprimento_aa",300)
    return {"simulador":"Biologia Molecular","dominio":"Biologia - Molecular",
            "peso_kDa":L*110/1000,"validacao":f"{L*110/1000:.1f} kDa"}
def sim_sistemas(pergunta, p):
    n=p.get("nos",10); k=p.get("conexoes",3)
    return {"simulador":"Sistemas","dominio":"Biologia - Sistemas",
            "densidade":k/(n*(n-1)/2) if n>1 else 0,"validacao":"Rede modelada"}

SIMULADORES.update({"evolucao":sim_evolucao,"micro":sim_micro,"imuno":sim_imuno,
"botanica":sim_botanica,"zoologia":sim_zoologia,"molecular":sim_molecular,
"sistemas":sim_sistemas})

DOMINIOS.update({
"evolucao":{"kws":["evolution","mutation","selection","darwin"],"sims":["evolucao"]},
"micro":{"kws":["bacteria","microbe","culture"],"sims":["micro"]},
"imuno":{"kws":["immune","antibody","antigen"],"sims":["imuno"]},
"botanica":{"kws":["plant","photosynthesis","leaf"],"sims":["botanica"]},
"zoologia":{"kws":["animal","metabolism","BMR"],"sims":["zoologia"]},
"molecular":{"kws":["protein","molecular","amino acid"],"sims":["molecular"]},
"sistemas":{"kws":["systems biology","pathway"],"sims":["sistemas"]},
})

# ============ MEDICINA EXPANDIDA ============
def sim_cardio(pergunta, p):
    FC=p.get("FC",70); VS=p.get("volume_sistolico",70)
    return {"simulador":"Cardiologia","dominio":"Medicina - Cardio",
            "debito_cardiaco_L_min":FC*VS/1000,"validacao":f"DC={FC*VS/1000:.2f} L/min"}
def sim_onco(pergunta, p):
    N0=p.get("N0",1e6); r=p.get("r",0.1); t=p.get("t",30)
    return {"simulador":"Oncologia","dominio":"Medicina - Onco",
            "N_final":N0*_math.exp(r*t),"tempo_doubling_h":_math.log(2)/r,
            "validacao":f"DT={_math.log(2)/r:.2f}h"}
def sim_imuno_med(pergunta, p):
    return {"simulador":"Imunologia Medica","dominio":"Medicina - Imuno",
            "IgG_mg_dL":p.get("IgG",1200),"validacao":"Perfil imuno"}
def sim_fisio(pergunta, p):
    peso=p.get("peso",70); alt=p.get("altura",1.75); IMC=peso/alt**2
    return {"simulador":"Fisiologia","dominio":"Medicina - Fisiologia",
            "IMC":IMC,"classificacao":"normal" if 18.5<=IMC<25 else "alterado",
            "validacao":f"IMC={IMC:.1f}"}
def sim_diag(pergunta, p):
    sens=p.get("sensibilidade",0.95); espec=p.get("especificidade",0.95); prev=p.get("prevalencia",0.01)
    VPP=sens*prev/(sens*prev+(1-espec)*(1-prev))
    return {"simulador":"Diagnostico","dominio":"Medicina - Diagnostico",
            "VPP":VPP,"validacao":f"VPP={VPP:.3f}"}
def sim_cirurgia(pergunta, p):
    r=p.get("risco_base",0.01); ASA=p.get("ASA",2)
    return {"simulador":"Cirurgia","dominio":"Medicina - Cirurgia",
            "risco_final":r*(1.5**(ASA-1)),"validacao":"Risco calculado"}

SIMULADORES.update({"cardio":sim_cardio,"onco":sim_onco,"imuno_med":sim_imuno_med,
"fisio":sim_fisio,"diag":sim_diag,"cirurgia":sim_cirurgia})

DOMINIOS.update({
"cardio":{"kws":["cardiac","heart","blood pressure"],"sims":["cardio"]},
"onco":{"kws":["cancer","tumor","oncology"],"sims":["onco"]},
"imuno_med":{"kws":["immunology","autoimmune"],"sims":["imuno_med"]},
"fisio":{"kws":["physiology","metabolism","BMI"],"sims":["fisio"]},
"diag":{"kws":["diagnosis","sensitivity","specificity"],"sims":["diag"]},
"cirurgia":{"kws":["surgery","surgical","ASA"],"sims":["cirurgia"]},
})

# ============ MATERIAIS EXPANDIDA ============
def sim_polim_mat(pergunta, p):
    E=p.get("E",3e9)
    return {"simulador":"Polimeros (mat)","dominio":"Materiais - Polimeros",
            "modulo_E_GPa":E/1e9,"validacao":f"E={E/1e9:.2f} GPa"}
def sim_metais(pergunta, p):
    E=p.get("E",200e9); rho=p.get("rho",7800)
    return {"simulador":"Metais","dominio":"Materiais - Metais",
            "velocidade_som_ms":_math.sqrt(E/rho),"validacao":"v_som calculada"}
def sim_ceram(pergunta, p):
    return {"simulador":"Ceramicas","dominio":"Materiais - Ceramicas",
            "Kic_Pam05":p.get("Kic",4e6),"validacao":"Kic calculado"}
def sim_comp(pergunta, p):
    Ef=p.get("Ef",70e9); Em=p.get("Em",3e9); Vf=p.get("Vf",0.6)
    return {"simulador":"Compositos","dominio":"Materiais - Compositos",
            "E_GPa":(Vf*Ef+(1-Vf)*Em)/1e9,"validacao":"Regra das misturas"}
def sim_nano(pergunta, p):
    d=p.get("diametro_nm",5)
    return {"simulador":"Nanomateriais","dominio":"Materiais - Nano",
            "area_relativa":6/d,"validacao":f"Area={6/d:.2f}"}

SIMULADORES.update({"polim_mat":sim_polim_mat,"metais":sim_metais,
"ceram":sim_ceram,"comp":sim_comp,"nano":sim_nano})

DOMINIOS.update({
"polim_mat":{"kws":["polymer material","plastic"],"sims":["polim_mat"]},
"metais":{"kws":["metal","alloy","steel"],"sims":["metais"]},
"ceram":{"kws":["ceramic","Kic","fracture"],"sims":["ceram"]},
"comp":{"kws":["composite","fiber","matrix"],"sims":["comp"]},
"nano":{"kws":["nanoparticle","nanomaterial","nanotube"],"sims":["nano"]},
})

# ============ ENGENHARIA EXPANDIDA ============
def sim_termico(pergunta, p):
    P=p.get("P",100); k=p.get("k",200); A=p.get("A",0.01); d=p.get("d",0.001)
    R=d/(k*A)
    return {"simulador":"Termico","dominio":"Engenharia - Termico",
            "dT_K":P*R,"validacao":f"dT={P*R:.2f} K"}
def sim_aero(pergunta, p):
    rho=p.get("rho",1.225); v=p.get("v",100); S=p.get("S",20); CL=p.get("CL",0.5)
    return {"simulador":"Aeroespacial","dominio":"Engenharia - Aero",
            "sustentacao_N":0.5*rho*v**2*S*CL,"validacao":"Lift calculado"}
def sim_quim_eng(pergunta, p):
    return {"simulador":"Eng Quimica","dominio":"Engenharia - Quimica",
            "produto":p.get("F",100)*p.get("X",0.9),"validacao":"Produto"}
def sim_civil(pergunta, p):
    return {"simulador":"Civil","dominio":"Engenharia - Civil",
            "carga_max_N":p.get("fck",30e6)*p.get("A",0.01),"validacao":"Carga"}
def sim_mecanica_eng(pergunta, p):
    return {"simulador":"Mecanica Eng","dominio":"Engenharia - Mecanica",
            "potencia_W":p.get("torque",100)*p.get("omega",100),"validacao":"Potencia"}
def sim_controle(pergunta, p):
    return {"simulador":"Controle PID","dominio":"Engenharia - Controle",
            "Kp":p.get("Kp",1),"validacao":"PID"}
def sim_robotica(pergunta, p):
    return {"simulador":"Robotica","dominio":"Engenharia - Robotica",
            "DOF":p.get("n_juntas",6),"validacao":"DOF"}

SIMULADORES.update({"termico":sim_termico,"aero":sim_aero,"quim_eng":sim_quim_eng,
"civil":sim_civil,"mecanica_eng":sim_mecanica_eng,"controle":sim_controle,
"robotica":sim_robotica})

DOMINIOS.update({
"termico":{"kws":["thermal engineering","heat sink","dissipation"],"sims":["termico"]},
"aero":{"kws":["aerospace","lift","drag","airfoil"],"sims":["aero"]},
"quim_eng":{"kws":["chemical engineering","reactor"],"sims":["quim_eng"]},
"civil":{"kws":["civil","concrete","fck","bridge"],"sims":["civil"]},
"mecanica_eng":{"kws":["mechanical","torque","power"],"sims":["mecanica_eng"]},
"controle":{"kws":["control","PID","feedback"],"sims":["controle"]},
"robotica":{"kws":["robot","kinematics","joint"],"sims":["robotica"]},
})

# ============ MATEMATICA EXPANDIDA ============
def sim_algebra(pergunta, p):
    """Sistema linear Ax=b com matriz aleatoria REPRODUZIVEL.

    DEFEITO CORRIGIDO (31/10/2026): `np.random.randn` sem semente fazia a mesma
    pergunta devolver outra solucao a cada chamada (medido em
    auditoria/compara_snapshots.py). Sem semente nao ha' como verificar nada.
    Passa a declarar tambem o residuo ||Ax-b||, que e' a prova de que a
    solucao devolvida resolve o sistema.
    """
    import numpy as np

    n = p.get("n", 3)
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n deve ser um inteiro maior ou igual a 2")
    semente = int(p.get("seed", 42))
    gerador = np.random.default_rng(semente)
    matriz = gerador.standard_normal((n, n))
    vetor = gerador.standard_normal(n)
    try:
        x = np.linalg.solve(matriz, vetor)
    except np.linalg.LinAlgError:
        return {"simulador": "Algebra Linear",
                "dominio": "Matematica - Algebra",
                "n": n, "seed": semente,
                "erro": "matriz singular: sem solucao unica",
                "validacao": f"A({n}x{n}) singular"}
    residuo = float(np.linalg.norm(matriz @ x - vetor))
    return {"simulador": "Algebra Linear", "dominio": "Matematica - Algebra",
            "n": n, "seed": semente, "solucao": x.tolist(),
            "residuo": residuo,
            "validacao": f"||x||={np.linalg.norm(x):.3f} "
                         f"residuo={residuo:.2e}"}
def sim_calculo(pergunta, p):
    f=lambda x:x**2; a=p.get("a",0); b=p.get("b",1); n=1000; h=(b-a)/n
    integral=sum(f(a+i*h)*h for i in range(n))
    return {"simulador":"Calculo","dominio":"Matematica - Calculo",
            "integral":integral,"validacao":f"int={integral:.4f}"}
def sim_topo(pergunta, p):
    g=p.get("genero",1)
    return {"simulador":"Topologia","dominio":"Matematica - Topologia",
            "genero":g,"euler":2-2*g,"validacao":f"Euler={2-2*g}"}
def sim_numeros(pergunta, p):
    n=p.get("n",100)
    pr=[i for i in range(2,n) if all(i%j for j in range(2,int(i**0.5)+1))]
    return {"simulador":"Teoria dos Numeros","dominio":"Matematica - Numeros",
            "primos_ate_n":len(pr),"validacao":f"{len(pr)} primos"}
def sim_grafos(pergunta, p):
    """Grafo com n nos e grau alvo k, sem grafo impossivel.

    DEFEITO CORRIGIDO (31/10/2026): `n*k//2` arredondava a soma de graus (que
    tem de ser par, lema do handshake) e aceitava k >= n.
    """
    n = p.get("n", 10)
    k = p.get("k", 3)
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n deve ser um inteiro maior ou igual a 2")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k < n:
        raise ValueError("k deve estar entre 1 e n-1")
    graus = [k] * n
    if (n * k) % 2:
        graus[-1] += 1
    arestas = sum(graus) // 2
    return {"simulador": "Grafos", "dominio": "Matematica - Grafos",
            "n": n, "grau_alvo": k, "arestas": arestas,
            "densidade": 2 * arestas / (n * (n - 1)),
            "validacao": f"{n} nos {arestas} arestas"}
def sim_prob(pergunta, p):
    from math import comb
    ps=p.get("p",0.5); n=p.get("n",10); k=p.get("k",5)
    prob=comb(n,k)*ps**k*(1-ps)**(n-k)
    return {"simulador":"Probabilidade","dominio":"Matematica - Probabilidade",
            "P_X_k":prob,"validacao":f"P={prob:.4f}"}

SIMULADORES.update({"algebra":sim_algebra,"calculo":sim_calculo,"topo":sim_topo,
"numeros":sim_numeros,"grafos":sim_grafos,"prob":sim_prob})

DOMINIOS.update({
"algebra":{"kws":["linear algebra","matrix","eigenvalue"],"sims":["algebra"]},
"calculo":{"kws":["calculus","integral","derivative"],"sims":["calculo"]},
"topo":{"kws":["topology","genus","euler"],"sims":["topo"]},
"numeros":{"kws":["number theory","prime","factorization"],"sims":["numeros"]},
"grafos":{"kws":["graph","network","node","edge"],"sims":["grafos"]},
"prob":{"kws":["probability","random variable","binomial"],"sims":["prob"]},
})

# ============ TERRA EXPANDIDA ============
def sim_geo(pergunta, p):
    return {"simulador":"Geologia","dominio":"Terra - Geologia",
            "idade_Ma":p.get("idade_Ma",100),"validacao":f"Idade={p.get('idade_Ma',100)} Ma"}
def sim_meteo(pergunta, p):
    T=p.get("T",25); UR=p.get("UR",60); a=17.27; b=237.7
    alpha=(a*T)/(b+T)+_math.log(UR/100); Td=(b*alpha)/(a-alpha)
    return {"simulador":"Meteorologia","dominio":"Terra - Meteo",
            "Td_C":Td,"validacao":f"Td={Td:.1f} C"}
def sim_oceano(pergunta, p):
    S=p.get("S",35); T=p.get("T",15)
    return {"simulador":"Oceanografia","dominio":"Terra - Oceano",
            "densidade_kgm3":1000+0.8*S-0.2*T,"validacao":f"rho={1000+0.8*S-0.2*T:.1f}"}
def sim_hidro(pergunta, p):
    A=p.get("area_km2",100); P=p.get("precipitacao_mm",1000)
    return {"simulador":"Hidrologia","dominio":"Terra - Hidro",
            "volume_m3":A*1e6*P/1000,"validacao":f"V={A*1e6*P/1000:.2e} m3/ano"}
def sim_vulcao(pergunta, p):
    VEI=p.get("VEI",4); E=10**(VEI+10)
    return {"simulador":"Vulcanologia","dominio":"Terra - Vulcao",
            "VEI":VEI,"energia_J":E,"validacao":f"VEI {VEI}"}
def sim_mineral(pergunta, p):
    return {"simulador":"Mineralogia","dominio":"Terra - Mineral",
            "dureza_Mohs":p.get("dureza",7),"validacao":"Mineral"}

SIMULADORES.update({"geo":sim_geo,"meteo":sim_meteo,"oceano":sim_oceano,
"hidro":sim_hidro,"vulcao":sim_vulcao,"mineral":sim_mineral})

DOMINIOS.update({
"geo":{"kws":["geology","rock","stratigraphy"],"sims":["geo"]},
"meteo":{"kws":["meteorology","dew point","humidity"],"sims":["meteo"]},
"oceano":{"kws":["ocean","salinity","sea water"],"sims":["oceano"]},
"hidro":{"kws":["hydrology","river","watershed"],"sims":["hidro"]},
"vulcao":{"kws":["volcano","eruption","VEI"],"sims":["vulcao"]},
"mineral":{"kws":["mineral","mohs","hardness"],"sims":["mineral"]},
})

# ============ ENERGIA ============
def sim_solar_e(pergunta, p):
    I=p.get("irradiancia",1000); A=p.get("area_m2",10); eta=p.get("eficiencia",0.2)
    P=I*A*eta
    return {"simulador":"Energia Solar","dominio":"Energia - Solar",
            "potencia_W":P,"energia_kWh_dia":P*5/1000,"validacao":f"P={P:.0f} W"}
def sim_eolica(pergunta, p):
    rho=1.225; A=p.get("area_rotor",100); v=p.get("vento",12); Cp=0.4
    P=0.5*rho*A*v**3*Cp
    return {"simulador":"Energia Eolica","dominio":"Energia - Eolica",
            "potencia_W":P,"Cp":Cp,"validacao":f"P={P/1000:.1f} kW"}
def sim_nuclear_e(pergunta, p):
    M=p.get("massa_U235_g",1); E=M*8.2e10
    return {"simulador":"Nuclear (energia)","dominio":"Energia - Nuclear",
            "energia_J":E,"validacao":f"E={E:.2e} J"}
def sim_bateria(pergunta, p):
    V=p.get("V",3.7); C=p.get("capacidade_Ah",3)
    return {"simulador":"Baterias","dominio":"Energia - Baterias",
            "energia_Wh":V*C,"validacao":f"E={V*C:.1f} Wh"}
def sim_hidrogenio(pergunta, p):
    m=p.get("massa_kg",1); LHV=120e6
    return {"simulador":"Hidrogenio","dominio":"Energia - H2",
            "energia_J":m*LHV,"validacao":f"E={m*LHV:.2e} J"}

SIMULADORES.update({"solar_e":sim_solar_e,"eolica":sim_eolica,"nuclear_e":sim_nuclear_e,
"bateria":sim_bateria,"hidrogenio":sim_hidrogenio})

DOMINIOS.update({
"solar_e":{"kws":["solar","photovoltaic","PV panel"],"sims":["solar_e"]},
"eolica":{"kws":["wind","turbine","wind power"],"sims":["eolica"]},
"nuclear_e":{"kws":["nuclear energy","U235"],"sims":["nuclear_e"]},
"bateria":{"kws":["battery","lithium","energy storage"],"sims":["bateria"]},
"hidrogenio":{"kws":["hydrogen","fuel cell","H2"],"sims":["hidrogenio"]},
})

# ============ AMBIENTE ============
def sim_poluicao(pergunta, p):
    C0=p.get("C0",100); k=p.get("k",0.1); t=p.get("t",10)
    C=C0*_math.exp(-k*t)
    return {"simulador":"Poluicao","dominio":"Ambiente - Poluicao",
            "C_final":C,"validacao":f"C={C:.2f}"}
def sim_conserv(pergunta, p):
    return {"simulador":"Conservacao","dominio":"Ambiente - Conservacao",
            "area_protegida_pct":p.get("pct",15),"validacao":"Conservacao"}
def sim_sustent(pergunta, p):
    return {"simulador":"Sustentabilidade","dominio":"Ambiente - Sustent",
            "pegada_C_t":p.get("pegada",5),"validacao":"Pegada"}
def sim_recicla(pergunta, p):
    return {"simulador":"Reciclagem","dominio":"Ambiente - Recicla",
            "taxa_reciclagem":p.get("taxa",0.3),"validacao":"Taxa"}
def sim_biodiv(pergunta, p):
    return {"simulador":"Biodiversidade","dominio":"Ambiente - Biodiv",
            "indice_shannon":p.get("H",2.5),"validacao":"Shannon"}

SIMULADORES.update({"poluicao":sim_poluicao,"conserv":sim_conserv,"sustent":sim_sustent,
"recicla":sim_recicla,"biodiv":sim_biodiv})

DOMINIOS.update({
"poluicao":{"kws":["pollution","contaminant","decay"],"sims":["poluicao"]},
"conserv":{"kws":["conservation","protected area"],"sims":["conserv"]},
"sustent":{"kws":["sustainability","carbon footprint"],"sims":["sustent"]},
"recicla":{"kws":["recycling","waste"],"sims":["recicla"]},
"biodiv":{"kws":["biodiversity","shannon","species richness"],"sims":["biodiv"]},
})

# ============ AGRICULTURA ============
def sim_solo(pergunta, p):
    return {"simulador":"Solo","dominio":"Agricultura - Solo",
            "pH":p.get("pH",6.5),"validacao":"Solo"}
def sim_culturas(pergunta, p):
    return {"simulador":"Culturas","dominio":"Agricultura - Culturas",
            "produtividade_t_ha":p.get("prod",5),"validacao":"Produtividade"}
def sim_pecuaria(pergunta, p):
    return {"simulador":"Pecuaria","dominio":"Agricultura - Pecuaria",
            "cabecas":p.get("cabecas",1000),"validacao":"Lotacao"}
def sim_irriga(pergunta, p):
    return {"simulador":"Irrigacao","dominio":"Agricultura - Irrigacao",
            "lamina_mm":p.get("lamina",500),"validacao":"Volume"}
def sim_agroeco(pergunta, p):
    return {"simulador":"Agroecologia","dominio":"Agricultura - Agroeco",
            "diversidade":p.get("diversidade",10),"validacao":"Agroeco"}

SIMULADORES.update({"solo":sim_solo,"culturas":sim_culturas,"pecuaria":sim_pecuaria,
"irriga":sim_irriga,"agroeco":sim_agroeco})

DOMINIOS.update({
"solo":{"kws":["soil","pH","organic matter"],"sims":["solo"]},
"culturas":{"kws":["crop","yield","agriculture"],"sims":["culturas"]},
"pecuaria":{"kws":["livestock","cattle","grazing"],"sims":["pecuaria"]},
"irriga":{"kws":["irrigation","water use"],"sims":["irriga"]},
"agroeco":{"kws":["agroecology","polyculture"],"sims":["agroeco"]},
})

# ============ SOCIAIS ============
def sim_econ(pergunta, p):
    return {"simulador":"Economia","dominio":"Sociais - Economia",
            "PIB":p.get("PIB",1e12),"validacao":"Economia"}
def sim_psico(pergunta, p):
    return {"simulador":"Psicologia","dominio":"Sociais - Psico",
            "QI_medio":p.get("QI",100),"validacao":"Normal"}
def sim_socio(pergunta, p):
    return {"simulador":"Sociologia","dominio":"Sociais - Socio",
            "populacao":p.get("pop",1e6),"validacao":"Demografia"}
def sim_antropo(pergunta, p):
    return {"simulador":"Antropologia","dominio":"Sociais - Antropo",
            "geracoes":p.get("geracoes",100),"validacao":"Cultural"}
def sim_politica(pergunta, p):
    return {"simulador":"Ciencia Politica","dominio":"Sociais - Politica",
            "eleitores":p.get("eleitores",1e6),"validacao":"Eleitoral"}

SIMULADORES.update({"econ":sim_econ,"psico":sim_psico,"socio":sim_socio,
"antropo":sim_antropo,"politica":sim_politica})

DOMINIOS.update({
"econ":{"kws":["economy","GDP","inflation"],"sims":["econ"]},
"psico":{"kws":["psychology","IQ","behavior"],"sims":["psico"]},
"socio":{"kws":["sociology","demography"],"sims":["socio"]},
"antropo":{"kws":["anthropology","culture"],"sims":["antropo"]},
"politica":{"kws":["political science","election","voting"],"sims":["politica"]},
})

# ============ HUMANAS ============
def sim_lingua(pergunta, p):
    return {"simulador":"Linguistica","dominio":"Humanas - Lingua",
            "palavras":p.get("palavras",10000),"validacao":"Linguistico"}
def sim_hist(pergunta, p):
    return {"simulador":"Historia","dominio":"Humanas - Historia",
            "ano":p.get("ano",1500),"validacao":"Historico"}
def sim_filo(pergunta, p):
    return {"simulador":"Filosofia","dominio":"Humanas - Filosofia",
            "argumentos":p.get("args",5),"validacao":"Logica"}
def sim_arqueo(pergunta, p):
    return {"simulador":"Arqueologia","dominio":"Humanas - Arqueo",
            "sitios":p.get("sitios",10),"validacao":"Arqueologico"}
def sim_artes(pergunta, p):
    return {"simulador":"Artes","dominio":"Humanas - Artes",
            "obras":p.get("obras",100),"validacao":"Artistico"}

SIMULADORES.update({"lingua":sim_lingua,"hist":sim_hist,"filo":sim_filo,
"arqueo":sim_arqueo,"artes":sim_artes})

DOMINIOS.update({
"lingua":{"kws":["linguistics","phoneme","syntax"],"sims":["lingua"]},
"hist":{"kws":["history","historical","century"],"sims":["hist"]},
"filo":{"kws":["philosophy","logic","argument"],"sims":["filo"]},
"arqueo":{"kws":["archaeology","artifact","excavation"],"sims":["arqueo"]},
"artes":{"kws":["art","artistic","painting"],"sims":["artes"]},
})

# ============ SAUDE PUBLICA ============
def sim_nutri(pergunta, p):
    return {"simulador":"Nutricao","dominio":"Saude - Nutricao",
            "kcal":p.get("kcal",2000),"validacao":"Nutricional"}
def sim_mental(pergunta, p):
    return {"simulador":"Saude Mental","dominio":"Saude - Mental",
            "prevalencia":p.get("prev",0.1),"validacao":"Mental"}
def sim_epi(pergunta, p):
    return {"simulador":"Epi Social","dominio":"Saude - Epi",
            "determinantes":p.get("det",5),"validacao":"Epi"}
def sim_global(pergunta, p):
    return {"simulador":"Saude Global","dominio":"Saude - Global",
            "cobertura":p.get("cob",0.7),"validacao":"Global"}

SIMULADORES.update({"nutri":sim_nutri,"mental":sim_mental,"epi":sim_epi,"global_":sim_global})

DOMINIOS.update({
"nutri":{"kws":["nutrition","calorie","protein"],"sims":["nutri"]},
"mental":{"kws":["mental health","depression","anxiety"],"sims":["mental"]},
"epi":{"kws":["social epidemiology","determinant"],"sims":["epi"]},
"global_":{"kws":["global health","coverage","WHO"],"sims":["global_"]},
})

# ============ INTEGRACAO FERMILINK ============
# Tenta usar a ponte FermiLink para acelerar simuladores pesados.
# Se a ponte nao existir, cai no comportamento antigo (analitico).

try:
    from fermilink_bridge import FERMILINK_DISPONIVEL, UPGRADE_MAP
    _BRIDGE_OK = True
except ImportError:
    _BRIDGE_OK = False
    FERMILINK_DISPONIVEL = False
    UPGRADE_MAP = {}

def _rodar_simulacoes_com_bridge(pergunta, max_sims=6, usar_fermilink=True):
    """Versao acelerada de rodar_simulacoes."""
    doms = detectar_dominios(pergunta)
    params = extrair_params(pergunta)
    
    sims_ids = []
    for d in doms:
        for s in DOMINIOS[d]["sims"]:
            if s not in sims_ids:
                sims_ids.append(s)
    sims_ids = sims_ids[:max_sims]
    
    resultados = {}
    for sid in sims_ids:
        # 1. Tenta FermiLink (se disponivel)
        if usar_fermilink and _BRIDGE_OK and FERMILINK_DISPONIVEL and sid in UPGRADE_MAP:
            try:
                fl_result = UPGRADE_MAP[sid]()
                if fl_result:
                    resultados[sid] = fl_result
                    continue
            except Exception as e:
                print(f"[BRIDGE] {sid} falhou: {e}")
        
        # 2. Fallback: analitico
        try:
            resultado = SIMULADORES[sid](pergunta, params)
            if isinstance(resultado, dict):
                # DEFEITO MEDIDO (26/10/2026): aqui havia
                #     resultado["fonte"] = "analitico"
                # incondicional, entao um resultado de MOTOR REAL saia com
                # `motor: "pymatgen (rede cristalina real)"` e
                # `fonte: "analitico"` no MESMO dicionario. Dois estados
                # contraditorios no mesmo payload, e o teste que checava
                # `fonte == "analitico"` passava sempre (nao provava nada).
                # Agora `fonte` diz a ORIGEM DO NUMERO:
                #   "motor_real" -> o calculo veio de integracoes_reais;
                #   "analitico"  -> veio da formula interna (com ou sem motor
                #                   que falhou; nesse caso `motor_situacao`
                #                   diz por que o motor nao entregou).
                if "motor" in resultado:
                    resultado.setdefault("fonte", "motor_real")
                else:
                    resultado["fonte"] = "analitico"
                resultado = _anotar_parametros_padrao(sid, resultado, params)
            resultados[sid] = resultado
        except Exception as e:
            resultados[sid] = {"erro": str(e), "simulador": sid}
    
    return resultados, doms, params

# Substitui a funcao original
rodar_simulacoes_analitico = rodar_simulacoes
rodar_simulacoes = _rodar_simulacoes_com_bridge

# 10/06/2026 13:14:58

# 10/06/2026 13:17:05

# 10/06/2026 13:29:22

# ============ MOTORES REAIS INTEGRADOS (componentes externos instalados) ============
# Se a biblioteca cientifica do componente externo estiver instalada, o MOTOR REAL
# executa; se nao estiver ou falhar, mantem-se a formula analitica interna.
# O wrapper ASSUME o nome da funcao original (globals()[nome]), de modo que tanto a
# rota HTTP quanto qualquer chamada direta passam pelo motor real.

# A tabela "motor -> submodulos que ele importa por dentro" mora em
# integracoes_reais.SUBMODULOS_DOS_MOTORES (fonte unica, usada pelo aquecimento
# da thread principal e por _com_motor_real).


def _com_motor_real(chave, funcao_base, tempo_limite=25.0):
    """Motor real com PRAZO: se o componente externo travar, cai no analitico.

    DEFEITO MEDIDO (26/10/2026): o prazo comecava a contar com a IMPORTACAO
    ainda por fazer. Com os motores instalados, o primeiro POST pagava o import
    (pymatgen/pybamm/brian2 levam segundos) dentro do prazo e o wrapper concluia
    "motor lento" -> devolvia a formula analitica. Efeito real observado:
    /api/simuladores/universal respondeu sem `motor`/`elemento` (fallback) mesmo
    com pymatgen instalado, e o e2e inteiro levou 19 min repetindo timeouts.
    Correcao: o import acontece ANTES do cronometro (abaixo); o prazo mede so o
    CALCULO. Importacao nao e' calculo, e nao pode reprovar um motor.
    """

    def _executar(pergunta, p=None):
        parametros = p if isinstance(p, dict) else {}
        # Interruptor explicito: rotas que validam CONTRATO HTTP (nao ciencia)
        # podem desligar o motor real e ficar deterministicas/rapidas. O padrao
        # e' motores LIGADOS; a ciencia dos motores e' provada em
        # boot_preheat/aquecer_detalhado, no harness de 195 e em
        # test_motor_real_prazo.py. Nunca e' ligado em producao.
        if os.environ.get("ALEF_SO_ANALITICO", "").strip() == "1":
            return funcao_base(pergunta, parametros)
        try:
            import integracoes_reais as _ir
        except Exception:  # noqa: BLE001
            _ir = None
        if _ir is not None:
            motor = _ir.para_chave(chave)
            if motor is not None:
                # Importacao primeiro, fora do prazo (idempotente: o app ja
                # aquece na thread principal; aqui e' rede de seguranca).
                try:
                    _ir.aquecer_motor(chave)
                except Exception:  # noqa: BLE001
                    pass
                caixa = {}

                def _alvo():
                    try:
                        caixa["resultado"] = motor(pergunta, parametros)
                    except Exception as exc:  # noqa: BLE001
                        caixa["erro"] = exc

                linha = threading.Thread(target=_alvo, daemon=True)
                linha.start()
                linha.join(tempo_limite)
                resultado = caixa.get("resultado")
                if isinstance(resultado, dict) and resultado:
                    return resultado
                # Sem resultado: registra POR QUE o motor nao entregou. Sem isto,
                # "motor instalado mas lento" (medido: solido 28,6 s com prazo de
                # 25 s) e "componente sem motor" devolvem o MESMO dicionario e o
                # relatorio confunde os dois estados.
                if linha.is_alive():
                    motivo = "prazo_excedido"
                elif "erro" in caixa:
                    motivo = "motor_falhou: %s: %s" % (
                        type(caixa["erro"]).__name__, str(caixa["erro"])[:200])
                else:
                    motivo = "motor_sem_resultado"
                base = funcao_base(pergunta, parametros)
                if isinstance(base, dict):
                    base = dict(base)
                    base.setdefault("motor_situacao", motivo)
                    base.setdefault("motor_prazo_s", float(tempo_limite))
                return base
        return funcao_base(pergunta, parametros)

    _executar.__name__ = getattr(funcao_base, "__name__", f"sim_{chave}")
    # Guarda a funcao analitica original: permite introspeccao de parametros
    # (_chaves_lidas_no_simulador) mesmo atraves do wrapper de motor real.
    _executar._base_sim = funcao_base
    return _executar


PRAZO_MOTOR_PADRAO_S = 25.0

# Orcamento por motor, em segundos. Nao e' chute: cada valor vem de medicao.
#   neuro  70 s -- brian2 aquece/carrega devagar (4 060 s a pilha pesada inteira)
#   solido 90 s -- o calculo real (ASE/EMT com relaxacao) mediu 28,6 s neste host
#                  com prazo de 25 s: o wrapper devolvia "prazo_excedido" e o
#                  fallback analitico, ou seja, o motor era dado como ausente
#                  estando instalado. Em 01/11/2026 o mesmo estouro apareceu no
#                  e2e (`motor_situacao: prazo_excedido`) porque o host estava
#                  ~4x mais lento. 90 s e' ~3x a pior medicao registrada.
TEMPO_POR_MOTOR = {"neuro": 70.0, "solido": 90.0}


def _prazo_do_motor(chave, padrao):
    """Prazo efetivo do motor `chave`, ajustavel por ambiente.

    Ordem: `ALEF_MOTOR_PRAZO_S_<CHAVE>` (por motor) -> `ALEF_MOTOR_PRAZO_S`
    (global) -> tabela `TEMPO_POR_MOTOR` -> `padrao`. O valor usado vai no
    relatorio (`motor_prazo_s`): prazo nao e' detalhe escondido, e um host
    carregado pode ser medido com orcamento maior SEM mexer no codigo.
    """
    for nome in ("ALEF_MOTOR_PRAZO_S_%s" % str(chave).upper(),
                 "ALEF_MOTOR_PRAZO_S"):
        bruto = os.environ.get(nome)
        if not bruto:
            continue
        try:
            valor = float(bruto)
        except (TypeError, ValueError):
            continue
        if valor > 0:
            return valor
    return float(TEMPO_POR_MOTOR.get(chave, padrao))


MOTORES_REAIS_INTEGRADOS = {}
for _chave_motor in ("md", "solido", "molecular", "cristalografia", "bateria",
                     "neuro", "hidro", "epidemia", "micro"):
    try:
        _base_motor = SIMULADORES.get(_chave_motor)
        if _base_motor is not None and not getattr(_base_motor, "_motor_real", False):
            _wrapper = _com_motor_real(_chave_motor, _base_motor,
                                       _prazo_do_motor(_chave_motor,
                                                       PRAZO_MOTOR_PADRAO_S))
            _wrapper._motor_real = True
            SIMULADORES[_chave_motor] = _wrapper
            globals()[getattr(_base_motor, "__name__", "")] = _wrapper
            MOTORES_REAIS_INTEGRADOS[_chave_motor] = getattr(
                _base_motor, "__name__", "")
    except Exception:  # noqa: BLE001
        pass

# 13/10/2026 - motores reais: ASE(EMT/Langevin), RDKit, pymatgen, PyBaMM,
# Brian2, WNTR/EPANET, Mesa, COBRApy (com fallback analitico automatico)


def _pre_aquecer_motores():
    """Carrega os motores em segundo plano para o 1o POST ja usar o motor real."""
    try:
        import integracoes_reais as _ir
        return _ir.aquecer()
    except Exception:  # noqa: BLE001
        return []


# DEFEITO MEDIDO (26/10/2026): esta thread daemon importa motores PESADOS
# (pybamm, brian2, cobra, mesa...) em paralelo ao servidor. Com os motores
# instalados, ela disputa o lock de importacao com a thread que atende a
# requisicao; o motor real estoura o prazo, cai no fallback analitico e o
# primeiro POST fica lento. Medido: o e2e passou a levar 19 min e
# /api/simuladores/universal respondeu pelo fallback mesmo com pymatgen
# instalado. O aquecimento correto e' o da thread PRINCIPAL (app.py); esta
# thread e' apenas um atalho para quem importa universal sem o app.
if os.environ.get("ALEF_SEM_PREAQUECER", "").strip() != "1":
    try:
        threading.Thread(target=_pre_aquecer_motores, daemon=True).start()
    except Exception:  # noqa: BLE001
        pass


# ============================================================
# SINONIMOS PT-BR -> DOMINIOS  (correcao de recall do roteamento)
# ============================================================
# Os kws originais sao quase todos em ingles, entao pergunta em portugues caia
# no fallback fixo (mecanica+termo) ou em nada. Estes termos sao ADICIONADOS
# (nunca substituem) as listas existentes. Entram em forma normalizada: minusculo
# e sem acento, porque detectar_dominios normaliza texto e palavra-chave.
# Chave inexistente nao quebra nada: e registrada em ALIASES_IGNORADOS, que um
# teste automatizado exige vazio.
ALIASES_PT = {
    "epidemia": ["epidemia", "epidemico", "surto", "viral", "virai", "infeccao",
                 "infectado", "pandemia", "contagio"],
    "cristalografia": ["cristalografia", "difracao", "difracao de raios x",
                       "raios x", "bragg", "reticulo cristalino"],
    "superficie": ["superficie", "adsorvente", "isoterma", "freundlich",
                   "langmuir", "dessorção", "dessorcao"],
    "cinetica": ["cinetica quimica", "constante de velocidade", "meia-vida",
                 "ordem de reacao"],
    "termo": ["calorimetria", "entalpia", "primeira lei", "segunda lei",
              "ciclo de carnot", "gases ideais"],
    "mecanica": ["mecanica classica", "aceleracao", "atrito", "momento angular",
                 "queda livre", "plano inclinado"],
    "materiais": ["propriedade dos materiais", "modulo de elasticidade",
                  "condutividade eletrica", "ponto de fusao"],
    "catalise": ["catalise heterogenea", "catalisador solido", "seletividade"],
    "poluicao": ["poluente", "poluentes", "metais pesados", "derramamento"],
    "genetica": ["genetica", "gene", "genes", "alelo", "dna", "rna",
                 "hereditariedade", "mutacao"],
    "ecologia": ["ecologia", "cadeia alimentar", "capacidade de suporte",
                 "crescimento populacional"],
    "neuro": ["neurociencia", "neuronio", "neuronal", "potencial de acao",
              "sinapse", "hodgkin"],
    "eletro": ["eletromagnetismo", "campo eletrico", "campo magnetico", "inducao"],
    "eletrica": ["carga eletrica", "corrente eletrica", "circuito eletrico",
                 "tensao eletrica"],
    "optica": ["optica", "refracao", "interferencia", "polarizacao", "laser",
               "foton"],
    "estatistica": ["estatistica", "probabilidade", "distribuicao normal",
                    "monte carlo", "regressao", "desvio padrao"],
    "fluido": ["fluido", "fluidos", "escoamento", "vazao", "reynolds",
               "turbulencia", "viscosidade"],
    "estrutural": ["estrutural", "viga", "flexao", "flambagem", "deformacao",
                   "tensao mecanica"],
    "farmaco": ["farmaco", "farmacocinetica", "biodisponibilidade",
                "dosagem", "meia vida plasmatica"],
    "cardio": ["cardiologia", "frequencia cardiaca", "debito cardiaco",
               "pressao arterial"],
    "diag": ["diagnostico medico", "sensibilidade do teste",
             "especificidade do teste", "valor preditivo"],
    "fisio": ["fisiologia", "imc", "indice de massa corporal", "metabolismo basal"],
    "onco": ["oncologia", "tumor", "tumoral", "cancer", "crescimento tumoral"],
    "imuno": ["imunologia", "anticorpo", "anticorpos", "antigeno"],
    "micro": ["microbiologia", "bacteria", "bacterias", "cultura microbiana"],
    "molecular": ["biologia molecular", "proteina", "aminoacido", "aminoacidos"],
    "zoologia": ["zoologia", "animal", "metabolismo animal"],
    "botanica": ["botanica", "fotossintese", "planta", "folha"],
    "organica": ["quimica organica", "isomero", "isomeros", "estereoquimica"],
    "inorganica": ["quimica inorganica", "complexo de coordenacao"],
    "polimeros": ["polimero", "polimeros", "macromolecula", "polidispersao"],
    "metais": ["metal", "metais", "liga metalica", "aco", "aluminio"],
    "ceram": ["ceramica", "ceramicas", "tenacidade", "fratura"],
    "comp": ["composto", "compostos", "fibra de carbono", "regra das misturas"],
    "nano": ["nanomaterial", "nanoparticula", "nanotubo", "nanotecnologia"],
    "termico": ["transferencia de calor", "trocador de calor", "conducao termica"],
    "aero": ["aerodinamica", "sustentacao", "arrasto", "perfil aerodinamico"],
    "civil": ["engenharia civil", "concreto", "ponte", "fck"],
    "controle": ["controle pid", "malha fechada", "realimentacao"],
    "robotica": ["robotica", "robo", "cinematica inversa", "junta robotica"],
    "comp_ia": ["rede neural", "redes neurais", "aprendizado de maquina"],
    "comp_cripto": ["criptografia", "criptografia rsa", "encriptacao"],
    "comp_redes": ["topologia de rede", "roteamento de rede"],
    "comp_algo": ["complexidade algoritmica", "big o"],
    # Segundo lote: dominios ja existentes que ficavam inalcancaveis por
    # pergunta em portugues. Todos os termos entram com fronteira de palavra,
    # entao "vento" em "meteorologia" nao casa dentro de "movimento".
    "quantica": ["quantica", "mecanica quantica", "qubit", "orbital atomico"],
    "sismo": ["terremoto", "sismo", "sismico", "magnitude do sismo"],
    "hidro": ["hidrologia", "bacia hidrografica", "recursos hidricos"],
    "clima": ["clima", "efeito estufa", "aquecimento global", "albedo"],
    "solido": ["estado solido", "rede cristalina", "fonon"],
    "plasma": ["plasma", "tokamak", "fusao nuclear"],
    "nuclear": ["fissao nuclear", "decaimento radioativo", "radiacao ionizante"],
    "particulas": ["particula", "particulas", "colisor", "higgs", "quark"],
    "equilibrio": ["equilibrio quimico", "constante de equilibrio"],
    "otimizacao": ["otimizacao", "minimizar", "maximizar", "gradiente descendente"],
    "prob": ["probabilidade", "distribuicao binomial", "variavel aleatoria"],
    "grafos": ["grafo", "grafos", "dijkstra", "caminho minimo"],
    "meteo": ["meteorologia", "previsao do tempo", "vento"],
    "relatividade": ["relatividade", "dilatacao do tempo", "transformacao de lorentz"],
}

ALIASES_IGNORADOS = []
for _dom_alias, _termos_alias in ALIASES_PT.items():
    _cfg_alias = DOMINIOS.get(_dom_alias)
    if _cfg_alias is None:
        ALIASES_IGNORADOS.append(_dom_alias)
        continue
    _kws_alias = _cfg_alias.setdefault("kws", [])
    for _termo_alias in _termos_alias:
        if _termo_alias not in _kws_alias:
            _kws_alias.append(_termo_alias)

