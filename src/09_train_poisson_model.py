"""
Train and backtest the feature-based goal model.

Usage:
    python src/09_train_poisson_model.py
"""

import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from features.training_dataset import read_csv, write_csv
from models.trained_poisson import (
    FEATURE_COLUMNS,
    FEATURE_SETS,
    TrainedPoissonModel,
    build_model_frame,
    evaluate_predictions,
)


WORLD_CUP_TRAINING_PATH = BASE_DIR / "data" / "processed" / "training" / "world_cup_matches_1998_2022.csv"
OFFICIAL_TRAINING_PATH = BASE_DIR / "data" / "processed" / "training" / "official_international_matches_1998_2024.csv"
OUT_DIR = BASE_DIR / "data" / "processed" / "models" / "poisson_regression"
TEST_YEARS = [2014, 2018, 2022]


def build_backtests(
    frame: pd.DataFrame,
    feature_set_name: str,
    feature_columns: list[str],
) -> tuple[list[dict[str, float | int | str]], pd.DataFrame]:
    metric_rows: list[dict[str, float | int]] = []
    prediction_frames = []

    for test_year in TEST_YEARS:
        train = frame[frame["season_year"] < test_year]
        test = frame[(frame["season_year"] == test_year) & (frame["competition_group"] == "world_cup")]
        if train.empty or test.empty:
            continue

        model = TrainedPoissonModel.fit(train, feature_columns=feature_columns)
        predictions = model.predict_matches(test)
        metrics = evaluate_predictions(predictions)
        metric_rows.append(
            {
                "feature_set": feature_set_name,
                "feature_count": len(feature_columns),
                "test_year": test_year,
                **metrics,
            }
        )
        prediction_frames.append(predictions.assign(test_year=test_year, feature_set=feature_set_name))

    all_predictions = pd.concat(prediction_frames, ignore_index=True) if prediction_frames else pd.DataFrame()
    return metric_rows, all_predictions


def build_correlation_rows(frame: pd.DataFrame, threshold: float = 0.8) -> list[dict[str, object]]:
    corr = frame[FEATURE_COLUMNS].corr(numeric_only=True)
    rows = []
    for left_index, left in enumerate(FEATURE_COLUMNS):
        for right in FEATURE_COLUMNS[left_index + 1 :]:
            value = corr.loc[left, right]
            if pd.isna(value) or abs(value) < threshold:
                continue
            rows.append(
                {
                    "feature_a": left,
                    "feature_b": right,
                    "correlation": round(float(value), 6),
                    "abs_correlation": round(abs(float(value)), 6),
                }
            )
    return sorted(rows, key=lambda row: row["abs_correlation"], reverse=True)


def summarize_feature_sets(metric_rows: list[dict[str, float | int | str]]) -> list[dict[str, object]]:
    frame = pd.DataFrame(metric_rows)
    if frame.empty:
        return []
    grouped = frame.groupby(["feature_set", "feature_count"], as_index=False).agg(
        avg_exact_accuracy=("exact_accuracy", "mean"),
        avg_result_accuracy=("result_accuracy", "mean"),
        avg_total_goal_mae=("total_goal_mae", "mean"),
        min_result_accuracy=("result_accuracy", "min"),
        max_result_accuracy=("result_accuracy", "max"),
    )
    grouped = grouped.sort_values(
        ["avg_result_accuracy", "avg_total_goal_mae", "avg_exact_accuracy"],
        ascending=[False, True, False],
    )
    return serializable_rows(grouped)


def serializable_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    if frame.empty:
        return []
    output = frame.copy()
    for column in output.columns:
        if pd.api.types.is_float_dtype(output[column]):
            output[column] = output[column].round(6)
    return output.to_dict(orient="records")


def main() -> None:
    training_path = OFFICIAL_TRAINING_PATH if OFFICIAL_TRAINING_PATH.exists() else WORLD_CUP_TRAINING_PATH
    rows = read_csv(training_path)
    frame = build_model_frame(rows)
    metric_rows = []
    prediction_frames = []

    for feature_set_name, feature_columns in FEATURE_SETS.items():
        set_metrics, set_predictions = build_backtests(frame, feature_set_name, feature_columns)
        metric_rows.extend(set_metrics)
        if not set_predictions.empty:
            prediction_frames.append(set_predictions)

    predictions = pd.concat(prediction_frames, ignore_index=True) if prediction_frames else pd.DataFrame()
    summary_rows = summarize_feature_sets(metric_rows)
    correlation_rows = build_correlation_rows(frame)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "backtest_metrics.csv", metric_rows)
    write_csv(OUT_DIR / "feature_set_summary.csv", summary_rows)
    write_csv(OUT_DIR / "high_correlations.csv", correlation_rows)
    write_csv(
        OUT_DIR / "backtest_predictions.csv",
        serializable_rows(
            predictions[
                [
                    "test_year",
                    "feature_set",
                    "event_id",
                    "season_year",
                    "match_date",
                    "stage",
                    "competition",
                    "competition_group",
                    "competition_weight",
                    "home_team",
                    "away_team",
                    "home_score",
                    "away_score",
                    "home_lambda",
                    "away_lambda",
                    "pred_home_score",
                    "pred_away_score",
                    "score_probability",
                    "home_win_90",
                    "draw_90",
                    "away_win_90",
                    "pred_result",
                ]
            ]
        ),
    )

    print(f"Training data: {training_path}")
    print("Backtest metrics")
    for row in summary_rows:
        print(
            "{feature_set}: features={feature_count}, avg_exact={avg_exact_accuracy:.3f}, "
            "avg_result={avg_result_accuracy:.3f}, avg_total_goal_mae={avg_total_goal_mae:.3f}".format(**row)
        )
    print(f"High correlations: {len(correlation_rows)} pairs with |corr| >= 0.80")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
