import io
from collections import Counter
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from app.helpers.config import APP_TITLE, APP_VERSION


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("T", parent=base["Title"], fontSize=20,
                                textColor=colors.HexColor("#7c5cfc"),
                                spaceAfter=4, fontName="Helvetica-Bold"),
        "h2":    ParagraphStyle("H2", parent=base["Heading2"], fontSize=12,
                                textColor=colors.HexColor("#5a5a8a"),
                                spaceBefore=14, spaceAfter=5, fontName="Helvetica-Bold"),
        "body":  ParagraphStyle("B", parent=base["Normal"], fontSize=10,
                                leading=16, spaceAfter=7, fontName="Helvetica"),
        "muted": ParagraphStyle("M", parent=base["Normal"], fontSize=9,
                                textColor=colors.HexColor("#7878a8"),
                                leftIndent=10, spaceAfter=4, fontName="Helvetica"),
        "label": ParagraphStyle("L", parent=base["Normal"], fontSize=9,
                                textColor=colors.HexColor("#7c5cfc"),
                                fontName="Helvetica-Bold", spaceAfter=3),
        "quote": ParagraphStyle("Q", parent=base["Normal"], fontSize=9,
                                textColor=colors.HexColor("#5a5a8a"),
                                leftIndent=12, fontName="Helvetica-Oblique",
                                spaceAfter=6, leading=14),
        "conf":  ParagraphStyle("C", parent=base["Normal"], fontSize=8,
                                textColor=colors.HexColor("#9090b0"),
                                leftIndent=10, spaceAfter=3, fontName="Helvetica"),
    }


def _safe(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_pdf(
    results: list[dict],
    bugs: list[str],
    dup_map: dict[int, list[int]],
    total: int,
    dup_count: int,
) -> bytes:
    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=letter,
                             rightMargin=0.75*inch, leftMargin=0.75*inch,
                             topMargin=0.75*inch,   bottomMargin=0.75*inch)
    s     = _styles()
    story = []

    story.append(Paragraph(APP_TITLE, s["title"]))
    story.append(Paragraph(f"Automated Bug Triage Report · v{APP_VERSION}", s["body"]))
    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2a2a3d")))
    story.append(Spacer(1, 0.15*inch))

    story.append(Paragraph("Analytics Summary", s["h2"]))
    story.append(Paragraph(f"Total Bugs Extracted: <b>{total}</b>", s["body"]))
    story.append(Paragraph(f"Duplicates Detected: <b>{dup_count}</b>", s["body"]))
    story.append(Paragraph(f"Unique Bugs Classified: <b>{len(results)}</b>", s["body"]))

    tc = Counter([r["bug_type"] for r in results])
    sc = Counter([r["severity"] for r in results])
    story.append(Paragraph("Bug Type Breakdown:", s["label"]))
    for bt, cnt in tc.most_common():
        story.append(Paragraph(f"• {bt}: {cnt}", s["muted"]))
    story.append(Paragraph("Severity Breakdown:", s["label"]))
    for sv, cnt in sc.most_common():
        story.append(Paragraph(f"• {sv}: {cnt}", s["muted"]))

    story += [
        Spacer(1, 0.15*inch),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2a2a3d")),
        Paragraph("Classified Bug Reports", s["h2"]),
    ]

    for i, r in enumerate(results):
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"Bug #{i+1}", s["label"]))

        bug_text = r.get("text", "")
        if bug_text:
            story.append(Paragraph(f'"{_safe(bug_text[:200])}{"..." if len(bug_text)>200 else ""}"', s["quote"]))

        if r.get("is_uncertain"):
            bt_cands = r.get("bt_candidates", [])
            story.append(Paragraph(
                f"⚠ Low confidence — possible: "
                f"{bt_cands[0][0]} ({bt_cands[0][1]}%) or {bt_cands[1][0]} ({bt_cands[1][1]}%)"
                if len(bt_cands) >= 2 else "⚠ Low confidence prediction",
                s["muted"]
            ))

        narrative = (
            f"As per the analyzed report, the severity of the current running bug is "
            f"<b>{r['severity']}</b>. With the current severity, we found out that the bug is a "
            f"<b>{r['bug_type']}</b> issue. With this bug running in the back, I would find out "
            f"that the fix time on the basis of the severity is <b>{r['fix_time']}</b>."
        )
        story.append(Paragraph(narrative, s["body"]))

        story.append(Paragraph(
            f"Confidence — Bug Type: {r.get('bt_conf',0)}% · "
            f"Severity: {r.get('sv_conf',0)}% · "
            f"Fix Time: {r.get('ft_conf',0)}% (Temperature T=0.6)",
            s["conf"]
        ))

        dup_list = dup_map.get(r["original_index"], [])
        if dup_list:
            story.append(Paragraph(
                "We also found that there are similar bugs with the same outcome in your input. "
                "And this all will take similar timeline or fix time:", s["muted"]
            ))
            for d in dup_list:
                dt = bugs[d][:120] + ("..." if len(bugs[d]) > 120 else "")
                story.append(Paragraph(f'• "{_safe(dt)}"', s["muted"]))

        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd")))

    doc.build(story)
    buf.seek(0)
    return buf.read()
