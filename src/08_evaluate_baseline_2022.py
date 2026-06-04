"""
Evaluate the first Elo + Poisson baseline on World Cup 2022.

Usage:
    python src/08_evaluate_baseline_2022.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from features.training_dataset import read_csv
from models.elo import EloSystem
from models.elo_poisson import EloPoissonModel
from tournament.world_cup_simulator import build_goal_profiles


TRAINING_PATH = BASE_DIR / "data" / "processed" / "training" / "world_cup_matches_1998_2022.csv"
HISTORY_PATH = BASE_DIR / "data" / "processed" / "features" / "world_cup_team_history.csv"


def result(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "H"
    if home_score < away_score:
        return "A"
    return "D"


def main() -> None:
    rows = read_csv(TRAINING_PATH)
    train = [row for row in rows if int(row["season_year"]) < 2022]
    test = [row for row in rows if int(row["season_year"]) == 2022]
    elo = EloSystem()
    model = EloPoissonModel()
    goal_profiles = build_goal_profiles(read_csv(HISTORY_PATH))
    elo.fit_transform(train)

    exact = 0
    result_hits = 0
    total = 0
    for row in test:
        home_profile = goal_profiles.get(row["home_team"], {"attack": 1.0, "defense": 1.0})
        away_profile = goal_profiles.get(row["away_team"], {"attack": 1.0, "defense": 1.0})
        pred = model.predict_score(
            elo.get(row["home_team"]),
            elo.get(row["away_team"]),
            home_attack=home_profile["attack"],
            away_attack=away_profile["attack"],
            home_defense=home_profile["defense"],
            away_defense=away_profile["defense"],
        )
        actual_home = int(row["home_score"])
        actual_away = int(row["away_score"])
        pred_home = int(pred["home_goals"])
        pred_away = int(pred["away_goals"])
        exact += int(pred_home == actual_home and pred_away == actual_away)
        result_hits += int(result(pred_home, pred_away) == result(actual_home, actual_away))
        total += 1
        elo.rate_match(row)

    print(f"Matches: {total}")
    print(f"Exact score accuracy: {exact / total:.3f} ({exact}/{total})")
    print(f"Result accuracy: {result_hits / total:.3f} ({result_hits}/{total})")


if __name__ == "__main__":
    main()
