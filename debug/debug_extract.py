import json
import time
from pathlib import Path

from src.extract import MODEL, extract, make_prompt
from src.ingest import ingest
from src.ocr import ocr_if_needed

LANG = "en"              # "fr" or "en"
FILE = "dossier_005.pdf"  # dossier_004.pdf is a scanned one
DOC_TYPE = "proof_of_address"     # id_card, payslip, proof_of_address, bank_statement
MODEL_NAME = MODEL
SHOW_PROMPT = True
CHECK_ALL = True        # all files and all types of LANG, takes a few minutes

LOAN_DIR = Path("data/loan_files")
GT_DIR = Path("data/ground_truth")

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_file(pdf):
    labels = load_json(pdf.with_suffix(".json"))
    pages = [ocr_if_needed(p) for p in ingest(pdf)]
    return pages, labels

def run_doc(pages, labels, doc_type):
    # true page numbers from the labels, so only extract is tested here
    nums = labels["documents"][doc_type]
    doc_pages = [p for p in pages if p["page_num"] in nums]
    start = time.perf_counter()
    fields = extract(doc_type, doc_pages, LANG, MODEL_NAME)
    seconds = time.perf_counter() - start
    expected = load_json(GT_DIR / f"{labels['person_id']}.json")["documents"][doc_type]
    ok = {name: fields[name] == expected[name] for name in expected}
    return fields, expected, ok, seconds

if CHECK_ALL:
    good, total, llm_time = 0, 0, 0.0
    for pdf in sorted((LOAN_DIR / LANG).glob("*.pdf")):
        pages, labels = load_file(pdf)
        for doc_type in labels["documents"]:
            fields, expected, ok, seconds = run_doc(pages, labels, doc_type)
            good += sum(ok.values())
            total += len(ok)
            llm_time += seconds
            for name, is_ok in ok.items():
                if not is_ok:
                    print(f"  {pdf.name} {doc_type} {name}: got {fields[name]!r} expected {expected[name]!r}")
        print(pdf.name, "done")
    print(f"{LANG}: {good}/{total} fields correct ({good / total:.1%}), llm time {llm_time:.1f} s")
else:
    pages, labels = load_file(LOAN_DIR / LANG / FILE)
    if SHOW_PROMPT:
        nums = labels["documents"][DOC_TYPE]
        text = "\n".join(p["text"] for p in pages if p["page_num"] in nums)
        print(make_prompt(DOC_TYPE, text, LANG))
        print("-" * 40)
    fields, expected, ok, seconds = run_doc(pages, labels, DOC_TYPE)
    for name in expected:
        print(f"{name:15} got {fields[name]!r:30} expected {expected[name]!r:30} {ok[name]}")
    print(f"{sum(ok.values())}/{len(ok)} fields correct in {seconds:.1f} s")