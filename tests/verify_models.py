"""
verify_models.py  (lives in tests/)
Run from project root:   python tests/verify_models.py
Or from tests/ folder:   python verify_models.py

Checks:
  1. huggingface_hub is installed
  2. All expected model files exist locally
  3. If any are missing → downloads them from HuggingFace and re-checks
"""

import os
import sys

# ── Config (must match config.py) ─────────────────────────────────────────────
# This file lives in tests/ — go one level up to reach the project root
BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HF_REPO_ID      = "Varadkulkarni2002/nlp-bug-classifier-models"
MODELS_DIR      = os.path.join(BASE_DIR, "models")

SBERT_PATH      = os.path.join(MODELS_DIR, "best_bugzilla_sbert")
CLASSIFIER_PATH = os.path.join(MODELS_DIR, "classifier", "best_model.pt")
CONFIG_PATH     = os.path.join(MODELS_DIR, "classifier", "run_config.json")

REQUIRED_FILES = [
    os.path.join(SBERT_PATH, "model.safetensors"),
    os.path.join(SBERT_PATH, "config.json"),
    os.path.join(SBERT_PATH, "tokenizer.json"),
    os.path.join(SBERT_PATH, "tokenizer_config.json"),
    CLASSIFIER_PATH,
    CONFIG_PATH,
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def check_files() -> list[str]:
    """Return list of missing file paths."""
    return [f for f in REQUIRED_FILES if not os.path.isfile(f)]


def human_size(path: str) -> str:
    try:
        b = os.path.getsize(path)
        for unit in ["B", "KB", "MB", "GB"]:
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"
    except Exception:
        return "?"


def print_status(label: str, ok: bool, detail: str = ""):
    icon = "✅" if ok else "❌"
    print(f"  {icon}  {label}" + (f"  →  {detail}" if detail else ""))


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 60)
    print("  NLP Bug Classifier — Model Verification")
    print(f"  Repo : {HF_REPO_ID}")
    print(f"  Dir  : {MODELS_DIR}")
    print("=" * 60)

    # 1. Check huggingface_hub
    print("\n[1] Checking huggingface_hub installation…")
    try:
        import huggingface_hub
        print_status(f"huggingface_hub {huggingface_hub.__version__}", True)
    except ImportError:
        print_status("huggingface_hub", False, "not installed")
        print("\n  Run:  pip install huggingface_hub")
        sys.exit(1)

    # 2. Check which files exist before download
    print("\n[2] Checking local model files…")
    missing_before = check_files()
    for f in REQUIRED_FILES:
        exists = os.path.isfile(f)
        rel    = os.path.relpath(f, BASE_DIR)
        size   = human_size(f) if exists else ""
        print_status(rel, exists, size)

    # 3. Download if anything is missing
    if missing_before:
        print(f"\n[3] {len(missing_before)} file(s) missing — downloading from HuggingFace…")
        print(f"    This may take a few minutes on first run.\n")
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=HF_REPO_ID,
                repo_type="model",
                local_dir=MODELS_DIR,
                local_dir_use_symlinks=False,
                ignore_patterns=["minilm/*"],
            )
            print("\n  Download complete. Re-checking files…\n")
        except Exception as e:
            print(f"\n  ❌ Download failed: {e}")
            print("  Possible causes:")
            print("    • No internet connection")
            print("    • Repo is private — run: huggingface-cli login")
            print(f"    • Repo ID is wrong: {HF_REPO_ID}")
            sys.exit(1)

        # Re-check after download
        missing_after = check_files()
        print("[4] Post-download file check…")
        for f in REQUIRED_FILES:
            exists = os.path.isfile(f)
            rel    = os.path.relpath(f, BASE_DIR)
            size   = human_size(f) if exists else ""
            print_status(rel, exists, size)

        if missing_after:
            print(f"\n  ❌ {len(missing_after)} file(s) still missing after download:")
            for f in missing_after:
                print(f"     • {os.path.relpath(f, BASE_DIR)}")
            print("\n  Check that the HuggingFace repo contains these files.")
            sys.exit(1)
    else:
        print("\n  All files already present — no download needed.")

    # 4. Quick load test
    print("\n[5] Quick load test…")
    try:
        sys.path.insert(0, BASE_DIR)  # project root so app imports work
        import torch
        ckpt = torch.load(CLASSIFIER_PATH, map_location="cpu", weights_only=False)
        keys = list(ckpt.keys())
        print_status("Classifier checkpoint loads", True, f"keys: {keys}")
    except Exception as e:
        print_status("Classifier checkpoint loads", False, str(e))

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(SBERT_PATH, device="cpu")
        emb   = model.encode(["test bug"], normalize_embeddings=True)
        print_status("SBERT model loads + encodes", True, f"embedding dim: {emb.shape[1]}")
    except Exception as e:
        print_status("SBERT model loads + encodes", False, str(e))

    print()
    print("=" * 60)
    print("  All checks passed — models are ready ✅")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()