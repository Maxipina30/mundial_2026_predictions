import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def timestamp_to_date(timestamp: str) -> str:
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).date().isoformat()


def load_rankings_by_country(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    rankings: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        code = row.get("country_code")
        if not code:
            continue
        rankings.setdefault(code, []).append(row)
    for code in rankings:
        rankings[code].sort(key=lambda row: row["ranking_date"])
    return rankings


def ranking_before(rankings: dict[str, list[dict[str, str]]], country_code: str, match_date: str) -> dict[str, str]:
    selected: dict[str, str] = {}
    for row in rankings.get(country_code, []):
        if row["ranking_date"] <= match_date:
            selected = row
        else:
            break
    return selected


def load_history_by_country(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["country_code"]: row for row in rows if row.get("country_code")}


def float_or_default(value: str | None, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def int_or_default(value: str | None, default: int = 0) -> int:
    if value in (None, ""):
        return default
    return int(float(value))


def build_training_dataset(
    matches: list[dict[str, str]],
    fifa_rankings: list[dict[str, str]],
    history_rows: list[dict[str, str]],
    min_year: int = 1998,
    max_year: int = 2022,
) -> list[dict[str, Any]]:
    rankings_by_country = load_rankings_by_country(fifa_rankings)
    history_by_country = load_history_by_country(history_rows)
    dataset: list[dict[str, Any]] = []

    history_fields = [
        "world_cup_participations",
        "world_cup_matches",
        "world_cup_wins",
        "world_cup_draws",
        "world_cup_losses",
        "world_cup_goals_for",
        "world_cup_goals_against",
        "world_cup_goal_diff",
        "world_cup_titles",
        "world_cup_finals",
        "world_cup_semi_finals",
        "world_cup_quarter_finals",
        "world_cup_round_of_16s",
    ]

    for match in matches:
        year = int(match["season_year"])
        if year < min_year or year > max_year:
            continue
        if match.get("status") != "finished":
            continue
        if match.get("home_score") == "" or match.get("away_score") == "":
            continue

        match_date = timestamp_to_date(match["start_timestamp"])
        home_code = match.get("home_country_code") or match.get("home_name_code")
        away_code = match.get("away_country_code") or match.get("away_name_code")
        home_rank = ranking_before(rankings_by_country, home_code, match_date)
        away_rank = ranking_before(rankings_by_country, away_code, match_date)
        home_hist = history_by_country.get(home_code, {})
        away_hist = history_by_country.get(away_code, {})

        row: dict[str, Any] = {
            "event_id": match["event_id"],
            "season_year": year,
            "match_date": match_date,
            "stage": match.get("round_name") or match.get("group_name") or match.get("sub_tournament"),
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "home_country_code": home_code,
            "away_country_code": away_code,
            "home_score": int(match["home_score"]),
            "away_score": int(match["away_score"]),
            "home_fifa_rank": int_or_default(home_rank.get("rank"), 999),
            "away_fifa_rank": int_or_default(away_rank.get("rank"), 999),
            "home_fifa_points": float_or_default(home_rank.get("total_points"), 1000.0),
            "away_fifa_points": float_or_default(away_rank.get("total_points"), 1000.0),
            "neutral": 1,
            "is_host_home": int(home_code == match.get("venue_country_code")),
            "is_host_away": int(away_code == match.get("venue_country_code")),
        }
        row["fifa_rank_diff"] = row["away_fifa_rank"] - row["home_fifa_rank"]
        row["fifa_points_diff"] = row["home_fifa_points"] - row["away_fifa_points"]

        for field in history_fields:
            home_value = float_or_default(home_hist.get(field), 0.0)
            away_value = float_or_default(away_hist.get(field), 0.0)
            row[f"home_{field}"] = home_value
            row[f"away_{field}"] = away_value
            row[f"{field}_diff"] = home_value - away_value

        dataset.append(row)

    return sorted(dataset, key=lambda row: (row["match_date"], row["event_id"]))
