import json
import unicodedata
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from src.ingest import ingest

MODEL_PATH = Path("outputs/models/page_classifier.joblib")
LOAN_DIR = Path("data/loan_files")

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

def classify_rules(page):
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

def make_model():
    # strip_accents does the same job as normalize(), lowercase is on by default
    return make_pipeline(
        #[^\W\d] means “a word character that is not a digit”, so the pattern keeps only words of 2 or more letters. 31, 2026 and 2145 disappear from the vocabulary because they are not giving any info in classification.
        TfidfVectorizer(strip_accents="unicode", ngram_range=(1, 2), min_df=2,token_pattern=r"(?u)\b[^\W\d]{2,}\b"),
        LogisticRegression(max_iter=1000),
    )

def load_text_pages(langs=("fr", "en")):
    # only pdf_text pages, the scanned (ocr) pages are kept for testing
    texts, labels = [], []
    for lang in langs:
        for pdf in sorted((LOAN_DIR / lang).glob("*.pdf")):
            with open(pdf.with_suffix(".json"), encoding="utf-8") as f:
                file_labels = json.load(f)
            for page, label in zip(ingest(pdf), file_labels["pages"]):
                if page["source"] == "pdf_text":
                    texts.append(page["text"])
                    labels.append(label["doc_type"])
    return texts, labels

def train(texts, labels):
    model = make_model()
    model.fit(texts, labels)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    return model

def load_model():
    return joblib.load(MODEL_PATH)

def classify_ml(page, model):
    # an empty page has no words, the model would still guess a type
    if not page["text"].strip():
        page["doc_type"] = "unknown"
        page["type_conf"] = 0.0
        return page
    probs = model.predict_proba([page["text"]])[0]
    best = probs.argmax()
    page["doc_type"] = str(model.classes_[best])
    page["type_conf"] = round(float(probs[best]), 3)
    return page

def classify(page, model=None):
    # rules by default, the ml model if one is given
    if model is None:
        return classify_rules(page)
    return classify_ml(page, model)

if __name__ == "__main__":
    texts, labels = load_text_pages()
    model = train(texts, labels)
    print(len(texts), "training pages, classes:", list(model.classes_.tolist()))
    print("saved", MODEL_PATH)