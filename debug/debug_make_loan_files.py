import json
import random
from pathlib import Path

import pymupdf

from src.generate.make_loan_files import load_people, make_loan_file

PERSON_ID = "p004"   # scanned person. try p001 (address_mismatch) and a missing_doc person
LANG = "fr"
SEED = 17
OUT_DIR = Path("outputs/debug_loan_files")

people = {p["person_id"]: p for p in load_people()}
person = people[PERSON_ID]
print("scenario:", person["scenario"])
print("docs in ground truth:", list(person["documents"]))
print("expected:", person["expected"])

doc_order = list(person["documents"])
random.Random(SEED).shuffle(doc_order)
print("doc order:", doc_order)

pdf_path = make_loan_file(person, doc_order, LANG, out_dir=OUT_DIR)
with open(pdf_path.with_suffix(".json"), encoding="utf-8") as f:
    labels = json.load(f)
print("documents:", labels["documents"])

with pymupdf.open(pdf_path) as doc:
    print("pages in pdf:", doc.page_count, "| pages in labels:", len(labels["pages"]))
    for page, label in zip(doc, labels["pages"]):
        text = page.get_text().strip()
        first_line = text.splitlines()[0] if text else "(no text, scanned)"
        print(label["page_num"], label["doc_type"], label["scanned"], "|", first_line)