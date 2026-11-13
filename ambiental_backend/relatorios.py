# -*- coding: utf-8 -*-
"""Geracao e armazenamento dos relatorios de pesquisa.

O relatorio e' montado a partir do que esta no banco (`motor_pesquisa.resumo`):
nada e' recalculado aqui e nada e' inventado. Formatos disponiveis dependendo
do que estiver instalado:

    md    sempre
    json  sempre
    pdf   reportlab (presente no ambiente de ciencia)
    docx  python-docx via `exportadores.texto_para_docx` (quando instalado)
"""
from __future__ import annotations

import json
import os

from . import config, motor_pesquisa
from . import persistencia as db
from .persistencia import Relatorio, json_dumps, json_loads, novo_id


class RelatorioNaoEncontrado(KeyError):
    """Identificador de relatorio inexistente."""


class FormatoIndisponivel(ValueError):
    """Formato pedido sem biblioteca instalada."""


def _tabela(cabecalho, linhas) -> str:
    saida = ["| " + " | ".join(str(c) for c in cabecalho) + " |",
             "|" + "|".join("---" for _ in cabecalho) + "|"]
    for linha in linhas:
        saida.append("| " + " | ".join(
            ("" if valor is None else str(valor)).replace("|", "/")
            for valor in linha) + " |")
    return "\n".join(saida)


def _fmt(valor) -> str:
    if valor is None:
        return "-"
    if isinstance(valor, float):
        return ("%.4f" % valor).rstrip("0").rstrip(".")
    return str(valor)


def _matriz_markdown(resumo) -> str:
    descritores = resumo.get("descritores") or []
    if not descritores:
        return ("_Nenhum descritor preenchido. A matriz 7Dx4 do material "
                "ainda esta vazia._")
    linhas = [(item["codigo"], item["dimensao"], item["nome"],
               _fmt(item.get("valor")), item.get("unidade") or "-",
               item.get("estado"), item.get("fonte") or "-")
              for item in sorted(descritores, key=lambda d: d["codigo"])]
    return _tabela(("Codigo", "Dim.", "Descritor", "Valor", "Unidade",
                    "Estado", "Fonte"), linhas)


def _dados_e_origens(resumo) -> str:
    partes = []
    for material in resumo.get("materiais") or []:
        partes.append("### %s" % material["nome"])
        if material.get("formula") or material.get("cas"):
            partes.append("- Formula: %s | CAS: %s"
                          % (material.get("formula") or "-",
                             material.get("cas") or "-"))
        if material.get("composicao"):
            partes.append(_tabela(
                ("Elemento", "Fracao m/m", "Origem"),
                [(c["elemento"], _fmt(c.get("fracao_massica")),
                  c.get("origem") or "-") for c in material["composicao"]]))
        if material.get("propriedades"):
            partes.append(_tabela(
                ("Propriedade", "Valor", "Unidade", "Origem", "Metodo"),
                [(p["nome"], _fmt(p.get("valor")), p.get("unidade") or "-",
                  p.get("origem") or "-", p.get("metodo") or "-")
                 for p in material["propriedades"]]))
        if not material.get("composicao") and not material.get("propriedades"):
            partes.append("_Sem composicao ou propriedades registradas._")
    return "\n\n".join(partes) or "_Nenhum material registrado._"


def _evidencias_markdown(resumo) -> str:
    evidencias = resumo.get("evidencias") or []
    if not evidencias:
        return "_Nenhuma evidencia recuperada._"
    linhas = [("[%d]" % (i + 1), item.get("titulo") or "-",
               item.get("ano") or "-", item.get("base") or "-",
               _fmt(item.get("relevancia")))
              for i, item in enumerate(evidencias)]
    blocos = [_tabela(("Ref", "Titulo", "Ano", "Base", "Relevancia"), linhas)]
    for i, item in enumerate(evidencias):
        referencia = ["[%d]" % (i + 1), item.get("titulo") or ""]
        if item.get("doi"):
            referencia.append("DOI: %s" % item["doi"])
        if item.get("link"):
            referencia.append(item["link"])
        blocos.append(" ".join(referencia))
    return "\n\n".join(blocos)


def _simulacoes_markdown(resumo) -> str:
    simulacoes = resumo.get("simulacoes") or []
    if not simulacoes:
        return "_Nenhuma simulacao executada._"
    linhas = [(s["simulador"], s.get("estado"), _fmt(s.get("duracao_s")),
               (s.get("erro") or "-")[:60]) for s in simulacoes]
    return _tabela(("Simulador", "Estado", "Duracao (s)", "Observacao"), linhas)


def _parametros_markdown(resumo) -> str:
    linhas = []
    for simulacao in resumo.get("simulacoes") or []:
        entrada = simulacao.get("parametros") or {}
        for chave, valor in (entrada.get("parametros") or {}).items():
            linhas.append((simulacao["simulador"], chave, _fmt(valor)))
    if not linhas:
        return "_Nenhum parametro de simulacao registrado._"
    return _tabela(("Simulador", "Parametro", "Valor"), linhas)


def _resultados_markdown(resumo) -> str:
    blocos = []
    executados = {"ok", "ok_com_aproximacao", "ok_sem_descritor"}
    for simulacao in resumo.get("simulacoes") or []:
        if simulacao.get("estado") not in executados:
            continue
        resultado = simulacao.get("resultado")
        rotulo = simulacao["simulador"]
        if simulacao.get("estado") == "ok_com_aproximacao":
            rotulo += " (aproximado: padrao interno do motor)"
        blocos.append("### %s\n\n```json\n%s\n```"
                      % (rotulo,
                         json.dumps(resultado, ensure_ascii=False,
                                    indent=2)[:1800]))
    prova = resumo.get("prova") or {}
    if prova.get("resultado"):
        blocos.append("### Prova de conceito\n\n```json\n%s\n```"
                      % json.dumps(prova["resultado"], ensure_ascii=False,
                                   indent=2)[:1500])
    return "\n\n".join(blocos) or "_Nenhum resultado computacional._"


def _comparacoes_markdown(resumo) -> str:
    comparacoes = resumo.get("comparacoes") or []
    if not comparacoes:
        return "_Nenhuma comparacao com a literatura registrada._"
    linhas = [(item["descritor"], _fmt(item["valor_calculado"]),
               item["unidade"], _fmt(item["valor_literatura"]),
               _fmt(item["desvio_relativo"]), item["veredito"],
               (item.get("fonte_literatura") or "-")[:70])
              for item in comparacoes]
    return _tabela(("Descr.", "Calculado", "Unidade", "Literatura", "Desvio",
                    "Veredito", "Fonte"), linhas)


def _viabilidade_markdown(resumo) -> str:
    viabilidade = resumo.get("viabilidade") or {}
    if not viabilidade:
        return "_Viabilidade nao avaliada._"
    partes = ["**Pontuacao:** %s (%s)"
              % (_fmt(viabilidade.get("pontuacao")),
                 viabilidade.get("classificacao")),
              _tabela(("Criterio", "Peso", "Fracao", "Contribuicao"),
                      [(c["chave"], c["peso"], _fmt(c["fracao"]),
                        _fmt(c["contribuicao"]))
                       for c in viabilidade.get("criterios") or []])]
    if viabilidade.get("lacunas"):
        partes.append("**Lacunas:** " + "; ".join(viabilidade["lacunas"]))
    if viabilidade.get("riscos"):
        partes.append("**Riscos:** " + "; ".join(viabilidade["riscos"]))
    if viabilidade.get("recomendacoes"):
        partes.append("**Recomendacoes:** "
                      + "; ".join(viabilidade["recomendacoes"]))
    return "\n\n".join(partes)


def _limitacoes(resumo) -> str:
    limitacoes = []
    preenchimento = resumo.get("preenchimento") or {}
    if preenchimento.get("sem_dado"):
        limitacoes.append("%d descritores da matriz sem dado medido."
                          % preenchimento["sem_dado"])
    if not (resumo.get("evidencias") or []):
        limitacoes.append("Nenhuma evidencia bibliografica recuperada.")
    falhas = [s["simulador"] for s in (resumo.get("simulacoes") or [])
              if s.get("estado") != "ok"]
    if falhas:
        limitacoes.append("Simuladores sem resultado: %s." % ", ".join(falhas))
    if not (resumo.get("comparacoes") or []):
        limitacoes.append("Sem comparacao numerica com a literatura.")
    limitacoes.append("Resultados computacionais nao substituem ensaio "
                      "experimental.")
    return "\n".join("- %s" % item for item in limitacoes)


def _conclusao(resumo) -> str:
    viabilidade = resumo.get("viabilidade") or {}
    prova = resumo.get("prova") or {}
    if not viabilidade:
        return ("_Viabilidade nao avaliada: execute POST "
                "/api/research/{id}/viability._")
    demonstravel = (prova.get("resultado") or {}).get("demonstravel")
    return ("A pesquisa esta classificada como **%s** com pontuacao %s de 100. "
            "Prova de conceito computacional: %s."
            % (viabilidade.get("classificacao"),
               _fmt(viabilidade.get("pontuacao")),
               "demonstravel" if demonstravel else "parcial"))


def _cruzamentos_markdown(resumo) -> str:
    """Os 28 cruzamentos 7x4: cobertura, indices e o que falta em cada celula."""
    matriz = resumo.get("cruzamentos") or {}
    cruzamentos = matriz.get("cruzamentos") or []
    if not cruzamentos:
        return ("_Matriz 7x4 nao montada: cadastre material e descritores para "
                "gerar os 28 cruzamentos._")
    linhas = []
    for celula in cruzamentos:
        extras = celula.get("extras") or {}
        linhas.append((
            celula.get("id"),
            "%s %s" % (celula.get("dimensao"), celula.get("dimensao_nome")),
            celula.get("componente_nome"),
            "%s/%s" % (extras.get("com_dado", 0),
                       extras.get("total_descritores", 0)),
            _fmt(extras.get("cobertura")),
            _fmt(extras.get("indice_qualidade")),
            _fmt(extras.get("indice_comparativo")),
            ", ".join(extras.get("lacunas") or []) or "-",
        ))
    resumo_matriz = matriz.get("resumo") or {}
    return "\n\n".join([
        _tabela(("Cruzamento", "Dimensao", "Componente", "Com dado",
                 "Cobertura", "Indice qualidade", "Indice comparativo",
                 "Lacunas"), linhas),
        ("Cobertura media dos 28 cruzamentos: %s. Cruzamentos com dado: %s de %s. "
         "Ausencia de dado nao recebe peso: a celula fica sem indice."
         % (_fmt(resumo_matriz.get("cobertura_media")),
            resumo_matriz.get("cruzamentos_com_dado"),
            resumo_matriz.get("cruzamentos"))),
    ])


def _pesos_markdown(resumo) -> str:
    """Peso de cada descritor dentro do cruzamento e o que o gerou."""
    matriz = resumo.get("cruzamentos") or {}
    linhas = []
    for celula in matriz.get("cruzamentos") or []:
        for item in celula.get("descritores") or []:
            if item.get("peso") in (None, 0):
                continue
            linhas.append((
                item.get("codigo"), item.get("nome"), celula.get("id"),
                item.get("estado"), _fmt(item.get("valor")),
                item.get("unidade") or "-", _fmt(item.get("peso")),
                _fmt(item.get("qualidade")), _fmt(item.get("pertinencia")),
                _fmt(item.get("utilidade")), _fmt(item.get("redundancia")),
            ))
    if not linhas:
        return "_Nenhum descritor com dado: nenhum peso atribuido._"
    metodo = matriz.get("metodo") or {}
    return "\n\n".join([
        _tabela(("Codigo", "Descritor", "Cruzamento", "Estado", "Valor",
                 "Unidade", "Peso", "Qualidade", "Pertinencia", "Utilidade",
                 "Redundancia"), linhas),
        ("Metodo: peso = %s; %s. %s."
         % (metodo.get("formula_peso"),
            metodo.get("normalizacao_peso"), metodo.get("ausencia"))),
    ])


def _componentes_markdown(resumo) -> str:
    """Caracterizacao dos quatro componentes: valor, unidade e origem."""
    dados = resumo.get("componentes") or {}
    blocos = []
    for bloco in dados.get("componentes") or []:
        linhas = [(item["nome"], _fmt(item.get("valor")),
                   item.get("valor_texto") or "-",
                   item.get("unidade") or item.get("unidade_registrada") or "-",
                   item.get("origem") or "-", item.get("estado"),
                   item.get("metodo") or "-")
                  for item in bloco.get("parametros") or []
                  if item.get("estado") != "ausente"]
        if not linhas:
            continue
        blocos.append("### %s — %s de %s parametros" %
                      (bloco.get("nome"), bloco.get("com_valor"),
                       bloco.get("total")))
        blocos.append(_tabela(("Parametro", "Valor", "Descricao", "Unidade",
                               "Origem", "Estado", "Metodo"), linhas))
    return "\n\n".join(blocos) or "_Nenhum parametro de componente registrado._"


def montar_markdown(resumo, tipo: str = "viabilidade") -> str:
    """Relatorio completo, na ordem exigida pelo fluxo de pesquisa."""
    pesquisa = resumo.get("pesquisa") or {}
    estrutura = resumo.get("estrutura_da_pergunta") or {}
    protocolo = resumo.get("protocolo") or {}
    preenchimento = resumo.get("preenchimento") or {}
    cabecalho = [
        "# Relatorio de %s — ALEF-TAV Ambiental" % tipo.replace("_", " "),
        "",
        "- **Pesquisa:** `%s`" % pesquisa.get("id"),
        "- **Material:** %s" % (pesquisa.get("material") or "-"),
        "- **Contaminante:** %s" % (pesquisa.get("contaminante") or "-"),
        "- **Aplicacao:** %s" % (pesquisa.get("aplicacao") or "-"),
        "- **Estado:** %s" % (pesquisa.get("estado") or "-"),
        "- **Gerado em:** %s" % resumo.get("gerado_em"),
    ]
    secoes = [
        ("1. Pergunta", "**%s**\n\n%s"
         % (pesquisa.get("pergunta") or "-",
            estrutura.get("pergunta_de_pesquisa")
            or "_Pergunta formal nao estruturada._")),
        ("2. Material", _dados_e_origens(resumo)),
        ("3. Matriz 7Dx4",
         "%s\n\nCobertura: %s de %s descritores com dado (%.2f%%)."
         % (_matriz_markdown(resumo),
            preenchimento.get("com_dado", 0),
            preenchimento.get("total_avaliado", 0),
            float(preenchimento.get("percentual_com_dado") or 0.0))),
        ("3.1 Cruzamentos 7 dimensoes x 4 componentes",
         _cruzamentos_markdown(resumo)),
        ("3.2 Peso dos descritores", _pesos_markdown(resumo)),
        ("3.3 Caracterizacao dos quatro componentes",
         _componentes_markdown(resumo)),
        ("4. Descritores selecionados",
         _tabela(("Codigo", "Descritor", "Unidade", "Motivo"),
                 [(d["codigo"], d["nome"], d["unidade"],
                   ", ".join(d.get("motivo") or []) or "-")
                  for d in protocolo.get("descritores") or []])
         if protocolo.get("descritores")
         else "_Protocolo nao montado._"),
        ("5. Dados e origens", _dados_e_origens(resumo)),
        ("6. Evidencias e referencias", _evidencias_markdown(resumo)),
        ("7. Simuladores", _simulacoes_markdown(resumo)),
        ("8. Parametros de entrada", _parametros_markdown(resumo)),
        ("9. Resultados", _resultados_markdown(resumo)),
        ("10. Comparacao com a literatura", _comparacoes_markdown(resumo)),
        ("11. Avaliacao de viabilidade", _viabilidade_markdown(resumo)),
        ("12. Limitacoes", _limitacoes(resumo)),
        ("13. Conclusao", _conclusao(resumo)),
        ("14. Recomendacoes",
         "\n".join("- %s" % item for item in
                   ((resumo.get("viabilidade") or {}).get("recomendacoes")
                    or ["Nenhuma recomendacao registrada."]))),
    ]
    corpo = ["\n".join(cabecalho)]
    for titulo, texto in secoes:
        corpo.append("## %s\n\n%s" % (titulo, texto))
    return "\n\n".join(corpo) + "\n"


def _pdf_bytes(texto: str, titulo: str) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        from xml.sax.saxutils import escape
    except ImportError as erro:                    # pragma: no cover
        raise FormatoIndisponivel("pdf indisponivel: reportlab ausente (%s)"
                                  % erro)

    import io

    buffer = io.BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=A4, title=titulo,
                                  author="ALEF-TAV Ambiental")
    estilos = getSampleStyleSheet()
    fluxo = []
    for linha in texto.splitlines():
        limpa = linha.rstrip()
        if not limpa.strip() or limpa.strip().startswith("```"):
            continue
        limpa = limpa.replace("|", " ").replace("**", "")
        if limpa.startswith("# "):
            fluxo.append(Paragraph(escape(limpa[2:]), estilos["Title"]))
        elif limpa.startswith("## "):
            fluxo.append(Paragraph(escape(limpa[3:]), estilos["Heading1"]))
        elif limpa.startswith("### "):
            fluxo.append(Paragraph(escape(limpa[4:]), estilos["Heading2"]))
        elif limpa.startswith("- "):
            fluxo.append(Paragraph("&bull; " + escape(limpa[2:]),
                                   estilos["BodyText"]))
        else:
            fluxo.append(Paragraph(escape(limpa), estilos["BodyText"]))
        fluxo.append(Spacer(1, 4))
    documento.build(fluxo)
    return buffer.getvalue()


def _docx_bytes(texto: str, titulo: str) -> bytes:
    try:
        import exportadores
    except Exception as erro:                       # noqa: BLE001
        raise FormatoIndisponivel("docx indisponivel: exportadores.py (%s)"
                                  % erro)
    conteudo = exportadores.texto_para_docx(texto, titulo)
    if not conteudo:
        raise FormatoIndisponivel("docx indisponivel: python-docx nao "
                                  "instalado neste ambiente")
    if isinstance(conteudo, str):
        with open(conteudo, "rb") as arquivo:
            return arquivo.read()
    return conteudo


EXTENSOES = {"md": "md", "markdown": "md", "json": "json", "pdf": "pdf",
             "docx": "docx"}


def gerar(pesquisa_id: str, tipo: str = "viabilidade",
          formato: str = "md", resumo: dict = None) -> dict:
    """Monta, grava e registra o relatorio."""
    tipo = (tipo or "viabilidade").strip().lower()
    formato = (formato or "md").strip().lower()
    if formato not in EXTENSOES:
        raise FormatoIndisponivel("formato nao suportado: %s (use %s)"
                                  % (formato, ", ".join(sorted(EXTENSOES))))
    if resumo is None:
        resumo = motor_pesquisa.resumo(pesquisa_id)
    texto = montar_markdown(resumo, tipo)
    titulo = "ALEF-TAV Ambiental — %s" % tipo

    if formato in ("md", "markdown"):
        dados = texto.encode("utf-8")
        conteudo_texto = texto
    elif formato == "json":
        conteudo_texto = json.dumps(resumo, ensure_ascii=False, indent=2,
                                    default=str)
        dados = conteudo_texto.encode("utf-8")
    elif formato == "pdf":
        dados = _pdf_bytes(texto, titulo)
        conteudo_texto = texto
    else:
        dados = _docx_bytes(texto, titulo)
        conteudo_texto = texto

    identificador = novo_id("rel")
    extensao = EXTENSOES[formato]
    destino = config.diretorio_relatorios() / (
        "%s_%s_%s.%s" % (tipo, pesquisa_id, identificador, extensao))
    destino.write_bytes(dados)

    sessao_db = db.sessao()
    try:
        sessao_db.add(Relatorio(
            id=identificador, pesquisa_id=pesquisa_id, tipo=tipo,
            formato=extensao, caminho=str(destino),
            conteudo=conteudo_texto[:200000],
            tamanho_bytes=len(dados)))
        db.registrar_historico(sessao_db, "pesquisa", pesquisa_id,
                               "relatorio_gerado",
                               {"relatorio": identificador,
                                "formato": extensao})
        sessao_db.commit()
    finally:
        sessao_db.close()

    return {
        "id": identificador,
        "pesquisa_id": pesquisa_id,
        "tipo": tipo,
        "formato": extensao,
        "arquivo": str(destino),
        "tamanho_bytes": len(dados),
        "url": "/api/reports/%s/arquivo" % identificador,
        "inicio": texto[:400],
    }


def obter(relatorio_id: str, incluir_conteudo: bool = False) -> dict:
    sessao_db = db.sessao()
    try:
        registro = sessao_db.get(Relatorio, str(relatorio_id).strip())
        if registro is None:
            raise RelatorioNaoEncontrado("relatorio nao encontrado: %s"
                                         % relatorio_id)
        dados = {
            "id": registro.id,
            "pesquisa_id": registro.pesquisa_id,
            "tipo": registro.tipo,
            "formato": registro.formato,
            "arquivo": registro.caminho,
            "tamanho_bytes": registro.tamanho_bytes,
            "url": "/api/reports/%s/arquivo" % registro.id,
            "criado_em": (registro.criado_em.isoformat()
                          if registro.criado_em else None),
        }
        if incluir_conteudo:
            dados["conteudo"] = registro.conteudo
        return dados
    finally:
        sessao_db.close()


def caminho(relatorio_id: str) -> str:
    sessao_db = db.sessao()
    try:
        registro = sessao_db.get(Relatorio, str(relatorio_id).strip())
        if registro is None or not registro.caminho:
            raise RelatorioNaoEncontrado("arquivo do relatorio nao encontrado: "
                                         "%s" % relatorio_id)
        return registro.caminho
    finally:
        sessao_db.close()


def listar(pesquisa_id: str) -> dict:
    sessao_db = db.sessao()
    try:
        registros = (sessao_db.query(Relatorio)
                     .filter(Relatorio.pesquisa_id == pesquisa_id)
                     .order_by(Relatorio.criado_em.desc()).all())
        return {"pesquisa_id": pesquisa_id, "total": len(registros),
                "relatorios": [{
                    "id": item.id, "tipo": item.tipo,
                    "formato": item.formato, "arquivo": item.caminho,
                    "tamanho_bytes": item.tamanho_bytes,
                    "url": "/api/reports/%s/arquivo" % item.id,
                    "criado_em": (item.criado_em.isoformat()
                                  if item.criado_em else None),
                } for item in registros]}
    finally:
        sessao_db.close()


def excluir(relatorio_id: str) -> dict:
    """Remove o registro e o arquivo do relatorio."""
    sessao_db = db.sessao()
    caminho_arquivo = None
    try:
        registro = sessao_db.get(Relatorio, str(relatorio_id).strip())
        if registro is None:
            raise RelatorioNaoEncontrado("relatorio nao encontrado: %s"
                                        % relatorio_id)
        caminho_arquivo = registro.caminho
        pesquisa_id = registro.pesquisa_id
        sessao_db.delete(registro)
        db.registrar_historico(sessao_db, "pesquisa", pesquisa_id,
                               "relatorio_excluido",
                               {"relatorio": str(relatorio_id)})
        sessao_db.commit()
    except Exception:
        sessao_db.rollback()
        raise
    finally:
        sessao_db.close()
    removido = False
    if caminho_arquivo:
        try:
            os.unlink(caminho_arquivo)
            removido = True
        except OSError:
            removido = False
    return {"id": str(relatorio_id), "excluido": True,
            "arquivo_removido": removido}

