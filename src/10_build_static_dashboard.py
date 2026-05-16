"""
Build a static HTML dashboard for the World Cup 2026 simulation.

This is a no-server fallback for quickly inspecting the current simulation:

    python src/10_build_static_dashboard.py
"""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
SIM_DIR = BASE_DIR / "data" / "processed" / "simulations" / "world_cup_2026"
OUT_PATH = BASE_DIR / "dashboard" / "world_cup_2026_dashboard.html"

STAGE_ORDER = [
    "Round of 32",
    "Round of 16",
    "Quarterfinals",
    "Semifinals",
    "Match for 3rd place",
    "Final",
]

ENCODING_FIXES = {
    "TÃ¼rkiye": "Türkiye",
    "CuraÃ§ao": "Curaçao",
    "CÃ´te d'Ivoire": "Côte d'Ivoire",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    return [fix_row(row) for row in rows]


def fix_text(value: str) -> str:
    for wrong, right in ENCODING_FIXES.items():
        value = value.replace(wrong, right)
    return value


def fix_row(row: dict[str, str]) -> dict[str, str]:
    return {key: fix_text(value) for key, value in row.items()}


def as_number(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_team_strength(groups: list[dict[str, str]], knockout: list[dict[str, str]]) -> list[dict[str, object]]:
    by_team: dict[str, float] = {}
    for row in groups + knockout:
        for side in ("home", "away"):
            team = row.get(f"{side}_team", "")
            elo = as_number(row.get(f"{side}_elo", "0"))
            if team:
                by_team[team] = max(by_team.get(team, 0.0), elo)
    return [
        {"team": team, "elo": round(elo, 1)}
        for team, elo in sorted(by_team.items(), key=lambda item: item[1], reverse=True)
    ]


def main() -> None:
    group_predictions = read_csv(SIM_DIR / "group_predictions.csv")
    standings = read_csv(SIM_DIR / "standings.csv")
    knockout = read_csv(SIM_DIR / "knockout_predictions.csv")
    final = next((row for row in knockout if row.get("stage") == "Final"), {})
    champion = final.get("advancing_team", "TBD")

    payload = {
        "groupPredictions": group_predictions,
        "standings": standings,
        "knockout": knockout,
        "teamStrength": build_team_strength(group_predictions, knockout),
        "stageOrder": STAGE_ORDER,
        "champion": champion,
    }
    data_json = json.dumps(payload, ensure_ascii=False)

    html_doc = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>World Cup 2026 Predictor</title>
  <style>
    :root {{
      --bg: #f7f8f8;
      --panel: #ffffff;
      --line: #d7dddd;
      --text: #1f2a2c;
      --muted: #617074;
      --accent: #176b87;
      --accent-soft: #e7f1f4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Segoe UI, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    header {{
      padding: 22px 28px 14px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 2;
    }}
    h1 {{ margin: 0 0 6px; font-size: 30px; letter-spacing: 0; }}
    h2 {{ margin: 24px 0 12px; font-size: 20px; }}
    h3 {{ margin: 0 0 10px; font-size: 16px; }}
    .subtitle {{ color: var(--muted); }}
    main {{ padding: 20px 28px 36px; max-width: 1500px; margin: 0 auto; }}
    .tabs {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }}
    .tab {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      border-radius: 7px;
      padding: 8px 12px;
      cursor: pointer;
      font: inherit;
    }}
    .tab.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
    .panel {{ display: none; }}
    .panel.active {{ display: block; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 12px; }}
    .metric, .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }}
    .metric .label {{
      color: var(--muted);
      text-transform: uppercase;
      font-size: 12px;
      letter-spacing: .04em;
    }}
    .metric .value {{ font-weight: 700; font-size: 23px; margin-top: 5px; }}
    .metric .help {{ color: var(--muted); font-size: 13px; margin-top: 5px; }}
    .grid-2 {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }}
    .bracket {{ display: grid; grid-template-columns: repeat(6, minmax(185px, 1fr)); gap: 12px; overflow-x: auto; }}
    .match {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      margin-bottom: 9px;
    }}
    .match-meta {{
      color: var(--muted);
      font-size: 12px;
      display: flex;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 7px;
    }}
    .scoreline {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
      align-items: center;
      gap: 8px;
      font-weight: 700;
    }}
    .team-left {{ text-align: right; overflow-wrap: anywhere; }}
    .team-right {{ text-align: left; overflow-wrap: anywhere; }}
    .score {{
      min-width: 52px;
      text-align: center;
      background: var(--accent-soft);
      color: var(--accent);
      border-radius: 6px;
      padding: 3px 8px;
      font-variant-numeric: tabular-nums;
    }}
    .match-extra {{ margin-top: 7px; font-size: 12px; color: var(--muted); }}
    select, input {{
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 8px 10px;
      font: inherit;
      background: #fff;
    }}
    .controls {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 8px 0 14px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px 9px;
      text-align: left;
      font-size: 13px;
      white-space: nowrap;
    }}
    th {{ background: #edf2f3; }}
    tr:last-child td {{ border-bottom: 0; }}
    .table-wrap {{ overflow-x: auto; }}
    .bar {{
      height: 24px;
      background: var(--accent-soft);
      border-radius: 5px;
      overflow: hidden;
      margin-bottom: 8px;
      position: relative;
    }}
    .bar span {{
      display: block;
      height: 100%;
      background: var(--accent);
    }}
    .bar label {{
      position: absolute;
      inset: 0;
      padding: 3px 8px;
      font-size: 12px;
      font-weight: 600;
    }}
    @media (max-width: 900px) {{
      .metrics, .grid-2 {{ grid-template-columns: 1fr; }}
      header, main {{ padding-left: 16px; padding-right: 16px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>World Cup 2026 Predictor</h1>
    <div class="subtitle">Dashboard estático de la simulación Elo + Poisson. No requiere servidor local.</div>
    <nav class="tabs">
      <button class="tab active" data-tab="resumen">Resumen</button>
      <button class="tab" data-tab="grupos">Grupos</button>
      <button class="tab" data-tab="eliminatoria">Eliminatoria</button>
      <button class="tab" data-tab="partidos">Partidos</button>
    </nav>
  </header>
  <main>
    <section id="resumen" class="panel active"></section>
    <section id="grupos" class="panel"></section>
    <section id="eliminatoria" class="panel"></section>
    <section id="partidos" class="panel"></section>
  </main>
  <script id="simulation-data" type="application/json">{html.escape(data_json)}</script>
  <script>
    const data = JSON.parse(document.getElementById('simulation-data').textContent);
    const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
    const pct = (value) => Number.isFinite(Number(value)) ? (Number(value) * 100).toFixed(1) + '%' : '-';
    const score = (row) => `${{row.home_score}}-${{row.away_score}}`;
    const byStage = (stage) => data.knockout.filter(row => row.stage === stage).sort((a, b) => Number(a.match_number) - Number(b.match_number));

    document.querySelectorAll('.tab').forEach(button => {{
      button.addEventListener('click', () => {{
        document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(panel => panel.classList.remove('active'));
        button.classList.add('active');
        document.getElementById(button.dataset.tab).classList.add('active');
      }});
    }});

    function matchCard(row, showStage = true) {{
      const metaLeft = showStage ? row.stage : `Grupo ${{row.group_sign || ''}}`;
      const metaRight = row.match_number ? `#${{row.match_number}}` : (row.venue || '');
      const details = [
        row.home_win_90 ? `90m: ${{pct(row.home_win_90)}} / ${{pct(row.draw_90)}} / ${{pct(row.away_win_90)}}` : '',
        row.score_probability ? `marcador: ${{pct(row.score_probability)}}` : '',
        row.advancing_team ? `avanza: ${{esc(row.advancing_team)}}` : ''
      ].filter(Boolean).join(' | ');
      return `<div class="match">
        <div class="match-meta"><span>${{esc(metaLeft)}}</span><span>${{esc(metaRight)}}</span></div>
        <div class="scoreline">
          <div class="team-left">${{esc(row.home_team)}}</div>
          <div class="score">${{esc(score(row))}}</div>
          <div class="team-right">${{esc(row.away_team)}}</div>
        </div>
        <div class="match-extra">${{details}}</div>
      </div>`;
    }}

    function table(rows, cols) {{
      return `<div class="table-wrap"><table><thead><tr>${{cols.map(col => `<th>${{esc(col.label)}}</th>`).join('')}}</tr></thead>
        <tbody>${{rows.map(row => `<tr>${{cols.map(col => `<td>${{esc(col.format ? col.format(row[col.key], row) : row[col.key])}}</td>`).join('')}}</tr>`).join('')}}</tbody></table></div>`;
    }}

    function renderResumen() {{
      const final = data.knockout.find(row => row.stage === 'Final') || {{}};
      const third = data.knockout.find(row => row.stage === 'Match for 3rd place') || {{}};
      const runnerUp = final.home_team === data.champion ? final.away_team : final.home_team;
      const topElo = data.teamStrength.slice(0, 12);
      const maxElo = Math.max(...topElo.map(row => row.elo));
      const championPath = data.knockout.filter(row => row.home_team === data.champion || row.away_team === data.champion);
      document.getElementById('resumen').innerHTML = `
        <div class="metrics">
          <div class="metric"><div class="label">Campeón</div><div class="value">${{esc(data.champion)}}</div><div class="help">Finalista: ${{esc(runnerUp || 'TBD')}}</div></div>
          <div class="metric"><div class="label">Final</div><div class="value">${{esc(final.home_team || 'TBD')}} ${{esc(score(final))}} ${{esc(final.away_team || '')}}</div><div class="help">${{esc(final.venue || '')}}</div></div>
          <div class="metric"><div class="label">Tercer lugar</div><div class="value">${{esc(third.advancing_team || 'TBD')}}</div><div class="help">Partido por el 3er puesto</div></div>
          <div class="metric"><div class="label">Partidos</div><div class="value">${{data.groupPredictions.length + data.knockout.length}}</div><div class="help">${{data.groupPredictions.length}} grupos + ${{data.knockout.length}} eliminatoria</div></div>
        </div>
        <div class="grid-2">
          <div><h2>Ranking Elo</h2>${{topElo.map(row => `<div class="bar"><span style="width:${{Math.max(8, row.elo / maxElo * 100)}}%"></span><label>${{esc(row.team)}} · ${{row.elo}}</label></div>`).join('')}}</div>
          <div><h2>Camino del campeón</h2>${{championPath.map(row => matchCard(row)).join('')}}</div>
        </div>`;
    }}

    function renderGrupos() {{
      const groups = [...new Set(data.standings.map(row => row.group_sign))].sort();
      document.getElementById('grupos').innerHTML = `
        <div class="controls"><label>Grupo <select id="group-select">${{groups.map(group => `<option>${{esc(group)}}</option>`).join('')}}</select></label></div>
        <div id="group-content"></div>
        <h2>Todas las tablas</h2>
        ${{table(data.standings.sort((a,b) => a.group_sign.localeCompare(b.group_sign) || Number(a.position)-Number(b.position)), [
          {{key:'group_sign', label:'Grupo'}}, {{key:'position', label:'#'}}, {{key:'team', label:'Equipo'}}, {{key:'played', label:'PJ'}}, {{key:'wins', label:'G'}}, {{key:'draws', label:'E'}}, {{key:'losses', label:'P'}}, {{key:'goals_for', label:'GF'}}, {{key:'goals_against', label:'GC'}}, {{key:'goal_diff', label:'DG'}}, {{key:'points', label:'Pts'}}
        ])}}`;
      const select = document.getElementById('group-select');
      const renderGroup = () => {{
        const group = select.value;
        const rows = data.standings.filter(row => row.group_sign === group).sort((a,b) => Number(a.position)-Number(b.position));
        const games = data.groupPredictions.filter(row => row.group_sign === group);
        document.getElementById('group-content').innerHTML = `<div class="grid-2">
          <div><h2>Tabla Grupo ${{esc(group)}}</h2>${{table(rows, [
            {{key:'position', label:'#'}}, {{key:'team', label:'Equipo'}}, {{key:'played', label:'PJ'}}, {{key:'wins', label:'G'}}, {{key:'draws', label:'E'}}, {{key:'losses', label:'P'}}, {{key:'goals_for', label:'GF'}}, {{key:'goals_against', label:'GC'}}, {{key:'goal_diff', label:'DG'}}, {{key:'points', label:'Pts'}}
          ])}}</div>
          <div><h2>Partidos</h2>${{games.map(row => matchCard(row, false)).join('')}}</div>
        </div>`;
      }};
      select.addEventListener('change', renderGroup);
      renderGroup();
    }}

    function renderEliminatoria() {{
      document.getElementById('eliminatoria').innerHTML = `<div class="bracket">${{data.stageOrder.map(stage => `
        <div><h3>${{esc(stage)}}</h3>${{byStage(stage).map(row => matchCard(row)).join('')}}</div>`).join('')}}</div>`;
    }}

    function renderPartidos() {{
      const allMatches = [
        ...data.groupPredictions.map(row => ({{...row, phase: 'Group'}})),
        ...data.knockout.map(row => ({{...row, phase: 'Knockout'}})),
      ];
      const teams = [...new Set(allMatches.flatMap(row => [row.home_team, row.away_team]).filter(Boolean))].sort();
      document.getElementById('partidos').innerHTML = `
        <div class="controls">
          <label>Equipo <select id="team-filter"><option>Todos</option>${{teams.map(team => `<option>${{esc(team)}}</option>`).join('')}}</select></label>
          <label>Buscar <input id="search-filter" placeholder="equipo, fase, sede"></label>
        </div>
        <div id="matches-table"></div>`;
      const teamFilter = document.getElementById('team-filter');
      const searchFilter = document.getElementById('search-filter');
      const renderMatches = () => {{
        const team = teamFilter.value;
        const query = searchFilter.value.toLowerCase();
        const rows = allMatches.filter(row => {{
          const teamOk = team === 'Todos' || row.home_team === team || row.away_team === team;
          const queryOk = !query || JSON.stringify(row).toLowerCase().includes(query);
          return teamOk && queryOk;
        }});
        document.getElementById('matches-table').innerHTML = table(rows, [
          {{key:'phase', label:'Fase'}}, {{key:'stage', label:'Etapa'}}, {{key:'group_sign', label:'Grupo'}}, {{key:'home_team', label:'Local'}}, {{key:'home_score', label:'GL'}}, {{key:'away_score', label:'GV'}}, {{key:'away_team', label:'Visita'}}, {{key:'home_elo', label:'Elo L'}}, {{key:'away_elo', label:'Elo V'}}, {{key:'home_win_90', label:'L', format:pct}}, {{key:'draw_90', label:'E', format:pct}}, {{key:'away_win_90', label:'V', format:pct}}, {{key:'score_probability', label:'Prob score', format:pct}}, {{key:'advancing_team', label:'Avanza'}}, {{key:'venue', label:'Sede'}}
        ]);
      }};
      teamFilter.addEventListener('change', renderMatches);
      searchFilter.addEventListener('input', renderMatches);
      renderMatches();
    }}

    renderResumen();
    renderGrupos();
    renderEliminatoria();
    renderPartidos();
  </script>
</body>
</html>
"""
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html_doc, encoding="utf-8")
    print(f"Static dashboard written to: {OUT_PATH}")


if __name__ == "__main__":
    main()
