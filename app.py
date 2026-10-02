"""FORESIGHT — Zidio M4 Streamlit dashboard (NorthBay Living)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from run_pipeline import main as run_full_pipeline

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
MODELS = ROOT / "models"


@st.cache_data(show_spinner=False)
def load_metrics() -> dict:
    path = MODELS / "backtest_metrics.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_quality_summary() -> dict:
    path = REPORTS / "data_quality_summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)


st.set_page_config(
    page_title="FORESIGHT | Zidio NorthBay Living",
    page_icon="📦",
    layout="wide",
)

st.title("FORESIGHT")
st.caption(
    "Demand forecasting, rolling-origin backtesting (WAPE vs seasonal naive), "
    "stockout/overstock risk, and replenishment recommendations."
)

with st.sidebar:
    st.header("Pipeline")
    st.markdown(
        "Runs **M1** data foundation → **M2/M3** forecast + backtest → "
        "**M3/M4** risk + recommendations (`run_pipeline.py`)."
    )
    if st.button("Re-run full pipeline", type="primary"):
        with st.spinner("Running pipeline…"):
            run_full_pipeline()
        st.cache_data.clear()
        st.rerun()

metrics = load_metrics()
quality = load_quality_summary()

try:
    recommendations = load_csv("forecast_inventory_recommendations.csv")
    risk_scores = load_csv("inventory_risk_scores.csv")
    backtest = load_csv("rolling_backtest_results.csv")
    sales = load_csv("sales_daily.csv")
    sales["Date"] = pd.to_datetime(sales["Date"])
except FileNotFoundError as err:
    st.error(f"Missing artifact: {err}. Click **Re-run full pipeline** in the sidebar.")
    st.stop()

tab_home, tab_forecast, tab_risk, tab_replenish, tab_data = st.tabs(
    [
        "Executive overview",
        "Forecasting & backtest",
        "Inventory risk",
        "Replenishment",
        "Data foundation (M1)",
    ]
)

with tab_home:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Active SKUs (sales)", quality.get("sales_skus", "—"))
    c2.metric(
        "RF WAPE (rolling backtest)",
        f"{metrics.get('random_forest_wape_pct', 0):.2f}%"
        if metrics
        else "—",
    )
    c3.metric(
        "Seasonal naive WAPE",
        f"{metrics.get('seasonal_naive_wape_pct', 0):.2f}%"
        if metrics
        else "—",
    )
    high_risk = int(
        (risk_scores["Risk_Status"] == "High Risk (Stockout)").sum()
    )
    overstock = int((risk_scores["Risk_Status"] == "Overstock Risk").sum())
    c4.metric("Stockout risk SKUs", high_risk)
    c5.metric("Overstock risk SKUs", overstock)

    total_units = int(recommendations["Recommended_Units"].sum())
    total_cost = float(recommendations["Estimated_Cost"].sum())
    st.info(
        f"**{len(recommendations)}** SKUs need replenishment | "
        f"**{total_units:,}** units | est. cost **₹{total_cost:,.2f}**"
    )

    daily = sales.groupby("Date", as_index=False)["Units_Sold"].sum()
    st.subheader("Portfolio daily demand")
    st.line_chart(daily, x="Date", y="Units_Sold")

with tab_forecast:
    st.subheader("M2/M3 — Model vs seasonal-naive baseline (WAPE)")
    if metrics:
        compare = pd.DataFrame(
            {
                "Model": ["Random Forest", "Seasonal Naive (lag-52)"],
                "MAE": [
                    metrics["random_forest_mae"],
                    metrics["seasonal_naive_mae"],
                ],
                "WAPE (%)": [
                    metrics["random_forest_wape_pct"],
                    metrics["seasonal_naive_wape_pct"],
                ],
            }
        )
        st.dataframe(compare, width="stretch", hide_index=True)
        st.bar_chart(compare, x="Model", y="WAPE (%)")
        st.caption(
            f"Rolling-origin backtest: last **{metrics.get('test_weeks', 12)}** weekly "
            f"origins, **{metrics.get('backtest_predictions', 0)}** SKU-week predictions."
        )
    else:
        st.warning("No `models/backtest_metrics.json`. Re-run the pipeline.")

    st.subheader("Backtest sample (latest week per SKU)")
    latest_week = backtest["Date"].max()
    sample = backtest[backtest["Date"] == latest_week].head(20)
    st.dataframe(sample, width="stretch", hide_index=True)

with tab_risk:
    st.subheader("M3 — Stockout & overstock risk (latest snapshot)")
    status_filter = st.multiselect(
        "Risk status",
        options=sorted(risk_scores["Risk_Status"].unique()),
        default=sorted(risk_scores["Risk_Status"].unique()),
    )
    filtered = risk_scores[risk_scores["Risk_Status"].isin(status_filter)]
    st.dataframe(
        filtered[
            [
                "SKU",
                "Product_Name",
                "Category",
                "Stock_Position",
                "Forecast_Weekly_Units",
                "Lead_Time_Days",
                "Days_of_Cover",
                "Target_Stock",
                "Risk_Status",
            ]
        ].round(2),
        width="stretch",
        hide_index=True,
    )
    risk_counts = (
        risk_scores["Risk_Status"].value_counts().reset_index()
    )
    risk_counts.columns = ["Risk_Status", "SKU count"]
    st.bar_chart(risk_counts, x="Risk_Status", y="SKU count")

with tab_replenish:
    st.subheader("M4 — Actionable replenishment")
    st.dataframe(recommendations, width="stretch", hide_index=True)
    st.download_button(
        "Download recommendations CSV",
        data=recommendations.to_csv(index=False).encode("utf-8"),
        file_name="forecast_inventory_recommendations.csv",
        mime="text/csv",
    )

with tab_data:
    st.subheader("M1 — Data quality (four Zidio extracts)")
    if quality:
        st.json(quality)
    report_path = REPORTS / "DATA_QUALITY_REPORT.md"
    if report_path.exists():
        st.markdown(report_path.read_text(encoding="utf-8"))
