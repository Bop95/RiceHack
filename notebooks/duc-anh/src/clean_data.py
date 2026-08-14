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


def load_partitioned_data(folder_name):
  print(f'Loading partitioned data for: {folder_name}...')
  data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data_raw'))
  folder_path = os.path.join(data_dir, folder_name)
  files = find_files(folder_path)
  
  if not files:
    print(f'-> No files found in directory {folder_name}.')
    return None
    
  df_list = []
  for f in files:
    if f.endswith('.parquet'):
      df_list.append(pd.read_parquet(f))
    elif f.endswith('.gz'):
      df_list.append(pd.read_csv(f, compression='gzip'))
    else:
      df_list.append(pd.read_csv(f))
      
  combined = pd.concat(df_list, ignore_index=True)
  print(f'-> Loaded successfully. Total rows: {len(combined)}')
  return combined


def clean_data():
  print('Step 1: Initializing output directory...')
  clean_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data_clean'))
  os.makedirs(clean_dir, exist_ok=True)

  print('Step 2: Cleaning daily-spend-brand-and-state-rice...')
  df_spend = load_partitioned_data('daily-spend-brand-and-state-rice')
  if df_spend is not None:
    if 'SPEND_AMOUNT' in df_spend.columns:
      df_spend = df_spend[df_spend['SPEND_AMOUNT'] >= 0]
      print('-> Filtered out negative SPEND_AMOUNT records.')
    if 'TRANS_DATE' in df_spend.columns:
      df_spend['TRANS_DATE'] = pd.to_datetime(df_spend['TRANS_DATE'])
      print('-> Standardized TRANS_DATE formatting.')

  print('Step 3: Cleaning core-poi-geometry-rice...')
  df_poi = load_partitioned_data('core-poi-geometry-rice')
  if df_poi is not None:
    if 'LATITUDE' in df_poi.columns and 'LONGITUDE' in df_poi.columns:
      df_poi = df_poi.dropna(subset=['LATITUDE', 'LONGITUDE'])
      print('-> Removed records with missing coordinate data.')

  print('Step 4: Cleaning daily-weather-rice...')
  df_weather = load_partitioned_data('daily-weather-rice')
  if df_weather is not None:
    if 'PRECIPITATION_MM' in df_weather.columns:
      df_weather = df_weather[df_weather['PRECIPITATION_MM'] >= 0]
      print('-> Filtered out negative precipitation anomalies.')

  print('Data cleaning execution completed.')


if __name__ == '__main__':
  clean_data()