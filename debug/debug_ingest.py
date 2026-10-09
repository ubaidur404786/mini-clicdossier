import json
import time
from pathlib import Path

from src.ingest import ingest

# parameters to change
PDF_PATH = Path("data/loan_files/fr/dossier_001.pdf")
DPI = 300
SAVE_IMAGES = True
OUT_DIR = Path("outputs/debug_ingest")

start = time.perf_counter()
pages = ingest(PDF_PATH, dpi=DPI)
seconds = time.perf_counter() - start
print(f"{PDF_PATH.name}: {len(pages)} pages in {seconds:.2f} s ({seconds / len(pages):.2f} s/page)")

# compare with the labels from step 1e
labels = json.loads(PDF_PATH.with_suffix(".json").read_text(encoding="utf-8"))

OUT_DIR.mkdir(parents=True, exist_ok=True)
for page, label in zip(pages, labels["pages"]):
    first_line = page["text"].strip().split("\n")[0] if page["text"].strip() else "(no text)"
    size = page["image"].size if page["image"] else None
    expected = "ocr" if label["scanned"] else "pdf_text"
    ok = "OK" if page["source"] == expected else "WRONG"
    print(f"page {page['page_num']}: {page['source']:8} {ok:5} true type={label['doc_type']:16} "
          f"image={size} | {first_line[:50]}")
    if SAVE_IMAGES and page["image"]:
        page["image"].save(OUT_DIR / f"{PDF_PATH.stem}_p{page['page_num']}_{DPI}dpi.png")

print("keys:", list(pages[0].keys()))