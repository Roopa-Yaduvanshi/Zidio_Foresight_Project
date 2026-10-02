# FORESIGHT — Executive readout

**Client context:** NorthBay Living (fictional assignment dataset)  
**Product:** FORESIGHT — demand forecasting and inventory intelligence  
**Snapshot date (inventory):** Latest row in `inventory_snapshots.csv`

## Problem

SKU-level demand is variable; holding too little stock causes lost sales, while holding too much ties up capital. Leadership needs **forecast-informed replenishment** with clear dollar impact.

## Approach (Zidio milestones)

1. **M1 — Data foundation** — Clean four extracts; data-quality report in `reports/DATA_QUALITY_REPORT.md`.
2. **M2 — EDA & baseline** — Weekly SKU demand features; **seasonal-naive (lag-52)** baseline.
3. **M3 — Modelling & risk** — Random Forest vs baseline with **rolling-origin backtest** and **WAPE**; stockout/overstock scoring.
4. **M4 — Productize** — Streamlit dashboard (`app.py`), optional FastAPI (`service/main.py`), replenishment CSV.

**Backtest (12 weekly origins):** Random Forest WAPE **10.05%** vs seasonal naive **11.51%** (lower is better).

## Inventory logic

- Stock position = on-hand + on-order; target stock = forecast lead-time demand + safety stock.
- **High Risk (Stockout)** when days of cover is below lead time; **Overstock Risk** when cover exceeds 2× lead time or stock exceeds 1.5× target.
- Recommendations: order max(0, target − position); cost = units × cost price.

## Key results (current run)

| Metric | Value |
|--------|------:|
| Active SKUs | 50 |
| SKUs needing replenishment | 5 |
| Total recommended units | 513 |
| Estimated replenishment cost | ₹ 21,50,193.67 |
| High-risk SKUs (coverage) | 5 |

### Priority replenishment (top 5)

| SKU | Product | Recommended units | Est. cost (₹) |
|-----|---------|------------------:|--------------:|
| SKU012 | Product 012 | 186 | 2,33,781.54 |
| SKU017 | Product 017 | 132 | 8,84,830.32 |
| SKU031 | Product 031 | 91 | 5,73,359.15 |
| SKU010 | Product 010 | 62 | 2,41,121.72 |
| SKU040 | Product 040 | 42 | 2,17,100.94 |

## Recommended actions

1. **Approve PO** for the five SKUs above within standard lead-time windows (9–13 days).
2. **Review high unit-cost SKUs** (SKU017) for supplier MOQ or alternate sourcing before final PO.
3. **Monitor** remaining 45 SKUs classified as sufficient/healthy on weekly inventory review.
4. **Re-run pipeline** when new sales and snapshot files arrive (weekly cadence).

## Live demo

- **Dashboard:** Streamlit app (`app.py`) — Overview, Replenishment, Demand trends, Inventory risk.
- **API (optional):** `service/main.py` — JSON recommendations for integration tests.

## Evaluation talking points

- **Why days-of-cover vs lead time?** If cover is shorter than supplier lead time, you cannot restock before expected stockout.
- **Why target stock formula?** Covers expected demand during lead time plus safety buffer from snapshot data.
- **What would you improve next?** Seasonal-naive baseline + WAPE rolling backtest (M3), persisted ML model in `models/`, automated data-quality report (M1).
