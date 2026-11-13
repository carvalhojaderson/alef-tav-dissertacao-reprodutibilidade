# -*- coding: utf-8 -*-
"""Teste de ponta a ponta do fluxo SMX na API do ALEF-TAV Ambiental.

Executa, pela API HTTP, o mesmo caminho que o painel usa para avaliar um
adsorvente:

    1. POST /api/research                       cria a pesquisa e devolve o id
    2. POST /api/research/{id}/materials  (A)   cadastra KL-KOH-1:1
    3. POST /api/research/{id}/materials  (B)   cadastra KL-KOH-2:1
    4. POST /api/research/{id}/adsorbent  (A)   simuladores -> matriz 7Dx4,
                                                modelos, compatibilidade, lacunas
    5. POST /api/research/{id}/adsorbent  (B)   idem para o segundo material
    6. resumo comparativo da cobertura 7Dx4 dos dois materiais

Nada e' inventado por este script nem por ele compensado: a caracterizacao vem
da literatura (Brazil et al., 2026) e PZC/KL ficam nulos de proposito, para
exercitar a regra de nao-invencao da plataforma (modelo sem parametro devolve
`bloqueado_por_parametros`, compatibilidade sem PZC devolve `indeterminado`).

Uso (a partir da raiz do projeto, com a API no ar)::

    python teste_smx_api.py
    python teste_smx_api.py --base-url http://127.0.0.1:7860
    python teste_smx_api.py --limpar              # apaga pesquisa/materiais no fim
    python teste_smx_api.py --json saida_smx.json # grava o resultado completo

Variavel de ambiente aceita: ALEF_API_URL (usada quando --base-url nao vem).
Codigo de saida: 0 = fluxo executado ate o fim; 1 = alguma chamada HTTP falhou.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import unicodedata

import requests

BASE_PADRAO = os.environ.get("ALEF_API_URL") or "http://127.0.0.1:7860"
TEMPO_LIMITE = 300          # s: simuladores/modelos podem demorar no primeiro uso


def _ascii(texto: str) -> str:
    """Translitera para ASCII (console legado do Windows: cp850/cp1252)."""
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_marcas = "".join(caractere for caractere in decomposto
                         if not unicodedata.combining(caractere))
    return sem_marcas.encode("ascii", "replace").decode("ascii")


class FluxoAscii:
    """Envolve stdout/stderr sem suporte a UTF-8, sem perder a formatacao."""

    def __init__(self, fluxo):
        self._fluxo = fluxo

    def write(self, texto):
        return self._fluxo.write(_ascii(texto))

    def flush(self):
        return self._fluxo.flush()

    def __getattr__(self, nome):
        return getattr(self._fluxo, nome)


CONTAMINANTE = "sulfametoxazol (SMX), classe iônica: ânion orgânico"

CORPO_PESQUISA = {
    "pergunta": ("Adsorção de sulfametoxazol (SMX) em carvões ativados "
                 "KL-KOH. Qual o melhor material?"),
    "contaminante": CONTAMINANTE,
    "aplicacao": "agua",
    "condicoes": {"pH": 5.5, "temperatura_C": 25.0},
}

#: Materiais reais da literatura (Brazil et al., 2026). Nenhum valor e'
#: completado por estimativa: o que a fonte nao reporta entra como None.
MATERIAIS = (
    {
        "rotulo": "A",
        "nome": "KL-KOH-1:1",
        "classe": "carvão ativado de lignina Kraft",
        "area_superficial": 1262.0,
        "volume_poros": 0.58,
        "propriedades": [
            {"nome": "area_superficial", "valor": 1262.0, "unidade": "m2/g",
             "origem": "Brazil et al., 2026"},
            {"nome": "volume_poros", "valor": 0.58, "unidade": "cm3/g",
             "origem": "Brazil et al., 2026"},
            {"nome": "qmax", "valor": 100.0, "unidade": "mg/g",
             "origem": "Brazil et al., 2026"},
            {"nome": "PZC", "valor": None, "unidade": "pH",
             "origem": "Não reportado"},
            {"nome": "KL", "valor": None, "unidade": "L/mg",
             "origem": "Não reportado"},
        ],
    },
    {
        "rotulo": "B",
        "nome": "KL-KOH-2:1",
        "classe": "carvão ativado de lignina Kraft",
        "area_superficial": 963.0,
        "volume_poros": 0.49,
        "propriedades": [
            {"nome": "area_superficial", "valor": 963.0, "unidade": "m2/g",
             "origem": "Brazil et al., 2026"},
            {"nome": "volume_poros", "valor": 0.49, "unidade": "cm3/g",
             "origem": "Brazil et al., 2026"},
            {"nome": "qmax", "valor": 100.0, "unidade": "mg/g",
             "origem": "Brazil et al., 2026"},
            {"nome": "PZC", "valor": None, "unidade": "pH",
             "origem": "Não reportado"},
            {"nome": "KL", "valor": None, "unidade": "L/mg",
             "origem": "Não reportado"},
        ],
    },
)

SIMULADORES = ["superficie", "nano", "cristalografia", "cfd", "dft"]
MODELOS = ["langmuir", "freundlich"]


def corpo_validacao(material_id: str, area: float, volume: float) -> dict:
    """Corpo do POST .../adsorbent para um material ja cadastrado."""
    return {
        "material_id": material_id,
        "contaminante": CONTAMINANTE,
        "caracterizacao": {
            "area_superficial": {"valor": area, "unidade": "m2/g",
                                 "metodo": "BET N2"},
            "volume_poros": {"valor": volume, "unidade": "cm3/g"},
        },
        "condicoes": {"pH": 5.5, "Ce": 10.0, "temperatura_C": 25.0},
        "simuladores": list(SIMULADORES),
        "modelos": list(MODELOS),
    }


# ---------------------------------------------------------------------- HTTP
class FalhaAPI(RuntimeError):
    """Chamada HTTP recusada ou fora do esperado."""


def _mensagem_erro(resposta) -> str:
    """Texto do envelope de erro da API (`{"erro": {...}}`), quando existir."""
    try:
        corpo = resposta.json()
    except ValueError:
        return (resposta.text or "corpo vazio")[:400]
    erro = corpo.get("erro") if isinstance(corpo, dict) else None
    if isinstance(erro, dict):
        detalhe = erro.get("detalhes")
        return "%s: %s%s" % (
            erro.get("codigo"), erro.get("mensagem"),
            (" | " + json.dumps(detalhe, ensure_ascii=False)) if detalhe else "")
    return json.dumps(corpo, ensure_ascii=False)[:400]


class Cliente:
    """Sessao HTTP com o mesmo tratamento de erro para todas as rotas."""

    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.http = requests.Session()
        self.http.headers.update({"Accept": "application/json"})

    def _requisitar(self, metodo, caminho, corpo, esperado):
        url = self.base + caminho
        try:
            resposta = self.http.request(metodo, url, json=corpo,
                                         timeout=TEMPO_LIMITE)
        except requests.RequestException as erro:
            raise FalhaAPI("%s %s: falha de rede (%s). A API esta no ar em %s?"
                           % (metodo, url, erro, self.base))
        if resposta.status_code not in esperado:
            raise FalhaAPI("%s %s -> HTTP %d | %s" % (
                metodo, caminho, resposta.status_code,
                _mensagem_erro(resposta)))
        try:
            return resposta.json()
        except ValueError:
            raise FalhaAPI("%s %s: resposta nao e' JSON" % (metodo, caminho))

    def get(self, caminho, esperado=(200,)):
        return self._requisitar("GET", caminho, None, esperado)

    def post(self, caminho, corpo=None, esperado=(200, 201)):
        return self._requisitar("POST", caminho, corpo, esperado)

    def delete(self, caminho, esperado=(200, 202, 204)):
        return self._requisitar("DELETE", caminho, None, esperado)


# ------------------------------------------------------------------ impressao
def titulo(texto: str, marca: str = "=") -> None:
    print("\n" + marca * 78)
    print(texto)
    print(marca * 78)


def sub(texto: str) -> None:
    print("\n  %s" % texto)
    print("  " + "-" * (len(texto)))


def _valor(valor, unidade=None) -> str:
    if valor is None:
        return "ausente"
    texto = ("%.6g" % valor) if isinstance(valor, (int, float)) else str(valor)
    return texto + (" " + unidade if unidade else "")


def _lista(itens) -> str:
    partes = []
    for item in itens or []:
        if isinstance(item, dict):
            partes.append(str(item.get("chave") or item.get("codigo")
                              or item.get("nome") or item))
        else:
            partes.append(str(item))
    return ", ".join(partes) if partes else "nada"


# --------------------------------------------------------------------- fluxo
def criar_pesquisa(cliente: Cliente) -> dict:
    dados = cliente.post("/api/research", corpo_pesquisa())
    return dados


def corpo_pesquisa() -> dict:
    return json.loads(json.dumps(CORPO_PESQUISA))


def cadastrar_material(cliente: Cliente, pesquisa_id: str, material: dict) -> dict:
    corpo = {"nome": material["nome"], "classe": material["classe"],
             "propriedades": material["propriedades"]}
    return cliente.post("/api/research/%s/materials" % pesquisa_id, corpo)


def validar_material(cliente: Cliente, pesquisa_id: str, material: dict,
                     material_id: str) -> dict:
    corpo = corpo_validacao(material_id, material["area_superficial"],
                            material["volume_poros"])
    return cliente.post("/api/research/%s/adsorbent" % pesquisa_id, corpo)


# ---------------------------------------------------------------- relatorios
def relatar_compatibilidade(compat: dict) -> None:
    sub("compatibilidade adsorvente x adsorbato (pH vs PZC)")
    print("    veredito.............: %s" % compat.get("veredito"))
    print("    classe do contaminante: %s" % compat.get("classe_contaminante"))
    print("    PZC..................: %s" % _valor(compat.get("pzc"), "pH"))
    print("    pH de operacao.......: %s" % _valor(compat.get("pH")))
    if compat.get("carga_superficie"):
        print("    carga da superficie..: %s (margem pH-PZC = %s)"
              % (compat["carga_superficie"], compat.get("margem_pH_PZC")))
    if compat.get("faltando"):
        print("    faltando.............: %s" % _lista(compat["faltando"]))
    for motivo in compat.get("motivos") or []:
        print("    motivo...............: %s" % motivo)


def relatar_simuladores(simuladores) -> None:
    sub("simuladores (descritores alimentados)")
    if not simuladores:
        print("    nenhum simulador foi solicitado")
        return
    for item in simuladores:
        print("    - %-15s estado=%-24s executado=%s"
              % (item.get("simulador"), item.get("estado"),
                 item.get("executado")))
        if item.get("faltando"):
            print("        faltando: %s" % _lista(item["faltando"]))
        if item.get("erro"):
            print("        erro....: %s" % item["erro"])
        for descritor in item.get("descritores") or []:
            print("        -> %s = %s (%s, estado %s)"
                  % (descritor.get("codigo"),
                     _valor(descritor.get("valor"), descritor.get("unidade")),
                     descritor.get("fonte") or "sem fonte",
                     descritor.get("estado")))
        for aviso in item.get("avisos") or []:
            print("        aviso...: %s" % aviso)


def relatar_descritores(descritores) -> None:
    sub("descritores preenchidos na matriz")
    if not descritores:
        print("    nenhum descritor foi gravado")
        return
    for item in descritores:
        print("    %-3s %-42s = %s  [%s]"
              % (item.get("codigo"),
                 (item.get("nome") or item.get("valor_texto") or "")[:42],
                 _valor(item.get("valor"), item.get("unidade")),
                 item.get("estado")))
        if item.get("fonte"):
            print("        fonte: %s" % item["fonte"])


def relatar_modelos(modelos) -> None:
    sub("modelos de adsorcao solicitados")
    if not modelos:
        print("    nenhum modelo foi solicitado")
        return
    for item in modelos:
        print("    - %-12s estado=%s" % (item.get("modelo"),
                                         item.get("estado")))
        if item.get("faltando"):
            print("        faltando: %s" % _lista(item["faltando"]))
        parametros = item.get("parametros") or {}
        if parametros:
            print("        parametros: %s"
                  % ", ".join("%s=%s" % (chave, _valor(valor))
                              for chave, valor in parametros.items()))
        if item.get("erro"):
            print("        erro....: %s" % item["erro"])
        if item.get("qe") is not None:
            print("        qe......: %s mg/g" % _valor(item["qe"]))
        if item.get("natureza"):
            print("        natureza: %s" % item["natureza"])


def relatar_lacunas(lacunas) -> None:
    sub("lacunas experimentais")
    if not lacunas:
        print("    nenhuma lacuna critica registrada")
        return
    for item in lacunas:
        print("    - %-3s %-42s estado_atual=%s"
              % (item.get("codigo"), (item.get("nome") or "")[:42],
                 item.get("estado_atual")))
        print("        fecha com: %s" % _lista(item.get("entradas_que_fecham")))
        print("        fonte....: %s" % item.get("fonte_possivel"))


def relatar_preenchimento(preenchimento: dict) -> None:
    sub("cobertura da matriz 7Dx4")
    print("    com dado...: %d de %d descritores (%.2f%%)"
          % (preenchimento.get("com_dado", 0),
             preenchimento.get("total_avaliado", 0),
             preenchimento.get("percentual_com_dado", 0.0)))
    for estado, quantidade in (preenchimento.get("por_estado") or {}).items():
        print("    %-10s: %d" % (estado, quantidade))
    for dimensao, dados in (preenchimento.get("por_dimensao") or {}).items():
        print("    %s: %d/%d (%.2f%%)" % (dimensao, dados.get("preenchidos"),
                                          dados.get("total"),
                                          dados.get("percentual")))


# --------------------------------------------------------------- verificacao
def verificar(material: dict, validacao: dict) -> list:
    """Confere o comportamento esperado do fluxo; devolve (status, texto)."""
    checagens = []
    descritores = {item.get("codigo"): item
                   for item in validacao.get("descritores") or []}

    area = material["area_superficial"]
    s3 = descritores.get("S3") or {}
    valor_s3 = s3.get("valor")
    if valor_s3 is not None and abs(float(valor_s3) - area) < 1e-6:
        checagens.append(("OK", "S3 = %s (area declarada %s m2/g)"
                          % (_valor(valor_s3), _valor(area))))
    else:
        checagens.append(("ATENCAO", "S3 = %s, esperado %s m2/g"
                          % (_valor(valor_s3), _valor(area))))

    modelos = {item.get("modelo"): item
               for item in validacao.get("modelos") or []}
    for nome in MODELOS:
        modelo = modelos.get(nome) or {}
        estado = modelo.get("estado")
        if estado == "bloqueado_por_parametros":
            checagens.append(("OK", "%s bloqueado_por_parametros (faltando: %s)"
                              % (nome, _lista(modelo.get("faltando")))))
        elif estado in ("calculado", "ok"):
            checagens.append(("ATENCAO", "%s calculado (qe=%s mg/g); confira a "
                                         "origem dos parametros"
                              % (nome, _valor(modelo.get("qe")))))
        elif estado:
            checagens.append(("ATENCAO", "%s terminou em '%s'" % (nome, estado)))

    compat = validacao.get("compatibilidade") or {}
    pzc = compat.get("pzc")
    if pzc is None and compat.get("veredito") == "indeterminado":
        checagens.append(("OK", "compatibilidade indeterminada com PZC ausente "
                                "(faltando: %s)" % _lista(compat.get("faltando"))))
    elif pzc is not None and compat.get("veredito") in ("favoravel",
                                                        "desfavoravel"):
        checagens.append(("OK", "compatibilidade %s com PZC=%s e pH=%s"
                          % (compat.get("veredito"), _valor(pzc),
                             _valor(compat.get("pH")))))
    else:
        checagens.append(("ATENCAO", "compatibilidade '%s' com PZC=%s"
                          % (compat.get("veredito"), _valor(pzc))))

    nao_mapeadas = (validacao.get("caracterizacao") or {}).get("nao_mapeadas") or []
    if nao_mapeadas:
        checagens.append(("ATENCAO", "propriedade sem descritor oficial: %s"
                          % _lista(nao_mapeadas)))

    propriedades = {str(item.get("nome") or "").strip().lower()
                    for item in material.get("propriedades") or []}
    if "qmax" in propriedades and "D1" not in descritores:
        checagens.append(("ATENCAO", "qmax foi cadastrado como propriedade do "
                                     "material (POST /materials); o modelo le o "
                                     "descritor D1, que so' e' preenchido por "
                                     "'caracterizacao'/'propriedades' no POST "
                                     "/adsorbent"))
    return checagens


def imprimir_verificacoes(checagens) -> None:
    sub("verificacoes automaticas")
    for status, texto in checagens:
        print("    [%-7s] %s" % (status, texto))


# ---------------------------------------------------------------- comparacao
def resumir(rotulo: str, material: dict, cadastro: dict,
            validacao: dict) -> dict:
    """Recorta do resultado o que entra na comparacao final dos materiais."""
    descritores = {item.get("codigo"): item
                   for item in validacao.get("descritores") or []}
    return {
        "rotulo": rotulo,
        "nome": material["nome"],
        "material_id": (validacao.get("material") or {}).get("id"),
        "cadastro": {"criado": cadastro.get("criado"),
                     "propriedades": cadastro.get("propriedades")},
        "compatibilidade": validacao.get("compatibilidade"),
        "simuladores": [{"simulador": item.get("simulador"),
                         "estado": item.get("estado"),
                         "executado": item.get("executado"),
                         "faltando": item.get("faltando"),
                         "erro": item.get("erro")}
                        for item in validacao.get("simuladores") or []],
        "descritores": {codigo: {"valor": item.get("valor"),
                                 "unidade": item.get("unidade"),
                                 "estado": item.get("estado")}
                        for codigo, item in descritores.items()},
        "modelos": {item.get("modelo"): item.get("estado")
                    for item in validacao.get("modelos") or []},
        "lacunas": [item.get("codigo")
                    for item in validacao.get("lacunas_experimentais") or []],
        "cobertura": validacao.get("preenchimento") or {},
    }


def comparar(resumos) -> None:
    """Compara a cobertura 7Dx4 dos materiais testados, dimensao por dimensao."""
    titulo("RESUMO COMPARATIVO - cobertura da matriz 7Dx4")
    for resumo in resumos:
        cobertura = resumo["cobertura"]
        print("  Material %s (%s): %d de %d descritores com dado (%.2f%%)"
              % (resumo["rotulo"], resumo["nome"],
                 cobertura.get("com_dado", 0),
                 cobertura.get("total_avaliado", 0),
                 cobertura.get("percentual_com_dado", 0.0)))

    dimensoes = []
    for resumo in resumos:
        for codigo in (resumo["cobertura"].get("por_dimensao") or {}):
            if codigo not in dimensoes:
                dimensoes.append(codigo)

    rotulos = [resumo["rotulo"] for resumo in resumos]
    print("\n  %-4s %s" % ("dim", "  ".join("%-14s" % r for r in rotulos)))
    for codigo in dimensoes:
        celulas = []
        for resumo in resumos:
            dados = (resumo["cobertura"].get("por_dimensao")
                     or {}).get(codigo) or {}
            celulas.append("%-14s" % ("%d/%d (%.0f%%)"
                                      % (dados.get("preenchidos", 0),
                                         dados.get("total", 0),
                                         dados.get("percentual", 0.0))))
        print("  %-4s %s" % (codigo, "  ".join(celulas)))

    if len(resumos) != 2:
        return
    a, b = resumos
    codigos = list(a["descritores"])
    codigos += [c for c in b["descritores"] if c not in codigos]

    print("\n  descritores com valor (A = %s | B = %s):" % (a["nome"], b["nome"]))
    for codigo in codigos:
        valores = []
        for resumo in (a, b):
            item = resumo["descritores"].get(codigo) or {}
            valores.append("%-18s" % _valor(item.get("valor"),
                                            item.get("unidade")))
        print("    %-3s %s %s" % (codigo, valores[0], valores[1]))

    lacunas_a = set(a.get("lacunas") or [])
    lacunas_b = set(b.get("lacunas") or [])
    print("\n  lacunas em comum.: %s" % _lista(sorted(lacunas_a & lacunas_b)))
    print("  lacunas so' em A.: %s" % _lista(sorted(lacunas_a - lacunas_b)))
    print("  lacunas so' em B.: %s" % _lista(sorted(lacunas_b - lacunas_a)))

    print("\n  modelos: A=%s | B=%s"
          % (", ".join("%s:%s" % (k, v) for k, v in a["modelos"].items()),
             ", ".join("%s:%s" % (k, v) for k, v in b["modelos"].items())))
    print("  compatibilidade: A=%s | B=%s"
          % ((a["compatibilidade"] or {}).get("veredito"),
             (b["compatibilidade"] or {}).get("veredito")))

    cobertura_a = a["cobertura"].get("com_dado", 0)
    cobertura_b = b["cobertura"].get("com_dado", 0)
    print("\n  VEREDITO DA COMPARACAO:")
    if cobertura_a == cobertura_b:
        print("    empate em cobertura (%d x %d descritores com dado)."
              % (cobertura_a, cobertura_b))
        print("    A escolha entre %s e %s depende de D1/D2 (capacidade e "
              "afinidade)," % (a["nome"], b["nome"]))
        print("    que exigem ensaio de isoterma (qmax com KL ajustado); sem "
              "isso, nenhum dos dois")
        print("    pode ser declarado melhor com base em dado.")
    else:
        melhor, pior = ((a, b) if cobertura_a > cobertura_b else (b, a))
        print("    %s teve a maior cobertura: %d x %d descritores com dado."
              % (melhor["nome"], max(cobertura_a, cobertura_b),
                 min(cobertura_a, cobertura_b)))
        print("    %s ficou atras em %d descritor(es); consulte as lacunas "
              "acima." % (pior["nome"],
                          abs(cobertura_a - cobertura_b)))


# ------------------------------------------------------------------- limpeza
def limpar(cliente: Cliente, pesquisa_id: str, materiais) -> None:
    """Remove a pesquisa e os materiais criados por esta execucao."""
    sub("limpeza (--limpar)")
    for material_id in materiais:
        try:
            cliente.delete("/api/materials/%s" % material_id)
            print("    material %s removido" % material_id)
        except FalhaAPI as erro:
            print("    material %s NAO removido: %s" % (material_id, erro))
    try:
        cliente.delete("/api/research/%s" % pesquisa_id)
        print("    pesquisa %s removida" % pesquisa_id)
    except FalhaAPI as erro:
        print("    pesquisa %s NAO removida: %s" % (pesquisa_id, erro))


# ---------------------------------------------------------------------- main
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Fluxo completo de teste do adsorvente SMX na API local.")
    parser.add_argument("--base-url", default=BASE_PADRAO,
                        help="endereco da API (padrao: %s)" % BASE_PADRAO)
    parser.add_argument("--limpar", action="store_true",
                        help="apaga a pesquisa e os materiais ao terminar")
    parser.add_argument("--json", dest="arquivo", default=None,
                        help="grava o resultado completo em arquivo JSON")
    args = parser.parse_args(argv)

    # Console legado do Windows (cp850/cp1252) nao aceita acento: translitera a
    # saida em vez de derrubar o teste. Em UTF-8 nada muda.
    if "utf" not in (sys.stdout.encoding or "").lower():
        sys.stdout = FluxoAscii(sys.stdout)
        sys.stderr = FluxoAscii(sys.stderr)

    cliente = Cliente(args.base_url)
    pesquisa_id = None
    materiais = []
    resumos = []
    try:
        titulo("0. ESTADO DO SERVICO - %s" % cliente.base)
        saude = cliente.get("/api/health")
        banco = saude.get("banco") or {}
        matriz = saude.get("matriz") or {}
        print("  estado=%s | servico=%s v%s | banco=%s"
              % (saude.get("estado"), saude.get("servico"),
                 saude.get("versao"), banco.get("motor")))
        print("  matriz=%s dimensoes x %s descritores"
              % (matriz.get("dimensoes"), matriz.get("descritores")))
        motores = saude.get("motores") or {}
        if motores:
            print("  motores do nucleo: %s"
                  % json.dumps(motores, ensure_ascii=False)[:400])

        titulo("1. CRIAR PESQUISA - POST /api/research")
        pesquisa = criar_pesquisa(cliente)
        pesquisa_id = pesquisa["id"]
        print("  pesquisa_id = %s" % pesquisa_id)
        print("  pergunta....: %s" % pesquisa.get("pergunta"))
        print("  contaminante: %s" % pesquisa.get("contaminante"))
        print("  aplicacao...: %s | condicoes: %s"
              % (pesquisa.get("aplicacao"),
                 json.dumps(pesquisa.get("condicoes"), ensure_ascii=False)))

        for numero, material in enumerate(MATERIAIS, start=2):
            titulo("%d. MATERIAL %s - %s" % (numero, material["rotulo"],
                                             material["nome"]))
            cadastro = cadastrar_material(cliente, pesquisa_id, material)
            material_id = cadastro["material"]["id"]
            materiais.append(material_id)
            print("  POST /api/research/%s/materials -> material_id = %s"
                  % (pesquisa_id, material_id))
            print("  criado=%s | propriedades gravadas=%s"
                  % (cadastro.get("criado"), cadastro.get("propriedades")))

            inicio = time.perf_counter()
            validacao = validar_material(cliente, pesquisa_id, material,
                                         material_id)
            duracao = time.perf_counter() - inicio
            print("  POST /api/research/%s/adsorbent -> %.2f s"
                  % (pesquisa_id, duracao))

            relatar_compatibilidade(validacao.get("compatibilidade") or {})
            relatar_simuladores(validacao.get("simuladores"))
            relatar_descritores(validacao.get("descritores"))
            relatar_modelos(validacao.get("modelos"))
            relatar_lacunas(validacao.get("lacunas_experimentais"))
            relatar_preenchimento(validacao.get("preenchimento") or {})
            imprimir_verificacoes(verificar(material, validacao))
            resumos.append(resumir(material["rotulo"], material, cadastro,
                                   validacao))

        if len(resumos) > 1:
            comparar(resumos)

        if args.arquivo:
            with open(args.arquivo, "w", encoding="utf-8") as arquivo:
                json.dump({"base_url": cliente.base,
                           "pesquisa_id": pesquisa_id,
                           "materiais": resumos}, arquivo, indent=2,
                          ensure_ascii=False, default=str)
            print("\n  resultado completo gravado em %s" % args.arquivo)

        if not args.limpar:
            print("\n  pesquisa %s mantida no banco (use --limpar para "
                  "remover)." % pesquisa_id)
    except FalhaAPI as erro:
        print("\n[FALHA] %s" % erro)
        return 1
    finally:
        if args.limpar and pesquisa_id:
            limpar(cliente, pesquisa_id, materiais)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


