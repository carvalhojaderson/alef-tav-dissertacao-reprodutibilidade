# -*- coding: utf-8 -*-
"""Testes da interface web: SPA sem build publicada pelo proprio backend.

A interface e' servida por `app.py` (`/` e `/app/`). Um E2E completo (jsdom
carregando `index.html`, importando os modulos ES e clicando contra um uvicorn
real) foi executado fora da suite; aqui ficam as garantias que o pytest mantem
sem navegador: as rotas respondem, todo arquivo citado existe e nenhum import
relativo aponta para modulo ausente.
"""
from __future__ import annotations

import pathlib
import re

INTERFACE = pathlib.Path(__file__).resolve().parent / "frontend"
PREFIXO = "/app/"

PADRAO_IMPORT = re.compile(r"""(?:import|export)\s[^;]*?from\s+["']([^"']+)["']""")
PADRAO_CITADO = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""")

TELAS = INTERFACE / "js" / "telas"
TELAS_MINIMAS = 10


def _texto(caminho: pathlib.Path) -> str:
    return caminho.read_text(encoding="utf-8")


def _publicado(citado: str) -> pathlib.Path:
    """Converte `/app/js/app.js` no arquivo real dentro de `frontend/`."""
    relativo = citado[len(PREFIXO):].split("?")[0].split("#")[0]
    return INTERFACE / relativo


def test_interface_existe_no_pacote():
    assert (INTERFACE / "index.html").is_file()
    assert (INTERFACE / "estilos.css").is_file()
    assert (INTERFACE / "js" / "app.js").is_file()
    assert len(list(TELAS.glob("*.js"))) >= TELAS_MINIMAS


def test_interface_tem_as_telas_do_fluxo():
    """O fluxo do metodo exige destas telas em diante (matriz, componentes...)."""
    nomes = {tela.stem for tela in TELAS.glob("*.js")}
    obrigatorias = {"painel", "pesquisas", "materiais", "caracterizacao",
                    "componentes", "matriz", "simuladores", "comparacao",
                    "relatorios", "historico"}
    assert obrigatorias <= nomes, sorted(obrigatorias - nomes)


def test_raiz_serve_o_index(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/html")
    corpo = resposta.text
    assert "<title>ALEF-TAV Ambiental</title>" in corpo
    assert "/app/js/app.js" in corpo


def test_app_serve_o_index(cliente):
    resposta = cliente.get("/app/")
    assert resposta.status_code == 200
    assert "/app/js/app.js" in resposta.text


def test_assets_citados_pelo_index_sao_servidos(cliente):
    citados = [item for item in PADRAO_CITADO.findall(_texto(INTERFACE / "index.html"))
               if item.startswith(PREFIXO)]
    assert PREFIXO + "js/app.js" in citados
    assert PREFIXO + "estilos.css" in citados
    for citado in citados:
        resposta = cliente.get(citado)
        assert resposta.status_code == 200, citado
        assert resposta.content, citado


def test_modulos_js_saem_com_tipo_javascript(cliente):
    for modulo in sorted(INTERFACE.rglob("*.js")):
        citado = PREFIXO + modulo.relative_to(INTERFACE).as_posix()
        resposta = cliente.get(citado)
        assert resposta.status_code == 200, citado
        assert "javascript" in resposta.headers["content-type"], citado


def test_css_sai_com_tipo_css(cliente):
    resposta = cliente.get("/app/estilos.css")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/css")


def test_arquivo_inexistente_nao_quebra_o_servico(cliente):
    resposta = cliente.get("/app/js/nao_existe.js")
    assert resposta.status_code == 404
    assert cliente.get("/api/ready").status_code == 200


def test_imports_relativos_apontam_para_modulos_existentes():
    faltando = []
    for modulo in sorted(INTERFACE.rglob("*.js")):
        for alvo in PADRAO_IMPORT.findall(_texto(modulo)):
            if not alvo.startswith("."):
                continue
            destino = (modulo.parent / alvo).resolve()
            if not destino.is_file():
                faltando.append(f"{modulo.relative_to(INTERFACE).as_posix()} -> {alvo}")
    assert not faltando, faltando


def test_cada_tela_exporta_meta_e_render():
    problemas = []
    for tela in sorted(TELAS.glob("*.js")):
        texto = _texto(tela)
        if "export const meta" not in texto:
            problemas.append(f"{tela.name}: sem `export const meta`")
        if "export async function render" not in texto:
            problemas.append(f"{tela.name}: sem `export async function render`")
    assert not problemas, problemas


def test_roteador_importa_todas_as_telas():
    app = _texto(INTERFACE / "js" / "app.js")
    ausentes = [tela.name for tela in sorted(TELAS.glob("*.js"))
                if f"./telas/{tela.name}" not in app]
    assert not ausentes, ausentes


def test_api_anuncia_a_interface(cliente):
    indice = cliente.get("/api").json()
    assert indice["interface"] == "/app/"
    assert indice["docs"] == "/docs"


def test_pacote_do_space_leva_a_interface(tmp_path):
    """`preparar_espaco.montar` publica a SPA junto com a API (sem testes)."""
    from ambiental_backend import preparar_espaco

    destino = preparar_espaco.montar(tmp_path / "space")["destino"]
    publicado = destino / "ambiental_backend" / "frontend"
    assert (publicado / "index.html").is_file()
    assert (publicado / "estilos.css").is_file()
    assert (publicado / "js" / "app.js").is_file()
    assert len(list((publicado / "js" / "telas").glob("*.js"))) >= TELAS_MINIMAS
    assert (destino / "app.py").is_file()
    assert not list((destino / "ambiental_backend").rglob("test_*.py"))
    assert not list((destino / "ambiental_backend").rglob("conftest.py"))
