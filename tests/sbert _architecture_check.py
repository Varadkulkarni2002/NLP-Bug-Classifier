import os
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SBERT_PATH = os.path.join(BASE_DIR, "best_bugzilla_sbert")

print("=" * 60)
print(f"Loading SBERT from: {SBERT_PATH}")
print("=" * 60)

model = SentenceTransformer(SBERT_PATH)
print(f"Model loaded: {model}")
print(f"Max sequence length: {model.max_seq_length}")

bugs = [
    "Bug 1: The submit button on the login page is cut off and overlaps with the footer at the bottom of the screen.",
    "Bug 2: The application instantly closes out to the desktop without any error message when trying to upload a profile picture.",
    "Bug 3: If I leave the software idle for 10 minutes, the whole application locks up and stops responding to mouse clicks.",
    "Bug 4: Login page submit button is hidden behind the footer border, making it impossible to click.",
    "Bug 5: RAM usage climbs steadily to 4GB if I keep the main dashboard tab open all day.",
    "Bug 6: There is a typo in the main settings menu. It says 'Prefrences' instead of 'Preferences'.",
    "Bug 7: Fatal exception thrown in the backend database when exporting a PDF, causing the server to forcibly restart.",
    "Bug 8: Software hangs completely and freezes on screen after being inactive for a while.",
    "Bug 9: When dark mode is enabled, the paragraph text remains black on a dark grey background, making it completely unreadable.",
    "Bug 10: The dashboard tab leaks memory constantly over time until the browser eventually runs out of RAM.",
]

print(f"\nEncoding {len(bugs)} bugs...")
embeddings = model.encode(bugs, normalize_embeddings=True, show_progress_bar=True)
sim = np.dot(embeddings, embeddings.T)

print("\n--- PAIRWISE SIMILARITY MATRIX ---")
print(f"{'':8}", end="")
for i in range(len(bugs)):
    print(f"  B{i+1:02d} ", end="")
print()

for i in range(len(bugs)):
    print(f"Bug {i+1:2d}: ", end="")
    for j in range(len(bugs)):
        val = sim[i][j]
        if i == j:
            print(f"  --- ", end="")
        elif val >= 0.85:
            print(f" [{val:.2f}]", end="")
        else:
            print(f"  {val:.2f} ", end="")
    print()

print("\n--- EXPECTED DUPLICATES (similarity >= 0.85) ---")
found_any = False
for i in range(len(bugs)):
    for j in range(i+1, len(bugs)):
        if sim[i][j] >= 0.85:
            print(f"  Bug {i+1} <-> Bug {j+1}  similarity={sim[i][j]:.4f}")
            print(f"    A: {bugs[i][:80]}")
            print(f"    B: {bugs[j][:80]}")
            found_any = True

if not found_any:
    print("  No pairs found at 0.85 threshold.")

print("\n--- CLOSEST PAIRS (top 5 by similarity, excluding self) ---")
pairs = []
for i in range(len(bugs)):
    for j in range(i+1, len(bugs)):
        pairs.append((sim[i][j], i, j))
pairs.sort(reverse=True)
for val, i, j in pairs[:5]:
    dup = " *** DUPLICATE" if val >= 0.85 else ""
    print(f"  Bug {i+1} <-> Bug {j+1}  sim={val:.4f}{dup}")

print("\n--- EXPECTED PAIRS ---")
print("  Bug 1 <-> Bug 4  (submit button / footer overlap)")
print("  Bug 3 <-> Bug 8  (freeze / hangs)")
print("  Bug 5 <-> Bug 10 (RAM / memory leak)")

print("\n--- THRESHOLD ANALYSIS ---")
for threshold in [0.75, 0.80, 0.82, 0.85, 0.88, 0.90]:
    pairs_at = [(i+1, j+1) for i in range(len(bugs)) for j in range(i+1, len(bugs)) if sim[i][j] >= threshold]
    print(f"  threshold={threshold:.2f} -> {len(pairs_at)} pairs found: {pairs_at}")