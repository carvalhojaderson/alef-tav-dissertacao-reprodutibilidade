# -*- coding: utf-8 -*-
"""Preenche as 28 celulas da matriz 7Dx4 para KL-KOH-1:1 (A) e 2:1 (B).

O dossie (`dossie_matriz.py`) diz de onde sai cada valor; este arquivo executa.

Uso
===

    python preencher_matriz.py                  # monta a tabela, nao grava nada
    python preencher_matriz.py --gravar         # grava numa COPIA do banco
    python preencher_matriz.py --gravar-real    # grava no banco real (com bkp)
    python preencher_matriz.py --python310 P    # forca o interpretador 3.10

Por que o palco 3.10: os motores experimentais dependem do bytecode CPython
3.10 de `analises_experimentais` (ver `rodar_simuladores.py`).  Este script
reusa o mesmo palco em vez de duplicar o carregador.

O que e' gravado
================

1. caracterizacao dos componentes (`componentes.registrar`, sem preencher
   descritor automatico): adsorvente (S3, S4, diametro de poro, densidade),
   adsorbato (SMX) e meio;
2. as 28 celulas por `motor_pesquisa.registrar_valor_medido`, que e' o caminho
   oficial de escrita e ja detecta conflito > 10% com o valor anterior.

Cada descritor leva no `dados_json.complemento`: `nivel` (1 medido, 2 derivado,
3 cenario, 4 nao aplicavel), `base` e `rota`.  E' isso que permite defender
depois, celula por celula, o que e' medicao e o que e' cenario.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import dossie_matriz as dossie                      # noqa: E402
import rodar_simuladores as rs                       # noqa: E402

MOTORES_JSON = AQUI / "_motores_matriz.json"
SAIDA_JSON = AQUI / "dossie_matriz_kl_koh.json"
COPIA_DADOS = AQUI / "_qa_matriz"
BANCO_REAL = AQUI / "dados_ambiental" / "ambiental.db"
BANCO_BACKUP = AQUI / "dados_ambiental" / "ambiental.backup-matriz.db"

NIVEIS = {0: "pendente", 1: "medido", 2: "derivado", 3: "cenario", 4: "n/a"}


# --------------------------------------------------------------- palco 3.10
def executar_motores() -> None:
    """Roda os motores do dossie (dentro do 3.10) e despeja JSON."""
    sys.path.insert(0, str(rs.PALCO))
    from ambiental_backend import descritores_simuladores as ds

    saida = {}
    for material in dossie.MATERIAIS:
        rotulo = material["rotulo"]
        for nome, parametros in dossie.entradas_motores(rotulo).items():
            try:
                resultado = ds.executar(nome, dict(parametros),
                                        "SMX em carvao KL-KOH", True)
            except Exception as erro:                        # noqa: BLE001
                resultado = {"simulador": nome, "estado": "excecao_local",
                             "erro": "%s: %s" % (type(erro).__name__, erro),
                             "descritores": []}
            resultado["parametros_usados"] = parametros
            saida["%s|%s" % (rotulo, nome)] = resultado
    with open(MOTORES_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(saida, arquivo, ensure_ascii=False, indent=1, default=str)


def rodar_no_palco(python310: str) -> None:
    ambiente = dict(os.environ)
    ambiente.update({
        "ALEF_MATRIZ310": "1",
        "ALEF_TAV_CORE": str(rs._core_cientifico()),
        "ALEF_SEM_PREAQUECER": "1",
        "PYTHONPATH": str(rs.SITE_NUMPY),
        "PYTHONIOENCODING": "utf-8",
    })
    rodada = subprocess.run([python310, str(Path(__file__).resolve())],
                            env=ambiente, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if rodada.returncode != 0:
        raise SystemExit("execucao no palco falhou:\n%s%s"
                         % (rodada.stdout[-2000:], rodada.stderr[-3000:]))



# ------------------------------------------------------- 28 celulas montadas
def _produto(saida: dict, chave: str, modo: str = "valor"):
    for item in saida.get("descritores") or []:
        if item.get("chave") != chave:
            continue
        if (item.get("modo") or "valor") != modo:
            continue
        return item
    return None


def _apoio(saida: dict, codigo: str) -> list:
    return [{"chave": item.get("chave"), "valor": item.get("valor"),
             "unidade": item.get("unidade"), "memoria": item.get("memoria")}
            for item in saida.get("descritores") or []
            if item.get("codigo") == codigo
            and (item.get("modo") or "valor") == "apoio"]


def _cobertura(saida: dict):
    """Fracao (0-1) da massa coberta pelo indicador, se o motor informar.

    A chave vem como `cobertura_avaliada_pct` **dentro** do resultado da
    analise, que por sua vez esta dentro de `saida["resultado"]` - por isso a
    busca e' recursiva e o sufixo `_pct` e' dividido por 100.
    """
    def _procurar(dados, profundidade=0):
        if not isinstance(dados, dict) or profundidade > 3:
            return None
        for chave, valor in dados.items():
            nome = str(chave).lower()
            if "cobertura" in nome and isinstance(valor, (int, float)):
                fracao = (float(valor) / 100.0 if nome.endswith("pct")
                          else float(valor))
                return fracao if fracao <= 1.0 else fracao / 100.0
            if isinstance(valor, dict):
                achado = _procurar(valor, profundidade + 1)
                if achado is not None:
                    return achado
        return None

    return _procurar(saida)


def montar_celulas(rotulo: str, motores: dict, atuais: dict):
    """Devolve as 28 linhas do material, com valor, lastro e memoria."""
    from ambiental_backend import matriz_7d4

    regras = dossie.dados_regras(rotulo)
    linhas = []
    for celula in dossie.celulas():
        codigo = celula["codigo"]
        rota = celula["rota"]
        nivel = int(celula.get("nivel") or 0)
        linha = {
            "codigo": codigo, "rota": rota, "nivel": nivel,
            "nivel_nome": NIVEIS.get(nivel, "?"), "base": celula.get("base"),
            "unidade": celula.get("unidade"), "valor": None,
            "valor_texto": None, "estado": celula.get("estado"),
            "memoria": None, "complemento": {}, "faltando": None,
        }
        if rota.startswith("banco:"):
            atual = atuais.get(rota.split(":", 1)[1]) or {}
            linha.update({
                "valor": atual.get("valor"),
                "valor_texto": atual.get("valor_texto"),
                "unidade": atual.get("unidade") or linha["unidade"],
                "estado": atual.get("estado") or "presente",
                "memoria": "valor medido em bancada (nao calculado)",
                "fonte": dossie.FONTE_ANCORA,
            })
        elif rota.startswith("motor:"):
            nome, chave = rota.split(":", 1)[1].split("/")
            saida = motores.get("%s|%s" % (rotulo, nome)) or {}
            produto = _produto(saida, chave)
            if produto is None:
                linha.update({"estado": "ausente", "nivel": 0,
                              "faltando": saida.get("faltando") or [],
                              "fonte": celula.get("fonte") or nome,
                              "memoria": "motor nao entregou a chave %s "
                                         "(estado %s)" % (chave,
                                                          saida.get("estado"))})
            else:
                linha.update({
                    "valor": produto.get("valor"),
                    "valor_texto": produto.get("valor_texto"),
                    "unidade": celula.get("unidade") or produto.get("unidade"),
                    "estado": produto.get("estado") or "calculado",
                    "memoria": produto.get("memoria"),
                    "fonte": celula.get("fonte") or nome,
                })
                apoio = _apoio(saida, codigo)
                if apoio:
                    linha["complemento"]["apoio"] = apoio
        elif rota.startswith("regra:"):
            dados = regras.get(rota.split(":", 1)[1]) or {}
            saida = matriz_7d4.aplicar(rota.split(":", 1)[1], dados)
            if saida.get("estado") != "calculado":
                linha.update({"estado": "ausente", "nivel": 0,
                              "faltando": saida.get("faltando") or [],
                              "fonte": celula.get("fonte") or codigo,
                              "memoria": saida.get("motivo")})
            else:
                linha.update({
                    "valor": saida.get("valor"),
                    "unidade": celula.get("unidade") or saida.get("unidade"),
                    "estado": celula.get("estado") or "calculado",
                    "memoria": saida.get("memoria"),
                    "fonte": celula.get("fonte") or "regra %s" % codigo,
                })
                if saida.get("complemento"):
                    linha["complemento"].update(saida["complemento"])
        elif rota == "direto":
            linha.update({
                "valor": celula.get("valor"),
                "valor_texto": celula.get("valor_texto"),
                "estado": celula.get("estado") or "estimado",
                "memoria": celula.get("base"),
                "fonte": celula.get("fonte"),
            })
        else:  # rota == "na"
            linha.update({"valor": None, "valor_texto": celula.get("base"),
                          "estado": celula.get("estado") or "ausente",
                          "fonte": celula.get("fonte"),
                          "faltando": celula.get("faltando")})
        linhas.append(_fechar(linha, celula, rotulo, motores, nivel))
    return linhas


def _fechar(linha: dict, celula: dict, rotulo: str, motores: dict,
            nivel: int) -> dict:
    """Aplica o fallback do C1, os complementos e o rotulo de lastro."""
    codigo = linha["codigo"]
    if codigo == "C1" and celula.get("fallback"):
        nome = celula["rota"].split(":", 1)[1].split("/")[0]
        cobertura = _cobertura(motores.get("%s|%s" % (rotulo, nome)) or {})
        limite = float(celula.get("cobertura_minima") or 0.5)
        if linha["valor"] is None or (cobertura is not None
                                      and cobertura < limite):
            linha.update({
                "valor": None,
                "valor_texto": celula["fallback"]["valor_texto"],
                "estado": celula["fallback"]["estado"],
                "fonte": celula["fallback"]["fonte"],
                "memoria": "indice numerico descartado (cobertura %s)"
                           % ("n/d" if cobertura is None
                              else "%.1f%%" % (100 * cobertura)),
            })
    if celula.get("complemento"):
        linha["complemento"].update(celula["complemento"])
    linha["complemento"].update({
        "nivel": nivel, "nivel_nome": NIVEIS.get(nivel, "?"),
        "base": celula.get("base"), "rota": celula.get("rota"),
        "material": rotulo,
    })
    linha["fonte"] = "%s [nivel %d: %s]" % (linha.get("fonte") or "?",
                                            nivel, NIVEIS.get(nivel, "?"))
    return linha



# ------------------------------------------------------------- banco e escrita
def configurar_banco(copia: bool) -> str:
    """Aponta o backend para a copia (ou para o banco real) ANTES do import.

    O backend resolve o banco por `AMBIENTAL_BANCO_URL`/`ALEF_TAV_DATABASE_URL`/
    `DATABASE_URL` e, quando nenhuma existe, cai no `nucleo_dados` (outro
    arquivo).  Por isso as tres variaveis sao sempre definidas aqui - foi o
    motivo de a pesquisa "sumir" numa rodada anterior.
    """
    if not copia:
        destino = BANCO_REAL
    else:
        if not BANCO_REAL.is_file():
            raise SystemExit("banco de origem ausente: %s" % BANCO_REAL)
        shutil.rmtree(COPIA_DADOS, ignore_errors=True)
        COPIA_DADOS.mkdir()
        destino = COPIA_DADOS / "ambiental.db"
        shutil.copy2(BANCO_REAL, destino)
        os.environ["AMBIENTAL_DADOS"] = str(COPIA_DADOS)
    url = "sqlite:///" + destino.as_posix()
    os.environ.setdefault("AMBIENTAL_DADOS", str(AQUI / "dados_ambiental"))
    for variavel in ("AMBIENTAL_BANCO_URL", "ALEF_TAV_DATABASE_URL",
                     "DATABASE_URL"):
        os.environ[variavel] = url
    return str(destino)


def gravar_material(rotulo: str, material_id: str, linhas: list) -> dict:
    """Grava caracterizacao dos componentes e as 28 celulas."""
    from ambiental_backend import componentes, motor_pesquisa

    relatorio = {"componentes": [], "descritores": [], "erros": [],
                 "conflitos": []}
    valores = {linha["codigo"]: linha for linha in linhas}
    for componente, itens in dossie.dados_componentes(rotulo, valores).items():
        try:
            resposta = componentes.registrar(
                material_id, componente, itens, dossie.PESQUISA,
                preencher_descritor=False)
            relatorio["componentes"].append({
                "componente": componente,
                "gravados": len(resposta["gravados"]),
                "avisos": resposta["avisos"]})
        except Exception as erro:                            # noqa: BLE001
            relatorio["erros"].append("componente %s: %s: %s"
                                      % (componente, type(erro).__name__, erro))
    for linha in linhas:
        try:
            resposta = motor_pesquisa.registrar_valor_medido(
                material_id, linha["codigo"], valor=linha.get("valor"),
                valor_texto=linha.get("valor_texto"),
                unidade=linha.get("unidade"), estado=linha.get("estado"),
                fonte=linha.get("fonte"), pesquisa_id=dossie.PESQUISA,
                complemento=dict(linha.get("complemento") or {},
                                 faltando=linha.get("faltando")),
                memoria=linha.get("memoria"))
            relatorio["descritores"].append(linha["codigo"])
            if resposta.get("conflito"):
                relatorio["conflitos"].append(
                    {"codigo": linha["codigo"],
                     "conflito": resposta["conflito"]})
        except Exception as erro:                            # noqa: BLE001
            relatorio["erros"].append("descritor %s: %s: %s"
                                      % (linha["codigo"], type(erro).__name__,
                                         erro))
    return relatorio


# ------------------------------------------------------------------- relatorio
def imprimir_tabela(dados: dict) -> None:
    print("| cod | rota | nivel | A | B | unidade | estado |")
    print("|---|---|---|---|---|---|---|")
    for indice, celula in enumerate(dossie.celulas()):
        codigo = celula["codigo"]
        linha_a = dados["A"]["celulas"][indice]
        linha_b = dados["B"]["celulas"][indice]

        def _valor(linha):
            if linha.get("valor") is not None:
                return ("%g" % linha["valor"])
            texto = linha.get("valor_texto")
            return (str(texto)[:26] + "...") if texto else "-"

        nivel = linha_a.get("nivel")
        print("| %s | %s | %s | %s | %s | %s | %s |" % (
            codigo, str(celula["rota"])[:26], nivel, _valor(linha_a),
            _valor(linha_b), (linha_a.get("unidade") or "")[:9],
            (linha_a.get("estado") or "")[:12]))


def resumo_niveis(linhas: list) -> dict:
    contagem = {}
    for linha in linhas:
        nome = linha.get("nivel_nome") or "?"
        contagem[nome] = contagem.get(nome, 0) + 1
    return contagem


def principal() -> int:
    analisador = argparse.ArgumentParser(
        description="Preenche a matriz 7Dx4 de KL-KOH-1:1 e 2:1")
    analisador.add_argument("--gravar", action="store_true",
                            help="gravar numa copia do banco (_qa_matriz/)")
    analisador.add_argument("--gravar-real", action="store_true",
                            help="gravar no banco real (faz backup antes)")
    analisador.add_argument("--python310", default=None,
                            help="caminho do python.exe 3.10")
    analisador.add_argument("--json", action="store_true",
                            help="escrever dossie_matriz_kl_koh.json")
    argumentos = analisador.parse_args()

    if os.environ.get("ALEF_MATRIZ310") == "1":
        executar_motores()
        return 0

    python310 = rs.preparar_palco(argumentos.python310)
    print("palco:", rs.PALCO)
    rodar_no_palco(python310)
    with open(MOTORES_JSON, encoding="utf-8") as arquivo:
        motores = json.load(arquivo)
    ok = sum(1 for chave, valor in motores.items()
             if str(valor.get("estado") or "").startswith("ok"))
    print("motores: %d/%d executaram" % (ok, len(motores)))

    if argumentos.gravar_real:
        if BANCO_REAL.is_file():
            shutil.copy2(BANCO_REAL, BANCO_BACKUP)
            print("backup:", BANCO_BACKUP.name)
        alvo = configurar_banco(copia=False)
    elif argumentos.gravar:
        alvo = configurar_banco(copia=True)
    else:
        alvo = configurar_banco(copia=False)
    print("banco:", alvo)

    from ambiental_backend import adsorventes

    dados = {}
    for material in dossie.MATERIAIS:
        rotulo = material["rotulo"]
        anterior = adsorventes.obter_validacao(dossie.PESQUISA, material["id"])
        atuais = {item["codigo"]: item for item in anterior["descritores"]}
        dados[rotulo] = {
            "material_id": material["id"], "nome": material["nome"],
            "antes": anterior["preenchimento"],
            "celulas": montar_celulas(rotulo, motores, atuais),
            "relatorio": None, "depois": None,
        }

    imprimir_tabela(dados)
    print()
    for rotulo in ("A", "B"):
        info = dados[rotulo]
        print("%s (%s) niveis: %s" % (rotulo, info["nome"],
                                      resumo_niveis(info["celulas"])))

    if argumentos.gravar or argumentos.gravar_real:
        print()
        for rotulo in ("A", "B"):
            info = dados[rotulo]
            info["relatorio"] = gravar_material(rotulo, info["material_id"],
                                               info["celulas"])
            info["depois"] = adsorventes.obter_validacao(
                dossie.PESQUISA, info["material_id"])["preenchimento"]
            antes = info["antes"]
            depois = info["depois"]
            print("%s: cobertura %d/%d -> %d/%d (%s%% -> %s%%)" % (
                rotulo, antes["com_dado"], antes["total_avaliado"],
                depois["com_dado"], depois["total_avaliado"],
                antes["percentual_com_dado"], depois["percentual_com_dado"]))
            print("   gravados: %d descritores, %d componentes, %d erros" % (
                len(info["relatorio"]["descritores"]),
                sum(c["gravados"] for c in info["relatorio"]["componentes"]),
                len(info["relatorio"]["erros"])))
            for erro in info["relatorio"]["erros"]:
                print("   ERRO:", erro)
            for conflito in info["relatorio"]["conflitos"]:
                print("   conflito:", conflito["codigo"],
                      conflito["conflito"].get("aviso"))

    if argumentos.json:
        with open(SAIDA_JSON, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=1, default=str)
        print("\ndossie:", SAIDA_JSON.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())

