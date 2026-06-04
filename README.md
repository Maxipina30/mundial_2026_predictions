# mundial_2026_predictions

Modelo y simulador para predecir el Mundial 2026.

## Primer objetivo

La primera version se enfoca solo en Mundiales, sin variables de plantel:

- descargar partidos de SofaScore para 2014, 2018, 2022 y 2026
- calcular un Elo propio con esos partidos
- calibrar un modelo Elo + Poisson
- predecir marcador exacto y clasificado
- correr dos modos:
  - prediccion completa desde fase de grupos
  - prediccion viva usando resultados reales ya jugados

## Scraper SofaScore

Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Ejecutar scraper de Mundiales:

```powershell
python src/01_scrape_world_cups.py
```

Salida:

```text
data/raw/sofascore/world_cups/
  2014/events.json
  2018/events.json
  2022/events.json
  2026/events.json
  matches.csv
```

## Scraper Ranking FIFA

Descarga snapshots historicos del ranking masculino desde la fuente oficial de FIFA.

```powershell
python src/02_scrape_fifa_rankings.py
```

Forzar refresco de la pagina oficial de fechas:

```powershell
python src/02_scrape_fifa_rankings.py --refresh
```

Salida:

```text
data/raw/fifa/rankings/
  dates.json
  snapshots/
  rankings.csv
```

## Inputs Mundial 2026

Una vez descargado SofaScore, preparar archivos normalizados para simulacion:

```powershell
python src/03_prepare_world_cup_2026_inputs.py
```

Salida:

```text
data/interim/world_cup_2026/
  fixtures.csv
  groups.csv
  teams.csv
```

## Historico Mundialista

Descargar todas las temporadas de Mundial disponibles en SofaScore:

```powershell
python src/04_scrape_world_cup_history.py
```

Construir variables historicas por seleccion:

```powershell
python src/05_build_world_cup_history_features.py
```

Salida:

```text
data/processed/features/world_cup_team_history.csv
```

## Entrenamiento Y Simulacion

Construir dataset de entrenamiento:

```powershell
python src/06_build_training_dataset.py
```

Descargar partidos oficiales internacionales sin amistosos:

```powershell
python src/11_scrape_official_international_matches.py
```

Construir dataset ponderado con Mundiales, clasificatorias y copas continentales:

```powershell
python src/12_build_official_training_dataset.py
```

Evaluar baseline en Mundial 2022:

```powershell
python src/08_evaluate_baseline_2022.py
```

Entrenar y evaluar el modelo de goles con regresion Poisson, comparando sets de variables:

```powershell
python src/09_train_poisson_model.py
```

Salida:

```text
data/processed/models/poisson_regression/
  backtest_metrics.csv
  feature_set_summary.csv
  high_correlations.csv
  backtest_predictions.csv
```

Si existe `data/processed/training/official_international_matches_1998_2024.csv`, el modelo lo usa
para entrenar con pesos por competicion y sigue evaluando solamente Mundiales pasados.

Simular Mundial 2026:

```powershell
python src/07_simulate_world_cup_2026.py
```

Salida:

```text
data/processed/simulations/world_cup_2026/
  group_predictions.csv
  standings.csv
  knockout_predictions.csv
```

## Dashboard Streamlit

Abrir una vista interactiva de la simulacion:

```powershell
C:\Users\maxip\Documents\futdata_v1\.runtime\python312\python.exe -m streamlit run app.py
```

En Windows tambien puedes abrir el launcher de doble click:

```text
run_dashboard.bat
```

Ese launcher deja Streamlit corriendo en la consola. Mantén esa ventana abierta mientras usas el dashboard.

Tambien puedes levantarlo desacoplado:

```powershell
C:\Users\maxip\Documents\futdata_v1\.runtime\python312\python.exe start_dashboard.py
```

Ambos usan `app.py` como entrypoint principal y levantan Streamlit en `http://127.0.0.1:8501/`. Si falla, revisa:

```text
logs/streamlit_stdout.log
logs/streamlit_stderr.log
```

La app muestra:

- resumen del campeon, final y tercer lugar proyectados
- tablas y partidos de fase de grupos
- llave completa desde Round of 32 hasta la final
- detalle por partido con Elo, probabilidades 1X2 y probabilidad del marcador
- visor de los CSV de salida

## Dashboard HTML sin servidor

Si no quieres depender de `localhost`, puedes generar un dashboard HTML estatico:

```powershell
python src/10_build_static_dashboard.py
```

Luego abre este archivo directamente en el navegador:

```text
dashboard/world_cup_2026_dashboard.html
```
