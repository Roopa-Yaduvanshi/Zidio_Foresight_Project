"""Minimal FORESIGHT scoring API for deployment / integration demo."""

from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import JSONResponse

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RECOMMENDATIONS_PATH = DATA_DIR / "forecast_inventory_recommendations.csv"

app = FastAPI(
    title="FORESIGHT API",
    description="Replenishment recommendations exported from the analytics pipeline.",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/recommendations")
def recommendations() -> JSONResponse:
    if not RECOMMENDATIONS_PATH.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": "forecast_inventory_recommendations.csv not found"},
        )
    df = pd.read_csv(RECOMMENDATIONS_PATH)
    return JSONResponse(content=df.to_dict(orient="records"))


@app.get("/summary")
def summary() -> dict:
    if not RECOMMENDATIONS_PATH.exists():
        return {"skus_to_replenish": 0, "total_units": 0, "total_cost_inr": 0.0}
    df = pd.read_csv(RECOMMENDATIONS_PATH)
    return {
        "skus_to_replenish": int(len(df)),
        "total_units": int(df["Recommended_Units"].sum()),
        "total_cost_inr": float(df["Estimated_Cost"].sum()),
    }
