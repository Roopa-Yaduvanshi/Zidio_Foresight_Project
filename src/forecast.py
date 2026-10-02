"""M2/M3 — EDA features, seasonal-naive baseline, Random Forest, WAPE, rolling backtest."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"

FEATURE_COLS = [
    "lag_1",
    "lag_4",
    "rolling_mean_4",
    "rolling_std_4",
    "rolling_max_4",
    "lag_52",
]
TEST_WEEKS = 12
CUTOFF_WEEKLY = pd.Timestamp("2026-01-04")


def wape(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    denom = np.abs(actual).sum()
    if denom == 0:
        return float("nan")
    return float(np.abs(actual - predicted).sum() / denom * 100)


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(actual) - np.asarray(predicted))))


def build_weekly_sales(sales: pd.DataFrame) -> pd.DataFrame:
    sales = sales.copy()
    sales["Date"] = pd.to_datetime(sales["Date"])
    weekly = (
        sales.groupby(["SKU", pd.Grouper(key="Date", freq="W-SUN")])["Units_Sold"]
        .sum()
        .reset_index()
    )
    return weekly[weekly["Date"] < CUTOFF_WEEKLY].copy()


def engineer_features(weekly: pd.DataFrame) -> pd.DataFrame:
    weekly = weekly.sort_values(["SKU", "Date"]).copy()
    grouped = weekly.groupby("SKU", group_keys=False)

    weekly["lag_1"] = grouped["Units_Sold"].shift(1)
    weekly["lag_4"] = grouped["Units_Sold"].shift(4)
    weekly["rolling_mean_4"] = grouped["Units_Sold"].transform(
        lambda s: s.shift(1).rolling(window=4, min_periods=4).mean()
    )
    weekly["rolling_std_4"] = grouped["Units_Sold"].transform(
        lambda s: s.shift(1).rolling(window=4, min_periods=4).std()
    )
    weekly["rolling_max_4"] = grouped["Units_Sold"].transform(
        lambda s: s.shift(1).rolling(window=4, min_periods=4).max()
    )
    weekly["lag_52"] = grouped["Units_Sold"].shift(52)

    model_ready = weekly.dropna(subset=FEATURE_COLS).copy()
    return weekly, model_ready


def rolling_origin_backtest(model_ready: pd.DataFrame) -> pd.DataFrame:
    test_dates = sorted(model_ready["Date"].unique())[-TEST_WEEKS:]
    rows: list[dict] = []

    for test_date in test_dates:
        train = model_ready[model_ready["Date"] < test_date]
        test = model_ready[model_ready["Date"] == test_date]

        model = RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(train[FEATURE_COLS], train["Units_Sold"])

        rf_pred = model.predict(test[FEATURE_COLS])
        seasonal_pred = test["lag_52"].to_numpy()

        for i, (_, row) in enumerate(test.iterrows()):
            rows.append(
                {
                    "SKU": row["SKU"],
                    "Date": test_date,
                    "Actual": row["Units_Sold"],
                    "RF_Forecast": float(rf_pred[i]),
                    "Seasonal_Forecast": float(seasonal_pred[i]),
                }
            )

    backtest = pd.DataFrame(rows)
    backtest["RF_Absolute_Error"] = (
        backtest["Actual"] - backtest["RF_Forecast"]
    ).abs()
    backtest["Seasonal_Absolute_Error"] = (
        backtest["Actual"] - backtest["Seasonal_Forecast"]
    ).abs()
    return backtest


def train_final_model(model_ready: pd.DataFrame) -> RandomForestRegressor:
    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(model_ready[FEATURE_COLS], model_ready["Units_Sold"])
    return model


def next_week_forecasts(
    weekly: pd.DataFrame, model: RandomForestRegressor
) -> pd.DataFrame:
    """One-step-ahead weekly forecast per SKU (last observed week features)."""
    _, model_ready = engineer_features(weekly)
    last_rows = model_ready.sort_values("Date").groupby("SKU").tail(1)
    preds = model.predict(last_rows[FEATURE_COLS])
    out = last_rows[["SKU", "Date"]].copy()
    out["Forecast_Weekly_Units"] = preds
    out = out.rename(columns={"Date": "Feature_Week_Ending"})
    return out


def run_modelling(sales: pd.DataFrame, persist: bool = True) -> dict:
    weekly = build_weekly_sales(sales)
    weekly_full, model_ready = engineer_features(weekly)
    backtest = rolling_origin_backtest(model_ready)

    metrics = {
        "random_forest_mae": mae(backtest["Actual"], backtest["RF_Forecast"]),
        "random_forest_wape_pct": wape(backtest["Actual"], backtest["RF_Forecast"]),
        "seasonal_naive_mae": mae(backtest["Actual"], backtest["Seasonal_Forecast"]),
        "seasonal_naive_wape_pct": wape(
            backtest["Actual"], backtest["Seasonal_Forecast"]
        ),
        "backtest_predictions": int(len(backtest)),
        "test_weeks": TEST_WEEKS,
    }

    model = train_final_model(model_ready)
    forecasts = next_week_forecasts(weekly, model)

    if persist:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODELS_DIR / "demand_forecast_rf.joblib")
        backtest.to_csv(DATA_DIR / "rolling_backtest_results.csv", index=False)
        forecasts.to_csv(DATA_DIR / "sku_weekly_forecasts.csv", index=False)
        (MODELS_DIR / "backtest_metrics.json").write_text(
            json.dumps(metrics, indent=2), encoding="utf-8"
        )

    return {
        "weekly": weekly_full,
        "model_ready": model_ready,
        "backtest": backtest,
        "metrics": metrics,
        "model": model,
        "forecasts": forecasts,
    }
