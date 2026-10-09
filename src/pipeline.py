import sys
import time
from datetime import date
from pathlib import Path

from src.checks import REQUIRED, completeness, cross_check
from src.classify import classify
from src.extract import extract
from src.ingest import ingest
from src.ocr import ocr_if_needed
from src.report import make_report, save
from src.split import split
from src.validate import validate


def since(t):
    return round(time.perf_counter() - t, 2)


def run(pdf_path, lang="fr", ref_date=None, model=None):
    # ref_date = day the loan file is received, model = ml classifier or None for rules
    times = {}
    start = time.perf_counter()

    t = time.perf_counter()
    pages = ingest(pdf_path)
    times["ingest"] = since(t)

    t = time.perf_counter()
    pages = [ocr_if_needed(p) for p in pages]
    # images are not needed after ocr, free the memory
    for page in pages:
        page["image"] = None
    times["ocr"] = since(t)

    t = time.perf_counter()
    pages = [classify(p, model) for p in pages]
    docs = split(pages)
    times["classify"] = since(t)

    t = time.perf_counter()
    results = {}
    for doc_type, page_nums in docs.items():
        # "unknown" pages have no fields to extract
        if doc_type not in REQUIRED:
            continue
        doc_pages = [p for p in pages if p["page_num"] in page_nums]
        results[doc_type] = validate(doc_type, extract(doc_type, doc_pages, lang))
    times["extract"] = since(t)

    checks = cross_check(results, ref_date)
    missing = completeness(docs)
    report = make_report(pdf_path, lang, docs, results, checks, missing, since(start))
    report["step_seconds"] = times
    return report


if __name__ == "__main__":
    # python -m src.pipeline data/loan_files/fr/dossier_001.pdf fr 2026-09-19
    pdf_path = Path(sys.argv[1])
    lang = sys.argv[2] if len(sys.argv) > 2 else "fr"
    ref_date = date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else None
    report = run(pdf_path, lang, ref_date)
    json_path, html_path = save(report)
    print(report["status"], report["alerts"], report["missing"], f"{report['seconds']} s")
    print("saved", json_path, html_path)