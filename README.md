# FORESIGHT

AI-powered **demand and inventory intelligence** for SKU-level forecasting, risk detection, and replenishment recommendations. Built for the Zidio Development internship project (NorthBay Living scenario).

## What it does

- Loads Zidio-style datasets (sales, SKU master, calendar, inventory snapshots).
- Surfaces **inventory risk** (high risk / reorder attention / healthy).
- Shows **forecast-based replenishment** with estimated PO cost.
- Interactive **Streamlit dashboard** and optional **FastAPI** readout.

## Project structure

```
foresight_project/
├── app.py                 # Streamlit dashboard (main entry)
├── data/                  # CSV datasets + recommendation output
├── notebooks/             # Analysis (EDA, risk, recommendations)
├── models/                # Saved ML models (optional)
├── reports/               # Executive readout for submission
├── service/main.py        # FastAPI demo service
├── requirements.txt
└── README.md
```

## Setup (local)

```bash
cd ~/Documents/foresight_project
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
pip install fastapi uvicorn   # only if you run the API
```

## Run the full pipeline (M1 → M4)

```bash
source myenv/bin/activate
python run_pipeline.py
```

This cleans the four Zidio tables, trains Random Forest vs **seasonal-naive baseline**, runs **rolling-origin backtest (WAPE)**, writes risk scores and recommendations under `data/`, and saves `models/backtest_metrics.json`.

## Run the dashboard

```bash
source myenv/bin/activate
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501).

## Run the API (optional, M4)

```bash
source myenv/bin/activate
uvicorn service.main:app --reload --port 8000
```

- Health: `GET http://localhost:8000/health`
- Recommendations: `GET http://localhost:8000/recommendations`
- Summary KPIs: `GET http://localhost:8000/summary`

## Notebooks (run in order)

| Notebook | Purpose |
|----------|---------|
| `01_data_understanding.ipynb` | Schema, quality, missing values |
| `02_feature_engineering.ipynb` | Features for forecasting |
| `03_model_preparation.ipynb` | Train / validate forecast model |
| `04_rolling_backtesting.ipynb` | Seasonal-naive baseline, WAPE, rolling origin |
| `05_inventory_risk_analysis.ipynb` | Stockout / coverage risk |
| `06_inventory_recommendations.ipynb` | Target stock & replenishment list |
| `07_forecast_based_inventory.ipynb` | Export `forecast_inventory_recommendations.csv` |

> **Important:** Re-run and **save** notebooks after editing. The dashboard reads `data/forecast_inventory_recommendations.csv`.

## Deploy dashboard (Streamlit Community Cloud)

1. Push this repo to GitHub (exclude `myenv/` — see `.gitignore`).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Repository: your repo, branch `main`, main file path: **`app.py`**.
4. Deploy. Copy the public URL for your submission form / demo video.

## GitHub submission checklist

See **[SUBMISSION.md](SUBMISSION.md)** for step-by-step GitHub, Streamlit Cloud, and demo video instructions.

- [x] `README.md`, `requirements.txt`, `SUBMISSION.md`
- [x] Notebooks 01–07
- [x] `reports/EXECUTIVE_READOUT.md`
- [ ] GitHub repo pushed (you create remote + push)
- [ ] Live Streamlit URL
- [ ] 3–5 minute demo video

## Data files

| File | Description |
|------|-------------|
| `sales_daily.csv` | Daily units sold by SKU |
| `sku_master.csv` | Product metadata and cost |
| `inventory_snapshots.csv` | Stock, lead time, safety stock |
| `calendar.csv` | Date features / events |
| `forecast_inventory_recommendations.csv` | Pipeline output for dashboard |

## Tech stack

Python, Pandas, NumPy, Scikit-learn, Matplotlib/Seaborn, Streamlit, FastAPI (optional), Joblib.

## License / attribution

Internship academic project. Dataset is synthetic / provided for the assignment; do not represent as proprietary client data.
