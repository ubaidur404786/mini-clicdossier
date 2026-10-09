# Mini ClicDossier

A small, 100% local document AI pipeline for loan files.
Input: one mixed PDF (ID card, payslip, proof of address, bank statement, some pages scanned),
in French or English. Output: a checked report (status, documents found, missing documents,
alerts, time per step) as JSON and HTML.

I built it to learn how document AI works end to end: OCR, page classification, field extraction
with a small LLM, validation, cross-document checks and evaluation. Nothing leaves the machine:
Tesseract for OCR and `qwen2.5:3b` through Ollama on a 6 GB laptop GPU.

## Results

30 loan files per language (114 pages each), same values in French and English,
`qwen2.5:3b` on an RTX 3050 6 GB laptop GPU, OCR at 200 dpi.

| Metric                                         | FR        | EN        |
| ---------------------------------------------- | --------- | --------- |
| Page classification, scanned pages (rules / ML) | 100 / 100 % | 100 / 100 % |
| Field extraction (end to end, exact match)     | 97.7 %    | 98.4 %    |
| Alerts found / false alerts                    | 6/6, 0    | 6/6, 0    |
| Files with the right status, alerts, missing   | 28/30     | 28/30     |
| Seconds per page (whole pipeline)              | 2.14      | 2.11      |

- The 4 missed files all ended as `REVIEW` (a field came back empty, so a check could not run),
  never as a wrong `OK`. Causes: the LLM left a field null, or OCR read `O` for `0` in an IBAN
  and the checksum rejected it.
- Time is mostly the LLM: extraction ~75-85 %, OCR the rest, ingest and classification ~0.
- Peak RAM of the Python process: ~220 MB. The model uses ~2.1 GB of VRAM in Ollama.

### Optimization: OCR at 300 -> 200 dpi

I measured OCR alone on the 24 scanned pages (are the true name, IBAN, postal code and ID number
in the raw OCR text?), then re-ran the full evaluation.

| dpi | s per scanned page | mean OCR conf | true values found |
| --- | ------------------ | ------------- | ----------------- |
| 300 | 2.54               | 0.948         | 93.8 %            |
| 200 | 1.36               | 0.943         | 95.8 %            |
| 150 | 1.02               | 0.940         | 95.8 %            |

200 dpi made the OCR step 46 % faster (54.4 s -> 29.5 s for the French set) with the same quality.
I did not pick 150: the gain is small and confidence keeps dropping, and real scans are worse
than mine. The total seconds per page did not move (2.15 -> 2.14): OCR was only ~22 % of the time,
so the next real gain is in the LLM step.

## Pipeline

```
loan file pdf (fr or en, mixed pages, some scanned)
  [1] ingest       pdf -> pages (text layer if present, else 200 dpi gray image)
  [2] ocr          image -> text + confidence (tesseract fra+eng)
  [3] classify     text -> page type (keyword rules, or TF-IDF + logistic regression)
  [4] split        pages -> documents {"payslip": [2], "id_card": [1], ...}
  [5] extract      document text -> json fields (qwen2.5:3b, format="json", temperature 0)
  [6] validate     pydantic types, ranges, regex, IBAN mod-97 checksum
  [7] cross-check  same name, same address, proof of address < 90 days, salary on statement
  [8] completeness all 4 required documents present?
  [9] report       report.json + report.html, status INCOMPLETE > ALERT > REVIEW > OK
```

Some choices:

- The LLM never has the last word. It copies values as written, code converts amounts and dates,
  and validation turns a value that breaks a rule into `None` + an error. A wrong value would
  give a false alert later, an empty one only gives "can't check" (`REVIEW`).
- Checks have 3 results: `OK`, `ALERT`, `UNKNOWN`. A missing value never becomes a fake alert.
- Names and addresses are compared after normalization (upper case, no accents) with a
  similarity score, because exact matching on OCR + LLM output gives false alarms.
- OCR is only run on pages without a text layer.
- Alert codes and field names are always English; only the report text is French or English.

## Data

I used synthetic data only. Real loan documents are personal data (GDPR) and not public,
and synthetic data gives exact ground truth for free.

- 30 fake people (Faker `fr_FR`, fixed seed), one ground truth JSON each in `data/ground_truth/`.
- Each document is drawn as a PDF with reportlab, in French and in English with the same values.
  Only labels and formats change (`2 145,30 €` / `€2,145.30`, `31/08/2026` / `31 Aug 2026`).
  So a FR/EN difference comes from the language, not the data.
- Scenarios: 12 ok, 6 missing document, 6 mismatch (other address, bill older than 90 days,
  salary not on the statement), 6 scanned (image only, gray, small rotation, blur, noise).
- The documents of one person are merged into one loan file in a shuffled order, with a JSON
  label file (true type of each page, expected missing documents and alerts) used by the evaluation.
- Generated PDFs are not in the repo, the scripts rebuild them (see below).

## How to run

Needs Python 3.11, [Tesseract](https://github.com/tesseract-ocr/tesseract) with French and English
data, and [Ollama](https://ollama.com). Commands are for Windows PowerShell; on Linux activate the
venv with `source .venv/bin/activate`.

```
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama pull qwen2.5:3b
```

Build the data (in this order):

```
python -m src.generate.fake_people
python -m src.generate.make_docs
python -m src.generate.scan_effects
python -m src.generate.make_loan_files
```

Train the page classifier, run one file, run the evaluation:

```
python -m src.classify
python -m src.pipeline data/loan_files/fr/dossier_001.pdf fr
python -m eval.evaluate both
python -m eval.dpi_test fr
```

Reports go to `outputs/`, evaluation results to `outputs/eval/`.
Check `ollama ps` shows `100% GPU` before measuring speed.

## Project structure

```
src/generate/   synthetic people, pdf documents, scan effects, loan files
src/            ingest, ocr, classify, split, extract, validate, checks, report, pipeline
eval/           evaluate.py (accuracy per step, fr vs en, time, memory), dpi_test.py
debug/          one script per step to run and inspect it alone
data/ground_truth/   true values for each person
```

## Limits

- Synthetic data with one fixed template per document type. 100 % classification here shows the
  code works, not that it generalizes to real documents.
- My scan effects are mild. Real phone photos and faxes are much harder for OCR.
- 30 files per language is small, and the LLM output changes a little between GPU runs,
  so differences under ~1 % are noise.
- Wrong values with the right shape still pass validation (`Jeannec` for `Jeannenec`,
  `O` for `0` in an ID number, which has no checksum).
- Every document is one page, and two documents of the same type (two payslips) would be merged.

## Next steps

- Make the LLM step faster: shorter prompts, one call per file instead of one per document.
- Send pages with low OCR confidence to a small vision model instead of a human.
- Test OCR and extraction on real scans (e.g. the SROIE receipts dataset) and harder scan effects.
- More document templates, and boundary detection for multi-page and repeated documents.