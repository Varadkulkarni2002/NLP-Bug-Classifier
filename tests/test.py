import io
import re
import os
import json
import torch
import numpy as np
import streamlit as st
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from transformers import BertTokenizer, BertModel
import torch.nn as nn
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from collections import Counter

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SBERT_PATH = os.path.join(BASE_DIR, "models", "best_bugzilla_sbert")
CLASSIFIER_PATH = os.path.join(BASE_DIR, "models", "classifier", "best_model.pt")
CONFIG_PATH     = os.path.join(BASE_DIR, "models", "classifier", "run_config.json")

def _load_labels():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        label_map = cfg.get("label_map", cfg.get("label_maps", cfg))
        bug_map = label_map.get("Bug_Type", {})
        sev_map = label_map.get("Severity", {})
        fix_map = label_map.get("Fixing_time", {})
        bug_labels = [k for k, _ in sorted(bug_map.items(), key=lambda x: x[1])]
        sev_labels = [k.lower() for k, _ in sorted(sev_map.items(), key=lambda x: x[1])]
        fix_labels = [k.lower() for k, _ in sorted(fix_map.items(), key=lambda x: x[1])]
        return bug_labels, sev_labels, fix_labels
    return (
        ["Crash", "Freeze", "Memory", "Other", "UI/Visual"],
        ["critical", "major", "minor"],
        ["fast", "medium", "slow"]
    )

BUG_TYPE_LABELS, SEVERITY_LABELS, FIX_TIME_LABELS = _load_labels()

st.set_page_config(
    page_title="NLP Bug Classifier",
    page_icon="🐛",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Epilogue:wght@300;400;500&display=swap');

:root {
    --bg:        #080714;
    --sb-bg:     #0d0b1c;
    --surface:   rgba(255,255,255,0.045);
    --surface2:  rgba(255,255,255,0.07);
    --border:    rgba(255,255,255,0.09);
    --accent:    #7c5cfc;
    --accent2:   #a78bfa;
    --accent3:   #38bdf8;
    --glow:      rgba(124,92,252,0.28);
    --text:      #eeeeff;
    --muted:     #7070a0;
    --dim:       #3a3a60;
    --critical:  #f87171;
    --major:     #fb923c;
    --minor:     #34d399;
}

html, body, [class*="css"] {
    font-family: 'Epilogue', sans-serif !important;
    background: var(--bg) !important;
    color: var(--text) !important;
}

.stApp {
    background:
        radial-gradient(ellipse 140% 60% at 65% -20%, rgba(124,92,252,0.22) 0%, transparent 55%),
        radial-gradient(ellipse 60% 50% at -5% 90%, rgba(56,189,248,0.09) 0%, transparent 50%),
        #080714 !important;
}

header[data-testid="stHeader"] { display:none !important; }

section[data-testid="stSidebar"] {
    background: var(--sb-bg) !important;
    border-right: 1px solid var(--border) !important;
    min-width: 240px !important;
    max-width: 240px !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
}

.main .block-container {
    padding-top: 0 !important;
    padding-bottom: 2rem !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
}

.chat-col {
    max-width: 720px;
    margin: 0 auto;
    padding: 0 1.5rem;
}

/* ── Sidebar elements ── */
.sb-logo { display:flex; align-items:center; gap:0.6rem; padding:0.2rem 0 1rem; border-bottom:1px solid var(--border); margin-bottom:0.75rem; }
.sb-icon { width:32px;height:32px; background:linear-gradient(135deg,var(--accent),var(--accent2)); border-radius:9px; display:flex;align-items:center;justify-content:center; font-size:0.95rem; box-shadow:0 0 14px var(--glow); flex-shrink:0; }
.sb-name { font-family:'Syne',sans-serif; font-size:0.85rem; font-weight:700; color:var(--text); }
.sb-sub  { font-size:0.6rem; color:var(--muted); }
.sb-sec  { font-size:0.6rem; font-weight:700; letter-spacing:0.09em; color:var(--dim); text-transform:uppercase; padding:0.5rem 0.3rem 0.25rem; }
.hist-item { display:flex;align-items:center;gap:0.45rem; padding:0.48rem 0.65rem; border-radius:7px; font-size:0.77rem; color:var(--muted); overflow:hidden;white-space:nowrap;text-overflow:ellipsis; }
.hist-item.active { background:rgba(124,92,252,0.13); color:var(--accent2); border-left:2px solid var(--accent); padding-left:calc(0.65rem - 2px); }
.hist-dot { width:5px;height:5px;border-radius:50%;background:var(--dim);flex-shrink:0; }
.hist-item.active .hist-dot { background:var(--accent); }
.sb-foot { border-top:1px solid var(--border); padding-top:0.7rem; margin-top:1.5rem; display:flex;align-items:center;gap:0.5rem; padding-left:0.3rem; }
.u-av { width:26px;height:26px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent3)); display:flex;align-items:center;justify-content:center;font-size:0.62rem;font-weight:700;color:#fff;flex-shrink:0; }
.u-name { font-size:0.76rem;color:var(--muted); }
.dev-chip { margin-left:auto;background:rgba(124,92,252,0.13);color:var(--accent2);border:1px solid rgba(124,92,252,0.27);border-radius:20px;padding:0.11rem 0.42rem;font-size:0.57rem;font-family:'Syne',sans-serif;font-weight:700;letter-spacing:0.05em; }

/* ── Chat header ── */
.chat-hdr { max-width:720px; margin:0 auto; padding:0.85rem 1.5rem 0.75rem; border-bottom:1px solid var(--border); margin-bottom:1rem; }
.chat-hdr-title { font-family:'Syne',sans-serif;font-size:0.9rem;font-weight:700;color:var(--text); }
.chat-hdr-sub   { font-size:0.67rem;color:var(--muted); }

/* ── Welcome ── */
.welcome { max-width:720px; margin:0 auto; text-align:center; padding:3rem 1.5rem 1.5rem; }
.wc-icon { width:60px;height:60px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:1.8rem;margin:0 auto 1rem;box-shadow:0 0 36px var(--glow); }
.wc-title { font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:800;background:linear-gradient(135deg,#f0f0ff,var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:0.5rem; }
.wc-sub { font-size:0.84rem;color:var(--muted);line-height:1.65;max-width:440px;margin:0 auto 1.4rem; }
.chips { display:flex;flex-wrap:wrap;gap:0.4rem;justify-content:center; }
.chip { padding:0.35rem 0.85rem;background:var(--surface);border:1px solid var(--border);border-radius:20px;font-size:0.73rem;color:var(--muted); }

/* ── Messages ── */
.msg-row { display:flex;gap:0.8rem;align-items:flex-start;margin-bottom:1rem; }
.msg-row.user { flex-direction:row-reverse; }
.mav { width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.78rem;flex-shrink:0;margin-top:2px; }
.mav.ai { background:linear-gradient(135deg,var(--accent),var(--accent2));box-shadow:0 0 10px var(--glow); }
.mav.user { background:var(--surface2);border:1px solid var(--border);font-size:0.62rem;font-weight:700;color:var(--muted); }
.mbubble { max-width:88%;padding:0.8rem 1rem;border-radius:14px;font-size:0.875rem;line-height:1.75;color:var(--text); }
.mbubble.ai   { background:var(--surface);border:1px solid var(--border);border-radius:4px 14px 14px 14px; }
.mbubble.user { background:linear-gradient(135deg,rgba(124,92,252,0.22),rgba(167,139,250,0.13));border:1px solid rgba(124,92,252,0.22);border-radius:14px 4px 14px 14px; }

/* ── Analytics ── */
.a-card { background:var(--surface);border:1px solid var(--border);border-radius:13px;padding:1rem 1.2rem;margin-bottom:0; }
.a-lbl { font-family:'Syne',sans-serif;font-size:0.63rem;font-weight:700;letter-spacing:0.08em;color:var(--accent);text-transform:uppercase;margin-bottom:0.7rem; }
.stat-grid { display:grid;grid-template-columns:repeat(3,1fr);gap:0.6rem;margin-bottom:0.85rem; }
.stat-box { background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:10px;padding:0.7rem;text-align:center; }
.stat-num { font-family:'Syne',sans-serif;font-size:1.65rem;font-weight:800;color:var(--accent2);line-height:1; }
.stat-lbl { font-size:0.65rem;color:var(--muted);margin-top:0.22rem; }
.t-row { margin-bottom:0.45rem; }
.t-meta { display:flex;justify-content:space-between;font-size:0.68rem;color:var(--muted);margin-bottom:0.25rem; }
.t-track { background:rgba(255,255,255,0.05);border-radius:3px;height:5px;overflow:hidden; }
.t-fill { height:100%;border-radius:3px;background:linear-gradient(90deg,var(--accent),var(--accent2)); }
.a-sub { font-family:'Syne',sans-serif;font-size:0.62rem;font-weight:700;letter-spacing:0.07em;color:var(--accent);text-transform:uppercase;margin:0.7rem 0 0.5rem; }

/* ── Bug card ── */
.bug-card { background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:0.9rem 1rem 0.9rem 1.1rem;position:relative;overflow:hidden; }
.bug-card::before { content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient(180deg,var(--accent),var(--accent2)); }
.bug-num { font-family:'Syne',sans-serif;font-size:0.6rem;font-weight:700;letter-spacing:0.08em;color:var(--dim);text-transform:uppercase;margin-bottom:0.42rem; }
.badge-row { display:flex;gap:0.32rem;flex-wrap:wrap;margin-bottom:0.6rem; }
.badge { padding:0.18rem 0.55rem;border-radius:20px;font-size:0.63rem;font-weight:700;font-family:'Syne',sans-serif;letter-spacing:0.04em; }
.b-critical { background:rgba(248,113,113,0.1);color:var(--critical);border:1px solid rgba(248,113,113,0.2); }
.b-major    { background:rgba(251,146,60,0.1);color:var(--major);border:1px solid rgba(251,146,60,0.2); }
.b-minor    { background:rgba(52,211,153,0.1);color:var(--minor);border:1px solid rgba(52,211,153,0.2); }
.b-type     { background:rgba(124,92,252,0.1);color:var(--accent2);border:1px solid rgba(124,92,252,0.2); }
.b-time     { background:rgba(56,189,248,0.1);color:var(--accent3);border:1px solid rgba(56,189,248,0.2); }
.narrative  { font-size:0.845rem;color:var(--text);line-height:1.75; }
.bug-text   { font-size:0.78rem;color:var(--muted);font-style:italic;margin-bottom:0.4rem;line-height:1.5;border-left:2px solid var(--dim);padding-left:0.6rem; }
.sim-block  { background:rgba(255,255,255,0.02);border-left:2px solid rgba(167,139,250,0.35);border-radius:0 7px 7px 0;padding:0.6rem 0.8rem;margin-top:0.65rem;font-size:0.77rem;color:var(--muted); }
.sim-item   { font-family:'Syne',sans-serif;font-size:0.65rem;color:var(--dim);background:rgba(255,255,255,0.025);border-radius:5px;padding:0.25rem 0.42rem;margin-top:0.32rem; }

/* ── Step pulse ── */
.step-line { display:flex;align-items:center;gap:0.42rem;font-size:0.79rem;color:var(--muted); }
.pdot { width:6px;height:6px;background:var(--accent);border-radius:50%;flex-shrink:0;animation:pulse 1.3s infinite; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.28;transform:scale(0.72)} }

/* ── Input bar — Streamlit-native, no fixed position ── */
.ibar-outer {
    max-width: 720px;
    margin: 0.5rem auto 0;
    padding: 0 0;
}
.ibar-wrap {
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.11);
    border-radius: 14px;
    padding: 0.4rem 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

div[data-testid="stTextInput"] input {
    background: transparent !important;
    border: none !important;
    color: var(--text) !important;
    font-family: 'Epilogue', sans-serif !important;
    font-size: 0.88rem !important;
    outline: none !important;
    box-shadow: none !important;
    padding: 0.3rem 0.2rem !important;
    caret-color: var(--accent2) !important;
}
div[data-testid="stTextInput"] > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Plus button */
div[data-testid="stButton"]:has(button[kind="secondary"]) button {
    border-radius: 9px !important;
    padding: 0.35rem 0.7rem !important;
    font-size: 1rem !important;
    line-height: 1 !important;
}

/* Send button */
.send-btn-wrap button {
    background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
    color: white !important;
    border: none !important;
    border-radius: 9px !important;
    font-size: 0.85rem !important;
    padding: 0.38rem 0.75rem !important;
    box-shadow: 0 0 12px var(--glow) !important;
    cursor: pointer !important;
}

.stButton > button {
    background: var(--surface2) !important;
    color: var(--muted) !important;
    border: 1px solid var(--border) !important;
    border-radius: 9px !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 0.77rem !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent2) !important;
    background: rgba(124,92,252,0.1) !important;
}

.stDownloadButton > button {
    background: linear-gradient(135deg,var(--accent),var(--accent2)) !important;
    color: white !important; border: none !important;
    border-radius: 9px !important;
    font-family: 'Syne',sans-serif !important;
    font-size: 0.77rem !important; font-weight: 700 !important;
    padding: 0.45rem 1rem !important;
    box-shadow: 0 0 12px var(--glow) !important;
    cursor: pointer !important;
}

div[data-testid="stFileUploader"] {
    background: rgba(124,92,252,0.06) !important;
    border: 1px dashed rgba(124,92,252,0.32) !important;
    border-radius: 10px !important;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


class AttentionPooling(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.attn = nn.Linear(hidden_size, 1)

    def forward(self, hidden_states, attention_mask):
        scores = self.attn(hidden_states).squeeze(-1)
        mask = (1.0 - attention_mask.float()) * -10000.0
        scores = scores + mask
        weights = torch.softmax(scores, dim=-1).unsqueeze(-1)
        return (hidden_states * weights).sum(dim=1)


def _make_head(in_dim, out_dim):
    from collections import OrderedDict
    return nn.Sequential(OrderedDict([
        ("0", nn.Linear(in_dim, 512)),
        ("1", nn.BatchNorm1d(512)),
        ("2", nn.GELU()),
        ("3", nn.Dropout(0.3)),
        ("4", nn.Linear(512, 256)),
        ("5", nn.BatchNorm1d(256)),
        ("6", nn.GELU()),
        ("7", nn.Dropout(0.3)),
        ("8", nn.Linear(256, out_dim)),
    ]))


class MultiTaskClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.bert = BertModel.from_pretrained("bert-base-uncased")
        h = self.bert.config.hidden_size
        self.attn_pooling = AttentionPooling(h)
        self.head_bugtype  = _make_head(h, 5)
        self.head_severity = _make_head(h, 3)
        self.head_fixtime  = _make_head(h, 3)

    def forward(self, input_ids, attention_mask):
        out = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = self.attn_pooling(out.last_hidden_state, attention_mask)
        return self.head_bugtype(pooled), self.head_severity(pooled), self.head_fixtime(pooled)


@st.cache_resource(show_spinner=False)
def load_sbert():
    return SentenceTransformer(SBERT_PATH, device=DEVICE)


@st.cache_resource(show_spinner=False)
def load_classifier():
    tok = BertTokenizer.from_pretrained("bert-base-uncased")
    mdl = MultiTaskClassifier()
    ckpt = torch.load(CLASSIFIER_PATH, map_location=DEVICE, weights_only=False)
    state = ckpt["model_state_dict"]
    load_result = mdl.load_state_dict(state, strict=False)
    missing = load_result.missing_keys
    unexpected = load_result.unexpected_keys
    st.session_state["_load_missing"] = missing
    st.session_state["_load_unexpected"] = unexpected
    mdl.to(DEVICE)
    mdl.eval()
    return tok, mdl


def extract_paragraphs(uploaded_file):
    reader = PdfReader(uploaded_file)
    paras = []
    for page in reader.pages:
        raw = page.extract_text() or ""
        blocks = re.split(r'\n{2,}', raw)
        for b in blocks:
            cleaned = re.sub(r'\s+', ' ', b).strip()
            if len(cleaned) > 40:
                paras.append(cleaned)
    return paras


def deduplicate(bugs, sbert_model, threshold=0.82):
    if not bugs:
        return [], {}, []
    emb = sbert_model.encode(bugs, normalize_embeddings=True, show_progress_bar=False)
    sim = np.dot(emb, emb.T)
    visited = [False] * len(bugs)
    groups = []
    for i in range(len(bugs)):
        if not visited[i]:
            g = [i]
            visited[i] = True
            for j in range(i + 1, len(bugs)):
                if not visited[j] and sim[i][j] >= threshold:
                    g.append(j)
                    visited[j] = True
            groups.append(g)
    unique = [g[0] for g in groups]
    dup_map = {g[0]: g[1:] for g in groups if len(g) > 1}
    return unique, dup_map, groups


def classify_bug(text, tokenizer, model):
    model.eval()
    enc = tokenizer(text, max_length=256, padding="max_length", truncation=True, return_tensors="pt")
    iids = enc["input_ids"].to(DEVICE)
    mask = enc["attention_mask"].to(DEVICE)
    with torch.no_grad():
        bt, sv, ft = model(iids, mask)
    return BUG_TYPE_LABELS[bt.argmax(1).item()], SEVERITY_LABELS[sv.argmax(1).item()], FIX_TIME_LABELS[ft.argmax(1).item()]


def build_pdf(results, bugs, dup_map, total, dups):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    ts  = ParagraphStyle("T",  parent=styles["Title"],   fontSize=20, textColor=colors.HexColor("#7c5cfc"), spaceAfter=6, fontName="Helvetica-Bold")
    h2s = ParagraphStyle("H2", parent=styles["Heading2"],fontSize=12, textColor=colors.HexColor("#5a5a8a"), spaceBefore=14, spaceAfter=5, fontName="Helvetica-Bold")
    bs  = ParagraphStyle("B",  parent=styles["Normal"],  fontSize=10, leading=16, spaceAfter=7, fontName="Helvetica")
    ms  = ParagraphStyle("M",  parent=styles["Normal"],  fontSize=9,  textColor=colors.HexColor("#7878a8"), leftIndent=10, spaceAfter=4, fontName="Helvetica")
    ls  = ParagraphStyle("L",  parent=styles["Normal"],  fontSize=9,  textColor=colors.HexColor("#7c5cfc"), fontName="Helvetica-Bold", spaceAfter=3)
    story = [
        Paragraph("NLP Bug Classifier", ts),
        Paragraph("Automated Bug Triage Report", styles["Normal"]),
        Spacer(1, 0.2*inch),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2a2a3d")),
        Spacer(1, 0.15*inch),
        Paragraph("Analytics Summary", h2s),
        Paragraph(f"Total Bugs Extracted: <b>{total}</b>", bs),
        Paragraph(f"Duplicates Detected: <b>{dups}</b>", bs),
        Paragraph(f"Unique Bugs Classified: <b>{len(results)}</b>", bs),
    ]
    tc = Counter([r["bug_type"] for r in results])
    sc = Counter([r["severity"] for r in results])
    story.append(Paragraph("Bug Type Breakdown:", ls))
    for bt, cnt in tc.most_common():
        story.append(Paragraph(f"• {bt}: {cnt}", ms))
    story.append(Paragraph("Severity Breakdown:", ls))
    for sv, cnt in sc.most_common():
        story.append(Paragraph(f"• {sv}: {cnt}", ms))
    qs = ParagraphStyle("Q", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#5a5a8a"),
                        leftIndent=12, fontName="Helvetica-Oblique", spaceAfter=6, leading=14)
    story += [Spacer(1, 0.15*inch), HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2a2a3d")), Paragraph("Classified Bug Reports", h2s)]
    for i, r in enumerate(results):
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"Bug #{i+1}", ls))
        bug_text = r.get("text", "")
        if bug_text:
            safe_text = bug_text.replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(f'"{safe_text}"', qs))
        story.append(Paragraph(
            f"As per the analyzed report, the severity of the current running bug is <b>{r['severity']}</b>. "
            f"With the current severity, we found out that the bug is a <b>{r['bug_type']}</b> issue. "
            f"With this bug running in the back, I would find out that the fix time on the basis of the severity is <b>{r['fix_time']}</b>.", bs))
        dup_list = dup_map.get(r["original_index"], [])
        if dup_list:
            story.append(Paragraph("We also found that there are similar bugs with the same outcome in your input. And this all will take similar timeline or fix time:", ms))
            for d in dup_list:
                dup_text = bugs[d][:120] + ("..." if len(bugs[d]) > 120 else "")
                safe_dup = dup_text.replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(f'• "{safe_dup}"', ms))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd")))
    doc.build(story)
    buf.seek(0)
    return buf.read()


def sev_cls(s):
    return {"critical": "b-critical", "major": "b-major", "minor": "b-minor"}.get(s, "b-type")


def ai_bubble(html):
    st.markdown(f"""
    <div class="chat-col">
      <div class="msg-row">
        <div class="mav ai">🐛</div>
        <div class="mbubble ai">{html}</div>
      </div>
    </div>""", unsafe_allow_html=True)


def user_bubble(text):
    st.markdown(f"""
    <div class="chat-col">
      <div class="msg-row user">
        <div class="mav user">VK</div>
        <div class="mbubble user">{text}</div>
      </div>
    </div>""", unsafe_allow_html=True)


def render_analytics(results, total, dups):
    tc = Counter([r["bug_type"] for r in results])
    sc = Counter([r["severity"] for r in results])
    n = len(results)
    sev_colors = {"critical": "#f87171", "major": "#fb923c", "minor": "#34d399"}
    bars = "".join(
        f'<div class="t-row"><div class="t-meta"><span>{bt}</span><span>{cnt} · {int(cnt/n*100)}%</span></div>'
        f'<div class="t-track"><div class="t-fill" style="width:{int(cnt/n*100)}%"></div></div></div>'
        for bt, cnt in tc.most_common()
    )
    sev_bars = "".join(
        f'<div class="t-row"><div class="t-meta"><span style="color:{sev_colors.get(sv,"#7c5cfc")}">{sv.upper()}</span><span>{cnt} · {int(cnt/n*100)}%</span></div>'
        f'<div class="t-track"><div class="t-fill" style="width:{int(cnt/n*100)}%;background:linear-gradient(90deg,{sev_colors.get(sv,"#7c5cfc")},{sev_colors.get(sv,"#7c5cfc")}88)"></div></div></div>'
        for sv, cnt in sc.most_common()
    )
    ai_bubble(f"""
    <div class="a-card">
        <div class="a-lbl">Analytics Overview</div>
        <div class="stat-grid">
            <div class="stat-box"><div class="stat-num">{total}</div><div class="stat-lbl">Total Bugs</div></div>
            <div class="stat-box"><div class="stat-num" style="color:#f87171">{dups}</div><div class="stat-lbl">Duplicates</div></div>
            <div class="stat-box"><div class="stat-num" style="color:#34d399">{n}</div><div class="stat-lbl">Unique</div></div>
        </div>
        <div class="a-sub">Bug Type Trend</div>{bars}
        <div class="a-sub">Severity Distribution</div>{sev_bars}
    </div>""")


def render_bug(r, idx, bugs, dup_map):
    dl = dup_map.get(r["original_index"], [])
    sim_html = ""
    if dl:
        items = "".join(
            f'<div class="sim-item">"{bugs[d][:100]}{"..." if len(bugs[d])>100 else ""}"</div>'
            for d in dl
        )
        sim_html = (
            f'<div class="sim-block">'
            f'We also found that there are similar bugs with the same outcome in your input. '
            f'And this all will take similar timeline or fix time:'
            f'{items}</div>'
        )
    bug_text = r.get("text", "")
    text_preview = f'<div class="bug-text">"{bug_text[:200]}{"..." if len(bug_text)>200 else ""}"</div>' if bug_text else ""
    ai_bubble(f"""
    <div class="bug-card">
        <div class="bug-num">Bug #{idx+1}</div>
        {text_preview}
        <div class="badge-row" style="margin-top:0.5rem;">
            <span class="badge {sev_cls(r['severity'])}">{r['severity'].upper()}</span>
            <span class="badge b-type">{r['bug_type']}</span>
            <span class="badge b-time">⏱ {r['fix_time']}</span>
        </div>
        <div class="narrative">
            As per the analyzed report, the severity of the current running bug is <strong>{r['severity']}</strong>.
            With the current severity, we found out that the bug is a <strong>{r['bug_type']}</strong> issue.
            With this bug running in the back, I would find out that the fix time on the basis of the severity is <strong>{r['fix_time']}</strong>.
        </div>
        {sim_html}
    </div>""")



def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div class="sb-logo">
            <div class="sb-icon">🐛</div>
            <div><div class="sb-name">BugClassifier</div><div class="sb-sub">NLP Triage Pipeline</div></div>
        </div>""", unsafe_allow_html=True)

        if st.button("＋  New analysis", key="new_btn", use_container_width=True):
            for k in ["results", "pdf_bytes", "bugs", "dup_map"]:
                st.session_state[k] = None
            st.session_state.total_bugs = 0
            st.session_state.dup_count  = 0
            st.session_state.show_upload = False
            st.rerun()

        st.markdown('<div class="sb-sec">Recents</div>', unsafe_allow_html=True)
        history = st.session_state.get("history", [])
        for i, h in enumerate(reversed(history[-8:])):
            active = "active" if i == 0 and st.session_state.get("results") else ""
            st.markdown(f'<div class="hist-item {active}"><div class="hist-dot"></div>{h[:24]}{"…" if len(h)>24 else ""}</div>', unsafe_allow_html=True)
        if not history:
            st.markdown('<div style="font-size:0.72rem;color:#3a3a60;padding:0.3rem 0.4rem;">No recent analyses</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div style="margin-top:auto;padding-top:1.5rem;">
            <div class="sb-foot">
                <div class="u-av">VK</div>
                <div class="u-name">Varad Kulkarni</div>
                <div class="dev-chip">{DEVICE.upper()}</div>
            </div>
        </div>""", unsafe_allow_html=True)


def main():
    for k, v in {"results": None, "pdf_bytes": None, "bugs": None, "dup_map": None,
                 "total_bugs": 0, "dup_count": 0, "show_upload": False, "history": [],
                 "pending_text": None, "pending_file": None, "processing": False,
                 "user_label": ""}.items():
        if k not in st.session_state:
            st.session_state[k] = v

    render_sidebar()

    st.markdown("""
    <div class="chat-hdr">
        <div class="chat-hdr-title">NLP Bug Classifier</div>
        <div class="chat-hdr-sub">Semantic deduplication · Multi-task BERT classification</div>
    </div>""", unsafe_allow_html=True)

    if st.session_state.results is None and not st.session_state.processing:
        st.markdown("""
        <div class="welcome">
            <div class="wc-icon">🐛</div>
            <div class="wc-title">What are you working on?</div>
            <div class="wc-sub">Upload a PDF bug report using the <strong>+</strong> button below. I'll deduplicate, classify by type, severity &amp; fix time, and generate a full report.</div>
            <div class="chips">
                <div class="chip">📄 PDF bug reports</div>
                <div class="chip">🔍 85% similarity dedup</div>
                <div class="chip">⚡ Crash · Memory · UI · Freeze</div>
                <div class="chip">📊 PDF export</div>
            </div>
        </div>""", unsafe_allow_html=True)
    elif st.session_state.processing:
        if st.session_state.get("user_label"):
            user_bubble(st.session_state.user_label)
    else:
        results  = st.session_state.results
        bugs     = st.session_state.bugs
        dup_map  = st.session_state.dup_map
        total    = st.session_state.total_bugs
        dups     = st.session_state.dup_count

        user_bubble(st.session_state.get("user_label") or f"📄 Uploaded bug report — {total} text blocks extracted")
        ai_bubble("Analysis complete. Here's your full triage report:")
        render_analytics(results, total, dups)
        ai_bubble(f"Classified <strong>{len(results)}</strong> unique bugs:")
        for i, r in enumerate(results):
            render_bug(r, i, bugs, dup_map)
        ai_bubble("✅ Report complete. Download the PDF below.")

        c1, c2, _ = st.columns([2, 2, 5])
        with c1:
            st.download_button("⬇ Download PDF", data=st.session_state.pdf_bytes,
                               file_name="nlp_bug_report.pdf", mime="application/pdf")
        with c2:
            if st.button("🔄 New analysis", key="reset_btn"):
                for k in ["results", "pdf_bytes", "bugs", "dup_map"]:
                    st.session_state[k] = None
                st.session_state.total_bugs = 0
                st.session_state.dup_count  = 0
                st.session_state.show_upload = False
                st.rerun()

    st.markdown('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:0.75rem 0;">', unsafe_allow_html=True)

    if st.session_state.processing:
        with st.spinner(""):
            pending_text = st.session_state.pending_text
            pending_file = st.session_state.pending_file

            if pending_file is not None:
                ai_bubble('<div class="step-line"><div class="pdot"></div>Loading models…</div>')
                sbert = load_sbert()
                tok, clf = load_classifier()
                missing_keys = st.session_state.get("_load_missing", [])
                unexpected_keys = st.session_state.get("_load_unexpected", [])
                ai_bubble(
                    f'<div style="font-size:0.72rem;font-family:monospace;color:#fb923c;">'
                    f'<b>Model load report</b><br>'
                    f'Missing ({len(missing_keys)}): {missing_keys}<br>'
                    f'Unexpected ({len(unexpected_keys)}): {unexpected_keys}'
                    f'</div>'
                )
                ai_bubble('<div class="step-line"><div class="pdot"></div>Parsing PDF and extracting bug blocks…</div>')
                bugs = extract_paragraphs(pending_file)
                total = len(bugs)
                if total == 0:
                    ai_bubble("⚠️ No readable text found. Please upload a PDF with selectable text.")
                    st.session_state.processing = False
                    st.session_state.pending_file = None
                    st.rerun()
                ai_bubble(f'<div class="step-line"><div class="pdot"></div>Extracted <strong>{total}</strong> blocks · running SBERT deduplication…</div>')
                unique_ids, dup_map, _ = deduplicate(bugs, sbert)
                dup_count = total - len(unique_ids)
                ai_bubble(f'<div class="step-line"><div class="pdot"></div><strong>{len(unique_ids)}</strong> unique · <strong>{dup_count}</strong> duplicates · classifying…</div>')
                results = []
                for idx in unique_ids:
                    bt, sv, ft = classify_bug(bugs[idx], tok, clf)
                    results.append({"original_index": idx, "text": bugs[idx], "bug_type": bt, "severity": sv, "fix_time": ft, "duplicates": dup_map.get(idx, [])})
                pdf_bytes = build_pdf(results, bugs, dup_map, total, dup_count)
                fname = pending_file.name
                st.session_state.results = results
                st.session_state.bugs = bugs
                st.session_state.dup_map = dup_map
                st.session_state.total_bugs = total
                st.session_state.dup_count = dup_count
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.processing = False
                st.session_state.pending_file = None
                st.session_state.show_upload = False
                if fname not in st.session_state.history:
                    st.session_state.history.append(fname)
                st.rerun()

            elif pending_text is not None:
                raw = pending_text
                ai_bubble('<div class="step-line"><div class="pdot"></div>Loading models…</div>')
                sbert = load_sbert()
                tok, clf = load_classifier()
                missing_keys = st.session_state.get("_load_missing", [])
                unexpected_keys = st.session_state.get("_load_unexpected", [])
                ai_bubble(
                    f'<div style="font-size:0.72rem;font-family:monospace;color:#fb923c;">'
                    f'<b>Model load report</b><br>'
                    f'Missing ({len(missing_keys)}): {missing_keys}<br>'
                    f'Unexpected ({len(unexpected_keys)}): {unexpected_keys}'
                    f'</div>'
                )
                ai_bubble('<div class="step-line"><div class="pdot"></div>Splitting text into bug blocks…</div>')
                numbered = re.split(r'(?=Bug\s+\d+\s*[:\-])', raw, flags=re.IGNORECASE)
                if len(numbered) > 1:
                    bugs = [p.strip() for p in numbered if len(p.strip()) > 10]
                else:
                    by_newline = re.split(r'\n+', raw)
                    if len(by_newline) > 1:
                        bugs = [p.strip() for p in by_newline if len(p.strip()) > 10]
                    else:
                        bugs = [p.strip() for p in re.split(r'(?<=[.!?])\s{2,}', raw) if len(p.strip()) > 10]
                if not bugs:
                    bugs = [raw]
                total = len(bugs)
                ai_bubble(f'<div class="step-line"><div class="pdot"></div>Extracted <strong>{total}</strong> blocks · running SBERT deduplication…</div>')
                unique_ids, dup_map, _ = deduplicate(bugs, sbert)
                dup_count = total - len(unique_ids)
                ai_bubble(f'<div class="step-line"><div class="pdot"></div><strong>{len(unique_ids)}</strong> unique · <strong>{dup_count}</strong> duplicates · classifying…</div>')
                results = []
                for idx in unique_ids:
                    bt, sv, ft = classify_bug(bugs[idx], tok, clf)
                    results.append({"original_index": idx, "text": bugs[idx], "bug_type": bt, "severity": sv, "fix_time": ft, "duplicates": dup_map.get(idx, [])})
                pdf_bytes = build_pdf(results, bugs, dup_map, total, dup_count)
                entry = raw[:30] + "…"
                st.session_state.results = results
                st.session_state.bugs = bugs
                st.session_state.dup_map = dup_map
                st.session_state.total_bugs = total
                st.session_state.dup_count = dup_count
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.processing = False
                st.session_state.pending_text = None
                if entry not in st.session_state.history:
                    st.session_state.history.append(entry)
                st.rerun()

    if st.session_state.show_upload and not st.session_state.processing:
        uploaded = st.file_uploader(
            "Upload PDF bug report",
            type=["pdf"],
            key="file_upload",
            label_visibility="visible"
        )
        if uploaded is not None:
            st.session_state.user_label = f"📄 {uploaded.name}"
            st.session_state.pending_file = uploaded
            st.session_state.processing = True
            st.session_state.show_upload = False
            st.rerun()

    st.markdown('<div class="ibar-outer"><div class="ibar-wrap">', unsafe_allow_html=True)
    col_plus, col_text, col_send = st.columns([0.6, 10, 0.8])

    with col_plus:
        if st.button("＋", key="plus_btn", help="Upload a PDF bug report"):
            st.session_state.show_upload = not st.session_state.show_upload
            st.rerun()

    with col_text:
        text_val = st.text_input(
            "msg",
            placeholder="Paste a bug description or use + to upload a PDF…",
            label_visibility="collapsed",
            key="user_text_input"
        )

    with col_send:
        send_clicked = st.button("➤", key="send_btn", help="Send")

    st.markdown("</div></div>", unsafe_allow_html=True)

    if send_clicked:
        raw = st.session_state.get("user_text_input", "").strip()
        if raw and not st.session_state.processing:
            preview = raw[:120] + ("…" if len(raw) > 120 else "")
            st.session_state.user_label = preview
            st.session_state.pending_text = raw
            st.session_state.processing = True
            st.rerun()


main()