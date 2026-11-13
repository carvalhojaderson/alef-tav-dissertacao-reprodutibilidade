# -*- coding: utf-8 -*-
"""Roda os testes unitarios de motores com o motor REAL (palco 3.10)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import rodar_simuladores as rs  # noqa: E402


def dentro() -> int:
    import types

    # shim minimo de pytest (o interpretador 3.10 do palco nao tem pytest):
    # cobre apenas `mark.parametrize` e `raises`, que e' o que este teste usa.
    falso = types.ModuleType("pytest")

    class _Mark:
        def parametrize(self, nomes, valores):
            def deco(funcao):
                funcao.__parametrizado__ = (nomes, valores)
                return funcao
            return deco

        def __getattr__(self, nome):
            def deco(*args, **kwargs):
                def aplicar(funcao):
                    return funcao
                return aplicar
            return deco

    class _Raises:
        def __init__(self, esperado):
            self.esperado = esperado

        def __enter__(self):
            return self

        def __exit__(self, tipo, valor, rastro):
            if tipo is None:
                raise AssertionError("nao levantou %s" % self.esperado)
            return issubclass(tipo, self.esperado)

    falso.mark = _Mark()
    falso.raises = lambda esperado, **kw: _Raises(esperado)
    sys.modules["pytest"] = falso

    sys.path.insert(0, str(AQUI))
    sys.path.insert(0, str(rs.PALCO))
    import test_ambiental_motores as testes

    nomes = sorted(n for n in dir(testes) if n.startswith("test_"))
    falhas, total = [], 0
    for nome in nomes:
        funcao = getattr(testes, nome)
        parametrizado = getattr(funcao, "__parametrizado__", None)
        casos = [()]
        if parametrizado:
            casos = [(valor,) for valor in parametrizado[1]]
        for argumentos in casos:
            total += 1
            rotulo = nome if not argumentos else "%s[%s]" % (nome, argumentos[0])
            try:
                funcao(*argumentos)
                print("PASS", rotulo)
            except Exception as erro:                    # noqa: BLE001
                falhas.append((rotulo, "%s: %s" % (type(erro).__name__, erro)))
                print("FAIL", rotulo, "->", erro)
    print("RESUMO %d/%d passaram" % (total - len(falhas), total))
    if falhas:
        print(json.dumps(falhas, ensure_ascii=False, indent=1))
        return 1
    return 0


def main() -> int:
    if os.environ.get("ALEF_CHECK310") == "1":
        return dentro()
    python310 = rs.preparar_palco(None)
    ambiente = dict(os.environ)
    ambiente.update({"ALEF_CHECK310": "1",
                     "ALEF_TAV_CORE": str(rs._core_cientifico()),
                     "ALEF_SEM_PREAQUECER": "1",
                     "PYTHONPATH": str(rs.SITE_NUMPY),
                     "PYTHONIOENCODING": "utf-8"})
    rodada = subprocess.run([python310, str(Path(__file__).resolve())],
                            env=ambiente, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    print(rodada.stdout[-4000:])
    if rodada.returncode != 0:
        print(rodada.stderr[-2000:])
    return rodada.returncode


if __name__ == "__main__":
    raise SystemExit(main())
