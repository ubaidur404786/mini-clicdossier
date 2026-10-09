import json
from pathlib import Path

from src.extract import extract
from src.ingest import ingest
from src.ocr import ocr_if_needed
from src.validate import validate

MODE = "extract"            # "truth", "examples" or "extract"
LANG = "en"
FILE = None  # extract mode, None = every file (slow, about 200 s)

TRUTH_DIR = Path("data/ground_truth")
LOAN_DIR = Path("data/loan_files")

EXAMPLES = [
    ("bank_statement", {"last_name": "riou", "first_name": "Frédéric", "address_line": "chemin de Moulin",
                        "postal_code": "28242", "city": "Saint Jeannenec",
                        "iban": "FR4179402654235116155940781", "statement_date": "2026-08-31",
                        "salary_credit": 2046.17}),
    ("bank_statement", {"last_name": "RIOU", "first_name": "Frédéric", "address_line": "chemin de Moulin",
                        "postal_code": "2824", "city": "Saint Jeannenec",
                        "iban": "FR41794O2654235116155940781", "statement_date": "31/08/2026",
                        "salary_credit": 204617.0}),
    ("payslip", {"last_name": "RIOU", "first_name": "", "employer": "Martinez SA",
                 "pay_period": "2026-13", "gross_salary": "2 623,30 €", "net_salary": None}),
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def show(doc_type, fields):
    result = validate(doc_type, fields)
    print(f"\n{doc_type}")
    for name, value in fields.items():
        print(f"  {name:15} {str(value):30} -> {result['fields'][name]}")
    for err in result["errors"]:
        print(f"  ERROR {err['field']}: {err['problem']} (got {err['value']!r})")


def check_truth():
    total = bad = 0
    for path in sorted(TRUTH_DIR.glob("*.json")):
        for doc_type, fields in load_json(path)["documents"].items():
            total += 1
            result = validate(doc_type, fields)
            if result["errors"] or result["fields"] != fields:
                bad += 1
                print(path.name, doc_type, result["errors"])
    print(f"{total - bad}/{total} true documents pass unchanged")


def check_extract():
    files = [FILE] if FILE else [p.name for p in sorted((LOAN_DIR / LANG).glob("*.pdf"))]
    caught = false_alarm = missed = 0
    for name in files:
        pdf = LOAN_DIR / LANG / name
        labels = load_json(pdf.with_suffix(".json"))
        truth = load_json(TRUTH_DIR / f"{labels['person_id']}.json")
        pages = [ocr_if_needed(p) for p in ingest(pdf)]
        for doc_type, nums in labels["documents"].items():
            doc_pages = [p for p in pages if p["page_num"] in nums]
            result = validate(doc_type, extract(doc_type, doc_pages, LANG))
            true_fields = truth["documents"][doc_type]
            error_fields = set()
            for err in result["errors"]:
                field = err["field"]
                error_fields.add(field)
                if err["value"] == true_fields[field]:
                    false_alarm += 1
                    print(f"FALSE ALARM {name}_{doc_type}_{field}: {err['value']!r} -> {err['problem']}")
                else:
                    caught += 1
                    print(f"caught      {name}_{doc_type}_{field}: got {err['value']!r} true {true_fields[field]!r}")
            for field, value in result["fields"].items():
                if field not in error_fields and value != true_fields[field]:
                    missed += 1
                    print(f"missed      {name}_{doc_type}_{field}: got {value!r} true {true_fields[field]!r}")
    print(f"\n{LANG}: caught {caught}, false alarms {false_alarm}, wrong but passed {missed}")


if __name__ == "__main__":
    if MODE == "truth":
        check_truth()
    elif MODE == "examples":
        for doc_type, fields in EXAMPLES:
            show(doc_type, fields)
    else:
        check_extract()