# -*- coding: utf-8 -*-
"""Luna — assistente conversacional do ALEF-TAV Ambiental (API da OpenAI).

Como este modulo funciona:

- a Luna fala pela API oficial da OpenAI (`/v1/chat/completions`) com
  *function calling*: quem le' o dado e' o backend, nao o modelo;
- cada ferramenta consulta o que ja existe (pesquisas, materiais, descritores,
  matriz 7Dx4, caracterizacao dos componentes, simuladores, resultados,
  relatorios). Nada e' recalculado aqui: `matriz_cruzamentos.montar` continua
  sendo a unica fonte dos 28 cruzamentos e dos pesos;
- a chave fica em `OPENAI_API_KEY` (Secret do Space) e nunca sai do processo:
  nao vai para o navegador, para o repositorio nem para a resposta. Todo texto
  que sai daqui passa por `_redigir`;
- sem chave configurada o modulo levanta `LunaNaoConfigurada` (HTTP 503) em vez
  de devolver uma resposta fingida.

Variaveis de ambiente lidas aqui:

    OPENAI_API_KEY        chave da API (obrigatoria para conversar)
    OPENAI_MODEL          modelo fixo; sem ela o modulo descobre na conta
    OPENAI_BASE_URL       padrao https://api.openai.com/v1
    AMBIENTAL_LUNA_TIMEOUT_S      segundos por chamada (padrao 90)
    AMBIENTAL_LUNA_MAX_TURNOS     rodadas de ferramenta (padrao 6)
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from . import (adaptadores, componentes, matriz_7d4, matriz_cruzamentos,
               motor_pesquisa, relatorios)
from . import persistencia as db

VERSAO = "1.0.0"
URL_PADRAO = "https://api.openai.com/v1"

#: Ordem de preferencia quando `OPENAI_MODEL` nao esta definido. O identificador
#: "gpt-6" e' o pretendido; se a conta nao o oferecer, cai para o primeiro
#: modelo da lista que ela realmente autoriza — nunca inventa um nome.
MODELOS_PREFERIDOS = ("gpt-6", "gpt-6-mini", "gpt-5.1", "gpt-5", "gpt-5-mini",
                      "gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini")

USUARIO_PADRAO = "publico"
LIMITE_RESULTADO = 14000          # caracteres por resultado de ferramenta
LIMITE_HISTORICO = 30             # mensagens antigas enviadas como contexto
_CACHE_MODELOS: dict = {"quando": 0.0, "ids": []}


class LunaErro(RuntimeError):
    """Falha de dominio da Luna (traduzida em HTTP por `api_ambiental`)."""


class LunaNaoConfigurada(LunaErro):
    """`OPENAI_API_KEY` ausente: a integracao existe, o motor nao."""


class LunaIndisponivel(LunaErro):
    """OpenAI respondeu erro ou nao respondeu."""


# ------------------------------------------------------------------ credencial
def chave() -> str:
    return str(os.environ.get("OPENAI_API_KEY") or "").strip()


def configurada() -> bool:
    return bool(chave())


def _redigir(texto) -> str:
    """Remove a chave de qualquer texto que va para log ou resposta."""
    saida = str(texto or "")
    segredo = chave()
    if segredo and len(segredo) >= 8:
        saida = saida.replace(segredo, "sk-***")
    return saida


def base_url() -> str:
    return str(os.environ.get("OPENAI_BASE_URL") or URL_PADRAO).rstrip("/")


def timeout_padrao() -> int:
    try:
        return max(10, min(300, int(os.environ.get("AMBIENTAL_LUNA_TIMEOUT_S",
                                                   "90"))))
    except (TypeError, ValueError):
        return 90


def max_turnos() -> int:
    try:
        return max(1, min(12, int(os.environ.get("AMBIENTAL_LUNA_MAX_TURNOS",
                                                 "6"))))
    except (TypeError, ValueError):
        return 6


# ------------------------------------------------------------------- transporte
def _http(metodo: str, caminho: str, corpo=None, timeout=None) -> dict:
    """Chamada autenticada a OpenAI. Erro nunca leva a chave para fora."""
    segredo = chave()
    if not segredo:
        raise LunaNaoConfigurada(
            "OPENAI_API_KEY nao configurada: defina o Secret do Space para a "
            "Luna conversar (a integracao esta pronta, o motor nao).")
    dados = None if corpo is None else json.dumps(corpo).encode("utf-8")
    pedido = urllib.request.Request("%s%s" % (base_url(), caminho), data=dados,
                                    method=metodo)
    pedido.add_header("Authorization", "Bearer " + segredo)
    pedido.add_header("Content-Type", "application/json")
    pedido.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(pedido,
                                    timeout=timeout or timeout_padrao()) as resposta:
            bruto = resposta.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as erro:
        detalhe = ""
        try:
            detalhe = erro.read().decode("utf-8", "replace")
        except Exception:                                  # noqa: BLE001
            detalhe = ""
        mensagem = detalhe
        try:
            mensagem = (json.loads(detalhe).get("error") or {}).get("message") \
                or detalhe
        except (ValueError, AttributeError):
            mensagem = detalhe
        raise LunaIndisponivel("OpenAI HTTP %s: %s"
                               % (erro.code, _redigir(mensagem)[:400]))
    except Exception as erro:                              # noqa: BLE001
        raise LunaIndisponivel(
            "sem resposta da OpenAI: %s"
            % _redigir("%s: %s" % (type(erro).__name__, erro)))
    try:
        return json.loads(bruto or "{}")
    except ValueError:
        raise LunaIndisponivel("resposta da OpenAI nao e' JSON")


def modelos_disponiveis(forcar: bool = False) -> list:
    """Ids de modelo que a chave realmente autoriza (cache de 5 minutos)."""
    agora = time.time()
    if not forcar and _CACHE_MODELOS["ids"] \
            and agora - _CACHE_MODELOS["quando"] < 300:
        return list(_CACHE_MODELOS["ids"])
    dados = _http("GET", "/models")
    ids = sorted(str(item.get("id")) for item in dados.get("data") or []
                 if item.get("id"))
    _CACHE_MODELOS.update({"quando": agora, "ids": ids})
    return ids


def resolver_modelo() -> dict:
    """Modelo efetivo: variavel de ambiente ou o melhor disponivel na conta."""
    fixo = str(os.environ.get("OPENAI_MODEL") or "").strip()
    if fixo:
        return {"modelo": fixo, "origem": "OPENAI_MODEL", "candidatos": [fixo]}
    ids = modelos_disponiveis()
    preferidos = []
    for base in MODELOS_PREFERIDOS:
        for item in ids:
            if item == base or item.startswith(base + "-") \
                    or item.startswith(base + "."):
                if item not in preferidos:
                    preferidos.append(item)
    if not preferidos:
        raise LunaIndisponivel(
            "nenhum modelo da lista preferida esta autorizado na conta "
            "(disponiveis: %s)" % (", ".join(ids[:12]) or "nenhum"))
    return {"modelo": preferidos[0], "origem": "descoberto na conta",
            "candidatos": preferidos[:5]}


def estado() -> dict:
    """Resumo honesto do que esta configurado (consulta a conta se houver chave)."""
    dados = {
        "configurada": configurada(),
        "motor": "OpenAI (chat/completions + function calling)",
        "base_url": base_url(),
        "modelo": str(os.environ.get("OPENAI_MODEL") or "").strip() or None,
        "modelos_preferidos": list(MODELOS_PREFERIDOS),
        "ferramentas": [item["function"]["name"] for item in ESQUEMAS],
        "total_ferramentas": len(ESQUEMAS),
        "max_turnos": max_turnos(),
        "timeout_s": timeout_padrao(),
        "usuario_padrao": USUARIO_PADRAO,
        "historico": total_historico(),
    }
    if not dados["configurada"]:
        dados["aviso"] = ("OPENAI_API_KEY ausente: a Luna esta implementada e "
                          "publicada, mas nao pode responder. Configure o "
                          "Secret no Space (Settings > Secrets) e reinicie.")
        return dados
    try:
        escolha = resolver_modelo()
        dados["modelo"] = escolha["modelo"]
        dados["modelo_origem"] = escolha["origem"]
        dados["modelos_candidatos"] = escolha["candidatos"]
        dados["aviso"] = None
    except LunaErro as erro:
        dados["modelo"] = None
        dados["aviso"] = _redigir(str(erro))
    return dados


# ------------------------------------------------------------------ ferramentas
def _curto(valor, limite: int = 160) -> str:
    texto = " ".join(str(valor if valor is not None else "").split())
    return texto if len(texto) <= limite else texto[:limite].rstrip() + "…"


def _json_seguro(dados, limite: int = LIMITE_RESULTADO) -> str:
    """Serializa o resultado da ferramenta e corta o excesso com aviso."""
    texto = json.dumps(dados, ensure_ascii=False, default=str)
    if len(texto) <= limite:
        return texto
    return json.dumps({
        "aviso": "resultado truncado para caber no contexto (%d caracteres)"
                 % limite,
        "recorte": texto[:limite],
    }, ensure_ascii=False)


def _pesquisa_id(pesquisa_id=None) -> str:
    """Sem id explicito, usa a pesquisa mais recente (nunca inventa)."""
    alvo = str(pesquisa_id or "").strip()
    if alvo:
        return alvo
    registros = motor_pesquisa.listar(limite=1)
    return str((registros[0] or {}).get("id") or "") if registros else ""


def _valores_por_material(pesquisa_id: str = None,
                          material_id: str = None) -> dict:
    """`{material: {codigo: valor}}` — mesma regra de /api/matriz/cruzamentos."""
    ids = []
    if pesquisa_id:
        pesquisa = motor_pesquisa.obter(pesquisa_id)
        ids = [item["id"] for item in pesquisa.get("materiais") or []]
    if material_id and material_id not in ids:
        ids.append(material_id)
    valores = {}
    for alvo in ids:
        try:
            dados = motor_pesquisa.descritores_do_material(alvo)
        except Exception:                                  # noqa: BLE001
            continue
        valores[alvo] = {item["codigo"]: item.get("valor")
                         for item in dados.get("descritores") or []
                         if item.get("valor") is not None}
    return valores


def _f_estado_plataforma(**_):
    return motor_pesquisa.estatisticas()


def _f_listar_pesquisas(limite=10, **_):
    registros = motor_pesquisa.listar(limite=max(1, min(int(limite or 10), 50)))
    return {"total": len(registros), "pesquisas": [{
        "id": item.get("id"),
        "titulo": item.get("titulo"),
        "pergunta": _curto(item.get("pergunta"), 200),
        "contaminante": item.get("contaminante"),
        "aplicacao": item.get("aplicacao"),
        "estado": item.get("estado"),
        "materiais": len(item.get("materiais") or []),
        "criado_em": item.get("criado_em"),
    } for item in registros]}


def _f_obter_pesquisa(pesquisa_id=None, **_):
    alvo = _pesquisa_id(pesquisa_id)
    if not alvo:
        return {"erro": "nenhuma pesquisa cadastrada ainda"}
    dados = motor_pesquisa.obter(alvo)
    return {
        "id": dados.get("id"),
        "titulo": dados.get("titulo"),
        "pergunta": _curto(dados.get("pergunta"), 300),
        "material": dados.get("material"),
        "contaminante": dados.get("contaminante"),
        "aplicacao": dados.get("aplicacao"),
        "estado": dados.get("estado"),
        "condicoes": dados.get("condicoes"),
        "materiais": [{"id": item.get("id"), "nome": item.get("nome"),
                       "papel": item.get("papel")}
                      for item in dados.get("materiais") or []],
    }


def _f_listar_materiais(pesquisa_id=None, busca=None, limite=20, **_):
    if pesquisa_id:
        dados = motor_pesquisa.obter(pesquisa_id)
        itens = dados.get("materiais") or []
    else:
        itens = motor_pesquisa.listar_materiais(
            busca=busca, limite=max(1, min(int(limite or 20), 100)))
    return {"total": len(itens), "materiais": [{
        "id": item.get("id"), "nome": item.get("nome"),
        "formula": item.get("formula"), "classe": item.get("classe"),
        "papel": item.get("papel"),
    } for item in itens[:100]]}


def _f_descritores_material(material_id=None, **_):
    if not material_id:
        return {"erro": "informe material_id (veja listar_materiais)"}
    dados = motor_pesquisa.descritores_do_material(material_id)
    linhas, com_valor = [], []
    for item in dados.get("descritores") or []:
        linha = {"codigo": item.get("codigo"), "nome": item.get("nome"),
                 "valor": item.get("valor"),
                 "valor_texto": item.get("valor_texto"),
                 "unidade": item.get("unidade"), "estado": item.get("estado"),
                 "fonte": item.get("fonte")}
        linhas.append(linha)
        if linha["valor"] is not None or linha["valor_texto"]:
            com_valor.append(linha["codigo"])
    return {"material": dados.get("material"), "total": len(linhas),
            "com_valor": len(com_valor), "ausentes":
                [item["codigo"] for item in linhas
                 if item["codigo"] not in com_valor],
            "descritores": linhas}


def _f_caracterizacao(material_id=None, componente=None, pesquisa_id=None, **_):
    if not material_id:
        return {"erro": "informe material_id"}
    dados = componentes.listar(material_id, pesquisa_id or None)
    blocos = dados.get("componentes") or []
    if componente:
        blocos = [item for item in blocos
                  if item.get("componente") == str(componente).strip().lower()]
    saida = []
    for bloco in blocos:
        presentes = [{"chave": item.get("chave"), "nome": item.get("nome"),
                      "valor": item.get("valor"), "unidade": item.get("unidade"),
                      "estado": item.get("estado"), "origem": item.get("origem")}
                     for item in bloco.get("parametros") or []
                     if item.get("estado") in ("presente", "calculado",
                                               "estimado", "validado")]
        saida.append({"componente": bloco.get("componente"),
                      "nome": bloco.get("nome"),
                      "cobertura_pct": bloco.get("cobertura"),
                      "com_valor": presentes,
                      "faltando": bloco.get("faltando")})
    return {"material": (dados.get("material") or {}).get("nome"),
            "total_parametros": dados.get("total_parametros"),
            "total_com_valor": dados.get("total_com_valor"),
            "componentes": saida}


def _f_catalogo_parametros(componente=None, **_):
    dados = componentes.catalogo(componente or None)
    return {"total": dados.get("total"),
            "componentes": [{"componente": item.get("chave"),
                             "nome": item.get("nome"),
                             "total": item.get("total"),
                             "parametros": [{"chave": par.get("chave"),
                                             "nome": par.get("nome"),
                                             "unidade": par.get("unidade"),
                                             "descritor": par.get("descritor"),
                                             "fonte": par.get("fonte")}
                                            for par in item.get("parametros") or []]}
                            for item in dados.get("componentes") or []]}


def _f_explicar_descritor(codigo=None, **_):
    alvo = str(codigo or "").strip().upper()
    if not alvo:
        return {"erro": "informe codigo (S1..S7, P1..P7, T1..T7, C1..C7)"}
    descritor = matriz_7d4.obter(alvo)
    if not descritor:
        return {"erro": "codigo inexistente: %s" % alvo}
    fontes = descritores_simuladores_do(alvo)
    return {"codigo": alvo, "nome": descritor.get("nome"),
            "definicao": descritor.get("definicao"),
            "unidade": descritor.get("unidade"),
            "dimensao": descritor.get("dimensao"),
            "regra": descritor.get("regra"),
            "essencial": descritor.get("essencial"),
            "cruzamentos": matriz_cruzamentos.relacoes(alvo),
            "simuladores": fontes.get("simuladores"),
            "modelos": fontes.get("modelos"),
            "cobertura": fontes.get("cobertura")}


def descritores_simuladores_do(codigo: str) -> dict:
    """Quais simuladores/modelos podem avaliar este descritor (mapa real)."""
    try:
        from . import descritores_simuladores
        for item in descritores_simuladores.mapa().get("descritores") or []:
            if item.get("codigo") == codigo:
                return item
    except Exception:                                      # noqa: BLE001
        return {}
    return {}


def _f_estrutura_matriz(**_):
    dados = matriz_cruzamentos.estrutura()
    return {
        "dimensoes": [{"letra": item.get("letra"), "nome": item.get("nome"),
                       "pergunta": item.get("pergunta")}
                      for item in dados.get("dimensoes") or []],
        "componentes": [{"chave": item.get("chave"), "nome": item.get("nome"),
                         "papel": item.get("papel")}
                        for item in dados.get("componentes") or []],
        "total_cruzamentos": dados.get("total_cruzamentos"),
        "cruzamentos": [{"id": item.get("id"),
                         "dimensao": item.get("dimensao"),
                         "dimensao_nome": item.get("dimensao_nome"),
                         "componente": item.get("componente"),
                         "componente_nome": item.get("componente_nome"),
                         "descritores": item.get("descritores_possiveis"),
                         "parametros": item.get("parametros_possiveis")}
                        for item in dados.get("cruzamentos") or []],
        "total_parametros": len(dados.get("parametros") or []),
    }


def _f_matriz_montada(material_id=None, pesquisa_id=None, **_):
    """Matriz 7Dx4 montada com o dado real (mesma regra da rota publicada)."""
    alvo_pesquisa = str(pesquisa_id or "").strip() or None
    linha_material, pergunta, aplicacao = None, None, None
    if material_id:
        linha_material = motor_pesquisa.descritores_do_material(material_id)
    if alvo_pesquisa:
        pesquisa = motor_pesquisa.obter(alvo_pesquisa)
        pergunta = pesquisa.get("pergunta")
        aplicacao = pesquisa.get("aplicacao")
        if not material_id:
            materiais = pesquisa.get("materiais") or []
            if materiais:
                material_id = materiais[0]["id"]
                linha_material = motor_pesquisa.descritores_do_material(
                    material_id)
    parametros = {}
    if material_id:
        parametros = componentes.parametros_de(material_id, alvo_pesquisa)
    resultado = matriz_cruzamentos.montar(
        linhas=(linha_material or {}).get("descritores") or [],
        parametros=parametros, aplicacao=aplicacao, pergunta=pergunta,
        valores_por_material=_valores_por_material(alvo_pesquisa, material_id),
        material_id=material_id)
    celulas = []
    for celula in resultado.get("cruzamentos") or []:
        pesos = [{"codigo": item["codigo"], "valor": item.get("valor"),
                  "unidade": item.get("unidade"), "estado": item.get("estado"),
                  "peso": item.get("peso")}
                 for item in celula.get("descritores") or []
                 if item.get("valor") is not None]
        celulas.append({
            "id": celula.get("id"),
            "cruzamento": "%s x %s" % (celula.get("dimensao_nome"),
                                      celula.get("componente_nome")),
            "com_dado": celula["extras"]["com_dado"],
            "lacunas": celula["extras"]["lacunas"],
            "cobertura": celula["extras"]["cobertura"],
            "indice_qualidade": celula["extras"]["indice_qualidade"],
            "indice_comparativo": celula["extras"]["indice_comparativo"],
            "motivo_indice": celula["extras"]["motivo_indice"],
            "descritores_com_valor": pesos,
        })
    return {"material_id": material_id, "pesquisa_id": alvo_pesquisa,
            "resumo": resultado.get("resumo"),
            "preenchimento_7d4": resultado.get("preenchimento_7d4"),
            "cruzamentos": celulas}


def _f_simuladores(**_):
    dados = adaptadores.catalogo_simuladores()
    return {"total_registrados": dados.get("total_registrados"),
            "total_ambientais": dados.get("total_ambientais"),
            "ambientais": [item.get("simulador")
                           for item in dados.get("ambientais") or []],
            "disponiveis": [item.get("simulador")
                            for item in dados.get("ambientais") or []
                            if item.get("disponivel")],
            "motor": dados.get("motor")}


def _f_requisitos_simulador(simulador=None, material_id=None,
                            pesquisa_id=None, **_):
    if not simulador:
        return {"erro": "informe o nome do simulador"}
    dados = componentes.para_simulador(simulador, material_id or None,
                                       pesquisa_id or None)
    return {"simulador": simulador, "tipo": dados.get("tipo"),
            "requisitos": dados.get("requisitos"),
            "parametros": dados.get("parametros"),
            "faltando": dados.get("faltando"),
            "estado": dados.get("estado")}


def _f_resultados_simulacoes(pesquisa_id=None, limite=10, **_):
    alvo = _pesquisa_id(pesquisa_id)
    if not alvo:
        return {"erro": "nenhuma pesquisa cadastrada ainda"}
    dados = motor_pesquisa.listar_simulacoes(alvo)
    itens = []
    for item in (dados.get("simulacoes") or [])[:max(1, min(int(limite or 10),
                                                            50))]:
        itens.append({"simulador": item.get("simulador"),
                      "estado": item.get("estado"),
                      "erro": _curto(item.get("erro"), 160),
                      "duracao_s": item.get("duracao_s"),
                      "quando": item.get("quando") or item.get("criado_em"),
                      "resultado": item.get("resultado")})
    return {"pesquisa_id": alvo, "total": dados.get("total"),
            "simulacoes": itens}


def _f_relatorios(pesquisa_id=None, **_):
    alvo = _pesquisa_id(pesquisa_id)
    if not alvo:
        return {"erro": "nenhuma pesquisa cadastrada ainda"}
    dados = relatorios.listar(alvo)
    return {"pesquisa_id": alvo, "total": dados.get("total"),
            "relatorios": [{"id": item.get("id"), "tipo": item.get("tipo"),
                            "formato": item.get("formato"),
                            "tamanho_bytes": item.get("tamanho_bytes"),
                            "criado_em": item.get("criado_em")}
                           for item in dados.get("relatorios") or []]}


def _f_resumo_pesquisa(pesquisa_id=None, **_):
    alvo = _pesquisa_id(pesquisa_id)
    if not alvo:
        return {"erro": "nenhuma pesquisa cadastrada ainda"}
    dados = motor_pesquisa.resumo(alvo)
    viabilidade = dados.get("viabilidade") or {}
    prova = dados.get("prova") or {}
    return {
        "pesquisa": {chave: (_curto(valor, 300) if isinstance(valor, str)
                             else valor)
                     for chave, valor in (dados.get("pesquisa") or {}).items()},
        "protocolo": dados.get("protocolo"),
        "materiais": [{"id": item.get("id"), "nome": item.get("nome"),
                       "descritores_com_valor": len([d for d in
                                                     item.get("descritores") or []
                                                     if d.get("valor") is not None])}
                      for item in dados.get("materiais") or []],
        "evidencias": len(dados.get("evidencias") or []),
        "simulacoes": [{"simulador": item.get("simulador"),
                        "estado": item.get("estado")}
                       for item in dados.get("simulacoes") or []],
        "viabilidade": {"pontuacao": viabilidade.get("pontuacao"),
                        "classificacao": viabilidade.get("classificacao"),
                        "criterios": viabilidade.get("criterios"),
                        "lacunas": viabilidade.get("lacunas"),
                        "riscos": viabilidade.get("riscos"),
                        "recomendacoes": viabilidade.get("recomendacoes")},
        "prova_de_conceito": {"estado": prova.get("estado"),
                              "passos": prova.get("passos")},
    }


def _f_historico_recente(pesquisa_id=None, limite=20, **_):
    dados = motor_pesquisa.historico(limite=max(1, min(int(limite or 20), 100)),
                                     pesquisa_id=pesquisa_id or None)
    return {"total": dados.get("total_eventos"),
            "eventos": [{"quando": item.get("quando"),
                         "entidade": item.get("entidade"),
                         "acao": item.get("acao")}
                        for item in dados.get("eventos") or []]}


#: Registro nome -> funcao. O modelo so' escolhe entre estas: nao existe
#: ferramenta que escreva no banco nem que rode calculo cientifico.
REGISTRO = {
    "estado_plataforma": _f_estado_plataforma,
    "listar_pesquisas": _f_listar_pesquisas,
    "obter_pesquisa": _f_obter_pesquisa,
    "listar_materiais": _f_listar_materiais,
    "descritores_material": _f_descritores_material,
    "caracterizacao_componentes": _f_caracterizacao,
    "catalogo_parametros": _f_catalogo_parametros,
    "explicar_descritor": _f_explicar_descritor,
    "estrutura_matriz": _f_estrutura_matriz,
    "matriz_montada": _f_matriz_montada,
    "simuladores": _f_simuladores,
    "requisitos_simulador": _f_requisitos_simulador,
    "resultados_simulacoes": _f_resultados_simulacoes,
    "relatorios_pesquisa": _f_relatorios,
    "resumo_pesquisa": _f_resumo_pesquisa,
    "historico_recente": _f_historico_recente,
}


def _esquema(nome: str, descricao: str, propriedades=None, obrigatorios=None):
    return {"type": "function", "function": {
        "name": nome,
        "description": descricao,
        "parameters": {"type": "object",
                       "properties": propriedades or {},
                       "required": obrigatorios or [],
                       "additionalProperties": False},
    }}


_P_PESQUISA = {"type": "string", "description": "id da pesquisa (research_id)"}
_P_MATERIAL = {"type": "string", "description": "id do material"}
_P_COMPONENTE = {"type": "string",
                 "description": "adsorbato, adsorvente, interface ou meio"}

ESQUEMAS = [
    _esquema("estado_plataforma",
             "Contagens reais do banco: pesquisas, materiais, descritores, "
             "simulacoes, relatorios. Use para saber o que existe antes de "
             "afirmar qualquer coisa."),
    _esquema("listar_pesquisas", "Lista as pesquisas persistidas.",
             {"limite": {"type": "integer", "description": "padrao 10"}}),
    _esquema("obter_pesquisa",
             "Dados de uma pesquisa (pergunta, contaminante, aplicacao, "
             "materiais). Sem id, usa a mais recente.",
             {"pesquisa_id": _P_PESQUISA}),
    _esquema("listar_materiais",
             "Materiais da pesquisa (ou do catalogo, com busca).",
             {"pesquisa_id": _P_PESQUISA,
              "busca": {"type": "string"},
              "limite": {"type": "integer", "description": "padrao 20"}}),
    _esquema("descritores_material",
             "Os 28 descritores 7Dx4 do material com valor, unidade, estado e "
             "quais estao ausentes.", {"material_id": _P_MATERIAL},
             ["material_id"]),
    _esquema("caracterizacao_componentes",
             "Caracterizacao real dos quatro componentes (adsorbato, "
             "adsorvente, interface, meio): parametros com valor e os que faltam.",
             {"material_id": _P_MATERIAL, "componente": _P_COMPONENTE,
              "pesquisa_id": _P_PESQUISA}, ["material_id"]),
    _esquema("catalogo_parametros",
             "Catalogo de parametros aceitos por componente (chave, unidade, "
             "descritor que alimenta).", {"componente": _P_COMPONENTE}),
    _esquema("explicar_descritor",
             "Definicao, unidade, regra, cruzamentos, simuladores e modelos de "
             "um descritor (codigo S1..S7, P1..P7, T1..T7, C1..C7).",
             {"codigo": {"type": "string"}}, ["codigo"]),
    _esquema("estrutura_matriz",
             "Estrutura do metodo: 7 dimensoes x 4 componentes = 28 "
             "cruzamentos, com os descritores e parametros de cada celula."),
    _esquema("matriz_montada",
             "Matriz 7Dx4 montada com o dado real: cobertura, lacunas, pesos, "
             "indice de qualidade e indice comparativo por cruzamento.",
             {"material_id": _P_MATERIAL, "pesquisa_id": _P_PESQUISA}),
    _esquema("simuladores",
             "Simuladores registrados no motor e quais estao disponiveis."),
    _esquema("requisitos_simulador",
             "Requisitos de um simulador preenchidos com o dado do material: "
             "o que ja existe, o que falta e o estado.",
             {"simulador": {"type": "string"}, "material_id": _P_MATERIAL,
              "pesquisa_id": _P_PESQUISA}, ["simulador"]),
    _esquema("resultados_simulacoes",
             "Execucoes de simulador ja registradas na pesquisa, com resultado "
             "real (ou o erro).", {"pesquisa_id": _P_PESQUISA,
                                   "limite": {"type": "integer"}}),
    _esquema("relatorios_pesquisa",
             "Relatorios gerados para a pesquisa (tipo, formato, tamanho).",
             {"pesquisa_id": _P_PESQUISA}),
    _esquema("resumo_pesquisa",
             "Resumo completo da pesquisa: protocolo, materiais, evidencias, "
             "simulacoes, viabilidade e prova de conceito.",
             {"pesquisa_id": _P_PESQUISA}),
    _esquema("historico_recente",
             "Trilha de auditoria recente (o que foi criado, alterado, "
             "executado).", {"pesquisa_id": _P_PESQUISA,
                             "limite": {"type": "integer"}}),
]


def executar_ferramenta(nome: str, argumentos) -> dict:
    """Executa a ferramenta pedida pelo modelo; erro volta como dado, nao 500."""
    funcao = REGISTRO.get(str(nome or "").strip())
    if funcao is None:
        return {"erro": "ferramenta desconhecida: %s" % nome}
    if isinstance(argumentos, str):
        try:
            argumentos = json.loads(argumentos or "{}")
        except ValueError:
            return {"erro": "argumentos nao sao JSON valido"}
    if not isinstance(argumentos, dict):
        argumentos = {}
    try:
        return funcao(**argumentos)
    except TypeError as erro:
        return {"erro": "argumentos invalidos: %s" % _curto(erro, 160)}
    except Exception as erro:                              # noqa: BLE001
        return {"erro": _redigir("%s: %s" % (type(erro).__name__, erro))[:300]}


# --------------------------------------------------------------------- prompt
INSTRUCOES = """Voce e' a Luna, assistente tecnica da plataforma ALEF-TAV Ambiental \
(pesquisa de adsorcao e remediacao ambiental).

Regras que nao podem ser quebradas:
1. Nunca invente numero, propriedade, referencia, resultado de simulacao nem \
material. Todo dado que voce citar tem de vir de uma ferramenta chamada nesta \
conversa. Se a ferramenta nao trouxe, diga que o dado nao esta registrado.
2. Voce nao calcula ciencia. Quem calcula sao os modulos do backend: a matriz \
7Dx4 (`matriz_montada`), os simuladores (`resultados_simulacoes`) e os \
relatorios. Voce interpreta e explica o que eles devolveram.
3. Lacuna nao e' zero. Quando a ferramenta listar descritor ou parametro \
ausente, apresente como ausente e diga o que precisa ser medido/informado para \
preencher (a tela de caracterizacao e' o caminho).
4. Nao invente pesos: os pesos saem de entropia, redundancia e pertinencia \
calculadas pelo backend. Repita os valores devolvidos por `matriz_montada`.
5. Nao prometa execucao: voce orienta qual simulador rodar e com quais \
requisitos (`requisitos_simulador`); a execucao e' feita pela tela de \
simuladores e grava resultado real.
6. Antes de opinar sobre uma pesquisa, consulte: `obter_pesquisa`, \
`descritores_material`, `caracterizacao_componentes`, `matriz_montada`, \
`resultados_simulacoes`.
7. Responda em portugues do Brasil, direto, com listas curtas e citando os \
codigos dos descritores (S1..S7, P1..P7, T1..T7, C1..C7). Use markdown simples.
8. Voce nao tem acesso a chave da API, a secrets, a credenciais nem a arquivos \
fora desta API. Se pedirem isso, recuse em uma frase.
"""


def _sistema(pesquisa_id=None, material_id=None) -> str:
    contexto = ["Contexto da sessao:"]
    if pesquisa_id:
        contexto.append("- pesquisa ativa: %s" % pesquisa_id)
    if material_id:
        contexto.append("- material ativo: %s" % material_id)
    if len(contexto) == 1:
        contexto.append("- nenhuma pesquisa selecionada na interface")
    contexto.append("- data/hora UTC: %s" % db.agora_iso()[:19])
    return INSTRUCOES + "\n" + "\n".join(contexto)


# ------------------------------------------------------------------- historico
PAPEIS = {"user": "usuario", "assistant": "luna", "usuario": "usuario",
          "luna": "luna"}


def registrar(conversa_id: str, pesquisa_id, material_id, usuario: str,
              papel: str, conteudo: str, modelo: str = None,
              ferramentas=None, uso=None) -> str:
    """Grava uma mensagem da conversa, isolada por pesquisa e usuario."""
    sessao_db = db.sessao()
    try:
        sessao_db.add(db.ConversaLuna(
            id=db.novo_id("luna_msg") if papel == "usuario" else conversa_id,
            conversa_id=conversa_id,
            pesquisa_id=pesquisa_id or None,
            material_id=material_id or None,
            usuario=str(usuario or USUARIO_PADRAO),
            papel=papel,
            conteudo=str(conteudo or ""),
            modelo=modelo,
            ferramentas_json=db.json_dumps(ferramentas or []),
            uso_json=db.json_dumps(uso or {}),
        ))
        sessao_db.commit()
        return conversa_id
    finally:
        sessao_db.close()


def listar_historico(pesquisa_id: str = None, usuario: str = None,
                     limite: int = 50) -> dict:
    """Mensagens gravadas, sempre filtradas por pesquisa e usuario."""
    sessao_db = db.sessao()
    try:
        consulta = sessao_db.query(db.ConversaLuna)
        if pesquisa_id:
            consulta = consulta.filter(db.ConversaLuna.pesquisa_id == pesquisa_id)
        else:
            consulta = consulta.filter(db.ConversaLuna.pesquisa_id.is_(None))
        consulta = consulta.filter(
            db.ConversaLuna.usuario == str(usuario or USUARIO_PADRAO))
        total = consulta.count()
        linhas = (consulta.order_by(db.ConversaLuna.criado_em.desc())
                  .limit(max(1, min(int(limite or 50), 200))).all())
        mensagens = [{
            "id": item.id,
            "conversa_id": item.conversa_id,
            "papel": item.papel,
            "conteudo": item.conteudo,
            "modelo": item.modelo,
            "ferramentas": db.json_loads(item.ferramentas_json, []),
            "uso": db.json_loads(item.uso_json, {}),
            "quando": item.criado_em.isoformat() if item.criado_em else None,
        } for item in reversed(linhas)]
        return {"pesquisa_id": pesquisa_id, "usuario": str(usuario
                                                          or USUARIO_PADRAO),
                "total": total, "mensagens": mensagens}
    finally:
        sessao_db.close()


def limpar_historico(pesquisa_id: str = None, usuario: str = None) -> dict:
    sessao_db = db.sessao()
    try:
        consulta = sessao_db.query(db.ConversaLuna)
        if pesquisa_id:
            consulta = consulta.filter(db.ConversaLuna.pesquisa_id == pesquisa_id)
        else:
            consulta = consulta.filter(db.ConversaLuna.pesquisa_id.is_(None))
        consulta = consulta.filter(
            db.ConversaLuna.usuario == str(usuario or USUARIO_PADRAO))
        removidas = consulta.delete(synchronize_session=False)
        sessao_db.commit()
        return {"removidas": int(removidas or 0), "pesquisa_id": pesquisa_id,
                "usuario": str(usuario or USUARIO_PADRAO)}
    finally:
        sessao_db.close()


def total_historico() -> int:
    sessao_db = db.sessao()
    try:
        return int(sessao_db.query(db.ConversaLuna).count())
    except Exception:                                      # noqa: BLE001
        return 0
    finally:
        sessao_db.close()


def _contexto(pesquisa_id=None, usuario=None, enviado=None) -> list:
    """Mensagens antigas viram contexto: as do cliente ou as gravadas no banco."""
    itens = []
    if isinstance(enviado, list):
        for item in enviado[-LIMITE_HISTORICO:]:
            papel = PAPEIS.get(str(item.get("papel") or item.get("role") or ""))
            texto = str(item.get("conteudo") or item.get("content") or "").strip()
            if papel and texto:
                itens.append({"role": "user" if papel == "usuario"
                              else "assistant", "content": texto})
        return itens
    dados = listar_historico(pesquisa_id, usuario, LIMITE_HISTORICO)
    for item in dados["mensagens"]:
        itens.append({"role": "user" if item["papel"] == "usuario"
                      else "assistant", "content": item["conteudo"]})
    return itens


# ------------------------------------------------------------------ conversa
def conversar(mensagem, pesquisa_id=None, material_id=None, usuario=None,
              historico=None, modelo=None, gravar=True) -> dict:
    """Uma rodada completa: modelo -> ferramentas -> resposta com dado real.

    Nao existe caminho "sem ferramenta": mesmo que o modelo responda de
    primeira, ele recebe o esquema das 16 consultas e as instrucoes proibindo
    inventar. O que voltar em `ferramentas` e' a prova do que foi consultado.
    """
    texto = str(mensagem or "").strip()
    if not texto:
        raise LunaErro("mensagem vazia")
    if not configurada():
        raise LunaNaoConfigurada(
            "OPENAI_API_KEY nao configurada: a Luna nao pode responder. "
            "Defina o Secret no Space (Settings > Secrets) e reinicie.")
    escolha = resolver_modelo()
    alvo = str(modelo or "").strip() or escolha["modelo"]
    pesquisa_alvo = str(pesquisa_id or "").strip() or None
    material_alvo = str(material_id or "").strip() or None
    conversa_id = db.novo_id("luna")
    lista = [{"role": "system",
              "content": _sistema(pesquisa_alvo, material_alvo)}]
    lista.extend(_contexto(pesquisa_alvo, usuario, historico))
    lista.append({"role": "user", "content": texto})

    usadas, uso_total, resposta_texto, turnos = [], {}, "", 0
    for turno in range(1, max_turnos() + 1):
        turnos = turno
        dados = _http("POST", "/chat/completions", {
            "model": alvo,
            "messages": lista,
            "tools": ESQUEMAS,
            "tool_choice": "auto",
        })
        uso = dados.get("usage") or {}
        for chave, valor in uso.items():
            if isinstance(valor, (int, float)):
                uso_total[chave] = uso_total.get(chave, 0) + valor
        escolhas = dados.get("choices") or [{}]
        mensagem_modelo = (escolhas[0] or {}).get("message") or {}
        chamadas = mensagem_modelo.get("tool_calls") or []
        conteudo = mensagem_modelo.get("content") or ""
        if not chamadas:
            resposta_texto = str(conteudo).strip()
            break
        lista.append({"role": "assistant", "content": conteudo,
                      "tool_calls": chamadas})
        for chamada in chamadas[:8]:
            funcao = (chamada or {}).get("function") or {}
            nome = funcao.get("name")
            bruto = funcao.get("arguments")
            try:
                argumentos = json.loads(bruto or "{}")
            except ValueError:
                argumentos = {}
            resultado = executar_ferramenta(nome, argumentos)
            ok = not (isinstance(resultado, dict) and resultado.get("erro"))
            usadas.append({"ferramenta": nome, "argumentos": argumentos,
                           "ok": bool(ok),
                           "resumo": _resumo_resultado(resultado)})
            lista.append({"role": "tool",
                          "tool_call_id": chamada.get("id") or nome,
                          "name": nome,
                          "content": _json_seguro(resultado)})
        if conteudo and str(conteudo).strip():
            resposta_texto = str(conteudo).strip()      # resposta parcial
    if not resposta_texto:
        resposta_texto = ("Nao consegui fechar a resposta em %d rodadas de "
                          "consulta. Tente uma pergunta mais especifica "
                          "(por exemplo: 'mostre as lacunas do material X')."
                          % turnos)
    resposta_texto = _redigir(resposta_texto)
    if gravar:
        registrar(conversa_id, pesquisa_alvo, material_alvo, usuario, "usuario",
                  texto)
        registrar(conversa_id, pesquisa_alvo, material_alvo, usuario, "luna",
                  resposta_texto, alvo, usadas, uso_total)
    return {
        "configurada": True,
        "conversa_id": conversa_id,
        "resposta": resposta_texto,
        "modelo": alvo,
        "modelo_origem": escolha["origem"],
        "ferramentas": usadas,
        "total_ferramentas": len(usadas),
        "uso": uso_total,
        "turnos": turnos,
        "pesquisa_id": pesquisa_alvo,
        "material_id": material_alvo,
        "usuario": str(usuario or USUARIO_PADRAO),
        "gravado": bool(gravar),
    }


def _resumo_resultado(resultado) -> str:
    """Uma linha sobre o que a ferramenta devolveu (mostrada na interface)."""
    if not isinstance(resultado, dict):
        return "resultado recebido"
    if resultado.get("erro"):
        return _curto(resultado["erro"], 120)
    for chave in ("total", "total_cruzamentos", "total_parametros",
                  "total_registrados", "com_valor", "resposta"):
        if chave in resultado and resultado[chave] is not None:
            return "%s: %s" % (chave, _curto(resultado[chave], 60))
    if "cruzamentos" in resultado:
        return "%d cruzamentos" % len(resultado["cruzamentos"] or [])
    return _curto(", ".join(sorted(resultado))[:120] or "ok", 120)
