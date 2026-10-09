import sys
import unicodedata
from pathlib import Path

from src.ingest import ingest
from src.ocr import ocr_if_needed

# keywords are written without accents, fr and en together
KEYWORDS = {
    "id_card": ["CARTE NATIONALE", "IDENTITE", "ID CARD", "IDENTITY", "EXPIRATION", "EXPIRY"],
    "payslip": ["BULLETIN DE SALAIRE", "PAYSLIP", "NET A PAYER", "NET PAY", "SALAIRE BRUT", "GROSS"],
    "proof_of_address": ["FACTURE", "BILL", "ENERGIE", "ENERGY", "CONSOMMATION", "CONSUMPTION"],
    "bank_statement": ["RELEVE", "STATEMENT", "IBAN", "SOLDE", "BALANCE"],
}


def normalize(text):
    # remove accents so "RELEVÉ" (pdf) and "RELEVE" (ocr) match the same keyword
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.upper()

def rule_scores(text):
    text = normalize(text)
    return {doc_type: sum(1 for word in words if word in text)
            for doc_type, words in KEYWORDS.items()}

def classify(page):
    scores = rule_scores(page["text"])
    total = sum(scores.values())
    if total == 0:
        page["doc_type"] = "unknown"
        page["type_conf"] = 0.0
        return page
    best = max(scores, key=scores.get)
    page["doc_type"] = best
    page["type_conf"] = round(scores[best] / total, 3)
    return page

if __name__ == "__main__":
    pdf_path = Path(sys.argv[1])
    for p in ingest(pdf_path):
        p = classify(ocr_if_needed(p))
        print(p["page_num"], p["source"], p["doc_type"], p["type_conf"])