# -*- coding: utf-8 -*-
"""Rotas REST do backend ambiental (consumidas pelo frontend do Google AI Studio).

Todas as respostas sao JSON. Erros seguem o mesmo envelope
(`{"erro": {"codigo", "mensagem", "detalhes"}}`), tratado em `app.py`.
Simulacao e busca bibliografica longas vao para segundo plano e devolvem
`tarefa_id`; o estado e' consultavel em `GET /api/tasks/{id}`.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from . import (adaptadores, adsorventes, componentes, descritores_simuladores,
               luna, matriz_7d4, matriz_cruzamentos, medicoes, motor_pesquisa,
               motores_ambientais, persistencia_remota, relatorios, tarefas)
from . import persistencia as db

router = APIRouter(tags=["ambiental"])


# --------------------------------------------------------------------- modelos
class CondicoesEntrada(BaseModel):
    temperatura_C: float = None
    pH: float = None
    Ce: float = None
    C0: float = None
    dose_g_L: float = None
    volume_L: float = None
    tempo_min: float = None
    observacao: str = None


class PesquisaEntrada(BaseModel):
    pergunta: str
    titulo: str = None
    material: str = None
    contaminante: str = None
    aplicacao: str = None
    condicoes: CondicoesEntrada = None


class ProtocoloEntrada(BaseModel):
    aplicacao: str = None
    contaminante: str = None
    material: str = None
    limite_descritores: int = None
    limite_simuladores: int = None
    cobertura_minima: float = None
    tolerancia: float = None
    min_evidencias: int = None


class MaterialEntrada(BaseModel):
    nome: str
    formula: str = None
    cas: str = None
    classe: str = None
    origem: str = None
    observacao: str = None
    papel: str = None
    composicao: list = None
    propriedades: list = None


class DescritoresEntrada(BaseModel):
    calculo: dict = None
    valores: dict = None
    codigos: list = None
    estado: str = None
    fonte: str = None


class ComponenteEntrada(BaseModel):
    """Caracterizacao de um componente: um ou varios parametros de uma vez."""
    parametros: list = None
    item: dict = None
    chave: str = None
    valor: float = None
    valor_texto: str = None
    unidade: str = None
    origem: str = None
    metodo: str = None
    referencia: str = None
    estado: str = None
    pesquisa_id: str = None
    preencher_descritor: bool = True


class EvidenciaEntrada(BaseModel):
    termo: str = None
    bases: list = None
    n: int = 3
    max_bases: int = 4
    material_id: str = None


class SimulacaoEntrada(BaseModel):
    simuladores: list = None
    parametros: dict = None
    parametros_por_simulador: dict = None
    material_id: str = None
    pergunta: str = None
    sincrono: bool = False
    timeout_s: int = None


class ViabilidadeEntrada(BaseModel):
    tolerancia: float = 0.2


class AdsorventeEntrada(BaseModel):
    material_id: str = None
    material: str = None
    nome: str = None
    formula: str = None
    cas: str = None
    classe: str = None
    origem: str = None
    observacao: str = None
    papel: str = None
    contaminante: str = None
    caracterizacao: dict = None
    propriedades: list = None
    composicao: list = None
    condicoes: dict = None
    calculo: dict = None
    simuladores: list = None
    parametros_simulador: dict = None
    parametros_modelo: dict = None
    modelos: list = None
    pergunta: str = None
    tolerancia: float = None


class ProvaEntrada(BaseModel):
    material_id: str = None
    validacao: dict = None


class SimuladorExecucaoEntrada(BaseModel):
    parametros: dict = None
    pergunta: str = None
    pesquisa_id: str = None
    material_id: str = None
    requer_completo: bool = True


class RelatorioEntrada(BaseModel):
    tipo: str = "viabilidade"
    formato: str = "md"


class PesquisaAtualizacao(BaseModel):
    pergunta: str = None
    titulo: str = None
    material: str = None
    contaminante: str = None
    aplicacao: str = None
    estado: str = None
    condicoes: dict = None


class MaterialAtualizacao(BaseModel):
    nome: str = None
    formula: str = None
    cas: str = None
    classe: str = None
    origem: str = None
    observacao: str = None
    propriedades: list = None
    composicao: list = None


class MedicaoEntrada(BaseModel):
    tipo: str
    valor: float = None
    valor_texto: str = None
    unidade: str = None
    replicatas: list = None
    incerteza: float = None
    metodo: str = None
    instrumento: str = None
    condicoes: dict = None
    laboratorio: str = None
    operador: str = None
    data_medicao: str = None
    pesquisa_id: str = None


class MedicoesLote(BaseModel):
    medicoes: list


class LunaEntrada(BaseModel):
    """Uma pergunta para a Luna.

    `historico` e' opcional: sem ele o backend usa o que ja esta gravado em
    `amb_luna_conversas` para a mesma pesquisa e o mesmo usuario.
    """
    mensagem: str
    pesquisa_id: str = None
    material_id: str = None
    usuario: str = None
    historico: list = None
    modelo: str = None


class ParametroInvalido(ValueError):
    """Parametro de consulta fora do intervalo aceito."""


def _corpo(modelo):
    if modelo is None:
        return {}
    if hasattr(modelo, "model_dump"):
        return modelo.model_dump(exclude_none=True)
    return modelo.dict(exclude_none=True)


def _chamar(funcao, *args, **kwargs):
    """Executa e traduz excecao de dominio em HTTP com codigo estavel."""
    try:
        return funcao(*args, **kwargs)
    except (motor_pesquisa.PesquisaNaoEncontrada,
            relatorios.RelatorioNaoEncontrado,
            tarefas.TarefaNaoEncontrada) as erro:
        raise HTTPException(status_code=404, detail={
            "codigo": "nao_encontrado", "mensagem": str(erro)})
    except adaptadores.SimuladorDesconhecido as erro:
        raise HTTPException(status_code=404, detail={
            "codigo": "simulador_desconhecido", "mensagem": str(erro)})
    except (motor_pesquisa.DadosInvalidos, relatorios.FormatoIndisponivel,
            ParametroInvalido, componentes.ComponenteInvalido) as erro:
        raise HTTPException(status_code=400, detail={
            "codigo": "entrada_invalida", "mensagem": str(erro)})
    except adaptadores.MotorIndisponivel as erro:
        raise HTTPException(status_code=503, detail={
            "codigo": "motor_indisponivel", "mensagem": str(erro)})
    except luna.LunaNaoConfigurada as erro:
        raise HTTPException(status_code=503, detail={
            "codigo": "luna_nao_configurada", "mensagem": str(erro)})
    except luna.LunaIndisponivel as erro:
        raise HTTPException(status_code=502, detail={
            "codigo": "luna_indisponivel", "mensagem": str(erro)})
    except luna.LunaErro as erro:
        raise HTTPException(status_code=400, detail={
            "codigo": "luna_entrada_invalida", "mensagem": str(erro)})
    except KeyError as erro:
        raise HTTPException(status_code=404, detail={
            "codigo": "nao_encontrado", "mensagem": str(erro)})


# ---------------------------------------------------------------------- health
@router.get("/api/health", summary="Estado do backend, banco e motores")
def saude():
    from . import config

    try:
        esquema = db.resumo_esquema()
    except Exception as erro:                       # noqa: BLE001
        esquema = {"erro": str(erro), "registros": {}, "versao_esquema": []}
    try:
        ativas = len([t for t in tarefas.listar(limite=50)
                      if t["estado"] not in tarefas.ESTADOS_FINAIS])
    except Exception:                               # noqa: BLE001
        ativas = 0
    return {
        "estado": "ok",
        "servico": config.NOME_SERVICO,
        "versao": config.VERSAO,
        "config": config.instantaneo(),
        "banco": {
            "motor": esquema.get("motor"),
            "versao_esquema": esquema.get("versao_esquema"),
            "tabelas_ambiental": len(esquema.get("registros") or {}),
            "registros": esquema.get("registros"),
            "herdado_de_nucleo_dados": esquema.get("herdado_de_nucleo_dados"),
            "erro": esquema.get("erro"),
        },
        "motores": adaptadores.estado_motores(),
        "persistencia_remota": persistencia_remota.estado(),
        "matriz": {"dimensoes": len(matriz_7d4.DIMENSOES),
                   "descritores": len(matriz_7d4.DESCRITORES)},
        "tarefas_ativas": ativas,
    }


@router.post("/api/persistence/sync",
             summary="Grava agora o backup do banco (dataset do Hugging Face)")
def sincronizar_persistencia():
    """Forca o envio do snapshot; usado no reinicio e na validacao."""
    return persistencia_remota.enviar(forcar=True)


# ----------------------------------------------------------------------- matriz
@router.get("/api/matriz", summary="Matriz 7Dx4 completa (28 descritores)")
def matriz():
    """Cada descritor traz os simuladores/modelos que podem avalia-lo."""
    base = matriz_7d4.listar()
    fontes = {item["codigo"]: item
              for item in descritores_simuladores.mapa()["descritores"]}
    for descritor in base["descritores"]:
        fonte = fontes.get(descritor["codigo"]) or {}
        descritor["cobertura"] = fonte.get("cobertura")
        descritor["simuladores"] = fonte.get("simuladores") or []
        descritor["modelos"] = fonte.get("modelos") or []
        descritor["regra_automatica"] = fonte.get("regra")
        descritor["exige_ensaio"] = fonte.get("cobertura") == "sem_simulador"
    base["fontes"] = {
        "com_regra_matematica": sum(1 for d in fontes.values() if d["regra"]),
        "com_simulador": sum(1 for d in fontes.values() if d["simuladores"]),
        "sem_simulador": sum(1 for d in fontes.values()
                             if d["cobertura"] == "sem_simulador"),
    }
    return base


@router.get("/api/matriz/estrutura",
            summary="Estrutura 7x4: dimensoes, componentes, relacoes e parametros")
def matriz_estrutura():
    """Metodo completo: 7 dimensoes informacionais x 4 componentes = 28 cruzamentos."""
    base = matriz_cruzamentos.estrutura()
    base["componentes_parametros"] = componentes.catalogo()
    return base


def _valores_por_material(pesquisa_id: str = None,
                          material_id: str = None) -> dict:
    """`{material: {codigo: valor}}` — base da entropia e da redundancia."""
    ids = []
    if pesquisa_id:
        pesquisa = _chamar(motor_pesquisa.obter, pesquisa_id)
        ids = [item["id"] for item in pesquisa.get("materiais") or []]
    if material_id and material_id not in ids:
        ids.append(material_id)
    valores = {}
    for alvo in ids:
        try:
            dados = _chamar(motor_pesquisa.descritores_do_material, alvo)
        except Exception:                                  # noqa: BLE001
            continue
        valores[alvo] = {item["codigo"]: item.get("valor")
                         for item in dados.get("descritores") or []
                         if item.get("valor") is not None}
    return valores


@router.get("/api/matriz/cruzamentos",
            summary="Matriz 7Dx4 montada com o dado real do material")
def matriz_cruzamentos_rota(material_id: str = None, pesquisa_id: str = None,
                            aplicacao: str = None,
                            incluir_parametros: bool = True):
    """Monta a matriz 7Dx4 do material: descritores, pesos, indices e lacunas.

    A matriz e' dinamica: so' entra descritor que existe. Celula sem dado volta
    com `lacunas` e sem indice — nunca com zero.
    """
    linha_material = None
    pergunta = None
    if material_id:
        linha_material = _chamar(motor_pesquisa.descritores_do_material,
                                 material_id)
    if pesquisa_id:
        pesquisa = _chamar(motor_pesquisa.obter, pesquisa_id)
        pergunta = pesquisa.get("pergunta")
        aplicacao = aplicacao or pesquisa.get("aplicacao")
        if not material_id:
            materiais = pesquisa.get("materiais") or []
            if materiais:
                material_id = materiais[0]["id"]
                linha_material = _chamar(
                    motor_pesquisa.descritores_do_material, material_id)
    parametros = {}
    if material_id and incluir_parametros:
        parametros = _chamar(componentes.parametros_de, material_id,
                             pesquisa_id)
    valores = _valores_por_material(pesquisa_id, material_id)
    resultado = matriz_cruzamentos.montar(
        linhas=(linha_material or {}).get("descritores") or [],
        parametros=parametros, aplicacao=aplicacao, pergunta=pergunta,
        valores_por_material=valores, material_id=material_id)
    resultado["pesquisa_id"] = pesquisa_id
    resultado["material"] = (linha_material or {}).get("material")
    return resultado


@router.get("/api/matriz/exportar",
            summary="Exporta a matriz 7Dx4 (csv ou json)")
def matriz_exportar(material_id: str = None, pesquisa_id: str = None,
                    aplicacao: str = None, formato: str = "csv"):
    resultado = matriz_cruzamentos_rota(material_id=material_id,
                                        pesquisa_id=pesquisa_id,
                                        aplicacao=aplicacao)
    formato = str(formato or "csv").strip().lower()
    nome = "matriz_7dx4_%s" % ((material_id or pesquisa_id or "geral")
                               .replace("/", "-"))
    if formato == "json":
        return resultado
    if formato not in ("csv", "txt"):
        raise HTTPException(status_code=400, detail={
            "codigo": "formato_invalido",
            "mensagem": "formatos: csv ou json (recebido %s)" % formato})
    return PlainTextResponse(
        matriz_cruzamentos.exportar_csv(resultado), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="%s.csv"' % nome})


@router.get("/api/matriz/{codigo}", summary="Descritor pelo codigo (S1..C7)")
def matriz_descritor(codigo: str):
    descritor = matriz_7d4.obter(codigo)
    if descritor is None:
        raise HTTPException(status_code=404, detail={
            "codigo": "descritor_desconhecido",
            "mensagem": "codigo inexistente: %s" % codigo})
    return descritor


@router.post("/api/matriz/{codigo}/calcular",
             summary="Aplica a regra matematica do descritor")
def matriz_calcular(codigo: str, dados: dict = None):
    if matriz_7d4.obter(codigo) is None:
        raise HTTPException(status_code=404, detail={
            "codigo": "descritor_desconhecido",
            "mensagem": "codigo inexistente: %s" % codigo})
    return matriz_7d4.aplicar(codigo, dados or {})


# ----------------------------------------------------------------- componentes
@router.get("/api/componentes",
            summary="Catalogo dos quatro componentes e seus parametros")
def catalogo_componentes(componente: str = None):
    """Adsorbato, adsorvente, interface e meio: o que cada um aceita."""
    return _chamar(componentes.catalogo, componente)


@router.get("/api/materials/{material_id}/components",
            summary="Caracterizacao dos quatro componentes do material")
def componentes_do_material(material_id: str, pesquisa_id: str = None):
    return _chamar(componentes.listar, material_id, pesquisa_id)


@router.post("/api/materials/{material_id}/components/{componente}",
             status_code=201,
             summary="Grava a caracterizacao de um componente")
def gravar_componente(material_id: str, componente: str,
                      corpo: ComponenteEntrada = None):
    dados = _corpo(corpo)
    itens = dados.get("parametros")
    if not itens:
        item = dados.get("item") or {
            chave: dados.get(chave) for chave in
            ("chave", "valor", "valor_texto", "unidade", "origem", "metodo",
             "referencia", "estado") if dados.get(chave) is not None}
        itens = [item] if item else []
    if not itens:
        raise HTTPException(status_code=400, detail={
            "codigo": "entrada_invalida",
            "mensagem": "envie 'parametros' (lista) ou 'item'/'chave' + valor"})
    return _chamar(componentes.registrar, material_id, componente, itens,
                   dados.get("pesquisa_id"),
                   bool(dados.get("preencher_descritor", True)))


@router.delete("/api/materials/{material_id}/components/{componente}/{chave}",
               summary="Remove um parametro de caracterizacao")
def apagar_componente(material_id: str, componente: str, chave: str):
    return _chamar(componentes.apagar, material_id, componente, chave)


@router.get("/api/simulators/{nome}/parameters",
            summary="Preenche os requisitos do simulador com o dado do material")
def parametros_do_simulador(nome: str, material_id: str = None,
                            pesquisa_id: str = None):
    dados = _chamar(componentes.para_simulador, nome, material_id, pesquisa_id)
    if dados.get("tipo") in (None, "desconhecido"):
        raise HTTPException(status_code=404, detail={
            "codigo": "simulador_desconhecido",
            "mensagem": "sem requisitos declarados: %s" % nome})
    return dados


# ----------------------------------------------------------------- simuladores
@router.get("/api/simulators/catalog", summary="Catalogo real de simuladores")
def catalogo_simuladores():
    return _chamar(adaptadores.catalogo_simuladores)


@router.get("/api/simulators",
            summary="Painel: requisitos, descritores, estado e ultima execucao")
def painel_simuladores(somente_mapeados: bool = False,
                       pesquisa_id: str = None):
    historico = _chamar(motor_pesquisa.historico_simulacoes, 500, pesquisa_id)
    return descritores_simuladores.catalogo(historico,
                                            somente_mapeados=somente_mapeados)


@router.get("/api/simulators/{nome}",
            summary="Detalhe operacional de um simulador")
def detalhe_simulador(nome: str):
    catalogo = descritores_simuladores.catalogo(
        _chamar(motor_pesquisa.historico_simulacoes, 500))
    item = next((linha for linha in catalogo["simuladores"]
                 if linha["simulador"] == nome), None)
    if item is None:
        raise HTTPException(status_code=404, detail={
            "codigo": "simulador_desconhecido",
            "mensagem": "simulador fora do catalogo: %s" % nome})
    item["requisitos_detalhados"] = descritores_simuladores.requisitos_de(nome)
    item["estado_atual"] = descritores_simuladores.classificar(nome, {})
    return item


@router.get("/api/simulators/{nome}/requirements",
            summary="Requisitos de entrada (unidades e obrigatoriedade)")
def requisitos_simulador(nome: str):
    dados = descritores_simuladores.requisitos_de(nome)
    if dados.get("tipo") == "desconhecido":
        raise HTTPException(status_code=404, detail={
            "codigo": "simulador_desconhecido",
            "mensagem": "sem requisitos declarados: %s" % nome})
    return dados


@router.post("/api/simulators/{nome}/run",
             summary="Executa o simulador agora (grava se houver pesquisa)")
def executar_simulador_agora(nome: str,
                             corpo: SimuladorExecucaoEntrada = None):
    dados = _corpo(corpo)
    parametros = dados.get("parametros") or {}
    pesquisa_id = dados.get("pesquisa_id")
    if not pesquisa_id:
        saida = _chamar(descritores_simuladores.executar, nome, parametros,
                        dados.get("pergunta") or "",
                        bool(dados.get("requer_completo", True)), None)
        saida["persistido"] = False
        saida["aviso"] = ("sem pesquisa_id: resultado nao foi gravado no banco")
        return saida
    criadas = _chamar(motor_pesquisa.criar_simulacoes, pesquisa_id, {
        "simuladores": [nome], "parametros": parametros,
        "material_id": dados.get("material_id"),
        "pergunta": dados.get("pergunta")})
    if not criadas:
        raise HTTPException(status_code=400, detail={
            "codigo": "entrada_invalida", "mensagem": "simulacao nao criada"})
    saida = _chamar(motor_pesquisa.executar_simulacao, criadas[0]["id"])
    saida["persistido"] = True
    saida["estado"] = saida.get("estado") or "erro"
    return saida


@router.get("/api/descritores/simuladores",
            summary="Mapa descritor -> simuladores, modelos e regras")
def mapa_descritores():
    return descritores_simuladores.mapa()


@router.get("/api/descritores/{codigo}/fontes",
            summary="Fontes que calculam ou apoiam um descritor")
def fontes_descritor(codigo: str):
    for item in descritores_simuladores.mapa()["descritores"]:
        if item["codigo"] == str(codigo).strip().upper():
            return item
    raise HTTPException(status_code=404, detail={
        "codigo": "descritor_desconhecido",
        "mensagem": "codigo inexistente: %s" % codigo})


@router.get("/api/evidence/sources", summary="Inventario das bases cientificas")
def fontes_cientificas():
    return adaptadores.fontes()


# --------------------------------------------------------------------- pesquisa
@router.post("/api/research", status_code=201,
             summary="Cria a pesquisa (pergunta de pesquisa)")
def criar_pesquisa(corpo: PesquisaEntrada):
    return _chamar(motor_pesquisa.criar, _corpo(corpo))


@router.get("/api/research", summary="Lista as pesquisas (mais recente antes)")
def listar_pesquisas(limite: int = 50):
    pesquisas = _chamar(motor_pesquisa.listar, limite)
    return {"total": len(pesquisas), "pesquisas": pesquisas}


@router.get("/api/research/{pesquisa_id}", summary="Pesquisa completa")
def obter_pesquisa(pesquisa_id: str):
    return _chamar(motor_pesquisa.obter, pesquisa_id)


@router.patch("/api/research/{pesquisa_id}",
              summary="Edita titulo, pergunta, contaminante, aplicacao ou estado")
def atualizar_pesquisa(pesquisa_id: str, corpo: PesquisaAtualizacao = None):
    return _chamar(motor_pesquisa.atualizar, pesquisa_id, _corpo(corpo))


@router.get("/api/stats", summary="Indicadores reais do painel")
def estatisticas():
    """Contadores do dashboard: todos calculados no banco, sem dado fixo."""
    return _chamar(motor_pesquisa.estatisticas)


@router.get("/api/history", summary="Historico persistido (eventos, pesquisas, "
                                    "simulacoes, relatorios)")
def historico_geral(limite: int = 50, pesquisa_id: str = None):
    return _chamar(motor_pesquisa.historico, limite, pesquisa_id)


# -------------------------------------------------------------------- protocolo
@router.post("/api/research/{pesquisa_id}/protocol", status_code=201,
             summary="Monta protocolo: descritores, simuladores e criterios")
def montar_protocolo(pesquisa_id: str, corpo: ProtocoloEntrada = None):
    return _chamar(motor_pesquisa.montar_protocolo, pesquisa_id,
                   _corpo(corpo))


@router.get("/api/research/{pesquisa_id}/protocol",
            summary="Protocolo vigente da pesquisa")
def obter_protocolo(pesquisa_id: str):
    try:
        return motor_pesquisa.obter_protocolo(pesquisa_id)
    except motor_pesquisa.PesquisaNaoEncontrada as erro:
        if "protocolo inexistente" in str(erro):
            raise HTTPException(status_code=404, detail={
                "codigo": "protocolo_ausente",
                "mensagem": "monte o protocolo em POST "
                            "/api/research/%s/protocol" % pesquisa_id})
        raise HTTPException(status_code=404, detail={
            "codigo": "nao_encontrado", "mensagem": str(erro)})


# --------------------------------------------------------------------- materiais
@router.post("/api/research/{pesquisa_id}/materials", status_code=201,
             summary="Cadastra material, composicao e propriedades")
def adicionar_material(pesquisa_id: str, corpo: MaterialEntrada):
    return _chamar(motor_pesquisa.adicionar_material, pesquisa_id,
                   _corpo(corpo))


@router.get("/api/materials", summary="Catalogo de materiais")
def listar_materiais(busca: str = None, limite: int = 100):
    return {"materiais": _chamar(motor_pesquisa.listar_materiais, busca,
                                 limite)}


@router.get("/api/materials/{material_id}", summary="Material com dados e matriz")
def obter_material(material_id: str):
    return _chamar(motor_pesquisa.obter_material, material_id)


@router.patch("/api/materials/{material_id}",
              summary="Edita o material e faz merge de propriedades/composicao")
def atualizar_material(material_id: str, corpo: MaterialAtualizacao = None):
    return _chamar(motor_pesquisa.atualizar_material, material_id,
                   _corpo(corpo))


@router.get("/api/materials/{material_id}/descriptors",
            summary="Matriz 7Dx4 do material (28 linhas com estado)")
def descritores_do_material(material_id: str):
    return _chamar(motor_pesquisa.descritores_do_material, material_id)


@router.post("/api/research/{pesquisa_id}/materials/{material_id}/descriptors",
             summary="Preenche/atualiza descritores do material")
def preencher_descritores(pesquisa_id: str, material_id: str,
                          corpo: DescritoresEntrada = None):
    return _chamar(motor_pesquisa.preencher_descritores, pesquisa_id,
                   material_id, _corpo(corpo))


@router.post("/api/materials/{material_id}/descriptors",
             summary="Atalho: preenche descritores informando pesquisa_id")
def preencher_descritores_atalho(material_id: str, pesquisa_id: str,
                                 corpo: DescritoresEntrada = None):
    if not pesquisa_id:
        raise HTTPException(status_code=400, detail={
            "codigo": "entrada_invalida",
            "mensagem": "informe pesquisa_id (query) ou use a rota aninhada"})
    return _chamar(motor_pesquisa.preencher_descritores, pesquisa_id,
                   material_id, _corpo(corpo))


# -------------------------------------------------------------------- evidencias
@router.get("/api/research/{pesquisa_id}/evidence",
            summary="Evidencias ja recuperadas para a pesquisa")
def listar_evidencias(pesquisa_id: str):
    return _chamar(motor_pesquisa.listar_evidencias, pesquisa_id)


@router.post("/api/research/{pesquisa_id}/evidence/search",
             summary="Busca nas bases cientificas e persiste as novas")
def buscar_evidencias(pesquisa_id: str, corpo: EvidenciaEntrada = None):
    dados = _corpo(corpo)
    return _chamar(motor_pesquisa.buscar_evidencias_pesquisa, pesquisa_id,
                   dados.get("termo"), dados.get("bases"),
                   int(dados.get("n") or 3), int(dados.get("max_bases") or 4),
                   dados.get("material_id"))


# -------------------------------------------------------------------- simulacoes
@router.post("/api/research/{pesquisa_id}/simulations", status_code=202,
             summary="Enfileira (ou executa, com sincrono=true) simuladores")
def criar_simulacoes(pesquisa_id: str, corpo: SimulacaoEntrada = None):
    dados = _corpo(corpo)
    criadas = _chamar(motor_pesquisa.criar_simulacoes, pesquisa_id, {
        chave: dados.get(chave) for chave in
        ("simuladores", "parametros", "parametros_por_simulador",
         "material_id", "pergunta") if dados.get(chave) is not None})
    if not criadas:
        return {"pesquisa_id": pesquisa_id, "total": 0, "simulacoes": [],
                "aviso": "nenhum simulador selecionado"}
    if dados.get("sincrono"):
        executadas = []
        for simulacao in criadas:
            executadas.append(_chamar(motor_pesquisa.executar_simulacao,
                                      simulacao["id"]))
        return {"pesquisa_id": pesquisa_id, "sincrono": True,
                "total": len(executadas), "simulacoes": executadas}
    tarefas_criadas = []
    for simulacao in criadas:
        tarefa = tarefas.registrar(pesquisa_id, "simulacao")
        motor_pesquisa.marcar_tarefa(simulacao["id"], tarefa["id"])
        tarefas.iniciar(tarefa["id"], motor_pesquisa.executar_simulacao,
                        simulacao["id"])
        tarefas_criadas.append(tarefa["id"])
    return {"pesquisa_id": pesquisa_id, "sincrono": False,
            "total": len(criadas), "tarefa_ids": tarefas_criadas,
            "simulacoes": criadas,
            "acompanhar": ("/api/tasks/%s" % tarefas_criadas[0]
                           if tarefas_criadas else None)}


@router.get("/api/research/{pesquisa_id}/simulations",
            summary="Lista simulacoes e seus estados")
def listar_simulacoes(pesquisa_id: str):
    return _chamar(motor_pesquisa.listar_simulacoes, pesquisa_id)


@router.get("/api/research/{pesquisa_id}/simulations/{simulacao_id}",
            summary="Detalhe de uma simulacao (resultado, erro, duracao)")
def obter_simulacao(pesquisa_id: str, simulacao_id: str):
    return _chamar(motor_pesquisa.obter_simulacao, pesquisa_id, simulacao_id)


# -------------------------------------------------------------------- viabilidade
@router.post("/api/research/{pesquisa_id}/viability",
             summary="Avalia viabilidade (6 criterios ponderados)")
def avaliar_viabilidade(pesquisa_id: str, corpo: ViabilidadeEntrada = None):
    dados = _corpo(corpo)
    tolerancia = float(dados.get("tolerancia") or 0.2)
    try:
        motor_pesquisa.comparar_com_literatura(pesquisa_id, tolerancia)
    except motor_pesquisa.DadosInvalidos:
        pass                       # sem evidencia/descritor ainda: segue
    return _chamar(motor_pesquisa.avaliar_viabilidade, pesquisa_id)


@router.get("/api/research/{pesquisa_id}/viability",
            summary="Ultima avaliacao de viabilidade")
def obter_viabilidade(pesquisa_id: str):
    return _chamar(motor_pesquisa.obter_viabilidade, pesquisa_id)


# ------------------------------------------------------- validacao adsorvente
@router.post("/api/research/{pesquisa_id}/adsorbent", status_code=201,
             summary="Valida adsorvente: simuladores, matriz, modelos, lacunas")
def validar_adsorvente(pesquisa_id: str, corpo: AdsorventeEntrada = None):
    dados = _corpo(corpo)
    if not dados.get("material_id") and not (dados.get("material")
                                             or dados.get("nome")):
        raise HTTPException(status_code=400, detail={
            "codigo": "entrada_invalida",
            "mensagem": "informe 'material_id' ou o nome do material"})
    return _chamar(adsorventes.validar, pesquisa_id, dados)


@router.get("/api/research/{pesquisa_id}/adsorbent",
            summary="Ultima validacao de adsorvente gravada")
def obter_ultima_validacao(pesquisa_id: str):
    return _chamar(adsorventes.obter_validacao, pesquisa_id)


@router.get("/api/research/{pesquisa_id}/adsorbent/{material_id}",
            summary="Validacao de um material especifico")
def obter_validacao_material(pesquisa_id: str, material_id: str):
    return _chamar(adsorventes.obter_validacao, pesquisa_id, material_id)


# ----------------------------------------------------------------- prova conceito
@router.post("/api/research/{pesquisa_id}/proof-of-concept",
             summary="Executa a prova de conceito computacional")
def prova_de_conceito(pesquisa_id: str, corpo: ProvaEntrada = None):
    dados = _corpo(corpo)
    return _chamar(motor_pesquisa.prova_de_conceito, pesquisa_id,
                   dados.get("material_id"), dados.get("validacao"))


@router.get("/api/research/{pesquisa_id}/proof-of-concept",
            summary="Ultima prova de conceito")
def obter_prova(pesquisa_id: str):
    return _chamar(motor_pesquisa.obter_prova, pesquisa_id)


# --------------------------------------------------------------------- relatorios
MEDIA_TYPES = {
    "md": "text/markdown; charset=utf-8",
    "json": "application/json",
    "pdf": "application/pdf",
    "docx": ("application/vnd.openxmlformats-officedocument"
             ".wordprocessingml.document"),
}


@router.post("/api/research/{pesquisa_id}/reports", status_code=201,
             summary="Gera relatorio (md, json, pdf, docx)")
def gerar_relatorio(pesquisa_id: str, corpo: RelatorioEntrada = None):
    dados = _corpo(corpo)
    return _chamar(relatorios.gerar, pesquisa_id,
                   dados.get("tipo") or "viabilidade",
                   dados.get("formato") or "md")


@router.get("/api/research/{pesquisa_id}/reports",
            summary="Relatorios gerados para a pesquisa")
def listar_relatorios(pesquisa_id: str):
    _chamar(motor_pesquisa.obter, pesquisa_id)
    return relatorios.listar(pesquisa_id)


@router.get("/api/reports/{relatorio_id}",
            summary="Metadados + conteudo (md/json) do relatorio")
def obter_relatorio(relatorio_id: str):
    return _chamar(relatorios.obter, relatorio_id, True)


@router.get("/api/reports/{relatorio_id}/arquivo",
            summary="Arquivo do relatorio para download")
def arquivo_relatorio(relatorio_id: str):
    caminho = _chamar(relatorios.caminho, relatorio_id)
    dados = _chamar(relatorios.obter, relatorio_id, False)
    return FileResponse(caminho,
                        media_type=MEDIA_TYPES.get(dados["formato"],
                                                   "application/octet-stream"),
                        filename=caminho.split("\\")[-1].split("/")[-1])


# ------------------------------------------------------------------------ tarefas
@router.get("/api/tasks/{tarefa_id}", summary="Estado da tarefa de background")
def obter_tarefa(tarefa_id: str):
    return _chamar(tarefas.obter, tarefa_id)


@router.get("/api/tasks", summary="Lista tarefas (opcional: por pesquisa)")
def listar_tarefas(pesquisa_id: str = None, limite: int = 50):
    registros = _chamar(tarefas.listar, pesquisa_id, limite)
    return {"total": len(registros), "tarefas": registros}
# --------------------------------------------------------------------- medidas
@router.get("/api/measurements/types",
            summary="Tipos de medicao aceitos (unidade, faixa e descritor)")
def tipos_medicao():
    return medicoes.catalogo()


@router.get("/api/engines",
            summary="Motores ambientais proprios (metodo, nivel de validacao)")
def motores_proprios():
    linhas = []
    for nome, meta in motores_ambientais.MOTORES.items():
        linhas.append({
            "motor": nome,
            "dominio": meta.get("dominio"),
            "tipo": meta.get("tipo"),
            "nivel_validacao": meta.get("nivel_validacao"),
            "natureza": meta.get("natureza"),
            "referencias": meta.get("referencias"),
            "requisitos": meta.get("requisitos"),
            "descritores": [{"codigo": item.get("codigo"),
                             "chave": item.get("chave"),
                             "unidade": item.get("unidade"),
                             "modo": item.get("modo")}
                            for item in (meta.get("produz") or [])],
        })
    return {"total": len(linhas), "versao": motores_ambientais.VERSAO_REGISTRO,
            "motores": linhas}


@router.post("/api/materials/{material_id}/measurements", status_code=201,
             summary="Registra medicao experimental e preenche o descritor")
def registrar_medicao(material_id: str, corpo: MedicaoEntrada):
    return _chamar(medicoes.registrar, material_id, _corpo(corpo))


@router.post("/api/materials/{material_id}/measurements/batch",
             summary="Registra lote de medicoes (erro em uma nao derruba o lote)")
def registrar_medicoes_lote(material_id: str, corpo: MedicoesLote):
    return _chamar(medicoes.registrar_lote, material_id,
                   _corpo(corpo).get("medicoes") or [])


@router.get("/api/materials/{material_id}/measurements",
            summary="Medicoes registradas do material")
def listar_medicoes_material(material_id: str, limite: int = 100):
    return _chamar(medicoes.listar, material_id, None, limite)


@router.get("/api/materials/{material_id}/measurements/summary",
            summary="Cobertura de medicao por descritor do material")
def resumo_medicoes_material(material_id: str):
    return _chamar(medicoes.resumo_material, material_id)


@router.get("/api/measurements", summary="Todas as medicoes registradas")
def listar_medicoes(pesquisa_id: str = None, limite: int = 100):
    return _chamar(medicoes.listar, None, pesquisa_id, limite)


@router.get("/api/measurements/{medicao_id}",
            summary="Detalhe de uma medicao (estatistica e condicoes)")
def obter_medicao(medicao_id: str):
    return _chamar(medicoes.obter, medicao_id)


@router.delete("/api/measurements/{medicao_id}",
               summary="Remove a medicao (o descritor permanece)")
def apagar_medicao(medicao_id: str):
    return _chamar(medicoes.apagar, medicao_id)


# -------------------------------------------------------------------- exclusoes
@router.delete("/api/materials/{material_id}",
               summary="Exclui o material e o que depende dele (cascata)")
def excluir_material(material_id: str):
    return _chamar(motor_pesquisa.excluir_material, material_id)


@router.delete("/api/research/{pesquisa_id}",
               summary="Exclui a pesquisa e seus registros (materiais ficam)")
def excluir_pesquisa(pesquisa_id: str):
    return _chamar(motor_pesquisa.excluir_pesquisa, pesquisa_id)


@router.delete("/api/reports/{relatorio_id}",
               summary="Exclui o relatorio e apaga o arquivo")
def excluir_relatorio(relatorio_id: str):
    return _chamar(relatorios.excluir, relatorio_id)


# ----------------------------------------------------------------------- luna
@router.get("/api/luna/status",
            summary="Estado da Luna: motor OpenAI, modelo e ferramentas")
def luna_status():
    """Diz com honestidade o que esta configurado.

    Sem `OPENAI_API_KEY` responde `configurada: false` e o `aviso` explica que
    falta o Secret — nenhuma resposta de conversa e' simulada.
    """
    return _chamar(luna.estado)


@router.post("/api/luna/chat",
             summary="Conversa com a Luna (OpenAI + dados reais do backend)")
def luna_chat(corpo: LunaEntrada = None):
    """Pergunta -> ferramentas que leem o banco -> resposta do modelo.

    A resposta traz `ferramentas`: a prova do que foi consultado. Se a chave
    nao estiver configurada volta 503 `luna_nao_configurada`; se a OpenAI
    falhar, 502 `luna_indisponivel`.
    """
    dados = _corpo(corpo)
    mensagem = str(dados.get("mensagem") or "").strip()
    if not mensagem:
        raise HTTPException(status_code=400, detail={
            "codigo": "entrada_invalida",
            "mensagem": "envie 'mensagem' com a pergunta para a Luna"})
    return _chamar(luna.conversar, mensagem,
                   dados.get("pesquisa_id"), dados.get("material_id"),
                   dados.get("usuario"), dados.get("historico"),
                   dados.get("modelo"))


@router.get("/api/luna/historico",
            summary="Historico da Luna por pesquisa e usuario")
def luna_historico(pesquisa_id: str = None, usuario: str = None,
                   limite: int = 60):
    return _chamar(luna.listar_historico, pesquisa_id, usuario, limite)


@router.delete("/api/luna/historico",
               summary="Apaga o historico da Luna da pesquisa/usuario")
def luna_limpar(pesquisa_id: str = None, usuario: str = None):
    return _chamar(luna.limpar_historico, pesquisa_id, usuario)

