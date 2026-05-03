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
                    g.append(j)
                    visited[j] = True
            groups.append(g)

    unique_indices = [g[0] for g in groups]
    dup_map        = {g[0]: g[1:] for g in groups if len(g) > 1}
    return unique_indices, dup_map, groups


def get_similarity_score(text_a: str, text_b: str, model: SentenceTransformer) -> float:
    emb = embed([text_a, text_b], model)
    return float(np.dot(emb[0], emb[1]))
