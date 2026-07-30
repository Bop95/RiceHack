# Store Visits: Dataset Notes

## Why this dataset matters

`store-visits-rice` gives FinalFlow a daily, transformed measure of activity at
commercial locations. It can help describe relative commercial activity around
visitor-oriented businesses and compare patterns across dates, categories, brands,
states, and broad markets.

The dataset must be described as a **commercial-activity proxy**. It is not measured
World Cup attendance, pedestrian flow, transit ridership, or exact future demand.

## Sources reviewed

- The FinalFlow project proposal, `World_Cup_26_Rice_Hack.pdf`.
- Hai Nam's direction guide, `Hai_Nam_Direction_Guide_Rice_Hack_26.pdf`.
- The repository README and its data-contract, dataset-layout, and Hai Nam workspace notes.
- The headers and a 100,000-row convenience sample from the local store-visit files.

The repository refers to `WorldCupHack_Dictionary.xlsx`, but that workbook was not
present in the repository, the downloaded dataset, Documents, or Downloads on the
inspection date. Therefore, the column guide separately identifies definitions taken
from the leader's guide and interpretations inferred from the field names and sample.
It should be checked against the official workbook once the team supplies it.

## Repository inspection

- Repository: `github.com/Bop95/RiceHack`
- Inspected baseline: `main` at commit `7bdeafa`
- Working branch: `hai-nam/store-visits-ai`
- Existing structure already separates data, documentation, notebooks, reports,
  scripts, tests, and the Streamlit prototype.
- Existing policy says restricted raw Rice files remain local and must not be committed.
- The repository already contains a general audit utility and placeholder store-visit
  cleaning/summarization scripts. No duplicate application or Step-2 workflow was
  created during this milestone.

## Local dataset inventory

- Format: 32 gzip-compressed CSV shards (`*.csv.gz`).
- Combined compressed size: 7,125,547,794 bytes (about 6.64 GiB).
- Raw columns: 13.
- All 32 inspected headers match exactly.
- Raw data remains outside the Git repository.

## How the sample was loaded

The inspection read the first 3,125 data records from each of the 32 sorted shards,
for 100,000 rows total. Reading across every shard checks schema consistency and gives
broader coverage than reading only one file.

This is a deterministic **convenience sample**, not a random sample. Counts and
percentages below describe only these 100,000 inspected rows and must not be presented
as full-dataset statistics.

## What the sample shows

| Check | Sample result |
| --- | ---: |
| Rows inspected | 100,000 |
| Columns | 13 |
| Distinct store IDs | 62,195 |
| Distinct brands | 3,844 |
| Distinct categories | 123 |
| Distinct sub-categories | 223 |
| Distinct markets | 9 |
| Distinct states | 11 |
| Earliest date | 2020-01-01 |
| Latest date | 2024-12-31 |
| Median daily visits | 242 |
| Mean daily visits | 677.99 |
| Minimum / maximum daily visits | 0 / 11,937 |

Additional observations:

- `LOCAL_DATE` parsed as an ISO date in every sampled row.
- `DAILY_VISITS` parsed as numeric in every sampled row.
- The sample contains 7,460 zero-visit records and no negative visit values.
- `STOCK_EXCHANGE` and `STOCK_SYMBOL` are blank in 51,359 sampled rows; this is
  plausible for private or otherwise unmatched businesses.
- `SUB_CATEGORY` is blank in 593 sampled rows.
- Every sampled `VERSION_ID` value is `9.0`.
- The most frequent sample category is `Restaurants and Other Eating Places`
  (32,484 rows), showing that food-service activity will be prominent in simple row
  counts. This does not establish its share in the complete dataset.

## Important limitations

1. The Rice files are transformed hackathon data. Numerical magnitudes may contain
   noise, so results demonstrate methods and relative patterns rather than exact local
   conditions.
2. Records are daily. They cannot reveal hour-by-hour pre-match or post-match movement.
3. The file contains no latitude or longitude. Location-level mapping requires a safe
   join to another approved dataset, likely through `STORE_ID` or another documented key.
4. Some `MARKET` values combine cities, such as `Dallas / Houston` and
   `Los Angeles / SF Bay Area`; they should not be treated as individual host cities.
5. A store may appear on many dates, so row counts are not store counts.
6. Sample summaries are exploratory only. Full-dataset claims require a complete,
   reproducible analysis in the next milestone.

## Step-1 conclusion

The dataset is suitable for studying relative historical commercial activity by time,
business type, brand, and broad market. Its most useful role in FinalFlow is to provide
transparent baseline patterns and possible scenario weights, with strong labels that
separate provided data from later derived or synthetic values.
