"""Leitor local do catálogo ALEF-TAV. Não instala nem executa motores externos."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).with_name("catalogo_simuladores_novas_integracoes.json")

def load_catalog(path: str | Path = CATALOG_PATH) -> dict[str, Any]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    ids = [x["id"] for x in data.get("components", [])]
    if len(ids) != len(set(ids)):
        raise ValueError("O catálogo possui IDs duplicados.")
    return data

def list_components(domain: str | None = None, priority: str | None = None,
                    status: str | None = None) -> list[dict[str, Any]]:
    data = load_catalog()
    rows = data.get("components", [])
    if domain:
        rows = [x for x in rows if x["domain"] == domain]
    if priority:
        rows = [x for x in rows if x["priority"] == priority]
    if status:
        rows = [x for x in rows if x["integration_status"] == status]
    return rows

def catalog_summary() -> dict[str, Any]:
    data = load_catalog()
    rows = data.get("components", [])
    domains: dict[str, int] = {}
    for row in rows:
        domains[row["domain"]] = domains.get(row["domain"], 0) + 1
    return {
        "catalog_version": data.get("catalog_version"),
        "new_external_components_cataloged": len(rows),
        "existing_unique_sim_functions": data.get("baseline", {}).get("detected_unique_sim_functions", 0),
        "operational_new_integrations": sum(bool(x.get("smoke_test_passed")) for x in rows),
        "by_domain": dict(sorted(domains.items())),
    }

if __name__ == "__main__":
    print(json.dumps(catalog_summary(), ensure_ascii=False, indent=2))
