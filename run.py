import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.helpers.config import APP_TITLE, APP_ICON
from app.helpers.classifier import load_classifier, classify_bug
from app.helpers.sbert import load_sbert, deduplicate
from app.helpers.pdf_parser import extract_paragraphs, split_text_input
from app.helpers.pdf_report import build_pdf
from app.helpers.chat_history import (
    create_session, append_analysis, update_solutions,
    load_session, list_sessions, delete_session, clear_all_sessions,
)
from app.ui.components import (
    inject_css, render_header, render_sidebar, render_welcome,
    ai_bubble, user_bubble, step_bubble,
    render_analytics, render_canvas,
    render_export_buttons, render_input_bar,
)

import streamlit as st

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


def _init_state():
    defaults = {
        # Session
        "session_id":       None,
        # List of analyses in current session
        "analyses":         [],   # list of dicts, one per input
        "active_canvas":    -1,   # index of which analysis is shown in canvas
        # Processing
        "processing":       False,
        "pending_text":     None,
        "pending_file":     None,
        "user_label":       "",
        # UI
        "show_upload":      False,
        "canvas_width_px":  480,
        "general_answer":   None,
        # Solutions (for active canvas)
        "show_solutions":   False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _build_result_entry(idx, bugs, dup_map, tok, clf):
    pred = classify_bug(bugs[idx], tok, clf)
    return {
        "original_index": idx,
        "text":           bugs[idx],
        "bug_type":       pred["bug_type"],
        "severity":       pred["severity"],
        "fix_time":       pred["fix_time"],
        "bt_conf":        pred["bt_conf"],
        "sv_conf":        pred["sv_conf"],
        "ft_conf":        pred["ft_conf"],
        "bt_candidates":  pred["bt_candidates"],
        "sv_candidates":  pred["sv_candidates"],
        "ft_candidates":  pred["ft_candidates"],
        "is_uncertain":   pred["is_uncertain"],
        "duplicates":     dup_map.get(idx, []),
    }


def _run_pipeline(bugs, sbert, tok, clf):
    step_bubble(f"Extracted <strong>{len(bugs)}</strong> blocks · running SBERT deduplication…")
    unique_ids, dup_map, _ = deduplicate(bugs, sbert)
    dup_count = len(bugs) - len(unique_ids)
    step_bubble(
        f"<strong>{len(unique_ids)}</strong> unique · "
        f"<strong>{dup_count}</strong> duplicates · classifying…"
    )
    results   = [_build_result_entry(idx, bugs, dup_map, tok, clf) for idx in unique_ids]
    pdf_bytes = build_pdf(results, bugs, dup_map, len(bugs), dup_count)
    return results, dup_map, dup_count, pdf_bytes


def _store_analysis(results, bugs, dup_map, total, dup_count, pdf_bytes, label):
    """Append this analysis to the current session (or create session if first)."""
    # Create session on first analysis
    if not st.session_state.session_id:
        st.session_state.session_id = create_session(label)

    # Save to JSON file
    analysis_idx = append_analysis(
        st.session_state.session_id,
        label, results, bugs,
        {k: v for k, v in dup_map.items()},
        total, dup_count,
    )

    # Build analysis dict for in-memory state
    analysis = {
        "index":          analysis_idx,
        "user_label":     label,
        "results":        results,
        "bugs":           bugs,
        "dup_map":        dup_map,
        "total":          total,
        "dups":           dup_count,
        "pdf_bytes":      pdf_bytes,
        "solutions_data": None,
    }
    st.session_state.analyses.append(analysis)
    # Always show the newest canvas
    st.session_state.active_canvas  = len(st.session_state.analyses) - 1
    st.session_state.processing     = False
    st.session_state.show_solutions = False
    st.rerun()


def main():
    _init_state()
    inject_css()
    render_sidebar()
    render_header()

    analyses = st.session_state.analyses

    # ── Welcome ───────────────────────────────────────────────────────────────
    if not analyses and not st.session_state.processing:
        render_welcome()

    # ── Processing spinner ────────────────────────────────────────────────────
    if st.session_state.processing:
        pending_file = st.session_state.pending_file
        pending_text = st.session_state.pending_text

        if st.session_state.get("user_label"):
            user_bubble(st.session_state.user_label)

        with st.spinner(""):
            step_bubble("Loading models…")
            sbert    = load_sbert()
            tok, clf = load_classifier()

            if pending_file is not None:
                step_bubble("Parsing PDF and extracting bug blocks…")
                bugs  = extract_paragraphs(pending_file)
                total = len(bugs)
                if total == 0:
                    ai_bubble("⚠️ No readable text found.")
                    st.session_state.processing   = False
                    st.session_state.pending_file = None
                    st.rerun()
                results, dup_map, dup_count, pdf_bytes = _run_pipeline(bugs, sbert, tok, clf)
                _store_analysis(results, bugs, dup_map, total, dup_count, pdf_bytes,
                                pending_file.name)

            elif pending_text is not None:
                step_bubble("Splitting text into bug blocks…")
                bugs  = split_text_input(pending_text)
                total = len(bugs)
                results, dup_map, dup_count, pdf_bytes = _run_pipeline(bugs, sbert, tok, clf)
                label = pending_text[:40] + "…"
                st.session_state.pending_text = None
                _store_analysis(results, bugs, dup_map, total, dup_count, pdf_bytes, label)

    # ── Render all analyses in chat order ─────────────────────────────────────
    for i, analysis in enumerate(analyses):
        results  = analysis["results"]
        bugs     = analysis["bugs"]
        dup_map  = analysis["dup_map"]
        total    = analysis["total"]
        dups     = analysis["dups"]
        label    = analysis["user_label"]

        # User message
        user_bubble(label)
        ai_bubble("Analysis complete. Here's your full triage report:")
        render_analytics(results, total, dups)
        ai_bubble(
            f"Classified <strong>{len(results)}</strong> unique "
            f"bug{'s' if len(results)!=1 else ''}."
        )

        # Show Canvas button for each analysis
        is_active = (st.session_state.active_canvas == i)
        btn_label = f"📋 {'Viewing Canvas' if is_active else 'Show Canvas →'} — Analysis #{i+1}"
        if st.button(btn_label, key=f"show_canvas_{i}"):
            st.session_state.active_canvas  = i
            st.session_state.show_solutions = False
            st.rerun()

    # ── General answer (non-bug chat) ─────────────────────────────────────────
    if st.session_state.get("general_answer"):
        user_bubble(st.session_state.get("user_label", ""))
        ai_bubble(st.session_state.general_answer)

    # ── Active canvas ─────────────────────────────────────────────────────────
    active_idx = st.session_state.active_canvas
    if 0 <= active_idx < len(analyses):
        active = analyses[active_idx]

        # Handle solution generation request from canvas
        canvas_msg = st.session_state.get("_canvas_msg")
        if canvas_msg == "gen_solutions" and active.get("solutions_data") is None:
            del st.session_state["_canvas_msg"]
            from app.helpers.solution_agent import get_solutions_for_all_bugs
            with st.spinner("Generating AI solutions…"):
                sols = get_solutions_for_all_bugs(active["results"])
            # Save into in-memory analyses list
            st.session_state.analyses[active_idx]["solutions_data"] = sols
            # Save into JSON session file
            update_solutions(st.session_state.session_id, active_idx, sols)
            st.session_state["_auto_show_solutions"] = True
            st.rerun()
        elif isinstance(canvas_msg, (int, float)) and canvas_msg >= 0:
            st.session_state.canvas_width_px = int(canvas_msg) if canvas_msg > 0 else 480
            if "_canvas_msg" in st.session_state:
                del st.session_state["_canvas_msg"]

        render_canvas(
            active["results"],
            active["bugs"],
            active["dup_map"],
            active["pdf_bytes"],
            session_label=active["user_label"],
            analysis_idx=active_idx,
            solutions_data=active.get("solutions_data"),
        )

    # ── File upload ───────────────────────────────────────────────────────────
    if st.session_state.show_upload and not st.session_state.processing:
        uploaded = st.file_uploader(
            "Upload PDF bug report", type=["pdf"],
            key="file_upload", label_visibility="visible"
        )
        if uploaded is not None:
            st.session_state.user_label   = f"📄 {uploaded.name}"
            st.session_state.pending_file = uploaded
            st.session_state.processing   = True
            st.session_state.show_upload  = False
            st.rerun()

    # ── Input bar ─────────────────────────────────────────────────────────────
    send_clicked = render_input_bar()

    if send_clicked:
        raw = st.session_state.get("user_text_input", "").strip()
        if raw and not st.session_state.processing:
            bug_indicators = [
                "bug", "crash", "error", "freeze", "hang", "memory", "leak",
                "fails", "broken", "overlap", "not working", "issue", "exception",
                "fatal", "slow", "unresponsive", "closes", "stops", "blank",
                "missing", "wrong", "incorrect", "typo", "glitch", "ui", "visual",
                "button", "screen", "app", "application", "software", "login",
                "upload", "download", "database", "server", "ram", "cpu",
            ]
            raw_lower  = raw.lower()
            is_bug     = any(w in raw_lower for w in bug_indicators) and len(raw.split()) >= 5

            if is_bug:
                st.session_state.user_label     = raw
                st.session_state.pending_text   = raw
                st.session_state.processing     = True
                st.session_state.general_answer = None
                st.rerun()
            else:
                greetings = ["hi","hello","hey","thanks","thank you","ok","okay",
                             "great","nice","cool","good","bye","goodbye","yes","no","sure"]
                is_greeting = any(raw_lower.strip("!.,?") == g for g in greetings)
                replies = {
                    "thanks":    "You're welcome! Paste more bugs or upload a PDF anytime.",
                    "thank you": "You're welcome! Let me know if you have more bugs to analyze.",
                    "hi":        "Hello! Paste bug descriptions or upload a PDF to get started.",
                    "hello":     "Hi there! Ready to classify your bugs.",
                    "hey":       "Hey! Paste your bug descriptions or upload a PDF to begin.",
                    "bye":       "Goodbye! Come back whenever you have bugs to triage.",
                    "ok":        "Got it! Let me know when you're ready.",
                    "okay":      "Got it! Let me know when you're ready.",
                    "great":     "Glad to help! Upload more bug reports whenever you're ready.",
                    "yes":       "Great! Go ahead and paste your bug descriptions or upload a PDF.",
                    "no":        "No problem. Let me know when you're ready.",
                }
                if is_greeting:
                    answer = replies.get(raw_lower.strip("!.,?"), "Got it!")
                else:
                    answer = (
                        "I'm a bug triage assistant. Paste bug descriptions or use "
                        "the <strong>+</strong> button to upload a PDF."
                    )
                st.session_state.user_label     = raw
                st.session_state.general_answer = answer
                st.rerun()


main()