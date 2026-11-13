# -*- coding: utf-8 -*-
"""SMX (sulfametoxazol) — dois carvões KL-KOH, sem HTTP, sem HF."""
import json, os

os.environ.setdefault("ALEF_SEM_PREAQUECER", "1")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ["AMBIENTAL_BACKUP_REPO"] = ""
os.environ["HF_TOKEN"] = ""

from ambiental_backend import (
    adsorventes, matriz_7d4, motor_pesquisa, motores_ambientais, relatorios,
)

CONTAMINANTE = "sulfametoxazol, classe ionica: anion organico"

MATERIAIS = [
    {
        "rotulo": "A", "nome": "KL-KOH-1:1",
        "area": 1262.0, "volume_poros": 0.58, "qmax": 100.0,
        # PZC e KL AUSENTES de propósito (não reportados na fonte)
    },
    {
        "rotulo": "B", "nome": "KL-KOH-2:1",
        "area": 963.0, "volume_poros": 0.49, "qmax": 100.0,
    },
]

# ---- pesquisa ----
pesquisa = motor_pesquisa.criar({
    "pergunta": "Adsorcao de sulfametoxazol (SMX) em carvoes ativados KL-KOH. Qual o melhor material?",
    "contaminante": CONTAMINANTE,
    "aplicacao": "agua",
    "condicoes": {"pH": 5.5, "temperatura_C": 25.0},
})
pesquisa_id = pesquisa["id"]
print("pesquisa:", pesquisa_id)

RESULTADO = {"pesquisa_id": pesquisa_id, "materiais": [], "comparacao": None}

# ---- cada material ----
for mat in MATERIAIS:
    print("\n=== Material", mat["rotulo"], "-", mat["nome"], "===")
    validacao = adsorventes.validar(pesquisa_id, {
        "material": mat["nome"],
        "classe": "carvao ativado de lignina Kraft",
        "contaminante": CONTAMINANTE,
        "condicoes": {"pH": 5.5, "Ce": 10.0, "temperatura_C": 25.0},
        # qmax na caracterizacao (corrige o bug #1 do relatório SMX):
        "caracterizacao": {
            "area_superficial": {"valor": mat["area"], "unidade": "m2/g",
                                 "metodo": "BET N2", "origem": "Brazil et al., 2026"},
            "volume_de_poros": {"valor": mat["volume_poros"], "unidade": "cm3/g",
                                 "origem": "Brazil et al., 2026"},
            "capacidade_adsorcao": {"valor": mat["qmax"], "unidade": "mg/g",
                                    "origem": "Brazil et al., 2026"},
            # PZC e KL NÃO enviados → Langmuir bloqueia e compat fica indeterminada
        },
        "simuladores": ["superficie", "nano", "cristalografia", "cfd", "dft"],
        "parametros_simulador": {
            "parametro_rede": 3.5, "densidade": 1000, "velocidade": 0.01,
            "diametro": 0.005, "viscosidade": 1e-3, "material": "C",
        },
        "modelos": ["langmuir", "freundlich"],
    })
    descritores = {d["codigo"]: {"valor": d.get("valor"), "estado": d["estado"],
                                 "unidade": d.get("unidade"), "fonte": d.get("fonte")}
                   for d in validacao["descritores"]}
    simuladores = [{"nome": s["simulador"], "estado": s["estado"],
                    "executado": s["executado"], "faltando": s["faltando"],
                    "descritores": [d["codigo"] for d in s.get("descritores") or []]}
                   for s in validacao["simuladores"]]
    modelos = [{"modelo": m["modelo"], "estado": m["estado"],
                "qe": m.get("qe"), "faltando": m.get("faltando")}
               for m in validacao["modelos"]]
    compat = validacao["compatibilidade"]
    lacunas = [l["codigo"] for l in validacao["lacunas_experimentais"]]
    preench = validacao["preenchimento"]

    print(f"  S3={descritores.get('S3',{}).get('valor')} m2/g")
    print(f"  D1={descritores.get('D1',{}).get('valor')} mg/g  estado={descritores.get('D1',{}).get('estado')}")
    print(f"  compatibilidade: {compat['veredito']} | classe={compat['classe_contaminante']} | faltando={compat['faltando']}")
    print(f"  modelos: {[(m['modelo'], m['estado']) for m in modelos]}")
    print(f"  simuladores ok: {[s['nome'] for s in simuladores if s['executado']]}")
    print(f"  cobertura: {preench['com_dado']}/{preench['total_avaliado']} ({preench['percentual_com_dado']}%)")
    print(f"  lacunas: {lacunas}")

    RESULTADO["materiais"].append({
        "rotulo": mat["rotulo"], "nome": mat["nome"],
        "material_id": validacao["material"]["id"],
        "descritores": descritores, "simuladores": simuladores,
        "modelos": modelos, "compatibilidade": compat,
        "lacunas": lacunas,
        "preenchimento": preench,
    })

# ---- comparação ----
a, b = RESULTADO["materiais"]
cov_a, cov_b = a["preenchimento"]["com_dado"], b["preenchimento"]["com_dado"]
RESULTADO["comparacao"] = {
    "cobertura_A": cov_a, "cobertura_B": cov_b,
    "empate": cov_a == cov_b,
    "veredito": ("empate — sem D1/D2 medido, nenhum dos dois pode ser declarado melhor"
                 if cov_a == cov_b else
                 f"material {'A' if cov_a > cov_b else 'B'} teve mais cobertura"),
}

# ---- viabilidade + prova + relatório ----
viab = motor_pesquisa.avaliar_viabilidade(pesquisa_id)
RESULTADO["viabilidade"] = {"pontuacao": viab["pontuacao"],
                            "classificacao": viab["classificacao"],
                            "lacunas": viab["lacunas"]}
prova = motor_pesquisa.prova_de_conceito(pesquisa_id)
RESULTADO["prova"] = {"estado": prova["estado"],
                      "demonstravel": prova["resultado"]["demonstravel"]}

rel_md = relatorios.gerar(pesquisa_id, "viabilidade", "md")
RESULTADO["relatorio_md"] = rel_md["arquivo"]

with open("resultado_smx_local.json", "w", encoding="utf-8") as f:
    json.dump(RESULTADO, f, indent=2, ensure_ascii=False, default=str)

print("\n=== JSON:", "resultado_smx_local.json", "===")
print(json.dumps(RESULTADO["comparacao"], indent=2, ensure_ascii=False))
