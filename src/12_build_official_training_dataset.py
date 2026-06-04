"""
Build a weighted training dataset from official international matches.

Usage:
    python src/12_build_official_training_dataset.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from features.training_dataset import build_training_dataset, read_csv, write_csv


MATCHES_PATH = BASE_DIR / "data" / "raw" / "sofascore" / "official_international" / "matches.csv"
RANKINGS_PATH = BASE_DIR / "data" / "raw" / "fifa" / "rankings" / "rankings.csv"
HISTORY_PATH = BASE_DIR / "data" / "processed" / "features" / "world_cup_team_history.csv"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "training" / "official_international_matches_1998_2024.csv"


def main() -> None:
    if not MATCHES_PATH.exists():
        raise RuntimeError(
            f"Missing official matches file: {MATCHES_PATH}. "
            "Run src/11_scrape_official_international_matches.py first."
        )
    dataset = build_training_dataset(
        read_csv(MATCHES_PATH),
        read_csv(RANKINGS_PATH),
        read_csv(HISTORY_PATH),
        min_year=1998,
        max_year=2024,
    )
    write_csv(OUTPUT_PATH, dataset)
    print(f"Rows: {len(dataset)}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
