import csv
from dataclasses import dataclass, field
from math import log1p
from pathlib import Path
from typing import Any

from features.training_dataset import read_csv, timestamp_to_date
from models.elo import EloSystem
from models.elo_poisson import EloPoissonModel


HOST_CODES = {"USA", "CAN", "MEX"}
TEAM_ALIASES = {
    "West Germany": "Germany",
    "Czechoslovakia": "Czechia",
}
ELO_REFERENCE_YEAR = 2022
ELO_PIVOT_YEAR = 1986
ELO_MODERN_DECAY_PER_CUP = 0.97
ELO_HISTORICAL_DECAY_PER_CUP = 0.93
GOAL_PROFILE_SMOOTHING_MATCHES = 12.0
GOAL_PROFILE_WEIGHT = 0.6
CURRENT_FORM_GOAL_PROFILE_WEIGHT = 0.30
CURRENT_FORM_SMOOTHING_MATCHES = 3.0
FIFA_POINTS_TO_ELO = 1.1
FIFA_RATING_WEIGHT = 0.60
WORLD_CUP_ELO_WEIGHT = 0.40
CURRENT_WORLD_CUP_GROUP_ELO_WEIGHT = 2.0
MAX_REFERENCE_PARTICIPATIONS = 18.0
MIN_EXPERIENCE_FACTOR = 0.62
OFFICIAL_KNOCKOUT_MATCH_NUMBERS = {
    "12813000": 73,
    "12813014": 74,
    "12812998": 75,
    "12813012": 76,
    "12812995": 77,
    "12812989": 78,
    "12813001": 79,
    "12813020": 80,
    "12812992": 81,
    "12813013": 82,
    "12812997": 83,
    "12813004": 84,
    "12813019": 85,
    "12812999": 86,
    "12813011": 87,
    "12813018": 88,
    "12813010": 89,
    "12813009": 90,
    "12813006": 91,
    "12813007": 92,
    "12812990": 93,
    "12813002": 94,
    "12812993": 95,
    "12812991": 96,
    "12813016": 97,
    "12812994": 98,
    "12813017": 99,
    "12813015": 100,
    "12813008": 101,
    "12812996": 102,
    "12813003": 103,
    "12813005": 104,
}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def numeric(value: str | int | float | None, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def team_code(team: dict[str, str]) -> str:
    return team.get("country_code") or team.get("name_code") or team["team"]


def normalized_name(value: str) -> str:
    return value.lower().replace("&", "and").replace(" ", "").replace("-", "").replace("'", "")


def canonical_team_name(value: str) -> str:
    return TEAM_ALIASES.get(value, value)


def world_cup_elo_weight(year: int) -> float:
    if year >= ELO_PIVOT_YEAR:
        return ELO_MODERN_DECAY_PER_CUP ** ((ELO_REFERENCE_YEAR - year) / 4.0)
    pivot_weight = ELO_MODERN_DECAY_PER_CUP ** ((ELO_REFERENCE_YEAR - ELO_PIVOT_YEAR) / 4.0)
    return pivot_weight * ELO_HISTORICAL_DECAY_PER_CUP ** ((ELO_PIVOT_YEAR - year) / 4.0)


def safe_match_date(row: dict[str, str]) -> str:
    timestamp = int(row.get("start_timestamp") or 0)
    if timestamp >= 0:
        return timestamp_to_date(str(timestamp))
    return f"{int(row['season_year']):04d}-01-01"


def has_finished_score(row: dict[str, str]) -> bool:
    return row.get("status") == "finished" and row.get("home_score") != "" and row.get("away_score") != ""


def winner_from_code(row: dict[str, str], home_team: str, away_team: str) -> str:
    if str(row.get("winner_code", "")) == "1":
        return home_team
    if str(row.get("winner_code", "")) == "2":
        return away_team
    home_score = int(row["home_score"])
    away_score = int(row["away_score"])
    if home_score > away_score:
        return home_team
    if away_score > home_score:
        return away_team
    return ""


def build_world_cup_elo_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    elo_rows: list[dict[str, Any]] = []
    for row in rows:
        if row.get("status") != "finished":
            continue
        if row.get("home_score") == "" or row.get("away_score") == "":
            continue
        home_code = row.get("home_country_code") or row.get("home_name_code")
        away_code = row.get("away_country_code") or row.get("away_name_code")
        year = int(row["season_year"])
        elo_rows.append(
            {
                "event_id": row["event_id"],
                "season_year": year,
                "match_date": safe_match_date(row),
                "stage": row.get("round_name") or row.get("group_name") or row.get("sub_tournament"),
                "home_team": canonical_team_name(row["home_team"]),
                "away_team": canonical_team_name(row["away_team"]),
                "home_score": int(row["home_score"]),
                "away_score": int(row["away_score"]),
                "is_host_home": int(home_code == row.get("venue_country_code")),
                "is_host_away": int(away_code == row.get("venue_country_code")),
                "elo_weight": world_cup_elo_weight(year),
            }
        )
    return sorted(elo_rows, key=lambda item: (item["match_date"], int(item["event_id"])))


def build_goal_profiles(rows: list[dict[str, str]] | None) -> dict[str, dict[str, float]]:
    if not rows:
        return {}
    if any("home_team" in row and "away_team" in row for row in rows):
        return build_weighted_goal_profiles(rows)

    totals: dict[str, dict[str, float]] = {}
    for row in rows:
        team = canonical_team_name(row["team"])
        team_totals = totals.setdefault(
            team,
            {
                "matches": 0.0,
                "goals_for": 0.0,
                "goals_against": 0.0,
                "participations": 0.0,
            },
        )
        team_totals["matches"] += numeric(row.get("world_cup_matches"))
        team_totals["goals_for"] += numeric(row.get("world_cup_goals_for"))
        team_totals["goals_against"] += numeric(row.get("world_cup_goals_against"))
        team_totals["participations"] += numeric(row.get("world_cup_participations"))

    return profiles_from_goal_totals(totals)


def build_weighted_goal_profiles(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    appearances: dict[str, set[int]] = {}
    for row in rows:
        if row.get("status") != "finished":
            continue
        if row.get("home_score") == "" or row.get("away_score") == "":
            continue
        year = int(row["season_year"])
        weight = world_cup_elo_weight(year)
        home = canonical_team_name(row["home_team"])
        away = canonical_team_name(row["away_team"])
        home_score = numeric(row.get("home_score"))
        away_score = numeric(row.get("away_score"))

        for team, goals_for, goals_against in ((home, home_score, away_score), (away, away_score, home_score)):
            team_totals = totals.setdefault(
                team,
                {
                    "matches": 0.0,
                    "goals_for": 0.0,
                    "goals_against": 0.0,
                    "participations": 0.0,
                },
            )
            team_totals["matches"] += weight
            team_totals["goals_for"] += goals_for * weight
            team_totals["goals_against"] += goals_against * weight
            appearances.setdefault(team, set()).add(year)

    for team, seasons in appearances.items():
        totals[team]["participations"] = float(len(seasons))
    return profiles_from_goal_totals(totals)


def build_current_form_goal_profiles(rows: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    for row in rows:
        if row.get("season_year") != "2026" or row.get("is_group") != "True":
            continue
        if not has_finished_score(row):
            continue
        home = canonical_team_name(row["home_team"])
        away = canonical_team_name(row["away_team"])
        home_score = numeric(row.get("home_score"))
        away_score = numeric(row.get("away_score"))

        for team, goals_for, goals_against in ((home, home_score, away_score), (away, away_score, home_score)):
            team_totals = totals.setdefault(
                team,
                {
                    "matches": 0.0,
                    "goals_for": 0.0,
                    "goals_against": 0.0,
                    "participations": 0.0,
                },
            )
            team_totals["matches"] += 1.0
            team_totals["goals_for"] += goals_for
            team_totals["goals_against"] += goals_against

    return profiles_from_goal_totals(totals, smoothing_matches=CURRENT_FORM_SMOOTHING_MATCHES)


def profiles_from_goal_totals(
    totals: dict[str, dict[str, float]],
    smoothing_matches: float = GOAL_PROFILE_SMOOTHING_MATCHES,
    profile_weight: float = GOAL_PROFILE_WEIGHT,
) -> dict[str, dict[str, float]]:
    total_matches = sum(row["matches"] for row in totals.values())
    if total_matches <= 0:
        return {}

    avg_for = sum(row["goals_for"] for row in totals.values()) / total_matches
    avg_against = sum(row["goals_against"] for row in totals.values()) / total_matches
    profiles: dict[str, dict[str, float]] = {}
    for team, row in totals.items():
        matches = row["matches"]
        goals_for = row["goals_for"]
        goals_against = row["goals_against"]
        attack_rate = (goals_for + avg_for * smoothing_matches) / (matches + smoothing_matches)
        defense_rate = (goals_against + avg_against * smoothing_matches) / (matches + smoothing_matches)
        profiles[team] = {
            "attack": (attack_rate / avg_for) ** profile_weight,
            "defense": (defense_rate / avg_against) ** profile_weight,
            "participations": row["participations"],
        }
    return profiles


def build_latest_fifa_lookup(rows: list[dict[str, str]] | None) -> dict[str, dict[str, str]]:
    if not rows:
        return {}
    latest_date = max(row["ranking_date"] for row in rows if row.get("ranking_date"))
    latest_rows = [row for row in rows if row.get("ranking_date") == latest_date]
    lookup: dict[str, dict[str, str]] = {}
    for row in latest_rows:
        for key in (row.get("country_code", ""), row.get("team", ""), normalized_name(row.get("team", ""))):
            if key:
                lookup[key] = row
    return lookup


def build_team_baseline_ratings(
    teams: list[dict[str, str]],
    history_profiles: dict[str, dict[str, float]],
    fifa_rows: list[dict[str, str]] | None,
    base_rating: float,
) -> dict[str, float]:
    _ = history_profiles
    fifa_lookup = build_latest_fifa_lookup(fifa_rows)
    tournament_rankings = []
    for team in teams:
        ranking = fifa_lookup.get(team_code(team)) or fifa_lookup.get(team.get("name_code", "")) or fifa_lookup.get(normalized_name(team["team"]))
        if ranking:
            tournament_rankings.append(numeric(ranking.get("total_points"), base_rating))
    avg_points = sum(tournament_rankings) / len(tournament_rankings) if tournament_rankings else base_rating

    ratings: dict[str, float] = {}
    for team in teams:
        ranking = fifa_lookup.get(team_code(team)) or fifa_lookup.get(team.get("name_code", "")) or fifa_lookup.get(normalized_name(team["team"]))
        fifa_points = numeric(ranking.get("total_points") if ranking else None, avg_points)
        ratings[team["team"]] = base_rating + (fifa_points - avg_points) * FIFA_POINTS_TO_ELO
    return ratings


@dataclass
class Standing:
    team: str
    team_id: str
    country_code: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    def add_match(self, goals_for: int, goals_against: int) -> None:
        self.played += 1
        self.goals_for += goals_for
        self.goals_against += goals_against
        if goals_for > goals_against:
            self.wins += 1
            self.points += 3
        elif goals_for == goals_against:
            self.draws += 1
            self.points += 1
        else:
            self.losses += 1

    def to_row(self, group_sign: str, position: int) -> dict[str, Any]:
        return {
            "group_sign": group_sign,
            "position": position,
            "team": self.team,
            "team_id": self.team_id,
            "country_code": self.country_code,
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_diff": self.goal_diff,
            "points": self.points,
        }


@dataclass
class WorldCupSimulator:
    training_rows: list[dict[str, str]]
    fixtures: list[dict[str, str]]
    teams: list[dict[str, str]]
    history_rows: list[dict[str, str]] | None = None
    fifa_rows: list[dict[str, str]] | None = None
    model: EloPoissonModel = field(default_factory=EloPoissonModel)
    elo: EloSystem = field(default_factory=EloSystem)

    def __post_init__(self) -> None:
        self.training_rows = sorted(self.training_rows, key=lambda row: (row["match_date"], row["event_id"]))
        self.training_with_elo = self.elo.fit_transform(self.training_rows)
        self.team_by_code = {team_code(team): team for team in self.teams}
        self.team_by_name = {team["team"]: team for team in self.teams}
        self.goal_profiles = build_goal_profiles(self.history_rows)
        self.current_form_goal_profiles = build_current_form_goal_profiles(self.fixtures)
        self.baseline_ratings = build_team_baseline_ratings(
            self.teams,
            self.goal_profiles,
            self.fifa_rows,
            self.elo.config.base_rating,
        )

    def current_elo(self, team_name: str) -> float:
        world_cup_elo = self.elo.get(team_name)
        baseline = self.baseline_ratings.get(team_name, self.elo.config.base_rating)
        return WORLD_CUP_ELO_WEIGHT * world_cup_elo + FIFA_RATING_WEIGHT * baseline

    def goal_profile(self, team_name: str) -> dict[str, float]:
        profile = self.goal_profiles.get(team_name, {"attack": 1.0, "defense": 1.0, "participations": 0.0})
        participations = numeric(profile.get("participations"), 0.0)
        experience = min(1.0, log1p(participations) / log1p(MAX_REFERENCE_PARTICIPATIONS))
        experience_factor = MIN_EXPERIENCE_FACTOR + (1.0 - MIN_EXPERIENCE_FACTOR) * experience
        historical = {
            "attack": profile["attack"] * experience_factor,
            "defense": profile["defense"] / experience_factor,
        }
        current = self.current_form_goal_profiles.get(team_name)
        if not current:
            return historical
        current_weight = CURRENT_FORM_GOAL_PROFILE_WEIGHT
        historical_weight = 1.0 - current_weight
        return {
            "attack": historical["attack"] * historical_weight + current["attack"] * current_weight,
            "defense": historical["defense"] * historical_weight + current["defense"] * current_weight,
        }

    def predict_match(self, home_team: str, away_team: str, venue_country_code: str = "", knockout: bool = False) -> dict[str, Any]:
        home_elo = self.current_elo(home_team)
        away_elo = self.current_elo(away_team)
        home_code = team_code(self.team_by_name.get(home_team, {"team": home_team, "country_code": ""}))
        away_code = team_code(self.team_by_name.get(away_team, {"team": away_team, "country_code": ""}))
        home_adv = self.elo.config.host_advantage if home_code in HOST_CODES and home_code == venue_country_code else 0.0
        away_adv = self.elo.config.host_advantage if away_code in HOST_CODES and away_code == venue_country_code else 0.0
        home_profile = self.goal_profile(home_team)
        away_profile = self.goal_profile(away_team)
        prediction = self.model.predict_score(
            home_elo,
            away_elo,
            home_advantage=home_adv,
            away_advantage=away_adv,
            home_attack=home_profile["attack"],
            away_attack=away_profile["attack"],
            home_defense=home_profile["defense"],
            away_defense=away_profile["defense"],
        )
        advancing_team = ""
        advance_method = ""
        if knockout:
            advancing_team, advance_method = self.model.advancing_team(prediction, home_team, away_team, home_elo, away_elo)
        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_score": prediction["home_goals"],
            "away_score": prediction["away_goals"],
            "home_elo": round(home_elo, 2),
            "away_elo": round(away_elo, 2),
            "home_xg": round(prediction["home_lambda"], 2),
            "away_xg": round(prediction["away_lambda"], 2),
            "home_win_90": round(prediction["home_win_90"], 4),
            "draw_90": round(prediction["draw_90"], 4),
            "away_win_90": round(prediction["away_win_90"], 4),
            "score_probability": round(prediction["score_probability"], 4),
            "advancing_team": advancing_team,
            "advance_method": advance_method,
        }

    def fixture_elo_weight(self, fixture: dict[str, str], stage: str) -> float:
        if fixture.get("season_year") == "2026" and stage == "Group":
            return CURRENT_WORLD_CUP_GROUP_ELO_WEIGHT
        return 1.0

    def rate_finished_fixture(self, fixture: dict[str, str], home_team: str, away_team: str, stage: str) -> None:
        home_code = team_code(self.team_by_name.get(home_team, {"team": home_team, "country_code": ""}))
        away_code = team_code(self.team_by_name.get(away_team, {"team": away_team, "country_code": ""}))
        self.elo.rate_match(
            {
                "event_id": fixture["event_id"],
                "season_year": int(fixture["season_year"]),
                "match_date": safe_match_date(fixture),
                "stage": stage,
                "home_team": home_team,
                "away_team": away_team,
                "home_score": int(fixture["home_score"]),
                "away_score": int(fixture["away_score"]),
                "is_host_home": int(home_code == fixture.get("venue_country_code")),
                "is_host_away": int(away_code == fixture.get("venue_country_code")),
                "elo_weight": self.fixture_elo_weight(fixture, stage),
            }
        )

    def actual_match_row(
        self,
        fixture: dict[str, str],
        home_team: str,
        away_team: str,
        *,
        knockout: bool,
    ) -> dict[str, Any]:
        pred = self.predict_match(home_team, away_team, fixture.get("venue_country_code", ""), knockout=knockout)
        home_score = int(fixture["home_score"])
        away_score = int(fixture["away_score"])
        pred["home_score"] = home_score
        pred["away_score"] = away_score
        if home_score <= self.model.max_goals and away_score <= self.model.max_goals:
            score = next(
                row
                for row in self.model.score_matrix(pred["home_xg"], pred["away_xg"])
                if row["home_goals"] == home_score and row["away_goals"] == away_score
            )
            pred["score_probability"] = round(score["probability"], 4)
        pred["result_source"] = "actual"
        if knockout:
            advancing_team = winner_from_code(fixture, home_team, away_team) or pred["advancing_team"]
            pred["advancing_team"] = advancing_team
            pred["advance_method"] = "actual"
        return pred

    def simulate_group_stage(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[Standing]]]:
        group_fixtures = [row for row in self.fixtures if row.get("is_group") == "True"]
        standings: dict[str, dict[str, Standing]] = {}
        predictions: list[dict[str, Any]] = []

        for team in self.teams:
            group = team["group_sign"]
            standings.setdefault(group, {})[team["team"]] = Standing(
                team=team["team"],
                team_id=team["team_id"],
                country_code=team_code(team),
            )

        for fixture in sorted(group_fixtures, key=lambda row: (int(row["start_timestamp"]), int(row["event_id"]))):
            if has_finished_score(fixture):
                pred = self.actual_match_row(fixture, fixture["home_team"], fixture["away_team"], knockout=False)
                self.rate_finished_fixture(fixture, fixture["home_team"], fixture["away_team"], "Group")
            else:
                pred = self.predict_match(fixture["home_team"], fixture["away_team"], fixture.get("venue_country_code", ""), knockout=False)
                pred["result_source"] = "predicted"
            pred.update(
                {
                    "event_id": fixture["event_id"],
                    "stage": "Group",
                    "group_sign": fixture["group_sign"],
                    "venue": fixture.get("venue", ""),
                }
            )
            predictions.append(pred)
            group = fixture["group_sign"]
            standings[group][fixture["home_team"]].add_match(pred["home_score"], pred["away_score"])
            standings[group][fixture["away_team"]].add_match(pred["away_score"], pred["home_score"])

        ordered: dict[str, list[Standing]] = {}
        table_rows: list[dict[str, Any]] = []
        for group, table in standings.items():
            ordered[group] = sorted(
                table.values(),
                key=lambda standing: (
                    standing.points,
                    standing.goal_diff,
                    standing.goals_for,
                    self.current_elo(standing.team),
                ),
                reverse=True,
            )
            for position, standing in enumerate(ordered[group], start=1):
                table_rows.append(standing.to_row(group, position))

        return predictions, table_rows, ordered

    def build_slots(self, ordered_groups: dict[str, list[Standing]]) -> dict[str, Any]:
        slots: dict[str, str] = {}
        third_place_pool: dict[str, Standing] = {}
        for group, standings in ordered_groups.items():
            if len(standings) >= 1:
                slots[f"1{group}"] = standings[0].team
                slots[f"{group}1"] = standings[0].team
            if len(standings) >= 2:
                slots[f"2{group}"] = standings[1].team
                slots[f"{group}2"] = standings[1].team
            if len(standings) >= 3:
                third_place_pool[group] = standings[2]

        best_thirds = sorted(
            third_place_pool.items(),
            key=lambda item: (
                item[1].points,
                item[1].goal_diff,
                item[1].goals_for,
                self.current_elo(item[1].team),
            ),
            reverse=True,
        )[:8]
        slots["_thirds"] = [group for group, _ in best_thirds]
        for group, standing in best_thirds:
            slots[f"3{group}"] = standing.team
        return slots

    def build_third_slot_assignments(self, knockout_fixtures: list[dict[str, str]], slots: dict[str, Any]) -> dict[str, str]:
        qualified_groups = set(slots.get("_thirds", []))
        third_slots = []
        for fixture in knockout_fixtures:
            for side in ("home_team", "away_team"):
                slot = fixture[side]
                if "/" in slot and any(part.startswith("3") for part in slot.split("/")):
                    candidates = [
                        part.replace("3", "")
                        for part in slot.split("/")
                        if part.startswith("3") and part.replace("3", "") in qualified_groups
                    ]
                    third_slots.append((slot, candidates))

        assignments: dict[str, str] = {}
        used_groups: set[str] = set()
        ordered_slots = sorted(third_slots, key=lambda item: len(item[1]))

        def backtrack(index: int) -> bool:
            if index == len(ordered_slots):
                return True
            slot, candidates = ordered_slots[index]
            if slot in assignments:
                return backtrack(index + 1)
            for group in candidates:
                if group in used_groups:
                    continue
                used_groups.add(group)
                assignments[slot] = slots[f"3{group}"]
                if backtrack(index + 1):
                    return True
                used_groups.remove(group)
                assignments.pop(slot, None)
            return False

        backtrack(0)
        return assignments

    def resolve_slot(self, slot: str, slots: dict[str, Any], winners: dict[str, str], losers: dict[str, str], third_assignments: dict[str, str]) -> str:
        slot = slot.strip()
        if slot in winners:
            return winners[slot]
        if slot in losers:
            return losers[slot]
        if slot in third_assignments:
            return third_assignments[slot]
        if slot in slots:
            return slots[slot]
        if "/" in slot:
            for candidate in slot.split("/"):
                if candidate in slots:
                    return slots[candidate]
            for group in slots.get("_thirds", []):
                candidate = f"3{group}"
                if candidate in slots:
                    return slots[candidate]
        return slot

    def simulate_knockouts(self, slots: dict[str, Any]) -> list[dict[str, Any]]:
        knockout_fixtures = [row for row in self.fixtures if row.get("is_group") != "True"]
        predictions: list[dict[str, Any]] = []
        winners: dict[str, str] = {}
        losers: dict[str, str] = {}
        third_assignments = self.build_third_slot_assignments(knockout_fixtures, slots)
        stage_offsets = {
            "Round of 32": 73,
            "Round of 16": 89,
            "Quarterfinals": 97,
            "Semifinals": 101,
            "Match for 3rd place": 103,
            "Final": 104,
        }
        stage_counts = {stage: 0 for stage in stage_offsets}

        for fixture in sorted(
            knockout_fixtures,
            key=lambda row: (
                OFFICIAL_KNOCKOUT_MATCH_NUMBERS.get(str(row["event_id"]), 999),
                int(row["start_timestamp"]),
                int(row["event_id"]),
            ),
        ):
            home_team = self.resolve_slot(fixture["home_team"], slots, winners, losers, third_assignments)
            away_team = self.resolve_slot(fixture["away_team"], slots, winners, losers, third_assignments)
            stage = fixture.get("round_name") or "Knockout"
            official_match_number = OFFICIAL_KNOCKOUT_MATCH_NUMBERS.get(str(fixture["event_id"]))
            if official_match_number:
                match_number = official_match_number
            elif stage in stage_offsets:
                match_number = stage_offsets[stage] + stage_counts[stage]
                stage_counts[stage] += 1
            else:
                match_number = len(predictions) + 73
            if has_finished_score(fixture):
                pred = self.actual_match_row(fixture, home_team, away_team, knockout=True)
                self.rate_finished_fixture(fixture, home_team, away_team, stage)
            else:
                pred = self.predict_match(home_team, away_team, fixture.get("venue_country_code", ""), knockout=True)
                pred["result_source"] = "predicted"
            winners[f"W{fixture['event_id']}"] = pred["advancing_team"]
            winners[f"W{match_number}"] = pred["advancing_team"]
            loser = away_team if pred["advancing_team"] == home_team else home_team
            losers[f"L{fixture['event_id']}"] = loser
            losers[f"L{match_number}"] = loser
            pred.update(
                {
                    "event_id": fixture["event_id"],
                    "match_number": match_number,
                    "stage": stage,
                    "venue": fixture.get("venue", ""),
                    "source_home_slot": fixture["home_team"],
                    "source_away_slot": fixture["away_team"],
                }
            )
            predictions.append(pred)
        return predictions

    def simulate(self) -> dict[str, list[dict[str, Any]]]:
        group_predictions, table_rows, ordered_groups = self.simulate_group_stage()
        slots = self.build_slots(ordered_groups)
        knockout_predictions = self.simulate_knockouts(slots)
        return {
            "group_predictions": group_predictions,
            "standings": table_rows,
            "knockout_predictions": knockout_predictions,
        }


def load_simulator(base_dir: Path) -> WorldCupSimulator:
    world_cup_history_rows = read_csv(base_dir / "data" / "raw" / "sofascore" / "world_cup_history" / "matches.csv")
    return WorldCupSimulator(
        training_rows=build_world_cup_elo_rows(world_cup_history_rows),
        fixtures=read_csv(base_dir / "data" / "interim" / "world_cup_2026" / "fixtures.csv"),
        teams=read_csv(base_dir / "data" / "interim" / "world_cup_2026" / "teams.csv"),
        history_rows=world_cup_history_rows,
        fifa_rows=read_csv(base_dir / "data" / "raw" / "fifa" / "rankings" / "rankings.csv"),
    )
