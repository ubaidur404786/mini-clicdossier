import json
import time
from pathlib import Path

from src.ingest import ingest
from src.ocr import ocr_if_needed

PDF_PATH = Path("data/loan_files/fr/dossier_004.pdf")
LANG = "fra+eng"
CONFIG = "--psm 3"
DPI = 300
SAVE_TEXT = True
OUT_DIR = Path("outputs/debug_ocr")

labels = json.load(open(PDF_PATH.with_suffix(".json"), encoding="utf-8"))
gt = json.load(open(Path("data/ground_truth") / f"{labels['person_id']}.json", encoding="utf-8"))
pages = ingest(PDF_PATH, dpi=DPI)
print(f"{PDF_PATH.name}: {len(pages)} pages, lang={LANG}, dpi={DPI}, config={CONFIG}")

if SAVE_TEXT:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

total = 0.0
for page, label in zip(pages, labels["pages"]):
    start = time.perf_counter()
    page = ocr_if_needed(page, lang=LANG, config=CONFIG)
    seconds = time.perf_counter() - start
    total += seconds

    # the person's last name must be somewhere in the text
    last_name = gt["documents"][label["doc_type"]]["last_name"]
    found = "name OK" if last_name in page["text"].upper() else "name MISSING"

    print(f"\npage {page['page_num']} | {label['doc_type']} | {page['source']} | "
          f"conf {page['ocr_conf']} | {len(page['text'])} chars | {seconds:.2f} s | {found}")
    print("\n".join(page["text"].splitlines()[:5]))

    if SAVE_TEXT:
        psm = CONFIG.replace("-", "").replace(" ", "")
        out = OUT_DIR / f"{PDF_PATH.stem}_p{page['page_num']}_{LANG.replace('+', '_')}_{DPI}dpi_{psm}.txt"
        out.write_text(page["text"], encoding="utf-8")

print(f"\ntotal ocr {total:.2f} s, {total / len(pages):.2f} s/page")