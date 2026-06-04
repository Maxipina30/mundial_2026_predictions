from dataclasses import dataclass, field
from math import log
from typing import Any


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def actual_score(goals_a: int, goals_b: int) -> float:
    if goals_a > goals_b:
        return 1.0
    if goals_a < goals_b:
        return 0.0
    return 0.5


def goal_multiplier(goals_a: int, goals_b: int) -> float:
    margin = abs(goals_a - goals_b)
    if margin <= 1:
        return 1.0
    return 1.0 + log(margin)


@dataclass
class EloConfig:
    base_rating: float = 1500.0
    k_group: float = 35.0
    k_round_of_16: float = 45.0
    k_quarter_final: float = 50.0
    k_semi_final: float = 55.0
    k_final: float = 65.0
    k_knockout: float = 45.0
    host_advantage: float = 60.0
    min_match_weight: float = 0.05


@dataclass
class EloSystem:
    config: EloConfig = field(default_factory=EloConfig)
    ratings: dict[str, float] = field(default_factory=dict)

    def get(self, team: str) -> float:
        return self.ratings.get(team, self.config.base_rating)

    def k_for_match(self, row: dict[str, Any]) -> float:
        stage = str(row.get("stage", "")).lower()
        if "group" in stage:
            base_k = self.config.k_group
        elif "final" in stage and "semi" not in stage and "third" not in stage and "3rd" not in stage:
            base_k = self.config.k_final
        elif "semi" in stage:
            base_k = self.config.k_semi_final
        elif "quarter" in stage:
            base_k = self.config.k_quarter_final
        elif "round of 16" in stage or "last 16" in stage:
            base_k = self.config.k_round_of_16
        else:
            base_k = self.config.k_knockout
        weight = float(row.get("elo_weight", 1.0) or 1.0)
        return base_k * max(self.config.min_match_weight, weight)

    def rate_match(self, row: dict[str, Any]) -> dict[str, float]:
        home = row["home_team"]
        away = row["away_team"]
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])
        home_pre = self.get(home)
        away_pre = self.get(away)
        adjusted_home = home_pre + self.config.host_advantage * int(row.get("is_host_home", 0))
        adjusted_away = away_pre + self.config.host_advantage * int(row.get("is_host_away", 0))
        exp_home = expected_score(adjusted_home, adjusted_away)
        act_home = actual_score(home_score, away_score)
        delta = self.k_for_match(row) * goal_multiplier(home_score, away_score) * (act_home - exp_home)
        self.ratings[home] = home_pre + delta
        self.ratings[away] = away_pre - delta
        return {
            "home_elo_pre": home_pre,
            "away_elo_pre": away_pre,
            "home_elo_post": self.ratings[home],
            "away_elo_post": self.ratings[away],
            "elo_diff": home_pre - away_pre,
        }

    def fit_transform(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        output = []
        for row in rows:
            enriched = dict(row)
            enriched.update(self.rate_match(row))
            output.append(enriched)
        return output
