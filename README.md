# 🐛 NLP Bug Classifier

> **Paste bug reports. Get instant triage.**
> An AI-powered Streamlit app that reads raw bug descriptions (or a PDF report), removes duplicates, classifies every bug by type, severity and estimated fix time, and generates root-cause solutions — all in one pipeline.

---

## What It Does

Most teams drown in bug reports. The same crash gets filed ten times, critical issues get buried next to cosmetic glitches, and nobody has time to read every ticket carefully.

This app solves that in three steps:

**1 — Deduplication**
It uses a fine-tuned SBERT (Sentence-BERT) model trained on Bugzilla data to embed every bug description and find semantically similar ones. An intent-fingerprinting guard prevents false positives — `"DB crashed"` and `"close button hangs"` will never be merged even if their embeddings are close.

**2 — Classification**
A custom multi-task BERT model (fine-tuned on `bert-base-uncased`) classifies each unique bug across three axes simultaneously:
- **Bug Type** — Crash / Freeze / Memory / UI-Visual / Other
- **Severity** — Critical / Major / Minor
- **Fix Time** — Fast / Medium / Slow

Temperature scaling and a keyword-safety-net keep low-confidence predictions honest instead of confidently wrong.

**3 — AI Solutions**
For each classified bug, the app queries **Groq's Llama-3.3-70B** to produce a root cause analysis, a recommended fix, and a code snippet — all formatted inline in the canvas panel.

Results can be exported as **PDF**, **CSV**, or **XLSX** and every session is saved locally so you can come back to it from the sidebar.

---

## Architecture

```
run.py                  ← Streamlit entry point (multi-analysis session)
app/
  helpers/
    config.py           ← Paths, thresholds, auto-downloads models from HuggingFace
    classifier.py       ← Multi-task BERT: bug type + severity + fix time
    sbert.py            ← SBERT deduplication + intent fingerprinting
    pdf_parser.py       ← PDF extraction + bug block splitting
    pdf_report.py       ← ReportLab PDF report builder
    solution_agent.py   ← Groq / Llama-3.3-70B solution generator
    exporter.py         ← CSV / XLSX / JSON export
    chat_history.py     ← Per-session JSON storage
    trend_analysis.py   ← Analytics aggregation
  ui/
    components.py       ← All Streamlit UI: bubbles, canvas, analytics, sidebar
models/                 ← Auto-downloaded from HuggingFace on first run
  best_bugzilla_sbert/  ← Fine-tuned SBERT
  classifier/           ← Multi-task BERT checkpoint + label config
sessions/               ← Local session storage (gitignored)
```

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10 or 3.11 |
| pip | latest |
| Git | any recent |
| Internet | needed on first run (model download ~500 MB) |
| Groq API key | free at [console.groq.com](https://console.groq.com) |

> **GPU optional.** The app runs on CPU. A CUDA GPU will make classification faster but is not required.

---

## Setup — Windows

```bat
:: 1. Clone the repo
git clone https://github.com/Varadkulkarni2002/NLP-Bug-Classifier.git
cd NLP-Bug-Classifier

:: 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate

:: 3. Install dependencies
pip install -r requirements.txt

:: 4. Create your .env file with your Groq API key
echo GROQ_API_KEY=your_groq_key_here > .env

:: 5. (Optional) Verify models download correctly
python verify_models.py

:: 6. Run the app
streamlit run run.py
```

---

## Setup — macOS / Linux

```bash
# 1. Clone the repo
git clone https://github.com/Varadkulkarni2002/NLP-Bug-Classifier.git
cd NLP-Bug-Classifier

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file with your Groq API key
echo "GROQ_API_KEY=your_groq_key_here" > .env

# 5. (Optional) Verify models download correctly
python verify_models.py

# 6. Run the app
streamlit run run.py
```

---

## Getting a Groq API Key (Free)

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up for a free account
3. Click **API Keys → Create API Key**
4. Copy the key and paste it into your `.env` file:

```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

> The free Groq tier is enough for this app. Solutions use Llama-3.3-70B-Versatile.

---

## How Models Are Downloaded

You do **not** need to download models manually. On the very first run, `config.py` automatically pulls the models from HuggingFace:

**Repo:** [`Varadkulkarni2002/nlp-bug-classifier-models`](https://huggingface.co/Varadkulkarni2002/nlp-bug-classifier-models)

What gets downloaded into `models/`:
```
models/
  best_bugzilla_sbert/       ← Fine-tuned SBERT (Bugzilla corpus)
    model.safetensors
    config.json
    tokenizer.json
    tokenizer_config.json
  classifier/
    best_model.pt             ← Multi-task BERT checkpoint
    run_config.json           ← Label maps for bug type / severity / fix time
```

The download happens silently in the background when you first `streamlit run run.py`. It takes 1–3 minutes depending on your connection. After that, models are cached locally and never re-downloaded.

To verify manually at any time:
```bash
python verify_models.py
```

---

## Usage

Once the app is running, open your browser to `http://localhost:8501`

**Option A — Paste bugs directly**
Type or paste bug descriptions into the input bar at the bottom. You can paste multiple bugs separated by `Bug 1:`, `Bug 2:` labels or just double newlines.

**Option B — Upload a PDF**
Click the **＋** button and upload a PDF bug report. The parser auto-detects `Bug #N` blocks, extracts quoted descriptions, and falls back to paragraph splitting for general PDFs.

**Canvas panel (right side)**
After analysis, a slide-out canvas shows all classified bugs with export buttons. Click **💡 Get AI Solutions for All Bugs** to generate Groq solutions for every bug. Solutions are saved into the session and shown automatically if you reload from the sidebar.

**Exports**
- **PDF** — full triage report with AI solutions embedded (if generated)
- **CSV** — flat table, one row per unique bug
- **XLSX** — same as CSV but colour-coded by severity

---

## Project Structure

```
NLP-Bug-Classifier/
├── run.py                    ← Entry point — run this
├── verify_models.py          ← Model download checker
├── requirements.txt
├── .env                      ← Your Groq key (never commit this)
├── .gitignore
├── .streamlit/
│   └── config.toml           ← Theme settings
├── app/
│   ├── helpers/
│   │   ├── config.py
│   │   ├── classifier.py
│   │   ├── sbert.py
│   │   ├── pdf_parser.py
│   │   ├── pdf_report.py
│   │   ├── solution_agent.py
│   │   ├── exporter.py
│   │   ├── chat_history.py
│   │   ├── trend_analysis.py
│   │   └── .bug_keywords.json
│   └── ui/
│       └── components.py
├── models/                   ← Auto-created on first run
├── sessions/                 ← Auto-created, gitignored
├── data/                     ← Training data (CSV)
└── metrics/                  ← Model evaluation results
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'groq'`**
```bash
pip install groq
```

**`GROQ_API_KEY not found`**
Make sure your `.env` file is in the project root (same folder as `run.py`) and contains:
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

**Models not downloading**
```bash
pip install huggingface_hub
python verify_models.py
```
If the repo is private, authenticate first:
```bash
huggingface-cli login
```

**App is slow on first load**
Normal — BERT and SBERT are being loaded into memory for the first time. Streamlit caches them after that, so subsequent runs in the same session are fast.

**`KeyError: 'timestamp'` or `KeyError: 'total'`**
You have an old `components.py`. Replace it with the latest version from the repo — this was fixed in the session index schema.

**Port already in use**
```bash
streamlit run run.py --server.port 8502
```

---

## CI/CD

The repo includes a GitHub Actions pipeline (`.github/workflows/ci.yml`) that runs on every push to `main` or `dev`:

1. **Lint & Import Check** — compiles every Python file, verifies model and data files exist after LFS pull
2. **Smoke Tests** — runs unit tests for config, pdf_parser, trend_analysis, exporter, chat_history, and SBERT similarity matrix
3. **Deploy Check** (main branch only) — starts Streamlit headlessly and hits the health endpoint

---

## Built With

| Component | Technology |
|-----------|-----------|
| UI | Streamlit |
| Classifier | Fine-tuned `bert-base-uncased` (multi-task) |
| Deduplication | Fine-tuned SBERT on Bugzilla corpus |
| AI Solutions | Groq — Llama-3.3-70B-Versatile |
| PDF parsing | pypdf + ReportLab |
| Model hosting | HuggingFace Hub |
| Export | openpyxl (XLSX), csv, reportlab (PDF) |

---

## Author

**Varad Kulkarni** — NLP Bug Classifier v0.2.0
