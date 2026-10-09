import json
from collections import Counter
from datetime import date
from pathlib import Path

from src.classify import load_model
from src.pipeline import run
from src.report import save

LANG = "en"
FILE = None   # None = every file (slow, a few minutes)
USE_ML = True             # True = tfidf model instead of rules
USE_FILE_DATE = False       # False = today as reference date
SAVE = True

LOAN_DIR = Path("data/loan_files")
TRUTH_DIR = Path("data/ground_truth")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def expected_status(expected):
    if expected["missing"]:
        return "INCOMPLETE"
    if expected["alerts"]:
        return "ALERT"
    return "OK"


def show_details(report, labels):
    print("pages  got ", {t: d["pages"] for t, d in report["documents"].items()})
    print("pages  want", labels["documents"])
    for c in report["checks"]:
        print(f"  {c['status']:8} {c['check']:25} {c['detail']}")
    for doc_type, doc in report["documents"].items():
        for err in doc["errors"]:
            print(f"  ERROR {doc_type}.{err['field']}: {err['problem']} (got {err['value']!r})")
    print("step seconds", report["step_seconds"])


if __name__ == "__main__":
    model = load_model() if USE_ML else None
    files = [LOAN_DIR / LANG / FILE] if FILE else sorted((LOAN_DIR / LANG).glob("*.pdf"))
    matched = n_pages = 0
    seconds = 0.0
    statuses = Counter()
    for pdf in files:
        labels = load_json(pdf.with_suffix(".json"))
        truth = load_json(TRUTH_DIR / f"{labels['person_id']}.json")
        ref_date = date.fromisoformat(truth["file_date"]) if USE_FILE_DATE else None

        report = run(pdf, LANG, ref_date, model)
        if SAVE:
            save(report)

        expected = labels["expected"]
        want = expected_status(expected)
        ok = (report["status"] == want
              and sorted(report["alerts"]) == sorted(expected["alerts"])
              and sorted(report["missing"]) == sorted(expected["missing"]))
        matched += ok
        n_pages += len(labels["pages"])
        seconds += report["seconds"]
        statuses[report["status"]] += 1

        mark = "ok  " if ok else "DIFF"
        print(f"{mark} {pdf.name} {labels['scenario']:17} got {report['status']:10} want {want:10} "
              f"alerts {report['alerts']} {report['seconds']:.1f} s")
        if FILE or not ok:
            show_details(report, labels)

    print(f"\n{LANG}: {matched}/{len(files)} files match, {dict(statuses)}")
    print(f"{seconds:.1f} s for {n_pages} pages = {seconds / n_pages:.2f} s/page")