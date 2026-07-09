from __future__ import annotations

import html
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components


BASE_DIR = Path(__file__).resolve().parents[1]
SIM_DIR = BASE_DIR / "data" / "processed" / "simulations" / "world_cup_2026"
GROUP_PREDICTIONS_PATH = SIM_DIR / "group_predictions.csv"
STANDINGS_PATH = SIM_DIR / "standings.csv"
KNOCKOUT_PATH = SIM_DIR / "knockout_predictions.csv"
HISTORY_PATH = SIM_DIR / "prediction_history.csv"

STAGE_ORDER = [
    "Round of 32",
    "Round of 16",
    "Quarterfinals",
    "Semifinals",
    "Match for 3rd place",
    "Final",
]


st.set_page_config(
    page_title="World Cup 2026 Predictor",
    page_icon="WC",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --panel-border: rgba(49, 51, 63, 0.18);
        --panel-soft: rgba(49, 51, 63, 0.055);
        --accent: #176b87;
        --accent-soft: rgba(23, 107, 135, 0.10);
    }
    .main .block-container {
        padding-top: 1.6rem;
        padding-bottom: 2rem;
        max-width: 1480px;
    }
    h1, h2, h3 {
        letter-spacing: 0;
    }
    .app-title {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        border-bottom: 1px solid var(--panel-border);
        padding-bottom: 0.8rem;
        margin-bottom: 1rem;
    }
    .app-title h1 {
        margin: 0;
        font-size: 2rem;
    }
    .subtle {
        color: rgba(49, 51, 63, 0.68);
        font-size: 0.95rem;
    }
    .metric-card {
        border: 1px solid var(--panel-border);
        border-radius: 8px;
        padding: 0.95rem 1rem;
        background: white;
        min-height: 108px;
    }
    .metric-label {
        color: rgba(49, 51, 63, 0.66);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.28rem;
    }
    .metric-value {
        font-size: 1.45rem;
        line-height: 1.15;
        font-weight: 700;
    }
    .metric-help {
        color: rgba(49, 51, 63, 0.68);
        font-size: 0.84rem;
        margin-top: 0.35rem;
    }
    .match-card {
        border: 1px solid var(--panel-border);
        border-radius: 8px;
        padding: 0.72rem 0.82rem;
        margin-bottom: 0.55rem;
        background: white;
    }
    .match-topline {
        display: flex;
        justify-content: space-between;
        gap: 0.7rem;
        color: rgba(49, 51, 63, 0.62);
        font-size: 0.78rem;
        margin-bottom: 0.38rem;
    }
    .scoreline {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
        align-items: center;
        gap: 0.6rem;
        font-weight: 700;
    }
    .score {
        background: var(--accent-soft);
        color: var(--accent);
        border-radius: 6px;
        min-width: 54px;
        text-align: center;
        padding: 0.18rem 0.5rem;
        font-variant-numeric: tabular-nums;
    }
    .team-left {
        text-align: right;
        white-space: normal;
        overflow-wrap: anywhere;
    }
    .team-right {
        text-align: left;
        white-space: normal;
        overflow-wrap: anywhere;
    }
    .winner {
        margin-top: 0.35rem;
        color: rgba(49, 51, 63, 0.75);
        font-size: 0.83rem;
    }
    .section-rule {
        border-top: 1px solid var(--panel-border);
        margin: 1.2rem 0 0.8rem;
    }
    .group-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 0.34rem;
    }
    .group-table th {
        color: rgba(49, 51, 63, 0.58);
        font-size: 0.74rem;
        font-weight: 700;
        padding: 0.18rem 0.45rem;
        text-transform: uppercase;
    }
    .group-table td {
        background: white;
        border-bottom: 1px solid rgba(49, 51, 63, 0.08);
        border-top: 1px solid rgba(49, 51, 63, 0.08);
        padding: 0.46rem 0.45rem;
        font-size: 0.88rem;
        font-variant-numeric: tabular-nums;
    }
    .group-table tr td:first-child {
        border-left: 4px solid transparent;
        border-radius: 7px 0 0 7px;
        text-align: center;
        width: 38px;
    }
    .group-table tr td:last-child {
        border-radius: 0 7px 7px 0;
    }
    .group-table .team-cell {
        font-weight: 700;
        min-width: 112px;
    }
    .group-table .pts-cell {
        font-size: 1.05rem;
        font-weight: 800;
        color: #172033;
    }
    .group-table .status-pill {
        border-radius: 999px;
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 700;
        padding: 0.14rem 0.48rem;
        white-space: nowrap;
    }
    .group-table tr.qualified td {
        background: #eef8f1;
    }
    .group-table tr.qualified td:first-child {
        border-left-color: #2f9e44;
    }
    .group-table tr.qualified .status-pill {
        background: #d6f1dd;
        color: #1f7a37;
    }
    .group-table tr.alive td {
        background: #fff9e8;
    }
    .group-table tr.alive td:first-child {
        border-left-color: #d99a00;
    }
    .group-table tr.alive .status-pill {
        background: #ffedbf;
        color: #8a5b00;
    }
    .group-table tr.out td {
        background: #fff1f1;
        color: rgba(49, 51, 63, 0.74);
    }
    .group-table tr.out td:first-child {
        border-left-color: #df4b4b;
    }
    .group-table tr.out .status-pill {
        background: #ffdada;
        color: #a52828;
    }
    .bracket-scroll {
        overflow-x: auto;
        padding-bottom: 0.5rem;
        width: 100%;
    }
    .bracket-svg {
        min-width: 1050px;
        width: 100%;
    }
    .bracket-label {
        fill: rgba(49, 51, 63, 0.64);
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
    }
    .bracket-line {
        fill: none;
        stroke: rgba(23, 107, 135, 0.72);
        stroke-width: 2;
    }
    .bracket-box {
        fill: white;
        stroke: rgba(49, 51, 63, 0.18);
        stroke-width: 1;
    }
    .bracket-row-winner {
        fill: #117a45;
    }
    .bracket-row-loser {
        fill: #ffffff;
    }
    .bracket-text-winner {
        fill: white;
        font-size: 12px;
        font-weight: 800;
    }
    .bracket-text-loser {
        fill: #213033;
        font-size: 12px;
    }
    .bracket-score-winner {
        fill: white;
        font-size: 12px;
        font-weight: 800;
        text-anchor: end;
    }
    .bracket-score-loser {
        fill: #213033;
        font-size: 12px;
        text-anchor: end;
    }
    .bracket-method {
        fill: rgba(49, 51, 63, 0.58);
        font-size: 10px;
    }
    .third-place-card {
        background: white;
        border: 1px solid var(--panel-border);
        border-radius: 8px;
        margin-top: 0.9rem;
        max-width: 320px;
        padding: 0.7rem 0.8rem;
    }
    .third-place-card h3 {
        color: rgba(49, 51, 63, 0.64);
        font-size: 0.8rem;
        margin: 0 0 0.45rem;
        text-transform: uppercase;
    }
    .third-place-row {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 0.55rem;
        padding: 0.12rem 0;
    }
    .third-place-row strong {
        font-weight: 800;
    }
    .third-place-score {
        background: var(--accent-soft);
        border-radius: 5px;
        color: var(--accent);
        font-weight: 800;
        min-width: 24px;
        text-align: center;
    }
    .old-bracket-grid {
        display: none;
        grid-template-columns: repeat(6, minmax(124px, 1fr));
        gap: 0.5rem;
        overflow-x: auto;
        padding-bottom: 0.5rem;
    }
    .bracket-stage h3 {
        color: rgba(49, 51, 63, 0.68);
        font-size: 0.84rem;
        margin: 0 0 0.55rem;
        text-transform: uppercase;
    }
    .bracket-card {
        background: white;
        border: 1px solid var(--panel-border);
        border-left: 4px solid var(--accent);
        border-radius: 8px;
        margin-bottom: 0.58rem;
        padding: 0.46rem 0.5rem;
    }
    .bracket-team {
        align-items: center;
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 0.45rem;
        line-height: 1.25;
        padding: 0.13rem 0;
    }
    .bracket-team span:first-child {
        overflow-wrap: anywhere;
    }
    .bracket-team .winner-name {
        font-weight: 800;
    }
    .bracket-score {
        background: var(--accent-soft);
        border-radius: 5px;
        color: var(--accent);
        font-weight: 800;
        min-width: 24px;
        padding: 0.08rem 0.34rem;
        text-align: center;
    }
    .bracket-meta {
        color: rgba(49, 51, 63, 0.56);
        font-size: 0.72rem;
        margin-top: 0.36rem;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--panel-border);
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def percent(value: float | int | None) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def fmt_number(value: float | int | None, decimals: int = 0) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):,.{decimals}f}"


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def top_scorelines(home_xg: float | int | None, away_xg: float | int | None, max_goals: int = 7, limit: int = 3) -> list[tuple[int, int, float]]:
    if pd.isna(home_xg) or pd.isna(away_xg):
        return []
    home_lambda = float(home_xg)
    away_lambda = float(away_xg)
    rows = []
    for home_goals in range(max_goals + 1):
        home_prob = poisson_pmf(home_goals, home_lambda)
        for away_goals in range(max_goals + 1):
            rows.append((home_goals, away_goals, home_prob * poisson_pmf(away_goals, away_lambda)))
    total = sum(row[2] for row in rows)
    if total <= 0:
        return []
    return sorted(
        [(home, away, probability / total) for home, away, probability in rows],
        key=lambda row: row[2],
        reverse=True,
    )[:limit]


def esc(value: object) -> str:
    if pd.isna(value):
        return ""
    return html.escape(str(value))


def tooltip_text(row: pd.Series) -> str:
    lines = [
        f"#{int(row['match_number'])} | {row['stage']}",
        f"{row['home_team']} vs {row['away_team']}",
        f"xG: {fmt_number(row['home_xg'], 2)} - {fmt_number(row['away_xg'], 2)}",
        f"90m: {percent(row['home_win_90'])} local | {percent(row['draw_90'])} empate | {percent(row['away_win_90'])} visita",
    ]
    if row.get("advancing_team"):
        lines.append(f"Avanza: {row['advancing_team']} ({row.get('advance_method', '')})")
    likely = top_scorelines(row.get("home_xg"), row.get("away_xg"))
    if likely:
        lines.append("Marcadores mas probables:")
        lines.extend(f"{home}-{away}: {probability * 100:.1f}%" for home, away, probability in likely)
    return "\n".join(lines)


def load_simulation() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing = [
        path
        for path in (GROUP_PREDICTIONS_PATH, STANDINGS_PATH, KNOCKOUT_PATH, HISTORY_PATH)
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(
            "Faltan archivos de simulacion: "
            + ", ".join(str(path.relative_to(BASE_DIR)) for path in missing)
        )
    groups = pd.read_csv(GROUP_PREDICTIONS_PATH)
    standings = pd.read_csv(STANDINGS_PATH)
    knockout = pd.read_csv(KNOCKOUT_PATH)
    history = pd.read_csv(HISTORY_PATH)
    return groups, standings, knockout, history


def result_code(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "Local"
    if away_score > home_score:
        return "Visitante"
    return "Empate"


def evaluated_history(history: pd.DataFrame) -> pd.DataFrame:
    evaluated = history.copy()
    score_columns = ["predicted_home_score", "predicted_away_score", "home_score", "away_score"]
    evaluated[score_columns] = evaluated[score_columns].astype(int)
    evaluated["predicted_result"] = evaluated.apply(
        lambda row: result_code(row["predicted_home_score"], row["predicted_away_score"]), axis=1
    )
    evaluated["actual_result"] = evaluated.apply(
        lambda row: result_code(row["home_score"], row["away_score"]), axis=1
    )
    evaluated["result_hit"] = evaluated["predicted_result"] == evaluated["actual_result"]
    evaluated["exact_hit"] = (
        (evaluated["predicted_home_score"] == evaluated["home_score"])
        & (evaluated["predicted_away_score"] == evaluated["away_score"])
    )
    evaluated["goal_difference_hit"] = (
        evaluated["result_hit"]
        & ~evaluated["exact_hit"]
        & (
            evaluated["predicted_home_score"] - evaluated["predicted_away_score"]
            == evaluated["home_score"] - evaluated["away_score"]
        )
    )
    knockout_scoring = (3, 5, 8)
    scoring = {
        "Group": (2, 3, 5),
        "Round of 32": knockout_scoring,
        "Round of 16": knockout_scoring,
        "Quarterfinals": knockout_scoring,
        "Semifinals": knockout_scoring,
        "Match for 3rd place": knockout_scoring,
        "Final": knockout_scoring,
    }

    def pool_score(row: pd.Series) -> int:
        result_points, difference_points, exact_points = scoring.get(row["stage"], (0, 0, 0))
        if row["exact_hit"]:
            return exact_points
        if row["goal_difference_hit"]:
            return difference_points
        if row["result_hit"]:
            return result_points
        return 0

    evaluated["pool_points"] = evaluated.apply(pool_score, axis=1)
    return evaluated


def run_simulation() -> tuple[bool, str]:
    script = BASE_DIR / "src" / "07_simulate_world_cup_2026.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return result.returncode == 0, output


def metric_card(label: str, value: str, help_text: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_match_card(row: pd.Series, show_stage: bool = True) -> None:
    score = f"{int(row['home_score'])}-{int(row['away_score'])}"
    stage = row.get("stage", "")
    venue = row.get("venue", "")
    match_no = row.get("match_number", "")
    event_id = row.get("event_id", "")
    title_left = f"{stage}" if show_stage else f"Match {event_id}"
    title_right = f"#{int(match_no)}" if not pd.isna(match_no) and str(match_no) else venue
    details = []
    if "home_xg" in row and "away_xg" in row:
        details.append(f"xG: {fmt_number(row['home_xg'], 2)} / {fmt_number(row['away_xg'], 2)}")
    if "home_win_90" in row:
        details.append(f"90m: {percent(row['home_win_90'])} / {percent(row['draw_90'])} / {percent(row['away_win_90'])}")
    if "score_probability" in row:
        details.append(f"score prob {percent(row['score_probability'])}")
    if "advancing_team" in row and pd.notna(row["advancing_team"]) and row["advancing_team"]:
        details.append(f"advances {row['advancing_team']}")
    info = " | ".join(details)
    st.markdown(
        f"""
        <div class="match-card">
            <div class="match-topline">
                <span>{title_left}</span>
                <span>{title_right}</span>
            </div>
            <div class="scoreline">
                <div class="team-left">{row['home_team']}</div>
                <div class="score">{score}</div>
                <div class="team-right">{row['away_team']}</div>
            </div>
            <div class="winner">{info}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_team_strength(groups: pd.DataFrame, knockout: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for frame in (groups, knockout):
        for side in ("home", "away"):
            rows.append(
                frame[
                    [
                        f"{side}_team",
                        f"{side}_elo",
                    ]
                ].rename(columns={f"{side}_team": "team", f"{side}_elo": "elo"})
            )
    teams = pd.concat(rows, ignore_index=True)
    return (
        teams.dropna()
        .groupby("team", as_index=False)["elo"]
        .max()
        .sort_values("elo", ascending=False)
    )


def get_final_row(knockout: pd.DataFrame) -> pd.Series | None:
    final = knockout[knockout["stage"] == "Final"]
    if final.empty:
        return None
    return final.iloc[0]


def podium_rows(knockout: pd.DataFrame) -> list[tuple[str, str]]:
    final = get_final_row(knockout)
    third = knockout[knockout["stage"] == "Match for 3rd place"]
    champion = final["advancing_team"] if final is not None else "TBD"
    runner_up = (
        final["away_team"] if final is not None and final["home_team"] == champion else final["home_team"]
    ) if final is not None else "TBD"
    third_team = third.iloc[0]["advancing_team"] if not third.empty else "TBD"
    fourth_team = ""
    if not third.empty:
        third_row = third.iloc[0]
        fourth_team = third_row["away_team"] if third_row["home_team"] == third_team else third_row["home_team"]
    return [
        ("1", champion),
        ("2", runner_up),
        ("3", third_team),
        ("4", fourth_team or "TBD"),
    ]


def qualification_statuses(standings_frame: pd.DataFrame) -> dict[str, str]:
    statuses = {team: "out" for team in standings_frame["team"].dropna()}
    for _, row in standings_frame[standings_frame["position"] <= 2].iterrows():
        statuses[row["team"]] = "qualified"

    thirds = standings_frame[standings_frame["position"] == 3].copy()
    if not thirds.empty:
        thirds = thirds.sort_values(
            ["points", "goal_diff", "goals_for", "team"],
            ascending=[False, False, False, True],
        ).head(8)
        for _, row in thirds.iterrows():
            statuses[row["team"]] = "alive"
    return statuses


def render_group_table(table: pd.DataFrame, statuses: dict[str, str]) -> None:
    labels = {
        "qualified": "Clasifica",
        "alive": "Clasifica 3°",
        "out": "Fuera",
    }
    headers = ["#", "Equipo", "Pts", "PJ", "G", "E", "P", "GF", "GC", "DG", "Estado"]
    rows = []
    for _, row in table.iterrows():
        status = statuses.get(row["team"], "out")
        rows.append(
            f"<tr class=\"{status}\">"
            f"<td>{int(row['position'])}</td>"
            f"<td class=\"team-cell\">{esc(row['team'])}</td>"
            f"<td class=\"pts-cell\">{int(row['points'])}</td>"
            f"<td>{int(row['played'])}</td>"
            f"<td>{int(row['wins'])}</td>"
            f"<td>{int(row['draws'])}</td>"
            f"<td>{int(row['losses'])}</td>"
            f"<td>{int(row['goals_for'])}</td>"
            f"<td>{int(row['goals_against'])}</td>"
            f"<td>{int(row['goal_diff'])}</td>"
            f"<td><span class=\"status-pill\">{labels[status]}</span></td>"
            "</tr>"
        )
    header_html = "".join(f"<th>{header}</th>" for header in headers)
    st.markdown(
        f"<div class=\"table-wrap\"><table class=\"group-table\"><thead><tr>{header_html}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_bracket(knockout: pd.DataFrame) -> None:
    bracket_stages = [stage for stage in STAGE_ORDER if stage != "Match for 3rd place"]
    rows_by_match = {
        int(row["match_number"]): row
        for _, row in knockout[knockout["stage"].isin(bracket_stages)].iterrows()
    }
    stage_match_numbers = {
        stage: [
            int(match_number)
            for match_number in knockout[knockout["stage"] == stage]
            .sort_values("match_number")["match_number"]
            .tolist()
        ]
        for stage in bracket_stages
    }

    def feeder_numbers(row: pd.Series, previous_stage: str) -> list[int]:
        numbers: list[int] = []
        previous_numbers = stage_match_numbers[previous_stage]
        for slot, team in (
            (row.get("source_home_slot", ""), row.get("home_team", "")),
            (row.get("source_away_slot", ""), row.get("away_team", "")),
        ):
            number = None
            if isinstance(slot, str) and slot.startswith("W") and slot[1:].isdigit():
                candidate = int(slot[1:])
                if candidate in previous_numbers:
                    number = candidate
            if number is None:
                number = next(
                    (
                        candidate
                        for candidate in previous_numbers
                        if rows_by_match[candidate].get("advancing_team", "") == team
                    ),
                    None,
                )
            if number is not None and number not in numbers:
                numbers.append(number)
        return numbers

    ordered_numbers = {bracket_stages[-1]: stage_match_numbers[bracket_stages[-1]]}
    for stage_index in range(len(bracket_stages) - 2, -1, -1):
        next_stage = bracket_stages[stage_index + 1]
        current_stage = bracket_stages[stage_index]
        order = []
        for match_number in ordered_numbers[next_stage]:
            row = rows_by_match[match_number]
            for source_number in feeder_numbers(row, current_stage):
                if source_number not in order:
                    order.append(source_number)
        order.extend(number for number in stage_match_numbers[current_stage] if number not in order)
        ordered_numbers[current_stage] = order

    stage_matches = {
        stage: pd.DataFrame([rows_by_match[number] for number in ordered_numbers[stage]]).reset_index(drop=True)
        for stage in bracket_stages
    }
    box_width = 145
    box_height = 43
    row_gap = 20
    col_gap = 34
    label_height = 26
    x_positions = [idx * (box_width + col_gap) for idx in range(len(bracket_stages))]
    r32_count = max(1, len(stage_matches["Round of 32"]))
    height = label_height + r32_count * box_height + (r32_count - 1) * row_gap + 8
    width = x_positions[-1] + box_width + 4

    positions: dict[str, list[tuple[float, float]]] = {}
    match_positions: dict[int, tuple[float, float]] = {}
    for stage_index, stage in enumerate(bracket_stages):
        matches = stage_matches[stage]
        if stage_index == 0:
            centers = [
                label_height + idx * (box_height + row_gap) + box_height / 2
                for idx in range(len(matches))
            ]
        else:
            centers = []
            for idx, row in matches.iterrows():
                previous_stage = bracket_stages[stage_index - 1]
                source_centers = [
                    match_positions[number][1]
                    for number in feeder_numbers(row, previous_stage)
                    if number in match_positions
                ]
                if len(source_centers) == 2:
                    centers.append(sum(source_centers) / 2)
                else:
                    centers.append(label_height + idx * (box_height + row_gap) + box_height / 2)
        positions[stage] = [(x_positions[stage_index], center) for center in centers]
        for idx, row in matches.iterrows():
            match_positions[int(row["match_number"])] = positions[stage][idx]

    lines = []
    for stage_index, stage in enumerate(bracket_stages[1:], start=1):
        for idx, (x, center) in enumerate(positions[stage]):
            left_x = x
            mid_x = left_x - col_gap / 2
            row = stage_matches[stage].iloc[idx]
            previous_stage = bracket_stages[stage_index - 1]
            for source_number in feeder_numbers(row, previous_stage):
                source_position = match_positions.get(source_number)
                if not source_position:
                    continue
                prev_x, prev_center = source_position
                start_x = prev_x + box_width
                lines.append(
                    f'<path class="bracket-line" d="M {start_x:.1f} {prev_center:.1f} H {mid_x:.1f} V {center:.1f} H {left_x:.1f}" />'
                )

    labels = [
        f'<text class="bracket-label" x="{x_positions[idx]}" y="15">{esc(stage.upper())}</text>'
        for idx, stage in enumerate(bracket_stages)
    ]

    boxes = []
    for stage in bracket_stages:
        for idx, row in stage_matches[stage].iterrows():
            x, center = positions[stage][idx]
            y = center - box_height / 2
            home_winner = row["advancing_team"] == row["home_team"]
            away_winner = row["advancing_team"] == row["away_team"]
            tooltip = esc(tooltip_text(row))
            boxes.append(
                f"""
                <g class="bracket-match" data-tooltip="{tooltip}">
                    <rect class="bracket-box" x="{x:.1f}" y="{y:.1f}" width="{box_width}" height="{box_height}" rx="5" />
                    <rect class="{'bracket-row-winner' if home_winner else 'bracket-row-loser'}" x="{x + 1:.1f}" y="{y + 1:.1f}" width="{box_width - 2}" height="18" rx="4" />
                    <rect class="{'bracket-row-winner' if away_winner else 'bracket-row-loser'}" x="{x + 1:.1f}" y="{y + 20:.1f}" width="{box_width - 2}" height="18" rx="4" />
                    <text class="{'bracket-text-winner' if home_winner else 'bracket-text-loser'}" x="{x + 7:.1f}" y="{y + 14:.1f}">{esc(short_team(row['home_team']))}</text>
                    <text class="{'bracket-score-winner' if home_winner else 'bracket-score-loser'}" x="{x + box_width - 7:.1f}" y="{y + 14:.1f}">{int(row['home_score'])}</text>
                    <text class="{'bracket-text-winner' if away_winner else 'bracket-text-loser'}" x="{x + 7:.1f}" y="{y + 33:.1f}">{esc(short_team(row['away_team']))}</text>
                    <text class="{'bracket-score-winner' if away_winner else 'bracket-score-loser'}" x="{x + box_width - 7:.1f}" y="{y + 33:.1f}">{int(row['away_score'])}</text>
                </g>
                """
            )

    third_html = ""
    third = knockout[knockout["stage"] == "Match for 3rd place"]
    if not third.empty:
        row = third.iloc[0]
        home_winner = row["advancing_team"] == row["home_team"]
        away_winner = row["advancing_team"] == row["away_team"]
        tooltip = esc(tooltip_text(row))
        third_html = (
            f'<div class="third-place-card tooltip-trigger" data-tooltip="{tooltip}"><h3>Tercer lugar</h3>'
            f'<div class="third-place-row"><span>{"<strong>" if home_winner else ""}{esc(row["home_team"])}{"</strong>" if home_winner else ""}</span><span class="third-place-score">{int(row["home_score"])}</span></div>'
            f'<div class="third-place-row"><span>{"<strong>" if away_winner else ""}{esc(row["away_team"])}{"</strong>" if away_winner else ""}</span><span class="third-place-score">{int(row["away_score"])}</span></div>'
            f'<div class="bracket-meta">{esc(row.get("advance_method", ""))}</div></div>'
        )

    svg = (
        f"""
        <style>
            body {{ margin: 0; font-family: "Segoe UI", Arial, sans-serif; color: #213033; }}
            .bracket-scroll {{ overflow-x: auto; padding-bottom: 8px; width: 100%; }}
            .bracket-svg {{ min-width: 1050px; width: 100%; }}
            .bracket-label {{ fill: rgba(49, 51, 63, 0.64); font-size: 12px; font-weight: 700; }}
            .bracket-line {{ fill: none; stroke: rgba(23, 107, 135, 0.72); stroke-width: 2; }}
            .bracket-match, .tooltip-trigger {{ cursor: help; }}
            .bracket-match:hover .bracket-box {{ stroke: #176b87; stroke-width: 2; }}
            .bracket-box {{ fill: white; stroke: rgba(49, 51, 63, 0.18); stroke-width: 1; }}
            .bracket-row-winner {{ fill: #117a45; }}
            .bracket-row-loser {{ fill: #ffffff; }}
            .bracket-text-winner {{ fill: white; font-size: 12px; font-weight: 800; }}
            .bracket-text-loser {{ fill: #213033; font-size: 12px; }}
            .bracket-score-winner {{ fill: white; font-size: 12px; font-weight: 800; text-anchor: end; }}
            .bracket-score-loser {{ fill: #213033; font-size: 12px; text-anchor: end; }}
            .third-place-card {{ background: white; border: 1px solid rgba(49, 51, 63, 0.18); border-radius: 8px; margin-top: 12px; max-width: 320px; padding: 11px 13px; }}
            .third-place-card h3 {{ color: rgba(49, 51, 63, 0.64); font-size: 13px; margin: 0 0 7px; text-transform: uppercase; }}
            .third-place-row {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 9px; padding: 2px 0; }}
            .third-place-row strong {{ font-weight: 800; }}
            .third-place-score {{ background: #e7f1f4; border-radius: 5px; color: #176b87; font-weight: 800; min-width: 24px; text-align: center; }}
            .bracket-meta {{ color: rgba(49, 51, 63, 0.58); font-size: 11px; margin-top: 6px; }}
            .bracket-tooltip {{
                background: rgba(18, 32, 37, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 7px;
                box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
                color: white;
                display: none;
                font-size: 12px;
                line-height: 1.35;
                max-width: 280px;
                padding: 9px 10px;
                pointer-events: none;
                position: fixed;
                white-space: pre-line;
                z-index: 20;
            }}
        </style>
        <div class="bracket-scroll">
            <svg class="bracket-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Llave eliminatoria proyectada">
                {"".join(lines)}{"".join(labels)}{"".join(boxes)}
            </svg>
        </div>
        {third_html}
        <div id="bracket-tooltip" class="bracket-tooltip"></div>
        <script>
            const tooltip = document.getElementById("bracket-tooltip");
            document.querySelectorAll(".bracket-match, .tooltip-trigger").forEach((match) => {{
                match.addEventListener("mouseenter", () => {{
                    tooltip.textContent = match.dataset.tooltip;
                    tooltip.style.display = "block";
                }});
                match.addEventListener("mousemove", (event) => {{
                    const offset = 14;
                    const tooltipWidth = tooltip.offsetWidth || 260;
                    const tooltipHeight = tooltip.offsetHeight || 130;
                    let left = event.clientX + offset;
                    let top = event.clientY + offset;
                    if (left + tooltipWidth > window.innerWidth - 8) left = event.clientX - tooltipWidth - offset;
                    if (top + tooltipHeight > window.innerHeight - 8) top = event.clientY - tooltipHeight - offset;
                    tooltip.style.left = `${{Math.max(8, left)}}px`;
                    tooltip.style.top = `${{Math.max(8, top)}}px`;
                }});
                match.addEventListener("mouseleave", () => {{
                    tooltip.style.display = "none";
                }});
            }});
        </script>
        """
    )
    components.html(svg, height=min(920, height + 150), scrolling=True)


def short_team(team: object, max_len: int = 16) -> str:
    text = str(team)
    return text if len(text) <= max_len else text[: max_len - 1] + "."


try:
    group_predictions, standings, knockout_predictions, prediction_history = load_simulation()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.code("python src/07_simulate_world_cup_2026.py", language="powershell")
    st.stop()


with st.sidebar:
    st.header("Controles")
    if st.button("Recalcular simulacion", width="stretch"):
        ok, output = run_simulation()
        if ok:
            st.cache_data.clear()
            st.success("Simulacion actualizada.")
            st.code(output.strip() or "Listo.", language="text")
            st.rerun()
        st.error("No se pudo recalcular la simulacion.")
        st.code(output.strip(), language="text")

    st.divider()
    st.caption("Fuente actual")
    st.write(str(SIM_DIR.relative_to(BASE_DIR)))
    st.caption("Modo")
    st.write("Baseline deterministico Elo + Poisson")


st.markdown(
    """
    <div class="app-title">
        <h1>World Cup 2026 Predictor</h1>
        <div class="subtle">Simulacion completa desde fase de grupos hasta la final</div>
    </div>
    """,
    unsafe_allow_html=True,
)

final_row = get_final_row(knockout_predictions)
champion = final_row["advancing_team"] if final_row is not None else "TBD"
runner_up = (
    final_row["away_team"] if final_row is not None and final_row["home_team"] == champion else final_row["home_team"]
) if final_row is not None else "TBD"
final_score = (
    f"{final_row['home_team']} {int(final_row['home_score'])}-{int(final_row['away_score'])} {final_row['away_team']}"
    if final_row is not None
    else "TBD"
)
third_place = knockout_predictions[knockout_predictions["stage"] == "Match for 3rd place"]
third = third_place.iloc[0]["advancing_team"] if not third_place.empty else "TBD"

summary_cols = st.columns(4)
with summary_cols[0]:
    metric_card("Campeon", champion, f"Finalista: {runner_up}")
with summary_cols[1]:
    metric_card("Final", final_score, final_row["venue"] if final_row is not None else "")
with summary_cols[2]:
    metric_card("Tercer lugar", third, "Ganador del partido por el 3er puesto")
with summary_cols[3]:
    metric_card(
        "Total simulado",
        str(len(group_predictions) + len(knockout_predictions)),
        f"{len(group_predictions)} grupos + {len(knockout_predictions)} eliminatoria",
    )

tab_overview, tab_groups, tab_bracket, tab_history, tab_methodology = st.tabs(
    ["Resumen", "Grupos", "Eliminatoria", "Historial", "Metodologia"]
)

with tab_overview:
    st.subheader("Prediccion principal")
    final_method = final_row.get("advance_method", "") if final_row is not None else ""
    final_help = f"{champion} avanza por {final_method}" if final_method else ""
    metric_card("Campeon", champion, final_help)

    col_final, col_podium = st.columns([1.05, 1])
    with col_final:
        st.subheader("Final proyectada")
        if final_row is not None:
            render_match_card(final_row)
        else:
            st.info("Final pendiente.")
    with col_podium:
        st.subheader("Podio")
        podium_html = "".join(
            f'<div class="third-place-row"><span>{place}. {esc(team)}</span></div>'
            for place, team in podium_rows(knockout_predictions)
        )
        st.markdown(f'<div class="third-place-card">{podium_html}</div>', unsafe_allow_html=True)

with tab_groups:
    group_statuses = qualification_statuses(standings)
    group_order = sorted(standings["group_sign"].dropna().unique())
    selected_group = st.selectbox("Grupo", group_order, index=0)
    group_games = group_predictions[group_predictions["group_sign"] == selected_group]
    group_table = standings[standings["group_sign"] == selected_group].sort_values("position")

    col_table, col_games = st.columns([1.05, 1])
    with col_table:
        st.subheader(f"Tabla Grupo {selected_group}")
        render_group_table(group_table, group_statuses)
    with col_games:
        st.subheader("Juegos del grupo")
        for _, row in group_games.iterrows():
            render_match_card(row, show_stage=False)

    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.subheader("Todas las posiciones")
    all_tables = standings.sort_values(["group_sign", "position"])
    for group in group_order:
        st.markdown(f"**Grupo {group}**")
        render_group_table(all_tables[all_tables["group_sign"] == group], group_statuses)

with tab_bracket:
    st.subheader("Llave proyectada")
    render_bracket(knockout_predictions)

with tab_history:
    history = evaluated_history(prediction_history)
    total = len(history)
    result_hits = int(history["result_hit"].sum())
    exact_hits = int(history["exact_hit"].sum())
    pool_points = int(history["pool_points"].sum())

    st.subheader("Rendimiento de las predicciones")
    history_cols = st.columns(4)
    with history_cols[0]:
        metric_card("Partidos evaluados", str(total), "Sólo partidos ya finalizados")
    with history_cols[1]:
        metric_card("Resultados acertados", f"{result_hits}/{total}", percent(result_hits / total) if total else "0%")
    with history_cols[2]:
        metric_card("Marcadores exactos", f"{exact_hits}/{total}", percent(exact_hits / total) if total else "0%")
    with history_cols[3]:
        metric_card("Puntos de la polla", str(pool_points), "Grupos 2/3/5 · eliminatorias 3/5/8")

    st.caption(
        "Puntaje: resultado correcto / diferencia de gol correcta / marcador exacto. "
        "Fase de grupos: 2 / 3 / 5 puntos. Eliminatorias: 3 / 5 / 8 puntos."
    )

    st.caption(
        "Para respetar las predicciones originales, la fase de grupos se reconstruye "
        "con ponderación Elo normal (1.0), sin el ajuste adicional usado posteriormente."
    )

    stage_summary = (
        history.groupby("stage", as_index=False)
        .agg(
            partidos=("event_id", "count"),
            resultados_acertados=("result_hit", "sum"),
            diferencias_acertadas=("goal_difference_hit", "sum"),
            exactos=("exact_hit", "sum"),
            puntos=("pool_points", "sum"),
        )
    )
    stage_summary["% resultado"] = (stage_summary["resultados_acertados"] / stage_summary["partidos"] * 100).round(1)
    stage_summary["% exacto"] = (stage_summary["exactos"] / stage_summary["partidos"] * 100).round(1)
    st.dataframe(stage_summary, width="stretch", hide_index=True)

    detail = history[
        ["stage", "home_team", "away_team", "predicted_home_score", "predicted_away_score", "home_score", "away_score", "result_hit", "goal_difference_hit", "exact_hit", "pool_points"]
    ].copy()
    detail["Predicción"] = detail["predicted_home_score"].astype(str) + "-" + detail["predicted_away_score"].astype(str)
    detail["Resultado real"] = detail["home_score"].astype(str) + "-" + detail["away_score"].astype(str)
    detail = detail.rename(columns={"stage": "Fase", "home_team": "Local", "away_team": "Visitante", "result_hit": "Acierta resultado", "goal_difference_hit": "Acierta diferencia", "exact_hit": "Exacto", "pool_points": "Puntos"})
    st.subheader("Detalle por partido")
    st.dataframe(detail[["Fase", "Local", "Visitante", "Predicción", "Resultado real", "Acierta resultado", "Acierta diferencia", "Exacto", "Puntos"]], width="stretch", hide_index=True)

with tab_methodology:
    st.subheader("Como se calculan las predicciones")
    st.markdown(
        """
        El modelo es un **Elo-Poisson con perfil ofensivo/defensivo** (Maher
        independiente): un sistema tipo Elo entrega un rating de fuerza, ese rating
        se transforma en goles esperados (lambda) ajustados por ataque y defensa de
        cada seleccion, y los goles de cada equipo se modelan con Poissons
        independientes.

        Para cada partido el modelo sigue tres pasos:

        ```text
        1. Calcular un rating de fuerza para cada seleccion
        2. Convertir el rating en goles esperados (lambda)
        3. Convertir lambda en probabilidades con Poisson
        ```

        ---

        **1. Rating**

        El rating es una mezcla de dos fuentes:

        ```text
        rating = 0.40 * elo_mundialista + 0.60 * rating_fifa
        ```

        - **Elo mundialista**: entrenado con todos los partidos de Mundiales desde 1930.
          Cada seleccion empieza en 1500 y sube o baja segun gane, empate o pierda. Los
          Mundiales recientes pesan mas que los antiguos.
        - **Rating FIFA**: parte del ranking FIFA actual, centrado en 1500 contra el
          promedio de puntos FIFA de las 48 selecciones del torneo. Esto sirve para
          valorar selecciones con poca o nula historia mundialista.

        Aparte del rating, cada seleccion tiene un perfil ofensivo y defensivo. El
        perfil combina historia mundialista y forma actual:

        ```text
        perfil_goles = 0.70 * perfil_historico + 0.30 * perfil_mundial_2026
        ```

        El perfil historico se calcula asi:

        ```text
        ataque  = (goles_a_favor   / partidos) * factor_experiencia
        defensa = (goles_en_contra / partidos) / factor_experiencia
        ```

        - Los goles a favor y en contra se cuentan sobre todos los Mundiales (recientes
          pesan mas) y se suavizan para que pocas participaciones no distorsionen.
        - El `factor_experiencia` vale entre `0.62` (debutantes) y `1.0` (selecciones
          con 18+ participaciones). Las debutantes anotan menos y reciben mas; las
          experimentadas no tienen penalizacion.
        - La forma actual usa los partidos reales de fase de grupos, 16avos y 8vos de 2026,
          con suavizado propio para capturar rendimiento reciente sin sobrerreaccionar.

        ---

        **2. Goles esperados (lambda)**

        La diferencia de rating se convierte en `lambda` (goles esperados), multiplicada
        por el ataque del local y la defensa del rival:

        ```text
        diff = rating_local - rating_visitante

        lambda_local =
            1.25
          * exp(diff / 750)
          * ataque_local
          * defensa_visitante

        lambda_visitante =
            1.25
          * exp(-diff / 750)
          * ataque_visitante
          * defensa_local
        ```

        El `1.25` es el promedio de goles por equipo en Mundiales recientes. El `750`
        controla que tan rapido la diferencia de rating se traduce en goles.

        ---

        **3. Poisson**

        Cada `lambda` se convierte en probabilidades de marcar 0, 1, 2... goles
        usando la distribucion de Poisson:

        ```text
        P(k goles) = e^(-lambda) * lambda^k / k!
        ```

        Combinando los dos equipos sale una matriz de marcadores. Tomemos como ejemplo
        un partido real del torneo: **England vs Croatia**, con
        `lambda_England = 1.50` y `lambda_Croatia = 0.79`.
        """
    )

    _home_team = "England"
    _away_team = "Croatia"
    _lambda_home = 1.50
    _lambda_away = 0.79
    _max_goals = 5

    def _poisson_pmf(k: int, lam: float) -> float:
        return math.exp(-lam) * lam**k / math.factorial(k)

    _home_probs = [_poisson_pmf(k, _lambda_home) for k in range(_max_goals + 1)]
    _away_probs = [_poisson_pmf(k, _lambda_away) for k in range(_max_goals + 1)]
    _matrix = [
        [_home_probs[i] * _away_probs[j] * 100 for j in range(_max_goals + 1)]
        for i in range(_max_goals + 1)
    ]

    _fig_matrix = px.imshow(
        _matrix,
        labels=dict(
            x=f"Goles {_away_team}",
            y=f"Goles {_home_team}",
            color="Probabilidad %",
        ),
        x=list(range(_max_goals + 1)),
        y=list(range(_max_goals + 1)),
        color_continuous_scale=["#f5f9fa", "#176b87"],
        text_auto=".1f",
        aspect="auto",
        zmin=0,
    )
    _fig_matrix.update_xaxes(side="top", title_standoff=10)
    _fig_matrix.update_yaxes(autorange="reversed")
    _fig_matrix.update_traces(textfont_size=13)
    _fig_matrix.update_layout(
        height=420,
        margin=dict(l=40, r=20, t=70, b=20),
        coloraxis_colorbar=dict(title="%", thickness=12),
    )
    st.plotly_chart(_fig_matrix, use_container_width=True)

    _home_win = sum(
        _matrix[i][j]
        for i in range(_max_goals + 1)
        for j in range(_max_goals + 1)
        if i > j
    )
    _draw = sum(_matrix[i][i] for i in range(_max_goals + 1))
    _away_win = sum(
        _matrix[i][j]
        for i in range(_max_goals + 1)
        for j in range(_max_goals + 1)
        if j > i
    )
    _best_i, _best_j, _best_p = 0, 0, 0.0
    for i in range(_max_goals + 1):
        for j in range(_max_goals + 1):
            if _matrix[i][j] > _best_p:
                _best_p = _matrix[i][j]
                _best_i, _best_j = i, j

    st.markdown(
        f"""
        De esa matriz salen las probabilidades del partido:

        ```text
        Gana England   = suma debajo de la diagonal = {_home_win:.0f}%
        Empate         = suma en la diagonal        = {_draw:.0f}%
        Gana Croatia   = suma arriba de la diagonal = {_away_win:.0f}%

        Marcador mas probable: {_best_i}-{_best_j} ({_best_p:.1f}%)
        ```

        El **marcador mostrado** en el dashboard es una lectura representativa del
        partido, no una certeza.

        ---

        **Fase de grupos**

        Cada grupo se ordena por puntos, diferencia de gol, goles a favor y rating.
        Clasifican el 1ro y 2do de cada grupo + los 8 mejores terceros.

        - Verde = clasifica directo
        - Amarillo = clasifica como mejor tercero
        - Rojo = eliminado

        **Eliminatoria**

        Si un partido de eliminatoria queda empatado en el marcador mas probable, gana
        el equipo con mayor rating (simulando penales). Esto solo sirve para cerrar la
        llave; no significa que ese equipo siempre gane.

        ---

        **Como leer las probabilidades**

        Una linea como:

        ```text
        Netherlands 39% | Draw 27% | France 34%
        ```

        significa favorito leve, no certeza. El bracket tiene que elegir un ganador
        para avanzar, pero la probabilidad real sigue repartida entre los tres resultados.

        ---

        **Referencias**

        - **Elo, A. (1978).** *The Rating of Chessplayers, Past and Present.* Arco
          Publishing. Sistema original de rating actualizado partido a partido segun
          resultado esperado vs resultado real. Es la base del Elo mundialista que
          usamos aca.
        - **Maher, M. J. (1982).** "Modelling association football scores."
          *Statistica Neerlandica*, 36(3), 109-118. Primer paper en proponer que los
          goles de cada equipo se modelen como Poissons independientes con tasas
          `lambda = base * ataque_equipo * defensa_rival`. Es exactamente la
          estructura de nuestra formula de xG.
        - **Dixon, M. J. & Coles, S. G. (1997).** "Modelling association football
          scores and inefficiencies in the football betting market." *Journal of the
          Royal Statistical Society: Series C*, 46(2), 265-280. Refinamiento del
          modelo de Maher: agrega una correccion para marcadores bajos (0-0, 1-0,
          0-1, 1-1) que los Poissons independientes subestiman. Nuestro modelo no
          aplica esta correccion (por simplicidad).
        - **Hvattum, L. M. & Arntzen, H. (2010).** "Using ELO ratings for match
          result prediction in association football." *International Journal of
          Forecasting*, 26(3), 460-470. Evalua empiricamente el uso de Elo en futbol
          y muestra que la diferencia de Elo predice resultados mejor que muchos
          modelos alternativos. Justifica usar Elo como insumo del rating.
        - **FiveThirtyEight Soccer Power Index (SPI).** Implementacion practica
          publica del enfoque Elo + Poisson para ligas y selecciones. Buena
          referencia de como se ven estos modelos en produccion.
        """
    )
