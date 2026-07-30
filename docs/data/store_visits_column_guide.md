# Store Visits: Column Guide

The raw files contain the following 13 columns in this order. "Recommended type"
means the type we should use in analysis later; this milestone does not convert or
clean any values.

| Column | Recommended type | Meaning and use | Priority | Definition status |
| --- | --- | --- | --- | --- |
| `BRAND` | Text | Business brand used for brand comparisons and dashboard filters. | Main | Leader's guide |
| `CATEGORY` | Text | Broad commercial category used to compare major kinds of activity. | Main | Leader's guide |
| `DAILY_VISITS` | Number | Transformed daily visit measure and the main numerical field. Aggregate it for relative activity patterns, not literal World Cup attendance. | Main | Leader's guide |
| `LOCAL_DATE` | Date (`YYYY-MM-DD`) | Local calendar date used for trends, weekdays, months, and historical baselines. | Main | Leader's guide |
| `MARKET` | Text | Broad regional market used for comparisons. A label may combine multiple cities. | Main | Leader's guide plus sample observation |
| `NAICS_CODE` | Text/category | Industry classification code. Keep it categorical rather than treating it as a quantity. | Supporting | Leader's guide |
| `NAME` | Text | Store or business label used for store-level identification and rankings. | Main | Leader's guide |
| `STATE` | Text | State abbreviation used for basic geographic grouping. | Main | Leader's guide |
| `STOCK_EXCHANGE` | Text | Exchange associated with a publicly traded company when available. Often blank and not central to FinalFlow. | Metadata | Inferred; verify with official dictionary |
| `STOCK_SYMBOL` | Text | Public-company ticker when available. Often blank and not central to FinalFlow. | Metadata | Inferred; verify with official dictionary |
| `STORE_ID` | Text identifier | Stable-looking store/location identifier used to count stores and follow the same location over dates. Never treat it as a number. | Main | Leader's guide |
| `SUB_CATEGORY` | Text | More detailed commercial classification nested below the broad category. | Main | Leader's guide |
| `VERSION_ID` | Text/version | Dataset or record-version metadata. Both the 100,000-row sample and the complete cleaned dataset contain only `9.0`; it is not a business metric. | Metadata | Inferred; verify with official dictionary |

## Most important relationships

- One `STORE_ID` can have many rows because activity is recorded on different
  `LOCAL_DATE` values.
- `CATEGORY` is broad; `SUB_CATEGORY` gives finer business detail.
- `BRAND` groups related businesses, while `NAME` is the store/business label.
- `STATE` and `MARKET` support broad geography, but neither provides an exact point
  location.
- `DAILY_VISITS` is interpreted together with `LOCAL_DATE` and a grouping field such as
  `STORE_ID`, `BRAND`, `CATEGORY`, or `MARKET`.

## Fields to focus on first

For the initial analysis, focus on:

1. `STORE_ID`
2. `BRAND`
3. `CATEGORY` and `SUB_CATEGORY`
4. `LOCAL_DATE`
5. `DAILY_VISITS`
6. `MARKET` and `STATE`

Treat `NAICS_CODE` as optional supporting classification. Document
`STOCK_EXCHANGE`, `STOCK_SYMBOL`, and `VERSION_ID`, but do not make them major analysis
features unless a later question specifically needs them.
