"""Export synthetic vendor recommendations without claiming observed confidence."""

import os
from pathlib import Path
import pandas as pd


def export_integration_schema(data_dir: Path | None = None) -> None:
  """Label current and legacy scenario inputs before exporting to Power BI."""
  print('Step 1: Verifying input scenario files...')
  clean_dir = data_dir if data_dir is not None else Path(__file__).resolve().parent.parent / 'data_clean'
  in_path = os.path.join(clean_dir, 'vendor_zone_scenarios.csv')
  
  if os.path.exists(in_path):
    print('-> Input file located. Reading data into memory...')
    df_final = pd.read_csv(in_path)

    print('Step 2: Processing operational reasoning and data confidence flags...')

    def get_reason(row):
      if row['placement_class'] == 'Recommended':
        return 'Synthetic scenario: high opportunity and low risk scores under heuristic thresholds'
      elif row['placement_class'] == 'Avoided':
        return 'Synthetic scenario: risk score exceeds the avoidance threshold'
      else:
        return 'Synthetic scenario: scores fall in the controlled placement band'

    # This exporter consumes generated scenarios, including older unlabeled files.
    df_final['data_type'] = 'synthetic'
    df_final['data_confidence'] = 'scenario'
    if 'scenario_id' not in df_final:
      df_final['scenario_id'] = 'vendor_zones_seed_42_v1'
    else:
      df_final['scenario_id'] = df_final['scenario_id'].fillna('').astype(str).str.strip()
      df_final.loc[df_final['scenario_id'] == '', 'scenario_id'] = 'vendor_zones_seed_42_v1'
    df_final['assumption_note'] = (
        'Synthetic scenario: coordinates and scores are randomly generated with '
        'seed 42; placement classes use heuristic thresholds, not observed evidence.'
    )
    df_final['reason'] = df_final.apply(get_reason, axis=1)

    print('Step 3: Exporting final integration schema...')
    out_path = os.path.join(clean_dir, 'finalflow_business_integration.csv')
    df_final.to_csv(out_path, index=False)
    print(f'-> Exported successfully: {out_path}')
  else:
    print(f'-> ERROR: Failed to locate input file: {in_path}')

  print('Final integration schema generation completed.')


if __name__ == '__main__':
  export_integration_schema()
