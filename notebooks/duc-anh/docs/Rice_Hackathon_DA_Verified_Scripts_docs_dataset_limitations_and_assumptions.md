# Milestone July 28: Dataset Limitations & Notes
**Author:** Đức Anh (Data Analyst) & Phương Anh (Business Analyst)

## Data Validation Results
1. **Missing Geometries:** `core-poi-geometry-rice` contains empty array [] rows for unbranded locations. Assume these are temporary stalls and exclude from standard POI footprint density calculations.
2. **Memory Overhead:** The `POLYGON_WKT` column requires conversion to centroids for fast spatial joins to avoid memory crashes.
3. **Temporal Granularity:** `daily-weather-rice` and `daily-spend-brand-and-state-rice` only provide daily aggregates, not hourly.
