# -*- coding: utf-8 -*-
"""Comparação dos dois carvões KL-KOH para a dissertação."""
import csv, json, os

os.environ.setdefault("ALEF_SEM_PREAQUECER", "1")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ["AMBIENTAL_BACKUP_REPO"] = ""
os.environ["HF_TOKEN"] = ""

from ambiental_backend import (
    adsorventes, matriz_7d4, motor_pesquisa, relatorios,
)

CONTAMINANTE = "sulfametoxazol, classe ionica: anion organico"

CANDIDATOS = [
    {"rotulo":"A", "nome":"KL-KOH-1:1", "area":1262.0, "volume":0.58, "qmax":100.0},
    {"rotulo":"B", "nome":"KL-KOH-2:1", "area":963.0,  "volume":0.49, "qmax":100.0},
]

# NOTA: PZC, KL, cinética, remoção e demais entradas NÃO são enviadas
# porque NÃO estão reportadas na fonte. O sistema registrará ausência —
# isso é resultado legítimo da comparação (o que a fonte não cobre).

# Origem declarada dos valores que vêm da fonte. Necessário porque o
# simulador `superficie` ecoa o mesmo número e sobrescreve a `fonte` do
# descritor S3 (achado F2 do QA) — sem isto a tabela citaria o simulador
# como origem de um dado de literatura.
BASE_DECLARADA = {"S3": "Brazil et al., 2026",
                  "S4": "Brazil et al., 2026",
                  "D1": "Brazil et al., 2026"}

# 1. Pesquisa
pesquisa = motor_pesquisa.criar({
    "pergunta": "Comparação de KL-KOH-1:1 e KL-KOH-2:1 na adsorção de sulfametoxazol",
    "contaminante": CONTAMINANTE,
    "aplicacao": "agua",
    "condicoes": {"pH": 5.5, "temperatura_C": 25.0},
})
pesquisa_id = pesquisa["id"]

# 2. Rodar cada candidato
resultados = []
for mat in CANDIDATOS:
    print(f"\n=== {mat['rotulo']} — {mat['nome']} ===")
    val = adsorventes.validar(pesquisa_id, {
        "material": mat["nome"],
        "classe": "carvao ativado de lignina Kraft",
        "contaminante": CONTAMINANTE,
        "condicoes": {"pH": 5.5, "Ce": 10.0, "temperatura_C": 25.0},
        "caracterizacao": {
            "area_superficial": {"valor": mat["area"], "unidade": "m2/g",
                                 "metodo": "BET N2", "origem": "Brazil et al., 2026"},
            "volume_de_poros": {"valor": mat["volume"], "unidade": "cm3/g",
                                 "origem": "Brazil et al., 2026"},
            "capacidade_adsorcao": {"valor": mat["qmax"], "unidade": "mg/g",
                                    "origem": "Brazil et al., 2026"},
        },
        "simuladores": ["superficie","nano","cristalografia","cfd","dft"],
        "parametros_simulador": {
            "parametro_rede": 3.5, "densidade": 1000, "velocidade": 0.01,
            "diametro": 0.005, "viscosidade": 1e-3, "material": "C",
        },
        "modelos": ["langmuir","freundlich"],
    })
    linhas = {d["codigo"]: d for d in motor_pesquisa.descritores_do_material(
        val["material"]["id"])["descritores"]}
    resultados.append({
        "rotulo": mat["rotulo"], "nome": mat["nome"],
        "material_id": val["material"]["id"],
        "descritores": {c: {"valor": l.get("valor"), "valor_texto": l.get("valor_texto"),
                             "unidade": l.get("unidade"), "estado": l.get("estado"),
                             "fonte": l.get("fonte")}
                         for c, l in linhas.items()},
        "preenchimento": val["preenchimento"],
        "compatibilidade": val["compatibilidade"],
        "modelos": {m["modelo"]: {"estado": m["estado"], "qe": m.get("qe"),
                                   "faltando": m.get("faltando")}
                     for m in val["modelos"]},
        "lacunas": [l["codigo"] for l in val["lacunas_experimentais"]],
    })


# 3. Montar a tabela A × B descritor por descritor (28 linhas)
a, b = resultados
tabela = []
for d in matriz_7d4.DESCRITORES:
    cod = d["codigo"]
    la = a["descritores"].get(cod, {})
    lb = b["descritores"].get(cod, {})
    va, vb = la.get("valor"), lb.get("valor")
    delta = None
    if isinstance(va,(int,float)) and isinstance(vb,(int,float)) and vb != 0:
        delta = round((va - vb) / vb * 100, 2)
    tabela.append({
        "codigo": cod, "nome": d["nome"], "dimensao": d["dimensao"],
        # unidade do valor efetivamente gravado; sem valor, a unidade
        # descritiva da matriz (que as vezes cobre duas grandezas:
        # "cm3/g e nm"). Evita celula do tipo "0,58 cm3/g e nm".
        "unidade": (la.get("unidade") or lb.get("unidade") or d.get("unidade")),
        "A_valor": va, "A_estado": la.get("estado","ausente"),
        "B_valor": vb, "B_estado": lb.get("estado","ausente"),
        "delta_pct_A_menos_B": delta,
        "base": (BASE_DECLARADA.get(cod)
                 or (la.get("fonte") if va is not None else lb.get("fonte"))),
        "presente_em": ("A e B" if va is not None and vb is not None
                        else "só A" if va is not None
                        else "só B" if vb is not None
                        else "nenhum"),
    })

# 4. Exportar CSV (para Excel/Word)
with open("comparacao_kl_koh.csv","w",newline="",encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(tabela[0].keys()), delimiter=";")
    w.writeheader(); w.writerows(tabela)

# 5. Exportar MD (para colar na dissertação)
def fmt(v, u=None):
    if v is None: return "—"
    if isinstance(v,float): v = f"{v:.4g}"
    return f"{v} {u}" if u else str(v)

md = ["# Comparação KL-KOH-1:1 × KL-KOH-2:1 — dissertação", "",
      "Contaminante: sulfametoxazol (SMX), ânion orgânico.",
      "Condições: pH 5,5; 25 °C. Fonte: Brazil et al., 2026.", "",
      "| Cód | Descritor | Unidade | A (1:1) | B (2:1) | Δ (A−B) | Base |",
      "|---|---|---|---|---|---|---|"]


def fmt_estado(v, u, estado):
    """Marca valor `estimado` para não ser lido como dado medido."""
    texto = fmt(v, u)
    return f"{texto} *(est.)*" if v is not None and estado == "estimado" else texto


for l in tabela:
    d = f"{l['delta_pct_A_menos_B']:+.1f}%" if l['delta_pct_A_menos_B'] is not None else "—"
    md.append(f"| {l['codigo']} | {l['nome']} | {l['unidade'] or '—'} | "
              f"{fmt_estado(l['A_valor'], l['unidade'], l['A_estado'])} | "
              f"{fmt_estado(l['B_valor'], l['unidade'], l['B_estado'])} | "
              f"{d} | {l['base'] or '—'} |")
md += ["",
       "*(est.)* = valor gerado pelo núcleo local (`sim_dft`, bandgap padrão), "
       "não medido e não reportado na fonte — não usar como propriedade do material."]
with open("comparacao_kl_koh.md","w",encoding="utf-8") as f:
    f.write("\n".join(md))


# 6. JSON completo
saida = {
    "pesquisa_id": pesquisa_id,
    "contaminante": CONTAMINANTE,
    "condicoes": {"pH":5.5, "temperatura_C":25.0},
    "candidatos": resultados,
    "tabela_28_descritores": tabela,
    "resumo": {
        "A_com_dado": a["preenchimento"]["com_dado"],
        "B_com_dado": b["preenchimento"]["com_dado"],
        "empate_cobertura": a["preenchimento"]["com_dado"] == b["preenchimento"]["com_dado"],
        "descritores_so_em_A": [l["codigo"] for l in tabela if l["presente_em"]=="só A"],
        "descritores_so_em_B": [l["codigo"] for l in tabela if l["presente_em"]=="só B"],
        "descritores_em_ambos": [l["codigo"] for l in tabela if l["presente_em"]=="A e B"],
        "descritores_em_nenhum": [l["codigo"] for l in tabela if l["presente_em"]=="nenhum"],
    },
}
with open("comparacao_kl_koh.json","w",encoding="utf-8") as f:
    json.dump(saida,f,indent=2,ensure_ascii=False,default=str)

# 7. Resumo no console
print("\n=== RESUMO A × B ===")
print(f"A ({a['nome']}): {a['preenchimento']['com_dado']}/28 descritores com dado")
print(f"B ({b['nome']}): {b['preenchimento']['com_dado']}/28 descritores com dado")
print("Presentes em ambos:", saida["resumo"]["descritores_em_ambos"])
print("Só em A:", saida["resumo"]["descritores_so_em_A"])
print("Só em B:", saida["resumo"]["descritores_so_em_B"])
print("Ausentes nos dois:", saida["resumo"]["descritores_em_nenhum"])
print("\nArquivos: comparacao_kl_koh.csv | .md | .json")

