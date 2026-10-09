import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import psutil

from src.classify import classify, load_model
from src.ingest import ingest
from src.ocr import ocr_if_needed
from src.pipeline import run

LOAN_DIR = Path("data/loan_files")
TRUTH_DIR = Path("data/ground_truth")
OUT_DIR = Path("outputs/eval")
ALERT_CODES = ["same_name", "same_address", "proof_of_address_recent", "salary_on_statement"]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def same(want, got):
    # amounts can differ by float rounding, everything else must be exact
    if isinstance(want, float):
        return isinstance(got, (int, float)) and abs(want - got) < 0.01
    return got is not None and str(got).strip() == str(want).strip()


def percent(good, total):
    return round(100 * good / total, 1) if total else None


def expected_status(expected):
    if expected["missing"]:
        return "INCOMPLETE"
    if expected["alerts"]:
        return "ALERT"
    return "OK"


def classify_rows(pdf, labels, model):
    # rules and ml on the same pages, no llm needed
    rows = []
    for page, label in zip(ingest(pdf), labels["pages"]):
        page = ocr_if_needed(page)
        rules = classify(page)["doc_type"]
        ml = classify(page, model)["doc_type"]
        rows.append({"scanned": label["scanned"], "want": label["doc_type"], "rules": rules, "ml": ml})
    return rows


def field_rows(report, truth, labels):
    # only documents really in the file, a missed document counts as wrong fields
    rows = []
    for doc_type, page_nums in labels["documents"].items():
        if not page_nums:
            continue
        fields = report["documents"].get(doc_type, {}).get("fields", {})
        for name, want in truth["documents"][doc_type].items():
            got = fields.get(name)
            rows.append({"file": labels["file"], "field": f"{doc_type}.{name}",
                         "want": want, "got": got, "ok": same(want, got)})
    return rows


def alert_rows(report, expected):
    return [{"check": code, "want": code in expected["alerts"], "got": code in report["alerts"]}
            for code in ALERT_CODES]


def accuracy(rows, key):
    return percent(sum(r[key] == r["want"] for r in rows), len(rows))


def evaluate_lang(lang, model):
    files = sorted((LOAN_DIR / lang).glob("*.pdf"))
    pages, fields, alerts = [], [], []
    matched = 0
    seconds = 0.0
    step_seconds = Counter()
    peak_mb = 0.0
    process = psutil.Process()

    for pdf in files:
        labels = load_json(pdf.with_suffix(".json"))
        truth = load_json(TRUTH_DIR / f"{labels['person_id']}.json")
        expected = labels["expected"]
        # fixed reference date, with today the results would change every day
        report = run(pdf, lang, date.fromisoformat(truth["file_date"]))

        pages += classify_rows(pdf, labels, model)
        fields += field_rows(report, truth, labels)
        alerts += alert_rows(report, expected)

        ok = (report["status"] == expected_status(expected)
              and sorted(report["alerts"]) == sorted(expected["alerts"])
              and sorted(report["missing"]) == sorted(expected["missing"]))
        matched += ok
        seconds += report["seconds"]
        step_seconds.update(report["step_seconds"])
        # ram of this python process only, ollama runs in its own process
        peak_mb = max(peak_mb, process.memory_info().rss / 1e6)
        print(f"{'ok  ' if ok else 'DIFF'} {pdf.name} {report['status']:10} {report['seconds']:.1f} s")

    text = [p for p in pages if not p["scanned"]]
    scanned = [p for p in pages if p["scanned"]]
    summary = {
        "lang": lang,
        "files": len(files),
        "pages": len(pages),
        "classify_rules_text": accuracy(text, "rules"),
        "classify_rules_scanned": accuracy(scanned, "rules"),
        # ml was trained on the text pages, only the scanned score is a real test
        "classify_ml_text": accuracy(text, "ml"),
        "classify_ml_scanned": accuracy(scanned, "ml"),
        "fields": percent(sum(f["ok"] for f in fields), len(fields)),
        "alerts_found": sum(a["want"] and a["got"] for a in alerts),
        "alerts_expected": sum(a["want"] for a in alerts),
        "false_alerts": sum(a["got"] and not a["want"] for a in alerts),
        "files_matched": matched,
        "seconds_per_page": round(seconds / len(pages), 2),
        "step_seconds": {step: round(s, 1) for step, s in step_seconds.items()},
        "peak_rss_mb": round(peak_mb),
    }
    wrong = [f for f in fields if not f["ok"]]
    return summary, wrong


if __name__ == "__main__":
    # python -m eval.evaluate fr   (or en, or both)
    arg = sys.argv[1] if len(sys.argv) > 1 else "both"
    langs = ["fr", "en"] if arg == "both" else [arg]
    model = load_model()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for lang in langs:
        summary, wrong = evaluate_lang(lang, model)
        with open(OUT_DIR / f"eval_{lang}.json", "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "wrong_fields": wrong}, f, ensure_ascii=False, indent=2)
        print(json.dumps(summary, indent=2))
        for w in wrong:
            print(f"  {w['file']} {w['field']}: want {w['want']!r} got {w['got']!r}")