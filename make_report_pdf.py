"""Renders the report (report_content.py) to Project_Report.pdf.

    python make_report_pdf.py
"""
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from report_content import TITLE, build

ROOT = Path(__file__).parent
OUT = ROOT / "Project_Report.pdf"
W = A4[0] - 40 * mm

ss = getSampleStyleSheet()
BLUE, GREY, LIGHT = colors.HexColor("#1F5FBF"), colors.HexColor("#5A5A5A"), colors.HexColor("#EEF3FB")
body = ParagraphStyle("body", parent=ss["Normal"], fontName="Times-Roman", fontSize=11, leading=15,
                      alignment=TA_JUSTIFY, spaceAfter=6)
small = ParagraphStyle("small", parent=body, fontName="Helvetica", fontSize=8.5, leading=11,
                       textColor=GREY, alignment=TA_CENTER)
cell = ParagraphStyle("cell", parent=body, fontName="Helvetica", fontSize=8.6, leading=11, alignment=0, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")
h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=15, leading=19,
                    textColor=BLUE, spaceBefore=10, spaceAfter=6, keepWithNext=1)
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14,
                    spaceBefore=7, spaceAfter=4, keepWithNext=1)
ttl = ParagraphStyle("ttl", parent=h1, fontSize=22, leading=28, alignment=TA_CENTER, textColor=colors.black)
sub = ParagraphStyle("sub", parent=body, fontName="Helvetica", fontSize=12, leading=17, alignment=TA_CENTER,
                     textColor=GREY)
ref = ParagraphStyle("ref", parent=body, fontSize=9.5, leading=12.5, alignment=0)
todo = ParagraphStyle("todo", parent=body, fontName="Helvetica-Oblique", fontSize=9.5, leading=13,
                      backColor=colors.HexColor("#FFF6DD"), borderColor=colors.HexColor("#E0B040"),
                      borderWidth=0.7, borderPadding=6, leftIndent=6, rightIndent=6, spaceBefore=6, spaceAfter=10)


def grid(rows, widths, header=True):
    data = [[Paragraph(str(c), cellb if header and i == 0 else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * W for w in widths], repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), LIGHT))
    t.setStyle(TableStyle(st))
    return t


def cover(info):
    out = [Spacer(1, 30 * mm)]
    out += [Paragraph(part, ttl) for part in info["title"].split(": ", 1)]
    out += [Spacer(1, 6 * mm), Paragraph(info["subtitle"], sub), Spacer(1, 14 * mm),
            Paragraph("<b>Submitted by</b>", sub), Spacer(1, 3 * mm)]
    team = grid([["Name", "Roll No."]] + [list(m) for m in info["team"]], [0.45, 0.2])
    team.hAlign = "CENTER"
    out += [team, Spacer(1, 6 * mm), Paragraph(f"<b>Under the guidance of</b><br/>{info['guide']}", sub),
            Spacer(1, 16 * mm), Paragraph(f"<b>Abstract.</b> {info['abstract']}", body)]
    return out


def heading_before(story):
    """Pop a heading that directly precedes a table or figure, so both move to the next page together."""
    if story and isinstance(story[-1], Paragraph) and story[-1].style in (h1, h2):
        return [story.pop()]
    return []


def main():
    blocks, have = build(ROOT)
    story, nfig, ntab = [], 0, 0
    for b in blocks:
        kind = b[0]
        if kind == "cover":
            story += cover(b[1])
        elif kind == "pagebreak":
            story.append(PageBreak())
        elif kind == "h1":
            story.append(Paragraph(b[1], h1))
        elif kind == "h2":
            story.append(Paragraph(b[1], h2))
        elif kind == "p":
            story.append(Paragraph(b[1], body))
        elif kind == "todo":
            story.append(Paragraph(f"[{b[1]}]", todo))
        elif kind == "bullets":
            for i, it in enumerate(b[1], 1):
                story.append(Paragraph(it, body, bulletText=f"{i}." if b[2] else "•"))
        elif kind == "table":
            ntab += 1
            story.append(KeepTogether(heading_before(story) + [Paragraph(f"Table {ntab}. {b[1]}", small), Spacer(1, 2),
                                                               grid(b[2], b[3]), Spacer(1, 8)]))
        elif kind == "figure":
            p = ROOT / b[1]
            if not p.exists():
                story.append(Paragraph(f"[Figure missing: {b[1]}]", todo))
                continue
            nfig += 1
            w, h = PILImage.open(p).size
            iw = W * b[3]
            story.append(KeepTogether(heading_before(story) + [Image(str(p), width=iw, height=iw * h / w),
                                                               Paragraph(f"Figure {nfig}. {b[2]}", small), Spacer(1, 8)]))
        elif kind == "refs":
            for i, r in enumerate(b[1], 1):
                story.append(Paragraph(r, ref, bulletText=f"[{i}]"))

    def footer(c, doc):
        if doc.page == 1:
            return
        c.saveState()
        c.setFont("Helvetica", 8)
        c.setFillColor(GREY)
        c.drawString(20 * mm, 10 * mm, "Real-Time PPE Detection - Mini Project Report")
        c.drawRightString(A4[0] - 20 * mm, 10 * mm, str(doc.page))
        c.restoreState()

    SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                      bottomMargin=18 * mm, title=TITLE).build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
