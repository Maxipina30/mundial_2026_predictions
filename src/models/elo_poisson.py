from dataclasses import dataclass
from math import ceil, exp, factorial
from typing import Any


def poisson_pmf(k: int, lam: float) -> float:
    return exp(-lam) * lam**k / factorial(k)


@dataclass
class EloPoissonModel:
    base_goals: float = 1.25
    elo_scale: float = 750.0
    max_goals: int = 7
    draw_penalty: float = 0.0
    win_confidence_threshold: float = 0.38

    def expected_goals(
        self,
        home_elo: float,
        away_elo: float,
        home_advantage: float = 0.0,
        away_advantage: float = 0.0,
        home_attack: float = 1.0,
        away_attack: float = 1.0,
        home_defense: float = 1.0,
        away_defense: float = 1.0,
    ) -> tuple[float, float]:
        diff = (home_elo + home_advantage) - (away_elo + away_advantage)
        home_lambda = self.base_goals * exp(diff / self.elo_scale) * home_attack * away_defense
        away_lambda = self.base_goals * exp(-diff / self.elo_scale) * away_attack * home_defense
        return max(0.05, home_lambda), max(0.05, away_lambda)

    def score_matrix(self, home_lambda: float, away_lambda: float) -> list[dict[str, Any]]:
        rows = []
        for home_goals in range(self.max_goals + 1):
            ph = poisson_pmf(home_goals, home_lambda)
            for away_goals in range(self.max_goals + 1):
                pa = poisson_pmf(away_goals, away_lambda)
                probability = ph * pa
                if home_goals == away_goals and self.draw_penalty:
                    probability *= 1.0 - self.draw_penalty
                rows.append(
                    {
                        "home_goals": home_goals,
                        "away_goals": away_goals,
                        "probability": probability,
                    }
                )
        total = sum(row["probability"] for row in rows)
        for row in rows:
            row["probability"] /= total
        return rows

    def goals_from_lambda(self, lam: float) -> int:
        if lam < 0.80:
            return 0
        if lam < 1.60:
            return 1
        if lam < 2.40:
            return 2
        return min(self.max_goals, round(lam))

    def representative_score(self, home_lambda: float, away_lambda: float, outcome: str) -> tuple[int, int]:
        home_goals = self.goals_from_lambda(home_lambda)
        away_goals = self.goals_from_lambda(away_lambda)

        if outcome == "D":
            goals = max(1, self.goals_from_lambda((home_lambda + away_lambda) / 2.0))
            return goals, goals

        if outcome == "H" and home_goals <= away_goals:
            if home_lambda - away_lambda < 0.25:
                return 1, 1
            home_goals = min(self.max_goals, away_goals + 1)
        elif outcome == "A" and away_goals <= home_goals:
            if away_lambda - home_lambda < 0.25:
                return 1, 1
            away_goals = min(self.max_goals, home_goals + 1)
        if outcome == "H" and home_lambda >= 4.0 and away_lambda < 0.5:
            home_goals = min(self.max_goals, ceil(home_lambda))
            away_goals = 0
        elif outcome == "A" and away_lambda >= 4.0 and home_lambda < 0.5:
            away_goals = min(self.max_goals, ceil(away_lambda))
            home_goals = 0
        return home_goals, away_goals

    def predict_score(
        self,
        home_elo: float,
        away_elo: float,
        home_advantage: float = 0.0,
        away_advantage: float = 0.0,
        home_attack: float = 1.0,
        away_attack: float = 1.0,
        home_defense: float = 1.0,
        away_defense: float = 1.0,
    ) -> dict[str, Any]:
        home_lambda, away_lambda = self.expected_goals(
            home_elo,
            away_elo,
            home_advantage,
            away_advantage,
            home_attack,
            away_attack,
            home_defense,
            away_defense,
        )
        matrix = self.score_matrix(home_lambda, away_lambda)
        home_win = sum(row["probability"] for row in matrix if row["home_goals"] > row["away_goals"])
        draw = sum(row["probability"] for row in matrix if row["home_goals"] == row["away_goals"])
        away_win = sum(row["probability"] for row in matrix if row["home_goals"] < row["away_goals"])
        best_win = max(home_win, away_win)
        if draw >= best_win or best_win < self.win_confidence_threshold:
            outcome = "D"
        elif home_win >= away_win:
            outcome = "H"
        else:
            outcome = "A"
        home_goals, away_goals = self.representative_score(home_lambda, away_lambda, outcome)
        score = next(
            row
            for row in matrix
            if row["home_goals"] == home_goals and row["away_goals"] == away_goals
        )
        return {
            "home_goals": home_goals,
            "away_goals": away_goals,
            "score_probability": score["probability"],
            "home_lambda": home_lambda,
            "away_lambda": away_lambda,
            "home_win_90": home_win,
            "draw_90": draw,
            "away_win_90": away_win,
        }

    def advancing_team(self, prediction: dict[str, Any], home_team: str, away_team: str, home_elo: float, away_elo: float) -> tuple[str, str]:
        if prediction["home_goals"] > prediction["away_goals"]:
            return home_team, "90min"
        if prediction["away_goals"] > prediction["home_goals"]:
            return away_team, "90min"
        return (home_team, "pens") if home_elo >= away_elo else (away_team, "pens")
