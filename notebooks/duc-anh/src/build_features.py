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

def fuzzy_match_col(df, keywords):
    """Tim ten cot thuc te co chua tu khoa (Khong phan biet hoa thuong)"""
    for col in df.columns:
        for kw in keywords:
            if kw.upper() in str(col).upper():
                return col
    return None

def process_spend_data(data_dir, clean_dir):
    print('Step 2: Processing financial spend aggregations...')
    folder_path = os.path.join(data_dir, 'daily-spend-brand-and-state-rice')
    files = find_files(folder_path)
    if not files: return

    daily_list = []
    brand_list = []

    for f in files:
        df = pd.read_parquet(f) if f.endswith('.parquet') else pd.read_csv(f, compression='gzip' if f.endswith('.gz') else None)
        spend_col = fuzzy_match_col(df, ['SPEND', 'AMOUNT'])
        date_col = fuzzy_match_col(df, ['DATE', 'TRANS_DATE'])
        trans_col = fuzzy_match_col(df, ['TRANS_COUNT', 'COUNT'])
        brand_col = fuzzy_match_col(df, ['BRAND'])

        if spend_col:
            df = df[pd.to_numeric(df[spend_col], errors='coerce') > 0]
        if date_col and spend_col and trans_col:
            df[date_col] = pd.to_datetime(df[date_col]).dt.date
            daily_grp = df.groupby(date_col).agg(TOTAL_SPEND=(spend_col, 'sum'), TRANS_COUNT=(trans_col, 'sum')).reset_index()
            daily_list.append(daily_grp)
        if brand_col and spend_col and trans_col:
            brand_grp = df.groupby(brand_col).agg(TOTAL_REVENUE=(spend_col, 'sum'), TOTAL_TRANS=(trans_col, 'sum')).reset_index()
            brand_list.append(brand_grp)
        del df

    if daily_list:
        final_daily = pd.concat(daily_list).groupby(daily_list[0].columns[0]).sum().reset_index()
        final_daily.to_csv(os.path.join(clean_dir, 'daily_business_trends.csv'), index=False)
        print(f'-> Exported 1/5: daily_business_trends.csv')

    if brand_list:
        final_brand = pd.concat(brand_list).groupby(brand_list[0].columns[0]).sum().reset_index()
        final_brand['AVG_SPEND_PER_TRANS'] = (final_brand['TOTAL_REVENUE'] / final_brand['TOTAL_TRANS']).round(2)
        final_brand.to_csv(os.path.join(clean_dir, 'brand_spending_summary.csv'), index=False)
        print(f'-> Exported 2/5: brand_spending_summary.csv')

def process_poi_data(data_dir, clean_dir):
    print('Step 3: Processing geospatial POI mapping...')
    folder_path = os.path.join(data_dir, 'core-poi-geometry-rice')
    files = find_files(folder_path)
    if not files: return

    poi_list = []
    for f in files:
        df = pd.read_parquet(f) if f.endswith('.parquet') else pd.read_csv(f, compression='gzip' if f.endswith('.gz') else None)
        place_col = fuzzy_match_col(df, ['PLACEKEY', 'ID'])
        lat_col = fuzzy_match_col(df, ['LAT', 'LATITUDE'])
        lon_col = fuzzy_match_col(df, ['LON', 'LONGITUDE'])
        cols = [c for c in [place_col, lat_col, lon_col] if c is not None]
        if cols: poi_list.append(df[cols].dropna().drop_duplicates())
        del df

    if poi_list:
        final_poi = pd.concat(poi_list).drop_duplicates()
        final_poi.to_csv(os.path.join(clean_dir, 'poi_business_locations.csv'), index=False)
        print(f'-> Exported 3/5: poi_business_locations.csv')


def process_visits_data(data_dir, clean_dir):
    print('Step 4: Processing foot traffic aggregations...')
    folder_path = os.path.join(data_dir, 'store-visits-rice')
    files = find_files(folder_path)
    if not files: return

    visit_list = []
    for f in files:
        df = pd.read_parquet(f) if f.endswith('.parquet') else pd.read_csv(f, compression='gzip' if f.endswith('.gz') else None)
        visit_col = fuzzy_match_col(df, ['VISIT', 'COUNT'])
        brand_col = fuzzy_match_col(df, ['LOCATION', 'BRAND', 'NAME'])
        
        if visit_col and brand_col:
            df[visit_col] = pd.to_numeric(df[visit_col], errors='coerce').fillna(0)
            grp = df.groupby(brand_col).agg(TOTAL_VISITS=(visit_col, 'sum')).reset_index()
            visit_list.append(grp)
        del df

    if visit_list:
        final_visits = pd.concat(visit_list).groupby(visit_list[0].columns[0]).sum().reset_index()
        final_visits.to_csv(os.path.join(clean_dir, 'visits_by_brand_category.csv'), index=False)
        print(f'-> Exported 4/5: visits_by_brand_category.csv')
    else:
        print('-> Error: Could not identify Visit Count or Brand columns.')


def process_weather_data(data_dir, clean_dir):
    print('Step 5: Processing meteorological data...')
    folder_path = os.path.join(data_dir, 'daily-weather-rice')
    files = find_files(folder_path)
    if not files: return

    weather_list = []
    for f in files:
        df = pd.read_parquet(f) if f.endswith('.parquet') else pd.read_csv(f, compression='gzip' if f.endswith('.gz') else None)
        date_col = fuzzy_match_col(df, ['DATE'])
        temp_col = fuzzy_match_col(df, ['TEMP', 'MAXIMUM_TEMPERATURE_C'])
        precip_col = fuzzy_match_col(df, ['PRECIP', 'PRECIPITATION_MM'])
        
        if date_col:
            agg_dict = {}
            if temp_col: agg_dict['MAX_TEMP_C'] = (temp_col, 'max')
            if precip_col: agg_dict['TOTAL_PRECIPITATION_MM'] = (precip_col, 'sum')
            if agg_dict:
                grp = df.groupby(date_col).agg(**agg_dict).reset_index()
                weather_list.append(grp)
        del df

    if weather_list:
        final_weather = pd.concat(weather_list)
        final_agg = {}
        if 'MAX_TEMP_C' in final_weather.columns: final_agg['MAX_TEMP_C'] = 'max'
        if 'TOTAL_PRECIPITATION_MM' in final_weather.columns: final_agg['TOTAL_PRECIPITATION_MM'] = 'sum'
        
        final_weather = final_weather.groupby(final_weather.columns[0]).agg(final_agg).reset_index()
        final_weather.to_csv(os.path.join(clean_dir, 'weather_business_summary.csv'), index=False)
        print(f'-> Exported 5/5: weather_business_summary.csv')
    else:
        print('-> Error: Could not identify Weather Date or Temp/Precip columns.')

def build_features():
    print('Step 1: Initializing data_clean output directory...')
    clean_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data_clean'))
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data_raw'))
    os.makedirs(clean_dir, exist_ok=True)

    process_spend_data(data_dir, clean_dir)
    process_poi_data(data_dir, clean_dir)
    process_visits_data(data_dir, clean_dir)
    process_weather_data(data_dir, clean_dir)

    print('Feature engineering execution completed successfully.')

if __name__ == '__main__':
    build_features()