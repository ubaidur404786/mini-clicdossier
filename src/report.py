import html
import json
from pathlib import Path

OUT_DIR = Path("outputs")

TEXT = {
    "fr": {"title": "Rapport du dossier", "subtitle": "Contrôle automatique d'un dossier de prêt",
           "status": "Statut", "missing": "Documents manquants", "alerts": "Alertes",
           "checks": "Contrôles", "documents": "Documents", "none": "aucun",
           "seconds": "Temps de traitement", "check": "Contrôle", "result": "Résultat",
           "detail": "Détail", "pages": "page(s)",
           "footer": "Rapport généré automatiquement, à valider par un analyste. Traitement 100 % local."},
    "en": {"title": "Loan file report", "subtitle": "Automatic check of a loan file",
           "status": "Status", "missing": "Missing documents", "alerts": "Alerts",
           "checks": "Checks", "documents": "Documents", "none": "none",
           "seconds": "Processing time", "check": "Check", "result": "Result",
           "detail": "Detail", "pages": "page(s)",
           "footer": "Report generated automatically, to be confirmed by an analyst. 100% local processing."},
}

DOC_NAMES = {
    "fr": {"id_card": "Carte d'identité", "payslip": "Bulletin de salaire",
           "proof_of_address": "Justificatif de domicile", "bank_statement": "Relevé bancaire",
           "unknown": "Pages non reconnues"},
    "en": {"id_card": "ID card", "payslip": "Payslip", "proof_of_address": "Proof of address",
           "bank_statement": "Bank statement", "unknown": "Unrecognized pages"},
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
    doc_names = DOC_NAMES[report["lang"]]

    check_rows = ""
    for c in report["checks"]:
        check_rows += (f"<tr><td>{names[c['check']]}</td>"
                       f"<td><span class='badge {c['status']}'>{c['status']}</span></td>"
                       f"<td>{html.escape(c['detail'])}</td></tr>\n")

    doc_parts = ""
    for doc_type, doc in report["documents"].items():
        rows = ""
        for name, value in doc["fields"].items():
            shown = "-" if value is None else html.escape(str(value))
            rows += f"<tr><td class='key'>{name}</td><td>{shown}</td></tr>\n"
        for err in doc["errors"]:
            rows += (f"<tr class='error'><td class='key'>{err['field']}</td>"
                     f"<td>{html.escape(err['problem'])} ({html.escape(str(err['value']))})</td></tr>\n")
        pages = ", ".join(str(p) for p in doc["pages"])
        doc_parts += (f"<section class='card'><h3>{doc_names.get(doc_type, doc_type)}"
                      f"<span>{t['pages']} {pages}</span></h3>\n<table>\n{rows}</table></section>\n")

    missing = ", ".join(doc_names.get(m, m) for m in report["missing"]) or t["none"]
    alerts = ", ".join(names[a] for a in report["alerts"]) or t["none"]
    seconds = "-" if report["seconds"] is None else f"{report['seconds']:.1f} s"
    status = report["status"]

    return f"""<!doctype html>
<html lang="{report['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t['title']} - {report['file']}</title>
<style>
body {{ margin: 0; background: #f4f5f7; color: #1f2933; font: 14px/1.5 "Segoe UI", Arial, sans-serif; }}
header {{ background: #1f2a44; color: #fff; padding: 14px 32px; display: flex; justify-content: space-between; }}
header b {{ letter-spacing: 1px; }}
main, footer {{ max-width: 980px; margin: 24px auto; padding: 0 16px; }}
h1 {{ font-size: 22px; margin: 0; }}
h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #52606d; margin: 28px 0 10px; }}
.sub {{ color: #52606d; margin: 2px 0 20px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
.docs {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }}
.box, .card {{ background: #fff; border: 1px solid #d9dde3; border-radius: 6px; overflow: hidden; }}
.box {{ padding: 12px 16px; }}
.box small {{ display: block; color: #52606d; text-transform: uppercase; font-size: 11px; letter-spacing: 1px; }}
.box div {{ font-size: 15px; font-weight: 600; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ text-align: left; font-size: 12px; color: #52606d; background: #f9fafb; }}
th, td {{ padding: 8px 12px; border-bottom: 1px solid #eceff3; overflow-wrap: anywhere; }}
tr:last-child td {{ border-bottom: none; }}
.card h3 {{ margin: 0; padding: 10px 12px; font-size: 14px; background: #f9fafb;
           border-bottom: 1px solid #d9dde3; display: flex; justify-content: space-between; }}
.card h3 span {{ font-weight: normal; color: #52606d; }}
.key {{ color: #52606d; width: 40%; font-family: Consolas, monospace; font-size: 12px; }}
.badge {{ display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 600; }}
.OK {{ background: #e3f4e8; color: #1e6b3a; }}
.ALERT, .INCOMPLETE {{ background: #fbe4e2; color: #a12a1f; }}
.UNKNOWN, .REVIEW {{ background: #fdf3d8; color: #8a5a00; }}
.error td {{ background: #fbe4e2; }}
footer {{ color: #7b8794; font-size: 12px; }}
</style>
</head>
<body>
<header><b>MINI CLICDOSSIER</b><span>{report['file']} · {report['lang'].upper()}</span></header>
<main>
<h1>{t['title']} : {report['file']}</h1>
<p class="sub">{t['subtitle']}</p>
<div class="summary">
<div class="box"><small>{t['status']}</small><div><span class="badge {status}">{status}</span></div></div>
<div class="box"><small>{t['missing']}</small><div>{missing}</div></div>
<div class="box"><small>{t['alerts']}</small><div>{alerts}</div></div>
<div class="box"><small>{t['seconds']}</small><div>{seconds}</div></div>
</div>
<h2>{t['checks']}</h2>
<div class="card"><table>
<tr><th>{t['check']}</th><th>{t['result']}</th><th>{t['detail']}</th></tr>
{check_rows}</table></div>
<h2>{t['documents']}</h2>
<div class="docs">
{doc_parts}</div>
</main>
<footer>{t['footer']}</footer>
</body>
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