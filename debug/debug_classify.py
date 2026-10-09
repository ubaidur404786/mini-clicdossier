import json
import time
from collections import Counter
from pathlib import Path

from src.classify import classify, load_model
from src.ingest import ingest
from src.ocr import ocr_if_needed

LANG = "en"
MAX_FILES = None
TEST_ON = "ocr"       # "ocr" = scanned pages, never seen in training. "all" = every page
LOW_CONF = 0.6
TOP_WORDS = 5

model = load_model()

# the words with the biggest weight for each type
vectorizer, lr = model[0], model[-1]
words = vectorizer.get_feature_names_out()
print("vocabulary size:", len(words))
for i, doc_type in enumerate(lr.classes_):
    top = lr.coef_[i].argsort()[::-1][:TOP_WORDS]
    print(f"  {doc_type:17} {[words[j] for j in top]}")

correct = Counter()
confs = {"rules": [], "ml": []}
low = []
errors = []
n = 0
start = time.perf_counter()

pdfs = sorted(Path("data/loan_files", LANG).glob("*.pdf"))[:MAX_FILES]
for pdf in pdfs:
    with open(pdf.with_suffix(".json"), encoding="utf-8") as f:
        labels = json.load(f)
    for page, label in zip(ingest(pdf), labels["pages"]):
        if TEST_ON == "ocr" and page["source"] != "ocr":
            continue
        page = ocr_if_needed(page)
        n += 1
        for method, m in [("rules", None), ("ml", model)]:
            p = classify(dict(page), m)
            confs[method].append(p["type_conf"])
            if p["doc_type"] == label["doc_type"]:
                correct[method] += 1
            else:
                errors.append((pdf.stem, p["page_num"], method, label["doc_type"], p["doc_type"], p["type_conf"]))
            if p["type_conf"] < LOW_CONF:
                low.append((pdf.stem, p["page_num"], method, p["doc_type"], p["type_conf"]))

print(f"\n{LANG} | test on: {TEST_ON} | {n} pages | {time.perf_counter() - start:.2f} s")
for method in ["rules", "ml"]:
    c = confs[method]
    print(f"  {method:5} accuracy {correct[method]}/{n}  conf mean {sum(c) / len(c):.3f}  min {min(c):.3f}")

print("\nlow conf:")
for row in low:
    print("  ", row)
print("\nerrors (file, page, method, true, pred, conf):")
for row in errors:
    print("  ", row)