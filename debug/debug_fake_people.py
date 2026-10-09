import json
from collections import Counter

from src.generate.fake_people import make_all, save

N_PEOPLE = 30
SEED = 42
SAVE = True  # True writes the json files to data/ground_truth
SHOW_ID = "p001"

people = make_all(N_PEOPLE, SEED)

print("people:", len(people))
print("scenarios:", Counter(p["scenario"] for p in people))
print()

for p in people:
    if p["scenario"] != "ok":
        print(p["person_id"], p["scenario"], p["expected"])
print()

for p in people:
    if p["person_id"] == SHOW_ID:
        print(json.dumps(p, ensure_ascii=False, indent=2))

if SAVE:
    for p in people:
        print("saved", save(p))