import json
import time
from collections import Counter
from pathlib import Path

from src.classify import classify, rule_scores
from src.ingest import ingest
from src.ocr import ocr_if_needed

LANG = "en"
MAX_FILES = None      # e.g. 3 for a quick run
SKIP_SCANNED = False   # True skips ocr pages (fast), False runs ocr on them (~2.4 s/page)
LOW_CONF = 0.6
SHOW_LINES = 3

pdfs = sorted(Path("data/loan_files", LANG).glob("*.pdf"))[:MAX_FILES]
print(f"{len(pdfs)} files, lang={LANG}, skip_scanned={SKIP_SCANNED}")

total = 0
correct = 0
errors = []
low = []
confusion = Counter()
start = time.perf_counter()

for pdf in pdfs:
    labels = json.load(open(pdf.with_suffix(".json"), encoding="utf-8"))
    for page, label in zip(ingest(pdf), labels["pages"]):
        if SKIP_SCANNED and page["source"] == "ocr":
            continue
        page = classify(ocr_if_needed(page))
        true_type = label["doc_type"]
        total += 1
        if page["doc_type"] == true_type:
            correct += 1
        else:
            confusion[(true_type, page["doc_type"])] += 1
            errors.append((pdf.name, page["page_num"], true_type, page["doc_type"],
                           rule_scores(page["text"]), page["text"]))
        if page["type_conf"] < LOW_CONF:
            low.append((pdf.name, page["page_num"], true_type, page["doc_type"], page["type_conf"]))

seconds = time.perf_counter() - start
print(f"\naccuracy {correct}/{total} = {correct / total:.3f} | {seconds:.2f} s total")
print(f"low conf (< {LOW_CONF}): {len(low)}")
for item in low:
    print("  ", item)

print("\nconfusion (true -> predicted):")
for (true_type, pred), n in confusion.items():
    print(f"  {true_type} -> {pred}: {n}")

for name, num, true_type, pred, scores, text in errors:
    print(f"\n{name} p{num} | true {true_type} | predicted {pred} | {scores}")
    print("\n".join(text.strip().splitlines()[:SHOW_LINES]))