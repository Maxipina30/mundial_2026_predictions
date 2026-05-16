"""
Prepare normalized World Cup 2026 inputs for the simulator.

Usage:
    python src/03_prepare_world_cup_2026_inputs.py

Input:
    data/raw/sofascore/world_cups/matches.csv

Output:
    data/interim/world_cup_2026/fixtures.csv
    data/interim/world_cup_2026/groups.csv
    data/interim/world_cup_2026/teams.csv
"""

import csv
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


BASE_DIR = Path(__file__).resolve().parents[1]
MATCHES_PATH = BASE_DIR / "data" / "raw" / "sofascore" / "world_cups" / "matches.csv"
OUT_DIR = BASE_DIR / "data" / "interim" / "world_cup_2026"


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


def team_row(match: dict[str, str], side: str) -> dict[str, str]:
    return {
        "team": match[f"{side}_team"],
        "team_id": match[f"{side}_team_id"],
        "name_code": match[f"{side}_name_code"],
        "country_code": match[f"{side}_country_code"],
        "group_sign": match["group_sign"],
        "sofascore_ranking": match[f"{side}_sofascore_ranking"],
    }


def main() -> None:
    if not MATCHES_PATH.exists():
        raise RuntimeError(f"Missing matches file: {MATCHES_PATH}")

    matches = [row for row in read_csv(MATCHES_PATH) if row["season_year"] == "2026"]
    fixtures = sorted(matches, key=lambda row: (int(row["start_timestamp"] or 0), int(row["event_id"] or 0)))

    teams_by_id: dict[str, dict[str, str]] = {}
    for match in fixtures:
        if match.get("is_group") == "True":
            for side in ("home", "away"):
                row = team_row(match, side)
                if row["team_id"]:
                    teams_by_id[row["team_id"]] = row

    group_rows = []
    for group_sign in sorted({row["group_sign"] for row in teams_by_id.values() if row["group_sign"]}):
        group_teams = sorted(
            [row for row in teams_by_id.values() if row["group_sign"] == group_sign],
            key=lambda row: row["team"],
        )
        for seed, row in enumerate(group_teams, start=1):
            group_rows.append(
                {
                    "group_sign": group_sign,
                    "seed": seed,
                    "team": row["team"],
                    "team_id": row["team_id"],
                    "name_code": row["name_code"],
                    "country_code": row["country_code"],
                    "sofascore_ranking": row["sofascore_ranking"],
                }
            )

    team_rows = sorted(teams_by_id.values(), key=lambda row: row["team"])

    write_csv(OUT_DIR / "fixtures.csv", fixtures)
    write_csv(OUT_DIR / "groups.csv", group_rows)
    write_csv(OUT_DIR / "teams.csv", team_rows)

    print(f"Fixtures 2026: {len(fixtures)}")
    print(f"Teams from group stage: {len(team_rows)}")
    print(f"Groups: {len(set(row['group_sign'] for row in group_rows))}")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
