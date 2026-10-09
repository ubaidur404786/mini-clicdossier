import json

import ollama

MODEL = "qwen2.5:3b"

# same field names for fr and en, used again in validate and evaluate
FIELDS = {
    "id_card": ["last_name", "first_name", "birth_date", "id_number", "expiry_date"],
    "payslip": ["last_name", "first_name", "employer", "pay_period", "gross_salary", "net_salary"],
    "proof_of_address": ["last_name", "first_name", "address_line", "postal_code", "city",
                         "supplier", "issue_date", "amount_due"],
    "bank_statement": ["last_name", "first_name", "address_line", "postal_code", "city",
                       "iban", "statement_date", "salary_credit"],
}

# short meaning of each key, in the prompt language
DESCRIPTIONS = {
    "fr": {
        "last_name": "nom de famille", "first_name": "prénom", "birth_date": "date de naissance",
        "id_number": "numéro du document", "expiry_date": "date d'expiration",
        "employer": "nom de l'employeur", "pay_period": "mois payé", "gross_salary": "salaire brut",
        "net_salary": "salaire net payé", "address_line": "numéro et rue", "postal_code": "code postal",
        "city": "ville", "supplier": "fournisseur", "issue_date": "date de la facture",
        "amount_due": "montant à payer", "iban": "IBAN", "statement_date": "date du relevé",
        "salary_credit": "montant du virement de salaire",
    },
    "en": {
        "last_name": "family name", "first_name": "given name", "birth_date": "date of birth",
        "id_number": "document number", "expiry_date": "expiry date",
        "employer": "employer name", "pay_period": "month paid", "gross_salary": "gross salary",
        "net_salary": "net pay", "address_line": "street number and street", "postal_code": "postcode",
        "city": "city", "supplier": "supplier", "issue_date": "date of the bill",
        "amount_due": "amount to pay", "iban": "IBAN", "statement_date": "date of the statement",
        "salary_credit": "amount of the salary transfer",
    },
}

AMOUNT_FIELDS = {"gross_salary", "net_salary", "amount_due", "salary_credit"}

PROMPTS = {
    "fr": (
        "Voici le texte d'un document français de type {doc_type}.\n"
        "Réponds uniquement en JSON avec exactement ces clés :\n{fields}\n"
        "Règles :\n"
        "- dates au format AAAA-MM-JJ (14/03/2028 devient 2028-03-14)\n"
        "- pay_period au format AAAA-MM (août 2026 devient 2026-08)\n"
        "- montants recopiés tels qu'ils sont écrits\n"
        "- iban sans espaces\n"
        "- recopie les autres valeurs exactement comme elles sont écrites\n"
        "- null si le champ n'est pas dans le texte\n\n"
        "Texte :\n{text}"
    ),
    "en": (
        "Here is the text of an English document of type {doc_type}.\n"
        "Answer only in JSON with exactly these keys:\n{fields}\n"
        "Rules:\n"
        "- dates in YYYY-MM-DD format (14 Mar 2028 becomes 2028-03-14)\n"
        "- pay_period in YYYY-MM format (August 2026 becomes 2026-08)\n"
        "- amounts copied as they are written\n"
        "- iban without spaces\n"
        "- copy the other values exactly as they are written\n"
        "- null if the field is not in the text\n\n"
        "Text:\n{text}"
    ),
}

def make_prompt(doc_type, text, lang):
    fields = "\n".join(f"- {name}: {DESCRIPTIONS[lang][name]}" for name in FIELDS[doc_type])
    return PROMPTS[lang].format(doc_type=doc_type, fields=fields, text=text)

def to_number(value, lang):
    # "2 046,17 €" (fr) or "€2,046.17" (en) -> 2046.17
    if not isinstance(value, str):
        return value
    text = "".join(value.replace("€", "").split())
    if lang == "fr":
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        # leave it as it is, validate will reject it
        return value
    
def extract(doc_type, pages, lang="fr", model=MODEL):
    # unknown pages have no fields to extract
    if doc_type not in FIELDS:
        return {}
    text = "\n".join(p["text"] for p in pages)
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": make_prompt(doc_type, text, lang)}],
        format="json",
        options={"temperature": 0},
    )
    data = json.loads(response.message.content)
    fields={name: data.get(name) for name in FIELDS[doc_type]}
    for name in AMOUNT_FIELDS & fields.keys():
        fields[name] = to_number(fields[name], lang)
    # keep only the expected keys, a missing key becomes None
    return fields