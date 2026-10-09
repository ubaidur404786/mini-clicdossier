import json
import random
import string
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

N_PEOPLE = 30
SEED = 42
OUT_DIR = Path("data/ground_truth")

DOC_TYPES = ["id_card", "payslip", "proof_of_address", "bank_statement"]

# 30 people: 12 ok, 6 missing doc, 6 mismatch, 6 scanned
SCENARIOS = (
    ["ok"] * 12
    + ["missing_doc"] * 6
    + ["address_mismatch"] * 2
    + ["old_bill"] * 2
    + ["salary_mismatch"] * 2
    + ["scanned"] * 6
)

SUPPLIERS = ["EDF", "Engie", "TotalEnergies", "Veolia"]

fake = Faker("fr_FR")


def make_address():
    return {
        "address_line": fake.street_address(),
        "postal_code": fake.postcode(),
        "city": fake.city(),
    }


def make_id_number():
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=9))


def make_birth_date():
    return date(random.randint(1960, 2004), random.randint(1, 12), random.randint(1, 28))


def make_person(person_id, scenario):
    file_date = date(2026, 9, 1) + timedelta(days=random.randint(0, 29))
    # payslip and statement are for the month before the file date
    last_month_end = file_date.replace(day=1) - timedelta(days=1)

    last_name = fake.last_name().upper()
    first_name = fake.first_name()
    address = make_address()

    gross = round(random.uniform(1900, 4500), 2)
    net = round(gross * 0.78, 2)

    id_card = {
        "last_name": last_name,
        "first_name": first_name,
        "birth_date": make_birth_date().isoformat(),
        "id_number": make_id_number(),
        "expiry_date": (file_date + timedelta(days=random.randint(365, 3650))).isoformat(),
    }

    payslip = {
        "last_name": last_name,
        "first_name": first_name,
        "employer": fake.company(),
        "pay_period": last_month_end.strftime("%Y-%m"),
        "gross_salary": gross,
        "net_salary": net,
    }

    bill_address = address
    bill_days_old = random.randint(5, 60)
    salary_credit = net
    expected_alerts = []

    if scenario == "address_mismatch":
        bill_address = make_address()
        expected_alerts.append("same_address")
    elif scenario == "old_bill":
        bill_days_old = random.randint(120, 200)
        expected_alerts.append("proof_of_address_recent")
    elif scenario == "salary_mismatch":
        salary_credit = round(net - random.uniform(200, 500), 2)
        expected_alerts.append("salary_on_statement")

    proof_of_address = {
        "last_name": last_name,
        "first_name": first_name,
        "address_line": bill_address["address_line"],
        "postal_code": bill_address["postal_code"],
        "city": bill_address["city"],
        "supplier": random.choice(SUPPLIERS),
        "issue_date": (file_date - timedelta(days=bill_days_old)).isoformat(),
        "amount_due": round(random.uniform(40, 180), 2),
    }

    bank_statement = {
        "last_name": last_name,
        "first_name": first_name,
        "address_line": address["address_line"],
        "postal_code": address["postal_code"],
        "city": address["city"],
        "iban": fake.iban(),
        "statement_date": last_month_end.isoformat(),
        "salary_credit": salary_credit,
    }

    documents = {
        "id_card": id_card,
        "payslip": payslip,
        "proof_of_address": proof_of_address,
        "bank_statement": bank_statement,
    }

    missing = []
    if scenario == "missing_doc":
        doc_type = random.choice(DOC_TYPES)
        del documents[doc_type]
        missing.append(doc_type)

    return {
        "person_id": person_id,
        "scenario": scenario,
        "file_date": file_date.isoformat(),
        "documents": documents,
        "expected": {"missing": missing, "alerts": expected_alerts},
    }


def make_all(n_people=N_PEOPLE, seed=SEED):
    random.seed(seed)
    Faker.seed(seed)

    scenarios = SCENARIOS.copy()
    random.shuffle(scenarios)

    people = []
    for i in range(n_people):
        person_id = f"p{i + 1:03d}"
        scenario = scenarios[i % len(scenarios)]
        people.append(make_person(person_id, scenario))
    return people


def save(person):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{person['person_id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(person, f, ensure_ascii=False, indent=2)
    return path


if __name__ == "__main__":
    for person in make_all():
        print("saved", save(person))