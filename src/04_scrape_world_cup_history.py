"""
Scrape all FIFA World Cup seasons available in SofaScore.

Usage:
    python src/04_scrape_world_cup_history.py

Output:
    data/raw/sofascore/world_cup_history/events/<season_year>.json
    data/raw/sofascore/world_cup_history/matches.csv
"""

import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_sources.sofascore import (
    SofaScoreClient,
    event_to_match_row,
    load_json,
    run,
    write_json,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


TOURNAMENT_ID = 16
TOURNAMENT_NAME = "FIFA World Cup"
OUT_DIR = BASE_DIR / "data" / "raw" / "sofascore" / "world_cup_history"
EVENTS_DIR = OUT_DIR / "events"
MATCHES_PATH = OUT_DIR / "matches.csv"


def write_matches_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


async def scrape_history() -> None:
    rows: list[dict] = []

    async with SofaScoreClient() as client:
        seasons = await client.get_seasons(TOURNAMENT_ID)
        seasons = sorted(seasons, key=lambda season: int(str(season.get("year", "0"))))
        write_json(OUT_DIR / "seasons.json", seasons)
        print(f"World Cup seasons found: {len(seasons)}")

        for season in seasons:
            season_year = str(season.get("year"))
            season_id = season["id"]
            season_name = season.get("name") or season_year
            events_path = EVENTS_DIR / f"{season_year}.json"
            print(f"  {season_year}: {season_name} (id={season_id})")

            if events_path.exists():
                events = load_json(events_path)
                print(f"    [cache] events: {len(events)}")
            else:
                events = await client.get_tournament_events(TOURNAMENT_ID, season_id)
                write_json(events_path, events)
                print(f"    downloaded events: {len(events)}")

            for event in events:
                rows.append(event_to_match_row(event, TOURNAMENT_NAME, season_year, season_id))

    rows = sorted(rows, key=lambda row: (row.get("start_timestamp") or 0, row.get("event_id") or 0))
    write_matches_csv(MATCHES_PATH, rows)
    print(f"\nListo: {len(rows)} eventos historicos.")
    print(f"CSV: {MATCHES_PATH}")


if __name__ == "__main__":
    run(scrape_history())
