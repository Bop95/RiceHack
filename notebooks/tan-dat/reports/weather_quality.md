# Daily Weather Dataset Data Quality Report

## 1. Dataset Overview
* **Total Raw Records:** 45,814 rows
* **Date Range:** 2020-01-01 to 2024-12-31
* **Unique Weather Stations:** 401 locations

## 2. Cleaning & Sentinel Handling
* **Column Renaming:** Standardized long raw schema headers to snake_case identifiers.
* **Precipitation Sentinels:** Converted `-1` sentinel values (indicating No Precipitation) to `0.0 mm`. Converted hundredths of a millimeter to millimeters (`x / 100.0`).
* **Temperature Consistency:** Verified that `temperature_min_c <= temperature_avg_c <= temperature_max_c` across records.