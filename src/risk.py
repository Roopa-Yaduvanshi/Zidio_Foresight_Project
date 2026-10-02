"""M3/M4 — Stockout & overstock risk scoring and forecast-based replenishment."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

INVENTORY_SNAPSHOT_DATE = None  # use latest in file


def build_weekly_before_snapshot(
    sales: pd.DataFrame, snapshot_date: pd.Timestamp
) -> pd.DataFrame:
    sales = sales.copy()
    sales["Date"] = pd.to_datetime(sales["Date"])
    weekly = (
        sales.groupby(["SKU", pd.Grouper(key="Date", freq="W-SUN")])["Units_Sold"]
        .sum()
        .reset_index()
    )
    return weekly[weekly["Date"] < snapshot_date].copy()


def score_inventory_risk(
    inventory: pd.DataFrame,
    sales: pd.DataFrame,
    sku_master: pd.DataFrame,
    forecasts: pd.DataFrame,
) -> pd.DataFrame:
    inventory = inventory.copy()
    inventory["Snapshot_Date"] = pd.to_datetime(inventory["Snapshot_Date"])
    snap_date = inventory["Snapshot_Date"].max()
    snap = inventory[inventory["Snapshot_Date"] == snap_date].copy()

    sales_skus = set(sales["SKU"].unique())
    snap = snap[snap["SKU"].isin(sales_skus)].copy()
    snap["Stock_Position"] = snap["Current_Stock"] + snap["On_Order"]

    weekly = build_weekly_before_snapshot(sales, snap_date)
    avg_weekly = (
        weekly.groupby("SKU")["Units_Sold"].mean().rename("Avg_Weekly_Demand")
    )
    snap["Avg_Weekly_Demand"] = snap["SKU"].map(avg_weekly)
    snap["Daily_Demand"] = snap["Avg_Weekly_Demand"] / 7
    snap["Days_of_Cover"] = snap["Stock_Position"] / snap["Daily_Demand"].replace(
        0, np.nan
    )

    fc = forecasts.set_index("SKU")["Forecast_Weekly_Units"]
    snap["Forecast_Weekly_Units"] = snap["SKU"].map(fc)
    snap["Lead_Time_Demand"] = snap["Forecast_Weekly_Units"] * (
        snap["Lead_Time_Days"] / 7
    )
    snap["Target_Stock"] = snap["Lead_Time_Demand"] + snap["Safety_Stock"]

    snap = snap.merge(
        sku_master[["SKU", "Product_Name", "Category", "Cost_Price"]],
        on="SKU",
        how="left",
    )

    overstock_threshold_days = snap["Lead_Time_Days"] * 2

    snap["Risk_Status"] = np.select(
        [
            snap["Days_of_Cover"] < snap["Lead_Time_Days"],
            snap["Stock_Position"] <= snap["Reorder_Point"],
            snap["Days_of_Cover"] > overstock_threshold_days,
            snap["Stock_Position"] > snap["Target_Stock"] * 1.5,
        ],
        [
            "High Risk (Stockout)",
            "Reorder Attention",
            "Overstock Risk",
            "Overstock Risk",
        ],
        default="Healthy",
    )

    return snap.sort_values("Days_of_Cover")


def build_recommendations(risk_table: pd.DataFrame) -> pd.DataFrame:
    rec = risk_table.copy()
    rec["Recommended_Units"] = (
        (rec["Target_Stock"] - rec["Stock_Position"]).clip(lower=0).apply(np.ceil)
    ).astype(int)
    rec["Estimated_Cost"] = rec["Recommended_Units"] * rec["Cost_Price"]
    rec["Inventory_Status"] = np.where(
        rec["Recommended_Units"] > 0,
        "Replenishment Needed",
        "Sufficient Stock",
    )
    rec["Recommendation"] = rec.apply(
        lambda r: f"Order {int(r['Recommended_Units'])} units"
        if r["Recommended_Units"] > 0
        else "Maintain current stock",
        axis=1,
    )

    out = rec[rec["Recommended_Units"] > 0][
        [
            "SKU",
            "Product_Name",
            "Current_Stock",
            "On_Order",
            "Forecast_Weekly_Units",
            "Lead_Time_Days",
            "Recommended_Units",
            "Estimated_Cost",
            "Recommendation",
        ]
    ].copy()
    out = out.rename(columns={"Forecast_Weekly_Units": "Forecast"})
    return out.sort_values("Recommended_Units", ascending=False)


def run_risk_and_recommendations(
    inventory: pd.DataFrame,
    sales: pd.DataFrame,
    sku_master: pd.DataFrame,
    forecasts: pd.DataFrame,
    persist: bool = True,
) -> dict[str, pd.DataFrame]:
    risk = score_inventory_risk(inventory, sales, sku_master, forecasts)
    recommendations = build_recommendations(risk)

    if persist:
        risk.to_csv(DATA_DIR / "inventory_risk_scores.csv", index=False)
        recommendations.to_csv(
            DATA_DIR / "forecast_inventory_recommendations.csv", index=False
        )

    return {"risk": risk, "recommendations": recommendations}
