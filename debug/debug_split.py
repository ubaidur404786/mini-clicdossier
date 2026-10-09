import json
from pathlib import Path

from src.classify import classify, load_model
from src.ingest import ingest
from src.ocr import ocr_if_needed
from src.split import split

LANG = "fr"
FILE = "dossier_002.pdf"   # one file printed in detail
CHECK_ALL = True           # compare split with the labels for every file
USE_ML = True              # False = rules classifier
BLANK_PAGE = None          # page_num to empty, to see an "unknown" page

LOAN_DIR = Path("data/loan_files")

def run_file(pdf, model):
    pages = [ocr_if_needed(p) for p in ingest(pdf)]
    for page in pages:
        if page["page_num"] == BLANK_PAGE:
            page["text"] = ""
    pages = [classify(p, model) for p in pages]
    return pages, split(pages)

def load_labels(pdf):
    with open(pdf.with_suffix(".json"), encoding="utf-8") as f:
        return json.load(f)

model = load_model() if USE_ML else None

pdf = LOAN_DIR / LANG / FILE
pages, docs = run_file(pdf, model)
for page in pages:
    print(page["page_num"], page["source"], page["doc_type"], page["type_conf"])
print("split   :", docs)
print("expected:", load_labels(pdf)["documents"])
print("same:", docs == load_labels(pdf)["documents"])

if CHECK_ALL:
    ok = 0
    pdfs = sorted((LOAN_DIR / LANG).glob("*.pdf"))
    for pdf in pdfs:
        _, docs = run_file(pdf, model)
        expected = load_labels(pdf)["documents"]
        if docs == expected:
            ok += 1
        else:
            print("diff", pdf.name, docs, expected)
    print(f"{LANG}: {ok}/{len(pdfs)} files split correctly")