"""Generate illustrative vendor zones, explicitly labeled as synthetic scenarios."""

import os
from pathlib import Path
import numpy as np
import pandas as pd


def score_scenarios(output_dir: Path | None = None) -> None:
  """Write scenario rows to the business folder or a configurable test directory."""
  print('Step 1: Initializing random seed state (42)...')
  np.random.seed(42)

  print('Step 2: Generating synthetic vendor zone scenarios...')
  n_zones = 50
  df_scenarios = pd.DataFrame({
      'zone_id': [f'ZONE_{str(i).zfill(3)}' for i in range(1, n_zones + 1)],
      'zone_name': [f'MetLife Sector {i}' for i in range(1, n_zones + 1)],
      'latitude': np.random.normal(40.8136, 0.003, n_zones).round(6),
      'longitude': np.random.normal(-74.0744, 0.003, n_zones).round(6),
      'business_opportunity_score': np.round(
          np.random.uniform(20, 100, n_zones), 2
      ),
      'mobility_risk_score': np.round(np.random.uniform(10, 90, n_zones), 2),
  })

  print('Step 3: Applying placement logic classification matrix...')
  conditions = [
      (df_scenarios['business_opportunity_score'] >= 70)
      & (df_scenarios['mobility_risk_score'] <= 40),
      (df_scenarios['mobility_risk_score'] >= 75),
  ]
  choices = ['Recommended', 'Avoided']
  df_scenarios['placement_class'] = np.select(
      conditions, choices, default='Controlled'
  )
  df_scenarios['data_type'] = 'synthetic'
  df_scenarios['data_confidence'] = 'scenario'
  df_scenarios['scenario_id'] = 'vendor_zones_seed_42_v1'
  df_scenarios['assumption_note'] = (
      'Synthetic scenario: coordinates and scores are randomly generated with '
      'seed 42; placement classes use heuristic thresholds, not observed evidence.'
  )

  print('Step 4: Exporting generated scenarios to CSV...')
  clean_dir = output_dir if output_dir is not None else Path(__file__).resolve().parent.parent / 'data_clean'
  os.makedirs(clean_dir, exist_ok=True)
  
  scenario_out = os.path.join(clean_dir, 'vendor_zone_scenarios.csv')
  df_scenarios.to_csv(scenario_out, index=False)
  print(f'-> Exported successfuly: {scenario_out}')
  
  print('Scenario generation execution completed.')


if __name__ == '__main__':
  score_scenarios()
