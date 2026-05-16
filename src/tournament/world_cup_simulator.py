import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from features.training_dataset import read_csv, timestamp_to_date
from models.elo import EloSystem
from models.elo_poisson import EloPoissonModel


HOST_CODES = {"USA", "CAN", "MEX"}


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
    model: EloPoissonModel = field(default_factory=EloPoissonModel)
    elo: EloSystem = field(default_factory=EloSystem)

    def __post_init__(self) -> None:
        self.training_rows = sorted(self.training_rows, key=lambda row: (row["match_date"], row["event_id"]))
        self.training_with_elo = self.elo.fit_transform(self.training_rows)
        self.team_by_code = {team_code(team): team for team in self.teams}
        self.team_by_name = {team["team"]: team for team in self.teams}

    def current_elo(self, team_name: str) -> float:
        return self.elo.get(team_name)

    def predict_match(self, home_team: str, away_team: str, venue_country_code: str = "", knockout: bool = False) -> dict[str, Any]:
        home_elo = self.current_elo(home_team)
        away_elo = self.current_elo(away_team)
        home_code = team_code(self.team_by_name.get(home_team, {"team": home_team, "country_code": ""}))
        away_code = team_code(self.team_by_name.get(away_team, {"team": away_team, "country_code": ""}))
        home_adv = self.elo.config.host_advantage if home_code in HOST_CODES and home_code == venue_country_code else 0.0
        away_adv = self.elo.config.host_advantage if away_code in HOST_CODES and away_code == venue_country_code else 0.0
        prediction = self.model.predict_score(home_elo, away_elo, home_advantage=home_adv, away_advantage=away_adv)
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
            "home_win_90": round(prediction["home_win_90"], 4),
            "draw_90": round(prediction["draw_90"], 4),
            "away_win_90": round(prediction["away_win_90"], 4),
            "score_probability": round(prediction["score_probability"], 4),
            "advancing_team": advancing_team,
            "advance_method": advance_method,
        }

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
            pred = self.predict_match(fixture["home_team"], fixture["away_team"], fixture.get("venue_country_code", ""), knockout=False)
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

        for fixture in sorted(knockout_fixtures, key=lambda row: (int(row["start_timestamp"]), int(row["event_id"]))):
            home_team = self.resolve_slot(fixture["home_team"], slots, winners, losers, third_assignments)
            away_team = self.resolve_slot(fixture["away_team"], slots, winners, losers, third_assignments)
            pred = self.predict_match(home_team, away_team, fixture.get("venue_country_code", ""), knockout=True)
            stage = fixture.get("round_name") or "Knockout"
            if stage in stage_offsets:
                match_number = stage_offsets[stage] + stage_counts[stage]
                stage_counts[stage] += 1
            else:
                match_number = len(predictions) + 73
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
    return WorldCupSimulator(
        training_rows=read_csv(base_dir / "data" / "processed" / "training" / "world_cup_matches_1998_2022.csv"),
        fixtures=read_csv(base_dir / "data" / "interim" / "world_cup_2026" / "fixtures.csv"),
        teams=read_csv(base_dir / "data" / "interim" / "world_cup_2026" / "teams.csv"),
    )
