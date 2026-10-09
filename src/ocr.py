import sys
from pathlib import Path

import pytesseract

from src.ingest import ingest

LANG = "fra+eng"
CONFIG="--psm 6"  # psm 6 reads the page as one block, row by row, so "Name/Nom" stays next to "Ubaid"


def ocr_image(image, lang=LANG,config=CONFIG):
    data = pytesseract.image_to_data(image, lang=lang,config=config, output_type=pytesseract.Output.DICT)
    lines = {}
    confs = []
    for i, word in enumerate(data["text"]):
        word = word.strip()
        conf = float(data["conf"][i])
        # -1 means a block or line box, not a word
        if not word or conf < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
        confs.append(conf)
    text = "\n".join(" ".join(words) for words in lines.values())
    mean_conf = sum(confs) / len(confs) / 100 if confs else 0.0
    return text, round(mean_conf, 3)


def ocr_if_needed(page, lang=LANG,config=CONFIG):
    # pages from a digital pdf already have exact text
    if page["source"] != "ocr":
        return page
    text, conf = ocr_image(page["image"], lang,config)
    page["text"] = text
    page["ocr_conf"] = conf
    return page


if __name__ == "__main__":
    pdf_path = Path(sys.argv[1])
    for p in ingest(pdf_path):
        p = ocr_if_needed(p)
        lines = p["text"].strip().splitlines()
        first = lines[0][:50] if lines else "(no text)"
        print(p["page_num"], p["source"], p["ocr_conf"], len(p["text"]), "chars |", first)