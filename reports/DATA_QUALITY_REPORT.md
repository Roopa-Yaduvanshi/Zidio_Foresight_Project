# Data quality report (M1 — Data foundation)

NorthBay Living / Zidio FORESIGHT — four provided extracts after cleaning.

| Check | Result |
|-------|--------|
| sales daily rows | 36550 |
| inventory rows | 4800 |
| sku master rows | 50 |
| calendar rows | 731 |
| sales duplicate date sku removed | 0 |
| inventory duplicate snapshot sku removed | 0 |
| sales skus | 50 |
| inventory skus | 200 |
| skus in sales and inventory | 50 |
| inventory skus not in sales | 150 |
| calendar missing holiday | 723 |
| calendar missing promotion event | 656 |

## Cleaning actions

- Parsed date columns to datetime.
- Standardised calendar `None` labels to missing values.
- Removed duplicate `(Date, SKU)` in sales and `(Snapshot_Date, SKU)` in inventory.
- Kept all four tables; analysis uses the **50 SKUs** present in `sales_daily`.
