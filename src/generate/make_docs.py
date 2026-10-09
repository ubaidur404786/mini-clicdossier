import json
from datetime import date
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

GT_DIR = Path("data/ground_truth")
OUT_DIR = Path("data/generated")
LANGS = ["fr", "en"]

TITLES = {
    "fr": {
        "id_card": "CARTE NATIONALE D'IDENTITÉ",
        "payslip": "BULLETIN DE SALAIRE",
        "proof_of_address": "FACTURE D'ÉNERGIE",
        "bank_statement": "RELEVÉ DE COMPTE",
    },
    "en": {
        "id_card": "NATIONAL ID CARD",
        "payslip": "PAYSLIP",
        "proof_of_address": "ENERGY BILL",
        "bank_statement": "BANK STATEMENT",
    },
}

LABELS = {
    "fr": {
        "last_name": "Nom",
        "first_name": "Prénom",
        "birth_date": "Date de naissance",
        "id_number": "N° de document",
        "expiry_date": "Date d'expiration",
        "employer": "Employeur",
        "pay_period": "Période",
        "gross_salary": "Salaire brut",
        "net_salary": "Net à payer",
        "address_line": "Adresse",
        "postal_code": "Code postal",
        "city": "Ville",
        "supplier": "Fournisseur",
        "issue_date": "Date de facture",
        "amount_due": "Montant à payer",
        "iban": "IBAN",
        "statement_date": "Date du relevé",
        "salary_credit": "Virement salaire",
    },
    "en": {
        "last_name": "Last name",
        "first_name": "First name",
        "birth_date": "Date of birth",
        "id_number": "Document number",
        "expiry_date": "Expiry date",
        "employer": "Employer",
        "pay_period": "Pay period",
        "gross_salary": "Gross salary",
        "net_salary": "Net pay",
        "address_line": "Address",
        "postal_code": "Postcode",
        "city": "City",
        "supplier": "Supplier",
        "issue_date": "Bill date",
        "amount_due": "Amount due",
        "iban": "IBAN",
        "statement_date": "Statement date",
        "salary_credit": "Salary credit",
    },
}

FOOTER = {
    "fr": "Document fictif, généré pour des tests.",
    "en": "Fictional document, made for testing.",
}

# own month names, so the output does not depend on the system locale
MONTHS = {
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
}

AMOUNT_FIELDS = {"gross_salary", "net_salary", "amount_due", "salary_credit"}
DATE_FIELDS = {"birth_date", "expiry_date", "issue_date", "statement_date"}


def format_amount(value, lang):
    text = f"{value:,.2f}"  # 2,145.30
    if lang == "fr":
        return text.replace(",", " ").replace(".", ",") + " €"
    return "€" + text


def format_date(iso, lang):
    d = date.fromisoformat(iso)
    if lang == "fr":
        return d.strftime("%d/%m/%Y")
    return f"{d.day} {MONTHS['en'][d.month - 1][:3]} {d.year}"  # 31 Aug 2026


def format_period(period, lang):
    year, month = period.split("-")
    return f"{MONTHS[lang][int(month) - 1]} {year}"


def format_iban(iban):
    return " ".join(iban[i:i + 4] for i in range(0, len(iban), 4))


def format_value(field, value, lang):
    if field in AMOUNT_FIELDS:
        return format_amount(value, lang)
    if field in DATE_FIELDS:
        return format_date(value, lang)
    if field == "pay_period":
        return format_period(value, lang)
    if field == "iban":
        return format_iban(value)
    return str(value)


def draw_doc(path, doc_type, fields, lang):
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    y = height - 80
    c.setFont("Helvetica-Bold", 18)
    c.drawString(60, y, TITLES[lang][doc_type])

    y -= 50
    c.setFont("Helvetica", 12)
    for field, value in fields.items():
        c.drawString(60, y, LABELS[lang][field])
        c.drawString(250, y, format_value(field, value, lang))
        y -= 25

    c.setFont("Helvetica", 8)
    c.drawString(60, 40, FOOTER[lang])
    c.showPage()
    c.save()


def make_docs(person):
    paths = []
    for lang in LANGS:
        out = OUT_DIR / lang
        out.mkdir(parents=True, exist_ok=True)
        # a missing document is not in the json, so it is never drawn
        for doc_type, fields in person["documents"].items():
            path = out / f"{person['person_id']}_{doc_type}.pdf"
            draw_doc(path, doc_type, fields, lang)
            paths.append(path)
    return paths


def load_people():
    people = []
    for path in sorted(GT_DIR.glob("p*.json")):
        with open(path, encoding="utf-8") as f:
            people.append(json.load(f))
    return people


if __name__ == "__main__":
    for person in load_people():
        for path in make_docs(person):
            print("saved", path)