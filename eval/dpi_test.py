import json
import sys
import time
from pathlib import Path

from src.ingest import ingest
from src.ocr import ocr_if_needed

LOAN_DIR = Path("data/loan_files")
TRUTH_DIR = Path("data/ground_truth")
DPIS = [300, 200, 150]
# values that must survive ocr, checked in the raw page text
KEYS = {
    "id_card": ["last_name", "id_number"],
    "payslip": ["last_name"],
    "proof_of_address": ["last_name", "postal_code"],
    "bank_statement": ["last_name", "iban", "postal_code"],
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def found(value, text):
    # spaces removed so "FR41 7940" matches "FR417940"
    return str(value).replace(" ", "") in text.replace(" ", "")


def test_dpi(lang, dpi):
    n_pages = n_values = n_found = 0
    seconds = conf = 0.0
    for pdf in sorted((LOAN_DIR / lang).glob("*.pdf")):
        labels = load_json(pdf.with_suffix(".json"))
        truth = load_json(TRUTH_DIR / f"{labels['person_id']}.json")

        t = time.perf_counter()
        pages = [ocr_if_needed(p) for p in ingest(pdf, dpi)]
        seconds += time.perf_counter() - t

        for page, label in zip(pages, labels["pages"]):
            if not label["scanned"]:
                continue
            n_pages += 1
            conf += page["ocr_conf"]
            values = truth["documents"][label["doc_type"]]
            for key in KEYS.get(label["doc_type"], []):
                n_values += 1
                n_found += found(values[key], page["text"])

    return {"dpi": dpi, "scanned_pages": n_pages,
            "seconds_per_scanned_page": round(seconds / n_pages, 2),
            "mean_conf": round(conf / n_pages, 3),
            "values_found": round(100 * n_found / n_values, 1)}


if __name__ == "__main__":
    # python -m eval.dpi_test fr
    lang = sys.argv[1] if len(sys.argv) > 1 else "fr"
    for dpi in DPIS:
        print(test_dpi(lang, dpi))