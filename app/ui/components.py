import streamlit as st
from app.helpers.config import (
    APP_TITLE, APP_ICON, APP_VERSION, DEVICE,
    SEVERITY_COLORS, CONF_THRESHOLD, TEMPERATURE,
)
from app.helpers.trend_analysis import (
    compute_session_analytics,
    trend_bars_html,
)
from app.helpers.chat_history import list_sessions, clear_all_sessions


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Epilogue:wght@300;400;500;600&display=swap');

:root {
    --sidebar-bg : #0d0b1e;
    --main-bg    : #0a0818;
    --surface    : rgba(255,255,255,0.04);
    --surface2   : rgba(255,255,255,0.07);
    --border     : rgba(255,255,255,0.08);
    --accent     : #7c5cfc;
    --accent2    : #a78bfa;
    --accent3    : #38bdf8;
    --glow       : rgba(124,92,252,0.28);
    --text       : #ededff;
    --muted      : #7878a8;
    --dim        : #44446a;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { font-family: 'Epilogue', sans-serif; background: var(--main-bg); color: var(--text); }

.stApp {
    background:
        radial-gradient(ellipse 130% 70% at 65% -15%, rgba(124,92,252,0.18) 0%, transparent 55%),
        radial-gradient(ellipse 70%  50% at -5% 85%, rgba(56,189,248,0.09) 0%, transparent 50%),
        #0a0818;
}

section[data-testid="stSidebar"] {
    background   : var(--sidebar-bg) !important;
    border-right : 1px solid var(--border) !important;
    min-width    : 256px !important;
    max-width    : 256px !important;
}
section[data-testid="stSidebar"] > div { padding: 0 !important; }
header[data-testid="stHeader"]         { display: none !important; }

.main .block-container {
    padding    : 0 !important;
    max-width  : 100% !important;
}

.chat-col {
    max-width : 740px;
    margin    : 0 auto;
    padding   : 0 1.5rem;
}

.chat-hdr {
    max-width     : 740px;
    margin        : 0 auto;
    padding       : 0.9rem 1.5rem 0.75rem;
    border-bottom : 1px solid var(--border);
    margin-bottom : 0.75rem;
}
.chat-hdr-title { font-family:'Syne',sans-serif; font-size:0.92rem; font-weight:700; color:var(--text); }
.chat-hdr-sub   { font-size:0.67rem; color:var(--muted); margin-top:2px; }

.sb-logo { display:flex; align-items:center; gap:0.6rem; padding:0.4rem 0 0.9rem; border-bottom:1px solid var(--border); margin-bottom:0.6rem; }
.sb-icon { width:32px; height:32px; background:linear-gradient(135deg,var(--accent),var(--accent2)); border-radius:9px; display:flex; align-items:center; justify-content:center; font-size:0.95rem; box-shadow:0 0 14px var(--glow); flex-shrink:0; }
.sb-name { font-family:'Syne',sans-serif; font-size:0.86rem; font-weight:700; color:var(--text); }
.sb-sub  { font-size:0.6rem; color:var(--muted); }
.sb-sec  { font-size:0.6rem; font-weight:700; letter-spacing:0.09em; color:var(--dim); text-transform:uppercase; padding:0.55rem 0.3rem 0.25rem; }

.hist-item { display:flex; align-items:center; gap:0.45rem; padding:0.48rem 0.65rem; border-radius:7px; font-size:0.77rem; color:var(--muted); overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.hist-item.active { background:rgba(124,92,252,0.13); color:var(--accent2); border-left:2px solid var(--accent); padding-left:calc(0.65rem - 2px); }
.hist-dot { width:5px; height:5px; border-radius:50%; background:var(--dim); flex-shrink:0; }
.hist-item.active .hist-dot { background:var(--accent); }

.sb-foot { border-top:1px solid var(--border); padding-top:0.7rem; margin-top:1rem; display:flex; align-items:center; gap:0.5rem; }
.u-av    { width:26px; height:26px; border-radius:50%; background:linear-gradient(135deg,var(--accent),var(--accent3)); display:flex; align-items:center; justify-content:center; font-size:0.62rem; font-weight:700; color:#fff; flex-shrink:0; }
.u-name  { font-size:0.76rem; color:var(--muted); }
.dev-chip { margin-left:auto; background:rgba(124,92,252,0.13); color:var(--accent2); border:1px solid rgba(124,92,252,0.27); border-radius:20px; padding:0.11rem 0.42rem; font-size:0.57rem; font-family:'Syne',sans-serif; font-weight:700; }

.msg-row       { display:flex; gap:0.8rem; align-items:flex-start; margin-bottom:0.9rem; }
.msg-row.user  { flex-direction:row-reverse; }
.mav           { width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:0.78rem; flex-shrink:0; margin-top:2px; }
.mav.ai        { background:linear-gradient(135deg,var(--accent),var(--accent2)); box-shadow:0 0 10px var(--glow); }
.mav.user      { background:var(--surface2); border:1px solid var(--border); font-size:0.62rem; font-weight:700; color:var(--muted); }
.mbubble       { max-width:88%; padding:0.8rem 1rem; border-radius:14px; font-size:0.875rem; line-height:1.75; color:var(--text); }
.mbubble.ai    { background:var(--surface); border:1px solid var(--border); border-radius:4px 14px 14px 14px; }
.mbubble.user  { background:linear-gradient(135deg,rgba(124,92,252,0.22),rgba(167,139,250,0.13)); border:1px solid rgba(124,92,252,0.22); border-radius:14px 4px 14px 14px; }

.welcome { max-width:740px; margin:0 auto; text-align:center; padding:3rem 1.5rem 1.5rem; }
.wc-icon  { width:62px; height:62px; background:linear-gradient(135deg,var(--accent),var(--accent2)); border-radius:18px; display:flex; align-items:center; justify-content:center; font-size:1.9rem; margin:0 auto 1.1rem; box-shadow:0 0 40px var(--glow); }
.wc-title { font-family:'Syne',sans-serif; font-size:1.7rem; font-weight:800; background:linear-gradient(135deg,#f0f0ff,var(--accent2)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:0.5rem; }
.wc-sub   { font-size:0.85rem; color:var(--muted); line-height:1.65; max-width:460px; margin:0 auto 1.5rem; }
.chips    { display:flex; flex-wrap:wrap; gap:0.4rem; justify-content:center; }
.chip     { padding:0.35rem 0.85rem; background:var(--surface); border:1px solid var(--border); border-radius:20px; font-size:0.73rem; color:var(--muted); }

.a-card  { background:rgba(255,255,255,0.025); border:1px solid var(--border); border-radius:14px; padding:1.1rem 1.3rem; }
.a-lbl   { font-family:'Syne',sans-serif; font-size:0.65rem; font-weight:700; letter-spacing:0.08em; color:var(--accent); text-transform:uppercase; margin-bottom:0.75rem; }
.a-sub   { font-family:'Syne',sans-serif; font-size:0.63rem; font-weight:700; letter-spacing:0.07em; color:var(--accent); text-transform:uppercase; margin:0.75rem 0 0.5rem; }
.stat-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:0.65rem; margin-bottom:0.9rem; }
.stat-box  { background:rgba(255,255,255,0.03); border:1px solid var(--border); border-radius:11px; padding:0.75rem; text-align:center; }
.stat-num  { font-family:'Syne',sans-serif; font-size:1.7rem; font-weight:800; color:var(--accent2); line-height:1; }
.stat-lbl  { font-size:0.67rem; color:var(--muted); margin-top:0.25rem; }

.bug-card  { background:rgba(255,255,255,0.025); border:1px solid var(--border); border-radius:13px; padding:1rem 1.1rem 1rem 1.2rem; position:relative; overflow:hidden; }
.bug-card::before { content:''; position:absolute; left:0; top:0; bottom:0; width:3px; background:linear-gradient(180deg,var(--accent),var(--accent2)); }
.bug-num   { font-family:'Syne',sans-serif; font-size:0.62rem; font-weight:700; letter-spacing:0.08em; color:var(--dim); text-transform:uppercase; margin-bottom:0.45rem; }
.bug-text  { font-size:0.78rem; color:var(--muted); font-style:italic; margin-bottom:0.4rem; line-height:1.5; border-left:2px solid var(--dim); padding-left:0.6rem; }
.badge-row { display:flex; gap:0.35rem; flex-wrap:wrap; }
.badge     { padding:0.2rem 0.6rem; border-radius:20px; font-size:0.65rem; font-weight:700; font-family:'Syne',sans-serif; letter-spacing:0.04em; }
.b-critical { background:rgba(248,113,113,0.1); color:#f87171; border:1px solid rgba(248,113,113,0.22); }
.b-major    { background:rgba(251,146,60,0.1);  color:#fb923c; border:1px solid rgba(251,146,60,0.22); }
.b-minor    { background:rgba(52,211,153,0.1);  color:#34d399; border:1px solid rgba(52,211,153,0.22); }
.b-uncertain{ background:rgba(167,139,250,0.1); color:#a78bfa; border:1px solid rgba(167,139,250,0.22); }
.b-type    { background:rgba(124,92,252,0.1);  color:var(--accent2); border:1px solid rgba(124,92,252,0.22); }
.b-time    { background:rgba(56,189,248,0.1);  color:var(--accent3); border:1px solid rgba(56,189,248,0.22); }
.narrative { font-size:0.855rem; color:var(--text); line-height:1.75; margin-top:0.65rem; }
.sim-block { background:rgba(255,255,255,0.02); border-left:2px solid rgba(167,139,250,0.35); border-radius:0 7px 7px 0; padding:0.6rem 0.8rem; margin-top:0.65rem; font-size:0.77rem; color:var(--muted); }
.sim-item  { font-family:'Syne',sans-serif; font-size:0.65rem; color:var(--dim); background:rgba(255,255,255,0.025); border-radius:5px; padding:0.25rem 0.42rem; margin-top:0.32rem; }
.conf-wrap { margin-top:0.7rem; padding-top:0.6rem; border-top:1px solid var(--border); }
.conf-lbl  { font-family:'Syne',sans-serif; font-size:0.62rem; font-weight:700; letter-spacing:0.07em; color:var(--accent); text-transform:uppercase; margin-bottom:0.4rem; }

.step-line { display:flex; align-items:center; gap:0.45rem; font-size:0.8rem; color:var(--muted); }
.pdot      { width:6px; height:6px; background:var(--accent); border-radius:50%; flex-shrink:0; animation:pulse 1.3s infinite; }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.3;transform:scale(0.75)} }

.ibar-outer { max-width:740px; margin:0.5rem auto 0; padding:0 0; }
.ibar-wrap  { background:rgba(255,255,255,0.045); border:1px solid rgba(255,255,255,0.11); border-radius:14px; padding:0.4rem 0.5rem; display:flex; align-items:center; gap:0.35rem; }
.ibar-wrap:focus-within { border-color:rgba(124,92,252,0.45); box-shadow:0 0 0 3px rgba(124,92,252,0.1); }

div[data-testid="stTextArea"] textarea {
    background:transparent !important; border:none !important;
    color:var(--text) !important; font-family:'Epilogue',sans-serif !important;
    font-size:0.87rem !important; resize:none !important;
    outline:none !important; box-shadow:none !important;
    padding:0.3rem 0.1rem !important; min-height:36px !important; line-height:1.5 !important;
}
div[data-testid="stTextArea"] > div            { background:transparent !important; border:none !important; }
div[data-testid="stTextArea"] > div > div      { background:transparent !important; }

div[data-testid="stFileUploader"] {
    background:rgba(124,92,252,0.06) !important;
    border:1px dashed rgba(124,92,252,0.3) !important;
    border-radius:10px !important; padding:0.5rem 0.75rem !important;
    margin-bottom:0.4rem;
}

.stDownloadButton > button {
    background:linear-gradient(135deg,var(--accent),var(--accent2)) !important;
    color:white !important; border:none !important; border-radius:9px !important;
    font-family:'Syne',sans-serif !important; font-size:0.78rem !important;
    font-weight:700 !important; padding:0.5rem 1.1rem !important;
    letter-spacing:0.04em !important; box-shadow:0 0 14px var(--glow) !important;
    cursor:pointer !important;
}

.stButton > button {
    background:var(--surface) !important; color:var(--muted) !important;
    border:1px solid var(--border) !important; border-radius:9px !important;
    font-family:'Syne',sans-serif !important; font-size:0.77rem !important;
    font-weight:600 !important; padding:0.45rem 1rem !important;
    cursor:pointer !important; transition:all 0.15s !important;
}
.stButton > button:hover {
    border-color:var(--accent) !important; color:var(--accent2) !important;
    background:rgba(124,92,252,0.1) !important;
}

::-webkit-scrollbar       { width:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:var(--border); border-radius:2px; }
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def render_header():
    st.markdown(f"""
    <div class="chat-hdr">
        <div class="chat-hdr-title">{APP_ICON} {APP_TITLE}</div>
        <div class="chat-hdr-sub">
            Semantic deduplication · Multi-task BERT classification ·
            Temperature T={TEMPERATURE} · Confidence ≥{int(CONF_THRESHOLD*100)}% · v{APP_VERSION}
        </div>
    </div>""", unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:1rem 0.7rem 0;">
            <div class="sb-logo">
                <div class="sb-icon">{APP_ICON}</div>
                <div>
                    <div class="sb-name">{APP_TITLE}</div>
                    <div class="sb-sub">NLP Triage Pipeline · v{APP_VERSION}</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div style="padding:0 0.7rem;">', unsafe_allow_html=True)

        if st.button("＋  New analysis", key="new_chat_btn", use_container_width=True):
            for k in ["results", "pdf_bytes", "bugs", "dup_map",
                      "show_upload", "processing", "pending_text",
                      "pending_file", "user_label", "session_id"]:
                st.session_state[k] = None if k not in [
                    "show_upload", "processing"] else False
            st.session_state.total_bugs = 0
            st.session_state.dup_count  = 0
            st.rerun()

        st.markdown('<div class="sb-sec">Recent Sessions</div>', unsafe_allow_html=True)

        sessions = list_sessions()
        current  = st.session_state.get("session_id", "")
        if sessions:
            for s in sessions[:8]:
                active = "active" if s["id"] == current else ""
                st.markdown(
                    f'<div class="hist-item {active}">'
                    f'<div class="hist-dot"></div>'
                    f'{s["label"][:26]}{"..." if len(s["label"])>26 else ""}'
                    f'</div>',
                    unsafe_allow_html=True
                )
            if st.button("Clear history", key="clear_hist"):
                clear_all_sessions()
                st.rerun()
        else:
            st.markdown(
                '<div style="font-size:0.73rem;color:#44446a;padding:0.4rem;">No sessions yet</div>',
                unsafe_allow_html=True
            )

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div style="padding:0 0.7rem;">
            <div class="sb-foot">
                <div class="u-av">VK</div>
                <div class="u-name">Varad Kulkarni</div>
                <div class="dev-chip">{DEVICE.upper()}</div>
            </div>
        </div>""", unsafe_allow_html=True)


def render_welcome():
    st.markdown("""
    <div class="welcome">
        <div class="wc-icon">🐛</div>
        <div class="wc-title">What are you working on?</div>
        <div class="wc-sub">
            Upload a PDF bug report or paste bug descriptions below.<br>
            I'll deduplicate, classify by type, severity &amp; fix time,
            and generate a full triage report.
        </div>
        <div class="chips">
            <div class="chip">📄 PDF upload</div>
            <div class="chip">✏️ Paste text</div>
            <div class="chip">🔍 SBERT dedup · 82% threshold</div>
            <div class="chip">⚡ Crash · Memory · UI · Freeze</div>
            <div class="chip">📊 PDF · CSV · XLSX export</div>
            <div class="chip">💡 AI solution suggestions</div>
        </div>
    </div>""", unsafe_allow_html=True)


def ai_bubble(html: str):
    st.markdown(f"""
    <div class="chat-col">
        <div class="msg-row">
            <div class="mav ai">🐛</div>
            <div class="mbubble ai">{html}</div>
        </div>
    </div>""", unsafe_allow_html=True)


def user_bubble(text: str):
    st.markdown(f"""
    <div class="chat-col">
        <div class="msg-row user">
            <div class="mav user">VK</div>
            <div class="mbubble user">{text}</div>
        </div>
    </div>""", unsafe_allow_html=True)


def step_bubble(message: str):
    ai_bubble(f'<div class="step-line"><div class="pdot"></div>{message}</div>')


def render_analytics(results: list[dict], total: int, dup_count: int):
    analytics  = compute_session_analytics(results, total, dup_count)
    sev_colors = SEVERITY_COLORS
    type_colors = {
        "Crash":     "#f87171",
        "Freeze":    "#38bdf8",
        "Memory":    "#fb923c",
        "UI/Visual": "#a78bfa",
        "Other":     "#7878a8",
        "Uncertain": "#44446a",
    }

    type_bars = trend_bars_html(analytics["type_counts"], analytics["unique"], type_colors)
    sev_bars  = trend_bars_html(analytics["sev_counts"],  analytics["unique"], sev_colors)

    avg_conf = round(
        (analytics["avg_bt_conf"] + analytics["avg_sv_conf"] + analytics["avg_ft_conf"]) / 3, 1
    )

    ai_bubble(f"""
    <div class="a-card">
        <div class="a-lbl">Analytics Overview</div>
        <div class="stat-grid">
            <div class="stat-box">
                <div class="stat-num">{total}</div>
                <div class="stat-lbl">Total Bugs</div>
            </div>
            <div class="stat-box">
                <div class="stat-num" style="color:#f87171">{dup_count}</div>
                <div class="stat-lbl">Duplicates</div>
            </div>
            <div class="stat-box">
                <div class="stat-num" style="color:#34d399">{analytics['unique']}</div>
                <div class="stat-lbl">Unique</div>
            </div>
        </div>
        <div class="stat-grid" style="margin-top:0;">
            <div class="stat-box">
                <div class="stat-num" style="font-size:1.2rem;color:#fb923c">{analytics['dup_rate']}%</div>
                <div class="stat-lbl">Dup Rate</div>
            </div>
            <div class="stat-box">
                <div class="stat-num" style="font-size:1.2rem;color:#a78bfa">{analytics['uncertain']}</div>
                <div class="stat-lbl">Uncertain</div>
            </div>
            <div class="stat-box">
                <div class="stat-num" style="font-size:1.2rem;color:#38bdf8">{avg_conf}%</div>
                <div class="stat-lbl">Avg Conf</div>
            </div>
        </div>
        <div class="a-sub">Bug Type Trend</div>
        {type_bars}
        <div class="a-sub">Severity Distribution</div>
        {sev_bars}
    </div>""")


def _sev_badge_class(severity: str) -> str:
    return {
        "critical":  "b-critical",
        "major":     "b-major",
        "minor":     "b-minor",
        "uncertain": "b-uncertain",
    }.get(severity.lower(), "b-uncertain")


def _conf_bars_html(r: dict) -> str:
    def bar(label, val, color):
        opacity = "1" if val >= CONF_THRESHOLD * 100 else "0.4"
        return (
            f'<div style="margin-bottom:0.28rem;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:0.64rem;color:var(--muted);margin-bottom:0.14rem;">'
            f'<span>{label}</span><span>{val}%</span></div>'
            f'<div style="background:rgba(255,255,255,0.05);border-radius:3px;height:4px;overflow:hidden;">'
            f'<div style="width:{min(val,100)}%;height:100%;border-radius:3px;'
            f'background:{color};opacity:{opacity};"></div>'
            f'</div></div>'
        )
    return (
        '<div class="conf-wrap">'
        f'<div class="conf-lbl">Confidence · T={TEMPERATURE}</div>'
        + bar("Bug Type", r.get("bt_conf", 0), "#a78bfa")
        + bar("Severity", r.get("sv_conf", 0), "#f87171")
        + bar("Fix Time", r.get("ft_conf", 0), "#38bdf8")
        + '</div>'
    )


def _uncertain_banner(r: dict) -> str:
    if not r.get("is_uncertain"):
        return ""
    bt = r.get("bt_candidates", [])
    sv = r.get("sv_candidates", [])
    ft = r.get("ft_candidates", [])
    lines = []
    if r["bug_type"] == "Uncertain" and len(bt) >= 2:
        lines.append(f'Type: {bt[0][0]} ({bt[0][1]}%) or {bt[1][0]} ({bt[1][1]}%)')
    if r["severity"] == "uncertain" and len(sv) >= 2:
        lines.append(f'Severity: {sv[0][0]} ({sv[0][1]}%) or {sv[1][0]} ({sv[1][1]}%)')
    if r["fix_time"] == "uncertain" and len(ft) >= 2:
        lines.append(f'Fix Time: {ft[0][0]} ({ft[0][1]}%) or {ft[1][0]} ({ft[1][1]}%)')
    body = "<br>".join(f'<span style="color:#e8e8f0;">{l}</span>' for l in lines)
    return (
        '<div style="background:rgba(251,146,60,0.1);border:1px solid rgba(251,146,60,0.25);'
        'border-radius:8px;padding:0.5rem 0.75rem;margin:0.5rem 0;font-size:0.74rem;color:#fb923c;">'
        f'⚠️ <strong>Low confidence</strong> — below {int(CONF_THRESHOLD*100)}% threshold<br>{body}'
        '</div>'
    )


def _similar_html(r: dict, bugs: list[str], dup_map: dict) -> str:
    dl = dup_map.get(r["original_index"], [])
    if not dl:
        return ""
    items = "".join(
        f'<div class="sim-item">"{bugs[d][:100]}{"..." if len(bugs[d])>100 else ""}"</div>'
        for d in dl
    )
    return (
        '<div class="sim-block">'
        'We also found similar bugs with the same outcome — they will take a similar timeline or fix time:'
        f'{items}</div>'
    )


def render_bug_card(r: dict, idx: int, bugs: list[str], dup_map: dict, show_solution_btn: bool = True):
    bug_text   = r.get("text", "")
    text_html  = (
        f'<div class="bug-text">"{bug_text[:200]}{"..." if len(bug_text)>200 else ""}"</div>'
        if bug_text else ""
    )
    sev_cls    = _sev_badge_class(r["severity"])
    uncertain  = _uncertain_banner(r)
    conf_html  = _conf_bars_html(r)
    sim_html   = _similar_html(r, bugs, dup_map)

    ai_bubble(f"""
    <div class="bug-card">
        <div class="bug-num">Bug #{idx+1}</div>
        {text_html}
        {uncertain}
        <div class="badge-row" style="margin-top:0.5rem;">
            <span class="badge {sev_cls}">{r['severity'].upper()}</span>
            <span class="badge b-type">{r['bug_type']}</span>
            <span class="badge b-time">⏱ {r['fix_time']}</span>
        </div>
        <div class="narrative">
            As per the analyzed report, the severity of the current running bug is
            <strong>{r['severity']}</strong>. With the current severity, we found out
            that the bug is a <strong>{r['bug_type']}</strong> issue. With this bug
            running in the back, I would find out that the fix time on the basis of
            the severity is <strong>{r['fix_time']}</strong>.
        </div>
        {conf_html}
        {sim_html}
    </div>""")

    if show_solution_btn:
        col_gap, col_btn = st.columns([11, 3])
        with col_btn:
            if st.button(
                "💡 Get Solution",
                key=f"sol_btn_{idx}_{r['original_index']}",
                help="AI-powered solution suggestion for this bug"
            ):
                st.session_state[f"show_solution_{idx}"] = True
                st.session_state[f"solution_bug_{idx}"]  = r.get("text", "")
                st.session_state[f"solution_type_{idx}"] = r.get("bug_type", "")
                st.rerun()


def render_export_buttons(pdf_bytes: bytes, results: list, bugs: list, dup_map: dict):
    from app.helpers.exporter import export_csv, export_xlsx, export_json

    ai_bubble("✅ Report complete. Download in your preferred format:")

    st.markdown('<div class="chat-col">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 3])

    with c1:
        st.download_button(
            "⬇ PDF", data=pdf_bytes,
            file_name="nlp_bug_report.pdf",
            mime="application/pdf"
        )
    with c2:
        st.download_button(
            "⬇ CSV", data=export_csv(results, bugs, dup_map),
            file_name="nlp_bug_report.csv",
            mime="text/csv"
        )
    with c3:
        try:
            xlsx_bytes = export_xlsx(results, bugs, dup_map)
            st.download_button(
                "⬇ XLSX", data=xlsx_bytes,
                file_name="nlp_bug_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except ImportError:
            st.caption("XLSX needs openpyxl")
    with c4:
        st.download_button(
            "⬇ JSON", data=export_json(results, bugs, dup_map),
            file_name="nlp_bug_report.json",
            mime="application/json"
        )
    with c5:
        if st.button("🔄 New analysis", key="reset_btn"):
            for k in ["results", "pdf_bytes", "bugs", "dup_map",
                      "show_upload", "processing", "pending_text",
                      "pending_file", "user_label"]:
                st.session_state[k] = None if k not in [
                    "show_upload", "processing"] else False
            st.session_state.total_bugs = 0
            st.session_state.dup_count  = 0
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def render_input_bar():
    st.markdown(
        '<hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:0.75rem 0;">',
        unsafe_allow_html=True
    )
    st.markdown('<div class="ibar-outer"><div class="ibar-wrap">', unsafe_allow_html=True)

    col_plus, col_text, col_send = st.columns([0.6, 10, 0.8])

    with col_plus:
        if st.button("＋", key="plus_btn", help="Upload PDF bug report"):
            st.session_state.show_upload = not st.session_state.get("show_upload", False)
            st.rerun()

    with col_text:
        text_val = st.text_input(
            "msg",
            placeholder="Paste bug descriptions or use + to upload PDF…",
            label_visibility="collapsed",
            key="user_text_input"
        )

    with col_send:
        send_clicked = st.button("➤", key="send_btn", help="Send")

    st.markdown("</div></div>", unsafe_allow_html=True)
    return send_clicked