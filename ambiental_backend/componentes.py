# -*- coding: utf-8 -*-
"""Caracterizacao dos quatro componentes do sistema de adsorcao.

Adsorbato, adsorvente, interface e meio tem parametros que nao sao
descritores 7Dx4 mas alimentam regras e simuladores (massa molar, pKa, PZC,
energia de adsorcao, pH, forca ionica, C0, tempo de contato...).

O que este modulo garante:

* o parametro tem que existir no catalogo (`matriz_cruzamentos.PARAMETROS`) e
  pertencer ao componente informado — nao se cria grandeza por texto livre;
* valor numerico e' float finito; unidade divergente da do catalogo nao e'
  aceita em silencio: volta como `aviso` para quem informou;
* origem (informado/importado/medido/calculado/simulado), metodo, referencia e
  estado de validacao ficam gravados em `amb_componentes`;
* quando o parametro declara `descritor`, o valor tambem entra na matriz 7Dx4
  pela via oficial (`motor_pesquisa.registrar_valor_medido`), sem duplicar
  dado: o descritor registra a fonte e o conflito, igual a uma medicao;
* nada e' preenchido por padrao: parametro sem valor fica `ausente`.
"""
from __future__ import annotations

import math
import unicodedata

from . import matriz_7d4, matriz_cruzamentos as cruzamentos
from . import motor_pesquisa, persistencia as db
from .persistencia import Componente

VERSAO = "1.0.0"

ORIGENS = ("informado", "importado", "medido", "calculado", "simulado")
COMPONENTES = tuple(item["chave"] for item in cruzamentos.COMPONENTES)


class ComponenteInvalido(ValueError):
    """Componente, parametro ou valor fora do que o catalogo aceita."""


def catalogo(componente: str = None) -> dict:
    """Catalogo de parametros por componente (alimenta a tela)."""
    if componente is not None:
        alvo = str(componente).strip().lower()
        if alvo not in COMPONENTES:
            raise ComponenteInvalido(
                "componente invalido: %s (use %s)"
                % (componente, ", ".join(COMPONENTES)))
    saida = []
    for item in cruzamentos.PARAMETROS:
        if componente is not None and item["componente"] != alvo:
            continue
        registro = dict(item)
        registro["descritor_nome"] = None
        if item.get("descritor"):
            descritor = matriz_7d4.obter(item["descritor"]) or {}
            registro["descritor_nome"] = descritor.get("nome")
        saida.append(registro)
    return {
        "componentes": [dict(item) for item in cruzamentos.COMPONENTES],
        "parametros": saida,
        "total": len(saida),
        "origens": list(ORIGENS),
        "estados": list(matriz_7d4.ESTADOS_DADO),
    }


def _validar(componente: str, chave: str, valor, valor_texto, estado) -> dict:
    alvo = str(componente or "").strip().lower()
    if alvo not in COMPONENTES:
        raise ComponenteInvalido("componente invalido: %s" % componente)
    meta = cruzamentos.PARAMETROS_POR_CHAVE.get(str(chave or "").strip().lower())
    if meta is None:
        raise ComponenteInvalido(
            "parametro desconhecido: %s (catalogo em GET /api/componENtes)"
            % chave)
    if meta["componente"] != alvo:
        raise ComponenteInvalido(
            "o parametro %s pertence ao componente %s, nao a %s"
            % (meta["chave"], meta["componente"], alvo))
    if estado not in matriz_7d4.ESTADOS_DADO:
        raise ComponenteInvalido("estado invalido: %s" % estado)
    numero = None
    if meta["tipo"] == "numero":
        if valor is None or valor == "":
            raise ComponenteInvalido(
                "o parametro %s exige valor numerico" % meta["chave"])
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            raise ComponenteInvalido(
                "o parametro %s exige valor numerico (recebido %r)"
                % (meta["chave"], valor))
        if math.isnan(numero) or math.isinf(numero):
            raise ComponenteInvalido(
                "o parametro %s exige valor finito" % meta["chave"])
        valor_texto = valor_texto or None
    else:
        if not valor_texto and valor in (None, ""):
            raise ComponenteInvalido(
                "o parametro %s exige descricao em valor_texto" % meta["chave"])
        valor_texto = valor_texto or str(valor)
        numero = None
    return {"meta": meta, "valor": numero, "valor_texto": valor_texto}


def registrar(material_id: str, componente: str, itens, pesquisa_id: str = None,
              preencher_descritor: bool = True) -> dict:
    """Grava a caracterizacao de um componente para o material.

    `itens` e' lista de `{chave, valor, valor_texto, unidade, origem, metodo,
    referencia, estado}`. Um item por parametro; regravar o mesmo parametro
    atualiza a linha em vez de duplicar.

    A gravacao acontece em duas etapas — primeiro os parametros, depois os
    descritores que eles alimentam — para nao abrir duas transacoes no SQLite
    ao mesmo tempo.
    """
    alvo = str(componente or "").strip().lower()
    if alvo not in COMPONENTES:
        raise ComponenteInvalido("componente invalido: %s" % componente)
    if isinstance(itens, dict):
        itens = [itens]
    if not itens:
        raise ComponenteInvalido("informe pelo menos um parametro")
    if pesquisa_id:
        motor_pesquisa.obter(str(pesquisa_id).strip())      # valida a pesquisa
    validados = []
    for item in itens:
        item = item or {}
        estado = str(item.get("estado") or "presente").strip().lower()
        validado = _validar(alvo, item.get("chave"), item.get("valor"),
                            item.get("valor_texto"), estado)
        validados.append((item, validado, estado))
    gravados, avisos = [], []
    sessao_db = db.sessao()
    try:
        material = _material(sessao_db, material_id)
        for item, validado, estado in validados:
            meta = validado["meta"]
            origem = str(item.get("origem") or meta.get("fonte") or "informado")
            if origem not in ORIGENS:
                raise ComponenteInvalido(
                    "origem invalida: %s (use %s)"
                    % (origem, ", ".join(ORIGENS)))
            unidade = item.get("unidade") or meta.get("unidade")
            if (item.get("unidade") and meta.get("unidade")
                    and str(item["unidade"]).strip() != meta["unidade"]):
                avisos.append(
                    "unidade %r difere da unidade do catalogo (%r) para %s"
                    % (item["unidade"], meta["unidade"], meta["chave"]))
            registro = sessao_db.query(Componente).filter(
                Componente.material_id == material.id,
                Componente.componente == alvo,
                Componente.chave == meta["chave"],
                Componente.pesquisa_id == (pesquisa_id or None)).first()
            if registro is None:
                registro = Componente(
                    id=db.novo_id("cmp"), material_id=material.id,
                    pesquisa_id=(pesquisa_id or None), componente=alvo,
                    chave=meta["chave"])
                sessao_db.add(registro)
            registro.nome = meta["nome"]
            registro.valor = validado["valor"]
            registro.valor_texto = validado["valor_texto"]
            registro.unidade = unidade
            registro.origem = origem
            registro.metodo = item.get("metodo")
            registro.referencia = item.get("referencia")
            registro.estado = estado
            registro.atualizado_em = db._agora()
            gravados.append({
                "chave": meta["chave"], "nome": meta["nome"],
                "componente": alvo, "valor": validado["valor"],
                "valor_texto": validado["valor_texto"], "unidade": unidade,
                "estado": estado, "origem": origem,
                "metodo": item.get("metodo"),
                "referencia": item.get("referencia"),
                "descritor": meta.get("descritor"),
            })
        db.registrar_historico(
            sessao_db, "material", material.id, "caracterizacao_componente",
            {"componente": alvo, "pesquisa": pesquisa_id,
             "chaves": [item["chave"] for item in gravados]})
        sessao_db.commit()
        material_id_final = material.id
    finally:
        sessao_db.close()

    descritores = []
    if preencher_descritor:
        for registro in gravados:
            codigo = registro.get("descritor")
            if not codigo:
                continue
            try:
                fonte = ("caracterizacao do %s (%s)"
                         % (alvo, registro["chave"]))
                if registro.get("metodo"):
                    fonte += " · %s" % registro["metodo"]
                resultado = motor_pesquisa.registrar_valor_medido(
                    material_id_final, codigo, valor=registro["valor"],
                    valor_texto=registro["valor_texto"],
                    unidade=registro["unidade"], estado=registro["estado"],
                    fonte=fonte, pesquisa_id=pesquisa_id,
                    complemento={"componente": alvo,
                                 "parametro": registro["chave"],
                                 "origem": registro["origem"]})
                descritores.append({
                    "parametro": registro["chave"], "codigo": codigo,
                    "estado": resultado["descritor"]["estado"],
                    "conflito": resultado.get("conflito"),
                })
            except (motor_pesquisa.DadosInvalidos,
                    motor_pesquisa.PesquisaNaoEncontrada) as erro:
                avisos.append("descritor %s nao preenchido: %s" % (codigo, erro))
    return {
        "material_id": material_id_final,
        "pesquisa_id": pesquisa_id,
        "componente": alvo,
        "gravados": gravados,
        "descritores": descritores,
        "avisos": avisos,
    }


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------
def _material(sessao_db, material_id):
    material = sessao_db.get(db.Material, str(material_id).strip())
    if material is None:
        raise motor_pesquisa.PesquisaNaoEncontrada(
            "material nao encontrado: %s" % material_id)
    return material


def _registros(sessao_db, material_id, pesquisa_id=None) -> dict:
    consulta = sessao_db.query(Componente).filter(
        Componente.material_id == str(material_id).strip())
    if pesquisa_id:
        consulta = consulta.filter(Componente.pesquisa_id == str(pesquisa_id))
    saida = {}
    for item in consulta.all():
        saida[(item.componente, item.chave)] = item
    return saida


def listar(material_id: str, pesquisa_id: str = None) -> dict:
    """Caracterizacao dos quatro componentes: o que existe e o que falta."""
    sessao_db = db.sessao()
    try:
        material = _material(sessao_db, material_id)
        registros = _registros(sessao_db, material.id, pesquisa_id)
        blocos = []
        for componente in cruzamentos.COMPONENTES:
            chave_comp = componente["chave"]
            parametros = []
            for meta in cruzamentos.PARAMETROS:
                if meta["componente"] != chave_comp:
                    continue
                registro = registros.get((chave_comp, meta["chave"]))
                parametros.append({
                    "chave": meta["chave"],
                    "nome": meta["nome"],
                    "tipo": meta["tipo"],
                    "unidade": meta["unidade"],
                    "fonte": meta["fonte"],
                    "papel": meta["papel"],
                    "descritor": meta.get("descritor"),
                    "valor": registro.valor if registro else None,
                    "valor_texto": registro.valor_texto if registro else None,
                    "unidade_registrada": registro.unidade if registro else None,
                    "estado": registro.estado if registro else "ausente",
                    "origem": registro.origem if registro else None,
                    "metodo": registro.metodo if registro else None,
                    "referencia": registro.referencia if registro else None,
                    "atualizado_em": (registro.atualizado_em.isoformat()
                                      if registro and registro.atualizado_em
                                      else None),
                })
            com_valor = [item for item in parametros
                         if item["estado"] in ("presente", "calculado",
                                               "estimado", "validado")]
            blocos.append({
                "componente": chave_comp,
                "nome": componente["nome"],
                "papel": componente["papel"],
                "parametros": parametros,
                "total": len(parametros),
                "com_valor": len(com_valor),
                "faltando": [item["chave"] for item in parametros
                             if item["estado"] not in ("presente", "calculado",
                                                       "estimado", "validado")],
                "cobertura": (round(100.0 * len(com_valor) / len(parametros), 2)
                              if parametros else 0.0),
            })
        return {
            "material": motor_pesquisa.material_dict(material),
            "pesquisa_id": pesquisa_id,
            "componentes": blocos,
            "total_parametros": sum(bloco["total"] for bloco in blocos),
            "total_com_valor": sum(bloco["com_valor"] for bloco in blocos),
        }
    finally:
        sessao_db.close()


def parametros_de(material_id: str, pesquisa_id: str = None) -> dict:
    """`{chave: {...}}` da caracterizacao gravada — entrada de matriz e motores."""
    sessao_db = db.sessao()
    try:
        material = _material(sessao_db, material_id)
        registros = _registros(sessao_db, material.id, pesquisa_id)
        return {
            chave: {
                "valor": registro.valor,
                "valor_texto": registro.valor_texto,
                "unidade": registro.unidade,
                "estado": registro.estado,
                "origem": registro.origem,
                "componente": registro.componente,
            }
            for (_, chave), registro in registros.items()
        }
    finally:
        sessao_db.close()


def apagar(material_id: str, componente: str, chave: str) -> dict:
    """Remove um parametro gravado (o descritor correspondente nao e' tocado)."""
    alvo = str(componente or "").strip().lower()
    sessao_db = db.sessao()
    try:
        material = _material(sessao_db, material_id)
        registro = sessao_db.query(Componente).filter(
            Componente.material_id == material.id,
            Componente.componente == alvo,
            Componente.chave == str(chave or "").strip().lower()).first()
        if registro is None:
            raise ComponenteInvalido(
                "parametro %s nao registrado para %s" % (chave, alvo))
        sessao_db.delete(registro)
        db.registrar_historico(sessao_db, "material", material.id,
                               "caracterizacao_removida",
                               {"componente": alvo, "chave": registro.chave})
        sessao_db.commit()
        return {"removido": True, "componente": alvo, "chave": registro.chave}
    finally:
        sessao_db.close()


# ---------------------------------------------------------------------------
# Ponte componentes -> regras e simuladores
# ---------------------------------------------------------------------------
# Chave que o motor le' -> (parametro de caracterizacao, descritor 7Dx4)
EQUIVALENCIAS = {
    "area_m2g": ("area_superficial", "S3"),
    "area_bet": ("area_superficial", "S3"),
    "diametro_nm": ("raio_ionico", "S5"),
    "densidade": ("densidade", "P1"),
    "temperatura": ("temperatura", "D7"),
    "T": ("temperatura", "D7"),
    "ph": ("ph", "D7"),
    "pH": ("ph", "D7"),
    "C0": ("concentracao_inicial", "D6"),
    "C0_mg_L": ("concentracao_inicial", "D6"),
    "Ce": ("concentracao_equilibrio", "D6"),
    "qmax": ("capacidade_experimental", "D1"),
    "q_max": ("capacidade_experimental", "D1"),
    "massa_g": ("massa_adsorvente", "P1"),
    "volume_mL": ("volume", "D6"),
    "tempo_contato": ("tempo_contato", "D3"),
    "tempo": ("tempo_contato", "D3"),
    "pzc": ("pzc", "P2"),
}


def _chave_texto(texto) -> str:
    base = unicodedata.normalize("NFKD", str(texto or "").strip().lower())
    base = "".join(c for c in base if not unicodedata.combining(c))
    return " ".join(base.replace("-", " ").split())


def _valor_para(chave, parametros, descritores, propriedades):
    """Valor disponivel para a chave que o motor pede, com a fonte de origem."""
    registro = parametros.get(chave)
    if registro and registro.get("valor") is not None:
        return registro["valor"], "caracterizacao:%s" % chave
    equivalencia = EQUIVALENCIAS.get(chave)
    if not equivalencia:
        return None, None
    chave_parametro, codigo = equivalencia
    registro = parametros.get(chave_parametro)
    if registro and registro.get("valor") is not None:
        return registro["valor"], "caracterizacao:%s" % chave_parametro
    propriedade = propriedades.get(_chave_texto(chave_parametro))
    if propriedade and propriedade.get("valor") is not None:
        return propriedade["valor"], "propriedade:%s" % propriedade.get("nome")
    descritor = descritores.get(codigo) or {}
    if descritor.get("valor") is not None:
        return descritor["valor"], "descritor:%s" % codigo
    return None, None


def para_simulador(nome: str, material_id: str = None,
                   pesquisa_id: str = None) -> dict:
    """Preenche os requisitos de um simulador com o que o material ja' tem.

    Ordem da busca: caracterizacao do componente com a mesma chave, parametro
    equivalente, propriedade do material, valor do descritor 7Dx4. O que nao
    existe fica de fora (o motor decide se bloqueia ou roda com padrao).
    """
    from . import descritores_simuladores as simuladores

    requisitos = simuladores.requisitos_de(nome)
    parametros_componente = {}
    descritores, propriedades = {}, {}
    if material_id:
        parametros_componente = parametros_de(material_id, pesquisa_id)
        material = motor_pesquisa.obter_material(material_id)
        descritores = {item["codigo"]: item
                       for item in material.get("descritores") or []}
        propriedades = {_chave_texto(item.get("nome")): item
                        for item in material.get("propriedades") or []}
    parametros, detalhe = {}, []
    for item in requisitos.get("requisitos") or []:
        chave = item.get("chave")
        valor, fonte = _valor_para(chave, parametros_componente, descritores,
                                   propriedades)
        if valor is not None:
            parametros[chave] = valor
        detalhe.append({
            "chave": chave,
            "unidade": item.get("unidade"),
            "obrigatorio": bool(item.get("obrigatorio")),
            "descricao": item.get("descricao"),
            "valor_sugerido": valor,
            "fonte": fonte,
        })
    return {
        "tipo": requisitos.get("tipo"),
        "nome": nome,
        "material_id": material_id,
        "requisitos": detalhe,
        "parametros": parametros,
        "faltando": simuladores.requisitos_pendentes(str(nome or "").strip(),
                                                     parametros),
        "estado": simuladores.classificar(str(nome or "").strip(), parametros),
    }

