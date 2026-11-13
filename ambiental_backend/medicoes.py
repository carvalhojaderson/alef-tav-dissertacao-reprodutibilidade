# -*- coding: utf-8 -*-
"""Recebimento de dados experimentais (medicoes de bancada).

Este e' o modulo que faltava para o sistema aceitar dado real: sem ele, os
descritores que exigem ensaio nunca seriam preenchidos e o material ficaria
sempre incompleto.

Fluxo de cada medicao:

    1. valida o tipo (catalogo `TIPOS`), a unidade e a faixa fisica;
    2. calcula estatistica das replicatas (media, desvio, RSR, outlier Grubbs);
    3. grava a linha em `amb_medicoes` (tecnica, instrumento, incerteza,
       condicoes, laboratorio, operador, data);
    4. grava o descritor correspondente com estado de medicao (`presente`, ou
       `validado` quando ha replicatas e RSR <= 10%);
    5. registra conflito quando o valor medido difere > 10% do valor anterior.

Nenhum dado e' inventado: valor ausente, unidade errada ou faixa fora do
dominio fisico geram `DadosInvalidos` (HTTP 400) com a mensagem do problema.
"""
from __future__ import annotations

from . import analises_experimentais as ax
from . import motor_pesquisa, persistencia as db
from .persistencia import json_dumps

VERSAO = "1.0.0"

# Catalogo de tecnicas aceitas. `descritor` e' o codigo 7Dx4 que a medicao
# preenche; `faixa` e' o dominio fisico aceito (fora disso e' erro de
# digitacao/unidade, nao dado novo).
TIPOS = {
    "bet_area": {
        "nome": "Area superficial especifica (BET)", "unidade": "m2/g",
        "descritor": "S3", "faixa": [0.01, 5000.0],
        "metodo_padrao": "BET por fisissorcao de N2 (ISO 9277)",
        "replicatas_minimas": 2},
    "volume_poros": {
        "nome": "Volume total de poros (BJH/DFT)", "unidade": "cm3/g",
        "descritor": "S4", "faixa": [0.001, 5.0],
        "metodo_padrao": "BJH/DFT a partir da isoterma de N2",
        "replicatas_minimas": 1},
    "diametro_particula": {
        "nome": "Diametro medio de particula", "unidade": "nm",
        "descritor": "S5", "faixa": [0.5, 1.0e7],
        "metodo_padrao": "difracao a laser (ISO 13320) ou microscopia",
        "replicatas_minimas": 1},
    "pzc": {
        "nome": "Ponto de carga zero", "unidade": "pH",
        "descritor": "P2", "faixa": [1.0, 13.0],
        "metodo_padrao": "deriva de pH ou titulacao de massa",
        "replicatas_minimas": 1},
    "acidez_superficie": {
        "nome": "Acidez total de superficie (Boehm)", "unidade": "mmol/g",
        "descritor": "S6", "faixa": [0.001, 20.0],
        "metodo_padrao": "titulacao de Boehm (NaOH 0,05 mol/L)",
        "replicatas_minimas": 2},
    "grupos_ftir": {
        "nome": "Grupos funcionais por FTIR", "unidade": "texto",
        "descritor": "S6", "faixa": None,
        "metodo_padrao": "FTIR-ATR 4000-400 cm-1", "replicatas_minimas": 1},
    "onset_termico": {
        "nome": "Onset de decomposicao termica", "unidade": "C",
        "descritor": "P5", "faixa": [20.0, 1200.0],
        "metodo_padrao": "TGA metodo da tangente (ASTM E1131)",
        "replicatas_minimas": 1},
    "angulo_contato": {
        "nome": "Angulo de contato com agua", "unidade": "graus",
        "descritor": "P4", "faixa": [0.0, 180.0],
        "metodo_padrao": "gota sessil (sessile drop)", "replicatas_minimas": 3},
    "ctc": {
        "nome": "Capacidade de troca cationica", "unidade": "mmolc/kg",
        "descritor": "P3", "faixa": [0.1, 5000.0],
        "metodo_padrao": "saturacao com acetato de amonio",
        "replicatas_minimas": 2},
    "capacidade_adsorcao": {
        "nome": "Capacidade de adsorcao qmax", "unidade": "mg/g",
        "descritor": "D1", "faixa": [0.001, 5000.0],
        "metodo_padrao": "isoterma de equilibrio (batelada)",
        "replicatas_minimas": 2},
    "tempo_equilibrio": {
        "nome": "Tempo de equilibrio da adsorcao", "unidade": "min",
        "descritor": "D3", "faixa": [0.1, 100000.0],
        "metodo_padrao": "cinetica em batelada com amostragem",
        "replicatas_minimas": 1},
    "lixiviacao": {
        "nome": "Concentracao lixiviada", "unidade": "mg/L",
        "descritor": "P7", "faixa": [0.0, 100000.0],
        "metodo_padrao": "ABNT NBR 10005 (extrato solubilizado)",
        "replicatas_minimas": 1},
    "dessorcao": {
        "nome": "Eficiencia de dessorcao", "unidade": "%",
        "descritor": "D5", "faixa": [0.0, 100.0],
        "metodo_padrao": "ciclo adsorcao/dessorcao", "replicatas_minimas": 1},
    "conformidade_analito": {
        "nome": "Concentracao de analito para conformidade", "unidade": "mg/L",
        "descritor": "C6", "faixa": [0.0, 100000.0],
        "metodo_padrao": "metodo normativo (ex.: SM 3111/EPA 200.8)",
        "replicatas_minimas": 1},
}


def catalogo() -> dict:
    """Tecnicas aceitas, unidade, faixa e descritor alimentado."""
    linhas = [{"tipo": chave, "nome": meta["nome"],
               "unidade": meta["unidade"], "descritor": meta["descritor"],
               "faixa_aceita": meta["faixa"],
               "metodo_padrao": meta["metodo_padrao"],
               "replicatas_minimas": meta["replicatas_minimas"]}
              for chave, meta in TIPOS.items()]
    return {"total": len(linhas), "versao": VERSAO, "tipos": linhas}



def _normalizar_unidade(texto):
    return (str(texto or "").strip().lower()
            .replace("²", "2").replace("³", "3").replace(" ", "")
            .replace("º", "").replace("°", ""))


def validar(medicao: dict) -> dict:
    """Normaliza e valida uma medicao. Levanta DadosInvalidos se inconsistente."""
    if not isinstance(medicao, dict):
        raise motor_pesquisa.DadosInvalidos("medicao deve ser um objeto JSON")
    tipo = str(medicao.get("tipo") or "").strip().lower()
    meta = TIPOS.get(tipo)
    if meta is None:
        raise motor_pesquisa.DadosInvalidos(
            "tipo de medicao desconhecido: %r (aceitos: %s)"
            % (medicao.get("tipo"), ", ".join(sorted(TIPOS))))
    unidade = _normalizar_unidade(medicao.get("unidade") or meta["unidade"])
    if unidade != _normalizar_unidade(meta["unidade"]):
        raise motor_pesquisa.DadosInvalidos(
            "unidade de %s deve ser '%s' (recebido: %r); converta antes de "
            "enviar" % (tipo, meta["unidade"], medicao.get("unidade")))
    replicatas = medicao.get("replicatas")
    if replicatas is not None and not isinstance(replicatas, list):
        raise motor_pesquisa.DadosInvalidos("replicatas deve ser lista")
    if replicatas:
        replicatas = [ax._num(valor, "replicata") for valor in replicatas]
    valor = medicao.get("valor")
    if valor is None and replicatas:
        valor = sum(replicatas) / len(replicatas)
    texto = medicao.get("valor_texto") or medicao.get("resultado_texto")
    if meta["faixa"] is not None:
        if valor is None:
            raise motor_pesquisa.DadosInvalidos(
                "informe 'valor' ou 'replicatas' para a medicao %s" % tipo)
        valor = ax._num(valor, "valor")
        minimo, maximo = meta["faixa"]
        if not (minimo <= valor <= maximo):
            raise motor_pesquisa.DadosInvalidos(
                "%s fora da faixa fisica aceita [%s, %s] %s (recebido: %s)"
                % (meta["nome"], minimo, maximo, meta["unidade"], valor))
    elif not texto:
        raise motor_pesquisa.DadosInvalidos(
            "para %s informe 'valor_texto' (ex.: grupos atribuidos)" % tipo)
    incerteza = medicao.get("incerteza")
    if incerteza is not None:
        incerteza = ax._num(incerteza, "incerteza", nao_negativo=True)
    condicoes = medicao.get("condicoes")
    if condicoes is not None and not isinstance(condicoes, dict):
        raise motor_pesquisa.DadosInvalidos("condicoes deve ser objeto JSON")
    return {
        "tipo": tipo, "descritor": meta["descritor"],
        "valor": valor, "valor_texto": texto, "unidade": meta["unidade"],
        "metodo": medicao.get("metodo") or meta["metodo_padrao"],
        "instrumento": medicao.get("instrumento"),
        "incerteza": incerteza, "replicatas": replicatas or [],
        "condicoes": condicoes or {},
        "laboratorio": medicao.get("laboratorio"),
        "operador": medicao.get("operador"),
        "data_medicao": medicao.get("data_medicao"),
        "pesquisa_id": medicao.get("pesquisa_id"),
        "replicatas_minimas": meta["replicatas_minimas"],
    }


def estatisticas(replicatas, incerteza=None):
    """Media, desvio, RSR e outlier de Grubbs das replicatas.

    Com 1 replicata devolve apenas o valor; com 2 ou mais calcula desvio e
    coeficiente de variacao; com 3 ou mais aplica o teste de Grubbs.
    """
    valores = [ax._num(valor, "replicata") for valor in (replicatas or [])]
    if not valores:
        return None
    media, sd = ax._media_sd(valores)
    n = len(valores)
    dados = {"n": n, "media": round(media, 6), "desvio": round(sd, 6),
             "rsr_pct": round(100.0 * sd / media, 3) if media else None,
             "incerteza_informada": incerteza,
             "valores_validos": list(valores)}
    if n >= 3:
        teste = ax.grubbs(valores)
        dados["grubbs"] = teste
        if teste["outlier"] is not None:
            dados["valores_validos"] = [valor for indice, valor
                                        in enumerate(valores)
                                        if indice != teste["outlier"]]
    return dados


def _estado_de_medicao(estat, replicatas_minimas):
    """`validado` so com replicatas suficientes e RSR <= 10%; senao `presente`."""
    if not estat or estat["n"] < max(2, replicatas_minimas):
        return "presente", ("replicata insuficiente para validar (n=%s, "
                            "minimo %s)" % (estat["n"] if estat else 0,
                                            max(2, replicatas_minimas)))
    if estat.get("rsr_pct") is not None and estat["rsr_pct"] > 10.0:
        return "presente", ("dispersao alta entre replicatas (RSR %.2f%% > "
                            "10%%)" % estat["rsr_pct"])
    return "validado", None


def registrar(material_id: str, medicao: dict) -> dict:
    """Valida, grava a medicao e atualiza o descritor correspondente."""
    dados = validar(medicao)
    estat = estatisticas(dados["replicatas"], dados["incerteza"])
    if estat and dados["valor"] is None:
        dados["valor"] = estat["media"]
    estado, motivo = _estado_de_medicao(estat, dados["replicatas_minimas"])
    fonte = ("medicao experimental: %s (%s)" %
             (dados["metodo"], dados["laboratorio"] or "laboratorio nao "
              "informado"))
    complemento = {
        "medicao_tipo": dados["tipo"], "metodo": dados["metodo"],
        "instrumento": dados["instrumento"], "incerteza": dados["incerteza"],
        "estatistica": estat, "condicoes": dados["condicoes"],
        "data_medicao": dados["data_medicao"],
        "operador": dados["operador"], "laboratorio": dados["laboratorio"],
        "motivo_estado": motivo,
    }
    sessao_db = db.sessao()
    try:
        registro = db.Medicao(
            id=db.novo_id("med"), material_id=str(material_id).strip(),
            pesquisa_id=dados["pesquisa_id"], tipo=dados["tipo"],
            descritor=dados["descritor"], valor=dados["valor"],
            valor_texto=dados["valor_texto"], unidade=dados["unidade"],
            metodo=dados["metodo"], instrumento=dados["instrumento"],
            incerteza=dados["incerteza"],
            replicatas_json=json_dumps(dados["replicatas"]),
            estatistica_json=json_dumps(estat),
            condicoes_json=json_dumps(dados["condicoes"]),
            laboratorio=dados["laboratorio"], operador=dados["operador"],
            data_medicao=dados["data_medicao"], estado=estado)
        sessao_db.add(registro)
        sessao_db.commit()
        medicao_id = registro.id
    finally:
        sessao_db.close()
    atualizacao = motor_pesquisa.registrar_valor_medido(
        material_id, dados["descritor"], valor=dados["valor"],
        valor_texto=dados["valor_texto"], unidade=dados["unidade"],
        estado=estado, fonte=fonte, pesquisa_id=dados["pesquisa_id"],
        complemento=complemento)
    return {
        "medicao_id": medicao_id, "material_id": str(material_id).strip(),
        "tipo": dados["tipo"], "descritor": dados["descritor"],
        "valor": dados["valor"], "valor_texto": dados["valor_texto"],
        "unidade": dados["unidade"], "metodo": dados["metodo"],
        "estado": estado, "motivo_estado": motivo,
        "estatistica": estat, "descritor_atualizado":
            atualizacao.get("descritor"),
        "conflito": atualizacao.get("conflito"),
        "origem": "medicao_experimental",
    }


def registrar_lote(material_id: str, medicoes: list) -> dict:
    """Registra varias medicoes; erro em uma nao derruba as demais."""
    if not isinstance(medicoes, list) or not medicoes:
        raise motor_pesquisa.DadosInvalidos("informe 'medicoes' como lista")
    registradas, falhas = [], []
    for indice, item in enumerate(medicoes):
        try:
            registradas.append(registrar(material_id, item))
        except motor_pesquisa.DadosInvalidos as erro:
            falhas.append({"indice": indice,
                           "tipo": (item or {}).get("tipo")
                           if isinstance(item, dict) else None,
                           "erro": str(erro)})
        except Exception as erro:                        # noqa: BLE001
            falhas.append({"indice": indice,
                           "tipo": (item or {}).get("tipo")
                           if isinstance(item, dict) else None,
                           "erro": "%s: %s" % (type(erro).__name__, erro)})
    return {"material_id": str(material_id).strip(),
            "total_recebidas": len(medicoes),
            "registradas": len(registradas), "falhas": len(falhas),
            "medicoes": registradas, "erros": falhas}


def _serializar(registro) -> dict:
    return {
        "medicao_id": registro.id, "material_id": registro.material_id,
        "pesquisa_id": registro.pesquisa_id, "tipo": registro.tipo,
        "descritor": registro.descritor, "valor": registro.valor,
        "valor_texto": registro.valor_texto, "unidade": registro.unidade,
        "metodo": registro.metodo, "instrumento": registro.instrumento,
        "incerteza": registro.incerteza,
        "replicatas": db.json_loads(registro.replicatas_json, []),
        "estatistica": db.json_loads(registro.estatistica_json, None),
        "condicoes": db.json_loads(registro.condicoes_json, {}),
        "laboratorio": registro.laboratorio, "operador": registro.operador,
        "data_medicao": (registro.data_medicao.isoformat()
                         if registro.data_medicao else None),
        "estado": registro.estado, "origem": registro.origem,
        "criado_em": (registro.criado_em.isoformat()
                      if registro.criado_em else None),
    }


def _contagem(itens) -> dict:
    saida = {}
    for item in itens:
        saida[item["tipo"]] = saida.get(item["tipo"], 0) + 1
    return saida


def listar(material_id: str = None, pesquisa_id: str = None,
           limite: int = 100) -> dict:
    """Medicoes registradas (mais recentes primeiro)."""
    sessao_db = db.sessao()
    try:
        consulta = sessao_db.query(db.Medicao)
        if material_id:
            consulta = consulta.filter(db.Medicao.material_id ==
                                       str(material_id).strip())
        if pesquisa_id:
            consulta = consulta.filter(db.Medicao.pesquisa_id == pesquisa_id)
        total = consulta.count()
        linhas = (consulta.order_by(db.Medicao.criado_em.desc())
                  .limit(max(1, min(int(limite), 500))).all())
        itens = [_serializar(linha) for linha in linhas]
        return {"total": total, "retornadas": len(itens), "medicoes": itens,
                "por_tipo": _contagem(itens)}
    finally:
        sessao_db.close()


def obter(medicao_id: str) -> dict:
    sessao_db = db.sessao()
    try:
        registro = sessao_db.get(db.Medicao, str(medicao_id).strip())
        if registro is None:
            raise motor_pesquisa.PesquisaNaoEncontrada(
                "medicao nao encontrada: %s" % medicao_id)
        return _serializar(registro)
    finally:
        sessao_db.close()


def apagar(medicao_id: str) -> dict:
    """Remove a medicao (o descritor permanece: e' historico de dado)."""
    sessao_db = db.sessao()
    try:
        registro = sessao_db.get(db.Medicao, str(medicao_id).strip())
        if registro is None:
            raise motor_pesquisa.PesquisaNaoEncontrada(
                "medicao nao encontrada: %s" % medicao_id)
        material_id, tipo = registro.material_id, registro.tipo
        sessao_db.delete(registro)
        db.registrar_historico(sessao_db, "medicao", medicao_id,
                               "medicao_removida",
                               {"tipo": tipo, "material": material_id})
        sessao_db.commit()
        return {"medicao_id": medicao_id, "removida": True,
                "material_id": material_id,
                "aviso": ("o descritor preenchido por esta medicao nao foi "
                          "revertido; reenvie o valor correto se necessario")}
    finally:
        sessao_db.close()


def resumo_material(material_id: str) -> dict:
    """Cobertura de medicao por descritor do material."""
    dados = listar(material_id=material_id, limite=500)
    cobertura = {}
    for item in dados["medicoes"]:
        codigo = item["descritor"] or "?"
        entrada = cobertura.setdefault(codigo, {"total": 0, "tipos": [],
                                                "ultimo_valor": None,
                                                "ultimo_estado": None})
        entrada["total"] += 1
        if item["tipo"] not in entrada["tipos"]:
            entrada["tipos"].append(item["tipo"])
        if entrada["ultimo_valor"] is None:
            entrada["ultimo_valor"] = item["valor"]
            entrada["ultimo_estado"] = item["estado"]
    return {"material_id": str(material_id).strip(),
            "total_medicoes": dados["total"], "por_descritor": cobertura,
            "descritores_cobertos": sorted(cobertura),
            "descritores_sem_medicao": sorted(
                set(TIPOS[t]["descritor"] for t in TIPOS) - set(cobertura))}
