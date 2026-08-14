import os
import pandas as pd


def export_integration_schema():
  print('Step 1: Verifying input scenario files...')
  clean_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data_clean'))
  in_path = os.path.join(clean_dir, 'vendor_zone_scenarios.csv')
  
  if os.path.exists(in_path):
    print('-> Input file located. Reading data into memory...')
    df_final = pd.read_csv(in_path)

    print('Step 2: Processing operational reasoning and data confidence flags...')

    def get_reason(row):
      if row['placement_class'] == 'Recommended':
        return 'Low risk, high traffic corridor'
      elif row['placement_class'] == 'Avoided':
        return 'High risk stadium egress chokepoint'
      else:
        return 'Requires strict queue management'

    df_final['data_confidence'] = 'High'
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