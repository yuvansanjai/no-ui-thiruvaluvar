import os
import sys
import json
import re
import sqlite3
import requests

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DATA_DIR, "thirukkural.db")
THIRUKKURAL_JSON_PATH = os.path.join(DATA_DIR, "thirukkural.json")
DETAIL_JSON_PATH = os.path.join(DATA_DIR, "detail.json")
LICENSE_PATH = os.path.join(DATA_DIR, "DATASET_LICENSE.txt")

SOURCE_REPO = "https://github.com/tk120404/thirukkural"
THIRUKKURAL_URL = "https://raw.githubusercontent.com/tk120404/thirukkural/master/thirukkural.json"
DETAIL_URL = "https://raw.githubusercontent.com/tk120404/thirukkural/master/detail.json"
LICENSE_URL = "https://raw.githubusercontent.com/tk120404/thirukkural/master/LICENSE"

def normalize_tamil(text: str) -> str:
    """Normalize Tamil text: remove punctuation, unify whitespace, strip extra marks."""
    if not text:
        return ""
    # Remove punctuation & symbols
    t = re.sub(r"[.,\/#!$%\^&\*;:{}=\-_`~()\"\'\?\।\॥]", " ", text)
    # Remove zero-width spaces / joiners if any
    t = re.sub(r"[\u200b-\u200d\ufeff]", "", t)
    # Replace multiple whitespace with single space
    t = re.sub(r"\s+", " ", t).strip()
    return t

def download_data():
    print(f"Downloading dataset from {SOURCE_REPO}...")
    if not os.path.exists(THIRUKKURAL_JSON_PATH):
        r = requests.get(THIRUKKURAL_URL, timeout=30)
        r.raise_for_status()
        with open(THIRUKKURAL_JSON_PATH, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"Saved {THIRUKKURAL_JSON_PATH}")
    else:
        print(f"Using existing {THIRUKKURAL_JSON_PATH}")

    if not os.path.exists(DETAIL_JSON_PATH):
        r = requests.get(DETAIL_URL, timeout=30)
        r.raise_for_status()
        with open(DETAIL_JSON_PATH, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"Saved {DETAIL_JSON_PATH}")
    else:
        print(f"Using existing {DETAIL_JSON_PATH}")

    if not os.path.exists(LICENSE_PATH):
        r = requests.get(LICENSE_URL, timeout=30)
        r.raise_for_status()
        with open(LICENSE_PATH, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"Saved {LICENSE_PATH}")

def build_database():
    download_data()

    with open(THIRUKKURAL_JSON_PATH, "r", encoding="utf-8") as f:
        kural_data = json.load(f)
    with open(DETAIL_JSON_PATH, "r", encoding="utf-8") as f:
        detail_data = json.load(f)

    # Build adhikaram mapping from detail_data
    # detail_data is [{'tamil': 'திருக்குறள்', 'section': {'detail': [...]}}]
    adhikaram_map = {} # adhikaram_no -> (adhikaram_name, paal)
    paal_counts = {}

    root = detail_data[0] if isinstance(detail_data, list) else detail_data
    sections = root.get("section", {}).get("detail", [])
    for sec in sections:
        paal_name = sec.get("name")
        paal_counts[paal_name] = 0
        for grp in sec.get("chapterGroup", {}).get("detail", []):
            for ch in grp.get("chapters", {}).get("detail", []):
                no = ch.get("number")
                name = ch.get("name")
                adhikaram_map[no] = (name, paal_name)

    # Process kurals
    kurals_list = kural_data.get("kural", []) if isinstance(kural_data, dict) else kural_data
    print(f"\nTotal raw kurals loaded: {len(kurals_list)}")
    print(f"Total adhikarams mapped: {len(adhikaram_map)}")

    # Setup SQLite database
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE kural (
            number INTEGER PRIMARY KEY,
            adhikaram_no INTEGER NOT NULL,
            adhikaram_name TEXT NOT NULL,
            paal TEXT NOT NULL,
            line1 TEXT NOT NULL,
            line2 TEXT NOT NULL,
            meaning_ta TEXT NOT NULL,
            normalized_text TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX idx_kural_adhikaram ON kural(adhikaram_no)")
    cur.execute("CREATE INDEX idx_kural_paal ON kural(paal)")

    records = []
    adhikaram_kural_count = {}

    for item in kurals_list:
        num = item.get("Number")
        line1 = item.get("Line1", "").strip()
        line2 = item.get("Line2", "").strip()
        # Prefer Dr. Mu. Varadarajanar meaning (mv), fallback to Solomon Pappaiah (sp)
        meaning = item.get("mv", "") or item.get("sp", "") or item.get("mk", "")
        meaning = meaning.strip()

        # Math check: kural 1-10 is adhikaram 1, 11-20 is 2, etc.
        calc_adhikaram_no = (num - 1) // 10 + 1
        adh_info = adhikaram_map.get(calc_adhikaram_no)
        if not adh_info:
            raise ValueError(f"Adhikaram info missing for kural {num} (adhikaram {calc_adhikaram_no})")
        adh_name, paal = adh_info

        adhikaram_kural_count[calc_adhikaram_no] = adhikaram_kural_count.get(calc_adhikaram_no, 0) + 1
        paal_counts[paal] = paal_counts.get(paal, 0) + 1

        norm_line1 = normalize_tamil(line1)
        norm_line2 = normalize_tamil(line2)
        norm_text = f"{norm_line1} {norm_line2}".strip()

        records.append((num, calc_adhikaram_no, adh_name, paal, line1, line2, meaning, norm_text))

    cur.executemany("""
        INSERT INTO kural (number, adhikaram_no, adhikaram_name, paal, line1, line2, meaning_ta, normalized_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, records)
    conn.commit()

    # Run Verification
    print("=" * 60)
    print("DATASET VERIFICATION REPORT")
    print("=" * 60)
    cur.execute("SELECT COUNT(*) FROM kural")
    total_db_kurals = cur.fetchone()[0]
    print(f"Total Kurals in DB: {total_db_kurals} (Expected: 1330)")
    assert total_db_kurals == 1330, f"Expected 1330 kurals, found {total_db_kurals}"

    cur.execute("SELECT COUNT(DISTINCT adhikaram_no) FROM kural")
    total_adhikarams = cur.fetchone()[0]
    print(f"Total Adhikarams: {total_adhikarams} (Expected: 133)")
    assert total_adhikarams == 133, f"Expected 133 adhikarams, found {total_adhikarams}"

    # Verify each adhikaram has exactly 10 kurals
    for adh_no, count in sorted(adhikaram_kural_count.items()):
        if count != 10:
            raise AssertionError(f"Adhikaram {adh_no} has {count} kurals (expected 10)")
    print("All 133 Adhikarams verified: each has exactly 10 Kurals.")

    # Paal distribution
    print("\nPaal Distribution:")
    for p, c in paal_counts.items():
        print(f"  - {p}: {c} kurals ({c // 10} adhikarams)")
    assert paal_counts.get("அறத்துப்பால்") == 380
    assert paal_counts.get("பொருட்பால்") == 700
    assert paal_counts.get("காமத்துப்பால்") == 250

    # Spot checks: Kural 1 and Kural 150
    print("\n--- Spot-Check: Kural 1 ---")
    cur.execute("SELECT number, adhikaram_no, adhikaram_name, paal, line1, line2, meaning_ta FROM kural WHERE number = 1")
    k1 = cur.fetchone()
    print(f"Number: {k1[0]}")
    print(f"Adhikaram: {k1[1]} ({k1[2]}) | Paal: {k1[3]}")
    print(f"Line 1: {k1[4]}")
    print(f"Line 2: {k1[5]}")
    print(f"Meaning: {k1[6]}")
    assert "அகர முதல" in k1[4], "Kural 1 line1 mismatch"
    assert "பகவன் முதற்றே உலகு" in k1[5], "Kural 1 line2 mismatch"

    print("\n--- Spot-Check: Kural 150 ---")
    cur.execute("SELECT number, adhikaram_no, adhikaram_name, paal, line1, line2, meaning_ta FROM kural WHERE number = 150")
    k150 = cur.fetchone()
    print(f"Number: {k150[0]}")
    print(f"Adhikaram: {k150[1]} ({k150[2]}) | Paal: {k150[3]}")
    print(f"Line 1: {k150[4]}")
    print(f"Line 2: {k150[5]}")
    print(f"Meaning: {k150[6]}")
    assert "அறன்வரையான்" in k150[4], "Kural 150 line1 mismatch"
    assert "பெண்மை நயவாமை நன்று" in k150[5], "Kural 150 line2 mismatch"

    conn.close()
    print("\nVerification PASSED! Database successfully built at:")
    print(DB_PATH)

if __name__ == "__main__":
    build_database()
