import json
from datetime import date
from pathlib import Path

from src.checks import completeness, cross_check
from src.report import make_report, save

LANG = "en"
FILE = "dossier_003.pdf"  # None = every file, only prints the status
SECONDS = None            # fake time, the pipeline will measure the real one
FAKE_ERROR = True        # True = add a validation error to the first document

TRUTH_DIR = Path("data/ground_truth")
LOAN_DIR = Path("data/loan_files")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_report(pdf):
    labels = load_json(pdf.with_suffix(".json"))
    truth = load_json(TRUTH_DIR / f"{labels['person_id']}.json")
    results = {t: {"fields": fields, "errors": []} for t, fields in truth["documents"].items()}
    if FAKE_ERROR:
        doc_type = next(iter(results))
        results[doc_type]["errors"].append({"field": "last_name", "problem": "fake error", "value": "<b>RIOU</b>"})
    checks = cross_check(results, date.fromisoformat(truth["file_date"]))
    missing = completeness(labels["documents"])
    report = make_report(pdf, LANG, labels["documents"], results, checks, missing, SECONDS)
    return report, labels


if __name__ == "__main__":
    if FILE:
        report, labels = build_report(LOAN_DIR / LANG / FILE)
        print("scenario:", labels["scenario"])
        print("status:  ", report["status"])
        print("alerts:  ", report["alerts"], "expected", labels["expected"]["alerts"])
        print("missing: ", report["missing"], "expected", labels["expected"]["missing"])
        for path in save(report):
            print("saved", path)
    else:
        counts = {}
        for pdf in sorted((LOAN_DIR / LANG).glob("*.pdf")):
            report, labels = build_report(pdf)
            counts[report["status"]] = counts.get(report["status"], 0) + 1
            print(f"{pdf.name}  {labels['scenario']:17} {report['status']:10} {report['alerts']}")
        print(counts)