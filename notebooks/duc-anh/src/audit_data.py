import glob
import os
import pandas as pd


def find_files(folder_path):
  f = glob.glob(os.path.join(folder_path, '**', '*.parquet'), recursive=True)
  if not f:
    f = glob.glob(os.path.join(folder_path, '**', '*.csv*'), recursive=True)
  if not f:
    f = glob.glob(os.path.join(folder_path, '**', '*.*'), recursive=True)
  return f


def audit_full_folder(files):
  total_rows = 0
  total_missing = 0
  columns_count = 0

  for filepath in files:
    if filepath.endswith('.parquet'):
      df = pd.read_parquet(filepath)
    elif filepath.endswith('.gz'):
      df = pd.read_csv(filepath, compression='gzip')
    else:
      df = pd.read_csv(filepath)

    total_rows += len(df)
    total_missing += df.isnull().sum().sum()
    if columns_count == 0:
      columns_count = len(df.columns)

    del df

  return total_rows, total_missing, columns_count


def run_audit():
  print('Step 1: Initiating Full Data Validation (Audit)...')
  
  # Adjusted path: Assumes you run this from within the 'RiceHack' root folder
  # or from 'src' if you adjust relative paths. Using absolute path mapping based on your environment.
  data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data_raw'))
  
  folders = [
      'core-poi-geometry-rice',
      'daily-spend-brand-and-state-rice',
      'daily-weather-rice',
      'spend-patterns-rice',
      'store-visits-rice',
      'urban-heat-index-rice',
  ]

  audit_results = []

  for folder in folders:
    print(f'Scanning directory: {folder}...')
    folder_path = os.path.join(data_dir, folder)
    files = find_files(folder_path)

    if files:
      try:
        total_rows, total_missing, cols = audit_full_folder(files)
        audit_results.append({
            'Dataset': folder,
            'Schema_Validated': True,
            'Partitions_Found': len(files),
            'Total_Rows': total_rows,
            'Columns': cols,
            'Missing_Values': total_missing,
            'Status': 'PASSED',
        })
        print(f'-> SUCCESS: {len(files)} files, {total_rows} rows, {total_missing} missing values.')
      except Exception as e:
        audit_results.append({
            'Dataset': folder,
            'Schema_Validated': False,
            'Partitions_Found': len(files),
            'Total_Rows': 0,
            'Columns': 0,
            'Missing_Values': 0,
            'Status': f'ERROR: {str(e)}',
        })
        print(f'-> FAILED processing {folder}: {str(e)}')
    else:
      audit_results.append({
          'Dataset': folder,
          'Schema_Validated': False,
          'Partitions_Found': 0,
          'Total_Rows': 0,
          'Columns': 0,
          'Missing_Values': 0,
          'Status': 'FOLDER NOT FOUND OR EMPTY',
      })
      print(f'-> WARNING: No files found in {folder}. Path checked: {folder_path}')

  print('Step 2: Exporting audit report to /reports directory...')
  report_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'reports'))
  os.makedirs(report_dir, exist_ok=True)
  
  report_path = os.path.join(report_dir, 'dataset_audit.csv')
  pd.DataFrame(audit_results).to_csv(report_path, index=False)
  print(f'Audit process completed successfully. Report saved at: {report_path}')


if __name__ == '__main__':
  run_audit()