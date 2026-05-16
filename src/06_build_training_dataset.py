"""
Build the first model training dataset.

Usage:
    python src/06_build_training_dataset.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from features.training_dataset import build_training_dataset, read_csv, write_csv


MATCHES_PATH = BASE_DIR / "data" / "raw" / "sofascore" / "world_cup_history" / "matches.csv"
RANKINGS_PATH = BASE_DIR / "data" / "raw" / "fifa" / "rankings" / "rankings.csv"
HISTORY_PATH = BASE_DIR / "data" / "processed" / "features" / "world_cup_team_history.csv"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "training" / "world_cup_matches_1998_2022.csv"


def main() -> None:
    dataset = build_training_dataset(
        read_csv(MATCHES_PATH),
        read_csv(RANKINGS_PATH),
        read_csv(HISTORY_PATH),
        min_year=1998,
        max_year=2022,
    )
    write_csv(OUTPUT_PATH, dataset)
    print(f"Rows: {len(dataset)}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
