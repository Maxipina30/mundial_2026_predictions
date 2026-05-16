from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


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

tab_overview, tab_groups, tab_bracket, tab_matches, tab_data = st.tabs(
    ["Resumen", "Grupos", "Eliminatoria", "Partidos", "Datos"]
)

with tab_overview:
    strength = build_team_strength(group_predictions, knockout_predictions)
    col_left, col_right = st.columns([1.1, 1])

    with col_left:
        st.subheader("Ranking Elo del simulador")
        top_n = st.slider("Equipos a mostrar", 8, 24, 12, key="top_elo")
        fig = px.bar(
            strength.head(top_n).sort_values("elo"),
            x="elo",
            y="team",
            orientation="h",
            text="elo",
            color="elo",
            color_continuous_scale=["#d9e8e9", "#176b87"],
            labels={"team": "", "elo": "Elo"},
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
    group_order = sorted(standings["group_sign"].dropna().unique())
    selected_group = st.selectbox("Grupo", group_order, index=0)
    group_games = group_predictions[group_predictions["group_sign"] == selected_group]
    group_table = standings[standings["group_sign"] == selected_group].sort_values("position")

    col_table, col_games = st.columns([1, 1.2])
    with col_table:
        st.subheader(f"Tabla Grupo {selected_group}")
        st.dataframe(
            group_table[
                [
                    "position",
                    "team",
                    "played",
                    "wins",
                    "draws",
                    "losses",
                    "goals_for",
                    "goals_against",
                    "goal_diff",
                    "points",
                ]
            ],
            hide_index=True,
            width="stretch",
        )
    with col_games:
        st.subheader("Partidos")
        for _, row in group_games.iterrows():
            render_match_card(row, show_stage=False)

    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.subheader("Todas las posiciones")
    all_tables = standings.sort_values(["group_sign", "position"])
    st.dataframe(all_tables, hide_index=True, width="stretch")

with tab_bracket:
    st.subheader("Llave proyectada")
    stage_cols = st.columns([1.1, 1.1, 1.1, 1.1, 0.9, 0.9])
    for col, stage in zip(stage_cols, STAGE_ORDER):
        with col:
            st.markdown(f"**{stage}**")
            stage_rows = knockout_predictions[knockout_predictions["stage"] == stage]
            stage_rows = stage_rows.sort_values("match_number")
            for _, row in stage_rows.iterrows():
                render_match_card(row)

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
    st.dataframe(display, hide_index=True, width="stretch")

with tab_data:
    st.subheader("Archivos de salida")
    st.write("Estos son los CSV que alimentan el dashboard.")

    data_choice = st.radio(
        "Dataset",
        ["Predicciones de grupos", "Tablas de grupos", "Eliminatoria"],
        horizontal=True,
    )
    if data_choice == "Predicciones de grupos":
        st.dataframe(group_predictions, hide_index=True, width="stretch")
    elif data_choice == "Tablas de grupos":
        st.dataframe(standings, hide_index=True, width="stretch")
    else:
        st.dataframe(knockout_predictions, hide_index=True, width="stretch")
