from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


KNOCKOUT_STAGE_ORDER = {
    "final": 7,
    "third-place": 6,
    "semi-final": 5,
    "quarter-final": 4,
    "round-of-16": 3,
    "round-of-32": 2,
    "group": 1,
    "other": 0,
}


def normalize_stage(row: dict[str, str]) -> str:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("sub_tournament", "round_name", "slug")
    ).lower()
    if "final round" in text:
        return "group"
    if "match for 3rd place" in text or "third" in text or "bronze" in text:
        return "third-place"
    if "semifinal" in text or "semi-final" in text:
        return "semi-final"
    if "quarterfinal" in text or "quarter-final" in text:
        return "quarter-final"
    if "final" in text and "semi" not in text and "third" not in text and "bronze" not in text:
        return "final"
    if "round of 16" in text or "last 16" in text:
        return "round-of-16"
    if "round of 32" in text:
        return "round-of-32"
    if str(row.get("is_group")) == "True" or "group" in text:
        return "group"
    return "other"


def match_result_for_team(row: dict[str, str], team: str) -> tuple[int, int, str]:
    home = row["home_team"]
    away = row["away_team"]
    home_score = int(row["home_score"])
    away_score = int(row["away_score"])
    winner_code = row.get("winner_code")

    if team == home:
        gf, ga = home_score, away_score
        if winner_code == "1":
            result = "W"
        elif winner_code == "2":
            result = "L"
        else:
            result = "D"
    elif team == away:
        gf, ga = away_score, home_score
        if winner_code == "2":
            result = "W"
        elif winner_code == "1":
            result = "L"
        else:
            result = "D"
    else:
        raise ValueError(f"{team} did not play event {row.get('event_id')}")
    return gf, ga, result


@dataclass
class TeamWorldCupStats:
    team: str
    team_id: str = ""
    country_code: str = ""
    appearances: set[str] = field(default_factory=set)
    matches: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    titles: int = 0
    finals: int = 0
    semi_finals: int = 0
    quarter_finals: int = 0
    round_of_16s: int = 0
    round_of_32s: int = 0
    best_stage_score: int = 0

    def to_row(self) -> dict[str, Any]:
        return {
            "team": self.team,
            "team_id": self.team_id,
            "country_code": self.country_code,
            "world_cup_participations": len(self.appearances),
            "world_cup_matches": self.matches,
            "world_cup_wins": self.wins,
            "world_cup_draws": self.draws,
            "world_cup_losses": self.losses,
            "world_cup_goals_for": self.goals_for,
            "world_cup_goals_against": self.goals_against,
            "world_cup_goal_diff": self.goals_for - self.goals_against,
            "world_cup_titles": self.titles,
            "world_cup_finals": self.finals,
            "world_cup_semi_finals": self.semi_finals,
            "world_cup_quarter_finals": self.quarter_finals,
            "world_cup_round_of_16s": self.round_of_16s,
            "world_cup_round_of_32s": self.round_of_32s,
            "best_stage_score": self.best_stage_score,
        }


def build_world_cup_team_stats(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    finished = [row for row in rows if row.get("status") == "finished" and row.get("home_score") != "" and row.get("away_score") != ""]
    stats: dict[str, TeamWorldCupStats] = {}
    season_stage_teams: dict[tuple[str, str], set[str]] = defaultdict(set)
    season_final_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    season_final_round_rows: dict[str, list[dict[str, str]]] = defaultdict(list)

    def ensure_team(row: dict[str, str], side: str) -> TeamWorldCupStats:
        team = row[f"{side}_team"]
        if team not in stats:
            stats[team] = TeamWorldCupStats(
                team=team,
                team_id=row.get(f"{side}_team_id", ""),
                country_code=row.get(f"{side}_country_code", ""),
            )
        return stats[team]

    for row in finished:
        season = row["season_year"]
        stage = normalize_stage(row)
        home_stats = ensure_team(row, "home")
        away_stats = ensure_team(row, "away")
        for team_stats, team in ((home_stats, row["home_team"]), (away_stats, row["away_team"])):
            gf, ga, result = match_result_for_team(row, team)
            team_stats.appearances.add(season)
            team_stats.matches += 1
            team_stats.goals_for += gf
            team_stats.goals_against += ga
            team_stats.best_stage_score = max(team_stats.best_stage_score, KNOCKOUT_STAGE_ORDER[stage])
            if result == "W":
                team_stats.wins += 1
            elif result == "D":
                team_stats.draws += 1
            else:
                team_stats.losses += 1
            season_stage_teams[(season, stage)].add(team)
        if stage == "final":
            season_final_rows[season].append(row)
        if "final round" in str(row.get("sub_tournament") or "").lower():
            season_final_round_rows[season].append(row)

    for (season, stage), teams in season_stage_teams.items():
        for team in teams:
            if stage == "round-of-32":
                stats[team].round_of_32s += 1
            elif stage == "round-of-16":
                stats[team].round_of_16s += 1
            elif stage == "quarter-final":
                stats[team].quarter_finals += 1
            elif stage == "semi-final":
                stats[team].semi_finals += 1

    for season, final_rows in season_final_rows.items():
        # Most modern World Cups have one final. If SofaScore returns extra
        # final-group rows for older formats, counting all teams as finalists
        # is still safer than inventing missing brackets.
        for row in final_rows:
            finalists = (row["home_team"], row["away_team"])
            for team in finalists:
                stats[team].finals += 1
            winner_code = row.get("winner_code")
            if winner_code == "1":
                stats[row["home_team"]].titles += 1
            elif winner_code == "2":
                stats[row["away_team"]].titles += 1

    for season, final_round_rows in season_final_round_rows.items():
        if season in season_final_rows:
            continue
        table: dict[str, dict[str, int]] = defaultdict(lambda: {"points": 0, "gd": 0, "gf": 0})
        for row in final_round_rows:
            home = row["home_team"]
            away = row["away_team"]
            home_score = int(row["home_score"])
            away_score = int(row["away_score"])
            table[home]["gf"] += home_score
            table[home]["gd"] += home_score - away_score
            table[away]["gf"] += away_score
            table[away]["gd"] += away_score - home_score
            if home_score > away_score:
                table[home]["points"] += 3
            elif away_score > home_score:
                table[away]["points"] += 3
            else:
                table[home]["points"] += 1
                table[away]["points"] += 1
        final_table = sorted(
            table,
            key=lambda team: (table[team]["points"], table[team]["gd"], table[team]["gf"]),
            reverse=True,
        )
        if final_table:
            stats[final_table[0]].titles += 1
        for team in final_table[:2]:
            stats[team].finals += 1

    return sorted(
        [team_stats.to_row() for team_stats in stats.values()],
        key=lambda row: (-row["world_cup_titles"], -row["world_cup_finals"], row["team"]),
    )
