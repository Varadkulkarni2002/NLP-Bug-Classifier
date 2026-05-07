import os
import json
from datetime import datetime
from app.helpers.config import BASE_DIR

# Each session is its own JSON file in sessions/
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")


def _session_path(session_id: str) -> str:
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    return os.path.join(SESSIONS_DIR, f"{session_id}.json")


def _load_session_file(session_id: str) -> dict | None:
    path = _session_path(session_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None


def _save_session_file(data: dict) -> None:
    path = _session_path(data["id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _index_path() -> str:
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    return os.path.join(SESSIONS_DIR, "_index.json")


def _load_index() -> list[dict]:
    path = _index_path()
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_index(entries: list[dict]) -> None:
    with open(_index_path(), "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def create_session(label: str) -> str:
    """Create a new empty session, return its ID."""
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    data = {
        "id":        session_id,
        "label":     label[:60],
        "created":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "analyses":  [],
    }
    _save_session_file(data)

    index = _load_index()
    index.append({
        "id":      session_id,
        "label":   label[:60],
        "created": data["created"],
        "updated": data["updated"],
        "count":   0,
    })
    index = index[-50:]
    _save_index(index)
    return session_id


def append_analysis(
    session_id: str,
    user_label: str,
    results: list[dict],
    bugs: list[str],
    dup_map: dict,
    total: int,
    dup_count: int,
    solutions_data: list[dict] | None = None,
) -> int:
    """Append one analysis to an existing session. Returns analysis index."""
    data = _load_session_file(session_id)
    if data is None:
        return -1

    idx = len(data["analyses"])
    data["analyses"].append({
        "index":          idx,
        "user_label":     user_label[:80],
        "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total":          total,
        "dups":           dup_count,
        "unique":         len(results),
        "results":        results,
        "bugs":           bugs,
        "dup_map":        {str(k): v for k, v in dup_map.items()},
        "has_solutions":  solutions_data is not None,
        "solutions_data": solutions_data,
    })
    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_session_file(data)

    # Update index
    index = _load_index()
    for entry in index:
        if entry["id"] == session_id:
            entry["updated"] = data["updated"]
            entry["count"]   = len(data["analyses"])
            entry["label"]   = data["analyses"][0]["user_label"][:60]
            break
    _save_index(index)
    return idx


def update_solutions(session_id: str, analysis_idx: int, solutions_data: list[dict]) -> None:
    """Save solutions into an existing analysis entry."""
    data = _load_session_file(session_id)
    if data is None or analysis_idx >= len(data["analyses"]):
        return
    data["analyses"][analysis_idx]["has_solutions"]  = True
    data["analyses"][analysis_idx]["solutions_data"] = solutions_data
    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_session_file(data)


def load_session(session_id: str) -> dict | None:
    return _load_session_file(session_id)


def list_sessions() -> list[dict]:
    index = _load_index()
    return list(reversed(index))


def delete_session(session_id: str) -> bool:
    path = _session_path(session_id)
    if os.path.exists(path):
        os.remove(path)
    index = _load_index()
    new   = [e for e in index if e["id"] != session_id]
    if len(new) == len(index):
        return False
    _save_index(new)
    return True


def clear_all_sessions() -> None:
    index = _load_index()
    for entry in index:
        path = _session_path(entry["id"])
        if os.path.exists(path):
            os.remove(path)
    _save_index([])


# ── Legacy compat ──────────────────────────────────────────────────────────────
def save_session(label, results, bugs, total, dup_count):
    sid = create_session(label)
    append_analysis(sid, label, results, bugs, {}, total, dup_count)
    return sid


def update_session(session_id, results, bugs, total, dup_count):
    return session_id