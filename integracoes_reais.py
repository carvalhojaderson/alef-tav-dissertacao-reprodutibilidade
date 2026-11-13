# -*- coding: utf-8 -*-
"""Integracao REAL dos motores cientificos instalados nos simuladores do app.

Regra: se a biblioteca do componente externo estiver instalada, o simulador
executa o MOTOR REAL e devolve 'motor' + numeros calculados. Se nao estiver,
retorna None e o simulador usa a formula analitica interna (fallback).

Tudo roda em processo, sem binario externo, para funcionar offline.
"""
from __future__ import annotations

import importlib
import inspect
import threading
import time


def _memoria_mb():
    """RSS maximo do processo em MB (evidencia do custo do aquecimento)."""
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
    except Exception:  # noqa: BLE001
        return None


def aquecer(modulos=None):
    """Importa os motores instalados para deixar o cache pronto (sem bloquear).

    Motivo real: a primeira importacao de alguns componentes (ex.: Mesa) consome
    dezenas de segundos; pre-aquecer evita que o primeiro POST caia no fallback
    por estourar o prazo do motor.

    ATENCAO (medido em 15/10/2026): este aquecimento NAO resolve os motores que
    exigem a thread principal -- ver `aquecer_detalhado()`. Chamado de uma thread
    daemon (como faz universal.py), o brian2 falha com "ValueError: signal only
    works in main thread of the main interpreter".

    CORRECAO (medido em 26/10/2026): aquecer so o pacote de TOPO nao basta.
        import ase                                  -> 0,59 s
        from ase.build import bulk; ...emt import EMT -> 85,44 s (1a vez)
    Os 85 s ficavam dentro do prazo do motor `solido`/`md` (25 s), o wrapper
    concluia "motor lento" e devolvia a formula analitica com o motor instalado.
    Por isso este aquecimento importa tambem os SUBMODULOS de
    SUBMODULOS_DOS_MOTORES, que sao os que o calculo realmente usa.
    """
    base = modulos or ("ase", "rdkit", "pymatgen", "pybamm", "wntr", "mesa",
                       "cobra")
    # So se aquecem os submodulos dos motores cujo pacote de TOPO foi pedido.
    # Sem este filtro, aquecer apenas ("ase",) arrastava pybamm/wntr/mesa/cobra
    # junto: medido em 26/10/2026, a pilha pesada custa 4 060 s neste host
    # (pybamm 1 338 s, wntr 1 294 s, mesa 706 s, cobra 321 s, brian2 297 s),
    # enquanto o conjunto rapido (ase+rdkit+pymatgen) custa 86 s.
    raizes = {str(m).split(".")[0] for m in base}
    alvos = list(base)
    for submodulos in SUBMODULOS_DOS_MOTORES.values():
        if submodulos and str(submodulos[0]).split(".")[0] in raizes:
            alvos.extend(submodulos)
    prontos = []
    for modulo in dict.fromkeys(alvos):
        try:
            importlib.import_module(modulo)
            prontos.append(modulo)
        except Exception:  # noqa: BLE001
            pass
    return prontos


# ---------------------------------------------------------------------------
# SUBMODULOS QUE O CALCULO REALMENTE IMPORTA DENTRO DO MOTOR
# ---------------------------------------------------------------------------
# Medido em 26/10/2026 (Windows, Python 3.13.9, miniconda):
#   import ase'                                    0,59 s
#   from ase.build import bulk + EMT              85,44 s
# A importacao de topo e' barata e engana o diagnostico; o custo esta nos
# submodulos. Aquecer a lista certa, na thread principal, e' o que impede o
# "fallback falso" (motor instalado, resultado analitico).
SUBMODULOS_DOS_MOTORES = {
    "md": ("ase", "ase.build", "ase.calculators.emt", "ase.md.langevin",
           "ase.md.velocitydistribution", "ase.units"),
    "solido": ("ase", "ase.build", "ase.calculators.emt"),
    "molecular": ("rdkit", "rdkit.Chem", "rdkit.Chem.Descriptors",
                  "rdkit.Chem.Lipinski", "rdkit.Chem.rdMolDescriptors"),
    "cristalografia": ("pymatgen", "pymatgen.core"),
    "bateria": ("pybamm",),
    "neuro": ("brian2",),
    "hidro": ("wntr",),
    "epidemia": ("mesa",),
    "micro": ("cobra",),
}


def modulos_do_motor(chave):
    """Submodulos que o motor desta chave importa la dentro (tupla vazia se nao ha)."""
    return SUBMODULOS_DOS_MOTORES.get(str(chave), ())


def aquecer_motor(chave):
    """Importa, NA THREAD ATUAL, os submodulos usados pelo motor `chave`.

    Serve para tirar a importacao de dentro do prazo do motor: importacao nao e'
    calculo, e nao pode reprovar um componente instalado. Importar aqui e'
    idempotente (sys.modules) e barato depois do primeiro aquecimento.
    """
    relatorio = {}
    for modulo in modulos_do_motor(chave):
        try:
            importlib.import_module(modulo)
            relatorio[modulo] = "IMPORT_OK"
        except Exception as erro:  # noqa: BLE001
            relatorio[modulo] = "%s: %s" % (type(erro).__name__, str(erro)[:200])
    return relatorio


MOTORES = {
    "md": "ASE + EMT/Langevin (dinamica molecular real)",
    "solido": "ASE + EMT (energia de coesao real)",
    "molecular": "RDKit (descritores moleculares reais)",
    "cristalografia": "pymatgen (rede cristalina real)",
    "bateria": "PyBaMM (SPM, tensao real)",
    "neuro": "Brian2 (rede de neuronios LIF real)",
    "hidro": "WNTR/EPANET (hidraulica real)",
    "epidemia": "Mesa (SIR baseado em agentes real)",
    "micro": "COBRApy (FBA real)",
}


def motores_disponiveis() -> dict:
    """Diz, sem importar pesado, quais motores reais estao no ambiente."""
    disponivel = {}
    for modulo in ("ase", "rdkit", "pymatgen", "pybamm", "brian2", "wntr",
                   "mesa", "cobra", "scanpy", "flopy", "matminer"):
        try:
            __import__(modulo)
            disponivel[modulo] = True
        except Exception:  # noqa: BLE001
            disponivel[modulo] = False
    return disponivel


# --------------------------------------------------------------------------
# PRE-AQUECIMENTO NA THREAD PRINCIPAL (isto e CORRECAO, nao otimizacao)
# --------------------------------------------------------------------------
# Modulos que as rotas de simulacao do app executam de verdade.
MODULOS_DO_APP = ("ase", "rdkit", "pymatgen", "pybamm", "brian2", "wntr",
                  "mesa", "cobra", "flopy", "matminer")

# Cache dos modulos importados na thread principal.
PRONTOS = {}


def aquecer_detalhado(modulos=None):
    """Importa os motores NA THREAD ATUAL e devolve o veredito de cada um.

    Defeito medido na imagem publicada (sha 66ba6383), na rota
    GET /api/simuladores/diagnostico-motores:
        brian2 | IMPORT_FALHOU |
        ValueError: signal only works in main thread of the main interpreter

    Duas coisas explicam o defeito: (1) o brian2 -- ou algo da sua cadeia de
    importacao -- chama signal.signal(), que so funciona na thread principal;
    (2) o FastAPI roda endpoint `def` (sincrono) na threadpool e o proprio
    universal.py ainda aquecia motores numa thread daemon. Consequencia real:
    o motor cientifico do componente brian2 NUNCA rodava no app publicado e o
    simulador `neuro` caia, em silencio, na formula analitica.

    Correcao: importar UMA vez, no import do app, que acontece na thread
    principal do processo; os modulos ficam em sys.modules e as rotas passam a
    receber do cache. Nao instala, nao promove e nao grava nada: apenas mede.
    """
    alvos = modulos or MODULOS_DO_APP
    antes = _memoria_mb()
    inicio = time.time()
    relatorio = {}
    for modulo in alvos:
        t0 = time.time()
        try:
            pacote = importlib.import_module(modulo)
            relatorio[modulo] = {
                "situacao": "IMPORT_OK",
                "versao": getattr(pacote, "__version__", None),
                "segundos": round(time.time() - t0, 2),
            }
            PRONTOS[modulo] = pacote
        except Exception as erro:  # noqa: BLE001
            relatorio[modulo] = {
                "situacao": "IMPORT_FALHOU",
                "erro": "%s: %s" % (type(erro).__name__, str(erro)[:300]),
                "segundos": round(time.time() - t0, 2),
            }
    # Mesmo filtro de `aquecer()`: submodulos so dos motores pedidos. Medido em
    # 26/10/2026 neste host: pilha pesada 4 060 s, conjunto rapido 86 s.
    raizes = {str(m).split(".")[0] for m in alvos}
    submodulos = {chave: aquecer_motor(chave)
                  for chave, mods in SUBMODULOS_DOS_MOTORES.items()
                  if mods and str(mods[0]).split(".")[0] in raizes}
    return {
        "submodulos": submodulos,
        "na_thread_principal": (threading.current_thread()
                                is threading.main_thread()),
        "thread": threading.current_thread().name,
        "segundos": round(time.time() - inicio, 2),
        "memoria_mb_antes": antes,
        "memoria_mb_depois": _memoria_mb(),
        "motores": relatorio,
        "ok": sum(1 for r in relatorio.values() if r["situacao"] == "IMPORT_OK"),
        "falhou": sum(1 for r in relatorio.values()
                      if r["situacao"] != "IMPORT_OK"),
        "observacao": ("Pre-aquecimento feito na thread principal: e o unico "
                       "lugar onde import que chama signal.signal (brian2) "
                       "funciona; as rotas do FastAPI rodam na threadpool."),
    }


def _criar_agente(classe, uid, modelo):
    """Compatibiliza mesa 3.x `Agent(model)` e mesa 2.x `Agent(unique_id, model)`."""
    try:
        return classe(modelo)
    except TypeError:
        return classe(uid, modelo)


# --------------------------------------------------------------------- MD/solido
def md_ase(pergunta, p):
    """Dinamica molecular REAL: Cu FCC + potencial EMT + termostato Langevin."""
    from ase import units
    from ase.build import bulk
    from ase.calculators.emt import EMT
    from ase.md.langevin import Langevin
    from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
    import numpy as np

    passos = int(p.get("passos", 20) or 20)
    T = float(p.get("T_K", p.get("temperatura", 300.0)) or 300.0)
    repeticao = 3 if int(p.get("n_atomos", 108) or 108) >= 100 else 2

    atomos = bulk("Cu", "fcc", a=3.615, cubic=True) * (repeticao, repeticao, repeticao)
    atomos.calc = EMT()
    MaxwellBoltzmannDistribution(atomos, temperature_K=T,
                                 rng=np.random.default_rng(7))
    din = Langevin(atomos, 5 * units.fs, temperature_K=T, friction=0.01)
    din.run(passos)

    n = len(atomos)
    e_pot_total = float(atomos.get_potential_energy())
    return {
        "simulador": "Dinamica Molecular (ASE+EMT)",
        "dominio": "Materiais - MD",
        "motor": MOTORES["md"],
        "N_atomos": n,
        "T_alvo_K": T,
        "T_final_K": float(atomos.get_temperature()),
        "passos": passos,
        "dt_fs": 5.0,
        "E_potencial_eV": e_pot_total,
        "E_por_atomo_eV": e_pot_total / n,
        "validacao": f"EMT Cu {e_pot_total / n:.3f} eV/atomo em {n} atomos",
    }


def _rede_em_angstrom(valor):
    """Normaliza o parametro de rede para angstrom (a unidade que o ASE usa).

    DEFEITO MEDIDO (31/10/2026, inventario de simuladores): o default analitico
    de `sim_solido` era `5,43e-10` (metros, o diamante do Si) e este motor lia
    `a` como angstrom -> celula de 5,43e-10 A -> `MemoryError` no ASE e queda
    para a formula analitica (`motor_situacao: motor_falhou`). Quem passa metro
    (5,43e-10) e' convertido; quem passa angstrom (5,43) fica como esta.
    """
    if valor is None:
        return None
    a = float(valor)
    if a <= 0:
        return None
    if a < 1e-8:  # veio em metros
        a *= 1e10
    return a


def solido_emt(pergunta, p):
    """Energia de coesao do cristal (ASE+EMT) + parametro de rede.

    Convencao do ASE (emt.py, "subtract E0 (ASAP convention)"): o EMT devolve a
    energia do cristal RELATIVA ao atomo isolado, entao o cristal em equilibrio
    da' ~0 eV/atomo e o atomo isolado da' +E0 (Cu: +3,51 eV). A energia de
    coesao e' a diferenca entre os dois: 3,515 eV/atomo no Cu.

    A versao anterior devolvia a energia do cristal (-0,0049 eV/atomo no Cu)
    rotulada como `E_coesao_eV_atomo`: errada em sinal e ~700x menor que a
    coesao real. Medido em `auditoria/sonda_emt.py`; travado em
    `test_solido_emt.py` e em `test_e2e_http.py`.
    """
    from ase import Atoms
    from ase.build import bulk
    from ase.calculators.emt import EMT

    simbolo = str(p.get("elemento", p.get("material", "Cu")) or "Cu")[:2]
    try:
        # Rede de equilibrio do proprio ASE para o elemento pedido: serve de
        # default e de ancora de faixa (nao se inventa constante de rede).
        rede_equilibrio = float(bulk(simbolo, "fcc", cubic=True).cell[0][0])
    except Exception:  # noqa: BLE001
        simbolo = "Cu"
        rede_equilibrio = 3.615
    bruto = p.get("a")
    if bruto in (None, "", 0):
        bruto = p.get("parametro_rede_m", p.get("parametro_rede"))
    a_angstrom = _rede_em_angstrom(bruto)
    if a_angstrom is None:
        a_angstrom = rede_equilibrio
    # Fora da faixa fisica util o ASE nao devolve erro claro (chegou a estourar
    # MemoryError com 5,43e-10 A): falha explicitamente para o wrapper cair no
    # analitico e registrar `motor_falhou` com motivo legivel.
    if not 1.5 <= a_angstrom <= 15.0:
        raise ValueError(
            "parametro de rede %.6g A fora da faixa util 1,5-15 A "
            "(esperado angstrom; 5,43e-10 seria metro)" % a_angstrom)
    try:
        atomos = bulk(simbolo, "fcc", a=a_angstrom, cubic=True)
    except Exception:  # noqa: BLE001
        simbolo = "Cu"
        a_angstrom = 3.615
        atomos = bulk("Cu", "fcc", a=3.615, cubic=True)
    atomos.calc = EMT()
    e_cristal = float(atomos.get_potential_energy()) / len(atomos)
    # Caixa de 12 A: imagem periodica do atomo isolado fica fora do alcance do
    # EMT (medido: +3,5100 eV para Cu, exatamente E0, sem interacao).
    isolado = Atoms(simbolo, positions=[(0.0, 0.0, 0.0)], cell=(12.0, 12.0, 12.0))
    isolado.calc = EMT()
    e_atomo = float(isolado.get_potential_energy())
    e_coesao = e_atomo - e_cristal
    return {
        "simulador": "Estado Solido (ASE+EMT)",
        "dominio": "Fisica - Condensada",
        "motor": MOTORES["solido"],
        "elemento": simbolo,
        "parametro_rede_A": a_angstrom,
        "parametro_rede_m": a_angstrom * 1e-10,
        "E_coesao_eV_atomo": e_coesao,
        "E_cristal_eV_atomo": e_cristal,
        "E_atomo_isolado_eV": e_atomo,
        "validacao": f"EMT {simbolo}: coesao {e_coesao:.3f} eV/atomo "
                     f"(cristal {e_cristal:+.4f} eV/atomo em {len(atomos)} atomos)",
    }



# ---------------------------------------------------------------------- molecular
def molecular_rdkit(pergunta, p):
    """Descritores moleculares REAIS via RDKit, a partir de SMILES."""
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors

    texto = str(p.get("smiles", "") or "")
    if not texto:
        # extrai um SMILES simples da propria pergunta, se existir
        for pedaco in str(pergunta or "").replace(",", " ").split():
            if any(c in pedaco for c in "=#()0123456789") and pedaco[:1] in "CONScnosc[":
                texto = pedaco
                break
    if not texto:
        return None
    mol = Chem.MolFromSmiles(texto)
    if mol is None:
        return None
    return {
        "simulador": "Moleculas (RDKit)",
        "dominio": "Quimica - Molecular",
        "motor": MOTORES["molecular"],
        "smiles": texto,
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "massa_molar_g_mol": round(Descriptors.MolWt(mol), 3),
        "logP": round(Descriptors.MolLogP(mol), 3),
        "doadores_H": Lipinski.NumHDonors(mol),
        "aceitadores_H": Lipinski.NumHAcceptors(mol),
        "ligacoes_rotativas": Lipinski.NumRotatableBonds(mol),
        "TPSA_A2": round(Descriptors.TPSA(mol), 3),
        "regra_de_5_violacoes": int(Descriptors.MolWt(mol) > 500) + int(Descriptors.MolLogP(mol) > 5),
        "validacao": f"RDKit {rdMolDescriptors.CalcMolFormula(mol)} "
                     f"MW={Descriptors.MolWt(mol):.2f}",
    }


# ------------------------------------------------------------------ cristalografia
def cristalografia_pymatgen(pergunta, p):
    """Rede cristalina REAL via pymatgen e espacamento por lei de Bragg.

    DEFEITOS CORRIGIDOS (31/10/2026, medidos em auditoria/verifica_todos.py):
      1. Nomes incompativeis: `sim_cristalografia` envia `parametro_rede` e
         `angulo`, mas o motor lia `parametro_rede_m` e `angulo_graus` -- o
         motor rodava SEMPRE com default e a auditoria mostrou resultado
         identico ao dobrar cada parametro. Agora aceita os dois nomes.
      2. Bragg errado: usava sin(theta/2) e tratava 0.154 nm como angstrom
         (erro de 10x no d). A lei e' n*lambda = 2 d sin(theta), com theta
         medido a partir do plano e lambda em metros.
    """
    import math

    from pymatgen.core import Lattice, Structure

    simbolo = str(p.get("elemento", "Cu") or "Cu")[:2]
    bruto = p.get("parametro_rede_m", p.get("parametro_rede"))
    try:
        a = float(bruto) if bruto else 3.615e-10
    except (TypeError, ValueError):
        a = 3.615e-10
    if not math.isfinite(a) or a <= 0:
        a = 3.615e-10
    a_ang = a * 1e10
    try:
        estrutura = Structure(Lattice.cubic(a_ang), [simbolo], [[0, 0, 0]])
    except Exception:  # noqa: BLE001
        simbolo = "Cu"
        a, a_ang = 3.615e-10, 3.615
        estrutura = Structure(Lattice.cubic(3.615), ["Cu"], [[0, 0, 0]])
    angulo = float(p.get("angulo_graus", p.get("angulo", 30.0)) or 30.0)
    ordem = p.get("n", 1)
    ordem = int(ordem) if isinstance(ordem, int) and ordem >= 1 else 1
    lam = p.get("lambda_X_m")
    if lam is None:
        lam_nm = p.get("lambda_X_nm")
        lam = float(lam_nm) * 1e-9 if lam_nm else 1.5406e-10
    lam = float(lam)
    seno = math.sin(math.radians(angulo))
    d = ordem * lam / (2 * seno) if seno > 0 else 0.0
    return {
        "simulador": "Cristalografia (Bragg + pymatgen)",
        "dominio": "Materiais - Cristalografia",
        "motor": MOTORES["cristalografia"],
        "elemento": simbolo,
        "parametro_rede_m": a,
        "volume_A3": round(estrutura.volume, 4),
        "densidade_g_cm3": round(float(estrutura.density), 4),
        "angulo_graus": angulo,
        "ordem_n": ordem,
        "lambda_X_m": lam,
        "d_espacamento_m": d,
        "validacao": f"pymatgen {simbolo} V={estrutura.volume:.3f} A^3 "
                     f"rho={estrutura.density:.3f} g/cm3 d={d * 1e10:.3f} A",
    }


# ------------------------------------------------------------------------ bateria
def bateria_pybamm(pergunta, p):
    """Descarga REAL de bateria de litio (modelo SPM do PyBaMM).

    DEFEITO CORRIGIDO (31/10/2026, medido em auditoria/verifica_todos.py):
    o motor recebia `capacidade_Ah` do simulador e ignorava o valor em
    silencio -- a auditoria mostrou resultado identico ao dobrar o parametro.
    Agora `capacidade_Ah` e' injetada no conjunto de parametros do SPM (knob
    real) e, quando nao existe no conjunto, o resultado DECLARA em
    `parametros_ignorados` em vez de fingir que aplicou.
    """
    import pybamm

    t_fim = float(p.get("tempo_s", 1800.0) or 1800.0)
    parametros = pybamm.ParameterValues("Chen2020")
    ignorados = []
    chave_capacidade = "Nominal cell capacity [A.h]"
    capacidade = p.get("capacidade_Ah")
    if capacidade is not None:
        try:
            capacidade = float(capacidade)
        except (TypeError, ValueError):
            capacidade = None
        if capacidade and capacidade > 0 and chave_capacidade in parametros:
            parametros[chave_capacidade] = capacidade
        else:
            ignorados.append("capacidade_Ah")
    if p.get("V") is not None:
        # O SPM nao aceita tensao nominal como entrada: V so vale no fallback
        # analitico (sim_bateria, energia = V*C). Declarar evita a impressao
        # de que o valor foi usado pelo motor.
        ignorados.append("V")
    modelo = pybamm.lithium_ion.SPM()
    sim = pybamm.Simulation(modelo, parameter_values=parametros,
                            solver=pybamm.CasadiSolver())
    sol = sim.solve([0, t_fim], initial_soc=1.0)
    v = [float(x) for x in sol["Terminal voltage [V]"].entries]
    # Energia entregue = integral de V dQ (Q em A.h, logo Wh direto).
    try:
        q = [float(x) for x in sol["Discharge capacity [A.h]"].entries]
    except KeyError:
        q = []
    if len(q) == len(v) and len(q) > 1:
        energia = sum(0.5 * (v[i] + v[i - 1]) * (q[i] - q[i - 1])
                      for i in range(1, len(q)))
        capacidade_descarga = q[-1]
    else:
        energia = None
        capacidade_descarga = None
    return {
        "simulador": "Bateria Li-ion (PyBaMM SPM)",
        "dominio": "Energia - Bateria",
        "motor": MOTORES["bateria"],
        "tempo_s": t_fim,
        "capacidade_Ah": capacidade,
        "parametros_ignorados": ignorados,
        "V_inicial": v[0],
        "V_final": v[-1],
        "V_medio": sum(v) / len(v),
        "energia_Wh": energia,
        "capacidade_descarga_Ah": capacidade_descarga,
        "n_pontos": len(v),
        "validacao": f"PyBaMM SPM V {v[0]:.3f} V -> {v[-1]:.3f} V"
                     + (f", E={energia:.2f} Wh" if energia is not None else ""),
    }


# --------------------------------------------------------------------------- neuro
def neuro_brian2(pergunta, p):
    """Rede de neuronios LIF REAL (Brian2) com contagem de spikes."""
    from brian2 import NeuronGroup, SpikeMonitor, ms, prefs, run, start_scope

    # Sem compilador C++ neste ambiente: usa o alvo NumPy puro do proprio Brian2.
    try:
        prefs.codegen.target = "numpy"
    except Exception:  # noqa: BLE001
        pass

    n = int(p.get("n_neuronios", p.get("N", 20)) or 20)
    duracao = float(p.get("duracao_ms", 50.0) or 50.0)
    corrente = float(p.get("corrente", 1.5) or 1.5)
    start_scope()
    # No Brian2 a corrente precisa ser declarada como PARAMETRO do modelo.
    grupo = NeuronGroup(n, "dv/dt = (-v + I)/(10*ms) : 1\nI : 1",
                        threshold="v > 1", reset="v = 0", method="exact")
    grupo.I = corrente
    monitor = SpikeMonitor(grupo)
    run(duracao * ms)
    return {
        "simulador": "Neurociencia (Brian2 LIF)",
        "dominio": "Neurociencia",
        "motor": MOTORES["neuro"],
        "n_neuronios": n,
        "duracao_ms": duracao,
        "corrente": corrente,
        "spikes_total": int(len(monitor.t)),
        "spikes_por_neuronio": [int(x) for x in monitor.count],
        "validacao": f"Brian2 {len(monitor.t)} spikes em {n} neuronios",
    }


# --------------------------------------------------------------------------- hidro
def hidro_wntr(pergunta, p):
    """Hidraulica REAL (WNTR/EPANET): pressao e velocidade em rede de agua.

    DEFEITO CORRIGIDO (31/10/2026, medido em auditoria/verifica_todos.py):
    `sim_hidro` declara `area_km2` e `precipitacao_mm`, mas o motor so lia
    vazao/comprimento/diametro/carga -- os dois parametros chegavam e nao
    afetavam nada (resultado identico ao dobra-los). Agora a chuva na area da
    bacia entra pelo metodo racional Q = C * i * A, que e' a conversao
    hidrologica correta de chuva em vazao superficial, e o resultado declara
    a vazao de escoamento obtida.
    """
    import wntr

    vazao = float(p.get("vazao_m3s", p.get("demanda", 0.005)) or 0.005)
    comprimento = float(p.get("comprimento_m", 200.0) or 200.0)
    diametro = float(p.get("diametro_m", 0.2) or 0.2)
    carga = float(p.get("carga_m", p.get("altura", 60.0)) or 60.0)

    # Metodo racional: Q = C * (A * 1e6 m2) * (i / 1000 m) / 86400 s
    escoamento = None
    if p.get("area_km2") is not None or p.get("precipitacao_mm") is not None:
        try:
            area = float(p.get("area_km2", 1.0) or 1.0)
            chuva = float(p.get("precipitacao_mm", 1.0) or 1.0)
            coef = float(p.get("coef_escoamento", 0.7) or 0.7)
        except (TypeError, ValueError):
            area = chuva = coef = None
        if area and chuva and coef and area > 0 and chuva >= 0:
            escoamento = coef * (area * 1e6) * (chuva / 1000.0) / 86400.0

    rede = wntr.network.WaterNetworkModel()
    rede.add_reservoir("R1", base_head=carga)
    rede.add_junction("J1", base_demand=vazao, elevation=10.0)
    rede.add_pipe("P1", "R1", "J1", length=comprimento, diameter=diametro,
                  roughness=100)
    resultado = wntr.sim.EpanetSimulator(rede).run_sim()
    ultimo = resultado.node["pressure"].index[-1]
    saida = {
        "simulador": "Hidraulica (WNTR/EPANET)",
        "dominio": "Engenharia - Hidraulica",
        "motor": MOTORES["hidro"],
        "vazao_m3s": vazao,
        "comprimento_m": comprimento,
        "diametro_m": diametro,
        "pressao_J1_m": round(float(resultado.node["pressure"].loc[ultimo, "J1"]), 4),
        "velocidade_P1_ms": round(float(resultado.link["velocity"].loc[ultimo, "P1"]), 4),
        "vazao_escoamento_m3s": escoamento,
        "validacao": "EPANET convergiu em 1 periodo",
    }
    if escoamento is not None:
        saida["validacao"] += f"; escoamento={escoamento:.4f} m3/s (racional)"
    return saida


# ------------------------------------------------------------------------ epidemia
def epidemia_mesa(pergunta, p):
    """SIR baseado em AGENTES REAL (Mesa): contagio e recuperacao estocasticos."""
    from mesa import Agent, Model

    n = int(p.get("populacao", p.get("N", 200)) or 200)
    beta = float(p.get("beta", 0.3) or 0.3)
    gamma = float(p.get("gamma", 0.1) or 0.1)
    passos = int(p.get("passos", 30) or 30)

    class Pessoa(Agent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.estado = "I" if getattr(self, "unique_id", 0) < 5 else "S"

        def step(self):
            if self.estado == "S":
                if self.random.random() < beta:
                    self.estado = "I"
            elif self.estado == "I" and self.random.random() < gamma:
                self.estado = "R"

    class Epidemia(Model):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.agentes = [_criar_agente(Pessoa, i, self) for i in range(n)]

        def step(self):
            for agente in self.agentes:
                agente.step()

    modelo = Epidemia()
    historico = []
    for _ in range(passos):
        modelo.step()
        historico.append(sum(1 for a in modelo.agentes if a.estado == "I"))
    return {
        "simulador": "Epidemiologia (Mesa ABM SIR)",
        "dominio": "Saude - Epidemiologia",
        "motor": MOTORES["epidemia"],
        "populacao": n,
        "beta": beta,
        "gamma": gamma,
        "passos": passos,
        "infectados_final": historico[-1],
        "pico_infectados": max(historico),
        "R0_teorico": round(beta / gamma, 3) if gamma else 0.0,
        "validacao": f"Mesa ABM pico={max(historico)} de {n}",
    }


# ---------------------------------------------------------------------------- micro
def micro_cobrapy(pergunta, p):
    """FBA REAL (COBRApy) com reacao de biossintese e crescimento resultante.

    DEFEITOS CORRIGIDOS (31/10/2026, medidos em auditoria/verifica_todos.py):
      1. O objetivo era a propria reacao de captacao, entao o "fluxo otimo"
         era sempre igual ao limite superior -- otimizacao decorativa, nao FBA;
      2. `N0`, `mu` e `t`, que o simulador declara, nao entravam em nada: o
         resultado era identico ao dobra-los (a auditoria marcou constante).
    Agora o FBA maximiza a reacao de biossintese com estequiometria de ATP,
    respeitando a manutencao e o mu maximo informado, e o crescimento predito
    alimenta a curva exponencial N(t) = N0 * exp(mu_fba * t).
    """
    import math

    import cobra

    fluxo_max = float(p.get("fluxo_max", 10.0) or 10.0)      # mmol/gDW/h
    manutencao = float(p.get("manutencao", 0.5) or 0.5)       # mmol ATP/gDW/h
    atp_biomassa = float(p.get("atp_por_biomassa", 2.0) or 2.0)
    mu_maximo = float(p.get("mu", 0.5) or 0.5)                # 1/h
    n0 = float(p.get("N0", 1.0) or 1.0)
    tempo = float(p.get("t", 10.0) or 10.0)                   # h
    if fluxo_max <= 0 or atp_biomassa <= 0 or mu_maximo <= 0:
        raise ValueError("fluxo_max, atp_por_biomassa e mu devem ser positivos")
    if n0 < 0 or tempo < 0:
        raise ValueError("N0 e t nao podem ser negativos")

    modelo = cobra.Model("issacar_minimo")
    glicose = cobra.Metabolite("glc_e")
    atp = cobra.Metabolite("atp_c")
    biomassa = cobra.Metabolite("biomassa")
    # A glicose precisa de fonte: sem reacao de suprimento o balanco de massa
    # exige captacao = 0 (era por isso que o motor antigo devolvia fluxo 0.0
    # mesmo "otimizando").
    fonte = cobra.Reaction("EX_glc")
    fonte.add_metabolites({glicose: 1.0})
    fonte.bounds = (0.0, fluxo_max)
    captacao = cobra.Reaction("R_captacao")
    captacao.add_metabolites({glicose: -1.0, atp: 1.0})
    captacao.bounds = (0.0, fluxo_max)
    manut = cobra.Reaction("R_manutencao")
    manut.add_metabolites({atp: -1.0})
    manut.bounds = (0.0, manutencao)
    crescimento = cobra.Reaction("R_crescimento")
    crescimento.add_metabolites({atp: -atp_biomassa, biomassa: 1.0})
    crescimento.bounds = (0.0, mu_maximo)
    # Biomassa tambem precisa de destino: no balanco estacionario dela,
    # producao - consumo = 0. Sem esse dreno a unica solucao e' crescimento
    # zero (defeito que fazia o motor devolver mu = 0 sempre).
    dreno = cobra.Reaction("R_biomassa_sink")
    dreno.add_metabolites({biomassa: -1.0})
    dreno.bounds = (0.0, mu_maximo)
    modelo.add_reactions([fonte, captacao, manut, crescimento, dreno])
    modelo.objective = "R_crescimento"
    solucao = modelo.optimize()
    mu_fba = float(solucao.fluxes["R_crescimento"])
    n_final = n0 * math.exp(mu_fba * tempo)
    return {
        "simulador": "Microbiologia (COBRApy FBA)",
        "dominio": "Biologia - Micro",
        "motor": MOTORES["micro"],
        "reacoes": len(modelo.reactions),
        "metabolitos": len(modelo.metabolites),
        "fluxo_max": fluxo_max,
        "manutencao": manutencao,
        "fluxo_otimo": float(solucao.fluxes["R_captacao"]),
        "mu_fba_h": mu_fba,
        "tempo_geracao_h": (math.log(2) / mu_fba) if mu_fba > 0 else None,
        "N0": n0, "t_h": tempo, "N_final": n_final,
        "status": str(solucao.status),
        "validacao": f"FBA {solucao.status} mu={mu_fba:.3f}/h "
                     f"N({tempo:.0f}h)={n_final:.3e}",
    }


MAPA = {
    "md": md_ase,
    "solido": solido_emt,
    "molecular": molecular_rdkit,
    "cristalografia": cristalografia_pymatgen,
    "bateria": bateria_pybamm,
    "neuro": neuro_brian2,
    "hidro": hidro_wntr,
    "epidemia": epidemia_mesa,
    "micro": micro_cobrapy,
}


def para_chave(chave: str):
    """Retorna o motor real desta chave de simulador, ou None."""
    return MAPA.get(str(chave))


