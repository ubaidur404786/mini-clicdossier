import unicodedata
from datetime import date
from difflib import SequenceMatcher

REQUIRED = ["id_card", "payslip", "proof_of_address", "bank_statement"]

# a bill older than this is not a valid proof of address
MAX_BILL_AGE_DAYS = 90
# euros, the bank credit can differ by a few cents
SALARY_TOLERANCE = 1.0
# 1.0 = same text, a small ocr mistake gives about 0.9
MIN_SIMILARITY = 0.85


def normalize(text):
    # "Frédéric  De-Oliveira" -> "FREDERIC DE OLIVEIRA"
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    for c in ",.-'":
        text = text.replace(c, " ")
    return " ".join(text.upper().split())


def similar(a, b):
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def get(results, doc_type, name):
    if doc_type not in results:
        return None
    return results[doc_type]["fields"].get(name)


def make_check(check, status, detail):
    return {"check": check, "status": status, "detail": detail}


def check_same_name(results):
    names = {}
    for doc_type in REQUIRED:
        last = get(results, doc_type, "last_name")
        first = get(results, doc_type, "first_name")
        if last and first:
            names[doc_type] = f"{last} {first}"
    if len(names) < 2:
        return make_check("same_name", "UNKNOWN", "less than 2 documents with a full name")
    # first in REQUIRED order, so the id card when we have it
    ref_type = next(iter(names))
    ref = names[ref_type]
    for doc_type, name in names.items():
        score = similar(ref, name)
        if score < MIN_SIMILARITY:
            return make_check("same_name", "ALERT", f"{ref_type} '{ref}' vs {doc_type} '{name}' ({score:.2f})")
    return make_check("same_name", "OK", f"{len(names)} documents, same name")


def full_address(results, doc_type):
    parts = [get(results, doc_type, name) for name in ["address_line", "postal_code", "city"]]
    if None in parts:
        return None
    return " ".join(parts)


def check_same_address(results):
    bill = full_address(results, "proof_of_address")
    bank = full_address(results, "bank_statement")
    if bill is None or bank is None:
        return make_check("same_address", "UNKNOWN", "address missing on bill or statement")
    score = similar(bill, bank)
    if score < MIN_SIMILARITY:
        return make_check("same_address", "ALERT", f"bill '{bill}' vs statement '{bank}' ({score:.2f})")
    return make_check("same_address", "OK", f"same address ({score:.2f})")


def check_bill_recent(results, ref_date):
    issue_date = get(results, "proof_of_address", "issue_date")
    if issue_date is None:
        return make_check("proof_of_address_recent", "UNKNOWN", "no bill date")
    age = (ref_date - date.fromisoformat(issue_date)).days
    if age > MAX_BILL_AGE_DAYS:
        return make_check("proof_of_address_recent", "ALERT", f"bill is {age} days old (max {MAX_BILL_AGE_DAYS})")
    return make_check("proof_of_address_recent", "OK", f"bill is {age} days old")


def check_salary(results):
    net = get(results, "payslip", "net_salary")
    credit = get(results, "bank_statement", "salary_credit")
    if net is None or credit is None:
        return make_check("salary_on_statement", "UNKNOWN", "net salary or salary credit missing")
    diff = abs(net - credit)
    if diff > SALARY_TOLERANCE:
        return make_check("salary_on_statement", "ALERT", f"net {net} vs credit {credit} (diff {diff:.2f})")
    return make_check("salary_on_statement", "OK", f"net {net} vs credit {credit}")


def cross_check(results, ref_date=None):
    # ref_date = day the loan file is received
    if ref_date is None:
        ref_date = date.today()
    return [
        check_same_name(results),
        check_same_address(results),
        check_bill_recent(results, ref_date),
        check_salary(results),
    ]


def completeness(docs):
    return [doc_type for doc_type in REQUIRED if not docs.get(doc_type)]