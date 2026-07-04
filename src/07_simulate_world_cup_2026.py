"""
Run the first deterministic World Cup 2026 simulation.

Usage:
    python src/07_simulate_world_cup_2026.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tournament.world_cup_simulator import load_simulator, write_csv


OUT_DIR = BASE_DIR / "data" / "processed" / "simulations" / "world_cup_2026"


def finished_history_rows(outputs: dict[str, list[dict]]) -> list[dict]:
    rows = outputs["group_predictions"] + outputs["knockout_predictions"]
    fields = [
        "event_id", "stage", "match_number", "home_team", "away_team",
        "predicted_home_score", "predicted_away_score", "home_score", "away_score",
        "home_elo", "away_elo", "home_xg", "away_xg", "home_win_90", "draw_90",
        "away_win_90", "advancing_team", "venue",
    ]
    return [
        {field: row.get(field, "") for field in fields}
        for row in rows
        if row.get("result_source") == "actual"
    ]


def main() -> None:
    simulator = load_simulator(BASE_DIR)
    outputs = simulator.simulate()
    write_csv(OUT_DIR / "group_predictions.csv", outputs["group_predictions"])
    write_csv(OUT_DIR / "standings.csv", outputs["standings"])
    write_csv(OUT_DIR / "knockout_predictions.csv", outputs["knockout_predictions"])

    history_simulator = load_simulator(BASE_DIR)
    # Las predicciones originales de grupos usaban el Elo normal, antes de que
    # se introdujera la ponderacion extra para la forma del Mundial 2026.
    history_simulator.current_elo_weights["Group"] = 1.0
    history_outputs = history_simulator.simulate()
    write_csv(OUT_DIR / "prediction_history.csv", finished_history_rows(history_outputs))
    final = [row for row in outputs["knockout_predictions"] if row["stage"] == "Final"]
    champion = final[0]["advancing_team"] if final else "TBD"
    print(f"Group predictions: {len(outputs['group_predictions'])}")
    print(f"Knockout predictions: {len(outputs['knockout_predictions'])}")
    print(f"Champion: {champion}")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
