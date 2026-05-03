import re
from pypdf import PdfReader


def extract_paragraphs(uploaded_file) -> list[str]:
    reader = PdfReader(uploaded_file)
    paras  = []
    for page in reader.pages:
        raw    = page.extract_text() or ""
        blocks = re.split(r'\n{2,}', raw)
        for b in blocks:
            cleaned = re.sub(r'\s+', ' ', b).strip()
            if len(cleaned) > 40:
                paras.append(cleaned)
    return paras


def split_text_input(raw: str) -> list[str]:
    numbered = re.split(r'(?=Bug\s+\d+\s*[:\-])', raw, flags=re.IGNORECASE)
    if len(numbered) > 1:
        bugs = [p.strip() for p in numbered if len(p.strip()) > 10]
        return bugs

    by_newline = re.split(r'\n+', raw)
    if len(by_newline) > 1:
        bugs = [p.strip() for p in by_newline if len(p.strip()) > 10]
        return bugs

    by_sentence = re.split(r'(?<=[.!?])\s{2,}', raw)
    bugs = [p.strip() for p in by_sentence if len(p.strip()) > 10]
    return bugs if bugs else [raw]


def clean_bug_text(text: str, max_chars: int = 500) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_chars] + ("..." if len(text) > max_chars else "")
