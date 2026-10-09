import json
import random
from pathlib import Path

import pymupdf

from src.generate.scan_effects import has_text

GT_DIR = Path("data/ground_truth")
GEN_DIR = Path("data/generated")
OUT_DIR = Path("data/loan_files")
LANGS = ["fr", "en"]
SEED = 17


def load_people():
    people = []
    for path in sorted(GT_DIR.glob("p*.json")):
        with open(path, encoding="utf-8") as f:
            people.append(json.load(f))
    return people


def file_name(person):
    # p001 -> dossier_001
    return "dossier_" + person["person_id"][1:]


def make_loan_file(person, doc_order, lang, out_dir=OUT_DIR):
    out = pymupdf.open()
    pages = []
    documents = {}

    for doc_type in doc_order:
        src_path = GEN_DIR / lang / f"{person['person_id']}_{doc_type}.pdf"
        scanned = not has_text(src_path)
        with pymupdf.open(src_path) as src:
            first = out.page_count + 1
            out.insert_pdf(src)
            page_nums = list(range(first, out.page_count + 1))
        for n in page_nums:
            pages.append({"page_num": n, "doc_type": doc_type, "scanned": scanned})
        documents[doc_type] = page_nums

    lang_dir = out_dir / lang
    lang_dir.mkdir(parents=True, exist_ok=True)
    name = file_name(person)
    pdf_path = lang_dir / f"{name}.pdf"
    out.save(pdf_path)
    out.close()

    labels = {
        "file": pdf_path.name,
        "person_id": person["person_id"],
        "lang": lang,
        "scenario": person["scenario"],
        "pages": pages,
        "documents": documents,
        "expected": person["expected"],
    }
    with open(lang_dir / f"{name}.json", "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)
    return pdf_path


if __name__ == "__main__":
    rng = random.Random(SEED)
    for person in load_people():
        # missing docs are not in the ground truth, so they are skipped here
        doc_order = list(person["documents"])
        rng.shuffle(doc_order)
        # same order for fr and en, so both languages get the same test
        for lang in LANGS:
            path = make_loan_file(person, doc_order, lang)
            print("saved", path, doc_order)