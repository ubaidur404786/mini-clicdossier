import json
from pathlib import Path

import pymupdf

from src.generate.make_docs import GT_DIR, draw_doc, format_value

PERSON_ID = "p001"
LANG = "fr"            # "fr" or "en"
DOC_TYPE = "payslip"   # id_card, payslip, proof_of_address, bank_statement
OUT_PATH = Path("outputs/debug_doc.pdf")

with open(GT_DIR / f"{PERSON_ID}.json", encoding="utf-8") as f:
    person = json.load(f)

print("scenario:", person["scenario"])
print("documents:", list(person["documents"]))

if DOC_TYPE not in person["documents"]:
    print(f"{DOC_TYPE} is missing for {PERSON_ID} (missing_doc scenario)")
else:
    fields = person["documents"][DOC_TYPE]
    print("\nvalue in json -> value printed")
    for field, value in fields.items():
        print(f"  {field}: {value!r} -> {format_value(field, value, LANG)!r}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    draw_doc(OUT_PATH, DOC_TYPE, fields, LANG)

    doc = pymupdf.open(OUT_PATH)
    print(f"\npages: {len(doc)}")
    print("text read back from the pdf:")
    print(doc[0].get_text())
    doc.close()
    print("open it to look:", OUT_PATH)