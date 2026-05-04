import re
from pypdf import PdfReader


def extract_paragraphs(uploaded_file) -> list[str]:
    reader = PdfReader(uploaded_file)
    full_text = ""
    for page in reader.pages:
        full_text += (page.extract_text() or "") + "\n\n"

    # 1. Check for explicit numbered bugs (Bug 1:, Bug 2:)
    numbered = re.split(r'(?=Bug\s+\d+\s*[:\-])', full_text, flags=re.IGNORECASE)
    if len(numbered) > 1:
        return [re.sub(r'\s+', ' ', p).strip() for p in numbered if len(p.strip()) > 10]

    # 2. Reconstruct paragraphs by removing single newlines (which break sentences in PDFs)
    clean_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', full_text)

    # 3. Split by actual paragraph breaks (double newlines)
    blocks = re.split(r'\n{2,}', clean_text)
    paras = []
    for b in blocks:
        cleaned = re.sub(r'\s+', ' ', b).strip()
        if len(cleaned) > 20:
            paras.append(cleaned)

    # 4. If it's still just one massive block, split by sentences
    if len(paras) <= 1 and len(full_text) > 50:
        by_sentence = re.split(r'(?<=[.!?])\s{1,}', clean_text)
        paras = [p.strip() for p in by_sentence if len(p.strip()) > 15]

    return paras if paras else [full_text.strip()]


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