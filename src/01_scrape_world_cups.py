"""
Scrape SofaScore events for FIFA World Cup seasons.

Usage:
    python src/01_scrape_world_cups.py

The script stores raw SofaScore event payloads and a normalized matches file under:
    data/raw/sofascore/world_cups/
"""

import csv
import argparse
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


CONFIG_PATH = BASE_DIR / "config" / "sofascore_world_cups.json"
OUT_DIR = BASE_DIR / "data" / "raw" / "sofascore" / "world_cups"
NORMALIZED_PATH = OUT_DIR / "matches.csv"


def write_matches_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


async def scrape_world_cups(refresh: bool = False) -> None:
    config = load_json(CONFIG_PATH)
    rows: list[dict] = []

    async with SofaScoreClient(
        api_url=config["api_url"],
        referer=config["referer"],
    ) as client:
        for tournament in config["tournaments"]:
            tournament_name = tournament["name"]
            tournament_id = tournament["unique_tournament_id"]
            print(f"\n{tournament_name} (unique_tournament_id={tournament_id})")

            for season_year in tournament["seasons"]:
                print(f"  Season {season_year}")
                season_id, season_name = await client.get_season_id(tournament_id, season_year)
                print(f"    SofaScore season: {season_name} (id={season_id})")

                season_dir = OUT_DIR / str(season_year)
                events_path = season_dir / "events.json"
                if events_path.exists() and not refresh:
                    events = load_json(events_path)
                    print(f"    [cache] events: {len(events)}")
                else:
                    events = await client.get_tournament_events(tournament_id, season_id)
                    supplemental_ids = tournament.get("supplemental_event_ids", {}).get(str(season_year), [])
                    for event_id in supplemental_ids:
                        event = await client.get_event(int(event_id))
                        if event and all(item.get("id") != event.get("id") for item in events):
                            events.append(event)
                    events.sort(key=lambda event: event.get("startTimestamp", 0))
                    write_json(events_path, events)
                    print(f"    downloaded events: {len(events)}")

                for event in events:
                    rows.append(event_to_match_row(event, tournament_name, season_year, season_id))

                write_json(
                    season_dir / "season_meta.json",
                    {
                        "tournament": tournament_name,
                        "unique_tournament_id": tournament_id,
                        "season_year": season_year,
                        "season_id": season_id,
                        "season_name": season_name,
                        "events_count": len(events),
                    },
                )

    rows = sorted(rows, key=lambda row: (row.get("start_timestamp") or 0, row.get("event_id") or 0))
    write_matches_csv(NORMALIZED_PATH, rows)
    print(f"\nListo: {len(rows)} partidos/eventos normalizados.")
    print(f"CSV: {NORMALIZED_PATH}")
    print(f"Raw: {OUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Download SofaScore events again instead of using cached season files.",
    )
    args = parser.parse_args()
    run(scrape_world_cups(refresh=args.refresh))
