from pathlib import Path

import numpy as np
import pytesseract

from src.generate.scan_effects import DPI, has_text, pdf_to_images, scan_look, scanned_people

PDF_PATH = Path("data/generated/fr/p001_payslip.pdf")
MAX_ANGLE = 2.0
MAX_BLUR = 1.2
NOISE_STD = 12
SEED = 7
RUN_OCR = True
OUT_DIR = Path("outputs")

print("scanned people:", [p["person_id"] for p in scanned_people()])
print("has text before:", has_text(PDF_PATH))

rng = np.random.default_rng(SEED)
clean = pdf_to_images(PDF_PATH)[0]
scanned = scan_look(clean, rng, MAX_ANGLE, MAX_BLUR, NOISE_STD)
print("size:", clean.size, "->", scanned.size, "| mode:", clean.mode, "->", scanned.mode)

OUT_DIR.mkdir(exist_ok=True)
clean.save(OUT_DIR / "debug_clean.png")
scanned.save(OUT_DIR / "debug_scanned.png")
out_pdf = OUT_DIR / "debug_scanned.pdf"
scanned.save(out_pdf, "PDF", resolution=DPI)
print("has text after:", has_text(out_pdf))

if RUN_OCR:
    print("--- ocr clean ---")
    print(pytesseract.image_to_string(clean, lang="fra+eng"))
    print("--- ocr scanned ---")
    print(pytesseract.image_to_string(scanned, lang="fra+eng"))