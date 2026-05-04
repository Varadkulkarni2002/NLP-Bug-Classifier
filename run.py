import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.helpers.config import APP_TITLE, APP_ICON
from app.helpers.classifier import load_classifier, classify_bug
from app.helpers.sbert import load_sbert, deduplicate
from app.helpers.pdf_parser import extract_paragraphs, split_text_input
from app.helpers.pdf_report import build_pdf
from app.helpers.chat_history import save_session
from app.ui.components import (
    inject_css, render_header, render_sidebar, render_welcome,
    ai_bubble, user_bubble, step_bubble,
    render_analytics, render_bug_card,
    render_export_buttons, render_input_bar, render_canvas,
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
        "results":        None,
        "pdf_bytes":      None,
        "bugs":           None,
        "dup_map":        None,
        "total_bugs":     0,
        "dup_count":      0,
        "show_upload":    False,
        "processing":     False,
        "pending_text":   None,
        "pending_file":   None,
        "user_label":     "",
        "session_id":     None,
        "history":        [],
        "show_solutions": False,
        "solutions_data": None,
        "general_answer": None,
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
        f"<strong>{dup_count}</strong> duplicates · "
        f"classifying with temperature scaling…"
    )
    results   = [_build_result_entry(idx, bugs, dup_map, tok, clf) for idx in unique_ids]
    pdf_bytes = build_pdf(results, bugs, dup_map, len(bugs), dup_count)
    return results, dup_map, dup_count, pdf_bytes


def _store_and_rerun(results, bugs, dup_map, total, dup_count, pdf_bytes, label):
    session_id = save_session(label, results, bugs, total, dup_count)
    st.session_state.results         = results
    st.session_state.bugs            = bugs
    st.session_state.dup_map         = dup_map
    st.session_state.total_bugs      = total
    st.session_state.dup_count       = dup_count
    st.session_state.pdf_bytes       = pdf_bytes
    st.session_state.session_id      = session_id
    st.session_state.processing      = False
    st.session_state.show_solutions  = False
    st.session_state.solutions_data  = None
    st.session_state.canvas_width_px = 480   # re-open canvas fresh on every new analysis
    st.rerun()


def main():
    _init_state()
    inject_css()
    render_sidebar()
    render_header()

    if st.session_state.results is None and not st.session_state.processing:
        render_welcome()

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
                    ai_bubble("⚠️ No readable text found. Please upload a PDF with selectable text.")
                    st.session_state.processing   = False
                    st.session_state.pending_file = None
                    st.rerun()
                results, dup_map, dup_count, pdf_bytes = _run_pipeline(bugs, sbert, tok, clf)
                _store_and_rerun(results, bugs, dup_map, total, dup_count, pdf_bytes,
                                 pending_file.name)

            elif pending_text is not None:
                step_bubble("Splitting text into bug blocks…")
                bugs  = split_text_input(pending_text)
                total = len(bugs)
                results, dup_map, dup_count, pdf_bytes = _run_pipeline(bugs, sbert, tok, clf)
                label = pending_text[:40] + "…"
                st.session_state.pending_text = None
                _store_and_rerun(results, bugs, dup_map, total, dup_count, pdf_bytes, label)

    if st.session_state.results is not None:
        results = st.session_state.results
        bugs    = st.session_state.bugs
        dup_map = st.session_state.dup_map
        total   = st.session_state.total_bugs
        dups    = st.session_state.dup_count

        user_bubble(st.session_state.get("user_label") or
                    f"📄 Uploaded bug report — {total} text blocks extracted")
        ai_bubble("Analysis complete. Here's your full triage report:")
        render_analytics(results, total, dups)
        ai_bubble(
            f"Classified <strong>{len(results)}</strong> unique "
            f"bug{'s' if len(results)!=1 else ''}. "
            f"View details, download, and get solutions in the canvas on the right:"
        )

        render_canvas(
            results, bugs, dup_map,
            st.session_state.pdf_bytes,
            session_label=st.session_state.get("user_label", "Bug Report"),
        )

    if st.session_state.get("general_answer"):
        user_bubble(st.session_state.get("user_label", ""))
        ai_bubble(st.session_state.general_answer)

    if st.session_state.show_upload and not st.session_state.processing:
        uploaded = st.file_uploader(
            "Upload PDF bug report",
            type=["pdf"],
            key="file_upload",
            label_visibility="visible"
        )
        if uploaded is not None:
            st.session_state.user_label   = f"📄 {uploaded.name}"
            st.session_state.pending_file = uploaded
            st.session_state.processing   = True
            st.session_state.show_upload  = False
            st.rerun()

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
            raw_lower = raw.lower()
            word_count = len(raw.split())
            is_bug = (
                any(w in raw_lower for w in bug_indicators)
                and word_count >= 5
            )

            if is_bug:
                st.session_state.user_label     = raw
                st.session_state.pending_text   = raw
                st.session_state.processing     = True
                st.session_state.general_answer = None
                st.rerun()
            else:
                greetings = ["hi", "hello", "hey", "thanks", "thank you",
                             "ok", "okay", "great", "nice", "cool", "good",
                             "bye", "goodbye", "yes", "no", "sure"]
                is_greeting = any(raw_lower.strip("!.,?") == g for g in greetings)

                if is_greeting:
                    replies = {
                        "thanks": "You're welcome! Upload a PDF or paste bug descriptions anytime to run a new analysis.",
                        "thank you": "You're welcome! Let me know if you have more bugs to analyze.",
                        "hi": "Hello! Upload a PDF or paste bug descriptions below to get started.",
                        "hello": "Hi there! Ready to classify your bugs — just upload a PDF or paste them below.",
                        "hey": "Hey! Paste your bug descriptions or upload a PDF to begin.",
                        "bye": "Goodbye! Come back whenever you have bugs to triage.",
                        "goodbye": "Goodbye! Come back whenever you have bugs to triage.",
                        "ok": "Got it! Let me know when you're ready to analyze more bugs.",
                        "okay": "Got it! Let me know when you're ready to analyze more bugs.",
                        "great": "Glad to help! Upload more bug reports whenever you're ready.",
                        "nice": "Thanks! Feel free to upload another bug report anytime.",
                        "cool": "Thanks! Feel free to upload another bug report anytime.",
                        "good": "Good to hear! Let me know if you have more bugs to triage.",
                        "yes": "Great! Go ahead and paste your bug descriptions or upload a PDF.",
                        "no": "No problem. Let me know when you're ready.",
                        "sure": "Sure! Paste your bug descriptions or use the + button to upload a PDF.",
                    }
                    answer = replies.get(raw_lower.strip("!.,?"),
                                         "Got it! Paste bug descriptions or upload a PDF to analyze.")
                else:
                    answer = (
                        "I'm a bug triage assistant. I can classify bugs by type, severity, "
                        "and fix time. To get started, either paste your bug descriptions "
                        "directly in the input box or use the <strong>+</strong> button to "
                        "upload a PDF bug report."
                    )

                st.session_state.user_label     = raw
                st.session_state.general_answer = answer
                st.rerun()


main()