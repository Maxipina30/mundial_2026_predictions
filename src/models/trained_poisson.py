from __future__ import annotations

from dataclasses import dataclass
from math import exp, factorial, log1p
from typing import Any

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from models.elo import EloSystem


FEATURE_COLUMNS = [
    "elo_diff",
    "fifa_points_diff",
    "fifa_rank_diff",
    "host_advantage_diff",
    "stage_importance",
    "home_attack_pre",
    "away_attack_pre",
    "home_defense_pre",
    "away_defense_pre",
    "home_experience_log",
    "away_experience_log",
    "log_participations_diff",
    "log_matches_diff",
    "log_wins_diff",
    "log_titles_diff",
    "log_finals_diff",
    "log_semi_finals_diff",
    "log_quarter_finals_diff",
    "win_rate_diff",
    "goals_for_per_match_diff",
    "goals_against_per_match_diff",
    "goal_diff_per_match_diff",
    "final_rate_diff",
    "semi_final_rate_diff",
    "quarter_final_rate_diff",
]

FEATURE_SETS = {
    "leakage_safe_attack_defense": [
        "elo_diff",
        "fifa_points_diff",
        "host_advantage_diff",
        "stage_importance",
        "home_attack_pre",
        "away_attack_pre",
        "home_defense_pre",
        "away_defense_pre",
        "home_experience_log",
        "away_experience_log",
    ],
    "base_elo_fifa": [
        "elo_diff",
        "fifa_points_diff",
        "fifa_rank_diff",
        "host_advantage_diff",
        "stage_importance",
    ],
    "compact_history": [
        "elo_diff",
        "fifa_points_diff",
        "fifa_rank_diff",
        "host_advantage_diff",
        "stage_importance",
        "log_matches_diff",
        "log_titles_diff",
        "log_finals_diff",
        "log_semi_finals_diff",
        "win_rate_diff",
        "goals_for_per_match_diff",
        "goals_against_per_match_diff",
        "goal_diff_per_match_diff",
    ],
    "history_ratios": [
        "elo_diff",
        "fifa_points_diff",
        "fifa_rank_diff",
        "host_advantage_diff",
        "stage_importance",
        "win_rate_diff",
        "goals_for_per_match_diff",
        "goals_against_per_match_diff",
        "goal_diff_per_match_diff",
        "final_rate_diff",
        "semi_final_rate_diff",
        "quarter_final_rate_diff",
    ],
    "deep_runs": [
        "elo_diff",
        "fifa_points_diff",
        "fifa_rank_diff",
        "host_advantage_diff",
        "stage_importance",
        "log_titles_diff",
        "log_finals_diff",
        "log_semi_finals_diff",
        "log_quarter_finals_diff",
        "final_rate_diff",
        "semi_final_rate_diff",
        "quarter_final_rate_diff",
    ],
    "all_features": FEATURE_COLUMNS,
}


def poisson_pmf(k: int, lam: float) -> float:
    return exp(-lam) * lam**k / factorial(k)


def stage_importance(stage: str) -> int:
    text = str(stage or "").lower()
    if "final" in text and "semi" not in text and "3rd" not in text:
        return 5
    if "3rd" in text or "third" in text:
        return 4
    if "semi" in text:
        return 4
    if "quarter" in text:
        return 3
    if "round of 16" in text:
        return 2
    if "round of 32" in text:
        return 1
    return 0


def safe_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def signed_log_diff(home_value: Any, away_value: Any) -> float:
    home = safe_float(home_value)
    away = safe_float(away_value)
    return log1p(home) - log1p(away)


def add_pre_match_elo(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    elo = EloSystem()
    enriched_rows: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: (item["match_date"], item["event_id"])):
        home = row["home_team"]
        away = row["away_team"]
        home_elo = elo.get(home)
        away_elo = elo.get(away)
        enriched = dict(row)
        enriched["home_elo_pre"] = home_elo
        enriched["away_elo_pre"] = away_elo
        enriched["elo_diff"] = home_elo - away_elo
        enriched_rows.append(enriched)
        elo.rate_match(row)
    return enriched_rows


def build_model_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    records = []
    for row in add_pre_match_elo(rows):
        home_matches = safe_float(row.get("home_world_cup_matches"))
        away_matches = safe_float(row.get("away_world_cup_matches"))
        home_participations = safe_float(row.get("home_world_cup_participations"))
        away_participations = safe_float(row.get("away_world_cup_participations"))
        home_wins = safe_float(row.get("home_world_cup_wins"))
        away_wins = safe_float(row.get("away_world_cup_wins"))
        home_goals_for = safe_float(row.get("home_world_cup_goals_for"))
        away_goals_for = safe_float(row.get("away_world_cup_goals_for"))
        home_goals_against = safe_float(row.get("home_world_cup_goals_against"))
        away_goals_against = safe_float(row.get("away_world_cup_goals_against"))
        home_goal_diff = safe_float(row.get("home_world_cup_goal_diff"))
        away_goal_diff = safe_float(row.get("away_world_cup_goal_diff"))
        home_finals = safe_float(row.get("home_world_cup_finals"))
        away_finals = safe_float(row.get("away_world_cup_finals"))
        home_semis = safe_float(row.get("home_world_cup_semi_finals"))
        away_semis = safe_float(row.get("away_world_cup_semi_finals"))
        home_quarters = safe_float(row.get("home_world_cup_quarter_finals"))
        away_quarters = safe_float(row.get("away_world_cup_quarter_finals"))
        home_attack = safe_rate(home_goals_for, home_matches)
        away_attack = safe_rate(away_goals_for, away_matches)
        home_defense = safe_rate(home_goals_against, home_matches)
        away_defense = safe_rate(away_goals_against, away_matches)

        records.append(
            {
                "event_id": row["event_id"],
                "season_year": int(row["season_year"]),
                "match_date": row["match_date"],
                "stage": row["stage"],
                "home_team": row["home_team"],
                "away_team": row["away_team"],
                "home_score": int(row["home_score"]),
                "away_score": int(row["away_score"]),
                "competition": row.get("competition", ""),
                "competition_group": row.get("competition_group", "world_cup"),
                "competition_weight": safe_float(row.get("competition_weight"), 1.0),
                "elo_diff": safe_float(row["elo_diff"]),
                "fifa_points_diff": safe_float(row.get("fifa_points_diff")),
                "fifa_rank_diff": safe_float(row.get("fifa_rank_diff")),
                "host_advantage_diff": safe_float(row.get("is_host_home")) - safe_float(row.get("is_host_away")),
                "stage_importance": stage_importance(str(row.get("stage"))),
                "home_attack_pre": home_attack,
                "away_attack_pre": away_attack,
                "home_defense_pre": home_defense,
                "away_defense_pre": away_defense,
                "home_experience_log": log1p(home_matches),
                "away_experience_log": log1p(away_matches),
                "log_participations_diff": signed_log_diff(home_participations, away_participations),
                "log_matches_diff": signed_log_diff(home_matches, away_matches),
                "log_wins_diff": signed_log_diff(home_wins, away_wins),
                "log_titles_diff": signed_log_diff(row.get("home_world_cup_titles"), row.get("away_world_cup_titles")),
                "log_finals_diff": signed_log_diff(home_finals, away_finals),
                "log_semi_finals_diff": signed_log_diff(home_semis, away_semis),
                "log_quarter_finals_diff": signed_log_diff(home_quarters, away_quarters),
                "win_rate_diff": safe_rate(home_wins, home_matches) - safe_rate(away_wins, away_matches),
                "goals_for_per_match_diff": safe_rate(home_goals_for, home_matches) - safe_rate(away_goals_for, away_matches),
                "goals_against_per_match_diff": safe_rate(home_goals_against, home_matches) - safe_rate(away_goals_against, away_matches),
                "goal_diff_per_match_diff": safe_rate(home_goal_diff, home_matches) - safe_rate(away_goal_diff, away_matches),
                "final_rate_diff": safe_rate(home_finals, home_participations) - safe_rate(away_finals, away_participations),
                "semi_final_rate_diff": safe_rate(home_semis, home_participations) - safe_rate(away_semis, away_participations),
                "quarter_final_rate_diff": safe_rate(home_quarters, home_participations) - safe_rate(away_quarters, away_participations),
            }
        )
    return pd.DataFrame.from_records(records)


def make_goal_model(alpha: float = 2.0) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("poisson", PoissonRegressor(alpha=alpha, max_iter=1000)),
        ]
    )


@dataclass
class TrainedPoissonModel:
    home_model: Pipeline
    away_model: Pipeline
    feature_columns: list[str]
    max_goals: int = 7

    @classmethod
    def fit(
        cls,
        frame: pd.DataFrame,
        alpha: float = 2.0,
        feature_columns: list[str] | None = None,
        use_sample_weight: bool = True,
    ) -> "TrainedPoissonModel":
        home_model = make_goal_model(alpha)
        away_model = make_goal_model(alpha)
        columns = feature_columns or FEATURE_COLUMNS
        x = frame[columns]
        fit_params = {}
        if use_sample_weight and "competition_weight" in frame.columns:
            fit_params["poisson__sample_weight"] = frame["competition_weight"]
        home_model.fit(x, frame["home_score"], **fit_params)
        away_model.fit(x, frame["away_score"], **fit_params)
        return cls(home_model=home_model, away_model=away_model, feature_columns=columns)

    def predict_lambdas(self, frame: pd.DataFrame) -> pd.DataFrame:
        x = frame[self.feature_columns]
        output = frame.copy()
        output["home_lambda"] = self.home_model.predict(x).clip(min=0.05)
        output["away_lambda"] = self.away_model.predict(x).clip(min=0.05)
        return output

    def score_matrix(self, home_lambda: float, away_lambda: float) -> list[dict[str, float | int]]:
        rows = []
        for home_goals in range(self.max_goals + 1):
            home_prob = poisson_pmf(home_goals, home_lambda)
            for away_goals in range(self.max_goals + 1):
                away_prob = poisson_pmf(away_goals, away_lambda)
                rows.append(
                    {
                        "home_goals": home_goals,
                        "away_goals": away_goals,
                        "probability": home_prob * away_prob,
                    }
                )
        total = sum(float(row["probability"]) for row in rows)
        for row in rows:
            row["probability"] = float(row["probability"]) / total
        return rows

    def predict_score_row(self, home_lambda: float, away_lambda: float) -> dict[str, float | int | str]:
        matrix = self.score_matrix(home_lambda, away_lambda)
        home_win = sum(float(row["probability"]) for row in matrix if row["home_goals"] > row["away_goals"])
        draw = sum(float(row["probability"]) for row in matrix if row["home_goals"] == row["away_goals"])
        away_win = sum(float(row["probability"]) for row in matrix if row["home_goals"] < row["away_goals"])
        best_score = max(matrix, key=lambda row: float(row["probability"]))
        if home_win >= draw and home_win >= away_win:
            result = "H"
        elif away_win >= draw:
            result = "A"
        else:
            result = "D"
        return {
            "pred_home_score": int(best_score["home_goals"]),
            "pred_away_score": int(best_score["away_goals"]),
            "score_probability": float(best_score["probability"]),
            "home_win_90": home_win,
            "draw_90": draw,
            "away_win_90": away_win,
            "pred_result": result,
        }

    def predict_matches(self, frame: pd.DataFrame) -> pd.DataFrame:
        output = self.predict_lambdas(frame)
        predictions = [
            self.predict_score_row(float(row.home_lambda), float(row.away_lambda))
            for row in output.itertuples(index=False)
        ]
        return pd.concat([output.reset_index(drop=True), pd.DataFrame(predictions)], axis=1)


def actual_result(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "H"
    if home_score < away_score:
        return "A"
    return "D"


def evaluate_predictions(predictions: pd.DataFrame) -> dict[str, float | int]:
    rows = predictions.copy()
    rows["actual_result"] = [
        actual_result(int(row.home_score), int(row.away_score))
        for row in rows.itertuples(index=False)
    ]
    rows["exact_hit"] = (rows["pred_home_score"] == rows["home_score"]) & (rows["pred_away_score"] == rows["away_score"])
    rows["result_hit"] = rows["pred_result"] == rows["actual_result"]
    rows["home_abs_error"] = (rows["home_lambda"] - rows["home_score"]).abs()
    rows["away_abs_error"] = (rows["away_lambda"] - rows["away_score"]).abs()
    return {
        "matches": int(len(rows)),
        "exact_accuracy": float(rows["exact_hit"].mean()),
        "result_accuracy": float(rows["result_hit"].mean()),
        "home_goal_mae": float(rows["home_abs_error"].mean()),
        "away_goal_mae": float(rows["away_abs_error"].mean()),
        "total_goal_mae": float((rows["home_abs_error"] + rows["away_abs_error"]).mean()),
    }
