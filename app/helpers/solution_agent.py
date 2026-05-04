import os
import time
import json
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
from app.helpers.config import BASE_DIR

# 1. Point explicitly to the .env file at the root of your project
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=env_path)

# 2. Fetch the key securely
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

try:
    if not GROQ_API_KEY:
        raise ValueError(f"GROQ_API_KEY not found. Make sure your file is named exactly '.env' and is located at {env_path}")
    client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    print(f"[solution_agent] Groq initialization failed: {e}")
    client = None

def get_solution_for_bug(bug_text: str, bug_type: str) -> dict:
    if not client:
        return _error_state(bug_text, bug_type, "Groq client not initialized. Check your API key.")

    print(f"\n[solution_agent] Querying Groq for: {bug_text[:60]}...")
    
    prompt = f"""You are a senior software engineer. Analyze this bug report:
Bug Description: {bug_text}
Bug Type: {bug_type}

Provide a root cause analysis and a recommended fix. 
Respond ONLY with a valid JSON object containing exactly three string keys:
"why": A short, technical explanation of the root cause (2-3 sentences).
"fix": A clear, actionable recommended fix (2-3 sentences).
"code": A relevant code snippet implementing the fix. If no code is needed, leave as an empty string. Do not use markdown backticks inside the JSON string value.
"""
    try:
        # Using the latest supported Llama 3.3 70B model
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        sol_data = json.loads(content)
        
        return {
            "query": bug_text[:100],
            "mode": "groq",
            "bug_type": bug_type,
            "groq_data": sol_data
        }
    except Exception as e:
        print(f"[solution_agent] Groq API Error: {e}")
        return _error_state(bug_text, bug_type, str(e))

def _error_state(bug_text: str, bug_type: str, error_msg: str) -> dict:
    return {
        "query": bug_text[:100],
        "mode": "error",
        "bug_type": bug_type,
        "groq_data": {
            "why": "API Connection Failed",
            "fix": f"Could not generate solution. Error: {error_msg}",
            "code": ""
        }
    }

def get_solutions_for_all_bugs(results: list[dict]) -> list[dict]:
    solutions = []
    for r in results:
        bug_text = r.get("text", "")
        if not bug_text:
            continue
            
        sol = get_solution_for_bug(bug_text, r.get("bug_type", "Other"))
        solutions.append({
            "bug_text":  bug_text,
            "bug_type":  r.get("bug_type", ""),
            "severity":  r.get("severity", ""),
            "fix_time":  r.get("fix_time", ""),
            "mode":      sol["mode"],
            "groq_data": sol["groq_data"]
        })
        # Groq is fast, but a tiny sleep prevents rate-limiting on the free tier
        time.sleep(0.5) 
    return solutions

def _render_answer_html(solution: dict) -> str:
    groq_data = solution.get("groq_data", {})
    why_text  = groq_data.get("why", "No analysis available.")
    fix_text  = groq_data.get("fix", "No fix available.")
    code_text = groq_data.get("code", "")
    mode      = solution.get("mode", "error")

    if mode == "error":
        return f'<div style="font-size:0.75rem;color:#dc2626;font-weight:600;padding:1rem;background:#fee2e2;border-radius:8px;text-align:center;">{fix_text}</div>'

    answer = (
        f'<div style="font-size:0.7rem;font-weight:600;color:#dc2626;'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.35rem;">'
        f'Root Cause Analysis</div>'
        f'<p style="font-size:0.855rem;color:#1c1b20;line-height:1.8;'
        f'margin-bottom:0.85rem;">{why_text}</p>'
        f'<div style="font-size:0.7rem;font-weight:600;color:#16a34a;'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.35rem;">'
        f'Recommended Fix</div>'
        f'<p style="font-size:0.855rem;color:#1c1b20;line-height:1.8;'
        f'margin-bottom:0.5rem;">{fix_text}</p>'
    )

    if code_text and code_text.strip():
        answer += (
            f'<div style="font-size:0.68rem;font-weight:600;color:#2563eb;'
            f'margin-bottom:0.3rem;margin-top:0.8rem;">Code Implementation</div>'
            f'<pre style="background:#f1f5f9;border:1px solid #e2e8f0;'
            f'border-radius:8px;padding:0.7rem 0.9rem;font-size:0.76rem;'
            f'color:#1e293b;overflow-x:auto;line-height:1.6;'
            f'white-space:pre-wrap;margin-bottom:0.6rem;">{code_text.strip()}</pre>'
        )

    return answer

def render_solution_card(solution: dict, bug_number: int) -> str:
    bug_text = solution["bug_text"]
    severity = solution["severity"]
    bug_type = solution["bug_type"]
    fix_time = solution["fix_time"]

    sev_color = {
        "critical": "#dc2626",
        "major":    "#ea580c",
        "minor":    "#16a34a",
    }.get(severity.lower(), "#6c47ff")
    sev_bg = {
        "critical": "#fee2e2",
        "major":    "#ffedd5",
        "minor":    "#dcfce7",
    }.get(severity.lower(), "#ede9ff")

    answer_html = _render_answer_html(solution)

    return f"""
    <div style="background:#ffffff;border:1px solid #e8e6df;
                border-radius:12px;padding:1rem 1.1rem;margin-bottom:0.85rem;
                border-left:3px solid {sev_color};
                box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <div style="font-size:0.62rem;font-weight:600;color:#9896a8;
                    text-transform:uppercase;letter-spacing:0.08em;
                    margin-bottom:0.4rem;">Bug #{bug_number}</div>
        <div style="font-size:0.8rem;color:#6b6880;font-style:italic;
                    background:#f8f7f4;border-radius:7px;
                    padding:0.45rem 0.65rem;margin-bottom:0.6rem;line-height:1.5;">
            {bug_text[:180]}{"…" if len(bug_text) > 180 else ""}
        </div>
        <div style="display:flex;gap:0.35rem;flex-wrap:wrap;margin-bottom:0.75rem;">
            <span style="padding:0.2rem 0.6rem;border-radius:20px;font-size:0.63rem;
                         font-weight:600;color:{sev_color};background:{sev_bg};">
                {severity.upper()}
            </span>
            <span style="padding:0.2rem 0.6rem;border-radius:20px;font-size:0.63rem;
                         font-weight:600;color:#6c47ff;background:#ede9ff;">
                {bug_type}
            </span>
            <span style="padding:0.2rem 0.6rem;border-radius:20px;font-size:0.63rem;
                         font-weight:600;color:#2563eb;background:#dbeafe;">
                ⏱ {fix_time}
            </span>
        </div>
        {answer_html}
    </div>"""

def render_all_solutions_html(solutions: list[dict]) -> str:
    if not solutions:
        return '<p style="color:#7878a8;">No solutions generated.</p>'

    cards = "".join(
        render_solution_card(s, i + 1)
        for i, s in enumerate(solutions)
    )

    return f"""
    <div style="font-size:0.68rem;font-weight:700;color:#6c47ff;
                text-transform:uppercase;letter-spacing:0.08em;
                margin-bottom:0.3rem;">
        💡 Solution Report — {len(solutions)} bug{"s" if len(solutions) != 1 else ""}
    </div>
    <div style="font-size:0.7rem;color:#9896a8;margin-bottom:0.85rem;">
        Solutions generated in real-time by Llama-3.3 (Groq)
    </div>
    {cards}
    """