# Synthetic Store-Visit Scenario Data Dictionary

This synthetic dataset is for interface testing, visualization, and scenario exploration. It does not represent measured World Cup activity or exact future store demand.

## Reproducibility

- Rows: 12,000
- Fixed random seed: 2026
- Negative values: prevented by construction
- Data label: `synthetic`

## Scenario multipliers

- `ordinary_day` (Ordinary day): 1.00x baseline
- `pre_match` (Pre-match): 1.25x baseline
- `during_match` (During match): 0.85x baseline
- `post_match` (Post-match): 1.45x baseline
- `rainy_post_match` (Rainy post-match): 1.20x baseline
- `transit_disruption` (Transit disruption): 1.10x baseline

Zone weights are 1.30 for stadium districts, 1.18 for transit hubs, 1.22 for
fan zones, and 1.00 for commercial corridors. They are divided by their 1.175
mean so the average zone effect is 1.00x; the stated scenario multiplier remains
the expected overall effect. A bounded random factor from 0.65 to 1.35 adds
variation. Brands are sampled from the top 25 using square-root total-visit
weights. Each sampled brand's category is then drawn from that brand's observed
prepared category mix using record-count weights. These assumptions are
illustrative, not predictions.

## Fields

| Field | Meaning |
| --- | --- |
| `scenario_id` | Stable identifier for one of six hypothetical scenarios. |
| `timestamp` | Hypothetical interface-testing timestamp, not a match schedule. |
| `match_phase` | Ordinary, pre-match, during-match, or post-match phase. |
| `zone_type` | Hypothetical stadium, transit, fan-zone, or commercial context. |
| `brand` | Brand sampled from the derived store-visit brand summary. |
| `category` | Category sampled from the selected brand's derived category mix. |
| `baseline_visits` | Synthetic baseline based on historical mean intensities. |
| `estimated_visits` | Baseline after documented scenario, zone, and noise factors. |
| `weather_condition` | Simplified clear or rain scenario condition. |
| `demand_level` | Low, medium, high, or very-high synthetic demand band. |
| `pedestrian_pressure` | Low, medium, or high illustrative pressure band. |
| `mobility_conflict_risk` | Low, medium, or high illustrative conflict-risk band. |
| `is_synthetic` | Always `true`. |
| `data_type` | Always `synthetic`. |
