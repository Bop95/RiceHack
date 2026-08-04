# Store Visits: Five Analysis Questions

These questions are answerable or supportable with the store-visit dataset and connect
to FinalFlow's Transportation & Access goal. Every answer must retain the limitation
that store visits are a commercial-activity proxy, not observed spectator movement.

## 1. How does commercial activity change by weekday, weekend, month, and season?

- **Fields:** `LOCAL_DATE`, `DAILY_VISITS`, `CATEGORY`, `MARKET`
- **Approach:** Aggregate visits by calendar period and compare patterns within each
  category and market.
- **Project value:** Establishes historical timing patterns that can inform transparent
  baseline scenarios.
- **Caution:** Daily records cannot determine match-hour arrival or departure timing.

## 2. Which visitor-relevant categories show the strongest activity in the New York/New Jersey market?

- **Fields:** `MARKET`, `CATEGORY`, `SUB_CATEGORY`, `DAILY_VISITS`
- **Approach:** Filter to `New York/New Jersey`, then compare hotels, restaurants,
  entertainment, transportation-related businesses, and other relevant categories.
- **Project value:** Helps identify commercial categories that may contribute to
  visitor-origin or activity-zone assumptions.
- **Caution:** High commercial activity does not prove that customers are World Cup fans.

## 3. Which brands and categories have stable activity, and which have large changes or spikes over time?

- **Fields:** `BRAND`, `CATEGORY`, `LOCAL_DATE`, `DAILY_VISITS`
- **Approach:** Build brand/category time series and compare typical levels with
  variability and unusually high days.
- **Project value:** Separates dependable baselines from volatile patterns when creating
  later scenarios or dashboard explanations.
- **Caution:** Apparent spikes may reflect transformation noise, coverage changes, or
  unusual records and require validation.

## 4. How do markets compare after accounting for the number of active stores?

- **Fields:** `MARKET`, `STORE_ID`, `LOCAL_DATE`, `DAILY_VISITS`
- **Approach:** Compare both total visits and normalized measures such as visits per
  active store-day instead of ranking markets only by raw totals.
- **Project value:** Produces a fairer cross-market benchmark for host-market readiness
  discussions.
- **Caution:** Combined market labels such as `Dallas / Houston` prevent clean
  city-versus-city conclusions.

## 5. Which stores or business groups could provide transparent weights for FinalFlow origin-zone scenarios?

- **Fields:** `STORE_ID`, `CATEGORY`, `SUB_CATEGORY`, `MARKET`, `DAILY_VISITS`
- **Approach:** Select relevant business types, summarize their relative activity, and
  later join approved POI/location data before normalizing them into scenario weights.
- **Project value:** Connects observed historical commercial patterns to FinalFlow's
  modeled origin zones without pretending the weights are observed spectator shares.
- **Caution:** The store-visit file alone has no coordinates, and any normalized result
  would be `derived` scenario input rather than provided fan-origin data.
