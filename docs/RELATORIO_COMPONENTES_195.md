# Relatorio de validacao dos componentes externos

Gerado por `infra/gerar_relatorio.py` a partir de `relatorio_componentes_195.json`. Nenhum numero aqui e digitado a mao.

## Ambiente

| Item | Valor |
|---|---|
| Data | 2026-10-29T11:38:33 |
| Python | 3.10.19 |
| Sistema | Windows |
| Docker | AUSENTE |
| Componentes avaliados | 195 |
| Tempo total | 537.1 s |
| Aquecimento dos motores | 22.4 s, modo rapido, 13 modulos |

## Estados (colunas independentes)

| Estado | Quantidade |
|---|---|
| `inventariado` | 195 |
| `implementacao_identificada` | 147 |
| `dependencias_resolvidas` | 28 |
| `imagem_construida` | 0 |
| `ambiente_iniciado` | 27 |
| `simulacao_executada` | 26 |
| `resultado_validado` | 25 |
| `integracao_api_aprovada` | 26 |

## Situacao final

| Situacao | Quantidade |
|---|---|
| `AMBIENTE_OK_SEM_CALCULO` | 1 |
| `APENAS_CATALOGADO` | 48 |
| `DEPENDENCIAS_OK_SEM_EXECUCAO` | 1 |
| `EXECUTADO_SEM_VALIDACAO` | 1 |
| `IMPLEMENTACAO_SEM_AMBIENTE` | 119 |
| `VALIDADO` | 25 |

## Integracao pela API

| Item | Valor |
|---|---|
| `/api/componentes/registro` responde 195 | sim |
| Componentes despachados via HTTP | 26 |
| Aprovados | 26 |
| Reprovados | 0 |

## Falha e timeout

```json
{
  "id_invalido": {
    "status": "BLOQUEADO",
    "bloqueado": true,
    "erro": "id nao existe no catalogo de 195"
  },
  "timeout_local": {
    "componente": "ase",
    "status": "OK",
    "observacao": "backend local nao e' preemptivo"
  }
}
```

## Componentes validados cientificamente (25)

| Componente | Backend | Grupo | Situacao |
|---|---|---|---|
| alphafold-protein-structure-database | remoto | remoto | VALIDADO |
| ase | local | nucleo | VALIDADO |
| bio-tools-registry | remoto | remoto | VALIDADO |
| biomodels-database | remoto | remoto | VALIDADO |
| brian2 | local | sci-leve | VALIDADO |
| chembl-api | remoto | remoto | VALIDADO |
| cobrapy | local | sci-leve | VALIDADO |
| europe-pmc-rest-api | remoto | remoto | VALIDADO |
| flopy | local | sci-leve | VALIDADO |
| gbif-api | remoto | remoto | VALIDADO |
| kegg-rest-api | remoto | remoto | VALIDADO |
| mesa | local | sci-leve | VALIDADO |
| ncbi-pubmed-e-utilities | remoto | remoto | VALIDADO |
| nomad | remoto | remoto | VALIDADO |
| obis-api | remoto | remoto | VALIDADO |
| pubchem-pug-rest | remoto | remoto | VALIDADO |
| pybamm | local | sci-leve | VALIDADO |
| pymatgen | local | nucleo | VALIDADO |
| rasterio | local | sci-leve | VALIDADO |
| rcsb-protein-data-bank-apis | remoto | remoto | VALIDADO |
| rdkit | local | nucleo | VALIDADO |
| reactome-content-analysis-api | remoto | remoto | VALIDADO |
| uniprot-rest-api | remoto | remoto | VALIDADO |
| usgs-water-data-apis | remoto | remoto | VALIDADO |
| wntr | local | sci-leve | VALIDADO |

## Executados sem validacao cientifica (1)

Rodaram de fato, mas o numero nao confere ou a prova e apenas de ambiente. Nao contam como aprovados.

| Componente | Backend | Grupo | Situacao |
|---|---|---|---|
| open-babel | subprocesso | cli-quim | EXECUTADO_SEM_VALIDACAO |

## Componentes sem ambiente neste host (167)

| Componente | Grupo | Situacao | Detalhe |
|---|---|---|---|
| `abinit` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'abinit' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `activity-browser` | worker-gui | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'worker-gui' exige imagem Docker (docker ausente no host) |
| `adcirc` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'adcirc' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `aermod` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'aermod' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `agromo` | servico | APENAS_CATALOGADO | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `aiida-workflows` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `apsim-next-generation` | servico | APENAS_CATALOGADO | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `aquacrop` | revisao | APENAS_CATALOGADO | catalogo marca decisao humana pendente |
| `aquatox` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'aquatox' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `arbor` | build | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'build' exige imagem Docker (docker ausente no host) |
| `atomate2` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `autodock-vina` | cli-quim | IMPLEMENTACAO_SEM_AMBIENTE | binario 'vina' ausente e imagem do grupo 'cli-quim' indisponivel (docker ausente no host) |
| `battmo` | servico | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `bcftools` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'bcftools' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `bedtools` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'bedtools' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `betse` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `bioconductor` | r-stats | APENAS_CATALOGADO | grupo 'r-stats' exige imagem Docker (docker ausente no host) |
| `bionetgen` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'BNG2.pl' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `biosimspace` | servico | APENAS_CATALOGADO | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `biosteam` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install biosteam (local) ou imagem Docker do grupo 'sci-leve' |
| `blast` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'blastn' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `bracken` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'bracken' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `brightway` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install brightway25 (local) ou imagem Docker do grupo 'sci-leve' |
| `bsm2-python` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install bsm2-python (local) ou imagem Docker do grupo 'sci-leve' |
| `bwa-mem2` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'bwa-mem2' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `cantera` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install cantera (local) ou imagem Docker do grupo 'sci-leve' |
| `capytaine` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install capytaine (local) ou imagem Docker do grupo 'sci-leve' |
| `cell-ranger` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `cellmodeller` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `cellprofiler` | worker-gui | APENAS_CATALOGADO | grupo 'worker-gui' exige imagem Docker (docker ausente no host) |
| `chaste` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `checkm2` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'checkm2' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `chgnet` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `cmaq` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'CCTM' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `colabfold` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'colabfold_batch' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `compucell3d` | servico | APENAS_CATALOGADO | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `copasi` | servico | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `copernicus-data-space-apis` | remoto | APENAS_CATALOGADO | exige credencial: OAuth client (CDSE) |
| `covasim` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install covasim (local) ou imagem Docker do grupo 'sci-leve' |
| `cp2k` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'cp2k.popt' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `crop2ml-crop-model-repository` | remoto | APENAS_CATALOGADO | exige credencial: repositorio remoto indisponivel |
| `dada2` | r-stats | APENAS_CATALOGADO | grupo 'r-stats' exige imagem Docker (docker ausente no host) |
| `delft3d` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'd_hydro' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `deseq2` | r-stats | APENAS_CATALOGADO | grupo 'r-stats' exige imagem Docker (docker ausente no host) |
| `dssat` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `dwsim` | servico | APENAS_CATALOGADO | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `e-cell4` | build | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'build' exige imagem Docker (docker ausente no host) |
| `edger` | r-stats | APENAS_CATALOGADO | grupo 'r-stats' exige imagem Docker (docker ausente no host) |
| `elmer-fem` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'ElmerSolver' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `emod` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `epa-comptox-chemicals-dashboard` | remoto | APENAS_CATALOGADO | exige credencial: EPA_COMPTOX_KEY |
| `epa-swmm` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'swmm5' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `epa-test-opera` | revisao | APENAS_CATALOGADO | instalacao real falhou nas duas passadas / ultimos erros: pip epa-test-opera:   cause: Because epa-test-opera  |
| `epanet` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'epanet2' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `epimodel` | r-stats | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'r-stats' exige imagem Docker (docker ausente no host) |
| `esa-snap` | cli-geo | IMPLEMENTACAO_SEM_AMBIENTE | binario 'gpt' ausente e imagem do grupo 'cli-geo' indisponivel (docker ausente no host) |
| `farsite` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'farsite' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `fastp` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'fastp' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `fastqc` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'fastqc' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `febio` | servico | APENAS_CATALOGADO | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `fenicsx` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `fiji-imagej` | worker-gui | APENAS_CATALOGADO | grupo 'worker-gui' exige imagem Docker (docker ausente no host) |
| `flammap` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'flammap' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `foldseek` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'foldseek' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `galaxy-project` | remoto | APENAS_CATALOGADO | sem sonda publica e sem satelite configurado |
| `gama-platform` | servico | APENAS_CATALOGADO | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `gdal` | cli-geo | IMPLEMENTACAO_SEM_AMBIENTE | binario 'gdalinfo' ausente e imagem do grupo 'cli-geo' indisponivel (docker ausente no host) |
| `gnina` | cli-quim | IMPLEMENTACAO_SEM_AMBIENTE | binario 'gnina' ausente e imagem do grupo 'cli-quim' indisponivel (docker ausente no host) |
| `gpaw` | build | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'build' exige imagem Docker (docker ausente no host) |
| `grass-gis` | cli-geo | IMPLEMENTACAO_SEM_AMBIENTE | binario 'grass' ausente e imagem do grupo 'cli-geo' indisponivel (docker ausente no host) |
| `gromacs` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'gmx' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `gtdb-tk` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'gtdbtk' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `hmmer` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'hmmsearch' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `hmmer-interproscan-bridge` | servico | APENAS_CATALOGADO | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `humann` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'humann' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `hydromt` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `hysplit` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'hycs_std' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `idaes` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `ilastik` | worker-gui | APENAS_CATALOGADO | grupo 'worker-gui' exige imagem Docker (docker ausente no host) |
| `iq-tree` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'iqtree2' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `jarvis` | remoto | APENAS_CATALOGADO | exige credencial: JARVIS_NIST_KEY |
| `kallisto` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'kallisto' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `kraken-2` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'kraken2' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `lammps` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'lmp' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `libroadrunner` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install libroadrunner (local) ou imagem Docker do grupo 'sci-leve' |
| `mafft` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'mafft' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `materials-cloud` | remoto | APENAS_CATALOGADO | exige credencial: MATERIALS_CLOUD_API_KEY |
| `materials-project-api` | remoto | APENAS_CATALOGADO | exige credencial: MP_API_KEY |
| `matgl-m3gnet` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `mdanalysis` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install MDAnalysis (local) ou imagem Docker do grupo 'sci-leve' |
| `megahit` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'megahit' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `metaphlan` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'metaphlan' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `metaspades` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'metaspades.py' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `minimap2` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'minimap2' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `mmseqs2` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'mmseqs2' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `modflow-6` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'mf6' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `morpheus` | servico | APENAS_CATALOGADO | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `multiqc` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'multiqc' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `napari` | worker-gui | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'worker-gui' exige imagem Docker (docker ausente no host) |
| `nest` | build | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'build' exige imagem Docker (docker ausente no host) |
| `netlogo` | worker-gui | APENAS_CATALOGADO | grupo 'worker-gui' exige imagem Docker (docker ausente no host) |
| `netpyne` | build | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'build' exige imagem Docker (docker ausente no host) |
| `neuron` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'nrniv' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `nextflow` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'nextflow' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `nf-core` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'nf-core' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `ome-zarr` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install ome-zarr (local) ou imagem Docker do grupo 'sci-leve' |
| `omero` | remoto | APENAS_CATALOGADO | exige credencial: OMERO_USER/PASSWORD |
| `open-systems-pharmacology-suite` | revisao | APENAS_CATALOGADO | instalacao real falhou nas duas passadas / ultimos erros: pip open-systems-pharmacology-suite:   cause: Becaus |
| `opencor-cellml` | worker-gui | APENAS_CATALOGADO | grupo 'worker-gui' exige imagem Docker (docker ausente no host) |
| `opendrift` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install opendrift (local) ou imagem Docker do grupo 'sci-leve' |
| `openfast` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'openfast' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `openfoam` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'foamRun' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `openfold` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `openlca` | worker-gui | APENAS_CATALOGADO | grupo 'worker-gui' exige imagem Docker (docker ausente no host) |
| `openmm` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `openmodelica` | servico | APENAS_CATALOGADO | grupo 'servico' exige imagem Docker (docker ausente no host) |
| `openms` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'OpenMSInfo' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `opentiva` | build | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'build' exige imagem Docker (docker ausente no host) |
| `orfeo-toolbox` | cli-geo | IMPLEMENTACAO_SEM_AMBIENTE | binario 'otbcli' ausente e imagem do grupo 'cli-geo' indisponivel (docker ausente no host) |
| `parflow` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'parflow' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `pdbfixer` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `phreeqc` | cli-quim | IMPLEMENTACAO_SEM_AMBIENTE | binario 'phreeqc' ausente e imagem do grupo 'cli-quim' indisponivel (docker ausente no host) |
| `physicell` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'PhysiCell' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `picrust2` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'picrust2_pipeline.py' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `poreblazer` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `prody` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install prody (local) ou imagem Docker do grupo 'sci-leve' |
| `psi4` | build | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'build' exige imagem Docker (docker ausente no host) |
| `pysb` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install pysb (local) ou imagem Docker do grupo 'sci-leve' |
| `qgis` | cli-geo | IMPLEMENTACAO_SEM_AMBIENTE | binario 'qgis' ausente e imagem do grupo 'cli-geo' indisponivel (docker ausente no host) |
| `qiime-2` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'qiime' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `qsdsan` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install qsdsan (local) ou imagem Docker do grupo 'sci-leve' |
| `quantum-espresso` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'pw.x' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `qupath` | worker-gui | APENAS_CATALOGADO | grupo 'worker-gui' exige imagem Docker (docker ausente no host) |
| `rangeshifter` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'rangeshifter' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `raspa3` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `raven-hydrological-modelling-framework` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'raven' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `roms` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'oceanM' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `salmon` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'salmon' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `samtools` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'samtools' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `scanpy` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `schism` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'pschism' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `scvi-tools` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `sea-stack` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `seurat` | r-stats | APENAS_CATALOGADO | grupo 'r-stats' exige imagem Docker (docker ausente no host) |
| `sire` | build | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'build' exige imagem Docker (docker ausente no host) |
| `smina` | cli-quim | IMPLEMENTACAO_SEM_AMBIENTE | binario 'smina' ausente e imagem do grupo 'cli-quim' indisponivel (docker ausente no host) |
| `snakemake` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install snakemake (local) ou imagem Docker do grupo 'sci-leve' |
| `star` | cli-bio | IMPLEMENTACAO_SEM_AMBIENTE | binario 'star' ausente e imagem do grupo 'cli-bio' indisponivel (docker ausente no host) |
| `sutra` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'sutra' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `swan` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'swan.exe' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `swat` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'swat' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `telemac-mascaret` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'telemac2d.py' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `tellurium` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install tellurium (local) ou imagem Docker do grupo 'sci-leve' |
| `the-virtual-brain` | worker-gui | APENAS_CATALOGADO | grupo 'worker-gui' exige imagem Docker (docker ausente no host) |
| `tissue-forge` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `useeio` | remoto | APENAS_CATALOGADO | exige credencial: USEEIO_API_KEY |
| `vcell` | remoto | APENAS_CATALOGADO | exige credencial: VCell credentials |
| `vsoil` | build | APENAS_CATALOGADO | grupo 'build' exige imagem Docker (docker ausente no host) |
| `wasp` | cli-hidro | IMPLEMENTACAO_SEM_AMBIENTE | binario 'wasp' ausente e imagem do grupo 'cli-hidro' indisponivel (docker ausente no host) |
| `watertap` | sci-pesado | IMPLEMENTACAO_SEM_AMBIENTE | grupo 'sci-pesado' exige imagem Docker (docker ausente no host) |
| `wec-sim` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'wec-sim' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `whiteboxtools` | cli-geo | IMPLEMENTACAO_SEM_AMBIENTE | binario 'whitebox_tools' ausente e imagem do grupo 'cli-geo' indisponivel (docker ausente no host) |
| `wrf` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'wrf.exe' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `wrf-chem` | build | IMPLEMENTACAO_SEM_AMBIENTE | binario 'wrf.exe' ausente e imagem do grupo 'build' indisponivel (docker ausente no host) |
| `xarray-rioxarray` | sci-leve | IMPLEMENTACAO_SEM_AMBIENTE | pip install rioxarray (local) ou imagem Docker do grupo 'sci-leve' |
| `xtb` | cli-quim | IMPLEMENTACAO_SEM_AMBIENTE | binario 'xtb' ausente e imagem do grupo 'cli-quim' indisponivel (docker ausente no host) |
| `zeo` | cli-quim | IMPLEMENTACAO_SEM_AMBIENTE | binario 'zeo++' ausente e imagem do grupo 'cli-quim' indisponivel (docker ausente no host) |

## Como reproduzir

```
python teste_componentes_195.py            # gera o JSON
python infra/gerar_relatorio.py            # gera este Markdown
python infra/gerar_dockerfiles.py          # Dockerfiles por grupo
```
