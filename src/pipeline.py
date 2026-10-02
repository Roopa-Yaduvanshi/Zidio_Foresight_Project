"""M1 — Data foundation: load, clean, and quality-report Zidio datasets."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"


def _read_calendar(path: Path) -> pd.DataFrame:
    cal = pd.read_csv(path)
    cal["date"] = pd.to_datetime(cal["date"])
    for col in ("holiday", "promotion_event"):
        if col in cal.columns:
            cal[col] = cal[col].replace({"None": pd.NA, "": pd.NA})
    return cal


def load_raw() -> dict[str, pd.DataFrame]:
    return {
        "sales_daily": pd.read_csv(DATA_RAW / "sales_daily.csv"),
        "sku_master": pd.read_csv(DATA_RAW / "sku_master.csv"),
        "calendar": _read_calendar(DATA_RAW / "calendar.csv"),
        "inventory_snapshots": pd.read_csv(DATA_RAW / "inventory_snapshots.csv"),
    }


def clean_datasets(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    sales = raw["sales_daily"].copy()
    sales["Date"] = pd.to_datetime(sales["Date"])
    sales = sales.drop_duplicates(subset=["Date", "SKU"], keep="first")

    inventory = raw["inventory_snapshots"].copy()
    inventory["Snapshot_Date"] = pd.to_datetime(inventory["Snapshot_Date"])
    inventory = inventory.drop_duplicates(subset=["Snapshot_Date", "SKU"], keep="first")

    sku = raw["sku_master"].copy()
    sku["Launch_Date"] = pd.to_datetime(sku["Launch_Date"])

    calendar = raw["calendar"].copy()

    return {
        "sales_daily": sales,
        "sku_master": sku,
        "calendar": calendar,
        "inventory_snapshots": inventory,
    }


def build_quality_report(raw: dict[str, pd.DataFrame], clean: dict[str, pd.DataFrame]) -> dict:
    sales_skus = set(clean["sales_daily"]["SKU"].unique())
    inv_skus = set(clean["inventory_snapshots"]["SKU"].unique())

    sales_dup = int(
        raw["sales_daily"].duplicated(subset=["Date", "SKU"]).sum()
    )
    inv_dup = int(
        raw["inventory_snapshots"]
        .duplicated(subset=["Snapshot_Date", "SKU"])
        .sum()
    )

    return {
        "sales_daily_rows": int(len(clean["sales_daily"])),
        "inventory_rows": int(len(clean["inventory_snapshots"])),
        "sku_master_rows": int(len(clean["sku_master"])),
        "calendar_rows": int(len(clean["calendar"])),
        "sales_duplicate_date_sku_removed": sales_dup,
        "inventory_duplicate_snapshot_sku_removed": inv_dup,
        "sales_skus": int(len(sales_skus)),
        "inventory_skus": int(len(inv_skus)),
        "skus_in_sales_and_inventory": int(len(sales_skus & inv_skus)),
        "inventory_skus_not_in_sales": int(len(inv_skus - sales_skus)),
        "calendar_missing_holiday": int(clean["calendar"]["holiday"].isna().sum()),
        "calendar_missing_promotion_event": int(
            clean["calendar"]["promotion_event"].isna().sum()
        ),
    }


def write_quality_markdown(report: dict, path: Path) -> None:
    lines = [
        "# Data quality report (M1 — Data foundation)",
        "",
        "NorthBay Living / Zidio FORESIGHT — four provided extracts after cleaning.",
        "",
        "| Check | Result |",
        "|-------|--------|",
    ]
    for key, value in report.items():
        lines.append(f"| {key.replace('_', ' ')} | {value} |")
    lines.extend(
        [
            "",
            "## Cleaning actions",
            "",
            "- Parsed date columns to datetime.",
            "- Standardised calendar `None` labels to missing values.",
            "- Removed duplicate `(Date, SKU)` in sales and `(Snapshot_Date, SKU)` in inventory.",
            "- Kept all four tables; analysis uses the **50 SKUs** present in `sales_daily`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_data_foundation(persist: bool = True) -> tuple[dict[str, pd.DataFrame], dict]:
    raw = load_raw()
    clean = clean_datasets(raw)
    report = build_quality_report(raw, clean)

    if persist:
        DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        for name, df in clean.items():
            out = DATA_PROCESSED / f"{name}.csv"
            df.to_csv(out, index=False)
        write_quality_markdown(report, REPORTS_DIR / "DATA_QUALITY_REPORT.md")
        (REPORTS_DIR / "data_quality_summary.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )

    return clean, report
