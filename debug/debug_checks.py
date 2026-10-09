import json
from datetime import date
from pathlib import Path

from src.checks import completeness, cross_check
from src.extract import extract
from src.ingest import ingest
from src.ocr import ocr_if_needed
from src.validate import validate

MODE = "truth"     # "truth" (fast, perfect fields) or "extract" (ocr + llm, slow)
LANG = "fr"
FILE = None        # e.g. "dossier_001.pdf", None = every file
VERBOSE = False    # True = print every check, not only the wrong ones

TRUTH_DIR = Path("data/ground_truth")
LOAN_DIR = Path("data/loan_files")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def truth_results(truth):
    # same shape as validate() output
    return {doc_type: {"fields": fields, "errors": []} for doc_type, fields in truth["documents"].items()}


def extract_results(pdf, labels):
    pages = [ocr_if_needed(p) for p in ingest(pdf)]
    results = {}
    for doc_type, nums in labels["documents"].items():
        doc_pages = [p for p in pages if p["page_num"] in nums]
        results[doc_type] = validate(doc_type, extract(doc_type, doc_pages, LANG))
    return results


def main():
    files = [FILE] if FILE else [p.name for p in sorted((LOAN_DIR / LANG).glob("*.pdf"))]
    counts = {"caught": 0, "false alarm": 0, "missed": 0, "unknown": 0}
    missing_ok = 0
    for name in files:
        pdf = LOAN_DIR / LANG / name
        labels = load_json(pdf.with_suffix(".json"))
        truth = load_json(TRUTH_DIR / f"{labels['person_id']}.json")
        expected = labels["expected"]

        results = truth_results(truth) if MODE == "truth" else extract_results(pdf, labels)
        checks = cross_check(results, date.fromisoformat(truth["file_date"]))
        missing = completeness(labels["documents"])

        if missing == expected["missing"]:
            missing_ok += 1
        else:
            print(f"MISSING WRONG {name}: got {missing}, expected {expected['missing']}")

        for check in checks:
            wanted = check["check"] in expected["alerts"]
            got = check["status"] == "ALERT"
            if check["status"] == "UNKNOWN":
                counts["unknown"] += 1
            result = None
            if wanted and got:
                result = "caught"
            elif got:
                result = "false alarm"
            elif wanted:
                result = "missed"
            if result:
                counts[result] += 1
            if VERBOSE or result in ("false alarm", "missed"):
                print(f"{name} {labels['scenario']:16} {check['check']:24} {check['status']:7} {result or ''} | {check['detail']}")

    print(f"\n{LANG} {MODE}: completeness {missing_ok}/{len(files)} right")
    print(f"alerts: caught {counts['caught']}, false alarms {counts['false alarm']}, "
          f"missed {counts['missed']}, unknown checks {counts['unknown']}")


if __name__ == "__main__":
    main()