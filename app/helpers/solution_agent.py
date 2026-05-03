import os
import re
import time
import requests
import streamlit as st
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util
from app.helpers.config import BASE_DIR

MINILM_MODEL_NAME = "all-MiniLM-L6-v2"
MINILM_CACHE_PATH = os.path.join(BASE_DIR, "models", "minilm")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

SO_SEARCH_URL     = "https://api.stackexchange.com/2.3/search/advanced"
GITHUB_SEARCH_URL = "https://api.github.com/search/issues"

BUG_TYPE_KEYWORDS = {
    "Crash":     ["crash", "fatal error", "exception", "force quit", "terminated"],
    "Freeze":    ["freeze", "hang", "not responding", "locks up", "deadlock"],
    "Memory":    ["memory leak", "RAM usage", "out of memory", "heap", "garbage collection"],
    "UI/Visual": ["UI bug", "visual glitch", "overlap", "layout broken", "CSS"],
    "Other":     ["bug fix", "issue", "error"],
}


@st.cache_resource(show_spinner=False)
def _load_minilm() -> SentenceTransformer:
    os.makedirs(MINILM_CACHE_PATH, exist_ok=True)
    model = SentenceTransformer(MINILM_MODEL_NAME, cache_folder=MINILM_CACHE_PATH)
    return model


def _build_query(bug_text: str, bug_type: str) -> str:
    keywords = BUG_TYPE_KEYWORDS.get(bug_type, BUG_TYPE_KEYWORDS["Other"])
    clean    = re.sub(r'Bug\s+\d+\s*[:\-]', '', bug_text, flags=re.IGNORECASE).strip()
    clean    = re.sub(r'["\']', '', clean).strip()
    clean    = clean[:120]
    kw       = keywords[0]
    return f"{clean} {kw} fix"


def _scrape_stackoverflow(query: str, max_results: int = 3) -> list[dict]:
    try:
        params = {
            "order":    "desc",
            "sort":     "relevance",
            "q":        query,
            "site":     "stackoverflow",
            "pagesize": max_results,
            "filter":   "withbody",
        }
        resp = requests.get(SO_SEARCH_URL, params=params, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return []
        data  = resp.json()
        items = data.get("items", [])
        results = []
        for item in items[:max_results]:
            title   = item.get("title", "")
            link    = item.get("link", "")
            body    = BeautifulSoup(item.get("body", ""), "html.parser").get_text()
            body    = re.sub(r'\s+', ' ', body).strip()[:400]
            score   = item.get("score", 0)
            answers = item.get("answer_count", 0)
            if title and link:
                results.append({
                    "source":  "Stack Overflow",
                    "title":   title,
                    "url":     link,
                    "snippet": body,
                    "score":   score,
                    "answers": answers,
                })
        return results
    except Exception:
        return []


def _scrape_github(query: str, bug_type: str, max_results: int = 2) -> list[dict]:
    try:
        params = {
            "q":        f"{query} is:issue is:closed label:bug",
            "sort":     "reactions",
            "order":    "desc",
            "per_page": max_results,
        }
        resp = requests.get(GITHUB_SEARCH_URL, params=params, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return []
        items   = resp.json().get("items", [])
        results = []
        for item in items[:max_results]:
            title   = item.get("title", "")
            url     = item.get("html_url", "")
            body    = item.get("body") or ""
            body    = re.sub(r'\s+', ' ', body).strip()[:300]
            if title and url:
                results.append({
                    "source":  "GitHub Issues",
                    "title":   title,
                    "url":     url,
                    "snippet": body,
                    "score":   item.get("reactions", {}).get("total_count", 0),
                    "answers": 0,
                })
        return results
    except Exception:
        return []


def _rank_by_relevance(
    bug_text: str,
    results:  list[dict],
    model:    SentenceTransformer,
) -> list[dict]:
    if not results:
        return []
    bug_emb     = model.encode(bug_text, convert_to_tensor=True)
    snippets    = [f"{r['title']} {r['snippet']}" for r in results]
    snip_embs   = model.encode(snippets, convert_to_tensor=True)
    scores      = util.cos_sim(bug_emb, snip_embs)[0].tolist()
    for i, r in enumerate(results):
        r["relevance"] = round(scores[i], 4)
    return sorted(results, key=lambda x: x["relevance"], reverse=True)


def _format_solution_html(
    bug_text:  str,
    bug_type:  str,
    results:   list[dict],
) -> str:
    if not results:
        return (
            '<div style="color:var(--muted);font-size:0.82rem;">'
            'No relevant solutions found online for this bug. '
            'Try searching manually on Stack Overflow or GitHub Issues.'
            '</div>'
        )

    source_icon = {"Stack Overflow": "🟠", "GitHub Issues": "🐙"}
    cards       = ""
    for r in results[:4]:
        icon      = source_icon.get(r["source"], "🔗")
        relevance = int(r["relevance"] * 100)
        snippet   = r["snippet"][:250] + ("..." if len(r["snippet"]) > 250 else "")
        score_txt = f"Score: {r['score']}" if r["score"] else ""
        ans_txt   = f"· {r['answers']} answers" if r.get("answers") else ""
        cards += f"""
        <div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.08);
                    border-radius:9px;padding:0.7rem 0.85rem;margin-bottom:0.55rem;">
            <div style="display:flex;align-items:center;justify-content:space-between;
                        margin-bottom:0.35rem;">
                <span style="font-size:0.7rem;color:var(--muted);">
                    {icon} {r['source']} &nbsp;·&nbsp; {score_txt}{ans_txt}
                </span>
                <span style="font-size:0.65rem;background:rgba(52,211,153,0.12);
                             color:#34d399;border:1px solid rgba(52,211,153,0.2);
                             border-radius:20px;padding:0.1rem 0.45rem;">
                    {relevance}% match
                </span>
            </div>
            <div style="font-size:0.82rem;font-weight:600;color:var(--text);margin-bottom:0.3rem;">
                <a href="{r['url']}" target="_blank"
                   style="color:var(--accent2);text-decoration:none;">
                    {r['title']}
                </a>
            </div>
            <div style="font-size:0.75rem;color:var(--muted);line-height:1.55;">
                {snippet}
            </div>
        </div>"""

    keywords_used = ", ".join(BUG_TYPE_KEYWORDS.get(bug_type, ["bug fix"])[:3])
    return f"""
    <div style="font-size:0.75rem;color:var(--muted);margin-bottom:0.65rem;">
        Searched Stack Overflow &amp; GitHub Issues for
        <strong style="color:var(--accent2);">{bug_type}</strong> bugs ·
        keywords: <em>{keywords_used}</em>
    </div>
    {cards}
    <div style="font-size:0.7rem;color:var(--dim);margin-top:0.4rem;">
        Results ranked by semantic similarity to your bug description using MiniLM.
    </div>"""


def get_solution(bug_text: str, bug_type: str) -> str:
    try:
        model   = _load_minilm()
        query   = _build_query(bug_text, bug_type)
        so_hits = _scrape_stackoverflow(query, max_results=3)
        time.sleep(0.5)
        gh_hits = _scrape_github(query, bug_type, max_results=2)
        all_hits = so_hits + gh_hits
        ranked   = _rank_by_relevance(bug_text, all_hits, model)
        return _format_solution_html(bug_text, bug_type, ranked)
    except Exception as e:
        return (
            f'<div style="color:#fb923c;font-size:0.8rem;">'
            f'⚠️ Could not fetch solutions: {str(e)[:120]}'
            f'</div>'
        )
