import streamlit as st
from app.helpers.config import APP_TITLE, APP_ICON, APP_VERSION, DEVICE, SEVERITY_COLORS
from app.helpers.trend_analysis import compute_session_analytics, trend_bars_html
from app.helpers.chat_history import list_sessions, load_session, clear_all_sessions


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

:root {
    --bg          : #f8f7f4;
    --bg2         : #f0efe9;
    --sidebar-bg  : #1a1825;
    --surface     : #ffffff;
    --border      : #e8e6df;
    --border-dark : rgba(255,255,255,0.1);
    --text        : #1c1b20;
    --text-2      : #6b6880;
    --text-3      : #9896a8;
    --accent      : #6c47ff;
    --accent-soft : #ede9ff;
    --accent-2    : #a78bfa;
    --green       : #16a34a;
    --green-soft  : #dcfce7;
    --red         : #dc2626;
    --red-soft    : #fee2e2;
    --orange      : #ea580c;
    --orange-soft : #ffedd5;
    --shadow-sm   : 0 2px 8px rgba(0,0,0,0.04);
    --shadow-md   : 0 8px 24px rgba(0,0,0,0.06);
}

html, body {
    font-family: 'Inter', sans-serif !important;
    color: var(--text) !important;
    background-color: var(--bg) !important;
}

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important; 
    max-width: calc(800px + var(--canvas-width, 0px)) !important;
    padding-right: calc(var(--canvas-width, 0px) + 2rem) !important;
    transition: padding-right 0.15s ease, max-width 0.15s ease !important;
}

/* Hide default top header */
header[data-testid="stHeader"] { display: transparent !important; }

/* ── BUTTONS (General) ── */
div[data-testid="stButton"] > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
    border: 1px solid var(--border) !important;
    background-color: var(--surface) !important;
    color: var(--text) !important;
}
div[data-testid="stButton"] > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    box-shadow: var(--shadow-sm) !important;
}

/* ── TYPOGRAPHY & HEADER ── */
.app-header {
    text-align: center;
    margin-bottom: 1rem;
}
.app-header h1 {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 2.4rem;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.02em;
}
.app-header p {
    font-size: 1rem;
    color: var(--text-2);
    margin: 0;
}

/* ── EXPANDERS ── */
div[data-testid="stExpander"] {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    box-shadow: var(--shadow-sm) !important;
    overflow: hidden;
}
div[data-testid="stExpander"] summary {
    background-color: transparent !important;
    padding: 0.8rem 1rem !important;
    font-weight: 600 !important;
    color: var(--text) !important;
}

/* ── CHAT BUBBLES — Claude.ai layout ── */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── AI message row: avatar left + plain text, no bubble background ── */
.msg-wrap {
    animation: fadeIn 0.25s ease-out;
    margin-bottom: 1.6rem;
}
.msg-row {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}

/* Avatar circle */
.mav {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 2px;
}
.mav.ai {
    background: var(--accent);
    color: #fff;
    box-shadow: 0 2px 8px rgba(108,71,255,0.25);
}
.mav.user {
    background: var(--text);
    color: #fff;
    font-size: 0.6rem;
    letter-spacing: 0.03em;
}

/* AI message body — no bubble, just prose flow like Claude */
.mbubble.ai {
    flex: 1;
    font-size: 0.95rem;
    line-height: 1.7;
    color: var(--text);
    padding-top: 4px;
    word-break: break-word;
}

/* User bubble — right-aligned pill */
.mbubble.user {
    max-width: 82%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px 18px 4px 18px;
    padding: 0.75rem 1rem;
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--text);
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    word-break: break-word;
}

/* Step / processing line inside ai bubble */
.step-line {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: var(--text-2);
    font-style: italic;
}
.pdot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--accent);
    opacity: 0.6;
    flex-shrink: 0;
    animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
    0%,100% { opacity: 0.35; transform: scale(1); }
    50%      { opacity: 1;    transform: scale(1.25); }
}

/* Legacy classes kept so nothing breaks */
.chat-row { display: flex; margin-bottom: 1.5rem; }
.chat-row.user { justify-content: flex-end; }
.chat-row.ai   { justify-content: flex-start; }
.bubble { max-width: 85%; padding: 1rem 1.2rem; border-radius: 16px; font-size: 0.95rem; line-height: 1.5; box-shadow: var(--shadow-sm); }
.bubble.user { background: var(--surface); border: 1px solid var(--border); border-bottom-right-radius: 4px; }
.bubble.ai   { background: var(--accent-soft); border: 1px solid rgba(108,71,255,0.1); border-bottom-left-radius: 4px; }
.bubble-label { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem; opacity: 0.7; }
.bubble.user .bubble-label { color: var(--text-2); text-align: right; }
.bubble.ai   .bubble-label { color: var(--accent); }

/* ── ANALYTICS CARDS ── */
.analytics-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
    box-shadow: var(--shadow-sm);
}
.stat-card .value {
    font-size: 1.8rem;
    font-weight: 700;
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: var(--text);
    line-height: 1.1;
    margin-bottom: 0.2rem;
}
.stat-card .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-3);
    font-weight: 600;
}

/* ── TREND BARS ── */
.trend-container {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 1.5rem;
    box-shadow: var(--shadow-sm);
}
.trend-title {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-2);
    margin-bottom: 0.8rem;
}
.trend-row {
    display: flex;
    align-items: center;
    margin-bottom: 0.5rem;
    font-size: 0.85rem;
}
.trend-row:last-child { margin-bottom: 0; }
.trend-label { width: 80px; font-weight: 500; color: var(--text); }
.trend-bar-wrap {
    flex: 1;
    height: 6px;
    background: var(--bg2);
    border-radius: 3px;
    margin: 0 0.8rem;
    overflow: hidden;
}
.trend-bar { height: 100%; border-radius: 3px; }
.trend-val { width: 30px; text-align: right; color: var(--text-2); font-size: 0.8rem; }

/* ── TAGS ── */
.tag {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-right: 0.4rem;
}

/* ── EXPORT BUTTONS ── */
.export-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
    margin-top: 1rem;
    box-shadow: var(--shadow-sm);
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.export-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text);
}

/* ── FIXED BOTTOM INPUT BAR — stays at bottom, X locked to chat center ── */
div[data-testid="stHorizontalBlock"]:has(.input-bar-hook) {
    position: fixed !important;
    bottom: 1.5rem !important;
    left: 248px !important;
    right: var(--canvas-width, 0px) !important;
    margin: 0 auto !important;
    width: auto !important;
    min-width: 380px !important;
    max-width: 760px !important;
    background-color: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 24px !important;
    padding: 6px 10px 6px 16px !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.06) !important;
    z-index: 9000 !important;
    align-items: flex-end !important;
    gap: 6px !important;
    transition: left 0s, right 0s !important;
}

/* Focus glow — matches Claude.ai ring */
div[data-testid="stHorizontalBlock"]:has(.input-bar-hook):focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(108,71,255,0.12), 0 4px 24px rgba(0,0,0,0.10) !important;
}

/* Columns pin to bottom so icons sit at bottom-right as text grows */
div[data-testid="stHorizontalBlock"]:has(.input-bar-hook) div[data-testid="column"] {
    display: flex !important;
    align-items: flex-end !important;
    justify-content: center !important;
    padding-bottom: 4px !important;
}

/* Textarea wrapper */
div[data-testid="stHorizontalBlock"]:has(.input-bar-hook) .stTextArea {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
}

/* The textarea itself — auto-grow, no chrome, Claude style */
div[data-testid="stHorizontalBlock"]:has(.input-bar-hook) .stTextArea textarea {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: var(--text) !important;
    caret-color: var(--accent) !important;
    padding: 10px 4px 10px 0 !important;
    min-height: 24px !important;
    max-height: 200px !important;          /* Claude caps at ~200px then scrolls */
    resize: none !important;
    overflow-y: auto !important;
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
    font-family: 'Inter', sans-serif !important;
    scrollbar-width: thin !important;
}

div[data-testid="stHorizontalBlock"]:has(.input-bar-hook) .stTextArea textarea::placeholder {
    color: var(--text-3) !important;
    font-size: 0.95rem !important;
}

/* Action buttons — round, flush to bottom-right like Claude */
div[data-testid="stHorizontalBlock"]:has(.input-bar-hook) .stButton > button {
    background-color: var(--accent) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 50% !important;          /* perfect circle like Claude send btn */
    height: 36px !important;
    width: 36px !important;
    min-width: 36px !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    transition: background 0.15s ease, transform 0.1s ease !important;
    flex-shrink: 0 !important;
}

div[data-testid="stHorizontalBlock"]:has(.input-bar-hook) .stButton > button:hover {
    background-color: #5538e0 !important;
    color: #ffffff !important;
    transform: scale(1.06) !important;
}

div[data-testid="stHorizontalBlock"]:has(.input-bar-hook) .stButton > button:active {
    transform: scale(0.96) !important;
}

/* File Uploader styling (above the input bar when active) */
div[data-testid="stFileUploader"] {
    background: var(--accent-soft) !important;
    border: 1px dashed rgba(108,71,255,0.35) !important;
    border-radius: 10px !important;
    padding: 0.5rem 0.8rem !important;
    margin-bottom: 0.4rem;
}
</style>
"""

def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def render_header():
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:1rem;
                padding-bottom:1.2rem;margin-bottom:1.5rem;
                border-bottom:1px solid #e8e6df;
                margin-top:2rem;"> <div style="width:44px;height:44px;background:#6c47ff;border-radius:12px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:1.4rem;color:white;
                    box-shadow:0 4px 12px rgba(108,71,255,0.25);flex-shrink:0;">
            {APP_ICON}
        </div>
        <div>
            <div style="font-family:'Plus Jakarta Sans','Inter',sans-serif;
                        font-size:1.15rem;font-weight:700;color:#1c1b20;line-height:1.1;">
                {APP_TITLE}
            </div>
            <div style="font-size:0.72rem;color:#9896a8;font-weight:500;margin-top:2px;">
                Semantic dedup · Multi-task BERT · v{APP_VERSION}
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.markdown(f"### {APP_ICON} {APP_TITLE}")
        st.caption(f"NLP Triage Pipeline · v{APP_VERSION} · {DEVICE.upper()}")
        st.divider()

        if st.button("＋  New analysis", key="new_chat_btn", use_container_width=True):
            st.session_state.analyses        = []
            st.session_state.session_id      = None
            st.session_state.active_canvas   = -1
            st.session_state.processing      = False
            st.session_state.show_upload     = False
            st.session_state.show_solutions  = False
            st.session_state.general_answer  = None
            st.session_state.canvas_width_px = 480
            st.session_state.pending_file    = None
            st.session_state.pending_text    = None
            st.session_state.user_label      = ""
            st.session_state.solutions_data  = None
            st.session_state["_canvas_msg"]  = None
            st.rerun()

        st.markdown("**Recent Sessions**")

        sessions = list_sessions()

        if sessions:
            for i, s in enumerate(sessions[:15]):
                label   = s["label"]
                ts      = s.get("updated", s.get("created", ""))[:10]
                caption = f'{s.get("count", 0)} analyses · {ts}'
                if st.button(
                    label[:36] + ("…" if len(label) > 36 else ""),
                    key=f'sess_{i}_{s["id"]}',
                    use_container_width=True,
                    help=caption,
                ):
                    loaded = load_session(s["id"])
                    if loaded:
                        raw_analyses = loaded.get("analyses", [])
                        # Rebuild in-memory analyses list from JSON
                        analyses = []
                        for a in raw_analyses:
                            dm = a.get("dup_map", {})
                            analyses.append({
                                "index":          a["index"],
                                "user_label":     a.get("user_label", ""),
                                "results":        a.get("results", []),
                                "bugs":           a.get("bugs", []),
                                "dup_map":        {int(k): v for k, v in dm.items()},
                                "total":          a.get("total", 0),
                                "dups":           a.get("dups", 0),
                                "pdf_bytes":      None,  # rebuild on demand
                                "solutions_data": a.get("solutions_data"),
                            })
                        st.session_state.analyses        = analyses
                        st.session_state.session_id      = loaded["id"]
                        st.session_state.active_canvas   = len(analyses) - 1 if analyses else -1
                        st.session_state.show_solutions  = False
                        st.session_state.processing      = False
                        st.session_state.general_answer  = None
                        st.session_state.pending_file    = None
                        st.session_state.pending_text    = None
                        st.session_state.user_label      = ""
                        st.session_state.solutions_data  = None
                        st.session_state.canvas_width_px = 480
                        st.session_state["_canvas_msg"]  = None
                        st.rerun()

            st.divider()
            if st.button("🗑 Clear all sessions", key="clear_hist", use_container_width=True):
                clear_all_sessions()
                st.rerun()
        else:
            st.caption("No sessions yet. Run your first analysis to see it here.")

        st.divider()
        st.caption(f"👤 Varad Kulkarni · {DEVICE.upper()}")


def render_welcome():
    st.markdown("""
    <div style="text-align:center;padding:3rem 1rem 2rem;animation:fadeIn 0.6s ease-out;">
        <div style="display:inline-block;background:#ede9ff;color:#6c47ff;
                    padding:0.3rem 0.8rem;border-radius:20px;font-size:0.75rem;
                    font-weight:700;letter-spacing:0.05em;margin-bottom:1.5rem;">
            🐛 AI Bug Triage
        </div>
        <div style="font-family:'Plus Jakarta Sans','Inter',sans-serif;
                    font-size:3rem;font-weight:800;color:#1c1b20;
                    line-height:1.1;letter-spacing:-0.03em;margin-bottom:1rem;">
            Classify bugs.<br>Ship faster.
        </div>
        <div style="font-size:1rem;color:#6b6880;max-width:480px;
                    margin:0 auto 2.5rem;line-height:1.6;">
            Paste bug descriptions or upload a PDF report.
            The pipeline deduplicates, classifies by type &amp; severity,
            and generates a structured triage report.
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);
                    gap:1.2rem;max-width:680px;margin:0 auto;">
            <div style="background:#fff;border:1px solid #e8e6df;border-radius:16px;
                        padding:1.5rem 1.2rem;text-align:left;
                        box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                <div style="font-size:1.5rem;margin-bottom:0.8rem;">🔍</div>
                <div style="font-size:0.9rem;font-weight:600;color:#1c1b20;
                            margin-bottom:0.4rem;">Smart Deduplication</div>
                <div style="font-size:0.8rem;color:#9896a8;line-height:1.4;">
                    SBERT semantic similarity removes duplicate reports automatically.
                </div>
            </div>
            <div style="background:#fff;border:1px solid #e8e6df;border-radius:16px;
                        padding:1.5rem 1.2rem;text-align:left;
                        box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                <div style="font-size:1.5rem;margin-bottom:0.8rem;">⚡</div>
                <div style="font-size:0.9rem;font-weight:600;color:#1c1b20;
                            margin-bottom:0.4rem;">Multi-task Classification</div>
                <div style="font-size:0.8rem;color:#9896a8;line-height:1.4;">
                    BERT classifies bug type, severity, and fix time in one pass.
                </div>
            </div>
            <div style="background:#fff;border:1px solid #e8e6df;border-radius:16px;
                        padding:1.5rem 1.2rem;text-align:left;
                        box-shadow:0 2px 8px rgba(0,0,0,0.04);">
                <div style="font-size:1.5rem;margin-bottom:0.8rem;">💡</div>
                <div style="font-size:0.9rem;font-weight:600;color:#1c1b20;
                            margin-bottom:0.4rem;">AI Solutions</div>
                <div style="font-size:0.8rem;color:#9896a8;line-height:1.4;">
                    Searches Stack Overflow and GitHub for relevant fixes.
                </div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)


def ai_bubble(html: str):
    st.markdown(f"""
    <div class="msg-wrap">
        <div class="msg-row">
            <div class="mav ai">🐛</div>
            <div class="mbubble ai">{html}</div>
        </div>
    </div>""", unsafe_allow_html=True)


def user_bubble(text: str):
    if len(text) > 200:
        preview  = text[:200].rsplit(" ", 1)[0] + "…"
        full_esc = text.replace('"', '&quot;').replace("'", "&#39;")
        content  = f"""
        <div>
            <div style="white-space:pre-wrap;word-break:break-word;
                        font-size:0.95rem;line-height:1.6;color:#1c1b20;">
                {preview}
            </div>
            <details style="margin-top:0.5rem;">
                <summary style="font-size:0.75rem;color:#6c47ff;cursor:pointer;
                                font-weight:600;list-style:none;outline:none;">
                    ▼ Show full input ({len(text)} chars)
                </summary>
                <div style="margin-top:0.6rem;white-space:pre-wrap;word-break:break-word;
                            font-size:0.88rem;line-height:1.65;color:#1c1b20;
                            background:#f8f7f4;border-radius:8px;padding:0.7rem 0.85rem;
                            border-left:3px solid #6c47ff;">
                    {text}
                </div>
            </details>
        </div>"""
    else:
        content = f'<div style="white-space:pre-wrap;word-break:break-word;">{text}</div>'

    st.markdown(f"""
    <div class="msg-wrap" style="display:flex;justify-content:flex-end;margin-bottom:1.2rem;">
        <div style="display:flex;align-items:flex-end;gap:0.6rem;max-width:82%;">
            <div class="mbubble user">{content}</div>
            <div class="mav user" style="flex-shrink:0;margin-bottom:2px;">VK</div>
        </div>
    </div>""", unsafe_allow_html=True)


def step_bubble(message: str):
    ai_bubble(f'<div class="step-line"><div class="pdot"></div>{message}</div>')


def render_analytics(results: list[dict], total: int, dup_count: int, analysis_idx: int = 0):
    analytics  = compute_session_analytics(results, total, dup_count)
    unique     = analytics["unique"]
    type_cnt   = analytics["type_counts"]
    sev_cnt    = analytics["sev_counts"]

    # ── Derive insights ────────────────────────────────────────────────────────
    critical_n  = sev_cnt.get("critical", 0)
    major_n     = sev_cnt.get("major",    0)
    most_type   = max(type_cnt, key=type_cnt.get) if type_cnt else "—"
    most_type_n = type_cnt.get(most_type, 0)
    urgent      = critical_n + major_n  # bugs needing immediate attention

    type_colors = {
        "Crash":     "#dc2626",
        "Freeze":    "#2563eb",
        "Memory":    "#ea580c",
        "UI/Visual": "#7c3aed",
        "Other":     "#6b7280",
    }
    sev_colors = {
        "critical": "#dc2626",
        "major":    "#ea580c",
        "minor":    "#16a34a",
    }

    def bar_rows(counts, total_c, colors):
        if not total_c:
            return ""
        rows = ""
        for label, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            pct   = round(cnt / total_c * 100)
            color = colors.get(label, "#6b7280")
            rows += (
                f'<div style="margin-bottom:0.55rem;">'
                f'<div style="display:flex;justify-content:space-between;'
                f'font-size:0.75rem;font-weight:500;margin-bottom:0.22rem;">'
                f'<span style="color:#1c1b20;">{label}</span>'
                f'<span style="color:#9896a8;">{cnt} · {pct}%</span></div>'
                f'<div style="background:#f0efe9;border-radius:4px;height:7px;overflow:hidden;">'
                f'<div style="width:{pct}%;height:100%;border-radius:4px;background:{color};"></div>'
                f'</div></div>'
            )
        return rows

    type_bars = bar_rows(type_cnt, unique, type_colors)
    sev_bars  = bar_rows(sev_cnt,  unique, sev_colors)

    # ── Insight chips ──────────────────────────────────────────────────────────
    chips = ""
    if critical_n:
        chips += f'<span style="background:#fee2e2;color:#dc2626;padding:0.22rem 0.65rem;border-radius:20px;font-size:0.72rem;font-weight:600;margin-right:0.4rem;">🔴 {critical_n} critical</span>'
    if major_n:
        chips += f'<span style="background:#ffedd5;color:#ea580c;padding:0.22rem 0.65rem;border-radius:20px;font-size:0.72rem;font-weight:600;margin-right:0.4rem;">🟠 {major_n} major</span>'
    if urgent:
        chips += f'<span style="background:#ede9ff;color:#6c47ff;padding:0.22rem 0.65rem;border-radius:20px;font-size:0.72rem;font-weight:600;margin-right:0.4rem;">⚡ {urgent} need urgent fix</span>'
    if most_type_n:
        chips += f'<span style="background:#f0efe9;color:#6b6880;padding:0.22rem 0.65rem;border-radius:20px;font-size:0.72rem;font-weight:600;">📌 Most: {most_type}</span>'

    chips_html = f'<div style="margin-bottom:0.85rem;display:flex;flex-wrap:wrap;gap:0.3rem;">{chips}</div>' if chips else ""

    _placeholder = st.empty()
    _placeholder.markdown(f"""
    <div id="analytics-block-{analysis_idx}" style="display:flex;gap:0.75rem;align-items:flex-start;margin-bottom:1.5rem;">
        <div style="width:32px;height:32px;border-radius:50%;background:#6c47ff;
                    display:flex;align-items:center;justify-content:center;
                    font-size:0.85rem;flex-shrink:0;margin-top:2px;color:#fff;">🐛</div>
        <div style="flex:1;min-width:0;">
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.6rem;margin-bottom:1rem;">
                <div style="background:#ffffff;border:1px solid #e8e6df;border-radius:12px;
                            padding:0.85rem 0.9rem;box-shadow:0 1px 3px rgba(0,0,0,0.05);text-align:center;">
                    <div style="font-size:1.9rem;font-weight:700;color:#1c1b20;line-height:1;">{total}</div>
                    <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.06em;
                                color:#9896a8;font-weight:600;margin-top:0.2rem;">Total</div>
                </div>
                <div style="background:#ffffff;border:1px solid #e8e6df;border-radius:12px;
                            padding:0.85rem 0.9rem;box-shadow:0 1px 3px rgba(0,0,0,0.05);text-align:center;">
                    <div style="font-size:1.9rem;font-weight:700;color:#dc2626;line-height:1;">{dup_count}</div>
                    <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.06em;
                                color:#9896a8;font-weight:600;margin-top:0.2rem;">Duplicates</div>
                </div>
                <div style="background:#ffffff;border:1px solid #e8e6df;border-radius:12px;
                            padding:0.85rem 0.9rem;box-shadow:0 1px 3px rgba(0,0,0,0.05);text-align:center;">
                    <div style="font-size:1.9rem;font-weight:700;color:#16a34a;line-height:1;">{unique}</div>
                    <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.06em;
                                color:#9896a8;font-weight:600;margin-top:0.2rem;">Unique</div>
                </div>
                <div style="background:#dc2626;border:1px solid #dc2626;border-radius:12px;
                            padding:0.85rem 0.9rem;box-shadow:0 1px 3px rgba(220,38,38,0.25);text-align:center;">
                    <div style="font-size:1.9rem;font-weight:700;color:#fff;line-height:1;">{urgent}</div>
                    <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.06em;
                                color:rgba(255,255,255,0.8);font-weight:600;margin-top:0.2rem;">Urgent</div>
                </div>
            </div>
            {chips_html}
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
                <div style="background:#ffffff;border:1px solid #e8e6df;border-radius:12px;
                            padding:0.9rem 1rem;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                    <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;
                                letter-spacing:0.08em;color:#9896a8;margin-bottom:0.75rem;">Bug type trend</div>
                    {type_bars if type_bars else '<div style="font-size:0.8rem;color:#9896a8;">No data</div>'}
                </div>
                <div style="background:#ffffff;border:1px solid #e8e6df;border-radius:12px;
                            padding:0.9rem 1rem;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                    <div style="font-size:0.68rem;font-weight:700;text-transform:uppercase;
                                letter-spacing:0.08em;color:#9896a8;margin-bottom:0.75rem;">Severity breakdown</div>
                    {sev_bars if sev_bars else '<div style="font-size:0.8rem;color:#9896a8;">No data</div>'}
                </div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)


def _sev_cls(severity: str) -> str:
    return {
        "critical": "b-critical",
        "major":    "b-major",
        "minor":    "b-minor",
    }.get(severity.lower(), "b-major")


def _sim_html(r: dict, bugs: list[str], dup_map: dict) -> str:
    dl = dup_map.get(r["original_index"], [])
    if not dl:
        return ""
    items = "".join(
        f'<div class="sim-item">"{bugs[d][:110]}{"…" if len(bugs[d])>110 else ""}"</div>'
        for d in dl
    )
    return f"""
    <div class="sim-block">
        <div class="sim-title">Similar bugs found</div>
        {items}
    </div>"""


def render_bug_card(r: dict, idx: int, bugs: list[str], dup_map: dict, show_solution_btn: bool = False):
    bug_text  = r.get("text", "")
    text_html = (
        f'<div class="bug-text">"{bug_text[:220]}{"…" if len(bug_text)>220 else ""}"</div>'
        if bug_text else ""
    )
    sev  = _sev_cls(r["severity"])
    sims = _sim_html(r, bugs, dup_map)

    ai_bubble(f"""
    <div class="bug-card">
        <div class="bug-card-header">
            <div class="bug-num">Bug #{idx+1}</div>
        </div>
        {text_html}
        <div class="badge-row">
            <span class="badge {sev}">{r['severity'].upper()}</span>
            <span class="badge b-type">{r['bug_type']}</span>
            <span class="badge b-time">⏱ {r['fix_time']}</span>
        </div>
        <div class="narrative">
            As per the analyzed report, the severity of the current running bug is
            <strong>{r['severity']}</strong>. With the current severity, we found out
            that the bug is a <strong>{r['bug_type']}</strong> issue.
            The estimated fix time on the basis of the severity is
            <strong>{r['fix_time']}</strong>.
        </div>
        {sims}
    </div>""")

def render_canvas(results: list, bugs: list, dup_map: dict,
                  pdf_bytes: bytes, session_label: str = "Bug Report",
                  analysis_idx: int = 0, solutions_data: list | None = None):
    """Claude-style right panel: Breaks out of the iframe, anchors right, drag-to-resize."""
    import streamlit.components.v1 as components
    from app.helpers.exporter import export_csv, export_xlsx

    if "canvas_width_px" not in st.session_state:
        st.session_state.canvas_width_px = 480

    w = st.session_state.canvas_width_px

    sev_style = {
        "critical": ("#dc2626", "#fee2e2"),
        "major":    ("#ea580c", "#ffedd5"),
        "minor":    ("#16a34a", "#dcfce7"),
    }

    # ── Build cards HTML ──────────────────────────────────────────────────────
    cards_html = ""
    for i, r in enumerate(results):
        sc, sb   = sev_style.get(r["severity"].lower(), ("#6b6880", "#f3f4f6"))
        bug_text = r.get("text", "")
        dl       = dup_map.get(r["original_index"], [])
        sim_block = ""
        if dl:
            sim_items = "".join(
                f'<div style="font-size:0.75rem;color:#6b6880;padding:0.28rem 0;'
                f'border-bottom:1px solid #f0efe9;">'
                f'&ldquo;{bugs[d][:100]}{"…" if len(bugs[d])>100 else ""}&rdquo;</div>'
                for d in dl
            )
            sim_block = (
                f'<div style="background:#f8f7f4;border-radius:7px;padding:0.55rem 0.7rem;'
                f'margin-top:0.65rem;border-left:3px solid #6c47ff;">'
                f'<div style="font-size:0.6rem;font-weight:600;text-transform:uppercase;'
                f'color:#9896a8;margin-bottom:0.3rem;">Similar bugs</div>'
                f'{sim_items}</div>'
            )
        bug_esc = bug_text.replace("<","&lt;").replace(">","&gt;").replace('"','&quot;')
        cards_html += (
            f'<div style="background:#fff;border:1px solid #e8e6df;border-radius:12px;'
            f'padding:1rem 1.1rem;margin-bottom:0.75rem;border-left:3px solid {sc};'
            f'box-shadow:0 1px 4px rgba(0,0,0,0.04);">'
            f'<div style="font-size:0.6rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.07em;color:#9896a8;margin-bottom:0.4rem;">Bug #{i+1}</div>'
            f'<div style="font-size:0.84rem;color:#1c1b20;background:#f8f7f4;'
            f'border-radius:6px;padding:0.6rem 0.8rem;margin-bottom:0.6rem;'
            f'line-height:1.6;white-space:pre-wrap;">&ldquo;{bug_esc}&rdquo;</div>'
            f'<div style="margin-bottom:0.6rem;">'
            f'<span style="padding:0.18rem 0.55rem;border-radius:5px;font-size:0.67rem;'
            f'font-weight:600;background:{sb};color:{sc};margin-right:0.3rem;">{r["severity"].upper()}</span>'
            f'<span style="padding:0.18rem 0.55rem;border-radius:5px;font-size:0.67rem;'
            f'font-weight:600;background:#f0efe9;color:#6b6880;border:1px solid #e8e6df;'
            f'margin-right:0.3rem;">{r["bug_type"]}</span>'
            f'<span style="padding:0.18rem 0.55rem;border-radius:5px;font-size:0.67rem;'
            f'font-weight:600;background:#ede9ff;color:#6c47ff;">⏱ {r["fix_time"]}</span>'
            f'</div>'
            f'<div style="font-size:0.82rem;color:#6b6880;line-height:1.65;'
            f'padding-top:0.6rem;border-top:1px solid #f0efe9;">'
            f'Severity: <strong style="color:#1c1b20;">{r["severity"]}</strong> · '
            f'Type: <strong style="color:#1c1b20;">{r["bug_type"]}</strong> · '
            f'Fix time: <strong style="color:#1c1b20;">{r["fix_time"]}</strong>'
            f'</div>{sim_block}</div>'
        )

    # ── Prepare download data ─────────────────────────────────────────────────
    import base64
    from app.helpers.pdf_report import _build_pdf_with_solutions

    # Rebuild PDF with solutions if available
    # Use the solutions_data passed in as parameter (already synced from analyses list)
    if not pdf_bytes:
        from app.helpers.pdf_report import build_pdf
        try:
            pdf_bytes = build_pdf(results, bugs, dup_map, len(bugs), len(bugs) - len(results))
        except Exception:
            pdf_bytes = b""
    final_pdf = _build_pdf_with_solutions(results, bugs, dup_map, pdf_bytes, solutions_data) if solutions_data else pdf_bytes
    if not final_pdf:
        final_pdf = b""

    # CSV — text/csv works in iframes
    csv_data = export_csv(results, bugs, dup_map)
    csv_b64  = base64.b64encode(
        csv_data if isinstance(csv_data, bytes) else csv_data.encode()
    ).decode()

    # XLSX — octet-stream forces download in iframe
    try:
        xlsx_data = export_xlsx(results, bugs, dup_map)
        xlsx_b64  = base64.b64encode(xlsx_data).decode()
        xlsx_btn  = f'<a class="dl-btn" href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{xlsx_b64}" download="bug_report.xlsx" target="_blank">📗 XLSX</a>'
    except Exception:
        xlsx_btn = ""

    # PDF download — base64 data URI avoids Streamlit media cache expiry (MediaFileStorageError)
    if final_pdf:
        import base64 as _b64
        pdf_b64 = _b64.b64encode(final_pdf).decode()
        st.markdown(
            f'''<a href="data:application/pdf;base64,{pdf_b64}"
                  download="bug_report_{analysis_idx + 1}.pdf"
                  style="display:inline-block;padding:0.45rem 1.1rem;
                         background:#6c47ff;color:#fff;border-radius:8px;
                         font-size:0.82rem;font-weight:600;text-decoration:none;
                         margin-bottom:0.5rem;cursor:pointer;">
                📄 Download PDF Report
            </a>''',
            unsafe_allow_html=True
        )
    else:
        st.caption("⚠ PDF unavailable — re-run the analysis.")

    # ── Inject CSS variable so input bar and block-container auto-adjust ────
   # ── Inject CSS variable so input bar and block-container auto-adjust ────
    st.markdown(f"""
    <style>
    :root {{
        --canvas-width: {w}px;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Build solutions HTML to embed inside canvas ───────────────────────────
    from app.helpers.solution_agent import get_solutions_for_all_bugs, render_all_solutions_html

    if solutions_data is not None:
        sol_html   = render_all_solutions_html(solutions_data)
        sol_loaded = "true"
    else:
        sol_html   = '<div style="padding:2rem 1rem;text-align:center;color:#9896a8;font-size:0.85rem;">Click the button above to generate AI solutions.<br><small>Takes 15–30 seconds.</small></div>'
        sol_loaded = "false"

    # ── The actual canvas panel rendered as an HTML component ─────────────────
    # ── The actual canvas panel rendered as an HTML component ─────────────────
    components.html(f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }}
      body {{ background: transparent; overflow: hidden; }}

      #panel {{
        position: fixed;
        top: 0; right: 0; bottom: 0;
        width: 100%;
        background: #ffffff;
        border-left: 1px solid #e8e6df;
        box-shadow: -4px 0 24px rgba(0,0,0,0.07);
        display: flex; flex-direction: column;
        z-index: 99999;
      }}

      #drag-handle {{
        position: absolute;
        top: 0; left: -10px; bottom: 0;
        width: 20px;
        cursor: col-resize;
        z-index: 100001;
        display: flex; align-items: center; justify-content: center;
        background: transparent;
      }}
      #drag-handle::after {{
        content: '';
        width: 5px; height: 52px;
        background: #c4b5fd;
        border-radius: 3px;
        transition: background 0.15s, width 0.15s;
      }}
      #drag-handle:hover::after {{ background: #6c47ff; width: 6px; }}

      #panel-header {{
        padding: 1rem 1.1rem 0.85rem;
        border-bottom: 1px solid #e8e6df;
        flex-shrink: 0;
      }}
      #panel-title {{
        font-size: 0.95rem; font-weight: 700; color: #1c1b20;
        display: flex; align-items: center; justify-content: space-between;
      }}
      #panel-sub {{
        font-size: 0.7rem; color: #9896a8; margin-top: 3px;
      }}
      #close-btn {{
        background: none; border: none; cursor: pointer;
        font-size: 1rem; color: #9896a8; padding: 0.1rem 0.3rem;
        border-radius: 5px; line-height: 1;
      }}
      #close-btn:hover {{ background: #f0efe9; color: #1c1b20; }}

      #panel-actions {{
        padding: 0.7rem 1.1rem;
        border-bottom: 1px solid #e8e6df;
        flex-shrink: 0;
      }}
      .dl-row {{
        display: flex; gap: 0.4rem; margin-bottom: 0.5rem;
      }}
      .dl-btn {{
        flex: 1; text-align: center; padding: 0.42rem 0;
        background: #fff; border: 1px solid #e8e6df; border-radius: 8px;
        font-size: 0.78rem; font-weight: 600; color: #1c1b20;
        text-decoration: none; cursor: pointer;
      }}
      .dl-btn:hover {{ background: #f8f7f4; border-color: #9896a8; }}
      .sol-btn {{
        width: 100%; padding: 0.48rem;
        background: #ede9ff; border: 1px solid #c4b5fd;
        border-radius: 8px; font-size: 0.8rem; font-weight: 600;
        color: #6c47ff; cursor: pointer; text-align: center;
        margin-top: 0.4rem;
      }}
      .sol-btn:hover {{ background: #6c47ff; color: #fff; border-color: #6c47ff; }}
      .sol-btn.active {{ background: #6c47ff; color: #fff; border-color: #6c47ff; }}

      #panel-body {{
        flex: 1; overflow-y: auto; padding: 1rem 1.1rem;
      }}
      #panel-body::-webkit-scrollbar {{ width: 4px; }}
      #panel-body::-webkit-scrollbar-thumb {{ background: #e8e6df; border-radius: 2px; }}
    </style>
    </head>
    <body>
    <div id="panel">
      <div id="drag-handle" title="Drag to resize"></div>

      <div id="panel-header">
        <div id="panel-title">
          <span>📋 Bug Report Canvas</span>
          <button id="close-btn" title="Close canvas">✕</button>
        </div>
        <div id="panel-sub">{len(results)} unique bug{'s' if len(results)!=1 else ''} · {session_label[:45]}{"…" if len(session_label)>45 else ""}</div>
      </div>

      <div id="panel-actions">
        <div class="dl-row">
          <a class="dl-btn" href="data:text/csv;base64,{csv_b64}" download="bug_report.csv" target="_blank">📊 CSV</a>
          {xlsx_btn}
        </div>
        <div class="sol-btn" id="sol-toggle-btn" onclick="toggleView()">
          💡 Get AI Solutions for All Bugs
        </div>
      </div>

      <div id="panel-body">
        <div id="view-bugs">{cards_html}</div>
        <div id="view-solutions" style="display:none;">{sol_html}</div>
      </div>
    </div>

    <script>
      // 1. Setup frame references
      window.frameElement && (window.frameElement.id = 'nlp-canvas-iframe');
      const iframe = window.parent.document.getElementById('nlp-canvas-iframe');

      // 2. Define state variables
      let dragging = false, startX = 0, startW = {w};
      let showingSolutions = false;
      let solutionsLoaded = {sol_loaded};

      // 3. Define all functions securely at the top
      function pushChat(newW) {{
        window.parent.document.documentElement.style.setProperty('--canvas-width', newW + 'px');
      }}

      function applyPosition() {{
        if (!iframe) return;
        iframe.style.position   = 'fixed';
        iframe.style.top        = '0';
        iframe.style.right      = '0';
        iframe.style.width      = '{w}px';
        iframe.style.height     = '100vh';
        iframe.style.zIndex     = '99990';
        iframe.style.border     = 'none';
        iframe.style.boxShadow  = '-4px 0 24px rgba(0,0,0,0.08)';

        let el = iframe.parentElement;
        for (let i = 0; i < 15 && el && el !== window.parent.document.body; i++) {{
          if (el.hasAttribute('data-testid')) {{
            el.style.cssText = 'width:0!important;height:0!important;min-height:0!important;padding:0!important;margin:0!important;overflow:hidden!important;position:absolute!important;';
            break;
          }}
          el = el.parentElement;
        }}
      }}

      function closePanel() {{
        if (iframe) iframe.style.width = '0px';
        pushChat(0);
        window.parent.postMessage({{ type:'streamlit:setComponentValue', value: 0 }}, '*');
      }}

      function toggleView() {{
        showingSolutions = !showingSolutions;
        const bugs = document.getElementById('view-bugs');
        const sols = document.getElementById('view-solutions');
        const btn  = document.getElementById('sol-toggle-btn');
        if (showingSolutions) {{
          bugs.style.display = 'none';
          sols.style.display = 'block';
          btn.textContent    = '← Back to Bug Cards';
          btn.classList.add('active');
          if (!solutionsLoaded) {{
            sols.innerHTML = '<div style="padding:2rem;text-align:center;color:#9896a8;font-size:0.85rem;">⏳ Generating AI solutions…<br><small>This takes 15-30 seconds. The canvas will refresh automatically.</small></div>';
            
            const buttons = Array.from(window.parent.document.querySelectorAll('button'));
            const targetBtn = buttons.find(b => b.textContent && b.textContent.includes('GenSolTrigger'));
            if (targetBtn) {{
                targetBtn.click();
            }} else {{
                console.error("GenSolTrigger button not found!");
            }}
            solutionsLoaded = true;
          }}
        }} else {{
          bugs.style.display = 'block';
          sols.style.display = 'none';
          btn.textContent    = '💡 Get AI Solutions for All Bugs';
          btn.classList.remove('active');
        }}
      }}

      function onMove(e) {{
        if (!dragging) return;
        const vw   = window.parent.innerWidth;
        const minW = Math.floor(vw * 0.35);
        const maxW = Math.floor(vw * 0.80);
        const diff = startX - e.clientX;
        const newW = Math.max(minW, Math.min(maxW, startW + diff));
        if (iframe) iframe.style.width = newW + 'px';
        pushChat(newW);
      }}

      function onUp(e) {{
        if (!dragging) return;
        dragging = false;
        window.parent.document.body.style.cursor     = '';
        window.parent.document.body.style.userSelect = '';
        const overlay = window.parent.document.getElementById('drag-overlay');
        if (overlay) overlay.remove();
        const finalW = iframe ? iframe.offsetWidth : startW;
        pushChat(finalW);
        window.parent.postMessage({{ type:'streamlit:setComponentValue', value: finalW }}, '*');
      }}

      // 4. Execute scripts and attach listeners
      applyPosition();
      pushChat({w});

      document.getElementById('close-btn').addEventListener('click', closePanel);
      document.getElementById('sol-toggle-btn').addEventListener('click', toggleView);

      const handle = document.getElementById('drag-handle');
      if (handle) {{
        handle.addEventListener('mousedown', e => {{
          e.preventDefault();
          e.stopPropagation();
          dragging = true;
          const rect = iframe ? iframe.getBoundingClientRect() : {{left: 0}};
          startX = rect.left + e.clientX;
          startW = iframe ? iframe.offsetWidth : {w};
          window.parent.document.body.style.cursor     = 'col-resize';
          window.parent.document.body.style.userSelect = 'none';
          let overlay = window.parent.document.getElementById('drag-overlay');
          if (!overlay) {{
            overlay = window.parent.document.createElement('div');
            overlay.id = 'drag-overlay';
            overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99998;cursor:col-resize;';
            window.parent.document.body.appendChild(overlay);
          }}
        }});
      }}

      window.parent.document.addEventListener('mousemove', onMove);
      window.parent.document.addEventListener('mouseup',   onUp);

      if ({'true' if st.session_state.pop('_auto_show_solutions', False) else 'false'}) {{
        toggleView();
      }}
    </script>
    </body>
    </html>
    """, height=800, scrolling=False)

    # ── Handle Solutions Trigger from iframe ──────────────────────────────────
    # ── Handle Solutions Trigger from iframe ──────────────────────────────────
    st.markdown('''
    <div id="hide-next-button"></div>
    <style>
        div:has(> #hide-next-button) + div[data-testid="element-container"],
        div:has(> #hide-next-button) + div.element-container {
            position: absolute !important;
            left: -9999px !important;
            opacity: 0 !important;
        }
    </style>
    ''', unsafe_allow_html=True)
    
    if st.button("GenSolTrigger", key=f"sol_hidden_btn_{analysis_idx}"):
        st.session_state["_canvas_msg"] = "gen_solutions"
        st.rerun()
        
def render_export_buttons(pdf_bytes: bytes, results: list, bugs: list, dup_map: dict):
    """Kept for backward compatibility — canvas replaces this."""
    pass


def render_input_bar():
    st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)

    col_plus, col_text, col_send = st.columns([0.8, 10, 0.8], gap="small")

    with col_plus:
        st.markdown('<span class="input-bar-hook"></span>', unsafe_allow_html=True)
        if st.button("＋", key="plus_btn", help="Upload PDF"):
            st.session_state.show_upload = not st.session_state.get("show_upload", False)
            st.rerun()

    with col_text:
        text_val = st.text_area(
            "msg",
            placeholder="Write a bug…",
            label_visibility="collapsed",
            key="user_text_input",
            height=44,
        )

    with col_send:
        send_clicked = st.button("➤", key="send_btn")

    if text_val:
        st.markdown(
            f'<div style="text-align:right;font-size:0.62rem;color:#9896a8;'
            f'margin-top:0.1rem;">{len(text_val)} chars · {len(text_val.split())} words</div>',
            unsafe_allow_html=True,
        )

    return send_clicked