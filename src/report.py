import html
import json
from pathlib import Path

OUT_DIR = Path("outputs")

TEXT = {
    "fr": {"title": "Rapport du dossier", "status": "Statut", "missing": "Documents manquants",
           "checks": "Contrôles", "documents": "Documents", "none": "aucun",
           "seconds": "Temps de traitement"},
    "en": {"title": "Loan file report", "status": "Status", "missing": "Missing documents",
           "checks": "Checks", "documents": "Documents", "none": "none",
           "seconds": "Processing time"},
}

CHECK_NAMES = {
    "fr": {"same_name": "Même nom sur les documents",
           "same_address": "Même adresse (facture et relevé)",
           "proof_of_address_recent": "Justificatif de domicile de moins de 90 jours",
           "salary_on_statement": "Salaire visible sur le relevé"},
    "en": {"same_name": "Same name on documents",
           "same_address": "Same address (bill and statement)",
           "proof_of_address_recent": "Proof of address under 90 days",
           "salary_on_statement": "Salary on bank statement"},
}


def file_status(results, checks, missing):
    if missing:
        return "INCOMPLETE"
    if any(c["status"] == "ALERT" for c in checks):
        return "ALERT"
    # a human must look if something could not be read or checked
    has_errors = any(r["errors"] for r in results.values())
    if has_errors or any(c["status"] == "UNKNOWN" for c in checks):
        return "REVIEW"
    return "OK"


def make_report(pdf_path, lang, docs, results, checks, missing, seconds=None):
    documents = {}
    for doc_type, page_nums in docs.items():
        result = results.get(doc_type, {"fields": {}, "errors": []})
        documents[doc_type] = {"pages": page_nums, "fields": result["fields"], "errors": result["errors"]}
    return {
        "file": Path(pdf_path).name,
        "lang": lang,
        "status": file_status(results, checks, missing),
        "missing": missing,
        "alerts": [c["check"] for c in checks if c["status"] == "ALERT"],
        "checks": checks,
        "documents": documents,
        "seconds": seconds,
    }


def to_html(report):
    t = TEXT[report["lang"]]
    names = CHECK_NAMES[report["lang"]]

    check_rows = ""
    for c in report["checks"]:
        check_rows += (f"<tr class='{c['status']}'><td>{names[c['check']]}</td>"
                       f"<td>{c['status']}</td><td>{html.escape(c['detail'])}</td></tr>\n")

    doc_parts = ""
    for doc_type, doc in report["documents"].items():
        rows = ""
        for name, value in doc["fields"].items():
            rows += f"<tr><td>{name}</td><td>{html.escape(str(value))}</td></tr>\n"
        for err in doc["errors"]:
            rows += (f"<tr class='ALERT'><td>{err['field']}</td>"
                     f"<td>{html.escape(err['problem'])} ({html.escape(str(err['value']))})</td></tr>\n")
        doc_parts += f"<h3>{doc_type} (pages {doc['pages']})</h3>\n<table>\n{rows}</table>\n"

    missing = ", ".join(report["missing"]) or t["none"]
    seconds = "-" if report["seconds"] is None else f"{report['seconds']:.1f} s"

    return f"""<!doctype html>
<html lang="{report['lang']}">
<head>
<meta charset="utf-8">
<title>{t['title']} - {report['file']}</title>
<style>
body {{ font-family: sans-serif; margin: 2em; }}
table {{ border-collapse: collapse; margin-bottom: 1em; }}
td {{ border: 1px solid #ccc; padding: 4px 8px; }}
.OK {{ background: #e6f4ea; }}
.ALERT {{ background: #fce8e6; }}
.UNKNOWN {{ background: #fef7e0; }}
</style>
</head>
<body>
<h1>{t['title']} : {report['file']}</h1>
<p><b>{t['status']} :</b> {report['status']}</p>
<p><b>{t['missing']} :</b> {missing}</p>
<p><b>{t['seconds']} :</b> {seconds}</p>
<h2>{t['checks']}</h2>
<table>
{check_rows}</table>
<h2>{t['documents']}</h2>
{doc_parts}</body>
</html>
"""


def save(report, out_dir=OUT_DIR):
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{Path(report['file']).stem}_{report['lang']}"
    json_path = out_dir / f"{stem}.json"
    html_path = out_dir / f"{stem}.html"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(to_html(report))
    return json_path, html_path