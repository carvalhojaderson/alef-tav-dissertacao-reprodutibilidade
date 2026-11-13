# -*- coding: utf-8 -*-
"""ALEF-TAV | REGISTRO CENTRAL DOS 195 COMPONENTES EXTERNOS.

O QUE ESTE MODULO E
-------------------
Fonte unica de verdade para responder, por componente:

    * qual e o identificador estavel;
    * qual e a natureza declarada no catalogo (e portanto onde ele pode rodar);
    * qual grupo de execucao o serve (processo local, imagem Docker
      reutilizavel, subprocesso ou adaptador remoto);
    * qual modulo/binario/endpoint prova a presenca;
    * qual o motivo declarado quando esta bloqueado.

O QUE ELE **NAO** FAZ
---------------------
Nao importa motor nenhum, nao chama rede, nao sobe conteiner e nao escreve
arquivo. A decisao "podemos executar agora?" recebe os fatos do ambiente por
parametro (`FatosAmbiente`), o que mantem o modulo puro e testavel. Quem
executa e `executor_isolado.py`.

REGRA DE HONESTIDADE
--------------------
`estado` no catalogo foi medido em OUTRO ambiente (Linux, env "holocine").
Aqui ele e apenas historico. O estado que vale e o de `resolver()`, que olha
ESTE host. Componente nunca e operacional por estar catalogado.
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).parent
CATALOGO = RAIZ / "componentes_195_estado.json"
METADADOS = RAIZ / "catalogo_simuladores_novas_integracoes.json"


def _grupo(backend: str, descricao: str, base: str | None = None,
           pip: tuple[str, ...] = (), apt: tuple[str, ...] = (), peso: int = 0,
           memoria_mb: int = 0, cpus: float = 0.0, timeout_s: int = 0,
           **extra: Any) -> dict[str, Any]:
    return {"backend": backend, "descricao": descricao, "base": base,
            "pip": list(pip), "apt": list(apt), "peso": peso,
            "memoria_mb": memoria_mb, "cpus": cpus, "timeout_s": timeout_s,
            **extra}


# ---------------------------------------------------------------------------
# GRUPOS DE EXECUCAO (uma imagem atende VARIOS componentes)
# ---------------------------------------------------------------------------
# Nao existe uma imagem por componente: componentes que compartilham pilha
# compativel dividem o grupo. A separacao e por incompatibilidade real
# (Qt/torch, libs nativas, R, GUI) e nao por conveniencia.
GRUPOS: dict[str, dict[str, Any]] = {
    "nucleo": _grupo("local", "processo do app (numpy/scipy + ase/rdkit/pymatgen)",
                     memoria_mb=256, cpus=1.0, timeout_s=120),
    "sci-leve": _grupo(
        "docker", "ciencia Python leve (sem Qt, sem torch)",
        base="python:3.12-slim-bookworm",
        pip=("numpy", "scipy", "pandas", "networkx", "matplotlib", "wntr", "mesa",
             "pysb", "flopy", "prody", "MDAnalysis", "pybamm", "cantera", "biosteam"),
        peso=1, memoria_mb=2048, cpus=1.0, timeout_s=300),
    "sci-pesado": _grupo(
        "docker", "stacks grandes (torch/Qt/compiladores) - construir por ultimo",
        base="python:3.12-slim-bookworm",
        pip=("numpy", "scipy", "chgnet", "matgl", "atomate2", "ase", "pymatgen"),
        peso=3, memoria_mb=6144, cpus=2.0, timeout_s=900),
    "cli-bio": _grupo(
        "docker", "binarios de bioinformatica",
        base="debian:bookworm-slim",
        apt=("samtools", "ncbi-blast+", "hmmer", "mafft", "bedtools", "minimap2",
             "fastqc", "iqtree", "bcftools", "kallisto", "salmon"),
        peso=2, memoria_mb=2048, cpus=2.0, timeout_s=600),
    "cli-geo": _grupo(
        "docker", "geoespacial", base="debian:bookworm-slim",
        apt=("gdal-bin", "grass-core", "proj-bin", "geos-bin"),
        peso=2, memoria_mb=2048, cpus=2.0, timeout_s=600),
    "cli-hidro": _grupo(
        "docker", "hidraulica/hidrologia com executavel",
        base="debian:bookworm-slim", pip=("numpy",),
        apt=("epanet2", "swmm", "ca-certificates"),
        peso=2, memoria_mb=1024, cpus=1.0, timeout_s=300),
    "cli-quim": _grupo(
        "docker", "quimica/estrutura com binario", base="debian:bookworm-slim",
        apt=("openbabel", "autodock-vina"),
        peso=2, memoria_mb=1024, cpus=1.0, timeout_s=300),
    "r-stats": _grupo(
        "docker", "pacotes R / Bioconductor", base="rocker/r-ver:4.4",
        peso=2, memoria_mb=3072, cpus=1.0, timeout_s=900,
        r=("BiocManager", "DESeq2", "edgeR", "Seurat", "dada2")),
    "servico": _grupo(
        "docker", "servicos com estado/porta propria",
        base="debian:bookworm-slim", apt=("ca-certificates", "curl"),
        peso=3, memoria_mb=3072, cpus=1.0, timeout_s=900),
    "build": _grupo(
        "docker", "exigem compilacao (fenicsx, arbor, openfold, dft...)",
        base="python:3.12-slim-bookworm",
        apt=("build-essential", "cmake", "gfortran", "git"),
        peso=4, memoria_mb=4096, cpus=2.0, timeout_s=1800),
    "worker-gui": _grupo(
        "docker", "GUI/desktop executada headless (xvfb)",
        base="debian:bookworm-slim", apt=("xvfb",),
        peso=4, memoria_mb=4096, cpus=2.0, timeout_s=900),
    "remoto": _grupo("remoto", "API REST publica ou satelite HTTP do dominio",
                     timeout_s=30),
    "revisao": _grupo("bloqueado",
                      "exige decisao humana (licenca, dado privado, julgamento)",
                      peso=9),
}

# Grupo padrao por natureza catalogada (ESPECIFICACOES pode sobrescrever).
GRUPO_POR_NATUREZA: dict[str, str] = {
    "external_api": "remoto",
    "api_or_data": "remoto",
    "service_or_api": "remoto",
    "service_or_cloud": "remoto",
    "container_or_cloud": "remoto",
    "python_package": "nucleo",
    "biblioteca_python": "nucleo",
    "container_cli": "build",
    "r_package": "r-stats",
    "container_or_service": "servico",
    "container_build": "build",
    "container_or_worker": "worker-gui",
    "service_or_worker": "worker-gui",
    "desktop_or_headless": "worker-gui",
    "vendor_tool": "build",
    "review_required": "revisao",
}

# ---------------------------------------------------------------------------
# FAMILIAS DE CLI
# ---------------------------------------------------------------------------
# O nome da familia e o nome do grupo Docker. Componentes de linha de comando
# que nao aparecem em nenhuma familia usam o grupo padrao da natureza ("build").
FAMILIA_CLI: dict[str, tuple[str, ...]] = {
    "cli-bio": ("samtools", "bcftools", "bedtools", "blast", "hmmer", "mafft",
                "iq-tree", "fastqc", "fastp", "salmon", "kallisto", "star",
                "minimap2", "mmseqs2", "metaphlan", "humann", "bracken",
                "kraken-2", "megahit", "metaspades", "checkm2", "gtdb-tk",
                "picrust2", "foldseek", "bwa-mem2", "openms", "bionetgen",
                "qiime-2", "multiqc", "nextflow", "nf-core", "colabfold"),
    "cli-geo": ("gdal", "grass-gis", "orfeo-toolbox", "whiteboxtools",
                "esa-snap", "qgis"),
    "cli-hidro": ("epanet", "epa-swmm", "modflow-6", "swat", "aquatox", "wasp",
                  "hysplit", "sutra", "telemac-mascaret", "delft3d", "parflow",
                  "adcirc", "raven-hydrological-modelling-framework"),
    "cli-quim": ("open-babel", "autodock-vina", "smina", "gnina", "xtb",
                 "phreeqc", "zeo"),
    "build": ("quantum-espresso", "cp2k", "abinit", "lammps", "gromacs",
              "openfoam", "neuron", "physicell", "openfast", "swan", "schism",
              "roms", "wrf", "wrf-chem", "cmaq", "aermod", "elmer-fem",
              "farsite", "flammap", "rangeshifter", "wec-sim"),
}

# Executavel quando o nome difere do id do catalogo.
BINARIO_OVERRIDE: dict[str, str] = {
    "blast": "blastn", "hmmer": "hmmsearch", "iq-tree": "iqtree2",
    "kraken-2": "kraken2", "metaspades": "metaspades.py",
    "gtdb-tk": "gtdbtk", "picrust2": "picrust2_pipeline.py",
    "bionetgen": "BNG2.pl", "gdal": "gdalinfo", "grass-gis": "grass",
    "orfeo-toolbox": "otbcli", "whiteboxtools": "whitebox_tools",
    "esa-snap": "gpt", "epanet": "epanet2", "epa-swmm": "swmm5",
    "modflow-6": "mf6", "open-babel": "obabel", "autodock-vina": "vina",
    "openms": "OpenMSInfo", "quantum-espresso": "pw.x", "cp2k": "cp2k.popt",
    "lammps": "lmp", "gromacs": "gmx", "openfoam": "foamRun",
    "neuron": "nrniv", "physicell": "PhysiCell", "qiime-2": "qiime",
    "swan": "swan.exe", "schism": "pschism", "telemac-mascaret": "telemac2d.py",
    "delft3d": "d_hydro", "roms": "oceanM", "wrf": "wrf.exe",
    "wrf-chem": "wrf.exe", "cmaq": "CCTM", "elmer-fem": "ElmerSolver",
    "dssat": "dscsm048", "zeo": "zeo++", "cell-ranger": "cellranger",
    "colabfold": "colabfold_batch", "raven-hydrological-modelling-framework":
        "raven", "hysplit": "hycs_std", "modflow-6": "mf6",
}

# ---------------------------------------------------------------------------
# ESPECIFICACOES PYTHON (id -> modulo importavel, pacote pip, grupo)
# ---------------------------------------------------------------------------
# Somente pacotes cujo nome tecnico e o que o projeto publica. `mod` e o nome
# de import (que nem sempre coincide com o nome do pacote pip).
PYTHON: dict[str, tuple[str, str, str]] = {
    # leves: podem rodar no processo ou no grupo leve
    "ase": ("ase", "ase", "nucleo"),
    "pymatgen": ("pymatgen", "pymatgen", "nucleo"),
    "rdkit": ("rdkit", "rdkit", "nucleo"),
    "wntr": ("wntr", "wntr", "sci-leve"),
    "mesa": ("mesa", "mesa", "sci-leve"),
    "pysb": ("pysb", "pysb", "sci-leve"),
    "cobrapy": ("cobra", "cobra", "sci-leve"),
    "flopy": ("flopy", "flopy", "sci-leve"),
    "prody": ("prody", "prody", "sci-leve"),
    "mdanalysis": ("MDAnalysis", "MDAnalysis", "sci-leve"),
    "pybamm": ("pybamm", "pybamm", "sci-leve"),
    "cantera": ("cantera", "cantera", "sci-leve"),
    "biosteam": ("biosteam", "biosteam", "sci-leve"),
    "capytaine": ("capytaine", "capytaine", "sci-leve"),
    "tellurium": ("tellurium", "tellurium", "sci-leve"),
    "libroadrunner": ("roadrunner", "libroadrunner", "sci-leve"),
    "brian2": ("brian2", "brian2", "sci-leve"),
    "covasim": ("covasim", "covasim", "sci-leve"),
    "opendrift": ("opendrift", "opendrift", "sci-leve"),
    "rasterio": ("rasterio", "rasterio", "sci-leve"),
    "xarray-rioxarray": ("rioxarray", "rioxarray", "sci-leve"),
    "matminer": ("matminer", "matminer", "sci-leve"),
    "multiqc": ("multiqc", "multiqc", "sci-leve"),
    "snakemake": ("snakemake", "snakemake", "sci-leve"),
    "brightway": ("bw2calc", "brightway25", "sci-leve"),
    "bsm2-python": ("bsm2", "bsm2-python", "sci-leve"),
    "ome-zarr": ("ome_zarr", "ome-zarr", "sci-leve"),
    "qsdsan": ("qsdsan", "qsdsan", "sci-leve"),
    # pesados / GUI / compilacao
    "openmm": ("openmm", "openmm", "sci-pesado"),
    "pdbfixer": ("pdbfixer", "pdbfixer", "sci-pesado"),
    "chgnet": ("chgnet", "chgnet", "sci-pesado"),
    "atomate2": ("atomate2", "atomate2", "sci-pesado"),
    "aiida-workflows": ("aiida", "aiida-core", "sci-pesado"),
    "betse": ("betse", "betse", "sci-pesado"),
    "hydromt": ("hydromt", "hydromt", "sci-pesado"),
    "idaes": ("idaes", "idaes-pse", "sci-pesado"),
    "watertap": ("watertap", "watertap", "sci-pesado"),
    "scanpy": ("scanpy", "scanpy", "sci-pesado"),
    "scvi-tools": ("scvi", "scvi-tools", "sci-pesado"),
    "matgl-m3gnet": ("matgl", "matgl", "sci-pesado"),
    "activity-browser": ("activity_browser", "activity-browser", "worker-gui"),
    "napari": ("napari", "napari", "worker-gui"),
    "e-cell4": ("ecell4", "ecell4", "build"),
    "gpaw": ("gpaw", "gpaw", "build"),
    "psi4": ("psi4", "psi4", "build"),
    "netpyne": ("netpyne", "netpyne", "build"),
    "opentiva": ("opentiva", "opentiva", "build"),
    "sire": ("sire", "sire", "build"),
}

# Dominio cientifico (usado para escolher satelite quando o backend e remoto).
DOMINIO: dict[str, str] = {
    "wntr": "hidro", "flopy": "hidro", "epa-swmm": "hidro", "epanet": "hidro",
    "modflow-6": "hidro", "mesa": "epidemia", "covasim": "epidemia",
    "epimodel": "epidemia", "pysb": "sistemas", "libroadrunner": "sistemas",
    "tellurium": "sistemas", "bionetgen": "sistemas", "copasi": "sistemas",
    "pybamm": "eletroquimica", "battmo": "eletroquimica",
    "cantera": "eletroquimica", "rdkit": "quimica", "open-babel": "quimica",
    "cobrapy": "micro", "brian2": "neuro", "neuron": "neuro",
    "nest": "neuro", "netpyne": "neuro", "arbor": "neuro",
    "ase": "materiais", "pymatgen": "materiais", "chgnet": "materiais",
    "matminer": "materiais", "atomate2": "materiais", "gdal": "geo",
    "grass-gis": "geo", "rasterio": "geo", "qgis": "geo",
}

# ---------------------------------------------------------------------------
# APIs REST publicas (sonda de integracao)
# ---------------------------------------------------------------------------
# Somente endpoints publicos, sem credencial e de resposta pequena. Nada aqui
# consome credito pago. Componente que exige chave/OAuth NAO tem sonda: fica
# bloqueado por credencial ate alguem autorizar o uso.
SONDAS_HTTP: dict[str, str] = {
    "rcsb-protein-data-bank-apis": "https://data.rcsb.org/rest/v1/core/entry/1CRN",
    "uniprot-rest-api": "https://rest.uniprot.org/uniprotkb/P69905.json",
    "pubchem-pug-rest": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
                        "cid/2244/property/MolecularWeight/JSON",
    "chembl-api": "https://www.ebi.ac.uk/chembl/api/data/molecule/CHEMBL25.json",
    "europe-pmc-rest-api": "https://www.ebi.ac.uk/europepmc/webservices/rest/"
                           "search?query=asthma&format=json&pageSize=1",
    "ncbi-pubmed-e-utilities": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
                               "esummary.fcgi?db=pubmed&id=1&retmode=json",
    "ncbi-datasets-api-cli": "https://api.ncbi.nlm.nih.gov/datasets/v2/genome/"
                             "taxon/9606/dataset_summary",
    "kegg-rest-api": "https://rest.kegg.jp/info/kegg",
    "reactome-content-analysis-api":
        "https://reactome.org/ContentService/data/database/version",
    "gbif-api": "https://api.gbif.org/v1/species/5231190",
    "obis-api": "https://api.obis.org/v3/taxon/48915",
    "biomodels-database": "https://www.ebi.ac.uk/biomodels/search"
                          "?query=BIOMD0000000012&format=json",
    "alphafold-protein-structure-database":
        "https://alphafold.ebi.ac.uk/api/prediction/P69905",
    "bio-tools-registry": "https://bio.tools/api/t/?format=json&q=blast&page_size=1",
    "nomad": "https://nomad-lab.eu/prod/v1/api/v1/info",
    "usgs-water-data-apis": "https://waterservices.usgs.gov/nwis/iv/?format=json"
                            "&sites=01646500&parameterCd=00060&period=P1D",
}

# Bloqueio por credencial: documentado, nunca contado como aprovado.
CREDENCIAL_NECESSARIA: dict[str, str] = {
    "materials-project-api": "MP_API_KEY",
    "materials-cloud": "MATERIALS_CLOUD_API_KEY",
    "copernicus-data-space-apis": "OAuth client (CDSE)",
    "jarvis": "JARVIS_NIST_KEY",
    "epa-comptox-chemicals-dashboard": "EPA_COMPTOX_KEY",
    "omero": "OMERO_USER/PASSWORD",
    "vcell": "VCell credentials",
    "crop2ml-crop-model-repository": "repositorio remoto indisponivel",
    "useeio": "USEEIO_API_KEY",
}

# Estados de resolucao (o que o host PODE fazer agora).
LOCAL = "EXECUTAVEL_LOCAL"
SUBPROCESSO = "EXECUTAVEL_SUBPROCESSO"
DOCKER_PRONTO = "EXECUTAVEL_DOCKER"
DOCKER_CONSTRUIR = "PRECISA_CONSTRUIR_IMAGEM"
REMOTO = "EXECUTAVEL_REMOTO"
INSTALAVEL = "INSTALAVEL_PIP"
SEM_DOCKER = "BLOQUEADO_DOCKER_AUSENTE"
SEM_CREDENCIAL = "BLOQUEADO_CREDENCIAL"
SEM_ESPEC = "BLOQUEADO_SEM_ESPECIFICACAO"
HUMANO = "BLOQUEADO_DECISAO_HUMANA"


@dataclass(frozen=True)
class Componente:
    """Metadados de um componente do catalogo (sem estado de execucao)."""

    id: str
    natureza: str
    estado_catalogo: str
    grupo: str
    prova: str = ""
    motivo: str = ""
    onde: str = ""
    modulo: str | None = None
    binario: str | None = None
    pacote_pip: str | None = None
    sonda: str | None = None
    dominio: str | None = None

    def como_dict(self) -> dict[str, Any]:
        return {"id": self.id, "natureza": self.natureza,
                "estado_catalogo": self.estado_catalogo, "grupo": self.grupo,
                "prova": self.prova, "motivo": self.motivo, "onde": self.onde,
                "modulo": self.modulo, "binario": self.binario,
                "pacote_pip": self.pacote_pip, "sonda": self.sonda,
                "dominio": self.dominio}


@dataclass
class FatosAmbiente:
    """Fatos medidos no host. Injetavel para manter o registro testavel."""

    python: str = ""
    sistema: str = ""
    docker: bool = False
    importaveis: dict[str, bool] = field(default_factory=dict)
    binarios: dict[str, bool] = field(default_factory=dict)
    imagens: set[str] = field(default_factory=set)
    satelites: dict[str, str] = field(default_factory=dict)

    @classmethod
    def medir(cls, com_import: bool = True) -> "FatosAmbiente":
        """Mede o host. `com_import=False` nao importa nada, so verifica spec."""
        import importlib.util
        import platform
        import sys

        fatos = cls(python=platform.python_version(), sistema=platform.system(),
                    docker=shutil.which("docker") is not None)
        if com_import:
            for modulo in sorted({m for m, _, _ in PYTHON.values()}):
                try:
                    fatos.importaveis[modulo] = importlib.util.find_spec(modulo) is not None
                except (ImportError, ValueError, ModuleNotFoundError):
                    fatos.importaveis[modulo] = False
        try:  # nome de cada binario, medido uma vez
            for cid in _ids_com_binario():
                nome = BINARIO_OVERRIDE.get(cid, cid)
                fatos.binarios[cid] = shutil.which(nome) is not None
        except Exception:  # noqa: BLE001 - medicao nunca deve derrubar o boot
            pass
        return fatos

    def tem_imagem(self, grupo: str) -> bool:
        """True se existir imagem cujo repositorio termine no nome do grupo.

        As imagens sao nomeadas `alef-tav/<grupo>:<hash>`; comparar apenas o
        nome do grupo (sem o hash) e' o que permite reconhecer uma imagem ja
        construida depois de um restart do processo.
        """
        for imagem in self.imagens:
            repositorio = str(imagem).rsplit(":", 1)[0]
            if repositorio.split("/")[-1] == grupo:
                return True
        return False



@dataclass(frozen=True)
class Resolucao:
    """Como este host pretende executar um componente, e por que."""

    id: str
    estado: str
    backend: str
    grupo: str
    motivo: str
    limites: dict[str, Any] = field(default_factory=dict)

    @property
    def executavel(self) -> bool:
        # DOCKER_CONSTRUIR tambem e executavel: o executor constroi a imagem
        # sob demanda antes de rodar. "imagem construida" continua sendo um
        # estado MEDIDO a parte (nunca inferido de "executavel").
        return self.estado in (LOCAL, SUBPROCESSO, DOCKER_PRONTO,
                               DOCKER_CONSTRUIR, REMOTO)

    def como_dict(self) -> dict[str, Any]:
        return {"id": self.id, "estado": self.estado, "backend": self.backend,
                "grupo": self.grupo, "motivo": self.motivo,
                "executavel": self.executavel, "limites": self.limites}

# ---------------------------------------------------------------------------
# CARGA DO CATALOGO
# ---------------------------------------------------------------------------
_CACHE: dict[str, Componente] | None = None


def _ids_com_binario() -> tuple[str, ...]:
    """Ids cuja execucao depende de binario no PATH."""
    vistos: list[str] = []
    for familia in FAMILIA_CLI.values():
        vistos.extend(familia)
    return tuple(dict.fromkeys(vistos))


def _grupo_do_componente(cid: str, natureza: str, modulo: str | None,
                         binario: str | None) -> str:
    """Resolve o grupo: especificacao explicita > familia de CLI > natureza."""
    for familia, membros in FAMILIA_CLI.items():
        if cid in membros:
            return familia
    if modulo:
        return PYTHON.get(cid, ("", "", "nucleo"))[2]
    if binario:
        return "build"
    return GRUPO_POR_NATUREZA.get(natureza, "revisao")


def carregar(caminho: Path | str | None = None) -> dict[str, Componente]:
    """Le o catalogo de 195 e devolve {id: Componente}. Sem efeito colateral."""
    global _CACHE
    if caminho is None and _CACHE is not None:
        return _CACHE
    origem = Path(caminho) if caminho else CATALOGO
    try:
        bruto = json.loads(origem.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise RuntimeError("catalogo de componentes ilegivel: %s" % origem) from erro
    if not isinstance(bruto, dict):
        raise RuntimeError("catalogo deve ser um objeto indexado por id")

    componentes: dict[str, Componente] = {}
    for cid, item in bruto.items():
        if not isinstance(item, dict):
            continue
        modulo, pacote, _ = PYTHON.get(cid, (None, None, "nucleo"))
        binario = BINARIO_OVERRIDE.get(cid, cid) if cid in _ids_com_binario() else None
        natureza = str(item.get("natureza") or "review_required")
        componentes[cid] = Componente(
            id=cid,
            natureza=natureza,
            estado_catalogo=str(item.get("estado") or "DESCONHECIDO"),
            grupo=_grupo_do_componente(cid, natureza, modulo, binario),
            prova=str(item.get("prova") or ""),
            motivo=str(item.get("motivo") or ""),
            onde=str(item.get("onde") or ""),
            modulo=modulo,
            binario=binario,
            pacote_pip=pacote,
            sonda=SONDAS_HTTP.get(cid),
            dominio=DOMINIO.get(cid),
        )
    if caminho is None:
        _CACHE = componentes
    return componentes


def limpar_cache() -> None:
    """Descarta o cache em memoria (usado pelos testes)."""
    global _CACHE
    _CACHE = None


def obter(cid: str) -> Componente:
    """Metadados de um id. Levanta KeyError se nao existir no catalogo."""
    componentes = carregar()
    if cid not in componentes:
        raise KeyError(cid)
    return componentes[cid]


def listar() -> list[Componente]:
    return [carregar()[cid] for cid in sorted(carregar())]


def validar_catalogo(esperado: int = 195) -> dict[str, Any]:
    """Verifica integridade estrutural. Nao mede execucao."""
    componentes = carregar()
    problemas: list[str] = []
    if len(componentes) != esperado:
        problemas.append("total %d != esperado %d" % (len(componentes), esperado))
    for cid, comp in componentes.items():
        if not comp.natureza:
            problemas.append("%s sem natureza" % cid)
        if comp.grupo not in GRUPOS:
            problemas.append("%s aponta grupo inexistente %s" % (cid, comp.grupo))
        if comp.natureza in ("external_api", "api_or_data") and not comp.sonda \
                and cid not in CREDENCIAL_NECESSARIA:
            problemas.append("%s API sem sonda e sem bloqueio declarado" % cid)
    return {"total": len(componentes), "grupos": len(GRUPOS),
            "ids_unicos": len(set(componentes)), "problemas": problemas,
            "integro": not problemas}

# ---------------------------------------------------------------------------
# RESOLUCAO: o que ESTE host consegue fazer agora
# ---------------------------------------------------------------------------
def _limites(grupo: str, fatos: FatosAmbiente) -> dict[str, Any]:
    config = GRUPOS.get(grupo, {})
    return {"memoria_mb": config.get("memoria_mb", 0),
            "cpus": config.get("cpus", 0.0),
            "timeout_s": config.get("timeout_s", 0),
            "somente_leitura": True,
            "rede": grupo == "remoto"}


def resolver(cid: str, fatos: FatosAmbiente | None = None) -> Resolucao:
    """Decide backend e motivo para um componente, com base no host medido.

    Nunca levanta excecao por componente ausente do catalogo: devolve
    BLOQUEADO_SEM_ESPECIFICACAO, porque um id desconhecido nao pode ser
    executado (isso tambem impede execucao arbitraria por parametro externo).
    """
    fatos = fatos or FatosAmbiente.medir()
    try:
        comp = obter(cid)
    except KeyError:
        return Resolucao(cid, SEM_ESPEC, "nenhum", "desconhecido",
                         "id nao existe no catalogo de 195", {})

    grupo = comp.grupo
    limites = _limites(grupo, fatos)
    backend = GRUPOS.get(grupo, {}).get("backend", "bloqueado")

    # 1) bloqueios declarados vencem qualquer disponibilidade local
    if cid in CREDENCIAL_NECESSARIA:
        return Resolucao(cid, SEM_CREDENCIAL, "nenhum", grupo,
                         "exige credencial: %s" % CREDENCIAL_NECESSARIA[cid], limites)
    if backend == "bloqueado":
        return Resolucao(cid, HUMANO, "nenhum", grupo,
                         comp.motivo or "catalogo marca decisao humana pendente",
                         limites)

    # 2) APIs: sonda publica = remoto executavel
    if backend == "remoto":
        if comp.sonda:
            return Resolucao(cid, REMOTO, "remoto", grupo,
                             "sonda HTTP publica declarada", limites)
        dominio = comp.dominio
        if dominio and dominio in fatos.satelites:
            return Resolucao(cid, REMOTO, "remoto", grupo,
                             "satelite '%s' configurado" % dominio, limites)
        return Resolucao(cid, SEM_ESPEC, "nenhum", grupo,
                         "sem sonda publica e sem satelite configurado", limites)

    # 3) modulo Python disponivel NESTE interpretador
    if comp.modulo:
        modulo_ok = fatos.importaveis.get(comp.modulo)
        if modulo_ok is None:
            import importlib.util
            try:
                modulo_ok = importlib.util.find_spec(comp.modulo) is not None
            except (ImportError, ValueError, ModuleNotFoundError):
                modulo_ok = False
        if modulo_ok:
            detalhe = ("grupo pesado" if grupo not in ("nucleo", "sci-leve")
                       else "leve")
            return Resolucao(cid, LOCAL, "local", grupo,
                             "modulo '%s' importavel (%s)" % (comp.modulo, detalhe),
                             limites)

    # 4) binario no PATH
    if comp.binario and fatos.binarios.get(cid):
        return Resolucao(cid, SUBPROCESSO, "subprocesso", grupo,
                         "binario '%s' encontrado no PATH" % comp.binario, limites)

    # 5) Docker disponivel
    if fatos.docker:
        if fatos.tem_imagem(grupo):
            return Resolucao(cid, DOCKER_PRONTO, "docker", grupo,
                             "imagem do grupo '%s' ja construida" % grupo, limites)
        return Resolucao(cid, DOCKER_CONSTRUIR, "docker", grupo,
                         "imagem do grupo '%s' precisa ser construida" % grupo,
                         limites)

    # 6) nada disponivel: dizer exatamente o que falta
    if backend == "docker":
        # Pacote Python LEVE ainda tem saida local honesta: pip no proprio
        # interpretador (documentado no relatorio como menos isolado). Grupo
        # pesado/GUI/compilacao nao se instala no app: exige imagem.
        if comp.pacote_pip and grupo == "sci-leve":
            return Resolucao(cid, INSTALAVEL, "nenhum", grupo,
                             "pip install %s (local) ou imagem Docker do grupo '%s'"
                             % (comp.pacote_pip, grupo), limites)
        if comp.binario:
            return Resolucao(cid, SEM_DOCKER, "nenhum", grupo,
                             "binario '%s' ausente e imagem do grupo '%s' "
                             "indisponivel (docker ausente no host)"
                             % (comp.binario, grupo), limites)
        return Resolucao(cid, SEM_DOCKER, "nenhum", grupo,
                         "grupo '%s' exige imagem Docker (docker ausente no host)"
                         % grupo, limites)
    if comp.pacote_pip:
        return Resolucao(cid, INSTALAVEL, "nenhum", grupo,
                         "pip install %s (ou Docker para isolar)" % comp.pacote_pip,
                         limites)
    if comp.binario:
        return Resolucao(cid, SEM_DOCKER, "nenhum", grupo,
                         "binario '%s' ausente e Docker indisponivel" % comp.binario,
                         limites)
    return Resolucao(cid, SEM_ESPEC, "nenhum", grupo,
                     "catalogo nao declara modulo/binario/endpoint", limites)


def resolver_todos(fatos: FatosAmbiente | None = None) -> dict[str, Resolucao]:
    fatos = fatos or FatosAmbiente.medir()
    return {cid: resolver(cid, fatos) for cid in sorted(carregar())}


def resumo(fatos: FatosAmbiente | None = None) -> dict[str, Any]:
    """Contagem por estado resolvido, por grupo e por natureza."""
    fatos = fatos or FatosAmbiente.medir()
    resolucoes = resolver_todos(fatos)
    componentes = carregar()
    por_estado: dict[str, int] = {}
    por_grupo: dict[str, int] = {}
    por_natureza: dict[str, int] = {}
    executaveis = 0
    for cid, res in resolucoes.items():
        por_estado[res.estado] = por_estado.get(res.estado, 0) + 1
        por_grupo[res.grupo] = por_grupo.get(res.grupo, 0) + 1
        natureza = componentes[cid].natureza
        por_natureza[natureza] = por_natureza.get(natureza, 0) + 1
        executaveis += int(res.executavel)
    return {
        "total_componentes": len(resolucoes),
        "executaveis_agora": executaveis,
        "por_estado": dict(sorted(por_estado.items())),
        "por_grupo": dict(sorted(por_grupo.items())),
        "por_natureza": dict(sorted(por_natureza.items())),
        "nota": "Executavel agora != simulado com sucesso. Ver teste_componentes_195.",
    }


def grupos_usados() -> dict[str, list[str]]:
    """Componentes por grupo (para gerar imagens e organizar lotes)."""
    saida: dict[str, list[str]] = {}
    for comp in listar():
        saida.setdefault(comp.grupo, []).append(comp.id)
    return {grupo: sorted(ids) for grupo, ids in sorted(saida.items())}






