"""
Generate data/precincts.csv — a first-pass precinct label for each of the 87
balanced-panel sensors, for a human to correct.

The labels below are inferred from sensor descriptions and coordinates by
someone who has never been to Melbourne. Treat every one of them as a guess.
The `confidence` column flags which ones most need your eyes:

    high  - description is unambiguous (e.g. "Building 80 RMIT")
    med   - reasonable inference from street and position
    low   - genuinely unsure, please check

Re-run this to regenerate. It will NOT overwrite an existing precincts.csv
unless you pass --force, so your edits are safe.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "precincts.csv"

# location_id -> (precinct, confidence)
LABELS = {
    # --- office ------------------------------------------------------------
    39:  ("office", "high"),      # Alfred Place, off Collins
    18:  ("office", "high"),      # Collins Place (North)
    17:  ("office", "high"),      # Collins Place (South)
    53:  ("office", "high"),      # Collins Street (North)
    137: ("office", "high"),      # NAB Building, Docklands
    131: ("office", "high"),      # King & Flinders
    132: ("office", "high"),      # King & La Trobe
    107: ("office", "high"),      # Royal Mint, 280 William St
    58:  ("office", "med"),       # Bourke & Spencer (North)
    167: ("office", "med"),       # 526 La Trobe St (crossing)
    164: ("office", "med"),       # 526 La Trobe St (footpath)
    130: ("office", "med"),       # 892 Bourke St, Docklands
    109: ("office", "med"),       # La Trobe & William (South)
    40:  ("office", "med"),       # Lonsdale & Spring — government precinct
    36:  ("office", "med"),       # Queen St (West)
    24:  ("office", "med"),       # Spencer & Collins (North)
    23:  ("office", "med"),       # Spencer & Collins (South)
    75:  ("office", "med"),       # Spring & Flinders (West)
    71:  ("office", "med"),       # Westwood Place
    118: ("office", "low"),       # 114 Flinders St car park crossing
    117: ("office", "low"),       # 114 Flinders St car park footpath
    21:  ("office", "low"),       # 155-161 Russell St
    165: ("office", "low"),       # 475 Spencer St
    141: ("office", "low"),       # 474 Flinders St awning
    62:  ("office", "low"),       # La Trobe St (North)
    30:  ("office", "low"),       # Lonsdale St (South)

    # --- retail ------------------------------------------------------------
    2:   ("retail", "high"),      # Bourke Street Mall (South)
    3:   ("retail", "high"),      # Melbourne Central
    47:  ("retail", "high"),      # Melbourne Central - Elizabeth St
    27:  ("retail", "high"),      # QV Market - Peel St
    48:  ("retail", "high"),      # QVM - Queen St
    49:  ("retail", "high"),      # QVM - Therry St
    63:  ("retail", "med"),       # 231 Bourke St
    52:  ("retail", "med"),       # Elizabeth & Lonsdale (South)
    45:  ("retail", "med"),       # Little Collins & Swanston
    56:  ("retail", "med"),       # Lonsdale & Elizabeth (North)
    51:  ("retail", "med"),       # QVM - Franklin St
    4:   ("retail", "med"),       # Town Hall (West)
    162: ("retail", "med"),       # 489 Elizabeth St

    # --- university --------------------------------------------------------
    59:  ("university", "high"),  # Building 80 RMIT
    61:  ("university", "high"),  # RMIT Building 14
    42:  ("university", "high"),  # Grattan & Swanston — Melbourne Uni
    43:  ("university", "high"),  # Monash Rd & Swanston
    44:  ("university", "high"),  # Tin Alley & Swanston
    46:  ("university", "med"),   # Pelham St (South)

    # --- entertainment -----------------------------------------------------
    142: ("entertainment", "high"),  # Hamer Hall entrance
    20:  ("entertainment", "high"),  # Chinatown - Lt Bourke
    69:  ("entertainment", "high"),  # Flinders Ln & Degraves (crossing)
    68:  ("entertainment", "high"),  # Flinders Ln & Degraves (North)
    67:  ("entertainment", "high"),  # Flinders Ln & Degraves (South)
    72:  ("entertainment", "high"),  # Flinders St - ACMI
    37:  ("entertainment", "high"),  # Lygon St (East)
    31:  ("entertainment", "high"),  # Lygon St (West)
    35:  ("entertainment", "high"),  # Southbank Promenade
    19:  ("entertainment", "med"),   # Chinatown - Swanston
    50:  ("entertainment", "med"),   # Faraday & Lygon
    25:  ("entertainment", "med"),   # Convention & Exhibition Centre
    41:  ("entertainment", "low"),   # Flinders Ln & Swanston

    # --- transport ---------------------------------------------------------
    6:   ("transport", "high"),   # Flinders Underpass - Myki barriers
    209: ("transport", "high"),   # Flinders Underpass - walkway
    9:   ("transport", "high"),   # Southern Cross Station
    134: ("transport", "high"),   # Southern Cross - Bourke St North
    135: ("transport", "high"),   # Southern Cross - Bourke St South
    133: ("transport", "high"),   # Southern Cross - Lonsdale St South
    84:  ("transport", "med"),    # Elizabeth & Flinders (East)
    79:  ("transport", "med"),    # Flinders St (South)
    5:   ("transport", "low"),    # Princes Bridge — heavy mixed use

    # --- residential -------------------------------------------------------
    87:  ("residential", "high"), # Errol St (West), North Melbourne
    70:  ("residential", "high"), # Errol St (East)
    85:  ("residential", "high"), # Macaulay Rd (North), Kensington
    76:  ("residential", "high"), # Macaulay Rd & Bellair St
    86:  ("residential", "high"), # Queensberry & Errol
    11:  ("residential", "med"),  # Docklands Waterfront City
    77:  ("residential", "med"),  # Harbour Esplanade (West)
    12:  ("residential", "med"),  # New Quay
    66:  ("residential", "med"),  # QV2 Apartments, 300 Swanston
    10:  ("residential", "med"),  # Victoria Point
    8:   ("residential", "med"),  # Webb Bridge
    140: ("residential", "med"),  # Boyd Park, Southbank

    # --- leisure / parks ---------------------------------------------------
    161: ("leisure", "high"),     # Birrarung Marr
    123: ("leisure", "high"),     # Birrarung Marr East
    29:  ("leisure", "high"),     # St Kilda Rd & Alexandra Gardens
    136: ("leisure", "med"),      # Fed Square bridge
    139: ("leisure", "med"),      # Sandridge Bridge signal box
    138: ("leisure", "med"),      # Enterprize Park, Queens Bridge
    14:  ("leisure", "med"),      # Sandridge Bridge
    143: ("leisure", "med"),      # Batman Park, Spencer St
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="overwrite existing precincts.csv")
    args = ap.parse_args()

    if OUT.exists() and not args.force:
        print(f"{OUT.name} already exists — not overwriting your edits.")
        print("Use --force if you really want to regenerate from scratch.")
        return 0

    sensors = pd.read_parquet(ROOT / "data" / "processed" / "balanced_sensors.parquet")

    df = sensors[["location_id", "sensor_description", "latitude", "longitude"]].copy()
    df["precinct"] = df.location_id.map(lambda i: LABELS.get(i, ("UNLABELLED", "none"))[0])
    df["confidence"] = df.location_id.map(lambda i: LABELS.get(i, ("UNLABELLED", "none"))[1])
    df["notes"] = ""

    # Sort so the ones needing attention float to the top.
    order = {"none": 0, "low": 1, "med": 2, "high": 3}
    df = df.sort_values(
        ["confidence", "precinct", "sensor_description"],
        key=lambda c: c.map(order) if c.name == "confidence" else c,
    )

    df.to_csv(OUT, index=False)

    print(f"wrote {OUT.relative_to(ROOT)}  ({len(df)} sensors)\n")
    print(df.precinct.value_counts().to_string())
    n_check = (df.confidence != "high").sum()
    print(f"\n{n_check} sensors marked low/med confidence — these are the ones to check.")
    print("Rows are sorted least-confident first, so start at the top and stop when bored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
