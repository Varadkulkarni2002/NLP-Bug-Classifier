import os
import json
import torch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Model paths ───────────────────────────────────────────────────────────────
SBERT_PATH      = os.path.join(BASE_DIR, "models", "best_bugzilla_sbert")
CLASSIFIER_PATH = os.path.join(BASE_DIR, "models", "classifier", "best_model.pt")
CONFIG_PATH     = os.path.join(BASE_DIR, "models", "classifier", "run_config.json")
METRICS_PATH    = os.path.join(BASE_DIR, "metrics", "test_metrics.json")
HISTORY_PATH    = os.path.join(BASE_DIR, "metrics", "training_history.json")

DATA_CLASSIFIER_TRAIN = os.path.join(BASE_DIR, "data", "classifier", "train_clean.csv")
DATA_CLASSIFIER_VAL   = os.path.join(BASE_DIR, "data", "classifier", "val_final.csv")
DATA_CLASSIFIER_TEST  = os.path.join(BASE_DIR, "data", "classifier", "test_final.csv")
DATA_SBERT_TRAIN      = os.path.join(BASE_DIR, "data", "sbert", "sbert_train.csv")
DATA_SBERT_VAL        = os.path.join(BASE_DIR, "data", "sbert", "sbert_val.csv")
DATA_SBERT_TEST       = os.path.join(BASE_DIR, "data", "sbert", "sbert_test.csv")

CHAT_HISTORY_PATH = os.path.join(BASE_DIR, "app", "chat_sessions.json")

# ── Auto-download models from HuggingFace if not present locally ──────────────
HF_REPO_ID = "Varadkulkarni2002/nlp-bug-classifier-models"

def _ensure_models():
    needs_download = (
        not os.path.isdir(SBERT_PATH)
        or not os.path.isfile(CLASSIFIER_PATH)
        or not os.path.isfile(CONFIG_PATH)
    )
    if needs_download:
        try:
            from huggingface_hub import snapshot_download
            print(f"[config] Downloading models from HuggingFace: {HF_REPO_ID}")
            snapshot_download(
                repo_id=HF_REPO_ID,
                repo_type="model",
                local_dir=os.path.join(BASE_DIR, "models"),
                local_dir_use_symlinks=False,
                ignore_patterns=["minilm/*"],  # ← skip unused MiniLM
            )
            print("[config] Models downloaded successfully.")
        except ImportError:
            raise RuntimeError("huggingface_hub not installed. Run: pip install huggingface_hub")
        except Exception as e:
            print(f"[config] Warning: Could not download models — {e}")

_ensure_models()

# ── Runtime settings ──────────────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

TEMPERATURE      = 0.6
CONF_THRESHOLD   = 0.60
DEDUP_THRESHOLD  = 0.86
MAX_TOKEN_LENGTH = 256


def _load_labels():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        label_map = cfg.get("label_map", cfg.get("label_maps", cfg))
        bug_map   = label_map.get("Bug_Type", {})
        sev_map   = label_map.get("Severity", {})
        fix_map   = label_map.get("Fixing_time", {})
        bug_labels = [k for k, _ in sorted(bug_map.items(), key=lambda x: x[1])]
        sev_labels = [k.lower() for k, _ in sorted(sev_map.items(), key=lambda x: x[1])]
        fix_labels = [k.lower() for k, _ in sorted(fix_map.items(), key=lambda x: x[1])]
        return bug_labels, sev_labels, fix_labels
    return (
        ["Crash", "Freeze", "Memory", "Other", "UI/Visual"],
        ["critical", "major", "minor"],
        ["fast", "medium", "slow"],
    )


BUG_TYPE_LABELS, SEVERITY_LABELS, FIX_TIME_LABELS = _load_labels()

SEVERITY_COLORS = {
    "critical":  "#f87171",
    "major":     "#fb923c",
    "minor":     "#34d399",
    "uncertain": "#7878a8",
}

APP_TITLE    = "NLP Bug Classifier"
APP_VERSION  = "0.2.0"
APP_ICON     = "🐛"

