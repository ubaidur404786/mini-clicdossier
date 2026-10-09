from datetime import date

from eval.evaluate import LOAN_DIR, TRUTH_DIR, alert_rows, classify_rows, field_rows, load_json
from src.classify import load_model
from src.pipeline import run

LANG = "fr"
FILE = "dossier_001.pdf"
BREAK = ("payslip", "net_salary", 9999.0)   # None = no change, else put a wrong value in the report

if __name__ == "__main__":
    pdf = LOAN_DIR / LANG / FILE
    labels = load_json(pdf.with_suffix(".json"))
    truth = load_json(TRUTH_DIR / f"{labels['person_id']}.json")
    report = run(pdf, LANG, date.fromisoformat(truth["file_date"]))
    if BREAK:
        doc_type, name, value = BREAK
        report["documents"][doc_type]["fields"][name] = value

    print("scenario", labels["scenario"])
    for row in classify_rows(pdf, labels, load_model()):
        print(row)
    for row in field_rows(report, truth, labels):
        mark = "ok " if row["ok"] else "BAD"
        print(f"{mark} {row['field']:32} want {row['want']!r} got {row['got']!r}")
    for row in alert_rows(report, labels["expected"]):
        print(row)