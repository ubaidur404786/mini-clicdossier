import json
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageFilter

GT_DIR = Path("data/ground_truth")
GEN_DIR = Path("data/generated")
LANGS = ["fr", "en"]

DPI = 200
MAX_ANGLE = 2.0   # degrees, both directions
MAX_BLUR = 1.2    # gaussian blur radius in pixels
NOISE_STD = 12    # pixel noise on a 0-255 scale
SEED = 7


def pdf_to_images(path, dpi=DPI):
    images = []
    with pymupdf.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            images.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    return images


def has_text(path):
    with pymupdf.open(path) as doc:
        return any(page.get_text().strip() for page in doc)


def add_noise(img, std, rng):
    arr = np.array(img).astype(np.float32)
    arr = arr + rng.normal(0, std, arr.shape)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def scan_look(img, rng, max_angle=MAX_ANGLE, max_blur=MAX_BLUR, noise_std=NOISE_STD):
    img = img.convert("L")
    angle = rng.uniform(-max_angle, max_angle)
    # white fill so the corners don't turn black after rotation
    img = img.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255)
    blur = rng.uniform(0.3, max_blur)
    img = img.filter(ImageFilter.GaussianBlur(blur))
    img = add_noise(img, noise_std, rng)
    return img


def scan_pdf(path, rng):
    images = [scan_look(img, rng) for img in pdf_to_images(path)]
    # image-only pdf, no text layer, like a real scan
    images[0].save(path, "PDF", resolution=DPI, save_all=True, append_images=images[1:])


def scanned_people():
    people = []
    for path in sorted(GT_DIR.glob("p*.json")):
        with open(path, encoding="utf-8") as f:
            person = json.load(f)
        if person["scenario"] == "scanned":
            people.append(person)
    return people


def scan_person(person, rng):
    done = []
    for lang in LANGS:
        for doc_type in person["documents"]:
            path = GEN_DIR / lang / f"{person['person_id']}_{doc_type}.pdf"
            # no text left means it was already scanned, don't blur it twice
            if not has_text(path):
                continue
            scan_pdf(path, rng)
            done.append(path)
    return done


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    for person in scanned_people():
        for path in scan_person(person, rng):
            print("scanned", path)