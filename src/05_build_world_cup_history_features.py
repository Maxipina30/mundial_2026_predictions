"""
Build all-time World Cup performance features from historical match data.

Usage:
    python src/05_build_world_cup_history_features.py

Input:
    data/raw/sofascore/world_cup_history/matches.csv

Output:
    data/processed/features/world_cup_team_history.csv
"""

import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from features.world_cup_history import build_world_cup_team_stats


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


INPUT_PATH = BASE_DIR / "data" / "raw" / "sofascore" / "world_cup_history" / "matches.csv"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "features" / "world_cup_team_history.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not INPUT_PATH.exists():
        raise RuntimeError(f"Missing historical World Cup matches file: {INPUT_PATH}")
    rows = read_csv(INPUT_PATH)
    features = build_world_cup_team_stats(rows)
    write_csv(OUTPUT_PATH, features)
    print(f"Teams: {len(features)}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
