# Store Visits: Cleaning and Summarization Notes

## Purpose

`scripts/data/clean_store_visits.py` is the single reusable Step-2 pipeline. It reads
the supplied CSV or compressed CSV shards with DuckDB so the full dataset does not
need to fit in memory. It never edits the original Rice files.

## Cleaning rules

The script:

1. verifies that every source file has the expected 13-column header;
2. trims text, converts blanks to nulls, and standardizes state and stock fields to
   uppercase;
3. parses `LOCAL_DATE` strictly as `YYYY-MM-DD` and `DAILY_VISITS` as a whole integer;
4. excludes rows missing `STORE_ID`, a valid date, or a valid visit count, plus rows
   with negative visits;
5. removes only exact duplicates after normalization;
6. retains zero visits with `is_zero_visits = true`;
7. retains visits above the exact discrete 99.9th percentile with
   `is_suspicious_high_visits = true`; this is a review flag, not a claim that the
   value is wrong; and
8. retains non-identical records sharing a store and date, while reporting their
   count for a future business-rule decision.

Exact percentiles are calculated efficiently from the frequency distribution of
`DAILY_VISITS`. The complete cleaned dataset has only 25,058 distinct visit values,
so this method is both exact and small enough to calculate safely.

NAICS values are summarized by 4-, 5-, and 6-digit granularity. Shorter values are
not called suspicious: the observed 4-digit values align with missing
`SUB_CATEGORY`, suggesting a broader classification level. This interpretation must
still be checked against `WorldCupHack_Dictionary.xlsx` when the team provides it.

## Outputs

- `data/processed/store_visits_clean.parquet`: typed row-level derived dataset.
- `data/summaries/data_quality_report.md`: readable checks and decisions.
- `data/summaries/summary_statistics.csv`: one-row overall summary.
- `data/summaries/visit_percentiles.csv`: exact percentiles and the flag threshold.
- `data/summaries/visits_by_brand.csv`, `visits_by_category.csv`, and
  `visits_by_market.csv`: commercial group summaries.
- `data/summaries/weekday_patterns.csv` and `monthly_trends.csv`: time summaries.
- `data/summaries/run_metadata.json`: source fingerprints, parameters, software
  versions, pipeline SHA-256 hash, threshold, and row counts for reproducibility.

The summary tables include record counts, unique-store counts, and mean daily visits.
Because the complete cleaned dataset has no duplicate `STORE_ID` plus `LOCAL_DATE`
pairs, each row represents one store-day and `mean_daily_visits` is also the observed
mean per store-day. Later comparisons should use this mean alongside totals so groups
with more stores or dates are not automatically treated as more active.

## Reproducibility and safety

`--limit` materializes one test sample before any checks, so every calculation within
the run uses the same rows. Exact-duplicate and store-date checks are hash-partitioned
into bounded buckets to avoid one very large in-memory group-by. `--memory-limit` and
`--temp-limit` make resource limits explicit, and the script checks available
temporary disk space before starting. Completed work is promoted with rollback: if
any replacement fails, the previous generated outputs are restored.

Generated data remains ignored by Git. Publishing any derived summary requires a
separate team decision because the source data may be restricted or licensed.

## Interpretation limits

The cleaned data supports relative historical commercial-activity analysis. It is
not observed World Cup attendance, pedestrian flow, transit ridership, a causal
estimate, or an exact future forecast. The distribution is strongly right-skewed, so
later analysis should emphasize medians, interquartile ranges, normalized rates, and
possibly log-scaled plots rather than relying only on means and totals.
