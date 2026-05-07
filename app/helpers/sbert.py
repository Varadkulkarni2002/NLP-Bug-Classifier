import re
import numpy as np
import streamlit as st
from sentence_transformers import SentenceTransformer
from app.helpers.config import SBERT_PATH, DEVICE, DEDUP_THRESHOLD


@st.cache_resource(show_spinner=False)
def load_sbert() -> SentenceTransformer:
    return SentenceTransformer(SBERT_PATH, device=DEVICE)


def embed(texts: list[str], model: SentenceTransformer) -> np.ndarray:
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    return np.dot(embeddings, embeddings.T)


# ── Action-verb fingerprint: captures WHAT is happening, not domain words ──
# Maps surface patterns to a semantic intent token
_INTENT_PATTERNS = [
    (r"\b(crash|crashes|crashed|crashing|fatal|aborted|killed|core dump|segfault)\b", "CRASH"),
    (r"\b(freeze|frozen|freezes|hang|hung|hangs|stuck|locks up|lock up|unresponsive|stops responding)\b", "FREEZE"),
    (r"\b(memory|ram|heap|leak|leaking|oom|out of memory|balloo|consumption grows)\b", "MEMORY"),
    (r"\b(overlap|misalign|render|visual|display|flicker|glitch|opacity|layout|css|icon|font|hover)\b", "UI"),
    (r"\b(close|closes|closing|button|click|tap|press)\b", "ACTION_CLOSE"),
    (r"\b(open|opens|opening|launch|launches|start|starts)\b", "ACTION_OPEN"),
    (r"\b(export|import|save|load|upload|download|sync|backup)\b", "ACTION_DATA"),
    (r"\b(login|logout|auth|password|token|session|permission)\b", "ACTION_AUTH"),
    (r"\b(database|db|query|sql|table|record|row)\b", "COMPONENT_DB"),
    (r"\b(network|api|request|response|timeout|connection|endpoint)\b", "COMPONENT_NET"),
    (r"\b(dashboard|page|screen|tab|panel|modal|dialog|window)\b", "COMPONENT_UI"),
]

def _intent_fingerprint(text: str) -> set[str]:
    """Extract a set of semantic intent tokens from bug text. Never shown to user."""
    text_lower = text.lower()
    tokens = set()
    for pattern, token in _INTENT_PATTERNS:
        if re.search(pattern, text_lower):
            tokens.add(token)
    return tokens


def _intents_compatible(text_a: str, text_b: str) -> bool:
    """
    Returns True if two bugs share the same core intent.
    Prevents bugs like 'DB crashed' vs 'close button hangs' from being
    marked as duplicates just because both mention crash-adjacent words.
    """
    fa = _intent_fingerprint(text_a)
    fb = _intent_fingerprint(text_b)

    if not fa or not fb:
        return True  # Can't determine — let SBERT score decide

    # Crash and Freeze intents are mutually exclusive
    exclusive_pairs = [
        {"CRASH", "FREEZE"},
        {"CRASH", "UI"},
        {"MEMORY", "UI"},
        {"FREEZE", "MEMORY"},
    ]
    for pair in exclusive_pairs:
        if fa & pair and fb & pair and not (fa & pair == fb & pair):
            return False  # One has CRASH, other has FREEZE → not duplicates

    # They must share at least one non-ACTION intent to be considered duplicates
    core_intents = {"CRASH", "FREEZE", "MEMORY", "UI"}
    core_a = fa & core_intents
    core_b = fb & core_intents

    if core_a and core_b and not (core_a & core_b):
        return False  # Different core bug categories → not duplicates

    return True


def deduplicate(
    bugs: list[str],
    sbert_model: SentenceTransformer,
    threshold: float = DEDUP_THRESHOLD,
) -> tuple[list[int], dict[int, list[int]], list[list[int]]]:
    if not bugs:
        return [], {}, []

    emb     = embed(bugs, sbert_model)
    sim     = similarity_matrix(emb)
    visited = [False] * len(bugs)
    groups  = []

    for i in range(len(bugs)):
        if not visited[i]:
            g = [i]
            visited[i] = True
            for j in range(i + 1, len(bugs)):
                if not visited[j] and sim[i][j] >= threshold:
                    # ── Intent guard: silently reject false positives ──
                    if _intents_compatible(bugs[i], bugs[j]):
                        g.append(j)
                        visited[j] = True
            groups.append(g)

    unique_indices = [g[0] for g in groups]
    dup_map        = {g[0]: g[1:] for g in groups if len(g) > 1}
    return unique_indices, dup_map, groups


def get_similarity_score(text_a: str, text_b: str, model: SentenceTransformer) -> float:
    emb = embed([text_a, text_b], model)
    return float(np.dot(emb[0], emb[1]))