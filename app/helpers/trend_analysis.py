import json
import os
from collections import Counter
from app.helpers.config import METRICS_PATH, HISTORY_PATH


def compute_session_analytics(results: list[dict], total: int, dup_count: int) -> dict:
    unique       = len(results)
    type_counts  = Counter(r["bug_type"]  for r in results)
    sev_counts   = Counter(r["severity"]  for r in results)
    fix_counts   = Counter(r["fix_time"]  for r in results)
    uncertain    = sum(1 for r in results if r.get("is_uncertain", False))
    avg_bt_conf  = round(sum(r.get("bt_conf", 0) for r in results) / unique, 1) if unique else 0
    avg_sv_conf  = round(sum(r.get("sv_conf", 0) for r in results) / unique, 1) if unique else 0
    avg_ft_conf  = round(sum(r.get("ft_conf", 0) for r in results) / unique, 1) if unique else 0
    dup_rate     = round((dup_count / total * 100), 1) if total else 0

    return {
        "total":        total,
        "unique":       unique,
        "dup_count":    dup_count,
        "dup_rate":     dup_rate,
        "uncertain":    uncertain,
        "type_counts":  dict(type_counts.most_common()),
        "sev_counts":   dict(sev_counts.most_common()),
        "fix_counts":   dict(fix_counts.most_common()),
        "avg_bt_conf":  avg_bt_conf,
        "avg_sv_conf":  avg_sv_conf,
        "avg_ft_conf":  avg_ft_conf,
        "dominant_type": type_counts.most_common(1)[0][0] if type_counts else "N/A",
        "dominant_sev":  sev_counts.most_common(1)[0][0]  if sev_counts  else "N/A",
    }


def trend_bars_html(counts: dict, total: int, color_map: dict | None = None) -> str:
    if not counts or total == 0:
        return ""
    html = ""
    for label, cnt in counts.items():
        pct   = int(cnt / total * 100)
        color = (color_map or {}).get(label, "#7c5cfc")
        html += (
            f'<div style="margin-bottom:0.5rem;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:0.7rem;color:var(--muted);margin-bottom:0.28rem;">'
            f'<span style="color:{color}">{label}</span>'
            f'<span>{cnt} · {pct}%</span></div>'
            f'<div style="background:rgba(255,255,255,0.05);border-radius:3px;height:5px;overflow:hidden;">'
            f'<div style="width:{pct}%;height:100%;border-radius:3px;'
            f'background:linear-gradient(90deg,{color},{color}88);"></div>'
            f'</div></div>'
        )
    return html


def load_training_metrics() -> dict:
    if not os.path.exists(METRICS_PATH):
        return {}
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def load_training_history() -> dict:
    if not os.path.exists(HISTORY_PATH):
        return {}
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def model_performance_summary() -> dict:
    metrics = load_training_metrics()
    history = load_training_history()
    return {
        "metrics": metrics,
        "history": history,
        "has_metrics": bool(metrics),
        "has_history": bool(history),
    }


def cross_session_trends(sessions: list[dict]) -> dict:
    if not sessions:
        return {}
    all_types = Counter()
    all_sevs  = Counter()
    total_bugs = 0
    total_dups = 0
    for s in sessions:
        results = s.get("results", [])
        total_bugs += s.get("total_bugs", 0)
        total_dups += s.get("dup_count", 0)
        for r in results:
            all_types[r.get("bug_type", "Unknown")] += 1
            all_sevs[r.get("severity", "unknown")]  += 1
    return {
        "total_bugs_all_sessions": total_bugs,
        "total_dups_all_sessions": total_dups,
        "type_counts":  dict(all_types.most_common()),
        "sev_counts":   dict(all_sevs.most_common()),
        "session_count": len(sessions),
    }
