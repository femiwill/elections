"""
Import GPS coordinates from mykeels/inec-polling-units dataset.

Since our DB has generic PU names that don't match the real INEC names,
we match at the LGA level: compute the centroid of all PUs with coordinates
in each LGA from the CSV, then assign that centroid to all PUs in the
matching LGA in our database.

This gives users approximate navigation to the right area (~3-10km accuracy).
"""

import csv
import sqlite3
import re
import sys
from collections import defaultdict

CSV_PATH = "data/polling_units_gps.csv"
DB_PATH = "instance/elections.db"

# State name mapping: CSV → DB
STATE_MAP = {
    "ABIA": "Abia",
    "ADAMAWA": "Adamawa",
    "AKWA IBOM": "Akwa Ibom",
    "ANAMBRA": "Anambra",
    "BAUCHI": "Bauchi",
    "BAYELSA": "Bayelsa",
    "BENUE": "Benue",
    "BORNO": "Borno",
    "CROSS RIVER": "Cross River",
    "DELTA": "Delta",
    "EBONYI": "Ebonyi",
    "EDO": "Edo",
    "EKITI": "Ekiti",
    "ENUGU": "Enugu",
    "FEDERAL CAPITAL TERRITORY": "FCT",
    "GOMBE": "Gombe",
    "IMO": "Imo",
    "JIGAWA": "Jigawa",
    "KADUNA": "Kaduna",
    "KANO": "Kano",
    "KATSINA": "Katsina",
    "KEBBI": "Kebbi",
    "KOGI": "Kogi",
    "KWARA": "Kwara",
    "LAGOS": "Lagos",
    "NASARAWA": "Nasarawa",
    "NIGER": "Niger",
    "OGUN": "Ogun",
    "ONDO": "Ondo",
    "OSUN": "Osun",
    "OYO": "Oyo",
    "PLATEAU": "Plateau",
    "RIVERS": "Rivers",
    "SOKOTO": "Sokoto",
    "TARABA": "Taraba",
    "YOBE": "Yobe",
    "ZAMFARA": "Zamfara",
}


def normalize_lga(name):
    """Normalize LGA name for matching."""
    name = name.upper().strip()
    name = re.sub(r'\s+', ' ', name)
    # Remove parenthetical suffixes like (UQUO)
    name = re.sub(r'\s*\(.*?\)', '', name)
    # Normalize slashes and dashes to spaces
    name = name.replace('/', ' ').replace('-', ' ')
    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


# Manual LGA name mapping: (DB state, DB LGA normalized) → CSV LGA normalized
# For cases where names differ between our DB and the CSV
LGA_ALIASES = {
    # Abia
    ("Abia", "OBI NGWA"): "OBINGWA",
    ("Abia", "OSISIOMA NGWA"): "OSISIOMA",
    ("Abia", "UMU NNEOCHI"): "UMUNNEOCHI",
    # Adamawa
    ("Adamawa", "GAYUK"): "GUYUK",
    ("Adamawa", "GRIE"): "GIRE 1",
    ("Adamawa", "MAYO BELWA"): "MAYO-BELWA",
    # Akwa Ibom
    ("Akwa Ibom", "ESIT EKET"): "ESIT EKET",
    # Anambra
    ("Anambra", "IHIALA"): "IHALA",
    ("Anambra", "ONITSHA SOUTH"): "ONITSHA -SOUTH",
    # Bauchi
    ("Bauchi", "DAMBAN"): "DAMBAM",
    # Borno
    ("Borno", "MAIDUGURI"): "MAIDUGURI M. C.",
    # Cross River
    ("Cross River", "CALABAR MUNICIPAL"): "CALABAR MUNICIPALITY",
    # Delta
    ("Delta", "ANIOCHA SOUTH"): "ANIOCHA SOUTH",
    ("Delta", "IKA NORTH EAST"): "IKA NORTH EAST",
    ("Delta", "IKA SOUTH"): "IKA SOUTH",
    ("Delta", "OSHIMILI NORTH"): "OSHIMILI NORTH",
    ("Delta", "OSHIMILI SOUTH"): "OSHIMILI SOUTH",
    # Edo
    ("Edo", "UHUNMWONDE"): "UHUNMWODE",
    # Gombe
    ("Gombe", "YAMALTU DEBA"): "YALMALTU DEBA",
    # Imo - many mismatches
    ("Imo", "IHITTE/UBOMA"): "IHITTE/UBOMA",
    ("Imo", "IKEDURU"): "IKEDURU",
    ("Imo", "ISIALA MBANO"): "ISIALA MBANO",
    ("Imo", "ISU"): "ISU",
    ("Imo", "MBAITOLI"): "MBAITOLI",
    ("Imo", "NGOR OKPALA"): "NGOR OKPALA",
    ("Imo", "NJABA"): "NJABA",
    ("Imo", "NWANGELE"): "NWANGELE",
    ("Imo", "OBOWO"): "OBOWO",
    ("Imo", "OGUTA"): "OGUTA",
    ("Imo", "OHAJI/EGBEMA"): "OHAJI/EGBEMA",
    ("Imo", "OKIGWE"): "OKIGWE",
    ("Imo", "ONUIMO"): "ONUIMO",
    ("Imo", "ORSU"): "ORSU",
    ("Imo", "ORU WEST"): "ORU WEST",
    ("Imo", "OWERRI NORTH"): "OWERRI NORTH",
    ("Imo", "OWERRI WEST"): "OWERRI WEST",
    # Jigawa
    ("Jigawa", "BIRINIWA"): "BIRNIWA",
    ("Jigawa", "KIRI KASAMA"): "KIRIKA SAMMA",
    # Kano
    ("Kano", "DAMBATTA"): "DANBATA",
    ("Kano", "DAWAKIN KUDU"): "DAWAKI KUDU",
    ("Kano", "DAWAKIN TOFA"): "DAWAKI TOFA",
    ("Kano", "GARUN MALLAM"): "GARUN MALAM",
    # Katsina
    ("Katsina", "MALUMFASHI"): "MALUFASHI",
    # Kebbi
    ("Kebbi", "ALEIRO"): "ALIERO",
    ("Kebbi", "AREWA DANDI"): "AREWA",
    # Kogi
    ("Kogi", "KOTON KARFE"): "KOGI . K. K.",
    ("Kogi", "MOPA MURO"): "MOPA MORO",
    ("Kogi", "OGORI MAGONGO"): "OGORI MANGOGO",
    # Kwara
    ("Kwara", "OKE ERO"): "OKE ERO",
    ("Kwara", "PATEGI"): "PATIGI",
    # Lagos
    ("Lagos", "IFAKO IJAIYE"): "IFAKO-IJAYE",
    ("Lagos", "SHOMOLU"): "SOMOLU",
    # Ogun
    ("Ogun", "OGUN WATERSIDE"): "OGUN WATERSIDE",
    # Ondo
    ("Ondo", "ILE OLUJI/OKEIGBO"): "ILE OLUJI/OKE IGBO",
    # Osun
    ("Osun", "AIYEDAADE"): "AYEDAADE",
    ("Osun", "AIYEDIRE"): "AYEDIRE",
    ("Osun", "ATAKUNMOSA EAST"): "ATAKUMOSA EAST",
    ("Osun", "ATAKUNMOSA WEST"): "ATAKUMOSA WEST",
    # Oyo
    ("Oyo", "OGBOMOSHO NORTH"): "OGBOMOSO NORTH",
    ("Oyo", "OGBOMOSHO SOUTH"): "OGBOMOSO SOUTH",
    ("Oyo", "ORELOPE"): "OORELOPE",
    ("Oyo", "SAKI EAST"): "SAKI EAST",
    ("Oyo", "SAKI WEST"): "SAKI WEST",
    ("Oyo", "SURULERE"): "SURULERE",
    # FCT
    ("FCT", "MUNICIPAL AREA COUNCIL (AMAC)"): "MUNICIPAL AREA COUNCIL",
}


def build_lga_centroids():
    """Read CSV and compute LGA centroids (average lat/lng of all PUs with coords)."""
    lga_coords = defaultdict(list)  # (db_state_name, normalized_lga) -> [(lat, lng)]

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat_str = row.get('location.latitude', '').strip()
            lng_str = row.get('location.longitude', '').strip()
            if not lat_str or not lng_str:
                continue
            try:
                lat = float(lat_str)
                lng = float(lng_str)
            except ValueError:
                continue
            # Validate Nigeria bounds
            if not (3.0 < lat < 15.0 and 2.0 < lng < 16.0):
                continue

            csv_state = row['state_name'].strip()
            db_state = STATE_MAP.get(csv_state)
            if not db_state:
                continue

            csv_lga = normalize_lga(row['local_government_name'])
            lga_coords[(db_state, csv_lga)].append((lat, lng))

    # Compute centroids
    centroids = {}
    for key, coords in lga_coords.items():
        avg_lat = sum(c[0] for c in coords) / len(coords)
        avg_lng = sum(c[1] for c in coords) / len(coords)
        centroids[key] = (avg_lat, avg_lng, len(coords))

    return centroids


def import_coordinates():
    """Match DB LGAs to CSV centroids and update PU coordinates."""
    print("Building LGA centroids from CSV...")
    centroids = build_lga_centroids()
    print(f"  Found {len(centroids)} LGAs with coordinate data")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Get all LGAs from our DB with state names
    c.execute("""
        SELECT l.id, l.name, s.name
        FROM lgas l JOIN states s ON l.state_id = s.id
    """)
    db_lgas = c.fetchall()

    matched = 0
    unmatched = []
    total_pus_updated = 0

    # Build a lookup index for CSV centroids by state
    csv_by_state = defaultdict(dict)
    for (cs, cl), val in centroids.items():
        csv_by_state[cs][cl] = val

    for lga_id, lga_name, state_name in db_lgas:
        norm_lga = normalize_lga(lga_name)
        key = (state_name, norm_lga)

        # Try direct match
        centroid = centroids.get(key)

        # Try alias mapping
        if not centroid and key in LGA_ALIASES:
            alias = normalize_lga(LGA_ALIASES[key])
            centroid = centroids.get((state_name, alias))

        # Try fuzzy: remove all non-alphanumeric and compare
        if not centroid:
            clean_db = re.sub(r'[^A-Z0-9]', '', norm_lga)
            for cl, val in csv_by_state.get(state_name, {}).items():
                clean_csv = re.sub(r'[^A-Z0-9]', '', cl)
                if clean_db == clean_csv:
                    centroid = val
                    break

        if centroid:
            lat, lng, src_count = centroid
            c.execute("""
                UPDATE polling_units
                SET latitude = ?, longitude = ?
                WHERE ward_id IN (SELECT id FROM wards WHERE lga_id = ?)
                  AND latitude IS NULL
            """, (lat, lng, lga_id))
            total_pus_updated += c.rowcount
            matched += 1
        else:
            unmatched.append((state_name, lga_name, norm_lga))

    conn.commit()

    print(f"\nResults:")
    print(f"  Matched LGAs: {matched}/{len(db_lgas)}")
    print(f"  PUs updated: {total_pus_updated:,}")

    if unmatched:
        print(f"\n  Unmatched LGAs ({len(unmatched)}):")
        for state, lga, norm in unmatched:
            # Show available CSV LGAs for that state
            avail = [cl for (cs, cl) in centroids if cs == state]
            print(f"    {state} / {lga} (norm: {norm})")
            if avail:
                print(f"      Available in CSV: {', '.join(sorted(avail)[:5])}...")

    # Show coverage
    c.execute("SELECT COUNT(*) FROM polling_units WHERE latitude IS NOT NULL")
    with_coords = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM polling_units")
    total = c.fetchone()[0]
    print(f"\nOverall coverage: {with_coords:,}/{total:,} ({with_coords/total*100:.1f}%)")

    conn.close()


if __name__ == "__main__":
    import_coordinates()
