"""
Scrape official FIFA men's ranking snapshots.

Usage:
    python src/02_scrape_fifa_rankings.py

Output:
    data/raw/fifa/rankings/dates.json
    data/raw/fifa/rankings/snapshots/<date_id>.json
    data/raw/fifa/rankings/rankings.csv
"""

import argparse
import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_sources.fifa_rankings import (
    extract_ranking_dates,
    fetch_ranking_snapshot,
    http_get_text,
    load_json,
    polite_sleep,
    ranking_payload_to_rows,
    write_json,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


CONFIG_PATH = BASE_DIR / "config" / "fifa_rankings.json"
OUT_DIR = BASE_DIR / "data" / "raw" / "fifa" / "rankings"
SNAPSHOT_DIR = OUT_DIR / "snapshots"
CSV_PATH = OUT_DIR / "rankings.csv"


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Download the FIFA ranking page again instead of using the cached HTML.",
    )
    args = parser.parse_args()

    config = load_json(CONFIG_PATH)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    page_path = OUT_DIR / "ranking_page.html"
    if page_path.exists() and not args.refresh:
        page_html = page_path.read_text(encoding="utf-8")
        print("FIFA ranking page: [cache]")
    else:
        page_html = http_get_text(config["ranking_page_url"])
        page_path.write_text(page_html, encoding="utf-8")
        print("FIFA ranking page: downloaded")

    dates = extract_ranking_dates(page_html, start_year=config.get("start_year"))
    if not dates:
        raise RuntimeError("No ranking dates found in FIFA ranking page")

    write_json(OUT_DIR / "dates.json", dates)
    print(f"Ranking dates found since {config.get('start_year')}: {len(dates)}")

    rows: list[dict] = []
    for index, date_meta in enumerate(dates, start=1):
        date_id = date_meta["date_id"]
        snapshot_path = SNAPSHOT_DIR / f"{date_id}.json"
        if snapshot_path.exists():
            payload = load_json(snapshot_path)
            print(f"  [{index}/{len(dates)}] {date_id} {date_meta['ranking_date'] if 'ranking_date' in date_meta else date_meta['iso'][:10]} [cache]")
        else:
            payload = fetch_ranking_snapshot(
                config["ranking_api_url"],
                date_id,
                gender=config.get("gender", "men"),
                locale=config.get("locale", "en"),
            )
            write_json(snapshot_path, payload)
            print(f"  [{index}/{len(dates)}] {date_id} {date_meta['iso'][:10]} downloaded")
            polite_sleep(0.2)
        rows.extend(ranking_payload_to_rows(payload, date_meta))

    rows = sorted(rows, key=lambda row: (row["ranking_date"], row["rank"] or 9999, row["country_code"] or ""))
    write_csv(CSV_PATH, rows)
    print(f"\nListo: {len(rows)} filas de ranking FIFA.")
    print(f"CSV: {CSV_PATH}")


if __name__ == "__main__":
    main()
