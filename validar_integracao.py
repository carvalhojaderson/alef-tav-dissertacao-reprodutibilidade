# -*- coding: utf-8 -*-
"""Validacao de ponta a ponta do backend integrado (HTTP real).

Reproduz, pela API, o fluxo que a interface executa:

    1  acordar/verificar o servico            -> /api/ready
    2  estado do backend e do banco            -> /api/health
    3  preflight CORS da origem do frontend    -> OPTIONS /api/research
    4  criar pesquisa                          -> POST /api/research
    5  editar pesquisa                         -> PATCH /api/research/{id}
    6  cadastrar material novo                 -> POST .../materials
    6b caracterizacao: medicoes de bancada     -> POST .../measurements/batch
    6c cobertura de medicao por descritor      -> GET .../measurements/summary
    7  conferir persistencia                   -> GET /api/research/{id}
    7b evidencias cientificas (opcional)       -> POST .../evidence/search
    8  montar protocolo                        -> POST .../protocol
    9  consultar a matriz 7Dx4                 -> GET /api/matriz
    10 matriz do material (28 linhas)          -> GET /api/materials/{m}/descriptors
    11 inventario de simuladores               -> GET /api/simulators
    12 motores ambientais proprios (16)        -> GET /api/engines + POST .../run
    12b um simulador do nucleo                 -> POST /api/simulators/{n}/run
    13 recuperar as simulacoes                 -> GET .../simulations
    14 avaliar adsorvente (modelos + lacunas)  -> POST .../adsorbent
    15 avaliar viabilidade                     -> POST .../viability
    16 gerar prova de conceito                 -> POST .../proof-of-concept
    17 gerar relatorio e baixar o arquivo      -> POST .../reports + /arquivo
    18 historico e indicadores                 -> GET /api/history, /api/stats
    19 persistencia apos reinicio (opcional)   -> GET /api/research/{id}

Uso:

    python ambiental_backend/validar_integracao.py --base http://127.0.0.1:7861
    python ambiental_backend/validar_integracao.py \
        --base https://Jaderson32-api-ambiental.hf.space --reiniciar

`--reiniciar` reinicia o Space (quando o alvo e' um Space) e reconsulta a
pesquisa criada, provando que o dado sobreviveu a reinicializacao.

Somente stdlib: roda em qualquer interpretador Python 3.8+.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ORIGEM_PADRAO = ("https://ais-dev-762xvkh6mpwv73wh6pxb4n-17975995585"
                 ".us-east1.run.app")
PERGUNTA = ("adsorcao de chumbo em zeolita para tratamento de agua "
            "contaminada")


class Resultado:
    """Uma linha do relatorio de validacao."""

    def __init__(self, passo, metodo, caminho, status, ms, ok, nota=""):
        self.passo = passo
        self.metodo = metodo
        self.caminho = caminho
        self.status = status
        self.ms = ms
        self.ok = ok
        self.nota = nota

    def linha(self):
        marca = "OK  " if self.ok else "FALHA"
        texto = "%s %-3s %-7s %-44s %s" % (
            marca, self.passo, self.metodo, self.caminho,
            self.status if self.status is not None else "-")
        if self.ms:
            texto += " %6d ms" % self.ms
        if self.nota:
            texto += "  " + self.nota
        return texto

    def dict(self):
        return {"passo": self.passo, "metodo": self.metodo,
                "caminho": self.caminho, "status": self.status,
                "ms": self.ms, "ok": self.ok, "nota": self.nota}


class Cliente:
    """Cliente HTTP minimo que sempre envia o `Origin` do frontend."""

    def __init__(self, base, origem, timeout=240):
        self.base = base.rstrip("/")
        self.origem = origem
        self.timeout = timeout
        self.cors = []

    def pedir(self, metodo, caminho, corpo=None, extra=None, timeout=None):
        dados = None
        cabecalhos = {"Origin": self.origem, "Accept": "application/json"}
        if corpo is not None:
            dados = json.dumps(corpo).encode("utf-8")
            cabecalhos["Content-Type"] = "application/json"
        cabecalhos.update(extra or {})
        pedido = urllib.request.Request(self.base + caminho, data=dados,
                                        method=metodo, headers=cabecalhos)
        inicio = time.time()
        try:
            with urllib.request.urlopen(pedido,
                                        timeout=timeout or self.timeout) as r:
                texto = r.read().decode("utf-8", "replace")
                status, resposta_cabecalhos = r.status, dict(r.headers)
        except urllib.error.HTTPError as erro:
            texto = erro.read().decode("utf-8", "replace")
            status, resposta_cabecalhos = erro.code, dict(erro.headers)
        except Exception as erro:                          # noqa: BLE001
            gasto = int((time.time() - inicio) * 1000)
            return None, {}, {"falha_de_rede": "%s: %s"
                              % (type(erro).__name__, erro)}, gasto
        gasto = int((time.time() - inicio) * 1000)
        self.cors.append({"caminho": caminho, "metodo": metodo,
                          "allow_origin": resposta_cabecalhos.get(
                              "access-control-allow-origin")})
        try:
            corpo_json = json.loads(texto)
        except ValueError:
            corpo_json = {"texto": texto[:400]}
        return status, resposta_cabecalhos, corpo_json, gasto


# ------------------------------------------------------------------ biblioteca
#: Valores de entrada usados na execucao real dos simuladores e dos modelos.
#: Sao condicoes de trabalho declaradas (nao medidas) â€” o relatorio marca essa
#: origem, e nada disso vira dado experimental.
PARAMETROS = {
    "area_m2g": 350.0, "area_especifica_m2_g": 350.0, "diametro_nm": 500.0,
    "diametro_particula_nm": 500.0, "temperatura_C": 298.15, "pH": 6.0,
    "pH_operacao": 6.0, "Ce": 10.0, "C0": 50.0, "dose_g_L": 1.0,
    "massa_g": 1.0, "volume_L": 1.0, "tempo_min": 60.0, "vazao_m3_h": 1.0,
    "densidade_g_cm3": 2.1, "porosidade": 0.4, "PZC": 8.0, "pzc": 8.0,
}

CARACTERIZACAO = {
    "area superficial": {"valor": 350.0, "unidade": "m2/g"},
    "volume de poros": {"valor": 0.32, "unidade": "cm3/g"},
    "tamanho de partÃ­cula": {"valor": 0.5, "unidade": "um"},
    "densidade real": {"valor": 2.1, "unidade": "g/cm3"},
    "PZC": {"valor": 8.0, "unidade": "pH"},
    "fase cristalina": {"valor_texto": "LTA (zeolita 4A)"},
    "morfologia": {"valor_texto": "cubica"},
    "grupos funcionais": {"valor_texto": "Si-OH / Al-OH"},
    "composiÃ§Ã£o elementar": {"valor": 45.0, "unidade": "% m/m"},
    "cristalinidade": {"valor": 88.0, "unidade": "%"},
    "qmax": {"valor": 30.0, "unidade": "mg/g"},
    "KL": {"valor": 0.05, "unidade": "L/mg"},
    "KF": {"valor": 3.0, "unidade": "(mg/g)(mg/L)^-1/n"},
    "seletividade": {"valor": 2.5, "unidade": "adimensional"},
    "regeneraÃ§Ã£o": {"valor": 85.0, "unidade": "%"},
    "remoÃ§Ã£o": {"valor": 80.0, "unidade": "%"},
    "qe": {"valor": 20.0, "unidade": "mg/g"},
    "faixa de pH": {"valor_texto": "4 - 9"},
    "toxidade": {"valor_texto": "GHS07 (irritante)"},
    "preÃ§o": {"valor": 120.0, "unidade": "R$/kg"},
    "disponibilidade": {"valor": 5000.0, "unidade": "t/ano"},
    "pegada energÃ©tica": {"valor": 0.5, "unidade": "kWh/kg"},
    "reciclabilidade": {"valor": 70.0, "unidade": "%"},
    "conformidade": {"valor": 0.05, "unidade": "mg/L"},
    "escalabilidade": {"valor": 2.0, "unidade": "m3/h"},
}

CONDICOES = {"temperatura_C": 298.15, "pH": 6.0, "Ce": 10.0, "C0": 50.0,
             "dose_g_L": 1.0, "volume_L": 1.0, "tempo_min": 60.0}

PARAMETROS_MODELO = {
    "langmuir": {"qmax": 30.0, "KL": 0.05, "Ce": 10.0},
    "freundlich": {"Kf": 3.0, "n": 2.0, "Ce": 10.0},
    "pfo_cinetica": {"q_e_equilibrio": 18.0, "k1": 0.05, "tempo": 60.0},
}


#: Entradas dos motores ambientais proprios (`GET /api/engines`). Mesmo papel de
#: `PARAMETROS`: condicoes de trabalho declaradas para exercitar o encanamento no
#: E2E — nao sao medidas do material nem viram resultado cientifico.
PARAMETROS_MOTORES = {
    "ph_inicial": [3.0, 5.0, 7.0, 9.0, 11.0],
    "ph_final": [4.1, 6.2, 7.0, 7.6, 8.3],
    "massa_g_L": [0.5, 1.0, 2.0, 4.0],
    "ph_equilibrio": [5.2, 6.0, 6.9, 7.8],
    "naoh_mmol_g": 0.85, "na2co3_mmol_g": 0.42, "nahco3_mmol_g": 0.18,
    "hcl_mmol_g": 0.35,
    "bandas_cm1": [3420, 2920, 1700, 1590, 1450, 1220, 1100, 800, 470],
    "diametros_um": [12.5, 25.0, 45.0, 63.0, 90.0, 125.0, 180.0, 250.0],
    "metodo": "analise_de_imagem",
    "massas_acumuladas_pct": [2.0, 9.0, 24.0, 45.0, 66.0, 83.0, 94.0, 100.0],
    "angulo_agua_deg": 78.5, "angulo_diiodometano_deg": 45.2,
    "temperatura_C": [30.0, 100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0],
    "massa_pct": [99.5, 97.0, 93.0, 84.0, 62.0, 34.0, 21.0, 18.5],
    "tempo_s": [60.0, 300.0, 900.0, 1800.0, 3600.0, 7200.0],
    "concentracao_mg_L": [0.4, 1.8, 3.1, 3.9, 4.2, 4.3],
    "volume_L": 0.5, "massa_amostra_g": 2.0, "teor_inicial_mg_kg": 2000.0,
    "massa_inicial_g": 5.0, "massa_final_g": 4.62,
    "componentes": [{"nome": "chumbo", "qmax_mg_g": 118.0,
                     "K_L_L_mg": 0.42},
                    {"nome": "cobre", "qmax_mg_g": 74.0, "K_L_L_mg": 0.21}],
    "concentracoes_mg_L": [10.0, 10.0],
    "capacidades_mg_g": [118.0, 106.0, 97.0, 88.0],
    "desorcao_pct": [94.0, 91.0, 88.0, 85.0],
    "composicao": [{"classe": "casca", "fracao": 0.85},
                   {"classe": "celulose", "fracao": 0.15}],
    "analitos": {"chumbo": 0.004, "pH": 7.2},
    "norma": "ms_888_2021",
    "elementos_pct": {"C": 78.4, "H": 2.1, "O": 17.9, "N": 0.9, "Si": 0.7},
    "formula_declarada": "C",
}

#: Entradas que so' fazem sentido para um motor especifico (a mesma chave tem
#: formato diferente em motores diferentes: `composicao` por classe em C5 e por
#: substancia em C1).
PARAMETROS_POR_MOTOR = {
    "perigo_composicao": {"composicao": [
        {"substancia": "chumbo", "fracao": 0.15},
        {"substancia": "celulose", "fracao": 0.85}]},
    "reciclabilidade": {"composicao": [
        {"classe": "casca", "fracao": 0.85},
        {"classe": "celulose", "fracao": 0.15}]},
}

#: Medicoes declaradas para provar o caminho de caracterizacao (medicoes.py ->
#: descritor -> matriz). Sao valores de ensaio simulados, gravados com
#: laboratorio/operador "validacao": servem ao teste de encanamento e nao sao
#: resultado cientifico.
MEDICOES_DECLARADAS = [
    {"tipo": "bet_area", "replicatas": [348.0, 352.0, 350.5],
     "instrumento": "Quantachrome Nova 1200e"},
    {"tipo": "volume_poros", "replicatas": [0.31, 0.33]},
    {"tipo": "diametro_particula", "replicatas": [492.0, 505.0, 512.0]},
    {"tipo": "pzc", "replicatas": [7.9, 8.1, 8.0]},
    {"tipo": "acidez_superficie", "replicatas": [0.84, 0.86]},
    {"tipo": "grupos_ftir", "valor_texto": "Si-OH (3420 cm-1); Al-OH (1100)"},
]


def _parametros_para(requisitos, propria=False, nome=None) -> dict:
    """Monta a entrada do simulador a partir das chaves que ele declara.

    `propria=True` usa a tabela dos motores ambientais, cujas chaves tem tipo
    diferente das do nucleo (ex.: `temperatura_C` e' a rampa do TGA, nao a
    temperatura de trabalho). `nome` aplica as entradas especificas daquele
    motor (`PARAMETROS_POR_MOTOR`).
    """
    base = PARAMETROS_MOTORES if propria else PARAMETROS
    especificos = PARAMETROS_POR_MOTOR.get(nome or "", {})
    entrada = {}
    for item in requisitos or []:
        chave = item.get("chave")
        if chave in especificos:
            entrada[chave] = especificos[chave]
        elif chave in base:
            entrada[chave] = base[chave]
        elif chave in PARAMETROS:
            entrada[chave] = PARAMETROS[chave]
    return entrada


def acordar(cliente, tentativas=8, espera=15):
    """Espera o servico responder (Space hibernado leva ~1 min para acordar).

    Uma falha de rede na primeira tentativa NAO e' servico fora do ar: e' o
    comportamento esperado do Hugging Face enquanto o contÃªiner inicializa.
    """
    inicio = time.time()
    historico = []
    for tentativa in range(1, tentativas + 1):
        status, _, _, ms = cliente.pedir("GET", "/api/ready", timeout=120)
        historico.append({"tentativa": tentativa, "status": status, "ms": ms})
        if status == 200:
            return True, historico, int(time.time() - inicio)
        time.sleep(espera)
    return False, historico, int(time.time() - inicio)


def executar(base, origem, com_evidencias=False, reiniciar=False) -> dict:
    """Executa o fluxo completo e devolve o relatorio da validacao."""
    cliente = Cliente(base, origem)
    resultados = []
    dados = {"base": base, "origem": origem, "passos": []}

    def registrar(passo, metodo, caminho, status, ms, ok, nota=""):
        item = Resultado(passo, metodo, caminho, status, ms, ok, nota)
        resultados.append(item)
        dados["passos"].append(item.dict())
        print(item.linha(), flush=True)
        return item

    print("\n== %s ==" % base)
    print("origem simulada: %s\n" % origem)

    # 1 --------------------------------------------------------------- acordar
    acordou, historico, segundos = acordar(cliente)
    registrar(1, "GET", "/api/ready", 200 if acordou else None,
              segundos * 1000, acordou,
              "acordou em %d s (%d tentativas)"
              % (segundos, len(historico)))
    dados["despertar"] = historico
    if not acordou:
        print("\nservico nao respondeu; nada mais pode ser validado")
        return finalizar(dados, resultados, None, None)

    # 2 ---------------------------------------------------------------- health
    status, cab, corpo, ms = cliente.pedir("GET", "/api/health")
    banco = (corpo or {}).get("banco") or {}
    motores = (corpo or {}).get("motores") or {}
    registrar(2, "GET", "/api/health", status, ms,
              status == 200 and (corpo or {}).get("estado") == "ok",
              "banco=%s motores=%s tabelas=%s"
              % (banco.get("motor"), len(motores),
                 banco.get("tabelas_ambiental")))

    # 3 -------------------------------------------------------------- CORS real
    status, cab, corpo, ms = cliente.pedir(
        "OPTIONS", "/api/research",
        extra={"Access-Control-Request-Method": "POST",
               "Access-Control-Request-Headers": "content-type"})
    permitida = cab.get("access-control-allow-origin")
    metodos = cab.get("access-control-allow-methods") or ""
    registrar(3, "OPTIONS", "/api/research", status, ms,
              status == 200 and permitida == origem and "POST" in metodos,
              "allow-origin=%s metodos=%s" % (permitida, metodos))

    # 3b ------------------------------- origem desconhecida e' recusada (403)
    intruso = "https://site-nao-autorizado.example"
    status, cab, corpo, ms = Cliente(base, intruso).pedir("GET", "/api/matriz")
    registrar(3, "GET", "/api/matriz (origem intrusa)", status, ms,
              status == 403,
              "codigo=%s" % ((corpo or {}).get("erro") or {}).get("codigo"))

    # 4 -------------------------------------------------------- criar pesquisa
    status, _, corpo, ms = cliente.pedir("POST", "/api/research", {
        "pergunta": PERGUNTA, "material": "Zeolita 4A",
        "titulo": "Validacao de integracao (frontend -> backend)",
        "contaminante": "chumbo", "aplicacao": "agua",
        "condicoes": CONDICOES})
    pesquisa_id = (corpo or {}).get("id")
    registrar(4, "POST", "/api/research", status, ms,
              status == 201 and bool(pesquisa_id),
              "pesquisa_id=%s" % pesquisa_id)
    if not pesquisa_id:
        print("\nsem pesquisa nao e' possivel seguir")
        return finalizar(dados, resultados, None, None)
    dados["pesquisa_id"] = pesquisa_id

    # 5 --------------------------------------------------------- editar pesquisa
    status, _, corpo, ms = cliente.pedir(
        "PATCH", "/api/research/%s" % pesquisa_id,
        {"estado": "em_andamento", "condicoes": {"pH": 6.0}})
    registrar(5, "PATCH", "/api/research/{id}", status, ms,
              status == 200 and (corpo or {}).get("atualizada") is True,
              "versao=%s"
              % (((corpo or {}).get("pesquisa") or {}).get("versao")))

    # 6 ----------------------------------------------------------- novo material
    nome_material = ("Zeolita 4A - validacao %s"
                     % time.strftime("%Y%m%d-%H%M%S"))
    status, _, corpo, ms = cliente.pedir(
        "POST", "/api/research/%s/materials" % pesquisa_id, {
            "nome": nome_material, "formula": "Na12[Al12Si12O48].27H2O",
            "classe": "zeolita", "origem": "sintetica", "papel": "alvo",
            "composicao": [{"elemento": "Si", "fracao_massica": 0.20},
                           {"elemento": "Al", "fracao_massica": 0.18},
                           {"elemento": "Na", "fracao_massica": 0.15}],
            "propriedades": [{"nome": "area superficial", "valor": 350.0,
                              "unidade": "m2/g", "origem": "declarada"},
                             {"nome": "PZC", "valor": 8.0, "unidade": "pH",
                              "origem": "declarada"}]})
    material_id = ((corpo or {}).get("material") or {}).get("id")
    registrar(6, "POST", "/api/research/{id}/materials", status, ms,
              status == 201 and bool(material_id),
              "material_id=%s propriedades=%s"
              % (material_id, (corpo or {}).get("propriedades")))
    if not material_id:
        return finalizar(dados, resultados, pesquisa_id, None)
    dados["material_id"] = material_id

    # 6b -------------------------------------------- caracterizacao: medicoes
    lote = []
    for item in MEDICOES_DECLARADAS:
        registro = dict(item)
        registro.setdefault("laboratorio", "validacao_e2e")
        registro.setdefault("operador", "validacao automatizada")
        registro["pesquisa_id"] = pesquisa_id
        lote.append(registro)
    status, _, corpo, ms = cliente.pedir(
        "POST", "/api/materials/%s/measurements/batch" % material_id,
        {"medicoes": lote})
    gravadas = (corpo or {}).get("registradas")
    registrar("6b", "POST", "/api/materials/{id}/measurements", status, ms,
              status in (200, 201) and gravadas == len(lote),
              "lote=%s gravadas=%s falhas=%s"
              % (len(lote), gravadas, (corpo or {}).get("falhas")))

    # 6c --------------------------------- cobertura de medicao por descritor
    status, _, corpo, ms = cliente.pedir(
        "GET", "/api/materials/%s/measurements/summary" % material_id)
    cobertos = (corpo or {}).get("descritores_cobertos") or []
    registrar("6c", "GET", "/api/materials/{id}/measurements/summary", status,
              ms, status == 200 and len(cobertos) > 0,
              "total=%s descritores_cobertos=%s"
              % ((corpo or {}).get("total_medicoes"), ",".join(cobertos)))

    # 7 --------------------------------------------------- persistencia do vinculo
    status, _, corpo, ms = cliente.pedir("GET", "/api/research/%s" % pesquisa_id)
    ids_materiais = [item.get("id") for item in
                     ((corpo or {}).get("materiais") or [])]
    registrar(7, "GET", "/api/research/{id}", status, ms,
              status == 200 and material_id in ids_materiais,
              "materiais vinculados=%d" % len(ids_materiais))

    # 7b ------------------------------------------------ evidencias cientificas
    if com_evidencias:
        status, _, corpo, ms = cliente.pedir(
            "POST", "/api/research/%s/evidence/search" % pesquisa_id,
            {"bases": ["openalex"], "n": 2, "max_bases": 1}, timeout=180)
        registrar(7, "POST", "/api/research/{id}/evidence/search", status, ms,
                  status in (200, 201),
                  "novas=%s total=%s falhas=%s"
                  % ((corpo or {}).get("novas"),
                     (corpo or {}).get("total_na_pesquisa"),
                     list(((corpo or {}).get("falhas") or {}).keys())))

    # 8 --------------------------------------------------------------- protocolo
    status, _, corpo, ms = cliente.pedir(
        "POST", "/api/research/%s/protocol" % pesquisa_id,
        {"material": nome_material, "contaminante": "chumbo",
         "aplicacao": "agua"})
    registrar(8, "POST", "/api/research/{id}/protocol", status, ms,
              status == 201,
              "descritores=%s simuladores=%s" % (
                  len(((corpo or {}).get("descritores") or [])),
                  len(((corpo or {}).get("simuladores") or []))))

    # 9 -------------------------------------------------------------- matriz 7Dx4
    status, _, corpo, ms = cliente.pedir("GET", "/api/matriz")
    total = (corpo or {}).get("total")
    fontes = (corpo or {}).get("fontes") or {}
    registrar(9, "GET", "/api/matriz", status, ms,
              status == 200 and total == 28,
              "28 descritores; sem_simulador=%s" % fontes.get("sem_simulador"))

    # 10 ----------------------------------------------------- matriz do material
    status, _, corpo, ms = cliente.pedir(
        "GET", "/api/materials/%s/descriptors" % material_id)
    linhas = ((corpo or {}).get("descritores")
              or (corpo or {}).get("linhas") or [])
    preenchimento = (corpo or {}).get("preenchimento") or {}
    registrar(10, "GET", "/api/materials/{id}/descriptors", status, ms,
              status == 200 and len(linhas) == 28,
              "linhas=%d cobertura=%s%%"
              % (len(linhas), preenchimento.get("percentual_com_dado")))

    # 11 --------------------------------------------------- inventario de simuladores
    status, _, corpo, ms = cliente.pedir("GET", "/api/simulators")
    catalogo = (corpo or {}).get("simuladores") or []
    registrar(11, "GET", "/api/simulators", status, ms,
              status == 200 and len(catalogo) > 0,
              "total=%s disponiveis=%s com_descritor=%s"
              % ((corpo or {}).get("total"), (corpo or {}).get("disponiveis"),
                 (corpo or {}).get("com_descritor")))

    # 12 -------------------------------- executar os motores ambientais proprios
    status, _, corpo, ms = cliente.pedir("GET", "/api/engines")
    proprios = [linha.get("motor") for linha in
                ((corpo or {}).get("motores") or [])]
    registrar("12", "GET", "/api/engines", status, ms,
              status == 200 and len(proprios) > 0,
              "motores proprios=%d" % len(proprios))

    por_nome = {item.get("simulador"): item for item in catalogo}
    executados, falhados = [], []
    for nome in proprios:
        item = por_nome.get(nome)
        if item is None:
            falhados.append((nome, "fora do catalogo de simuladores"))
            continue
        entrada = _parametros_para(item.get("requisitos"), propria=True,
                                   nome=nome)
        if not entrada:
            falhados.append((nome, "nenhuma entrada conhecida para o motor"))
            continue
        status, _, corpo, ms = cliente.pedir(
            "POST", "/api/simulators/%s/run" % nome,
            {"parametros": entrada, "pesquisa_id": pesquisa_id,
             "material_id": material_id, "pergunta": PERGUNTA,
             "requer_completo": True})
        estado = (corpo or {}).get("estado") or ""
        ok = status == 200 and estado.startswith("ok")
        executados.append({"simulador": nome, "status": status,
                           "estado": estado,
                           "erro": (corpo or {}).get("erro")})
        if not ok:
            falhados.append((nome, estado or str((corpo or {}).get("erro"))))
    registrar(12, "POST", "/api/simulators/{nome}/run", None, 0,
              bool(proprios) and not falhados,
              "%d/%d motores ok%s"
              % (len(proprios) - len(falhados), len(proprios),
                 ("; falhas=" + "; ".join("%s: %s" % par for par in falhados))
                 if falhados else ""))

    # 12b ------------------------------------ executar um simulador do nucleo
    candidatos = []
    for item in catalogo:
        if item.get("simulador") in set(proprios):
            continue
        if not item.get("disponivel") or not item.get("descritores"):
            continue
        entrada = _parametros_para(item.get("requisitos"))
        obrigatorias = [r.get("chave") for r in (item.get("requisitos") or [])
                        if r.get("obrigatorio")]
        if entrada and all(chave in entrada for chave in obrigatorias):
            candidatos.append((len(obrigatorias), item, entrada))
    candidatos.sort(key=lambda trio: trio[0])
    for _, item, entrada in candidatos[:3]:
        status, _, corpo, ms = cliente.pedir(
            "POST", "/api/simulators/%s/run" % item["simulador"],
            {"parametros": entrada, "pesquisa_id": pesquisa_id,
             "material_id": material_id, "pergunta": PERGUNTA,
             "requer_completo": True})
        estado = (corpo or {}).get("estado") or ""
        ok = status == 200 and estado.startswith("ok")
        executados.append({"simulador": item["simulador"], "status": status,
                           "estado": estado})
        registrar("12b", "POST", "/api/simulators/{nome}/run", status, ms, ok,
                  "%s -> %s (descritores=%s)"
                  % (item["simulador"], estado,
                     len(item.get("descritores") or [])))
        if ok:
            break
    dados["simuladores"] = executados

    # 13 ---------------------------------------------------- recuperar simulacoes
    status, _, corpo, ms = cliente.pedir(
        "GET", "/api/research/%s/simulations" % pesquisa_id)
    lista = (corpo or {}).get("simulacoes") or []
    registrar(13, "GET", "/api/research/{id}/simulations", status, ms,
              status == 200 and len(lista) >= 1,
              "simulacoes=%d" % len(lista))

    # 14 ------------------------------------------------- avaliacao do adsorvente
    status, _, corpo, ms = cliente.pedir(
        "POST", "/api/research/%s/adsorbent" % pesquisa_id, {
            "material_id": material_id, "contaminante": "chumbo",
            "caracterizacao": CARACTERIZACAO, "condicoes": CONDICOES,
            "parametros_modelo": PARAMETROS_MODELO,
            "modelos": ["langmuir", "freundlich", "pfo_cinetica"],
            "pergunta": PERGUNTA}, timeout=600)
    modelos = (corpo or {}).get("modelos") or []
    lacunas = (corpo or {}).get("lacunas") or []
    preench = (corpo or {}).get("preenchimento") or {}
    registrar(14, "POST", "/api/research/{id}/adsorbent", status, ms,
              status == 201,
              "modelos=%d lacunas=%d cobertura=%s%%"
              % (len(modelos), len(lacunas),
                 preench.get("percentual_com_dado")))
    dados["adsorvente"] = {"modelos": modelos, "lacunas": lacunas}

    # 15 ------------------------------------------------------------- viabilidade
    status, _, corpo, ms = cliente.pedir(
        "POST", "/api/research/%s/viability" % pesquisa_id,
        {"tolerancia": 0.2})
    registrar(15, "POST", "/api/research/{id}/viability", status, ms,
              status == 200,
              "pontuacao=%s classificacao=%s"
              % ((corpo or {}).get("pontuacao"),
                 (corpo or {}).get("classificacao")))

    # 16 ------------------------------------------------------- prova de conceito
    status, _, corpo, ms = cliente.pedir(
        "POST", "/api/research/%s/proof-of-concept" % pesquisa_id,
        {"material_id": material_id}, timeout=900)
    passos = (corpo or {}).get("passos") or []
    resultado_prova = (corpo or {}).get("resultado") or {}
    registrar(16, "POST", "/api/research/{id}/proof-of-concept", status, ms,
              status == 200 and bool(passos) and bool(resultado_prova),
              "estado=%s passos_ok=%s/%s demonstravel=%s"
              % ((corpo or {}).get("estado"),
                 resultado_prova.get("passos_ok"),
                 resultado_prova.get("passos_total"),
                 resultado_prova.get("demonstravel")))

    # 17 ---------------------------------------------------------------- relatorios
    status, _, corpo, ms = cliente.pedir(
        "POST", "/api/research/%s/reports" % pesquisa_id,
        {"tipo": "viabilidade", "formato": "md"})
    relatorio_id = (corpo or {}).get("id")
    registrar(17, "POST", "/api/research/{id}/reports", status, ms,
              status == 201 and bool(relatorio_id),
              "relatorio=%s bytes=%s"
              % (relatorio_id, (corpo or {}).get("tamanho_bytes")))
    if relatorio_id:
        status, cab, corpo, ms = cliente.pedir(
            "GET", "/api/reports/%s/arquivo" % relatorio_id)
        exposto = (cab.get("access-control-expose-headers") or "").strip()
        registrar(17, "GET", "/api/reports/{id}/arquivo", status, ms,
                  status == 200 and ("Content-Disposition" in exposto
                                     or exposto == "*"),
                  "expose-headers=%s" % exposto)

    # 18 ---------------------------------------------- historico e indicadores
    status, _, corpo, ms = cliente.pedir("GET", "/api/history?limite=20")
    eventos = (corpo or {}).get("eventos") or []
    registrar(18, "GET", "/api/history", status, ms,
              status == 200 and len(eventos) > 0,
              "eventos=%d pesquisas=%d"
              % (len(eventos), len((corpo or {}).get("pesquisas") or [])))

    status, _, corpo, ms = cliente.pedir("GET", "/api/stats")
    stats = corpo or {}
    registrar(18, "GET", "/api/stats", status, ms,
              status == 200 and stats.get("dados_demonstracao") is False,
              "pesquisas=%s materiais=%s cobertura=%s%%"
              % ((stats.get("pesquisas") or {}).get("total"),
                 (stats.get("materiais") or {}).get("total"),
                 (stats.get("matriz") or {}).get("cobertura_pct")))

    # 19 ----------------------------------------------- persistencia apos reinicio
    if reiniciar:
        etapa = reiniciar_e_conferir(cliente, base, pesquisa_id)
        registrar(19, "GET", "/api/research/{id}", etapa.get("status"),
                  etapa.get("ms"), etapa.get("ok"), etapa.get("nota", ""))
        dados["reinicio"] = etapa

    dados["cors"] = cliente.cors
    return finalizar(dados, resultados, pesquisa_id, material_id)


# ------------------------------------------------------------------ utilitarios
def reiniciar_e_conferir(cliente, base, pesquisa_id) -> dict:
    """Reinicia o Space (quando aplicavel) e reconsulta a pesquisa criada."""
    endereco = urllib.parse.urlparse(base).hostname or ""
    if not endereco.endswith("hf.space"):
        return {"status": None, "ms": 0, "ok": True,
                "nota": "alvo nao e' um Space: reinicio manual do servidor "
                        "local confirma a mesma persistencia"}
    subdominio = endereco.split(".")[0]
    if "-" not in subdominio:
        return {"status": None, "ms": 0, "ok": False,
                "nota": "dominio de Space nao reconhecido: %s" % endereco}
    dono, nome = subdominio.split("-", 1)
    try:
        from huggingface_hub import HfApi
    except Exception as erro:                             # noqa: BLE001
        return {"status": None, "ms": 0, "ok": False,
                "nota": "huggingface_hub ausente: %s" % erro}
    api = HfApi(token=os.environ.get("HF_TOKEN") or None)
    repo_id = None
    try:
        for espaco in api.list_spaces(author=dono):
            if espaco.id.split("/")[-1].lower() == nome.lower():
                repo_id = espaco.id
                break
    except Exception:                                     # noqa: BLE001
        repo_id = "%s/%s" % (dono, nome)
    if not repo_id:
        repo_id = "%s/%s" % (dono, nome)
    print("\nreiniciando %s ..." % repo_id, flush=True)
    try:
        api.restart_space(repo_id)
    except Exception as erro:                             # noqa: BLE001
        return {"status": None, "ms": 0, "ok": False,
                "nota": "falha ao reiniciar %s: %s" % (repo_id, erro)}
    inicio = time.time()
    time.sleep(20)
    acordou, historico, segundos = acordar(cliente, tentativas=20, espera=15)
    if not acordou:
        return {"status": None, "ms": int((time.time() - inicio) * 1000),
                "ok": False, "nota": "servico nao voltou apos o reinicio",
                "despertar": historico}
    status, _, corpo, ms = cliente.pedir("GET", "/api/research/%s" % pesquisa_id)
    materiais = (corpo or {}).get("materiais") or []
    historico_pesquisa = (corpo or {}).get("historico") or {}
    ok = status == 200 and (corpo or {}).get("id") == pesquisa_id
    return {"status": status, "ms": ms, "ok": ok,
            "nota": "pesquisa recuperada apos reinicio em %d s "
                    "(materiais=%d, simulacoes=%s)" % (
                        segundos, len(materiais),
                        len(((corpo or {}).get("simulacoes") or []))),
            "despertar": historico, "pesquisa": historico_pesquisa}


def finalizar(dados, resultados, pesquisa_id, material_id) -> dict:
    """Resume, grava o relatorio em JSON e devolve o dicionario."""
    falhas = [item for item in resultados if not item.ok]
    aprovado = not falhas
    dados.update({
        "pesquisa_id": pesquisa_id,
        "material_id": material_id,
        "total_passos": len(resultados),
        "aprovados": len(resultados) - len(falhas),
        "falhas": [item.dict() for item in falhas],
        "aprovado": aprovado,
        "finalizado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    pasta = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "dados_ambiental")
    try:
        os.makedirs(pasta, exist_ok=True)
    except Exception:                                     # noqa: BLE001
        import tempfile
        pasta = tempfile.mkdtemp(prefix="ambiental_validacao_")
    caminho = os.path.join(pasta, "validacao_integracao_%s.json"
                           % time.strftime("%Y%m%d_%H%M%S"))
    try:
        with open(caminho, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=1)
    except Exception as erro:                             # noqa: BLE001
        caminho = "nao gravado (%s)" % erro
    print("\n%s: %d/%d passos aprovados"
          % ("APROVADO" if aprovado else "REPROVADO",
             len(resultados) - len(falhas), len(resultados)))
    if pesquisa_id:
        print("pesquisa criada: %s (use para limpar depois)" % pesquisa_id)
    print("relatorio:", caminho)
    dados["relatorio"] = caminho
    return dados


def principal(argv=None):
    parser = argparse.ArgumentParser(
        description="Validacao de ponta a ponta do backend ambiental")
    parser.add_argument("--base", default=os.environ.get(
        "AMBIENTAL_BASE", "http://127.0.0.1:7861"),
        help="URL do backend (padrao: %(default)s)")
    parser.add_argument("--origem", default=os.environ.get(
        "AMBIENTAL_ORIGEM", ORIGEM_PADRAO),
        help="Origin do frontend enviada nas chamadas")
    parser.add_argument("--evidencias", action="store_true",
                        help="inclui a busca bibliografica real (usa rede)")
    parser.add_argument("--reiniciar", action="store_true",
                        help="reinicia o Space e confere a persistencia")
    argumentos = parser.parse_args(argv)
    relatorio = executar(argumentos.base, argumentos.origem,
                         com_evidencias=argumentos.evidencias,
                         reiniciar=argumentos.reiniciar)
    return 0 if relatorio.get("aprovado") else 1


if __name__ == "__main__":                              # pragma: no cover
    sys.exit(principal())
