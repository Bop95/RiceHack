# Store Visits: Visualization Interpretations

## Scope

These charts describe **relative historical commercial activity** in the transformed
Rice store-visit data. They do not measure World Cup attendance, pedestrian counts,
transit ridership, causality, or exact future demand. All chart inputs are labeled
`derived` and come from the Step-2 clean dataset and summary tables.

## Static plots

### 1. Top brands by total visits

File: `reports/figures/store_visits_top_brands.png`

- `Walmart` has the largest total among the displayed brands at
  5.35 billion transformed visits.
- Across its 368 stores, the mean is
  8,043.57 visits per store-day. This shows why
  total rankings combine business footprint and activity intensity.
- Brand totals are useful for prioritization, but they should not be interpreted as
  evidence that a brand causes higher mobility demand.

### 2. Category scale versus daily intensity

File: `reports/figures/store_visits_top_categories.png`

- `Restaurants and Other Eating Places` accounts for
  43.1% of all transformed
  visits, making it the dominant category by total scale.
- Among the displayed high-total categories,
  `General Merchandise Stores, including Warehouse Clubs and Supercenters` has the highest mean daily intensity at
  1,676.93 visits per store-day.
- The two panels prevent a large category footprint from being confused with a high
  activity level at the typical store-day record.

### 3. Weekday pattern

File: `reports/figures/store_visits_weekday_pattern.png`

- `Saturday` is highest at
  727.60 mean visits per store-day;
  `Monday` is lowest at
  549.77.
- The high day is 32.3% above the low day.
- Because weekday record counts are nearly equal, the mean comparison is more useful
  here than comparing raw totals.

### 4. Visit distribution

File: `reports/figures/store_visits_distribution.png`

- 8.31% of records have zero visits and are retained rather than
  deleted.
- The median is 199, well below the mean of
  620.77; this confirms a strongly right-skewed
  distribution.
- The exact p99 is 4,348 and p99.9 is
  10,647. Values above p99.9 are review candidates, not
  automatically invalid observations.

## Interactive plots

### 5. Monthly trend

File: `reports/interactive/store_visits_monthly_trend.html`

- The selector switches between mean daily intensity and total monthly scale; hover
  shows totals, records, and unique stores for each month.
- Monthly totals are affected by the number of days in each month; the mean view
  removes that calendar-length effect.
- The lowest monthly mean is 168.53 in
  April 2020; the highest is
  727.44 in
  February 2020.
- The chart reveals timing and recovery patterns, but the dataset alone cannot prove
  what caused any rise or decline.

### 6. Market comparison

File: `reports/interactive/store_visits_market_comparison.html`

- `Los Angeles / SF Bay Area` has the largest total at
  30.95 billion transformed visits.
- `Miami` has the highest mean daily intensity at
  695.49 visits per store-day.
- Bubble size represents unique stores, making it possible to distinguish market
  footprint from per-record intensity. Combined market labels such as
  `Los Angeles / SF Bay Area` must not be treated as single cities.

## Recommended use

Use the static plots in reports or presentations and the interactive plots for
exploration or dashboard prototyping. For later World Cup scenarios, use these
patterns as transparent historical baselines—not direct forecasts—and combine them
with event schedules, transport, weather, and approved geographic data.
