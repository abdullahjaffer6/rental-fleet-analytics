"""Combine yearly Turo trip exports into one anonymized trip table.

Usage:
    python src/clean.py

Reads data/raw/trips_*.csv (Turo "trip earnings" exports, one per year) and
writes data/processed/trips.csv. Guest names, VINs, license plates, owner names
and street addresses are dropped; each car gets a short readable label.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "trips.csv"

# Turo vehicle id -> readable label used everywhere in the project.
CAR_LABELS = {
    "1973030": "Elantra 2023",
    "2108968": "Sportage 2023",
    "2132491": "Civic 2022",
    "2178285": "Expedition 2023",
    "2608639": "Elantra 2024 (white)",
    "2846068": "Navigator 2024",
    "2941347": "Elantra 2024 (black)",
    "3102746": "Mustang 2025",
    "3304474": "Mercedes CLA 2025",
    "3304499": "Aviator 2025",
    "3648997": "Corvette 2026",
    "3843361": "Tahoe 2026",
    "3844860": "Trax 2026 #1",
    "3844880": "Trax 2026 #2",
}

# Money columns Turo exports as text like "$1,234.50" or "- 10.40".
MONEY_COLS = [
    "Trip price", "Boost price", "3-day discount", "1-week discount",
    "2-week discount", "3-week discount", "1-month discount", "2-month discount",
    "3-month discount", "Non-refundable discount", "Early bird discount",
    "Host promotional credit", "Delivery", "Excess distance", "Extras",
    "Cancellation fee", "Additional usage", "Late fee", "Improper return fee",
    "Airport operations fee", "Airport parking credit", "Tolls & tickets",
    "On-trip EV charging", "Post-trip EV charging", "Smoking", "Cleaning",
    "Fines (paid to host)", "Gas reimbursement", "Gas fee", "Other fees",
    "Sales tax", "Total earnings",
]

DROP_COLS = ["Guest", "Vehicle", "VIN", "Vehicle name", "Pickup location",
             "Return location", "Reservation ID"]


def to_money(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.str.replace(r"[$,\s]", "", regex=True), errors="coerce").fillna(0.0)


def location_type(addr: pd.Series) -> pd.Series:
    addr = addr.fillna("")
    out = pd.Series("Other delivery", index=addr.index)
    out[addr.str.contains("Ann Arbor", case=False)] = "Ann Arbor"
    out[addr.str.contains("Airport", case=False)] = "DTW Airport"
    return out


def main() -> None:
    frames = [pd.read_csv(f, dtype=str) for f in sorted(RAW.glob("trips_*.csv"))]
    df = pd.concat(frames, ignore_index=True)
    # Yearly exports overlap by a few days at the edges; keep one row per reservation.
    df = df.drop_duplicates("Reservation ID", keep="last")

    unknown = set(df["Vehicle id"]) - set(CAR_LABELS)
    if unknown:
        raise ValueError(f"Add a label for these vehicle ids: {sorted(unknown)}")

    for c in MONEY_COLS:
        df[c] = to_money(df[c])
    for c in ["Trip start", "Trip end"]:
        df[c] = pd.to_datetime(df[c], format="%Y-%m-%d %I:%M %p")
    for c in ["Trip days", "Distance traveled", "Check-in odometer", "Check-out odometer"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["car"] = df["Vehicle id"].map(CAR_LABELS)
    df["pickup_type"] = location_type(df["Pickup location"])
    df = df.drop(columns=DROP_COLS + ["Vehicle id"])
    df.columns = [c.lower().replace(" & ", "_").replace(" ", "_").replace("-", "_")
                  for c in df.columns]
    df = df.sort_values("trip_start").reset_index(drop=True)
    df.insert(0, "trip_id", range(1, len(df) + 1))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df):,} trips ({(df.trip_status == 'Completed').sum():,} completed) to {OUT}")


if __name__ == "__main__":
    main()
