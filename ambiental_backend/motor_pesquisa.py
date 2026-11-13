# -*- coding: utf-8 -*-
"""Motor de pesquisa: da pergunta ate a avaliacao de viabilidade.

Fluxo (cada passo grava no banco e devolve o que foi medido):

    1. estruturar a pergunta           -> termos, contaminante, aplicacao
    2. identificar propriedades        -> descritores 7Dx4 relevantes
    3. montar protocolo                -> descritores + simuladores + criterios
    4. recuperar dados                 -> material, composicao, propriedades
    5. cruzar evidencias               -> bases cientificas reais
    6. selecionar e executar simuladores -> `universal.py`
    7. comparar com a literatura       -> desvio relativo por grandeza
    8. avaliar viabilidade             -> pontuacao + lacunas + riscos

Nenhum passo inventa dado: quando falta entrada, o campo sai como `ausente`
com a lista do que falta.
"""
from __future__ import annotations

import os
import unicodedata

from . import adaptadores, matriz_7d4
from . import descritores_simuladores
from . import persistencia as db
from .persistencia import (Composicao, Comparacao, Descritor, Evidencia,
                           Historico, Material, Pesquisa, PesquisaMaterial,
                           Propriedade, Protocolo, ProvaConceito, Referencia,
                           Relatorio, Simulacao, Tarefa, Viabilidade, agora_iso,
                           json_dumps, json_loads, novo_id,
                           registrar_historico)

APLICACOES = {
    "agua": ("agua", "aguas", "corpo hidrico", "potavel", "aquifero"),
    "efluente": ("efluente", "esgoto", "wastewater", "corrente liquida",
                 "banho galvanico"),
    "solo": ("solo", "lixiviacao", "remediacao", "subsolo"),
    "ar": ("atmosfera", "gasoso", "emissoes", "voc"),
    "residuo": ("residuo", "rejeito", "biomassa", "casca", "lodo", "escoria"),
}

CONTAMINANTES = {
    "chumbo": ("chumbo", "pb", "plumbum"),
    "cadmio": ("cadmio", "cd"),
    "cromo": ("cromo", "cr", "cromo hexavalente"),
    "mercurio": ("mercurio", "hg"),
    "arsenio": ("arsenio", "as"),
    "cobre": ("cobre", "cu"),
    "niquel": ("niquel", "ni"),
    "zinco": ("zinco", "zn"),
    "corante": ("corante", "azul de metileno", "rodamina", "tintura", "dye"),
    "farmaco": ("farmaco", "antibiotico", "ibuprofeno", "diclofenaco",
                "paracetamol"),
    "pesticida": ("pesticida", "glifosato", "atrazina", "herbicida"),
    "pfas": ("pfas", "pfoa", "pfos"),
    "nitrato": ("nitrato", "nitrogenio", "amonia"),
    "fosfato": ("fosfato", "fosforo"),
    "oleo": ("oleo", "hidrocarboneto", "petroleo", "diesel"),
}


class PesquisaNaoEncontrada(KeyError):
    """Identificador de pesquisa inexistente."""


class DadosInvalidos(ValueError):
    """Entrada fora do contrato da API."""


def _sem_acento(texto) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _pergunta_formal(pergunta, contaminante, aplicacao) -> str:
    alvo = contaminante or "o contaminante de interesse"
    meio = aplicacao or "o meio estudado"
    return ("Qual material remove %s de %s com desempenho demonstravel, "
            "custo e conformidade verificaveis? (origem: %s)"
            % (alvo, meio, (pergunta or "").strip()[:200]))


def estruturar_pergunta(pergunta: str) -> dict:
    """Extrai termos, contaminante, aplicacao e pergunta formal."""
    texto = _sem_acento(pergunta)
    cercado = " %s " % texto.replace(",", " ")
    aplicacao = None
    for nome, pistas in APLICACOES.items():
        if any(pista in texto for pista in pistas):
            aplicacao = nome
            break
    contaminante = None
    for nome, pistas in CONTAMINANTES.items():
        for pista in pistas:
            if (" %s " % pista) in cercado:
                contaminante = nome
                break
        if contaminante:
            break
    termos = [parte for parte in texto.replace(",", " ").split()
              if len(parte) > 3][:20]
    return {
        "texto": (pergunta or "").strip(),
        "termos": termos,
        "contaminante": contaminante,
        "aplicacao": aplicacao,
        "pergunta_de_pesquisa": _pergunta_formal(pergunta, contaminante,
                                                aplicacao),
        "idioma": "pt-BR",
    }


def criar(dados: dict) -> dict:
    """Cria a pesquisa com identificador unico e trilha de auditoria."""
    pergunta = (dados or {}).get("pergunta")
    if not isinstance(pergunta, str) or len(pergunta.strip()) < 10:
        raise DadosInvalidos("campo 'pergunta' obrigatorio (minimo 10 "
                             "caracteres)")
    estruturada = estruturar_pergunta(pergunta)
    material = (dados.get("material") or "").strip() or None
    contaminante = ((dados.get("contaminante") or "").strip()
                    or estruturada["contaminante"])
    aplicacao = (dados.get("aplicacao") or "").strip() or estruturada["aplicacao"]
    condicoes = dados.get("condicoes")
    if not isinstance(condicoes, dict):
        condicoes = {}

    identificador = novo_id("pesq")
    sessao_db = db.sessao()
    try:
        sessao_db.add(Pesquisa(
            id=identificador, pergunta=pergunta.strip(),
            titulo=(dados.get("titulo") or pergunta.strip()[:200]),
            material=material, contaminante=contaminante,
            aplicacao=aplicacao, condicoes_json=json_dumps(condicoes),
            estado="criada"))
        registrar_historico(sessao_db, "pesquisa", identificador, "criada",
                            {"pergunta": pergunta.strip()})
        sessao_db.commit()
    finally:
        sessao_db.close()
    return obter(identificador)


def _pesquisa_dict(pesquisa: Pesquisa) -> dict:
    return {
        "id": pesquisa.id,
        "pergunta": pesquisa.pergunta,
        "titulo": pesquisa.titulo,
        "material": pesquisa.material,
        "contaminante": pesquisa.contaminante,
        "aplicacao": pesquisa.aplicacao,
        "condicoes": json_loads(pesquisa.condicoes_json, {}),
        "estado": pesquisa.estado,
        "versao": pesquisa.versao,
        "criado_em": (pesquisa.criado_em.isoformat()
                      if pesquisa.criado_em else None),
        "atualizado_em": (pesquisa.atualizado_em.isoformat()
                          if pesquisa.atualizado_em else None),
    }


def _carregar(sessao_db, pesquisa_id: str) -> Pesquisa:
    if not pesquisa_id or not str(pesquisa_id).strip():
        raise DadosInvalidos("identificador de pesquisa vazio")
    pesquisa = sessao_db.get(Pesquisa, str(pesquisa_id).strip())
    if pesquisa is None:
        raise PesquisaNaoEncontrada("pesquisa nao encontrada: %s" % pesquisa_id)
    return pesquisa


def _toque(sessao_db, pesquisa: Pesquisa, estado: str = None) -> None:
    pesquisa.atualizado_em = db._agora()
    if estado:
        pesquisa.estado = estado


def material_dict(material: Material) -> dict:
    if material is None:
        return {}
    return {
        "id": material.id, "nome": material.nome, "formula": material.formula,
        "cas": material.cas, "classe": material.classe,
        "origem": material.origem_material,
        "observacao": material.observacao,
        "criado_em": (material.criado_em.isoformat()
                      if material.criado_em else None),
    }


def obter(pesquisa_id: str) -> dict:
    """Visao agregada da pesquisa (GET /api/research/{id})."""
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        vinculos = sessao_db.query(PesquisaMaterial).filter(
            PesquisaMaterial.pesquisa_id == pesquisa.id).all()
        dados = _pesquisa_dict(pesquisa)
        materiais = []
        for vinculo in vinculos:
            material = sessao_db.get(Material, vinculo.material_id)
            if material is not None:
                item = material_dict(material)
                item["papel"] = vinculo.papel
                materiais.append(item)
        dados.update({
            "estrutura_da_pergunta": estruturar_pergunta(pesquisa.pergunta),
            "materiais": materiais,
            "total_descritores": sessao_db.query(Descritor).filter(
                Descritor.pesquisa_id == pesquisa.id).count(),
            "total_evidencias": sessao_db.query(Evidencia).filter(
                Evidencia.pesquisa_id == pesquisa.id).count(),
            "total_simulacoes": sessao_db.query(Simulacao).filter(
                Simulacao.pesquisa_id == pesquisa.id).count(),
            "tem_protocolo": sessao_db.query(Protocolo).filter(
                Protocolo.pesquisa_id == pesquisa.id).first() is not None,
            "tem_viabilidade": sessao_db.query(Viabilidade).filter(
                Viabilidade.pesquisa_id == pesquisa.id).first() is not None,
            "tem_prova": sessao_db.query(ProvaConceito).filter(
                ProvaConceito.pesquisa_id == pesquisa.id).first() is not None,
        })
        return dados
    finally:
        sessao_db.close()


def listar(limite: int = 50) -> list:
    sessao_db = db.sessao()
    try:
        registros = (sessao_db.query(Pesquisa)
                     .order_by(Pesquisa.criado_em.desc())
                     .limit(max(1, min(int(limite), 200))).all())
        return [_pesquisa_dict(item) for item in registros]
    finally:
        sessao_db.close()


CRITERIOS_VIABILIDADE = [
    {"chave": "dados_descritores", "peso": 25,
     "descricao": "Cobertura da matriz 7Dx4 com dado medido ou calculado"},
    {"chave": "evidencia_cientifica", "peso": 20,
     "descricao": "Evidencias recuperadas em bases reais"},
    {"chave": "simulacao_executada", "peso": 20,
     "descricao": "Simulacoes concluidas com resultado"},
    {"chave": "validacao_externa", "peso": 15,
     "descricao": "Comparacao concordante com a literatura"},
    {"chave": "caracterizacao_material", "peso": 10,
     "descricao": "Composicao e propriedades registradas"},
    {"chave": "risco_e_conformidade", "peso": 10,
     "descricao": "Descritores de risco (P7, C1, C6) preenchidos"},
]


def protocolo_dict(protocolo: Protocolo) -> dict:
    return {
        "id": protocolo.id,
        "pesquisa_id": protocolo.pesquisa_id,
        "perguntas": json_loads(protocolo.perguntas_json, {}),
        "propriedades": json_loads(protocolo.propriedades_json, []),
        "descritores": json_loads(protocolo.descritores_json, []),
        "simuladores": json_loads(protocolo.simuladores_json, []),
        "criterios": json_loads(protocolo.criterios_json, {}),
        "criado_em": (protocolo.criado_em.isoformat()
                      if protocolo.criado_em else None),
    }


def montar_protocolo(pesquisa_id: str, dados: dict = None) -> dict:
    """Monta e persiste o protocolo (descritores, simuladores, criterios)."""
    dados = dados or {}
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        estrutura = estruturar_pergunta(pesquisa.pergunta)
        aplicacao = (dados.get("aplicacao") or pesquisa.aplicacao
                     or estrutura["aplicacao"])
        contaminante = (dados.get("contaminante") or pesquisa.contaminante
                        or estrutura["contaminante"])
        material = dados.get("material") or pesquisa.material
        limite_descritores = dados.get("limite_descritores")
        descritores = matriz_7d4.selecionar(
            pesquisa.pergunta, aplicacao=aplicacao, contaminante=contaminante,
            material=material,
            limite=int(limite_descritores) if limite_descritores else None)
        try:
            simuladores = adaptadores.selecionar_simuladores(
                pesquisa.pergunta,
                limite=int(dados.get("limite_simuladores") or 5))
        except adaptadores.MotorIndisponivel as erro:
            simuladores = [{"simulador": None, "erro": str(erro),
                            "disponivel": False}]
        propriedades = [{"codigo": d["codigo"], "nome": d["nome"],
                         "unidade": d["unidade"], "dimensao": d["dimensao"]}
                        for d in descritores]
        criterios = {
            "cobertura_minima": float(dados.get("cobertura_minima") or 40.0),
            "tolerancia_comparacao": float(dados.get("tolerancia") or 0.2),
            "min_evidencias": int(dados.get("min_evidencias") or 3),
            "criterios_viabilidade": CRITERIOS_VIABILIDADE,
        }
        protocolo = Protocolo(
            id=novo_id("prot"), pesquisa_id=pesquisa.id,
            perguntas_json=json_dumps(estrutura),
            propriedades_json=json_dumps(propriedades),
            descritores_json=json_dumps(descritores),
            simuladores_json=json_dumps(simuladores),
            criterios_json=json_dumps(criterios))
        sessao_db.add(protocolo)
        _toque(sessao_db, pesquisa, "protocolada")
        registrar_historico(sessao_db, "pesquisa", pesquisa.id,
                            "protocolo_montado",
                            {"descritores": len(descritores),
                             "simuladores": len(simuladores)})
        sessao_db.commit()
        return protocolo_dict(protocolo)
    finally:
        sessao_db.close()


def obter_protocolo(pesquisa_id: str) -> dict:
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        protocolo = (sessao_db.query(Protocolo)
                     .filter(Protocolo.pesquisa_id == pesquisa.id)
                     .order_by(Protocolo.criado_em.desc()).first())
        if protocolo is None:
            raise PesquisaNaoEncontrada(
                "protocolo inexistente para %s" % pesquisa.id)
        return protocolo_dict(protocolo)
    finally:
        sessao_db.close()


def _buscar_material_por_nome(sessao_db, nome: str):
    alvo = _sem_acento(nome).strip()
    for material in sessao_db.query(Material).all():
        if _sem_acento(material.nome).strip() == alvo:
            return material
    return None


def adicionar_material(pesquisa_id: str, dados: dict) -> dict:
    """Cadastra (ou reaproveita) o material e vincula a pesquisa."""
    dados = dados or {}
    nome = (dados.get("nome") or "").strip()
    if not nome:
        raise DadosInvalidos("campo 'nome' do material obrigatorio")
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        material = _buscar_material_por_nome(sessao_db, nome)
        criado = False
        if material is None:
            material = Material(
                id=novo_id("mat"), nome=nome,
                formula=dados.get("formula"), cas=dados.get("cas"),
                classe=dados.get("classe"),
                origem_material=dados.get("origem"),
                observacao=dados.get("observacao"))
            sessao_db.add(material)
            sessao_db.flush()
            criado = True
        vinculo = sessao_db.query(PesquisaMaterial).filter(
            PesquisaMaterial.pesquisa_id == pesquisa.id,
            PesquisaMaterial.material_id == material.id).first()
        if vinculo is None:
            sessao_db.add(PesquisaMaterial(
                pesquisa_id=pesquisa.id, material_id=material.id,
                papel=dados.get("papel") or "alvo"))
        composicoes = dados.get("composicao")
        composicoes = composicoes if isinstance(composicoes, list) else []
        for item in composicoes:
            if not isinstance(item, dict) or not item.get("elemento"):
                continue
            sessao_db.add(Composicao(
                material_id=material.id, elemento=str(item["elemento"]),
                fracao_massica=item.get("fracao_massica"),
                fracao_molar=item.get("fracao_molar"),
                origem=item.get("origem") or "declarada pelo usuario"))
        propriedades = dados.get("propriedades")
        propriedades = propriedades if isinstance(propriedades, list) else []
        for item in propriedades:
            if not isinstance(item, dict) or not item.get("nome"):
                continue
            sessao_db.add(Propriedade(
                material_id=material.id, nome=str(item["nome"]),
                valor=item.get("valor"), valor_texto=item.get("valor_texto"),
                unidade=item.get("unidade"), origem=item.get("origem"),
                metodo=item.get("metodo"), confianca=item.get("confianca")))
        if not pesquisa.material:
            pesquisa.material = material.nome
        _toque(sessao_db, pesquisa)
        registrar_historico(sessao_db, "material", material.id,
                            "cadastrado" if criado else "reaproveitado",
                            {"pesquisa": pesquisa.id, "nome": material.nome})
        sessao_db.commit()
        return {
            "material": material_dict(material),
            "criado": criado,
            "composicao": len([c for c in composicoes
                               if isinstance(c, dict) and c.get("elemento")]),
            "propriedades": len([p for p in propriedades
                                 if isinstance(p, dict) and p.get("nome")]),
        }
    finally:
        sessao_db.close()


def listar_materiais(busca: str = None, limite: int = 100) -> list:
    sessao_db = db.sessao()
    try:
        consulta = sessao_db.query(Material)
        if busca:
            consulta = consulta.filter(Material.nome.ilike("%%%s%%" % busca))
        registros = (consulta.order_by(Material.nome)
                     .limit(max(1, min(int(limite), 500))).all())
        return [material_dict(item) for item in registros]
    finally:
        sessao_db.close()


def _descritor_dict(descritor: Descritor) -> dict:
    return {
        "codigo": descritor.codigo,
        "dimensao": descritor.dimensao,
        "nome": descritor.nome,
        "valor": descritor.valor,
        "valor_texto": descritor.valor_texto,
        "unidade": descritor.unidade,
        "estado": descritor.estado,
        "fonte": descritor.fonte,
        "regra": descritor.regra,
        "detalhe": json_loads(descritor.dados_json, {}),
        "atualizado_em": (descritor.atualizado_em.isoformat()
                          if descritor.atualizado_em else None),
    }


def obter_material(material_id: str) -> dict:
    sessao_db = db.sessao()
    try:
        material = sessao_db.get(Material, str(material_id).strip())
        if material is None:
            raise PesquisaNaoEncontrada("material nao encontrado: %s"
                                        % material_id)
        dados = material_dict(material)
        dados["composicao"] = [
            {"elemento": item.elemento,
             "fracao_massica": item.fracao_massica,
             "fracao_molar": item.fracao_molar, "origem": item.origem}
            for item in sessao_db.query(Composicao).filter(
                Composicao.material_id == material.id).all()]
        dados["propriedades"] = [
            {"nome": item.nome, "valor": item.valor,
             "valor_texto": item.valor_texto, "unidade": item.unidade,
             "origem": item.origem, "metodo": item.metodo,
             "confianca": item.confianca}
            for item in sessao_db.query(Propriedade).filter(
                Propriedade.material_id == material.id).all()]
        linhas = [_descritor_dict(item) for item in
                  sessao_db.query(Descritor).filter(
                      Descritor.material_id == material.id).all()]
        dados["descritores"] = linhas
        existentes = {item["codigo"]: item["estado"] for item in linhas}
        dados["preenchimento"] = matriz_7d4.avaliar_preenchimento(
            [{"codigo": item["codigo"],
              "estado": existentes.get(item["codigo"], "ausente")}
             for item in matriz_7d4.DESCRITORES])
        return dados
    finally:
        sessao_db.close()


def descritores_do_material(material_id: str) -> dict:
    """Matriz 7Dx4 do material: 28 linhas, cada uma com seu estado."""
    sessao_db = db.sessao()
    try:
        material = sessao_db.get(Material, str(material_id).strip())
        if material is None:
            raise PesquisaNaoEncontrada("material nao encontrado: %s"
                                        % material_id)
        registrados = {item.codigo: item for item in sessao_db.query(
            Descritor).filter(Descritor.material_id == material.id).all()}
        linhas = []
        for descritor in matriz_7d4.DESCRITORES:
            registro = registrados.get(descritor["codigo"])
            linha = {
                "codigo": descritor["codigo"],
                "dimensao": descritor["dimensao"],
                "dimensao_nome": descritor["dimensao_nome"],
                "nome": descritor["nome"],
                "definicao": descritor["definicao"],
                "unidade": descritor["unidade"],
                "regra": descritor["regra"],
                "essencial": descritor["essencial"],
                "valor": None, "valor_texto": None, "fonte": None,
                "estado": "ausente",
            }
            if registro is not None:
                linha.update({
                    "valor": registro.valor,
                    "valor_texto": registro.valor_texto,
                    "unidade": registro.unidade or linha["unidade"],
                    "estado": registro.estado,
                    "fonte": registro.fonte,
                    "detalhe": json_loads(registro.dados_json, {}),
                })
            linhas.append(linha)
        return {
            "material": material_dict(material),
            "total": len(linhas),
            "descritores": linhas,
            "preenchimento": matriz_7d4.avaliar_preenchimento(linhas),
        }
    finally:
        sessao_db.close()


def _resultado_descritor(codigo, entrada_calculo, entrada_valor,
                         estado_padrao, fonte):
    """Decide entre valor informado e aplicacao da regra matematica."""
    if isinstance(entrada_valor, dict):
        valor = entrada_valor.get("valor")
        texto = entrada_valor.get("valor_texto")
        if valor is not None or texto:
            return {
                "codigo": codigo,
                "estado": (entrada_valor.get("estado") or estado_padrao),
                "valor": valor, "valor_texto": texto,
                "unidade": entrada_valor.get("unidade"),
                "fonte": entrada_valor.get("fonte") or fonte,
                "memoria": "valor informado pelo usuario",
            }
    if isinstance(entrada_calculo, dict):
        resultado = matriz_7d4.aplicar(codigo, entrada_calculo)
        resultado.setdefault("fonte", fonte or "calculo a partir dos dados "
                                              "informados")
        return resultado
    if isinstance(entrada_valor, (int, float)):
        return {"codigo": codigo, "estado": estado_padrao,
                "valor": float(entrada_valor), "fonte": fonte,
                "memoria": "valor informado pelo usuario"}
    return matriz_7d4.aplicar(codigo, {})


def _upsert_descritor(sessao_db, pesquisa_id, material_id, descritor, resultado):
    registro = sessao_db.query(Descritor).filter(
        Descritor.material_id == material_id,
        Descritor.codigo == descritor["codigo"]).first()
    if registro is None:
        registro = Descritor(material_id=material_id,
                             codigo=descritor["codigo"],
                             dimensao=descritor["dimensao"],
                             nome=descritor["nome"])
        sessao_db.add(registro)
    registro.pesquisa_id = pesquisa_id
    registro.valor = resultado.get("valor")
    texto = resultado.get("valor_texto")
    registro.valor_texto = str(texto) if texto is not None else None
    registro.unidade = resultado.get("unidade") or descritor["unidade"]
    registro.estado = resultado.get("estado") or "ausente"
    registro.fonte = resultado.get("fonte")
    registro.regra = resultado.get("regra") or descritor["regra"]
    registro.dados_json = json_dumps({
        "memoria": resultado.get("memoria"),
        "complemento": resultado.get("complemento"),
        "faltando": resultado.get("faltando"),
    })
    registro.atualizado_em = db._agora()
    sessao_db.flush()
    return _descritor_dict(registro)


def preencher_descritores(pesquisa_id: str, material_id: str,
                          dados: dict) -> dict:
    """Preenche a matriz do material sem exigir os 28 descritores.

    Corpo aceito::

        {"calculo": {"D1": {"pontos": [...]}, "D6": {"C0": 100, "Ce": 20}},
         "valores": {"S3": {"valor": 750, "unidade": "m2/g",
                            "estado": "presente", "fonte": "artigo"}}}

    Cada descritor citado vira uma linha; o que nao fecha fica `ausente` com
    a lista do que falta.
    """
    dados = dados or {}
    calculo = dados.get("calculo") if isinstance(dados.get("calculo"), dict) else {}
    valores = dados.get("valores") if isinstance(dados.get("valores"), dict) else {}
    estado_padrao = (dados.get("estado") or "presente")
    if estado_padrao not in matriz_7d4.ESTADOS_DADO:
        raise DadosInvalidos("estado invalido: %s" % estado_padrao)
    fonte = dados.get("fonte")
    codigos = list(dict.fromkeys(list(calculo) + list(valores)))
    if not codigos and isinstance(dados.get("codigos"), list):
        codigos = [str(c) for c in dados["codigos"]]
    if not codigos:
        raise DadosInvalidos("informe 'calculo', 'valores' ou 'codigos'")

    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        material = sessao_db.get(Material, str(material_id).strip())
        if material is None:
            raise PesquisaNaoEncontrada("material nao encontrado: %s"
                                        % material_id)
        resultados = []
        for codigo in codigos:
            descritor = matriz_7d4.obter(codigo)
            if descritor is None:
                raise DadosInvalidos("descritor desconhecido: %s" % codigo)
            resultado = _resultado_descritor(codigo, calculo.get(codigo),
                                             valores.get(codigo), estado_padrao,
                                             fonte)
            resultados.append(_upsert_descritor(
                sessao_db, pesquisa.id, material.id, descritor, resultado))
        _toque(sessao_db, pesquisa)
        registrar_historico(sessao_db, "material", material.id,
                            "descritores_atualizados",
                            {"pesquisa": pesquisa.id,
                             "codigos": [item["codigo"] for item in resultados]})
        sessao_db.commit()
        return {
            "pesquisa_id": pesquisa.id,
            "material_id": material.id,
            "descritores": resultados,
            "preenchimento": matriz_7d4.avaliar_preenchimento(resultados),
        }
    finally:
        sessao_db.close()


def registrar_valor_medido(material_id: str, codigo: str, valor=None,
                           valor_texto=None, unidade=None,
                           estado="presente", fonte=None, pesquisa_id=None,
                           complemento=None, memoria=None) -> dict:
    """Grava um descritor a partir de medicao experimental (dado de bancada).

    Diferente de `preencher_descritores`, nao exige pesquisa: a medicao pode
    entrar so no material. O estado padrao e' `presente` (dado medido); quem
    chama decide `validado` quando a medicao tem replicatas estatisticamente
    consistentes. Quando o valor anterior difere mais de 10%, a resposta traz
    `conflito` com o valor antigo — nada e' sobrescrito em silencio.

    `memoria` permite registrar a conta/rota que gerou o numero; quando fica
    em branco, vale o texto historico de medicao de bancada (compatibilidade).
    """
    descritor = matriz_7d4.obter(codigo)
    if descritor is None:
        raise DadosInvalidos("descritor desconhecido: %s" % codigo)
    if estado not in matriz_7d4.ESTADOS_DADO:
        raise DadosInvalidos("estado invalido: %s" % estado)
    if valor is None and not valor_texto:
        raise DadosInvalidos("informe valor numerico ou valor_texto")
    sessao_db = db.sessao()
    try:
        material = sessao_db.get(Material, str(material_id).strip())
        if material is None:
            raise PesquisaNaoEncontrada("material nao encontrado: %s"
                                        % material_id)
        anterior = sessao_db.query(Descritor).filter(
            Descritor.material_id == material.id,
            Descritor.codigo == descritor["codigo"]).first()
        conflito = None
        if (anterior is not None and anterior.valor not in (None, 0)
                and isinstance(valor, (int, float))):
            desvio = abs(float(valor) - float(anterior.valor)) / \
                abs(float(anterior.valor))
            if desvio > 0.10:
                conflito = {
                    "valor_anterior": float(anterior.valor),
                    "estado_anterior": anterior.estado,
                    "desvio_relativo": round(desvio, 4),
                    "aviso": ("valor medido difere mais de 10%% do valor "
                              "anterior (%s); os dois ficam registrados") %
                             anterior.estado,
                }
        resultado = {
            "codigo": descritor["codigo"], "estado": estado,
            "valor": valor if isinstance(valor, (int, float)) else None,
            "valor_texto": valor_texto,
            "unidade": unidade or descritor["unidade"],
            "fonte": fonte or "medicao experimental registrada via API",
            "memoria": memoria or "valor medido em bancada (nao calculado por modelo)",
            "complemento": complemento,
        }
        registro = _upsert_descritor(sessao_db, pesquisa_id, material.id,
                                     descritor, resultado)
        registrar_historico(sessao_db, "material", material.id,
                            "medicao_registrada",
                            {"codigo": descritor["codigo"], "estado": estado,
                             "conflito": bool(conflito)})
        sessao_db.commit()
        return {"descritor": registro, "conflito": conflito}
    finally:
        sessao_db.close()


def _consulta_padrao(pesquisa: Pesquisa) -> str:
    partes = [pesquisa.material, pesquisa.contaminante, pesquisa.aplicacao]
    base = " ".join(parte for parte in partes if parte)
    if not base:
        base = pesquisa.pergunta[:200]
    return ("%s adsorcao remocao capacidade" % base).strip()


def _chave_evidencia(item: dict) -> str:
    import hashlib

    doi = (item.get("doi") or "").strip().lower()
    if doi:
        semente = doi
    else:
        semente = "%s|%s" % ((item.get("titulo") or "").strip().lower()[:180],
                             item.get("ano") or "")
    return hashlib.sha1(semente.encode("utf-8")).hexdigest()[:32]


def _relevancia(pesquisa: Pesquisa, item: dict) -> float:
    texto = _sem_acento("%s %s" % (item.get("titulo") or "",
                                  item.get("resumo") or ""))
    alvos = [pesquisa.contaminante, pesquisa.material, "adsorcao",
             "remocao", "isoterma", "capacidade"]
    achados = sum(1 for alvo in alvos if alvo and _sem_acento(alvo) in texto)
    return round(min(1.0, achados / max(1, len([a for a in alvos if a]))), 3)


def evidencia_dict(evidencia: Evidencia) -> dict:
    return {
        "id": evidencia.id,
        "base": evidencia.base,
        "fonte": evidencia.fonte,
        "titulo": evidencia.titulo,
        "ano": evidencia.ano,
        "doi": evidencia.doi,
        "link": evidencia.link,
        "resumo": evidencia.resumo,
        "tipo": evidencia.tipo,
        "relevancia": evidencia.relevancia,
        "termo": evidencia.termo,
        "criado_em": (evidencia.criado_em.isoformat()
                      if evidencia.criado_em else None),
    }


def buscar_evidencias_pesquisa(pesquisa_id: str, termo: str = None, bases=None,
                               n: int = 3, max_bases: int = 4,
                               material_id: str = None) -> dict:
    """Executa a busca nas bases e persiste o que e' novo (dedup por DOI/titulo)."""
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        consulta = (termo or "").strip() or _consulta_padrao(pesquisa)
        resultado = adaptadores.buscar_evidencias(
            consulta, bases=bases, n=n, max_bases=max_bases)
        novas, repetidas = 0, 0
        for item in resultado.get("itens") or []:
            chave = _chave_evidencia(item)
            existente = sessao_db.query(Evidencia).filter(
                Evidencia.pesquisa_id == pesquisa.id,
                Evidencia.chave == chave).first()
            if existente is not None:
                repetidas += 1
                continue
            evidencia = Evidencia(
                id=novo_id("evid"), pesquisa_id=pesquisa.id,
                material_id=material_id, termo=consulta[:300],
                base=(item.get("base") or item.get("fonte") or "")[:60],
                fonte=(item.get("fonte") or "")[:160],
                titulo=item.get("titulo"), ano=item.get("ano"),
                doi=(item.get("doi") or "")[:160],
                link=(item.get("link") or "")[:400],
                resumo=item.get("resumo"),
                tipo=(item.get("tipo") or "")[:80],
                relevancia=_relevancia(pesquisa, item),
                chave=chave, bruto_json=json_dumps(item))
            sessao_db.add(evidencia)
            sessao_db.flush()
            autores = item.get("autores") or []
            if autores or item.get("link"):
                sessao_db.add(Referencia(
                    evidencia_id=evidencia.id,
                    autores_json=json_dumps(autores),
                    veiculo=(item.get("fonte") or "")[:240],
                    ano=item.get("ano"), doi=(item.get("doi") or "")[:160],
                    url=(item.get("link") or "")[:400]))
            novas += 1
        _toque(sessao_db, pesquisa)
        registrar_historico(sessao_db, "pesquisa", pesquisa.id,
                            "evidencias_buscadas",
                            {"termo": consulta, "novas": novas,
                             "repetidas": repetidas,
                             "motor": resultado.get("motor")})
        sessao_db.commit()
        total = sessao_db.query(Evidencia).filter(
            Evidencia.pesquisa_id == pesquisa.id).count()
        return {
            "pesquisa_id": pesquisa.id,
            "termo": consulta,
            "motor": resultado.get("motor"),
            "estado": resultado.get("estado"),
            "falhas": resultado.get("falhas") or {},
            "totais": resultado.get("totais") or {},
            "novas": novas, "repetidas": repetidas,
            "total_na_pesquisa": total,
        }
    finally:
        sessao_db.close()


def listar_evidencias(pesquisa_id: str) -> dict:
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        registros = (sessao_db.query(Evidencia)
                     .filter(Evidencia.pesquisa_id == pesquisa.id)
                     .order_by(Evidencia.relevancia.desc(),
                               Evidencia.ano.desc()).all())
        return {"pesquisa_id": pesquisa.id, "total": len(registros),
                "evidencias": [evidencia_dict(item) for item in registros]}
    finally:
        sessao_db.close()


def simulacao_dict(simulacao: Simulacao) -> dict:
    return {
        "id": simulacao.id,
        "pesquisa_id": simulacao.pesquisa_id,
        "material_id": simulacao.material_id,
        "simulador": simulacao.simulador,
        "motor": simulacao.motor,
        "parametros": json_loads(simulacao.parametros_json, {}),
        "estado": simulacao.estado,
        "resultado": json_loads(simulacao.resultado_json, None),
        "erro": simulacao.erro,
        "duracao_s": simulacao.duracao_s,
        "nivel_evidencia": simulacao.nivel_evidencia,
        "tarefa_id": simulacao.tarefa_id,
        "criado_em": (simulacao.criado_em.isoformat()
                      if simulacao.criado_em else None),
        "concluido_em": (simulacao.concluido_em.isoformat()
                         if simulacao.concluido_em else None),
    }


def _simuladores_do_protocolo(sessao_db, pesquisa_id):
    protocolo = (sessao_db.query(Protocolo)
                 .filter(Protocolo.pesquisa_id == pesquisa_id)
                 .order_by(Protocolo.criado_em.desc()).first())
    if protocolo is None:
        return []
    return [item.get("simulador") for item in
            (json_loads(protocolo.simuladores_json, []) or [])
            if isinstance(item, dict) and item.get("simulador")]


def criar_simulacoes(pesquisa_id: str, dados: dict = None) -> list:
    """Registra as simulacoes a executar (estado `enfileirada`)."""
    dados = dados or {}
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        nomes = dados.get("simuladores")
        if isinstance(nomes, str):
            nomes = [nomes]
        if not isinstance(nomes, list) or not nomes:
            nomes = _simuladores_do_protocolo(sessao_db, pesquisa.id)
        if not nomes:
            nomes = [item["simulador"] for item in
                     adaptadores.selecionar_simuladores(pesquisa.pergunta)]
        parametros = dados.get("parametros")
        parametros = parametros if isinstance(parametros, dict) else {}
        por_simulador = dados.get("parametros_por_simulador")
        por_simulador = por_simulador if isinstance(por_simulador, dict) else {}
        pergunta = dados.get("pergunta") or pesquisa.pergunta
        pedidos = [str(n).strip() for n in nomes if str(n).strip()][:12]
        disponiveis = adaptadores.nomes_disponiveis()
        desconhecidos = [n for n in pedidos if n not in disponiveis]
        if desconhecidos:
            raise adaptadores.SimuladorDesconhecido(
                "simulador nao registrado: %s" % ", ".join(desconhecidos))
        criadas = []
        for nome in pedidos:
            entrada = {"pergunta": pergunta,
                       "parametros": dict(parametros,
                                          **(por_simulador.get(nome) or {}))}
            entrada["classificacao"] = descritores_simuladores.classificar(
                nome, entrada["parametros"])
            simulacao = Simulacao(
                id=novo_id("sim"), pesquisa_id=pesquisa.id,
                material_id=dados.get("material_id"), simulador=nome,
                motor="universal.SIMULADORES", parametros_json=json_dumps(entrada),
                estado="enfileirada",
                nivel_evidencia=dados.get("nivel_evidencia") or "computacional")
            sessao_db.add(simulacao)
            criadas.append(simulacao)
        _toque(sessao_db, pesquisa)
        registrar_historico(sessao_db, "pesquisa", pesquisa.id,
                            "simulacoes_enfileiradas",
                            {"simuladores": [s.simulador for s in criadas]})
        sessao_db.commit()
        return [simulacao_dict(item) for item in criadas]
    finally:
        sessao_db.close()


def executar_simulacao(simulacao_id: str) -> dict:
    """Executa uma simulacao registrada e grava resultado, erro e duracao."""
    sessao_db = db.sessao()
    try:
        simulacao = sessao_db.get(Simulacao, str(simulacao_id).strip())
        if simulacao is None:
            raise PesquisaNaoEncontrada("simulacao nao encontrada: %s"
                                        % simulacao_id)
        entrada = json_loads(simulacao.parametros_json, {}) or {}
        simulacao.estado = "executando"
        sessao_db.commit()
        try:
            resultado = adaptadores.executar_simulador(
                simulacao.simulador, entrada.get("pergunta") or "",
                entrada.get("parametros") or {})
        except adaptadores.SimuladorDesconhecido as erro:
            resultado = {"simulador": simulacao.simulador, "estado": "erro",
                         "erro": str(erro), "duracao_s": 0.0,
                         "motor": "universal.SIMULADORES"}
        simulacao.estado = resultado.get("estado") or "erro"
        simulacao.resultado_json = json_dumps(resultado.get("resultado"))
        simulacao.erro = resultado.get("erro")
        simulacao.duracao_s = resultado.get("duracao_s")
        simulacao.motor = resultado.get("motor")
        simulacao.concluido_em = db._agora()
        aplicados, avisos = [], []
        if simulacao.material_id and simulacao.estado == "ok":
            from . import adsorventes

            parametros = entrada.get("parametros") or {}
            mapeado = descritores_simuladores.descritores_de(
                simulacao.simulador, parametros,
                json_loads(simulacao.resultado_json, {}) or {})
            avisos = mapeado.get("avisos") or []
            try:
                aplicados = adsorventes.aplicar_descritores(
                    sessao_db, simulacao.pesquisa_id, simulacao.material_id,
                    mapeado.get("descritores") or [])
                if aplicados:
                    registrar_historico(
                        sessao_db, "simulacao", simulacao.id,
                        "descritores_atualizados",
                        {"codigos": [item["codigo"] for item in aplicados]})
            except KeyError as erro:
                avisos.append("material do vinculo inexistente: %s" % erro)
        sessao_db.commit()
        dados = simulacao_dict(simulacao)
        dados["descritores_atualizados"] = aplicados
        dados["avisos"] = avisos
        return dados
    finally:
        sessao_db.close()


def listar_simulacoes(pesquisa_id: str) -> dict:
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        registros = (sessao_db.query(Simulacao)
                     .filter(Simulacao.pesquisa_id == pesquisa.id)
                     .order_by(Simulacao.criado_em).all())
        return {"pesquisa_id": pesquisa.id, "total": len(registros),
                "simulacoes": [simulacao_dict(item) for item in registros]}
    finally:
        sessao_db.close()


def obter_simulacao(pesquisa_id: str, simulacao_id: str) -> dict:
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        simulacao = sessao_db.get(Simulacao, str(simulacao_id).strip())
        if simulacao is None or simulacao.pesquisa_id != pesquisa.id:
            raise PesquisaNaoEncontrada(
                "simulacao %s nao pertence a pesquisa %s"
                % (simulacao_id, pesquisa.id))
        return simulacao_dict(simulacao)
    finally:
        sessao_db.close()


def historico_simulacoes(limite: int = 300, pesquisa_id: str = None) -> list:
    """Execucoes registradas (alimenta o painel de simuladores)."""
    sessao_db = db.sessao()
    try:
        consulta = sessao_db.query(Simulacao)
        if pesquisa_id:
            consulta = consulta.filter(Simulacao.pesquisa_id == pesquisa_id)
        registros = (consulta.order_by(Simulacao.criado_em.desc())
                     .limit(max(1, min(int(limite), 1000))).all())
        return [{
            "id": item.id,
            "simulador": item.simulador,
            "estado": item.estado,
            "erro": item.erro,
            "duracao_s": item.duracao_s,
            "pesquisa_id": item.pesquisa_id,
            "material_id": item.material_id,
            "quando": (item.criado_em.isoformat()
                       if item.criado_em else None),
            "resultado": json_loads(item.resultado_json, None),
        } for item in registros]
    finally:
        sessao_db.close()


def marcar_tarefa(simulacao_id: str, tarefa_id: str) -> None:
    """Vincula a simulacao a tarefa de background que a executa.

    Grava so o identificador: o estado da simulacao e' escrito por
    `executar_simulacao`, para nao sobrescrever um resultado ja concluido.
    """
    sessao_db = db.sessao()
    try:
        simulacao = sessao_db.get(Simulacao, str(simulacao_id).strip())
        if simulacao is None:
            return
        simulacao.tarefa_id = tarefa_id
        sessao_db.commit()
    finally:
        sessao_db.close()


def comparacao_dict(comparacao: Comparacao) -> dict:
    return {
        "id": comparacao.id,
        "descritor": comparacao.descritor,
        "grandeza": comparacao.grandeza,
        "valor_calculado": comparacao.valor_calculado,
        "unidade": comparacao.unidade,
        "valor_literatura": comparacao.valor_literatura,
        "desvio_relativo": comparacao.desvio_relativo,
        "veredito": comparacao.veredito,
        "fonte_literatura": comparacao.fonte_literatura,
    }


def comparar_com_literatura(pesquisa_id: str, tolerancia: float = 0.2) -> dict:
    """Compara valores calculados/medidos com os numeros das evidencias."""
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        evidencias = [json_loads(item.bruto_json, {}) for item in
                      sessao_db.query(Evidencia).filter(
                          Evidencia.pesquisa_id == pesquisa.id).all()]
        if not evidencias:
            raise DadosInvalidos("sem evidencias: execute "
                                 "POST /api/research/{id}/evidence/search antes")
        descritores = sessao_db.query(Descritor).filter(
            Descritor.pesquisa_id == pesquisa.id,
            Descritor.valor.isnot(None)).all()
        if not descritores:
            raise DadosInvalidos("sem descritores numericos: preencha a matriz "
                                 "antes de comparar")
        for antigo in sessao_db.query(Comparacao).filter(
                Comparacao.pesquisa_id == pesquisa.id).all():
            sessao_db.delete(antigo)
        criadas = []
        for descritor in descritores:
            achados = adaptadores.comparar_com_literatura(
                descritor.valor, descritor.unidade or "", evidencias,
                tolerancia=float(tolerancia))
            for achado in achados:
                linha = Comparacao(
                    pesquisa_id=pesquisa.id, descritor=descritor.codigo,
                    grandeza=descritor.nome,
                    valor_calculado=achado["valor_calculado"],
                    unidade=achado["unidade"],
                    valor_literatura=achado["valor_literatura"],
                    fonte_literatura=achado["fonte_literatura"][:300],
                    desvio_relativo=achado["desvio_relativo"],
                    criterio="desvio_relativo <= %.2f" % float(tolerancia),
                    veredito=achado["veredito"])
                sessao_db.add(linha)
                criadas.append(linha)
        _toque(sessao_db, pesquisa)
        registrar_historico(sessao_db, "pesquisa", pesquisa.id,
                            "comparacao_executada",
                            {"comparacoes": len(criadas)})
        sessao_db.commit()
        concordantes = sum(1 for item in criadas
                           if item.veredito == "concordante")
        return {"pesquisa_id": pesquisa.id, "total": len(criadas),
                "concordantes": concordantes,
                "tolerancia": float(tolerancia),
                "comparacoes": [comparacao_dict(item) for item in criadas]}
    finally:
        sessao_db.close()


def listar_comparacoes(pesquisa_id: str) -> dict:
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        registros = sessao_db.query(Comparacao).filter(
            Comparacao.pesquisa_id == pesquisa.id).all()
        return {"pesquisa_id": pesquisa.id, "total": len(registros),
                "comparacoes": [comparacao_dict(item) for item in registros]}
    finally:
        sessao_db.close()


def _fracao(valor, total):
    if not total:
        return 0.0
    return max(0.0, min(1.0, float(valor) / float(total)))


def viabilidade_dict(viabilidade: Viabilidade) -> dict:
    return {
        "id": viabilidade.id,
        "pesquisa_id": viabilidade.pesquisa_id,
        "pontuacao": viabilidade.pontuacao,
        "classificacao": viabilidade.classificacao,
        "criterios": json_loads(viabilidade.criterios_json, []),
        "lacunas": json_loads(viabilidade.lacunas_json, []),
        "riscos": json_loads(viabilidade.riscos_json, []),
        "recomendacoes": json_loads(viabilidade.recomendacoes_json, []),
        "criado_em": (viabilidade.criado_em.isoformat()
                      if viabilidade.criado_em else None),
    }


def avaliar_viabilidade(pesquisa_id: str) -> dict:
    """Pontua a pesquisa nos 6 criterios declarados e classifica."""
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        descritores = sessao_db.query(Descritor).filter(
            Descritor.pesquisa_id == pesquisa.id).all()
        estados_por_codigo = {item.codigo: item.estado for item in descritores}
        # Cobertura sobre os 28 descritores da matriz: descritor sem linha
        # conta como `ausente` (nao inflar a cobertura com o subconjunto usado).
        preenchimento = matriz_7d4.avaliar_preenchimento(
            [{"codigo": item["codigo"],
              "estado": estados_por_codigo.get(item["codigo"], "ausente")}
             for item in matriz_7d4.DESCRITORES])
        evidencias = sessao_db.query(Evidencia).filter(
            Evidencia.pesquisa_id == pesquisa.id).count()
        simulacoes = sessao_db.query(Simulacao).filter(
            Simulacao.pesquisa_id == pesquisa.id).all()
        ok = [item for item in simulacoes
              if item.estado in ("ok", "ok_com_aproximacao")]
        comparacoes = sessao_db.query(Comparacao).filter(
            Comparacao.pesquisa_id == pesquisa.id).all()
        concordantes = [item for item in comparacoes
                        if item.veredito == "concordante"]
        vinculos = sessao_db.query(PesquisaMaterial).filter(
            PesquisaMaterial.pesquisa_id == pesquisa.id).all()
        caracterizacao = 0
        for vinculo in vinculos:
            caracterizacao += sessao_db.query(Composicao).filter(
                Composicao.material_id == vinculo.material_id).count()
            caracterizacao += sessao_db.query(Propriedade).filter(
                Propriedade.material_id == vinculo.material_id).count()
        estados = {item.codigo: item.estado for item in descritores}
        com_dado = {"presente", "calculado", "estimado", "validado"}
        risco = sum(1 for codigo in ("P7", "C1", "C6")
                    if estados.get(codigo) in com_dado)

        total_avaliado = preenchimento["total_avaliado"]
        fracoes = {
            "dados_descritores": (_fracao(preenchimento["com_dado"],
                                          total_avaliado)
                                  if total_avaliado else 0.0),
            "evidencia_cientifica": _fracao(evidencias, 5),
            "simulacao_executada": _fracao(len(ok), max(1, len(simulacoes))),
            "validacao_externa": _fracao(len(concordantes), 3),
            "caracterizacao_material": _fracao(caracterizacao, 4),
            "risco_e_conformidade": _fracao(risco, 3),
        }
        # __CONTINUACAO_VIABILIDADE__
        criterios, pontuacao = [], 0.0
        for criterio in CRITERIOS_VIABILIDADE:
            fracao = fracoes.get(criterio["chave"], 0.0)
            contribuicao = fracao * criterio["peso"]
            pontuacao += contribuicao
            criterios.append({
                "chave": criterio["chave"],
                "descricao": criterio["descricao"],
                "peso": criterio["peso"],
                "fracao": round(fracao, 3),
                "contribuicao": round(contribuicao, 2),
            })
        pontuacao = round(pontuacao, 2)
        if pontuacao >= 75:
            classificacao = "viavel"
        elif pontuacao >= 50:
            classificacao = "viavel_com_restricoes"
        elif pontuacao >= 25:
            classificacao = "requer_dados"
        else:
            classificacao = "inviavel_no_estado_atual"

        lacunas = []
        if preenchimento["sem_dado"]:
            lacunas.append("%d descritores sem dado na matriz"
                           % preenchimento["sem_dado"])
        if evidencias < 3:
            lacunas.append("evidencias insuficientes (%d; minimo 3)"
                           % evidencias)
        if not ok:
            lacunas.append("nenhuma simulacao concluida com resultado")
        if comparacoes and not concordantes:
            lacunas.append("nenhuma comparacao concordante com a literatura")
        if caracterizacao < 2:
            lacunas.append("material sem composicao/propriedades registradas")
        if risco < 3:
            lacunas.append("risco e conformidade incompletos (P7, C1, C6)")

        riscos = []
        if estados.get("P7") not in com_dado:
            riscos.append("lixiviacao/solubilidade nao avaliada")
        if estados.get("C1") not in com_dado:
            riscos.append("toxicidade do material nao declarada")
        if estados.get("C6") not in com_dado:
            riscos.append("conformidade normativa nao verificada")
        if any(item.estado in ("timeout", "erro") for item in simulacoes):
            riscos.append("ha simulacao com falha; resultado nao utilizado")

        recomendacoes = []
        if preenchimento["por_dimensao"]["D3"]["percentual"] < 50:
            recomendacoes.append("priorizar ensaios de desempenho (dimensao D3)")
        if not evidencias:
            recomendacoes.append("executar busca bibliografica antes de "
                                 "concluir viabilidade")
        if not ok:
            recomendacoes.append("executar ao menos um simulador do catalogo")
        if caracterizacao < 2:
            recomendacoes.append("registrar composicao e propriedades do "
                                 "material")
        if not recomendacoes:
            recomendacoes.append("manter o protocolo e ampliar a faixa de "
                                 "condicoes operacionais")

        viabilidade = Viabilidade(
            id=novo_id("viab"), pesquisa_id=pesquisa.id,
            pontuacao=pontuacao, classificacao=classificacao,
            criterios_json=json_dumps(criterios),
            lacunas_json=json_dumps(lacunas),
            riscos_json=json_dumps(riscos),
            recomendacoes_json=json_dumps(recomendacoes))
        sessao_db.add(viabilidade)
        _toque(sessao_db, pesquisa, "avaliada")
        registrar_historico(sessao_db, "pesquisa", pesquisa.id,
                            "viabilidade_avaliada",
                            {"pontuacao": pontuacao,
                             "classificacao": classificacao})
        sessao_db.commit()
        return viabilidade_dict(viabilidade)
    finally:
        sessao_db.close()


def obter_viabilidade(pesquisa_id: str) -> dict:
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        registro = (sessao_db.query(Viabilidade)
                    .filter(Viabilidade.pesquisa_id == pesquisa.id)
                    .order_by(Viabilidade.criado_em.desc()).first())
        if registro is None:
            raise PesquisaNaoEncontrada(
                "viabilidade inexistente para %s" % pesquisa.id)
        return viabilidade_dict(registro)
    finally:
        sessao_db.close()


def prova_dict(prova: ProvaConceito) -> dict:
    return {
        "id": prova.id,
        "pesquisa_id": prova.pesquisa_id,
        "estado": prova.estado,
        "passos": json_loads(prova.passos_json, []),
        "resultado": json_loads(prova.resultado_json, {}),
        "criado_em": (prova.criado_em.isoformat()
                      if prova.criado_em else None),
    }


def prova_de_conceito(pesquisa_id: str, material_id: str = None,
                      dados: dict = None) -> dict:
    """Executa o caminho completo com os dados ja registrados.

    A prova nao cria dado novo: recalcula com os modelos existentes
    (Langmuir/Freundlich) a partir dos parametros que a pesquisa possui e
    registra cada passo como `ok`, `ausente` ou `falhou`.

    Quando `material_id`/`dados` vem preenchidos, executa antes o fluxo de
    validacao do adsorvente (`adsorventes.validar`): simuladores reais,
    descritores na matriz, modelos, comparacao com literatura e lacunas.
    """
    validacao = None
    if material_id or dados:
        from . import adsorventes

        pedido = dict(dados or {})
        if material_id:
            pedido.setdefault("material_id", material_id)
        validacao = adsorventes.validar(pesquisa_id, pedido)
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        passos = []

        protocolo = (sessao_db.query(Protocolo)
                     .filter(Protocolo.pesquisa_id == pesquisa.id)
                     .order_by(Protocolo.criado_em.desc()).first())
        passos.append({
            "passo": "protocolo", "estado": "ok" if protocolo else "ausente",
            "detalhe": ("protocolo com descritores e simuladores"
                        if protocolo else "monte o protocolo primeiro"),
        })

        vinculos = sessao_db.query(PesquisaMaterial).filter(
            PesquisaMaterial.pesquisa_id == pesquisa.id).all()
        passos.append({
            "passo": "material", "estado": "ok" if vinculos else "ausente",
            "detalhe": "%d material(is) vinculado(s) a pesquisa" % len(vinculos),
        })

        consulta_descritores = sessao_db.query(Descritor).filter(
            Descritor.pesquisa_id == pesquisa.id)
        if material_id:
            consulta_descritores = consulta_descritores.filter(
                Descritor.material_id == material_id)
        descritores = {item.codigo: item
                       for item in consulta_descritores.all()}
        qmax = descritores.get("D1")
        kl = descritores.get("D2")
        parametros = {}
        if qmax is not None and qmax.valor is not None:
            parametros["q_max"] = qmax.valor
        if kl is not None and kl.valor is not None:
            parametros["K_L"] = kl.valor
        if "K_L" not in parametros and qmax is not None:
            # O ajuste de Langmuir do D1 ja devolve KL como complemento: usar
            # esse valor evita pedir o mesmo dado duas vezes.
            complemento = (json_loads(qmax.dados_json, {}) or {}).get(
                "complemento") or {}
            if complemento.get("KL_L_mg"):
                parametros["K_L"] = float(complemento["KL_L_mg"])
        condicoes = json_loads(pesquisa.condicoes_json, {}) or {}
        ce = condicoes.get("Ce") or condicoes.get("C_e") or 10.0
        calculado = None
        # __CONTINUACAO_PROVA__
        if "q_max" in parametros and "K_L" in parametros:
            try:
                calculado = adaptadores.isoterma("langmuir", C_e=float(ce),
                                                 **parametros)
                passos.append({
                    "passo": "calculo_isoterma", "estado": "ok",
                    "detalhe": "qe = %.4f mg/g em Ce = %.4f mg/L"
                               % (calculado["q_e"], float(ce)),
                    "resultado": calculado,
                })
            except Exception as erro:               # noqa: BLE001
                passos.append({"passo": "calculo_isoterma", "estado": "falhou",
                               "detalhe": "%s: %s"
                                          % (type(erro).__name__, erro)})
        else:
            passos.append({
                "passo": "calculo_isoterma", "estado": "ausente",
                "detalhe": "faltam D1 (qmax) e/ou D2 (KL) calculados",
            })

        evidencias = sessao_db.query(Evidencia).filter(
            Evidencia.pesquisa_id == pesquisa.id).count()
        passos.append({
            "passo": "evidencias", "estado": "ok" if evidencias else "ausente",
            "detalhe": "%d evidencia(s) no corpus" % evidencias,
        })

        simulacoes = sessao_db.query(Simulacao).filter(
            Simulacao.pesquisa_id == pesquisa.id).all()
        ok = [item for item in simulacoes
              if item.estado in ("ok", "ok_com_aproximacao")]
        passos.append({
            "passo": "simulacoes",
            "estado": "ok" if ok else ("falhou" if simulacoes else "ausente"),
            "detalhe": "%d de %d simulacao(oes) com resultado"
                       % (len(ok), len(simulacoes)),
            "simuladores": [item.simulador for item in ok],
        })

        comparacoes = sessao_db.query(Comparacao).filter(
            Comparacao.pesquisa_id == pesquisa.id).all()
        concordantes = [item for item in comparacoes
                        if item.veredito == "concordante"]
        passos.append({
            "passo": "comparacao",
            "estado": "ok" if concordantes else ("ausente" if not comparacoes
                                                 else "falhou"),
            "detalhe": "%d comparacao(oes), %d concordante(s)"
                       % (len(comparacoes), len(concordantes)),
        })

        if validacao is not None:
            simuladores_ok = [s for s in validacao["simuladores"]
                              if s.get("executado")]
            passos.append({
                "passo": "validacao_adsorvente",
                "estado": ("ok" if simuladores_ok else "ausente"),
                "detalhe": ("material '%s': %d propriedade(s), %d simulador(es) "
                            "executado(s)" % (validacao["material"]["nome"],
                                              validacao["caracterizacao"]
                                              ["propriedades_gravadas"],
                                              len(simuladores_ok))),
                "material": validacao["material"],
                "nao_mapeadas": validacao["caracterizacao"]["nao_mapeadas"],
            })
            for nome in ("superficie", "cristalografia", "nano", "dft"):
                item = next((s for s in validacao["simuladores"]
                             if s["simulador"] == nome), None)
                if item is None:
                    continue
                passos.append({
                    "passo": "simulador_%s" % nome,
                    "estado": ("ok" if item.get("executado")
                               else item.get("estado")),
                    "detalhe": ("%s | descritores: %s"
                                % (item.get("estado"),
                                   ", ".join(d["codigo"] for d in
                                             (item.get("descritores") or []))
                                   or "nenhum")),
                })
            modelos_ok = [m for m in validacao["modelos"]
                          if m.get("estado") in ("calculado", "ok")]
            passos.append({
                "passo": "modelos_adsorcao",
                "estado": "ok" if modelos_ok else "ausente",
                "detalhe": "%d de %d modelo(s) aplicado(s)" % (
                    len(modelos_ok), len(validacao["modelos"])),
                "resultados": [{"modelo": m["modelo"], "estado": m["estado"],
                                "qe": m.get("qe"), "faltando": m.get("faltando")}
                               for m in validacao["modelos"]],
            })
            compat = validacao["compatibilidade"]
            passos.append({
                "passo": "compatibilidade",
                "estado": ("ok" if compat.get("veredito") == "favoravel"
                           else ("ausente" if compat.get("veredito") ==
                                 "indeterminado" else "atencao")),
                "detalhe": "%s | %s" % (compat.get("veredito"),
                                        "; ".join(compat.get("motivos") or [])),
            })
            passos.append({
                "passo": "lacunas_experimentais",
                "estado": ("ok" if not validacao["lacunas_experimentais"]
                           else "ausente"),
                "detalhe": "%d lacuna(s): %s" % (
                    len(validacao["lacunas_experimentais"]),
                    ", ".join(l["codigo"] for l in
                              validacao["lacunas_experimentais"])),
            })

        resultado = {
            "demonstravel": bool(calculado and (ok or concordantes)),
            "passos_ok": len([p for p in passos if p["estado"] == "ok"]),
            "passos_total": len(passos),
            "lacunas": [p["passo"] for p in passos if p["estado"] != "ok"],
            "calculo": calculado,
        }
        if validacao is not None:
            resultado["validacao_adsorvente"] = {
                "material": validacao["material"],
                "simuladores": [{"simulador": s["simulador"],
                                 "estado": s.get("estado"),
                                 "descritores": [d["codigo"] for d in
                                                 (s.get("descritores") or [])]}
                                for s in validacao["simuladores"]],
                "modelos": [{"modelo": m["modelo"], "estado": m["estado"],
                             "qe": m.get("qe")}
                            for m in validacao["modelos"]],
                "compatibilidade": validacao["compatibilidade"],
                "comparacao_literatura": {
                    "total": validacao["comparacao_literatura"].get("total", 0),
                    "concordantes": validacao["comparacao_literatura"].get(
                        "concordantes", 0),
                },
                "lacunas_experimentais": validacao["lacunas_experimentais"],
                "preenchimento": validacao["preenchimento"],
            }
        prova = ProvaConceito(
            id=novo_id("prova"), pesquisa_id=pesquisa.id,
            estado="executada" if resultado["demonstravel"] else "parcial",
            passos_json=json_dumps(passos),
            resultado_json=json_dumps(resultado))
        sessao_db.add(prova)
        _toque(sessao_db, pesquisa, "prova_executada")
        registrar_historico(sessao_db, "pesquisa", pesquisa.id,
                            "prova_de_conceito",
                            {"demonstravel": resultado["demonstravel"]})
        sessao_db.commit()
        return prova_dict(prova)
    finally:
        sessao_db.close()


def obter_prova(pesquisa_id: str) -> dict:
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        registro = (sessao_db.query(ProvaConceito)
                    .filter(ProvaConceito.pesquisa_id == pesquisa.id)
                    .order_by(ProvaConceito.criado_em.desc()).first())
        if registro is None:
            raise PesquisaNaoEncontrada(
                "prova de conceito inexistente para %s" % pesquisa.id)
        return prova_dict(registro)
    finally:
        sessao_db.close()


def _acrescentar_cruzamentos(dados: dict) -> None:
    """Acrescenta ao resumo a matriz 7x4 (cruzamentos) e a caracterizacao.

    Roda fora da sessao do banco: `componentes` abre as proprias sessoes e o
    SQLite nao aceita duas transacoes simultaneas. O material de referencia e'
    o primeiro vinculado a pesquisa (papel principal do estudo).
    """
    from . import componentes, matriz_cruzamentos as mc

    pesquisa = dados.get("pesquisa") or {}
    materiais = dados.get("materiais") or []
    dados["cruzamentos"] = None
    dados["componentes"] = None
    if not materiais:
        return
    alvo = materiais[0]
    valores = {item["id"]: {linha["codigo"]: linha.get("valor")
                            for linha in item.get("descritores") or []
                            if linha.get("valor") is not None}
               for item in materiais}
    parametros = {}
    try:
        parametros = componentes.parametros_de(alvo["id"], pesquisa.get("id"))
    except Exception:                                   # noqa: BLE001
        parametros = {}
    montada = mc.montar(
        linhas=alvo.get("descritores") or [], parametros=parametros,
        aplicacao=pesquisa.get("aplicacao"), pergunta=pesquisa.get("pergunta"),
        valores_por_material=valores, material_id=alvo["id"])
    montada["material"] = alvo.get("nome")
    dados["cruzamentos"] = montada
    try:
        dados["componentes"] = componentes.listar(alvo["id"], pesquisa.get("id"))
    except Exception:                                   # noqa: BLE001
        dados["componentes"] = None


def resumo(pesquisa_id: str) -> dict:
    """Tudo o que o relatorio precisa, em um dicionario."""
    sessao_db = db.sessao()
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        protocolo = (sessao_db.query(Protocolo)
                     .filter(Protocolo.pesquisa_id == pesquisa.id)
                     .order_by(Protocolo.criado_em.desc()).first())
        vinculos = sessao_db.query(PesquisaMaterial).filter(
            PesquisaMaterial.pesquisa_id == pesquisa.id).all()
        materiais = []
        for vinculo in vinculos:
            material = sessao_db.get(Material, vinculo.material_id)
            if material is None:
                continue
            item = material_dict(material)
            item["papel"] = vinculo.papel
            item["composicao"] = [
                {"elemento": c.elemento, "fracao_massica": c.fracao_massica,
                 "origem": c.origem}
                for c in sessao_db.query(Composicao).filter(
                    Composicao.material_id == material.id).all()]
            item["propriedades"] = [
                {"nome": p.nome, "valor": p.valor, "unidade": p.unidade,
                 "origem": p.origem, "metodo": p.metodo}
                for p in sessao_db.query(Propriedade).filter(
                    Propriedade.material_id == material.id).all()]
            item["descritores"] = [
                _descritor_dict(d) for d in sessao_db.query(Descritor).filter(
                    Descritor.material_id == material.id).all()]
            materiais.append(item)

        descritores = sessao_db.query(Descritor).filter(
            Descritor.pesquisa_id == pesquisa.id).all()
        evidencias = sessao_db.query(Evidencia).filter(
            Evidencia.pesquisa_id == pesquisa.id).order_by(
                Evidencia.relevancia.desc()).all()
        simulacoes = sessao_db.query(Simulacao).filter(
            Simulacao.pesquisa_id == pesquisa.id).order_by(
                Simulacao.criado_em).all()
        comparacoes = sessao_db.query(Comparacao).filter(
            Comparacao.pesquisa_id == pesquisa.id).all()
        viabilidade = (sessao_db.query(Viabilidade)
                       .filter(Viabilidade.pesquisa_id == pesquisa.id)
                       .order_by(Viabilidade.criado_em.desc()).first())
        prova = (sessao_db.query(ProvaConceito)
                 .filter(ProvaConceito.pesquisa_id == pesquisa.id)
                 .order_by(ProvaConceito.criado_em.desc()).first())
        relatorios = sessao_db.query(Relatorio).filter(
            Relatorio.pesquisa_id == pesquisa.id).order_by(
                Relatorio.criado_em.desc()).all()
        base = {
            "pesquisa": _pesquisa_dict(pesquisa),
            "estrutura_da_pergunta": estruturar_pergunta(pesquisa.pergunta),
            "protocolo": protocolo_dict(protocolo) if protocolo else None,
            "materiais": materiais,
            "descritores": [_descritor_dict(item) for item in descritores],
            "preenchimento": matriz_7d4.avaliar_preenchimento(
                [_descritor_dict(item) for item in descritores]),
            "evidencias": [evidencia_dict(item) for item in evidencias],
            "simulacoes": [simulacao_dict(item) for item in simulacoes],
            "comparacoes": [comparacao_dict(item) for item in comparacoes],
            "viabilidade": viabilidade_dict(viabilidade) if viabilidade else None,
            "prova": prova_dict(prova) if prova else None,
            "relatorios": [{
                "id": item.id, "tipo": item.tipo, "formato": item.formato,
                "criado_em": (item.criado_em.isoformat()
                              if item.criado_em else None),
            } for item in relatorios],
            "gerado_em": agora_iso(),
        }
    finally:
        sessao_db.close()
    _acrescentar_cruzamentos(base)
    return base


# ---------------------------------------------------------------------- edicao
CAMPOS_PESQUISA = ("pergunta", "titulo", "material", "contaminante",
                   "aplicacao", "estado")
ESTADOS_PESQUISA = ("criada", "em_andamento", "concluida", "arquivada")


def atualizar(pesquisa_id: str, dados: dict) -> dict:
    """Edita a pesquisa (PATCH).

    Campo ausente nao e' tocado; valor igual ao gravado nao incrementa versao.
    Cada alteracao efetiva entra na trilha (`amb_historico`), de onde a tela de
    Historico le o que mudou e quando.
    """
    dados = dados or {}
    sessao_db = db.sessao()
    alterados = {}
    try:
        pesquisa = _carregar(sessao_db, pesquisa_id)
        for campo in CAMPOS_PESQUISA:
            if dados.get(campo) is None:
                continue
            valor = str(dados[campo]).strip()
            if getattr(pesquisa, campo) == valor:
                continue                     # sem mudanca: nao valida nem grava
            if campo == "pergunta" and len(valor) < 10:
                raise DadosInvalidos("campo 'pergunta' exige 10 caracteres")
            if campo == "estado" and valor not in ESTADOS_PESQUISA:
                raise DadosInvalidos("estado invalido: %s (use %s)"
                                     % (valor, ", ".join(ESTADOS_PESQUISA)))
            setattr(pesquisa, campo, valor or None)
            alterados[campo] = valor
        condicoes = dados.get("condicoes")
        if isinstance(condicoes, dict) and condicoes:
            atuais = json_loads(pesquisa.condicoes_json, {}) or {}
            atuais.update({chave: valor for chave, valor in condicoes.items()
                           if valor is not None})
            pesquisa.condicoes_json = json_dumps(atuais)
            alterados["condicoes"] = condicoes
        if alterados:
            pesquisa.versao = int(pesquisa.versao or 1) + 1
            _toque(sessao_db, pesquisa)
            registrar_historico(sessao_db, "pesquisa", pesquisa.id,
                                "atualizada", alterados)
            sessao_db.commit()
        identificador = pesquisa.id
    finally:
        sessao_db.close()
    return {"atualizada": bool(alterados), "alterados": alterados,
            "pesquisa": obter(identificador)}


CAMPOS_MATERIAL = {"nome": "nome", "formula": "formula", "cas": "cas",
                   "classe": "classe", "origem": "origem_material",
                   "observacao": "observacao"}


def atualizar_material(material_id: str, dados: dict) -> dict:
    """Edita o material e faz merge de propriedades/composicao.

    Propriedade e' identificada pelo `nome`; composicao pelo `elemento`. Item
    ja existente e' atualizado, item novo e' inserido — nada e' apagado, para
    que uma edicao da tela nunca apague medicao anterior sem aviso.
    """
    dados = dados or {}
    sessao_db = db.sessao()
    alterados = {}
    novas_propriedades = 0
    novas_composicoes = 0
    try:
        material = sessao_db.get(Material, str(material_id or "").strip())
        if material is None:
            raise PesquisaNaoEncontrada("material nao encontrado: %s"
                                        % material_id)
        for chave, coluna in CAMPOS_MATERIAL.items():
            if dados.get(chave) is None:
                continue
            valor = str(dados[chave]).strip()
            if chave == "nome" and not valor:
                raise DadosInvalidos("campo 'nome' do material nao pode "
                                     "ficar vazio")
            if getattr(material, coluna) == (valor or None):
                continue
            setattr(material, coluna, valor or None)
            alterados[chave] = valor
        for item in dados.get("propriedades") or []:
            if not isinstance(item, dict):
                continue
            nome = str(item.get("nome") or "").strip()
            if not nome:
                continue
            registro = (sessao_db.query(Propriedade)
                        .filter(Propriedade.material_id == material.id,
                                Propriedade.nome == nome).first())
            if registro is None:
                registro = Propriedade(material_id=material.id, nome=nome)
                sessao_db.add(registro)
                novas_propriedades += 1
            for campo in ("valor", "valor_texto", "unidade", "origem",
                          "metodo", "confianca"):
                if item.get(campo) is not None:
                    setattr(registro, campo, item[campo])
        for item in dados.get("composicao") or []:
            if not isinstance(item, dict):
                continue
            elemento = str(item.get("elemento") or "").strip()
            if not elemento:
                continue
            registro = (sessao_db.query(Composicao)
                        .filter(Composicao.material_id == material.id,
                                Composicao.elemento == elemento).first())
            if registro is None:
                registro = Composicao(material_id=material.id,
                                      elemento=elemento)
                sessao_db.add(registro)
                novas_composicoes += 1
            for campo in ("fracao_massica", "fracao_molar", "origem"):
                if item.get(campo) is not None:
                    setattr(registro, campo, item[campo])
        mudou = bool(alterados or novas_propriedades or novas_composicoes)
        if mudou:
            registrar_historico(sessao_db, "material", material.id, "editado",
                                {"campos": sorted(alterados),
                                 "propriedades_novas": novas_propriedades,
                                 "composicoes_novas": novas_composicoes})
            sessao_db.commit()
        identificador = material.id
    finally:
        sessao_db.close()
    return {"atualizado": mudou, "alterados": alterados,
            "propriedades_novas": novas_propriedades,
            "composicoes_novas": novas_composicoes,
            "material": obter_material(identificador)}


# ------------------------------------------------------------------ indicadores
def estatisticas() -> dict:
    """Indicadores reais do painel (GET /api/stats).

    Tudo sai de uma leitura do banco, com o mesmo criterio de honestidade da
    matriz: `linhas_com_valor` conta apenas descritor com valor gravado, e
    `linhas_possiveis` e' 28 x numero de materiais. Nenhum numero fixo,
    nenhuma linha de demonstracao.
    """
    sessao_db = db.sessao()
    try:
        pesquisas = sessao_db.query(Pesquisa).all()
        materiais = sessao_db.query(Material).count()
        simulacoes = sessao_db.query(Simulacao).all()
        descritores = sessao_db.query(Descritor).all()
        provas = sessao_db.query(ProvaConceito).count()
        relatorios = sessao_db.query(Relatorio).count()
        evidencias = sessao_db.query(Evidencia).count()
        comparacoes = sessao_db.query(Comparacao).count()
        viabilidades = sessao_db.query(Viabilidade).count()
        tarefas_abertas = sessao_db.query(Tarefa).filter(
            ~Tarefa.estado.in_(("concluida", "erro", "cancelada"))).count()

        por_estado = {}
        for pesquisa in pesquisas:
            chave = pesquisa.estado or "criada"
            por_estado[chave] = por_estado.get(chave, 0) + 1

        estados_simulacao = {}
        simulacoes_com_resultado = 0
        for simulacao in simulacoes:
            chave = simulacao.estado or "enfileirada"
            estados_simulacao[chave] = estados_simulacao.get(chave, 0) + 1
            if chave in ("ok", "ok_com_aproximacao", "ok_sem_descritor"):
                simulacoes_com_resultado += 1

        estados_descritor = {}
        linhas_com_valor = 0
        for descritor in descritores:
            chave = descritor.estado or "ausente"
            estados_descritor[chave] = estados_descritor.get(chave, 0) + 1
            if (descritor.valor is not None
                    or (descritor.valor_texto or "").strip()):
                linhas_com_valor += 1

        por_material = len(matriz_7d4.DESCRITORES)
        possiveis = por_material * materiais
        mapa = descritores_simuladores.mapa()
        mapeados = mapa.get("descritores") or []
        com_simulador = int(mapa.get("com_simulador") or len(
            [item for item in mapeados if item.get("simuladores")]))
        sem_simulador = int(mapa.get("sem_simulador") or len(
            [item for item in mapeados
             if item.get("cobertura") == "sem_simulador"]))
        nomes = set()
        for item in mapeados:
            for simulador in (item.get("simuladores") or []):
                if isinstance(simulador, str):
                    nomes.add(simulador)
                    continue
                for chave in ("simulador", "nome", "component_id"):
                    valor = (simulador or {}).get(chave)
                    if valor:
                        nomes.add(str(valor))
                        break
        nomes.discard("")
        nomes_simuladores = sorted(nomes)
        return {
            "dados_demonstracao": False,
            "fonte": "banco ambiental (tabelas amb_*)",
            "pesquisas": {"total": len(pesquisas), "por_estado": por_estado},
            "materiais": {"total": materiais},
            "evidencias": {"total": evidencias},
            "simulacoes": {"total": len(simulacoes),
                           "com_resultado": simulacoes_com_resultado,
                           "por_estado": estados_simulacao},
            "simuladores": {"com_descritor": com_simulador,
                            "descritores_sem_simulador": sem_simulador,
                            "nomes_mapeados": nomes_simuladores},
            "matriz": {"descritores_por_material": por_material,
                       "linhas": len(descritores),
                       "linhas_com_valor": linhas_com_valor,
                       "linhas_possiveis": possiveis,
                       "cobertura_pct": (round(100.0 * linhas_com_valor
                                               / possiveis, 2)
                                         if possiveis else 0.0),
                       "por_estado": estados_descritor},
            "provas_de_conceito": {"total": provas},
            "relatorios": {"total": relatorios},
            "comparacoes_literatura": {"total": comparacoes},
            "viabilidades": {"total": viabilidades},
            "tarefas_ativas": tarefas_abertas,
            "gerado_em": agora_iso(),
        }
    finally:
        sessao_db.close()


def historico(limite: int = 50, pesquisa_id: str = None) -> dict:
    """Historico consolidado (GET /api/history).

    Junta a trilha de auditoria, as pesquisas, as simulacoes e os relatorios
    que estao no banco — o que sobrevive a reinicializacao do servidor, e nao
    o que ficou na memoria do navegador.
    """
    from sqlalchemy import or_

    limite = max(1, min(int(limite or 50), 500))
    sessao_db = db.sessao()
    try:
        consulta = sessao_db.query(Historico)
        if pesquisa_id:
            alvo = str(pesquisa_id).strip()
            consulta = consulta.filter(or_(
                Historico.entidade_id == alvo,
                Historico.detalhe_json.like("%" + alvo + "%")))
        registros = (consulta.order_by(Historico.quando.desc())
                     .limit(limite).all())
        eventos = [{
            "id": item.id,
            "entidade": item.entidade,
            "entidade_id": item.entidade_id,
            "acao": item.acao,
            "detalhe": json_loads(item.detalhe_json, {}),
            "quando": item.quando.isoformat() if item.quando else None,
        } for item in registros]
        relatorios = sessao_db.query(Relatorio).order_by(
            Relatorio.criado_em.desc()).limit(limite).all()
    finally:
        sessao_db.close()
    return {
        "total_eventos": len(eventos),
        "eventos": eventos,
        "pesquisas": listar(limite),
        "simulacoes": historico_simulacoes(limite, pesquisa_id),
        "relatorios": [{
            "id": item.id, "pesquisa_id": item.pesquisa_id, "tipo": item.tipo,
            "formato": item.formato, "tamanho_bytes": item.tamanho_bytes,
            "criado_em": item.criado_em.isoformat() if item.criado_em else None,
        } for item in relatorios],
        "gerado_em": agora_iso(),
    }


# ---------------------------------------------------------------- exclusoes
def _ids(sessao_db, modelo, coluna, valor) -> list:
    """Identificadores das linhas que casam com o filtro."""
    linhas = sessao_db.query(modelo.id).filter(coluna == valor).all()
    return [linha[0] for linha in linhas]


def excluir_material(material_id: str) -> dict:
    """Remove o material e tudo que depende dele.

    A cascata e' escrita a mao (na ordem das chaves estrangeiras) em vez de
    depender de `ON DELETE CASCADE`: SQLite e Postgres precisam se comportar
    igual. A resposta traz a contagem por tabela, para a interface poder
    mostrar o que foi removido em vez de prometer sucesso sem prova.
    """
    from .persistencia import Medicao

    sessao_db = db.sessao()
    apagados = {}
    try:
        material = sessao_db.get(Material, str(material_id).strip())
        if material is None:
            raise PesquisaNaoEncontrada("material nao encontrado: %s"
                                        % material_id)
        simulacoes = _ids(sessao_db, Simulacao,
                          Simulacao.material_id, material.id)
        evidencias = _ids(sessao_db, Evidencia,
                          Evidencia.material_id, material.id)
        apagados["amb_comparacoes"] = (
            sessao_db.query(Comparacao)
            .filter(Comparacao.simulacao_id.in_(simulacoes))
            .delete(synchronize_session=False) if simulacoes else 0)
        apagados["amb_referencias"] = (
            sessao_db.query(Referencia)
            .filter(Referencia.evidencia_id.in_(evidencias))
            .delete(synchronize_session=False) if evidencias else 0)
        for modelo, coluna, tabela in (
                (Simulacao, Simulacao.material_id, "amb_simulacoes"),
                (Evidencia, Evidencia.material_id, "amb_evidencias"),
                (Descritor, Descritor.material_id, "amb_descritores"),
                (Propriedade, Propriedade.material_id, "amb_propriedades"),
                (Composicao, Composicao.material_id, "amb_composicoes"),
                (Medicao, Medicao.material_id, "amb_medicoes"),
                (PesquisaMaterial, PesquisaMaterial.material_id,
                 "amb_pesquisa_materiais")):
            apagados[tabela] = (sessao_db.query(modelo)
                                .filter(coluna == material.id)
                                .delete(synchronize_session=False))
        registrar_historico(sessao_db, "material", material.id, "excluido",
                            {"nome": material.nome, "apagados": apagados})
        sessao_db.delete(material)
        sessao_db.commit()
        return {"material_id": str(material_id), "excluido": True,
                "nome": material.nome, "apagados": apagados}
    except Exception:
        sessao_db.rollback()
        raise
    finally:
        sessao_db.close()


def excluir_pesquisa(pesquisa_id: str) -> dict:
    """Remove a pesquisa e os registros que so' existem dentro dela.

    Materiais nao sao apagados: eles pertencem ao catalogo e podem estar em
    outras pesquisas — apenas o vinculo com esta pesquisa sai.
    """
    sessao_db = db.sessao()
    apagados = {}
    arquivos = []
    try:
        pesquisa = sessao_db.get(Pesquisa, str(pesquisa_id).strip())
        if pesquisa is None:
            raise PesquisaNaoEncontrada("pesquisa nao encontrada: %s"
                                        % pesquisa_id)
        simulacoes = _ids(sessao_db, Simulacao,
                          Simulacao.pesquisa_id, pesquisa.id)
        evidencias = _ids(sessao_db, Evidencia,
                          Evidencia.pesquisa_id, pesquisa.id)
        for registro in sessao_db.query(Relatorio).filter(
                Relatorio.pesquisa_id == pesquisa.id).all():
            if registro.caminho:
                arquivos.append(registro.caminho)
        apagados["amb_comparacoes"] = (
            sessao_db.query(Comparacao)
            .filter(Comparacao.pesquisa_id == pesquisa.id)
            .delete(synchronize_session=False))
        if simulacoes:
            sessao_db.query(Comparacao).filter(
                Comparacao.simulacao_id.in_(simulacoes)).delete(
                    synchronize_session=False)
        apagados["amb_referencias"] = (
            sessao_db.query(Referencia)
            .filter(Referencia.evidencia_id.in_(evidencias))
            .delete(synchronize_session=False) if evidencias else 0)
        for modelo, tabela in (
                (Simulacao, "amb_simulacoes"),
                (Evidencia, "amb_evidencias"),
                (Descritor, "amb_descritores"),
                (Relatorio, "amb_relatorios"),
                (Viabilidade, "amb_viabilidades"),
                (ProvaConceito, "amb_provas_conceito"),
                (Tarefa, "amb_tarefas"),
                (Protocolo, "amb_protocolos"),
                (PesquisaMaterial, "amb_pesquisa_materiais")):
            apagados[tabela] = (sessao_db.query(modelo)
                                .filter(modelo.pesquisa_id == pesquisa.id)
                                .delete(synchronize_session=False))
        apagados["amb_historico"] = (
            sessao_db.query(Historico)
            .filter(Historico.entidade_id == pesquisa.id)
            .delete(synchronize_session=False))
        sessao_db.delete(pesquisa)
        sessao_db.commit()
    except Exception:
        sessao_db.rollback()
        raise
    finally:
        sessao_db.close()
    removidos = 0
    for caminho in arquivos:
        try:
            os.unlink(caminho)
            removidos += 1
        except OSError:
            continue
    return {"pesquisa_id": str(pesquisa_id), "excluido": True,
            "apagados": apagados, "arquivos_removidos": removidos}

