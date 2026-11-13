# -*- coding: utf-8 -*-
"""Teste obrigatorio do adendo §7 — executado com os motores REAIS.

Dois materiais, nesta ordem:

    A) material de REFERENCIA INTERNA: parametros de Langmuir (qmax, KL) lidos
       do banco da plataforma (`experimentos` + `parametros_simulacao`), sem
       nenhum valor inventado;
    B) material DIFERENTE (zeolita 4A), com caracterizacao declarada apenas
       para exercitar o fluxo de integracao — rotulada como dado de teste.

Para cada material o script executa o caminho completo: simuladores reais ->
descritores na matriz -> modelos de adsorcao -> evidencias -> comparacao com a
literatura -> compatibilidade -> lacunas -> prova de conceito -> relatorio.

Uso (a partir da raiz do projeto)::

    python ambiental_backend/validar_adsorventes.py            # limpa no fim
    python ambiental_backend/validar_adsorventes.py --manter   # deixa gravado
    python ambiental_backend/validar_adsorventes.py --sem-rede # sem busca

Nada aqui e' simulado por duble: `ALEF_SEM_PREAQUECER=1` apenas evita o
pre-aquecimento dos motores no import (medido em `universal.py`).
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sqlite3
import sys

os.environ.setdefault("ALEF_SEM_PREAQUECER", "1")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

RAIZ = pathlib.Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from ambiental_backend import (adaptadores, adsorventes, config,  # noqa: E402
                               descritores_simuladores, matriz_7d4,
                               motor_pesquisa, relatorios)

PERGUNTA = ("adsorcao de chumbo em efluente com adsorvente de baixo custo: "
            "qual material remove Pb(II) com desempenho demonstravel?")

# Parametros usados se o banco da plataforma nao estiver acessivel.
REFERENCIA_PADRAO = {"qmax": 20.0, "KL": 0.5, "temperatura_C": 25.0,
                     "origem": "valor declarado no proprio script de teste"}


def parametros_de_referencia() -> dict:
    """Le qmax/KL do ultimo experimento de adsorcao gravado pela plataforma."""
    banco = RAIZ / "alef_tav.db"
    if not banco.is_file():
        return dict(REFERENCIA_PADRAO,
                    origem="banco da plataforma ausente; valor de teste")
    try:
        conexao = sqlite3.connect(str(banco))
        linhas = conexao.execute(
            "SELECT experimento_id, chave, valor FROM parametros_simulacao "
            "ORDER BY experimento_id DESC, id").fetchall()
        conexao.close()
    except sqlite3.Error as erro:
        return dict(REFERENCIA_PADRAO, origem="erro ao ler banco: %s" % erro)
    ultimo = {}
    for experimento_id, nome, valor in linhas:
        if experimento_id not in ultimo:
            ultimo[experimento_id] = {}
        try:
            ultimo[experimento_id][nome] = float(str(valor).replace(",", "."))
        except (TypeError, ValueError):
            continue
    for experimento_id in sorted(ultimo, reverse=True):
        dados = ultimo[experimento_id]
        if "qmax" in dados and "KL" in dados:
            return {"qmax": dados["qmax"], "KL": dados["KL"],
                    "temperatura_C": dados.get("temperatura_C"),
                    "experimento_id": experimento_id,
                    "origem": ("banco da plataforma (tabela "
                               "parametros_simulacao, experimento %s)"
                               % experimento_id)}
    return dict(REFERENCIA_PADRAO,
                origem="sem qmax/KL no banco; valor de teste")


def curva_langmuir(qmax: float, kl: float, concentracoes) -> list:
    """Pontos da isoterma de Langmuir (curva teorica, nao medicao)."""
    pontos = []
    for ce in concentracoes:
        pontos.append({"Ce": ce,
                       "qe": round(qmax * kl * ce / (1.0 + kl * ce), 6)})
    return pontos


def material_de_referencia(referencia: dict) -> dict:
    """Material A: parametros internos da plataforma, sem invencao de dado."""
    concentracoes = [1.0, 2.0, 5.0, 10.0, 20.0]
    return {
        "material": "carvao ativado - referencia interna da plataforma",
        "classe": "adsorvente de referencia",
        "origem": referencia["origem"],
        "caracterizacao": {
            "capacidade_adsorcao": {
                "valor": referencia["qmax"], "unidade": "mg/g",
                "origem": referencia["origem"],
                "metodo": "ajuste de Langmuir registrado na plataforma"},
            "kl": {"valor": referencia["KL"], "unidade": "L/mg",
                   "origem": referencia["origem"],
                   "metodo": "ajuste de Langmuir registrado na plataforma"},
        },
        "condicoes": {"pH": 5.5, "Ce": 10.0,
                      "temperatura_C": referencia.get("temperatura_C") or 25.0},
        "calculo": {"D6": {"C0": 100, "Ce": 20, "volume_L": 0.1,
                           "massa_g": 0.05}},
        "modelos": ["langmuir", "freundlich"],
        "parametros_modelo": {"freundlich": {"Kf": 6.0, "n": 2.5}},
        "simuladores": [],
    }


def material_diferente() -> dict:
    """Material B: adsorvente novo, com caracterizacao declarada para o teste.

    Os numeros abaixo servem para exercitar a integracao (rotulados como dado
    de teste na resposta). Eles NAO sao resultados experimentais.
    """
    return {
        "material": "zeolita 4A modificada (teste de integracao)",
        "formula": "Na12Al12Si12O48",
        "classe": "zeolita",
        "origem": "dados declarados para o teste de integracao do adendo §7",
        "composicao": [{"elemento": "Si", "fracao_massica": 0.21},
                       {"elemento": "Al", "fracao_massica": 0.20},
                       {"elemento": "Na", "fracao_massica": 0.17}],
        "caracterizacao": {
            "area_superficial": {"valor": 620, "unidade": "m2/g",
                                 "metodo": "BET N2", "origem": "teste"},
            "pzc": {"valor": 6.8, "unidade": "pH", "origem": "teste"},
            "densidade_real": {"valor": 2.0, "unidade": "g/cm3",
                               "origem": "teste"},
            "diametro_particula": {"valor": 90, "unidade": "nm",
                                   "origem": "teste"},
            "ctc": {"valor": 310, "unidade": "cmol/kg", "origem": "teste"},
            "grupos_funcionais": {"valor_texto": "Si-OH, Al-OH",
                                  "origem": "teste"},
        },
        "condicoes": {"pH": 5.0, "Ce": 10.0, "temperatura_C": 25.0},
        "calculo": {
            "D1": {"pontos": curva_langmuir(38.0, 0.35, [1.0, 2.0, 5.0,
                                                        10.0, 20.0])},
            "D3": {"pontos_cinetica": [
                {"t": 5, "qt": 18.0}, {"t": 15, "qt": 27.0},
                {"t": 30, "qt": 33.0}, {"t": 60, "qt": 36.0},
                {"t": 120, "qt": 37.2}]},
            "D6": {"C0": 50, "Ce": 12.5, "volume_L": 0.1, "massa_g": 0.1},
            "C7": {"volume_leito_m3": 0.012, "vazao_m3_h": 0.05},
            "C4": {"potencia_kW": 0.75, "tempo_h": 2.0, "massa_kg": 5.0},
            "C2": {"preco_kg": 45.0, "qmax_mg_g": 38.0},
        },
        "simuladores": ["superficie", "nano", "cfd", "dft"],
        "parametros_simulador": {"densidade": 1000, "velocidade": 0.01,
                                 "diametro": 0.005, "viscosidade": 1e-3,
                                 "material": "Si"},
        "modelos": ["langmuir", "pfo_cinetica"],
        "parametros_modelo": {"pfo_cinetica": {"k1": 0.08, "tempo": 30}},
    }


def _resumo_material(rotulo: str, validacao: dict, prova: dict = None) -> dict:
    simuladores = [{"simulador": item["simulador"],
                    "estado": item["estado"],
                    "descritores": [d["codigo"] for d in
                                    item.get("descritores") or []]}
                   for item in validacao["simuladores"]]
    modelos = [{"modelo": item["modelo"], "estado": item["estado"],
                "qe": item.get("qe"), "faltando": item.get("faltando")}
               for item in validacao["modelos"]]
    descritores = {item["codigo"]: {"valor": item.get("valor"),
                                    "unidade": item.get("unidade"),
                                    "estado": item.get("estado")}
                   for item in validacao["descritores"]}
    return {
        "rotulo": rotulo,
        "material": validacao["material"],
        "descritores": descritores,
        "simuladores": simuladores,
        "modelos": modelos,
        "compatibilidade": validacao["compatibilidade"]["veredito"],
        "lacunas": [item["codigo"] for item in
                    validacao["lacunas_experimentais"]],
        "preenchimento": validacao["preenchimento"]["percentual_com_dado"],
        "prova": (prova or {}).get("resultado", {}).get("demonstravel"),
    }


def _limpar(pesquisa_id: str, material_ids, inicio=None) -> dict:
    """Remove a pesquisa de teste e o que foi criado por ela (sem tocar no resto)."""
    from ambiental_backend import persistencia as db
    from ambiental_backend.persistencia import (Composicao, Comparacao,
                                                Descritor, Evidencia,
                                                Historico, Material, Pesquisa,
                                                PesquisaMaterial, Propriedade,
                                                Protocolo, ProvaConceito,
                                                Referencia, Relatorio,
                                                Simulacao, Tarefa, Viabilidade)

    sessao = db.sessao()
    removidos = {}
    try:
        evidencias = [item.id for item in sessao.query(Evidencia).filter(
            Evidencia.pesquisa_id == pesquisa_id).all()]
        if evidencias:
            removidos["referencias"] = sessao.query(Referencia).filter(
                Referencia.evidencia_id.in_(evidencias)).delete(
                    synchronize_session=False)
        for modelo in (Comparacao, Descritor, Evidencia, Simulacao, Viabilidade,
                       ProvaConceito, Relatorio, Protocolo, PesquisaMaterial,
                       Tarefa):
            removidos[modelo.__tablename__] = sessao.query(modelo).filter(
                modelo.pesquisa_id == pesquisa_id).delete(
                    synchronize_session=False)
        for material_id in material_ids or []:
            sessao.query(Propriedade).filter(
                Propriedade.material_id == material_id).delete(
                    synchronize_session=False)
            sessao.query(Composicao).filter(
                Composicao.material_id == material_id).delete(
                    synchronize_session=False)
            material = sessao.get(Material, material_id)
            if material is not None:
                sessao.delete(material)
        sessao.query(Historico).filter(
            Historico.detalhe_json.like('%%%s%%' % pesquisa_id)).delete(
                synchronize_session=False)
        if inicio is not None:
            # Trilha da propria execucao (alguns eventos nao citam o id).
            sessao.query(Historico).filter(
                Historico.quando >= inicio).delete(
                    synchronize_session=False)
        sessao.query(Pesquisa).filter(Pesquisa.id == pesquisa_id).delete(
            synchronize_session=False)
        sessao.commit()
    finally:
        sessao.close()
    return removidos


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manter", action="store_true",
                        help="nao apaga a pesquisa de teste no fim")
    parser.add_argument("--sem-rede", action="store_true",
                        help="pula a busca bibliografica real")
    parser.add_argument("--json", dest="saida", default=None,
                        help="grava o resumo em arquivo JSON")
    args = parser.parse_args(argv)

    print("banco:", config.instantaneo()["dados"])
    referencia = parametros_de_referencia()
    print("referencia interna:", json.dumps(referencia, ensure_ascii=False))

    from ambiental_backend import persistencia as db

    inicio = db._agora()
    pesquisa = motor_pesquisa.criar({
        "pergunta": PERGUNTA, "titulo": "Validacao de adsorventes (adendo §7)",
        "material": None, "contaminante": "chumbo", "aplicacao": "efluente",
        "condicoes": {"Ce": 10.0, "pH": 5.5, "temperatura_C": 25.0}})
    pesquisa_id = pesquisa["id"]
    print("pesquisa:", pesquisa_id)
    protocolo = motor_pesquisa.montar_protocolo(pesquisa_id, {})

    evidencias = {"estado": "nao_executado"}
    if not args.sem_rede:
        try:
            evidencias = motor_pesquisa.buscar_evidencias_pesquisa(
                pesquisa_id, n=2, max_bases=3)
        except Exception as erro:                       # noqa: BLE001
            evidencias = {"erro": "%s: %s" % (type(erro).__name__, erro)}
    print("evidencias:", evidencias.get("novas", evidencias.get("erro")))

    validacao_a = adsorventes.validar(pesquisa_id, material_de_referencia(
        referencia))
    print("material A:", validacao_a["material"]["nome"])
    validacao_b = adsorventes.validar(pesquisa_id, material_diferente())
    print("material B:", validacao_b["material"]["nome"])

    comparacao = validacao_b["comparacao_literatura"]
    viabilidade = motor_pesquisa.avaliar_viabilidade(pesquisa_id)
    prova_b = motor_pesquisa.prova_de_conceito(
        pesquisa_id, validacao_b["material"]["id"],
        {"simuladores": ["superficie", "nano", "cfd", "dft"],
         "modelos": ["langmuir", "pfo_cinetica"]})

    relatorio_md = relatorios.gerar(pesquisa_id, "viabilidade", "md")
    try:
        relatorio_pdf = relatorios.gerar(pesquisa_id, "viabilidade", "pdf")
    except Exception as erro:                           # noqa: BLE001
        relatorio_pdf = {"erro": "%s: %s" % (type(erro).__name__, erro)}

    painel = descritores_simuladores.catalogo(
        motor_pesquisa.historico_simulacoes(500, pesquisa_id))
    resumo = {
        "pesquisa_id": pesquisa_id,
        "referencia_interna": referencia,
        "protocolo": {"descritores": len(protocolo["descritores"]),
                      "simuladores": len(protocolo["simuladores"])},
        "evidencias": {chave: evidencias.get(chave)
                       for chave in ("estado", "novas", "erro")},
        "material_a": _resumo_material("referencia interna", validacao_a),
        "material_b": _resumo_material("material diferente", validacao_b,
                                       prova_b),
        "comparacao_literatura": {"total": comparacao.get("total", 0),
                                  "concordantes": comparacao.get("concordantes", 0),
                                  "estado": comparacao.get("estado")},
        "viabilidade": {"pontuacao": viabilidade["pontuacao"],
                        "classificacao": viabilidade["classificacao"],
                        "lacunas": len(viabilidade["lacunas"])},
        "prova_de_conceito": {"estado": prova_b["estado"],
                              "passos_ok": prova_b["resultado"]["passos_ok"],
                              "passos_total": prova_b["resultado"]["passos_total"],
                              "lacunas": prova_b["resultado"]["lacunas"]},
        "simuladores_no_painel": {"total": painel["total"],
                                  "disponiveis": painel["disponiveis"],
                                  "com_descritor": painel["com_descritor"]},
        "relatorios": {
            "md": relatorio_md.get("tamanho_bytes"),
            "pdf": relatorio_pdf.get("tamanho_bytes")
                   if "erro" not in relatorio_pdf else relatorio_pdf["erro"],
        },
    }
    print(json.dumps(resumo, indent=2, ensure_ascii=False))
    if args.saida:
        pathlib.Path(args.saida).write_text(
            json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
        print("resumo gravado em:", args.saida)
    if not args.manter:
        removidos = _limpar(pesquisa_id, [validacao_a["material"]["id"],
                                          validacao_b["material"]["id"]],
                            inicio)
        print("limpeza: pesquisa de teste removida",
              json.dumps(removidos.get("amb_descritores", 0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

