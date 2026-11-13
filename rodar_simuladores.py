# -*- coding: utf-8 -*-
"""Roda os 25 simuladores mapeados (matriz 7Dx4) com os motores REAIS.

Por que este arquivo existe
===========================

`ambiental_backend/analises_experimentais.py` nesta copia e' um stub, e o modulo
original exige o bytecode CPython 3.10 preservado em `_recuperacao/`. Rodar com
o Python 3.13 do ambiente devolve `indisponivel` para os 9 simuladores de
`universal.py` (falta numpy) e `erro` para os 16 motores experimentais (stub).

Este script resolve as duas coisas sem tocar no projeto nem no banco:

1. monta um palco isolado em `_palco310/` (copia do pacote + o carregador
   original + o `.pyc` 3.10 + numpy cp310 baixado do PyPI);
2. reexecuta a si mesmo com um CPython 3.10, onde os 25 motores carregam;
3. escreve `resultado_simuladores.json` e imprime a tabela;
4. com `--gravar`, aplica as saidas numa COPIA do banco (`_qa_sim_dados/`) via
   `adsorventes.aplicar_descritores` e mostra a cobertura antes/depois.

Uso
===
    python rodar_simuladores.py                 # roda os 25 e mostra a tabela
    python rodar_simuladores.py --gravar        # + prova de gravacao na copia
    python rodar_simuladores.py --python310 P   # forca o interpretador 3.10
    python rodar_simuladores.py --limpar        # apaga o palco e sai

Nada aqui inventa numero: as entradas sao de ensaio tipico de carvao ativado e
estao declaradas em `PARAMETROS`. Trocar por dado medido e' editar o dicionario.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PACOTE = AQUI / "ambiental_backend"
PALCO = AQUI / "_palco310"
DENTRO_DO_PALCO = PALCO / "ambiental_backend"
SITE_NUMPY = PALCO / "numpy_site"
JSON_SAIDA = AQUI / "resultado_simuladores.json"
DADOS_COPIA = AQUI / "_qa_sim_dados"

PESQUISA = "pesq_63b32e62389dae7c"
MATERIAIS = {"A (KL-KOH-1:1)": "mat_ca84ac210575584a",
             "B (KL-KOH-2:1)": "mat_358eb4207c9fb795"}

# Entradas de ensaio tipico (NAO sao dado medido do KL-KOH; ver docstring).
PARAMETROS = {
    "superficie": {"area_m2g": 1262.0},
    "nano": {"diametro_nm": 45.0},
    "cristalografia": {"parametro_rede": 3.5, "n": 1, "angulo": 30.0},
    "dft": {"material": "carbono"},
    "cfd": {"densidade": 997.0, "velocidade": 0.01, "diametro": 0.005,
            "viscosidade": 0.001},
    "fluido": {"densidade": 997.0, "velocidade": 0.01, "diametro": 0.005},
    "poluicao": {"C0": 20.0, "k": 0.05, "t": 120.0},
    "equilibrio": {"dG0": -5000.0, "T": 298.15},
    "hidro": {"area_km2": 100.0, "precipitacao_mm": 1200.0},
    "angulo_contato": {"angulo_agua_deg": 95.0,
                       "angulo_diiodometano_deg": 60.0},
    "boehm_grupos": {"naoh_mmol_g": 0.80, "na2co3_mmol_g": 0.50,
                     "nahco3_mmol_g": 0.30, "hcl_mmol_g": 0.20},
    "composicao_elementar": {"elementos_pct": {"C": 80.0, "H": 2.5, "N": 0.5,
                                              "S": 0.3},
                             "elementos_principais": ["C", "H", "N", "S"]},
    "conformidade_limites": {"analitos": {"sulfametoxazol": 0.0072},
                             "limites": {"sulfametoxazol": 0.05}},
    "fractal_agregacao": {"diametros_um": [1.0, 2.0, 5.0, 10.0, 20.0]},
    "ftir_grupos": {"bandas_cm1": [3430.0, 1600.0, 1100.0]},
    "granulometria_psd": {"diametros_um": [1.0, 2.0, 5.0, 10.0, 20.0, 50.0]},
    "lixiviacao_cinetica": {"tempo_s": [3600, 7200, 14400, 28800, 86400],
                            "fracao_lixiviada": [0.05, 0.09, 0.15, 0.21, 0.30]},
    "perigo_composicao": {"composicao": [
        {"substancia": "carbono", "fracao": 0.80},
        {"substancia": "zinco", "fracao": 0.02}]},
    "pzc_deriva_ph": {"ph_inicial": [2, 4, 6, 8, 10, 12],
                      "ph_final": [3.1, 4.2, 5.3, 7.4, 9.9, 11.8]},
    "pzc_titulacao_massa": {"massa_g_L": [1, 2, 4, 6, 8, 10],
                            "ph_equilibrio": [4.6, 5.0, 5.6, 6.2, 6.9, 7.8]},
    "reciclabilidade": {"composicao": [
        {"classe": "carbono ativado", "fracao": 0.80},
        {"classe": "lignina", "fracao": 0.05}]},
    "regeneracao_reuso": {"capacidades_mg_g": [100, 95, 91, 87, 84, 80],
                          "desorcao_pct": 92.0},
    "seletividade_competitiva": {"componentes": [
        {"nome": "sulfametoxazol", "qmax_mg_g": 100.47, "K_L_L_mg": 0.1497},
        {"nome": "ibuprofeno", "qmax_mg_g": 120.0, "K_L_L_mg": 0.045}],
        "concentracoes_mg_L": [20.0, 20.0]},
    "solubilidade_imersao": {"massa_inicial_g": 1.0, "massa_final_g": 0.97},
    "tga_tangente": {"temperatura_C": [30, 100, 200, 400, 600, 700, 800],
                     "massa_pct": [96.0, 92.0, 88.0, 80.0, 62.0, 45.0, 30.0]},
}



# --------------------------------------------------------------- palco 3.10
def _core_cientifico() -> Path:
    """Diretorio com `universal.py` e o carregador original."""
    candidatos = [os.environ.get("ALEF_TAV_CORE"), str(AQUI.parent), str(AQUI),
                  str(Path.home() / "hf_upload")]
    candidatos += sorted(glob.glob(str(Path.home() / "hf_upload*")))
    for caminho in candidatos:
        if not caminho:
            continue
        pasta = Path(caminho)
        if (pasta / "universal.py").is_file():
            return pasta
    raise SystemExit("nao achei o nucleo cientifico (universal.py). Defina "
                     "ALEF_TAV_CORE com o diretorio que o contem.")


def _carregador_original(core: Path) -> Path:
    """O `.py` que carrega o bytecode 3.10 preservado."""
    alvos = [core / "ambiental_backend" / "analises_experimentais.py",
             PACOTE / "analises_experimentais.pycshim",
             AQUI / "analises_experimentais.py"]
    for caminho in alvos:
        if caminho.is_file() and "_carregar_codigo" in caminho.read_text(
                encoding="utf-8", errors="replace"):
            return caminho
    raise SystemExit("nao achei o carregador original de "
                     "analises_experimentais (o .py que le o .pyc 3.10)")


def _bytecode_310(core: Path) -> Path:
    alvos = [core / "ambiental_backend" / "_recuperacao"
             / "analises_experimentais.cpython-310.pyc"]
    alvos += [Path(p) for p in glob.glob(str(
        AQUI / "**" / "_recuperacao" / "analises_experimentais.cpython-310.pyc"),
        recursive=True)]
    for caminho in alvos:
        if caminho.is_file() and caminho.read_bytes()[:4] == b"\x6f\x0d\x0d\x0a":
            return caminho
    raise SystemExit("bytecode CPython 3.10 de analises_experimentais nao "
                     "encontrado (cabecalho 6f 0d 0d 0a)")


def _python_310(explicito: str = None) -> str:
    candidatos = [explicito, os.environ.get("ALEF_PYTHON310")]
    bases = [Path.home() / "miniconda3" / "pkgs",
             Path.home() / "miniconda_alef" / "pkgs",
             Path.home() / "AppData" / "Local" / "Programs" / "Python",
             Path("C:/")]
    for base in bases:
        if not base.is_dir():
            continue
        for padrao in ("python-3.10*", "Python310*"):
            candidatos += [str(p) for p in sorted(base.glob(padrao),
                                                  reverse=True)]
    for caminho in candidatos:
        if not caminho:
            continue
        pasta = Path(caminho)
        exe = pasta if pasta.suffix.lower() == ".exe" else pasta / "python.exe"
        if not exe.is_file():
            continue
        versao = subprocess.run(
            [str(exe), "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
            capture_output=True, text=True)
        if versao.stdout.strip() == "3.10":
            return str(exe)
    raise SystemExit("nao achei um CPython 3.10. Instale-o ou passe "
                     "--python310 CAMINHO (o bytecode original exige 3.10).")


def _numpy_310() -> None:
    if (SITE_NUMPY / "numpy").is_dir():
        return
    SITE_NUMPY.mkdir(parents=True, exist_ok=True)
    rodada = subprocess.run(
        [sys.executable, "-m", "pip", "download", "numpy==2.2.6",
         "--only-binary=:all:", "--no-deps", "--python-version", "310",
         "--implementation", "cp", "--abi", "cp310", "--platform", "win_amd64",
         "-d", str(PALCO / "_wheels"), "--disable-pip-version-check"],
        capture_output=True, text=True)
    if rodada.returncode != 0:
        raise SystemExit("pip download numpy cp310 falhou:\n%s%s"
                         % (rodada.stdout, rodada.stderr))
    for roda in (PALCO / "_wheels").glob("numpy*cp310*.whl"):
        with zipfile.ZipFile(roda) as pacote:
            pacote.extractall(SITE_NUMPY)


def preparar_palco(explicito: str = None) -> str:
    """Monta o palco e devolve o caminho do interpretador 3.10."""
    core = _core_cientifico()
    carregador = _carregador_original(core)
    bytecode = _bytecode_310(core)
    if DENTRO_DO_PALCO.exists():
        shutil.rmtree(DENTRO_DO_PALCO)
    shutil.copytree(PACOTE, DENTRO_DO_PALCO,
                    ignore=shutil.ignore_patterns("__pycache__", "_recuperacao"))
    (DENTRO_DO_PALCO / "_recuperacao").mkdir()
    shutil.copy2(bytecode, DENTRO_DO_PALCO / "_recuperacao" / bytecode.name)
    shutil.copy2(carregador, DENTRO_DO_PALCO / "analises_experimentais.py")
    _numpy_310()
    return _python_310(explicito)


# ------------------------------------------------------------- dentro do 3.10
def executar_simuladores() -> None:
    sys.path.insert(0, str(PALCO))
    from ambiental_backend import descritores_simuladores as ds

    saidas = []
    for nome in sorted(ds.SIMULADORES):
        parametros = dict(PARAMETROS.get(nome) or {})
        try:
            saida = ds.executar(nome, parametros, "SMX em carvao KL-KOH", True)
        except Exception as erro:                                # noqa: BLE001
            saida = {"simulador": nome, "estado": "excecao_local",
                     "erro": "%s: %s" % (type(erro).__name__, erro),
                     "descritores": []}
        saida["parametros_usados"] = parametros
        saidas.append(saida)
    with open(JSON_SAIDA, "w", encoding="utf-8") as arquivo:
        json.dump(saidas, arquivo, ensure_ascii=False, indent=1, default=str)


def rodar_no_palco(python310: str) -> None:
    ambiente = dict(os.environ)
    ambiente.update({
        "ALEF_PALCO310": "1",
        "ALEF_TAV_CORE": str(_core_cientifico()),
        "ALEF_SEM_PREAQUECER": "1",
        "PYTHONPATH": str(SITE_NUMPY),
        "PYTHONIOENCODING": "utf-8",
    })
    rodada = subprocess.run([python310, str(Path(__file__).resolve())],
                            env=ambiente, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if rodada.returncode != 0:
        raise SystemExit("execucao no palco falhou:\n%s%s"
                         % (rodada.stdout, rodada.stderr))


# --------------------------------------------------------------- fora: tabela
def tabela(saidas: list) -> None:
    print("| simulador | estado | descritores gravados (modo valor) | apoio |")
    print("|---|---|---|---|")
    for item in saidas:
        valores = []
        for descritor in item.get("descritores") or []:
            if descritor.get("modo") != "valor" or descritor.get("valor") is None:
                continue
            valor = descritor["valor"]
            texto = ("%.6g" % valor) if isinstance(valor, (int, float)) else valor
            valores.append("%s=%s %s" % (descritor["codigo"], texto,
                                         descritor.get("unidade") or ""))
        apoios = sum(1 for d in item.get("descritores") or []
                     if d.get("modo") == "apoio")
        print("| `%s` | %s | %s | %s |" % (item["simulador"],
                                           item.get("estado"),
                                           "; ".join(valores) or "—",
                                           apoios or "—"))


def gravar_copia(saidas: list) -> None:
    """Aplica as saidas numa copia do banco e mostra a cobertura."""
    origem = AQUI / "dados_ambiental" / "ambiental.db"
    if not origem.is_file():
        raise SystemExit("banco de origem ausente: %s" % origem)
    shutil.rmtree(DADOS_COPIA, ignore_errors=True)
    DADOS_COPIA.mkdir()
    copia = DADOS_COPIA / "ambiental.db"
    shutil.copy2(origem, copia)
    url = "sqlite:///" + copia.as_posix()
    os.environ["AMBIENTAL_DADOS"] = str(DADOS_COPIA)
    for variavel in ("AMBIENTAL_BANCO_URL", "ALEF_TAV_DATABASE_URL",
                     "DATABASE_URL"):
        os.environ[variavel] = url
    from ambiental_backend import adsorventes, persistencia

    persistencia.garantir_esquema()
    print("banco de prova:", persistencia.URL_BANCO)
    for rotulo, material_id in MATERIAIS.items():
        antes = adsorventes.obter_validacao(PESQUISA, material_id)
        sessao = persistencia.sessao()
        try:
            for item in saidas:
                if item.get("descritores"):
                    adsorventes.aplicar_descritores(sessao, PESQUISA,
                                                    material_id,
                                                    item["descritores"])
            sessao.commit()
        finally:
            sessao.close()
        depois = adsorventes.obter_validacao(PESQUISA, material_id)
        cobertura = (antes["preenchimento"], depois["preenchimento"])
        print("%s: cobertura %s/%s -> %s/%s (%s%% -> %s%%)" % (
            rotulo, cobertura[0]["com_dado"], cobertura[0]["total_avaliado"],
            cobertura[1]["com_dado"], cobertura[1]["total_avaliado"],
            cobertura[0]["percentual_com_dado"],
            cobertura[1]["percentual_com_dado"]))
        gravados = {d["codigo"]: d["valor"] for d in depois["descritores"]
                    if d["valor"] is not None}
        print("   valores:", ", ".join("%s=%s" % par for par in
                                       sorted(gravados.items())))


def principal() -> int:
    analisador = argparse.ArgumentParser(
        description="Executa os 25 simuladores da matriz 7Dx4 nos motores reais")
    analisador.add_argument("--gravar", action="store_true",
                            help="aplicar as saidas numa copia do banco")
    analisador.add_argument("--python310", default=None,
                            help="caminho do python.exe 3.10")
    analisador.add_argument("--limpar", action="store_true",
                            help="apagar palco e copia do banco")
    argumentos = analisador.parse_args()

    if argumentos.limpar:
        shutil.rmtree(PALCO, ignore_errors=True)
        shutil.rmtree(DADOS_COPIA, ignore_errors=True)
        print("palco e copia do banco removidos")
        return 0

    if os.environ.get("ALEF_PALCO310") == "1":
        executar_simuladores()
        return 0

    python310 = preparar_palco(argumentos.python310)
    print("palco:", PALCO)
    print("interpretador:", python310)
    rodar_no_palco(python310)
    with open(JSON_SAIDA, encoding="utf-8") as arquivo:
        saidas = json.load(arquivo)
    print()
    tabela(saidas)
    ok = sum(1 for s in saidas if str(s.get("estado", "")).startswith("ok"))
    print()
    print("executaram: %d/%d   (json: %s)" % (ok, len(saidas), JSON_SAIDA.name))
    if argumentos.gravar:
        print()
        gravar_copia(saidas)
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
