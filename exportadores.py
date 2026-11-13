# exportadores.py - Multiplos formatos de exportacao
import io

try:
    from docx import Document
    DOCX_OK = True
except ImportError:
    DOCX_OK = False

try:
    from pptx import Presentation
    PPTX_OK = True
except ImportError:
    PPTX_OK = False


def texto_para_docx(texto, titulo="ALEF-TAV"):
    if not DOCX_OK:
        return None
    try:
        doc = Document()
        doc.add_heading(titulo, 0)
        for linha in texto.split("\n"):
            l = linha.strip()
            if not l:
                continue
            if l.startswith("# "):
                doc.add_heading(l[2:], 1)
            elif l.startswith("## "):
                doc.add_heading(l[3:], 2)
            elif l.startswith("### "):
                doc.add_heading(l[4:], 3)
            elif l.startswith("- "):
                doc.add_paragraph(l[2:], style="List Bullet")
            else:
                doc.add_paragraph(l)
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None


def texto_para_pptx(texto, titulo="ALEF-TAV"):
    if not PPTX_OK:
        return None
    try:
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = titulo
        slide.placeholders[1].text = "Gerado por ALEF-TAV"

        blocos = [b.strip() for b in texto.split("\n\n") if len(b.strip()) > 30]
        for bloco in blocos[:15]:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            linhas = bloco.split("\n")
            titulo_slide = linhas[0][:80]
            slide.shapes.title.text = titulo_slide
            corpo = "\n".join(linhas[1:])[:800]
            if corpo:
                slide.placeholders[1].text = corpo

        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None


def artigos_para_bibtex(artigos):
    linhas = []
    for i, a in enumerate(artigos, 1):
        linhas.append("@article{alef" + str(i) + ",")
        linhas.append("  title = {" + a.get("titulo", "").replace("{", "").replace("}", "") + "},")
        linhas.append("  year = {" + str(a.get("ano", 2024)) + "},")
        linhas.append("  url = {" + a.get("link", "") + "},")
        linhas.append("  note = {" + a.get("fonte", "") + "}")
        linhas.append("}")
        linhas.append("")
    return "\n".join(linhas)


def artigos_para_ris(artigos):
    linhas = []
    for a in artigos:
        linhas.append("TY  - JOUR")
        linhas.append("TI  - " + a.get("titulo", ""))
        linhas.append("PY  - " + str(a.get("ano", 2024)))
        linhas.append("UR  - " + a.get("link", ""))
        linhas.append("PB  - " + a.get("fonte", ""))
        linhas.append("ER  - ")
        linhas.append("")
    return "\n".join(linhas)
# 10/06/2026 13:14:58

# 10/06/2026 13:17:05

# 10/06/2026 13:29:22
