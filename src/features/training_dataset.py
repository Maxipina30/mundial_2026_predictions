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


def empty_world_cup_stats() -> dict[str, Any]:
    return {
        "appearances": set(),
        "matches": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
        "titles": 0,
        "finals": 0,
        "semi_finals": 0,
        "quarter_finals": 0,
        "round_of_16s": 0,
    }


def normalize_stage_text(match: dict[str, str]) -> str:
    text = " ".join(
        str(match.get(key) or "")
        for key in ("sub_tournament", "round_name", "group_name", "slug")
    ).lower()
    if "match for 3rd place" in text or "third" in text:
        return "third_place"
    if "semifinal" in text or "semi-final" in text:
        return "semi_final"
    if "quarterfinal" in text or "quarter-final" in text:
        return "quarter_final"
    if "round of 16" in text or "last 16" in text:
        return "round_of_16"
    if "final" in text and "semi" not in text and "third" not in text:
        return "final"
    return "group"


def stats_to_world_cup_fields(stats: dict[str, Any]) -> dict[str, float]:
    return {
        "world_cup_participations": float(len(stats["appearances"])),
        "world_cup_matches": float(stats["matches"]),
        "world_cup_wins": float(stats["wins"]),
        "world_cup_draws": float(stats["draws"]),
        "world_cup_losses": float(stats["losses"]),
        "world_cup_goals_for": float(stats["goals_for"]),
        "world_cup_goals_against": float(stats["goals_against"]),
        "world_cup_goal_diff": float(stats["goals_for"] - stats["goals_against"]),
        "world_cup_titles": float(stats["titles"]),
        "world_cup_finals": float(stats["finals"]),
        "world_cup_semi_finals": float(stats["semi_finals"]),
        "world_cup_quarter_finals": float(stats["quarter_finals"]),
        "world_cup_round_of_16s": float(stats["round_of_16s"]),
    }


def update_world_cup_stats(stats: dict[str, dict[str, Any]], match: dict[str, str]) -> None:
    season = str(match["season_year"])
    stage = normalize_stage_text(match)
    home_code = match.get("home_country_code") or match.get("home_name_code")
    away_code = match.get("away_country_code") or match.get("away_name_code")
    home_score = int(match["home_score"])
    away_score = int(match["away_score"])
    winner_code = match.get("winner_code")

    for code in (home_code, away_code):
        stats.setdefault(code, empty_world_cup_stats())

    match_updates = (
        (home_code, home_score, away_score, winner_code == "1", winner_code == "2"),
        (away_code, away_score, home_score, winner_code == "2", winner_code == "1"),
    )
    for code, goals_for, goals_against, won, lost in match_updates:
        team_stats = stats[code]
        team_stats["appearances"].add(season)
        team_stats["matches"] += 1
        team_stats["goals_for"] += goals_for
        team_stats["goals_against"] += goals_against
        if won:
            team_stats["wins"] += 1
        elif lost:
            team_stats["losses"] += 1
        else:
            team_stats["draws"] += 1
        if stage == "round_of_16":
            team_stats["round_of_16s"] += 1
        elif stage == "quarter_final":
            team_stats["quarter_finals"] += 1
        elif stage == "semi_final":
            team_stats["semi_finals"] += 1
        elif stage == "final":
            team_stats["finals"] += 1

    if stage == "final":
        if winner_code == "1":
            stats[home_code]["titles"] += 1
        elif winner_code == "2":
            stats[away_code]["titles"] += 1


def build_training_dataset(
    matches: list[dict[str, str]],
    fifa_rankings: list[dict[str, str]],
    history_rows: list[dict[str, str]],
    min_year: int = 1998,
    max_year: int = 2022,
) -> list[dict[str, Any]]:
    rankings_by_country = load_rankings_by_country(fifa_rankings)
    _ = history_rows
    dataset: list[dict[str, Any]] = []
    rolling_stats: dict[str, dict[str, Any]] = {}

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

    finished_matches = sorted(
        [
            match
            for match in matches
            if match.get("status") == "finished"
            and match.get("home_score") != ""
            and match.get("away_score") != ""
        ],
        key=lambda match: (int(match["start_timestamp"]), int(match["event_id"])),
    )

    for match in finished_matches:
        year = int(match["season_year"])
        match_date = timestamp_to_date(match["start_timestamp"])
        home_code = match.get("home_country_code") or match.get("home_name_code")
        away_code = match.get("away_country_code") or match.get("away_name_code")
        home_rank = ranking_before(rankings_by_country, home_code, match_date)
        away_rank = ranking_before(rankings_by_country, away_code, match_date)
        home_hist = stats_to_world_cup_fields(rolling_stats.get(home_code, empty_world_cup_stats()))
        away_hist = stats_to_world_cup_fields(rolling_stats.get(away_code, empty_world_cup_stats()))

        if min_year <= year <= max_year:
            row: dict[str, Any] = {
                "event_id": match["event_id"],
                "season_year": year,
                "match_date": match_date,
                "competition": match.get("tournament", ""),
                "competition_group": match.get("competition_group", "world_cup"),
                "competition_weight": float_or_default(match.get("competition_weight"), 1.0),
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
                home_value = float_or_default(str(home_hist.get(field, 0.0)), 0.0)
                away_value = float_or_default(str(away_hist.get(field, 0.0)), 0.0)
                row[f"home_{field}"] = home_value
                row[f"away_{field}"] = away_value
                row[f"{field}_diff"] = home_value - away_value

            dataset.append(row)

        update_world_cup_stats(rolling_stats, match)

    return sorted(dataset, key=lambda row: (row["match_date"], row["event_id"]))
