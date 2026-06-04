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


def esc(value: object) -> str:
    if pd.isna(value):
        return ""
    return html.escape(str(value))


@st.cache_data
def load_simulation() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing = [
        path
        for path in (GROUP_PREDICTIONS_PATH, STANDINGS_PATH, KNOCKOUT_PATH)
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
    return groups, standings, knockout


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
    ordered_numbers = {bracket_stages[-1]: stage_match_numbers[bracket_stages[-1]]}
    for stage_index in range(len(bracket_stages) - 2, -1, -1):
        next_stage = bracket_stages[stage_index + 1]
        current_stage = bracket_stages[stage_index]
        order = []
        for match_number in ordered_numbers[next_stage]:
            row = rows_by_match[match_number]
            for slot in (row.get("source_home_slot", ""), row.get("source_away_slot", "")):
                if isinstance(slot, str) and slot.startswith("W") and slot[1:].isdigit():
                    source_number = int(slot[1:])
                    if source_number in stage_match_numbers[current_stage] and source_number not in order:
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
                source_centers = []
                for slot in (row.get("source_home_slot", ""), row.get("source_away_slot", "")):
                    if isinstance(slot, str) and slot.startswith("W") and slot[1:].isdigit():
                        source_position = match_positions.get(int(slot[1:]))
                        if source_position:
                            source_centers.append(source_position[1])
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
            for slot in (row.get("source_home_slot", ""), row.get("source_away_slot", "")):
                if not (isinstance(slot, str) and slot.startswith("W") and slot[1:].isdigit()):
                    continue
                source_position = match_positions.get(int(slot[1:]))
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
            boxes.append(
                f"""
                <g>
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
        third_html = (
            '<div class="third-place-card"><h3>Tercer lugar</h3>'
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
        </style>
        <div class="bracket-scroll">
            <svg class="bracket-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Llave eliminatoria proyectada">
                {"".join(lines)}{"".join(labels)}{"".join(boxes)}
            </svg>
        </div>
        {third_html}
        """
    )
    components.html(svg, height=min(920, height + 150), scrolling=True)


def short_team(team: object, max_len: int = 16) -> str:
    text = str(team)
    return text if len(text) <= max_len else text[: max_len - 1] + "."


try:
    group_predictions, standings, knockout_predictions = load_simulation()
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
        "Partidos simulados",
        str(len(group_predictions) + len(knockout_predictions)),
        f"{len(group_predictions)} grupos + {len(knockout_predictions)} eliminatoria",
    )

tab_overview, tab_groups, tab_bracket, tab_matches, tab_methodology = st.tabs(
    ["Resumen", "Grupos", "Eliminatoria", "Partidos", "Metodologia"]
)

with tab_overview:
    strength = build_team_strength(group_predictions, knockout_predictions)
    col_left, col_right = st.columns([1.1, 1])

    with col_left:
        st.subheader("Rating del simulador")
        st.caption("Valor final usado para predecir: 40% Elo mundialista + 60% FIFA actual.")
        top_n = st.slider("Equipos a mostrar", 8, 24, 12, key="top_elo")
        fig = px.bar(
            strength.head(top_n).sort_values("elo"),
            x="elo",
            y="team",
            orientation="h",
            text="elo",
            color="elo",
            color_continuous_scale=["#d9e8e9", "#176b87"],
            labels={"team": "", "elo": "Rating"},
        )
        fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        fig.update_layout(
            height=max(360, top_n * 28),
            margin=dict(l=8, r=8, t=10, b=10),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, width="stretch")

    with col_right:
        st.subheader("Camino del campeon")
        champion_matches = knockout_predictions[
            (knockout_predictions["home_team"] == champion)
            | (knockout_predictions["away_team"] == champion)
        ].copy()
        champion_matches["stage_rank"] = champion_matches["stage"].map(
            {stage: idx for idx, stage in enumerate(STAGE_ORDER)}
        )
        champion_matches = champion_matches.sort_values("stage_rank")
        for _, row in champion_matches.iterrows():
            render_match_card(row)

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
        st.subheader("Partidos")
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

with tab_matches:
    all_matches = pd.concat(
        [
            group_predictions.assign(phase="Group", match_number=pd.NA),
            knockout_predictions.assign(phase="Knockout"),
        ],
        ignore_index=True,
        sort=False,
    )
    teams = sorted(
        set(all_matches["home_team"].dropna().tolist())
        | set(all_matches["away_team"].dropna().tolist())
    )
    stages = ["All"] + ["Group"] + STAGE_ORDER
    col_filters = st.columns([1, 1, 1])
    with col_filters[0]:
        selected_team = st.selectbox("Equipo", ["All"] + teams)
    with col_filters[1]:
        selected_stage = st.selectbox("Fase", stages)
    with col_filters[2]:
        sort_by = st.selectbox("Orden", ["Calendario", "Probabilidad marcador", "Diferencia Elo"])

    filtered = all_matches.copy()
    if selected_team != "All":
        filtered = filtered[
            (filtered["home_team"] == selected_team) | (filtered["away_team"] == selected_team)
        ]
    if selected_stage != "All":
        if selected_stage == "Group":
            filtered = filtered[filtered["phase"] == "Group"]
        else:
            filtered = filtered[filtered["stage"] == selected_stage]

    filtered["elo_diff_abs"] = (filtered["home_elo"] - filtered["away_elo"]).abs()
    if sort_by == "Probabilidad marcador":
        filtered = filtered.sort_values("score_probability", ascending=False)
    elif sort_by == "Diferencia Elo":
        filtered = filtered.sort_values("elo_diff_abs", ascending=False)
    else:
        filtered = filtered.sort_values(["phase", "match_number", "event_id"], na_position="first")

    display_cols = [
        "phase",
        "stage",
        "group_sign",
        "match_number",
        "home_team",
        "home_score",
        "away_score",
        "away_team",
        "home_elo",
        "away_elo",
        "home_xg",
        "away_xg",
        "home_win_90",
        "draw_90",
        "away_win_90",
        "score_probability",
        "advancing_team",
        "venue",
    ]
    display_cols = [col for col in display_cols if col in filtered.columns]
    display = filtered[display_cols].copy()
    for col in ("home_win_90", "draw_90", "away_win_90", "score_probability"):
        if col in display.columns:
            display[col] = display[col].map(percent)
    for col in ("home_elo", "away_elo"):
        if col in display.columns:
            display[col] = display[col].map(lambda value: fmt_number(value, 0))
    for col in ("home_xg", "away_xg"):
        if col in display.columns:
            display[col] = display[col].map(lambda value: fmt_number(value, 2))
    st.dataframe(display, hide_index=True, width="stretch")

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

        Aparte del rating, cada seleccion tiene un perfil ofensivo y defensivo que
        tambien entra en la formula:

        ```text
        ataque  = (goles_a_favor   / partidos) * factor_experiencia
        defensa = (goles_en_contra / partidos) / factor_experiencia
        ```

        - Los goles a favor y en contra se cuentan sobre todos los Mundiales (recientes
          pesan mas) y se suavizan para que pocas participaciones no distorsionen.
        - El `factor_experiencia` vale entre `0.62` (debutantes) y `1.0` (selecciones
          con 18+ participaciones). Las debutantes anotan menos y reciben mas; las
          experimentadas no tienen penalizacion.

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

