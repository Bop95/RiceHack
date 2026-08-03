import os
import pandas as pd
os.makedirs('data/processed', exist_ok=True)
file_name = "daily-weather-rice_3_5_0.csv"
df = pd.read_csv(file_name)

column_mapping = {
    'CITY_LOCATION_IDENTIFIER__UP_TO_9_ALPHANUMERIC_CHARACTERS_': (
        'location_id'
    ),
    'VALID_DATE_AS_YYYYMMDD': 'date',
    'MAXIMUM_TEMPERATURE_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE': (
        'temperature_max_c'
    ),
    'MINIMUM_TEMPERATURE_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE': (
        'temperature_min_c'
    ),
    'AVERAGE_TEMPERATURE_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE': (
        'temperature_avg_c'
    ),
    'AVERAGE_RELATIVE_HUMIDITY_____FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE': (
        'relative_humidity_pct'
    ),
    'AVERAGE_WIND_SPEED_KNOTS___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE': (
        'wind_speed_knots'
    ),
    'AVERAGE_VISIBILITY_KILOMETERS___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE': (
        'visibility_km'
    ),
    (
        'PRECIPITATION_INTEGER_IN_HUNDREDTHS_OF_A_MILLIMETER___LIQUID_EQUIVALENT____0__IS_USED_FOR_TRACE_AMOUNTS_AND___1__IS_USED_FOR_NO_PRECIPITATION'
    ): 'precipitation_raw',
    'AVERAGE_DEW_POINT_F___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE': (
        'dew_point_f'
    ),
    (
        'AVERAGE_SEA_LEVEL_PRESSURE_MILLIBARS___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE'
    ): 'sea_level_pressure_mb',
    'COOLING_DEGREE_DAYS_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE': (
        'cooling_degree_days_c'
    ),
    'HEATING_DEGREE_DAYS_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE': (
        'heating_degree_days_c'
    ),
}

df = df.rename(columns=column_mapping)
df['date'] = pd.to_datetime(df['date'])
df['precipitation_mm'] = df['precipitation_raw'].apply(
    lambda x: 0.0 if x < 0 else x / 100.0
)
output_csv = 'data/processed/daily_weather_clean.csv'
df.to_csv(output_csv, index=False)
print(f'Saved cleaned dataset to {output_csv} ({len(df):,} rows)')