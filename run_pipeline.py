"""Run full Zidio FORESIGHT pipeline (M1 → M4 artifacts)."""

from src.forecast import run_modelling
from src.pipeline import run_data_foundation
from src.risk import run_risk_and_recommendations


def main() -> None:
    clean, report = run_data_foundation(persist=True)
    print("M1 complete — data quality summary:", report)

    modelling = run_modelling(clean["sales_daily"], persist=True)
    print("M2/M3 complete — backtest metrics:", modelling["metrics"])

    outputs = run_risk_and_recommendations(
        clean["inventory_snapshots"],
        clean["sales_daily"],
        clean["sku_master"],
        modelling["forecasts"],
        persist=True,
    )
    print(
        "M3/M4 complete — replenishment SKUs:",
        len(outputs["recommendations"]),
    )


if __name__ == "__main__":
    main()
