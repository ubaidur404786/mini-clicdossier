import sys
from pathlib import Path

import pymupdf
from PIL import Image

DPI = 300
MIN_CHARS=50

def page_to_image(page, dpi=DPI):
    # gray is enough for ocr and uses 3x less memory than rgb
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    return Image.frombytes("L", (pix.width, pix.height), pix.samples)


def ingest(pdf_path, dpi=DPI):
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text()
            #real documents have more than 50 characters of text, so if the page has less than that, we assume it's a footer by any scanner app or software that adds it
            if len(text.strip())>=MIN_CHARS:
                # the pdf already has text, no ocr needed
                image = None
                source = "pdf_text"
            else:
                image = page_to_image(page, dpi)
                source = "ocr"
            pages.append({
                "page_num": i + 1,
                "text": text if source == "pdf_text" else "",
                "image": image,
                "source": source,
                "ocr_conf": None,
                "doc_type": None,
                "type_conf": None,
            })
    return pages


if __name__ == "__main__":
    pdf_path = Path(sys.argv[1])
    for p in ingest(pdf_path):
        size = p["image"].size if p["image"] else None
        print(p["page_num"], p["source"], len(p["text"]), "chars", size)