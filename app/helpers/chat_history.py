import os
import json
from datetime import datetime
from app.helpers.config import CHAT_HISTORY_PATH


def _load_all() -> list[dict]:
    if not os.path.exists(CHAT_HISTORY_PATH):
        return []
    with open(CHAT_HISTORY_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_all(sessions: list[dict]) -> None:
    os.makedirs(os.path.dirname(CHAT_HISTORY_PATH), exist_ok=True)
    with open(CHAT_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)


def save_session(
    label: str,
    results: list[dict],
    bugs: list[str],
    total_bugs: int,
    dup_count: int,
) -> str:
    sessions   = _load_all()
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    sessions.append({
        "id":         session_id,
        "label":      label[:60],
        "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_bugs": total_bugs,
        "dup_count":  dup_count,
        "unique":     len(results),
        "results":    results,
        "bugs":       bugs,
    })
    sessions = sessions[-50:]
    _save_all(sessions)
    return session_id


def load_session(session_id: str) -> dict | None:
    sessions = _load_all()
    for s in sessions:
        if s["id"] == session_id:
            return s
    return None


def list_sessions() -> list[dict]:
    sessions = _load_all()
    return [
        {
            "id":        s["id"],
            "label":     s.get("label", "Untitled"),
            "timestamp": s.get("timestamp", ""),
            "total":     s.get("total_bugs", 0),
            "unique":    s.get("unique", 0),
            "dups":      s.get("dup_count", 0),
        }
        for s in reversed(sessions)
    ]


def delete_session(session_id: str) -> bool:
    sessions = _load_all()
    new      = [s for s in sessions if s["id"] != session_id]
    if len(new) == len(sessions):
        return False
    _save_all(new)
    return True


def clear_all_sessions() -> None:
    _save_all([])
