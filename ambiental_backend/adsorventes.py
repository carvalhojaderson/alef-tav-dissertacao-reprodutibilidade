# -*- coding: utf-8 -*-
"""Validacao computacional de materiais adsorventes (adendo §3 e §4).

Entrada: um material (novo ou ja cadastrado) + a caracterizacao declarada.
Saida: descritores da matriz 7Dx4 atualizados, simuladores executados,
modelos de adsorcao aplicados quando os requisitos existem, comparacao com a
literatura recuperada e lista de lacunas experimentais.

Principios (os mesmos do restante do backend):

* nenhuma propriedade nova e' criada como descritor: cada dado de
  caracterizacao e' mapeado para um dos 28 descritores oficiais ou fica
  registrado como propriedade do material sem virar descritor (`nao_mapeadas`);
* simulador so roda quando as entradas obrigatorias existem — caso contrario a
  resposta diz `bloqueado_por_parametros` e o que falta;
* valor calculado por modelo nao e' apresentado como medicao experimental:
  `nivel_evidencia` acompanha cada bloco.
"""
from __future__ import annotations

from . import adaptadores, descritores_simuladores
from . import matriz_7d4
from . import persistencia as db
from .persistencia import (Composicao, Comparacao, Descritor, Evidencia,
                           Material, Pesquisa, PesquisaMaterial, Propriedade,
                           Simulacao, agora_iso, json_dumps, json_loads,
                           novo_id, registrar_historico)

# ---------------------------------------------------------------------------
# Propriedades de caracterizacao -> descritor oficial.
# A chave canonica e' normalizada (minuscula, sem acento, sem espaco/underscore).
# Nenhum item aqui cria descritor: todos apontam para um dos 28 codigos.
# ---------------------------------------------------------------------------
CARACTERIZACAO = {
    "composicaoelementar": {"codigo": "S1", "unidade": "% m/m"},
    "pureza": {"codigo": "S1", "unidade": "% m/m"},
    "fasecristalina": {"codigo": "S2", "unidade": "texto"},
    "cristalinidade": {"codigo": "S2", "unidade": "%"},
    "areasuperficial": {"codigo": "S3", "unidade": "m2/g"},
    "areabet": {"codigo": "S3", "unidade": "m2/g"},
    "areab": {"codigo": "S3", "unidade": "m2/g"},
    "volumedeporos": {"codigo": "S4", "unidade": "cm3/g"},
    "volumeporos": {"codigo": "S4", "unidade": "cm3/g"},
    "porosidade": {"codigo": "S4", "unidade": "adimensional"},
    "diametrodeporo": {"codigo": "S4", "unidade": "nm"},
    "tamanhodeparticula": {"codigo": "S5", "unidade": "um"},
    "diametroparticula": {"codigo": "S5", "unidade": "um"},
    "d50": {"codigo": "S5", "unidade": "um"},
    "gruposfuncionais": {"codigo": "S6", "unidade": "texto"},
    "morfologia": {"codigo": "S7", "unidade": "texto"},
    "densidadereal": {"codigo": "P1", "unidade": "g/cm3"},
    "densidade": {"codigo": "P1", "unidade": "g/cm3"},
    "pzc": {"codigo": "P2", "unidade": "pH"},
    "pontodecargazero": {"codigo": "P2", "unidade": "pH"},
    "ctc": {"codigo": "P3", "unidade": "cmol/kg"},
    "capacidadedetrocaionica": {"codigo": "P3", "unidade": "cmol/kg"},
    "angulodecontato": {"codigo": "P4", "unidade": "graus"},
    "estabilidadetermica": {"codigo": "P5", "unidade": "graus C"},
    "bandgap": {"codigo": "P6", "unidade": "eV"},
    "condutividade": {"codigo": "P6", "unidade": "S/m"},
    "solubilidade": {"codigo": "P7", "unidade": "mg/L"},
    "lixiviacao": {"codigo": "P7", "unidade": "% m/m"},
    "qmax": {"codigo": "D1", "unidade": "mg/g"},
    "capacidadeadsorcao": {"codigo": "D1", "unidade": "mg/g"},
    "kl": {"codigo": "D2", "unidade": "L/mg"},
    "kf": {"codigo": "D2", "unidade": "(mg/g)(mg/L)^-1/n"},
    "k2pso": {"codigo": "D3", "unidade": "g/(mg*min)"},
    "seletividade": {"codigo": "D4", "unidade": "adimensional"},
    "regeneracao": {"codigo": "D5", "unidade": "%"},
    "remocao": {"codigo": "D6", "unidade": "%"},
    "eficienciaderemocao": {"codigo": "D6", "unidade": "%"},
    "qe": {"codigo": "D6", "unidade": "mg/g"},
    "faixadeph": {"codigo": "D7", "unidade": "pH"},
    "photimo": {"codigo": "D7", "unidade": "pH"},
    "toxicidade": {"codigo": "C1", "unidade": "categoria GHS"},
    "lc50": {"codigo": "C1", "unidade": "mg/L"},
    "preco": {"codigo": "C2", "unidade": "R$/kg"},
    "custokg": {"codigo": "C2", "unidade": "R$/kg"},
    "disponibilidade": {"codigo": "C3", "unidade": "t/ano"},
    "pegadaenergetica": {"codigo": "C4", "unidade": "kWh/kg"},
    "reciclabilidade": {"codigo": "C5", "unidade": "%"},
    "conformidade": {"codigo": "C6", "unidade": "mg/L"},
    "escalabilidade": {"codigo": "C7", "unidade": "m3/h"},
}


def _sem_acento(texto) -> str:
    import unicodedata

    base = unicodedata.normalize("NFKD", str(texto or "").lower())
    return "".join(c for c in base if not unicodedata.combining(c))


def _chave(nome) -> str:
    """Normaliza o nome da propriedade para consultar o mapa."""
    return "".join(c for c in _sem_acento(nome) if c.isalnum())


def mapear_propriedade(nome):
    """Descritor oficial correspondente ao nome da propriedade (ou None)."""
    return CARACTERIZACAO.get(_chave(nome))



# ---------------------------------------------------------------------------
# Compatibilidade adsorvente-adsorbato.
# Regra fisico-quimica explicita (nao e' ajuste empirico): em pH abaixo do PZC
# a superficie esta protonada (carga positiva) e atrai anions; acima do PZC a
# superficie e' desprotonada (carga negativa) e atrai cations.
# ---------------------------------------------------------------------------
CLASSES_CONTAMINANTE = {
    "cation_metalico": ("chumbo", "pb", "cadmio", "cd", "cobre", "cu", "niquel",
                        "ni", "zinco", "zn", "mercurio", "hg", "cromo iii",
                        "cr(iii)", "cobalto", "co", "manganes", "mn"),
    "oxianion": ("arsenio", "arsenato", "arsenito", "cromato", "cromo vi",
                 "cr(vi)", "nitrato", "fosfato", "sulfato", "fluoreto",
                 "borato", "selenato"),
    "cation_organico": ("azul de metileno", "corante cationico", "rodamina b",
                        "violeta cristal"),
    "anion_organico": ("alaranjado de metila", "corante anionico", "eosina",
                       "acido humico", "tensoativo anionico",
                       "sulfametoxazol", "sulfa", "antibiotico anionico"),
    "organico_neutro": ("farmaco", "antibiotico", "ibuprofeno", "diclofenaco",
                        "paracetamol", "pesticida", "glifosato", "atrazina",
                        "pfas", "pfoa", "pfos", "oleo", "diesel", "fenol"),
}

REGRA_COMPATIBILIDADE = (
    "pH < PZC: superficie protonada (carga positiva) favorece adsorcao de "
    "especies anionicas; pH > PZC: superficie desprotonada (carga negativa) "
    "favorece cations. |pH - PZC| e' a margem de carga efetiva."
)


def _pista_presente(texto: str, pista: str) -> bool:
    """Sigla curta (pb, cd, cu...) exige fronteira de palavra.

    Sem isso, 'carvao de coco' casaria 'co' (cobalto) e o contaminante seria
    classificado errado.
    """
    if len(pista) <= 3:
        import re

        padrao = r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(pista)
        return re.search(padrao, texto) is not None
    return pista in texto


def classe_contaminante(contaminante) -> str:
    """Classe fisico-quimica do contaminante, pelo vocabulario declarado."""
    texto = _sem_acento(contaminante or "")
    for classe, pistas in CLASSES_CONTAMINANTE.items():
        if any(_pista_presente(texto, pista) for pista in pistas):
            return classe
    return "nao_classificado"


def _sinal_desejado(classe: str):
    if classe in ("cation_metalico", "cation_organico"):
        return "negativa"          # superficie negativa (pH > PZC)
    if classe in ("oxianion", "anion_organico"):
        return "positiva"          # superficie positiva (pH < PZC)
    return None


def compatibilidade(contaminante: str, pzc, ph, classe: str = None) -> dict:
    """Avalia se a carga de superficie favorece o contaminante informado."""
    classe = classe or classe_contaminante(contaminante)
    sinal = _sinal_desejado(classe)
    faltando = []
    try:
        pzc = float(pzc) if pzc is not None else None
    except (TypeError, ValueError):
        pzc = None
    try:
        ph = float(ph) if ph is not None else None
    except (TypeError, ValueError):
        ph = None
    if pzc is None:
        faltando.append("P2 (PZC)")
    if ph is None:
        faltando.append("pH de operacao")
    if sinal is None:
        faltando.append("classe do contaminante")
    if faltando:
        return {
            "veredito": "indeterminado", "classe_contaminante": classe,
            "pzc": pzc, "pH": ph, "faltando": faltando,
            "regra": REGRA_COMPATIBILIDADE,
            "motivos": ["sem dado suficiente: %s" % ", ".join(faltando)],
        }
    margem = ph - pzc
    carga = "negativa" if margem > 0 else ("positiva" if margem < 0 else "nula")
    if margem == 0:
        veredito = "neutro"
        motivos = ["pH igual ao PZC: carga liquida nula, sem seletividade "
                   "eletrostatica"]
    elif carga == sinal:
        veredito = "favoravel"
        motivos = ["carga de superficie %s em pH %.2f (PZC %.2f) atrai a "
                   "classe %s" % (carga, ph, pzc, classe)]
    else:
        veredito = "desfavoravel"
        motivos = ["carga de superficie %s em pH %.2f (PZC %.2f) repele a "
                   "classe %s" % (carga, ph, pzc, classe)]
    return {
        "veredito": veredito, "classe_contaminante": classe,
        "pzc": pzc, "pH": ph, "carga_superficie": carga,
        "margem_pH_PZC": round(margem, 3),
        "margem_absoluta": round(abs(margem), 3),
        "faltando": [], "motivos": motivos,
        "regra": REGRA_COMPATIBILIDADE,
        "nivel_evidencia": "inferencia fisico-quimica a partir de PZC e pH",
    }



# ---------------------------------------------------------------------------
# Persistencia e normalizacao
# ---------------------------------------------------------------------------
def _carregar_pesquisa(sessao, pesquisa_id) -> Pesquisa:
    pesquisa = sessao.get(Pesquisa, str(pesquisa_id or "").strip())
    if pesquisa is None:
        raise KeyError("pesquisa nao encontrada: %s" % pesquisa_id)
    return pesquisa


def _resolver_material(sessao, pesquisa, dados: dict):
    """Material por id, por nome existente ou novo (nome obrigatorio)."""
    material_id = dados.get("material_id")
    if material_id:
        material = sessao.get(Material, str(material_id).strip())
        if material is None:
            raise KeyError("material nao encontrado: %s" % material_id)
        criado = False
    else:
        nome = str(dados.get("material") or dados.get("nome") or "").strip()
        if not nome:
            raise ValueError("informe 'material_id' ou 'material' (nome)")
        material = (sessao.query(Material)
                    .filter(Material.nome.ilike(nome)).first())
        criado = material is None
        if criado:
            material = Material(
                id=novo_id("mat"), nome=nome,
                formula=dados.get("formula"), cas=dados.get("cas"),
                classe=dados.get("classe"),
                origem_material=dados.get("origem"),
                observacao=dados.get("observacao"))
            sessao.add(material)
            sessao.flush()
    vinculo = (sessao.query(PesquisaMaterial)
               .filter(PesquisaMaterial.pesquisa_id == pesquisa.id,
                       PesquisaMaterial.material_id == material.id).first())
    if vinculo is None:
        sessao.add(PesquisaMaterial(pesquisa_id=pesquisa.id,
                                    material_id=material.id,
                                    papel=dados.get("papel") or "alvo"))
        sessao.flush()
    if not pesquisa.material:
        pesquisa.material = material.nome
    return material, criado


def normalizar_caracterizacao(dados: dict) -> dict:
    """Aceita dicionario ou lista e devolve itens com descritor mapeado."""
    bruto = dados.get("caracterizacao")
    itens = []
    if isinstance(bruto, dict):
        for nome, valor in bruto.items():
            if isinstance(valor, dict):
                item = dict(valor)
                item.setdefault("nome", nome)
            else:
                item = {"nome": nome, "valor": valor}
            itens.append(item)
    elif isinstance(bruto, list):
        itens = [dict(item) for item in bruto if isinstance(item, dict)]
    itens.extend(dict(item) for item in (dados.get("propriedades") or [])
                 if isinstance(item, dict))
    normalizados, nao_mapeadas = [], []
    for item in itens:
        nome = str(item.get("nome") or item.get("propriedade") or "").strip()
        if not nome:
            continue
        destino = mapear_propriedade(nome)
        registro = {
            "nome": nome,
            "codigo": (destino or {}).get("codigo"),
            "valor": item.get("valor"),
            "valor_texto": item.get("valor_texto") or item.get("texto"),
            "unidade": item.get("unidade") or (destino or {}).get("unidade"),
            "origem": item.get("origem") or item.get("fonte"),
            "metodo": item.get("metodo"),
            "confianca": item.get("confianca"),
        }
        if registro["codigo"] is None:
            nao_mapeadas.append(nome)
        normalizados.append(registro)
    return {"itens": normalizados, "nao_mapeadas": nao_mapeadas}



def _gravar_descritor(sessao, pesquisa_id, material_id, codigo, resultado):
    """Insere/atualiza a linha do descritor preservando o apoio acumulado."""
    descritor = matriz_7d4.obter(codigo)
    if descritor is None:
        raise KeyError("descritor desconhecido: %s" % codigo)
    registro = (sessao.query(Descritor)
                .filter(Descritor.material_id == material_id,
                        Descritor.codigo == descritor["codigo"]).first())
    if registro is None:
        registro = Descritor(material_id=material_id,
                             codigo=descritor["codigo"],
                             dimensao=descritor["dimensao"],
                             nome=descritor["nome"])
        sessao.add(registro)
    anteriores = json_loads(registro.dados_json, {}) or {}
    apoio = list(anteriores.get("apoio") or [])
    if resultado.get("modo") == "apoio":
        apoio.append({
            "simulador": (resultado.get("fonte") or "").split(" (")[0],
            "chave": resultado.get("chave"),
            "valor": resultado.get("valor_apoio"),
            "unidade": resultado.get("unidade"),
            "memoria": resultado.get("memoria"),
            "quando": agora_iso(),
        })
    else:
        registro.valor = resultado.get("valor")
        texto = resultado.get("valor_texto")
        registro.valor_texto = str(texto) if texto is not None else None
        registro.estado = resultado.get("estado") or "presente"
        registro.unidade = resultado.get("unidade") or descritor["unidade"]
        registro.fonte = resultado.get("fonte")
        registro.regra = resultado.get("regra") or descritor["regra"]
    registro.pesquisa_id = pesquisa_id
    registro.dados_json = json_dumps({
        "memoria": resultado.get("memoria"),
        "complemento": resultado.get("complemento"),
        "faltando": resultado.get("faltando"),
        "apoio": apoio[-20:],
    })
    registro.atualizado_em = db._agora()
    sessao.flush()
    return {
        "codigo": registro.codigo, "valor": registro.valor,
        "valor_texto": registro.valor_texto, "unidade": registro.unidade,
        "estado": registro.estado, "fonte": registro.fonte,
        "modo": resultado.get("modo") or "valor",
        "valor_apoio": (resultado.get("valor_apoio")
                        if resultado.get("modo") == "apoio" else None),
        "memoria": resultado.get("memoria"),
    }


def _registrar_propriedades(sessao, material, itens) -> int:
    """Grava as propriedades declaradas no material (tabela de propriedades)."""
    gravadas = 0
    for item in itens:
        sessao.add(Propriedade(
            material_id=material.id, nome=item["nome"][:160],
            valor=(float(item["valor"])
                   if isinstance(item.get("valor"), (int, float)) else None),
            valor_texto=(str(item.get("valor_texto"))[:400]
                         if item.get("valor_texto") else None),
            unidade=(str(item["unidade"])[:60] if item.get("unidade") else None),
            origem=(str(item["origem"])[:200] if item.get("origem") else None),
            metodo=item.get("metodo"), confianca=item.get("confianca")))
        gravadas += 1
    return gravadas


def _registrar_composicao(sessao, material, composicao) -> int:
    if not isinstance(composicao, list):
        return 0
    gravadas = 0
    for item in composicao:
        if not isinstance(item, dict) or not item.get("elemento"):
            continue
        sessao.add(Composicao(
            material_id=material.id,
            elemento=str(item["elemento"])[:120],
            fracao_massica=item.get("fracao_massica"),
            fracao_molar=item.get("fracao_molar"),
            origem=(str(item.get("origem"))[:200]
                    if item.get("origem") else None)))
        gravadas += 1
    return gravadas


def _descritores_de_caracterizacao(sessao, pesquisa_id, material, itens):
    """Cada propriedade mapeada entra no descritor oficial correspondente."""
    gravados, sem_valor = [], []
    for item in itens:
        codigo = item.get("codigo")
        if not codigo:
            continue
        fonte = item.get("origem") or "propriedade declarada no pedido"
        memoria = "propriedade '%s' mapeada para o descritor %s" % (
            item["nome"], codigo)
        if isinstance(item.get("valor"), (int, float)):
            resultado = {"valor": float(item["valor"]),
                         "unidade": item.get("unidade"), "estado": "presente",
                         "fonte": fonte, "memoria": memoria}
        elif item.get("valor_texto"):
            resultado = {"valor_texto": str(item["valor_texto"]),
                         "unidade": item.get("unidade"), "estado": "presente",
                         "fonte": fonte, "memoria": memoria}
        else:
            sem_valor.append({"codigo": codigo, "nome": item["nome"],
                              "motivo": "propriedade declarada sem valor"})
            continue
        gravados.append(_gravar_descritor(sessao, pesquisa_id, material.id,
                                          codigo, resultado))
    return {"descritores": gravados, "sem_valor": sem_valor}


def _aplicar_regras(sessao, pesquisa_id, material, calculo):
    """Aplica as regras matematicas da matriz (mesmo contrato da API)."""
    gravados, pendentes = [], []
    for codigo, entrada in (calculo or {}).items():
        if not isinstance(entrada, dict):
            continue
        resultado = matriz_7d4.aplicar(codigo, entrada)
        meta = descritores_simuladores.REGRAS.get(str(codigo).upper()) or {}
        resultado["fonte"] = "matriz_7d4 %s" % (meta.get("motor") or codigo)
        if resultado.get("estado") == "ausente":
            pendentes.append({"codigo": codigo,
                              "faltando": resultado.get("faltando") or []})
        gravados.append(_gravar_descritor(sessao, pesquisa_id, material.id,
                                          codigo, resultado))
    return {"descritores": gravados, "pendentes": pendentes}


def _preenchimento_matriz(sessao, material_id) -> dict:
    """Cobertura sobre os 28 descritores: sem linha = `ausente`."""
    existentes = {linha.codigo: linha.estado
                  for linha in sessao.query(Descritor).filter(
                      Descritor.material_id == material_id).all()}
    itens = [{"codigo": descritor["codigo"],
              "estado": existentes.get(descritor["codigo"], "ausente")}
             for descritor in matriz_7d4.DESCRITORES]
    return matriz_7d4.avaliar_preenchimento(itens)


def _parametros_automaticos(valores: dict, parametros: dict) -> dict:
    """Completa parametros do simulador com descritores ja conhecidos.

    Conversao so quando a unidade coincide: nada de converter um para outro
    silenciosamente.
    """
    saida = dict(parametros or {})
    s3 = valores.get("S3")
    if "area_m2g" not in saida and s3 and s3.get("valor") is not None:
        if "m2/g" in str(s3.get("unidade") or "m2/g"):
            saida["area_m2g"] = s3["valor"]
    s5 = valores.get("S5")
    if ("diametro_nm" not in saida and s5 and s5.get("valor") is not None
            and str(s5.get("unidade") or "").strip().lower() == "nm"):
        saida["diametro_nm"] = s5["valor"]
    return saida


def _valores_do_material(sessao, material_id) -> dict:
    linhas = (sessao.query(Descritor)
              .filter(Descritor.material_id == material_id).all())
    return {linha.codigo: {"valor": linha.valor, "unidade": linha.unidade,
                           "estado": linha.estado,
                           "detalhe": json_loads(linha.dados_json, {}) or {}}
            for linha in linhas}


def _executar_simuladores(sessao, pesquisa_id, material, pesquisa, nomes,
                          parametros, pergunta):
    """Executa os simuladores pedidos, guarda entrada/saida e atualiza a matriz."""
    valores = _valores_do_material(sessao, material.id)
    params = _parametros_automaticos(valores, parametros)
    registros = []
    for nome in nomes:
        saida = descritores_simuladores.executar(
            nome, params, pergunta or pesquisa.pergunta or "",
            requer_completo=True)
        simulacao = Simulacao(
            id=novo_id("sim"), pesquisa_id=pesquisa_id,
            material_id=material.id, simulador=nome,
            motor=(saida.get("motor") or "universal.SIMULADORES"),
            parametros_json=json_dumps({"pergunta": pergunta or
                                        pesquisa.pergunta,
                                        "parametros": params}),
            estado=saida.get("estado") or "erro",
            resultado_json=json_dumps(saida.get("resultado")),
            erro=saida.get("erro"),
            duracao_s=saida.get("duracao_s"),
            nivel_evidencia="computacional",
            concluido_em=(db._agora() if saida.get("executado") else None))
        sessao.add(simulacao)
        sessao.flush()
        aplicados = []
        for item in saida.get("descritores") or []:
            aplicados.append(_gravar_descritor(sessao, pesquisa_id,
                                               material.id,
                                               item["codigo"], item))
        registros.append({
            "simulacao_id": simulacao.id,
            "simulador": nome,
            "estado": saida.get("estado"),
            "executado": saida.get("executado"),
            "duracao_s": saida.get("duracao_s"),
            "erro": saida.get("erro"),
            "faltando": saida.get("faltando"),
            "parametros_padrao": saida.get("parametros_padrao"),
            "resultado": saida.get("resultado"),
            "descritores": aplicados,
            "avisos": saida.get("avisos"),
        })
    return {"simuladores": registros, "parametros": params}


def _parametros_modelo(nome, dados, valores, condicoes) -> dict:
    """Parametros do modelo: explicitos primeiro, depois descritores e condicoes."""
    meta = descritores_simuladores.MODELOS.get(nome) or {}
    informados = (dados.get("parametros_modelo") or {}).get(nome) or {}
    params = dict(informados)
    if nome in ("langmuir", "langmuir_curva"):
        d1 = valores.get("D1") or {}
        d2 = valores.get("D2") or {}
        chave_q = "q_max" if nome == "langmuir_curva" else "qmax"
        chave_k = "K_L" if nome == "langmuir_curva" else "KL"
        params.setdefault(chave_q, d1.get("valor"))
        params.setdefault(chave_k, d2.get("valor"))
        if params.get(chave_k) in (None, ""):
            # O ajuste de D1 ja devolve KL como complemento: usar o mesmo
            # resultado evita pedir o dado duas vezes (nao inventa valor).
            complemento = (d1.get("detalhe") or {}).get("complemento") or {}
            params[chave_k] = complemento.get("KL_L_mg")
    if nome == "pfo_cinetica":
        complemento = ((valores.get("D6") or {}).get("detalhe")
                       or {}).get("complemento") or {}
        params.setdefault("q_e_equilibrio", complemento.get("qe_mg_g"))
    chave_ce = "C_e" if nome.endswith("curva") else "Ce"
    if nome != "pfo_cinetica":
        # PFO nao recebe Ce: passar a chave daria TypeError no motor.
        params.setdefault(chave_ce, condicoes.get("Ce")
                          or condicoes.get("C_e"))
    return {chave: valor for chave, valor in params.items() if valor is not None}


def _aplicar_modelos(sessao, pesquisa_id, material, pesquisa, valores, pedidos,
                     condicoes, dados):
    """Aplica os modelos de adsorcao cujos requisitos estao completos."""
    resultados = []
    for nome in (pedidos or []):
        meta = descritores_simuladores.MODELOS.get(nome)
        if meta is None:
            resultados.append({"modelo": nome, "estado": "desconhecido",
                               "motivo": "modelo nao registrado"})
            continue
        params = _parametros_modelo(nome, dados, valores, condicoes)
        faltando = [item["chave"] for item in meta["requisitos"]
                    if params.get(item["chave"]) in (None, "")]
        base = {"modelo": nome, "motor": meta["motor"],
                "parametros": params, "faltando": faltando,
                "natureza": meta["natureza"]}
        if faltando:
            resultados.append(dict(base, estado="bloqueado_por_parametros"))
            continue
        try:
            if nome in ("langmuir", "freundlich"):
                consulta = "isoterma de adsorcao modelo %s" % nome
                saida = adaptadores.modelo_adsorcao(consulta, params)
                estado = saida.get("status")
                valor = saida.get("qe_mg_g")
            elif nome in ("langmuir_curva", "freundlich_curva"):
                tipo = "langmuir" if nome.startswith("langmuir") else "freundlich"
                saida = adaptadores.isoterma(tipo, **params)
                estado = "calculado"
                valor = saida.get("q_e")
            else:
                saida = adaptadores.modelo_analitico("cinetica_pfo", **params)
                estado = "calculado"
                valor = saida.get("q_t")
        except Exception as erro:                       # noqa: BLE001
            resultados.append(dict(base, estado="erro",
                                   erro="%s: %s" % (type(erro).__name__, erro)))
            continue
        sessao.add(Simulacao(
            id=novo_id("sim"), pesquisa_id=pesquisa_id,
            material_id=material.id, simulador="modelo:%s" % nome,
            motor=meta["motor"], parametros_json=json_dumps(params),
            estado=("ok" if estado in ("calculado", "ok") else estado or "erro"),
            resultado_json=json_dumps(saida), duracao_s=0.0,
            nivel_evidencia="modelo_analitico", concluido_em=db._agora()))
        sessao.flush()
        resultados.append(dict(base, estado=estado, resultado=saida,
                               qe=valor))
    return resultados


# ---------------------------------------------------------------------------
# Lacunas experimentais
# ---------------------------------------------------------------------------
COM_DADO = {"presente", "calculado", "estimado", "validado"}

CRITICOS_ADSORCAO = (
    ("S1", "composicao elementar e pureza"),
    ("S3", "area superficial especifica (BET)"),
    ("P2", "ponto de carga zero"),
    ("D1", "capacidade maxima de adsorcao"),
    ("D2", "afinidade (KL/Kf) e fator de separacao"),
    ("D3", "cinetica de adsorcao"),
    ("D6", "eficiencia de remocao"),
    ("D7", "faixa operacional de pH/temperatura"),
    ("C1", "toxicidade e seguranca"),
    ("C6", "conformidade normativa"),
)


def _lacunas(valores: dict) -> list:
    """Descritores criticos sem dado e o que seria necessario para fechar."""
    lacunas = []
    for codigo, nome in CRITICOS_ADSORCAO:
        registro = valores.get(codigo) or {}
        if registro.get("valor") is not None and registro.get("estado") in COM_DADO:
            continue
        necessario = []
        meta = descritores_simuladores.REGRAS.get(codigo)
        if meta:
            necessario = [item["chave"] for item in meta["requisitos"]]
        lacunas.append({
            "codigo": codigo,
            "nome": nome,
            "estado_atual": registro.get("estado") or "ausente",
            "motivo": ("sem valor registrado para o material"
                       if registro.get("valor") is None
                       else "valor existe mas o estado '%s' nao e' aceito"
                            % registro.get("estado")),
            "entradas_que_fecham": necessario,
            "fonte_possivel": ("regra %s" % meta["motor"] if meta
                               else "ensaio/medicao experimental"),
        })
    return lacunas


def _simuladores_compativeis(parametros: dict) -> list:
    """Simuladores cujas entradas obrigatorias estao presentes E que recebem
    ao menos uma entrada declarada.

    A segunda condicao evita executar motor que so tem entradas opcionais
    quando o material nao trouxe nenhum dado — executar sem nenhuma entrada
    produziria erro, nao resultado.
    """
    nomes = []
    for nome in descritores_simuladores.SIMULADORES:
        pendentes = descritores_simuladores.requisitos_pendentes(nome,
                                                                 parametros)
        if pendentes:
            continue
        chaves = (descritores_simuladores.SIMULADORES.get(nome) or {}).get(
            "le_chaves") or []
        if chaves and not any(parametros.get(chave) not in (None, "", [], {})
                              for chave in chaves):
            continue
        nomes.append(nome)
    return nomes


# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------
def _comparar_literatura(pesquisa_id: str, tolerancia: float) -> dict:
    from . import motor_pesquisa

    try:
        return motor_pesquisa.comparar_com_literatura(pesquisa_id, tolerancia)
    except motor_pesquisa.DadosInvalidos as erro:
        return {"estado": "sem_dados", "motivo": str(erro),
                "comparacoes": [], "total": 0}


def _s1_da_composicao(sessao, pesquisa_id, material, composicao) -> list:
    if not isinstance(composicao, list) or not composicao:
        return []
    partes = []
    for item in composicao:
        if isinstance(item, dict) and item.get("elemento"):
            fracao = item.get("fracao_massica")
            partes.append("%s%s" % (item["elemento"],
                                    (" %.4g" % fracao) if fracao else ""))
    if not partes:
        return []
    resultado = {
        "valor_texto": "; ".join(partes)[:400], "unidade": "fracao m/m",
        "estado": "presente",
        "fonte": "composicao declarada no pedido de validacao",
        "memoria": "S1 recebe a composicao declarada; pureza depende de ensaio",
    }
    return [_gravar_descritor(sessao, pesquisa_id, material.id, "S1",
                              resultado)]


def validar(pesquisa_id: str, dados: dict = None) -> dict:
    """Executa a validacao computacional do adsorvente e grava cada artefato.

    Corpo aceito (todos opcionais, exceto `material` ou `material_id`)::

        {"material": "carvao ativado de casca de arroz",
         "caracterizacao": {"area_superficial": {"valor": 750,
                                                 "unidade": "m2/g",
                                                 "metodo": "BET N2"}},
         "composicao": [{"elemento": "C", "fracao_massica": 0.82}],
         "condicoes": {"pH": 5.5, "temperatura_C": 25, "Ce": 10},
         "calculo": {"D1": {"pontos": [{"Ce": 1, "qe": 4}]}},
         "simuladores": ["superficie", "cristalografia"],
         "parametros_simulador": {"parametro_rede": 3.5},
         "modelos": ["langmuir", "freundlich", "pfo_cinetica"]}
    """
    dados = dict(dados or {})
    sessao = db.sessao()
    try:
        pesquisa = _carregar_pesquisa(sessao, pesquisa_id)
        material, criado = _resolver_material(sessao, pesquisa, dados)
        caracterizacao = normalizar_caracterizacao(dados)
        propriedades = _registrar_propriedades(sessao, material,
                                               caracterizacao["itens"])
        composicao = _registrar_composicao(sessao, material,
                                           dados.get("composicao"))
        descritores = list(_s1_da_composicao(sessao, pesquisa.id, material,
                                             dados.get("composicao")))
        de_caract = _descritores_de_caracterizacao(
            sessao, pesquisa.id, material, caracterizacao["itens"])
        descritores.extend(de_caract["descritores"])
        calculo = dict(dados.get("calculo") or {})
        if "D2" not in calculo and isinstance(calculo.get("D1"), dict):
            # D2 usa exatamente os mesmos pontos de D1 (mesmo ajuste de
            # Langmuir); repetir a entrada nao acrescenta dado novo.
            calculo["D2"] = dict(calculo["D1"])
        de_regras = _aplicar_regras(sessao, pesquisa.id, material, calculo)
        descritores.extend(de_regras["descritores"])

        condicoes = json_loads(pesquisa.condicoes_json, {}) or {}
        for chave, valor in (dados.get("condicoes") or {}).items():
            if valor is not None:
                condicoes[chave] = valor

        parametros = dict(dados.get("parametros_simulador") or {})
        nomes = dados.get("simuladores")
        if isinstance(nomes, str):
            nomes = [nomes]
        if not nomes:
            nomes = _simuladores_compativeis(parametros)
        execucao = _executar_simuladores(
            sessao, pesquisa.id, material, pesquisa, nomes, parametros,
            dados.get("pergunta"))

        valores = _valores_do_material(sessao, material.id)
        modelos = _aplicar_modelos(
            sessao, pesquisa.id, material, pesquisa, valores,
            dados.get("modelos") or ["langmuir", "freundlich",
                                     "pfo_cinetica"],
            condicoes, dados)
        compat = compatibilidade(
            dados.get("contaminante") or pesquisa.contaminante,
            (valores.get("P2") or {}).get("valor"), condicoes.get("pH"))
        lacunas = _lacunas(valores)
        preenchimento = _preenchimento_matriz(sessao, material.id)
        registrar_historico(sessao, "material", material.id,
                            "validacao_adsorvente",
                            {"pesquisa": pesquisa.id,
                             "propriedades": propriedades,
                             "simuladores": [s["simulador"] for s in
                                             execucao["simuladores"]],
                             "lacunas": [l["codigo"] for l in lacunas]})
        # Commita antes de comparar: `comparar_com_literatura` abre outra sessao
        # e o SQLite aceita um escritor por vez.
        sessao.commit()
        comparacao = _comparar_literatura(
            pesquisa.id, float(dados.get("tolerancia") or 0.2))
        resumo = {
            "pesquisa_id": pesquisa.id,
            "material": {"id": material.id, "nome": material.nome,
                         "criado": criado},
            "nivel_evidencia": {
                "propriedades": "dado declarado pelo operador",
                "simuladores": "resultado computacional do motor real",
                "modelos": "calculo analitico; nao e' medicao experimental",
                "comparacao": "texto das evidencias recuperadas",
            },
            "caracterizacao": {"propriedades_gravadas": propriedades,
                               "composicao": composicao,
                               "nao_mapeadas": caracterizacao["nao_mapeadas"],
                               "sem_valor": de_caract["sem_valor"]},
            "descritores": descritores,
            "regras_pendentes": de_regras["pendentes"],
            "simuladores": execucao["simuladores"],
            "parametros_simulador": execucao["parametros"],
            "modelos": modelos,
            "comparacao_literatura": comparacao,
            "compatibilidade": compat,
            "lacunas_experimentais": lacunas,
            "preenchimento": preenchimento,
        }
        return resumo
    finally:
        sessao.close()


def _descritor_publico(linha) -> dict:
    return {
        "codigo": linha.codigo,
        "dimensao": linha.dimensao,
        "nome": linha.nome,
        "valor": linha.valor,
        "valor_texto": linha.valor_texto,
        "unidade": linha.unidade,
        "estado": linha.estado,
        "fonte": linha.fonte,
        "regra": linha.regra,
        "detalhe": json_loads(linha.dados_json, {}),
        "atualizado_em": (linha.atualizado_em.isoformat()
                          if linha.atualizado_em else None),
    }


def obter_validacao(pesquisa_id: str, material_id: str = None) -> dict:
    """Le de volta a ultima validacao gravada (descritores, execucoes, comparacao)."""
    sessao = db.sessao()
    try:
        pesquisa = _carregar_pesquisa(sessao, pesquisa_id)
        if material_id:
            material = sessao.get(Material, str(material_id).strip())
            if material is None:
                raise KeyError("material nao encontrado: %s" % material_id)
        else:
            vinculo = (sessao.query(PesquisaMaterial)
                       .filter(PesquisaMaterial.pesquisa_id == pesquisa.id)
                       .order_by(PesquisaMaterial.id.desc()).first())
            if vinculo is None:
                raise KeyError("nenhum material vinculado a %s" % pesquisa.id)
            material = sessao.get(Material, vinculo.material_id)
        linhas = (sessao.query(Descritor)
                  .filter(Descritor.material_id == material.id)
                  .order_by(Descritor.codigo).all())
        simulacoes = (sessao.query(Simulacao)
                      .filter(Simulacao.pesquisa_id == pesquisa.id,
                              Simulacao.material_id == material.id)
                      .order_by(Simulacao.criado_em).all())
        comparacoes = (sessao.query(Comparacao)
                       .filter(Comparacao.pesquisa_id == pesquisa.id).all())
        return {
            "pesquisa_id": pesquisa.id,
            "material": {"id": material.id, "nome": material.nome},
            "descritores": [_descritor_publico(l) for l in linhas],
            "preenchimento": _preenchimento_matriz(sessao, material.id),
            "simulacoes": [{
                "id": item.id, "simulador": item.simulador,
                "estado": item.estado, "motor": item.motor,
                "parametros": json_loads(item.parametros_json, {}),
                "resultado": json_loads(item.resultado_json, None),
                "erro": item.erro, "duracao_s": item.duracao_s,
                "nivel_evidencia": item.nivel_evidencia,
            } for item in simulacoes],
            "comparacoes": [{
                "descritor": item.descritor, "grandeza": item.grandeza,
                "valor_calculado": item.valor_calculado,
                "valor_literatura": item.valor_literatura,
                "unidade": item.unidade,
                "desvio_relativo": item.desvio_relativo,
                "veredito": item.veredito,
                "fonte_literatura": item.fonte_literatura,
            } for item in comparacoes],
        }
    finally:
        sessao.close()


def aplicar_descritores(sessao, pesquisa_id, material_id, itens) -> list:
    """Grava atualizacoes de descritor vindas de simulador/modelo (sessao aberta).

    Recebe a sessao de quem chamou para que a escrita participe da mesma
    transacao: ou a simulacao e os descritores entram juntos, ou nenhum entra.
    """
    material = sessao.get(Material, str(material_id).strip())
    if material is None:
        raise KeyError("material nao encontrado: %s" % material_id)
    return [_gravar_descritor(sessao, pesquisa_id, material.id,
                              item["codigo"], item) for item in (itens or [])]


