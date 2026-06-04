"""
Scrape official international matches from SofaScore.

Usage:
    python src/11_scrape_official_international_matches.py

The script intentionally excludes friendlies by only using tournaments listed in
config/sofascore_official_international.json.
"""

import csv
import sys
from pathlib import Path
from typing import Any

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


CONFIG_PATH = BASE_DIR / "config" / "sofascore_official_international.json"
OUT_DIR = BASE_DIR / "data" / "raw" / "sofascore" / "official_international"
NORMALIZED_PATH = OUT_DIR / "matches.csv"


def safe_dir_name(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.lower()).strip("_")


def write_matches_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


async def scrape_official_international() -> None:
    config = load_json(CONFIG_PATH)
    rows: list[dict[str, Any]] = []

    async with SofaScoreClient(
        api_url=config["api_url"],
        referer=config["referer"],
    ) as client:
        for tournament in config["tournaments"]:
            tournament_name = tournament["name"]
            tournament_id = tournament["unique_tournament_id"]
            competition_group = tournament["competition_group"]
            competition_weight = float(tournament["weight"])
            tournament_dir = OUT_DIR / safe_dir_name(tournament_name)
            print(f"\n{tournament_name} (unique_tournament_id={tournament_id}, weight={competition_weight})")

            for season_year in tournament["seasons"]:
                print(f"  Season {season_year}")
                season_dir = tournament_dir / str(season_year)
                season_meta_path = season_dir / "season_meta.json"
                events_path = season_dir / "events.json"

                if events_path.exists() and season_meta_path.exists():
                    season_meta = load_json(season_meta_path)
                    season_id = int(season_meta["season_id"])
                    season_name = str(season_meta["season_name"])
                    print(f"    [cache] SofaScore season: {season_name} (id={season_id})")
                    events = load_json(events_path)
                    print(f"    [cache] events: {len(events)}")
                else:
                    try:
                        season_id, season_name = await client.get_season_id(tournament_id, season_year)
                    except RuntimeError as exc:
                        print(f"    [skip] {exc}")
                        continue
                    print(f"    SofaScore season: {season_name} (id={season_id})")
                    events = await client.get_tournament_events(tournament_id, season_id)
                    write_json(events_path, events)
                    print(f"    downloaded events: {len(events)}")

                for event in events:
                    row = event_to_match_row(event, tournament_name, season_year, season_id)
                    row["competition_group"] = competition_group
                    row["competition_weight"] = competition_weight
                    rows.append(row)

                write_json(
                    season_meta_path,
                    {
                        "tournament": tournament_name,
                        "competition_group": competition_group,
                        "competition_weight": competition_weight,
                        "unique_tournament_id": tournament_id,
                        "season_year": season_year,
                        "season_id": season_id,
                        "season_name": season_name,
                        "events_count": len(events),
                    },
                )

    rows = sorted(rows, key=lambda row: (row.get("start_timestamp") or 0, row.get("event_id") or 0))
    write_matches_csv(NORMALIZED_PATH, rows)
    print(f"\nListo: {len(rows)} partidos/eventos oficiales normalizados.")
    print(f"CSV: {NORMALIZED_PATH}")
    print(f"Raw: {OUT_DIR}")


if __name__ == "__main__":
    run(scrape_official_international())
