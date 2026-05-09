import re
from pypdf import PdfReader


# ══════════════════════════════════════════════════════════════════════════════
#  METADATA / NOISE FILTERS
#  Lines that should NEVER appear in a bug description
# ══════════════════════════════════════════════════════════════════════════════

# Exact or pattern matches for lines to throw away entirely
_NOISE_PATTERNS = [
    r'^-{3,}.*PAGE.*\d+.*-{3,}$',          # --- PAGE 1 ---
    r'^page\s+\d+(\s+of\s+\d+)?$',          # Page 1  /  Page 1 of 3
    r'^-{3,}$',                              # --- separators ---
    r'^\[.*?\]$',                            # [Image]  [Table]  [Figure]
    r'^(figure|table|chart|graph|image|photo|screenshot|diagram|shape|object|video|clip|embed)\s*[\d\:\-]',
    r'^(generated|prepared|created|authored|date|version|rev)\s*[:\-]',
    r'^(confidential|internal|draft|proprietary)\s*$',
    r'^\d+\s*$',                             # lone page numbers
    r'^copyright\s',                         # copyright lines
    r'^www\.|^http',                         # URLs as standalone lines
]
_NOISE_RE = re.compile(
    '|'.join(_NOISE_PATTERNS),
    flags=re.IGNORECASE
)

# Header patterns — these appear at the top of documents
_HEADER_PATTERNS = [
    r'^BUG\s+REPORT',
    r'^TEST\s+REPORT',
    r'^INCIDENT\s+REPORT',
    r'^DEFECT\s+REPORT',
    r'^ISSUE\s+LOG',
    r'^PROBLEM\s+STATEMENT',
]
_HEADER_RE = re.compile('|'.join(_HEADER_PATTERNS), re.IGNORECASE)


def _is_noise(line: str) -> bool:
    """Return True if this line is metadata/noise and should be discarded."""
    s = line.strip()
    if not s:
        return False   # blanks are separators — handled separately

    # ALL CAPS lines longer than 2 words are almost always titles/headers
    words = s.split()
    if s.isupper() and len(words) >= 2:
        return True

    # Student / employee IDs  e.g. MT24AAC007, EMP-2024-001
    if re.match(r'^[A-Z]{1,5}[\-]?\d{2,}[A-Z]{0,5}\d*$', s):
        return True

    # Pure name lines — 2-4 Title Case words, no digits, no punctuation
    if (re.match(r'^[A-Z][a-z]+(?:\s[A-Z][a-z]+){1,3}$', s)
            and not any(c.isdigit() for c in s)
            and len(words) <= 4):
        return True

    # Known noise patterns
    if _NOISE_RE.match(s):
        return True

    # Document header lines
    if _HEADER_RE.match(s):
        return True

    # Very short lines that are clearly labels, not sentences
    # e.g. "Title:", "Author:", "Status:", "Priority:"
    if re.match(r'^[A-Za-z\s]{2,20}:\s*$', s) and len(words) <= 3:
        return True

    return False


# ══════════════════════════════════════════════════════════════════════════════
#  MARKER DETECTION
#  Recognise what kind of list marker starts a line
# ══════════════════════════════════════════════════════════════════════════════

# Numbered:  1)  1.  1:  Bug 1:  Bug #1:  #1.
_NUMBERED_RE = re.compile(
    r'^\s*(?:Bug\s*#?\s*|#\s*)?\d+\s*[\)\.\:\-]\s+\S',
    re.IGNORECASE
)

# Bullets: • ● ◦ ▪ ▸ → ‣ ⁃ - * – —
_BULLET_RE = re.compile(
    r'^\s*[\•\●\◦\▪\▸\→\‣\⁃\–\—\-\*]\s+\S'
)

# Letter-based:  a)  b.  A)
_ALPHA_RE = re.compile(r'^\s*[a-zA-Z]\s*[\)\.\:]\s+\S')


def _marker_type(line: str) -> str | None:
    """Return 'numbered', 'bullet', 'alpha', or None."""
    if _NUMBERED_RE.match(line):
        return 'numbered'
    if _BULLET_RE.match(line):
        return 'bullet'
    if _ALPHA_RE.match(line):
        return 'alpha'
    return None


def _strip_marker(line: str) -> str:
    """Remove leading list marker from a line."""
    s = line.strip()
    # Numbered / Bug N: / #N
    s = re.sub(r'^(?:Bug\s*#?\s*|#\s*)?\d+\s*[\)\.\:\-]\s+', '', s, flags=re.IGNORECASE)
    # Bullet
    s = re.sub(r'^[\•\●\◦\▪\▸\→\‣\⁃\–\—\-\*]\s+', '', s)
    # Alpha
    s = re.sub(r'^[a-zA-Z]\s*[\)\.\:]\s+', '', s)
    return s.strip()


# ══════════════════════════════════════════════════════════════════════════════
#  CORE EXTRACTOR
#  Works for numbered lists, bullet lists, and plain paragraphs
# ══════════════════════════════════════════════════════════════════════════════

def _group_into_bugs(lines: list[str]) -> list[str]:
    """
    Walk lines and group them into individual bug descriptions.

    Strategy (in priority order):
    1. If ANY line has a number/bullet marker → use markers as boundaries
    2. Otherwise → use blank lines as paragraph boundaries
    3. Plain sentences with no structure → treat whole block as one bug
    """
    # Detect which format this document uses
    has_numbered = any(_marker_type(l) == 'numbered' for l in lines)
    has_bullet   = any(_marker_type(l) == 'bullet'   for l in lines)
    has_alpha    = any(_marker_type(l) == 'alpha'     for l in lines)
    use_markers  = has_numbered or has_bullet or has_alpha

    bugs    = []
    current = []   # lines belonging to current bug

    def flush():
        if current:
            text = ' '.join(current)
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) > 15:
                bugs.append(text)
            current.clear()

    if use_markers:
        # ── Marker-based splitting ─────────────────────────────────────────
        for i, line in enumerate(lines):
            stripped = line.strip()
            mtype    = _marker_type(line)

            if not stripped:
                # Blank — peek ahead: if next real line is a new marker → flush
                for j in range(i + 1, len(lines)):
                    nxt = lines[j].strip()
                    if nxt:
                        if _marker_type(lines[j]):
                            flush()
                        break
                # else keep blank — continuation of current bug
                continue

            if mtype:
                # New bug starts
                flush()
                current.append(_strip_marker(line))
            elif current:
                # Continuation line of current bug
                current.append(stripped)
            # Lines before the first marker are noise — ignore
        flush()

    else:
        # ── Paragraph-based splitting (no markers found) ───────────────────
        for line in lines:
            stripped = line.strip()
            if not stripped:
                flush()
            else:
                current.append(stripped)
        flush()

    return bugs


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def extract_paragraphs(uploaded_file) -> list[str]:
    reader    = PdfReader(uploaded_file)
    all_lines = []
    for page in reader.pages:
        text = page.extract_text() or ""
        all_lines.extend(text.split('\n'))
    all_lines.append('')  # sentinel blank at end

    # Step 1: Remove noise lines (keep blanks as separators)
    clean_lines = [l for l in all_lines if not _is_noise(l)]

    # Step 2: Group into bugs
    bugs = _group_into_bugs(clean_lines)
    if bugs:
        return bugs

    # Step 3: Fallback — join everything and sentence-split
    full_text = ' '.join(l.strip() for l in clean_lines if l.strip())
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    by_sentence = re.split(r'(?<=[.!?])\s+', full_text)
    paras = [p.strip() for p in by_sentence if len(p.strip()) > 15]
    return paras if paras else [full_text]


def split_text_input(raw: str) -> list[str]:
    """Same pipeline for manually typed / pasted text."""
    lines = raw.split('\n')
    lines.append('')  # sentinel

    # Remove noise
    clean_lines = [l for l in lines if not _is_noise(l)]

    bugs = _group_into_bugs(clean_lines)
    if bugs:
        return bugs

    # Fallback: sentence split
    full_text   = ' '.join(l.strip() for l in clean_lines if l.strip())
    by_sentence = re.split(r'(?<=[.!?])\s{1,}', full_text)
    bugs = [p.strip() for p in by_sentence if len(p.strip()) > 10]
    return bugs if bugs else [raw]


def clean_bug_text(text: str, max_chars: int = 500) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_chars] + ("..." if len(text) > max_chars else "")