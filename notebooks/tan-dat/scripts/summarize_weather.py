import os
import pandas as pd

os.makedirs('data/summaries', exist_ok=True)

file_name = "data/processed/daily_weather_clean.csv"

df = pd.read_csv(file_name)
df['date'] = pd.to_datetime(df['date'])
df['month'] = df['date'].dt.month

# --- Table 1: weather_monthly.csv ---
monthly_summary = (
    df.groupby('month')
    .agg(
        temp_max_avg=('temperature_max_c', 'mean'),
        temp_avg_mean=('temperature_avg_c', 'mean'),
        temp_min_avg=('temperature_min_c', 'mean'),
        humidity_avg=('relative_humidity_pct', 'mean'),
        wind_speed_avg=('wind_speed_knots', 'mean'),
        total_precip_mm=('precipitation_mm', 'sum'),
        rainy_days=('precipitation_mm', lambda x: (x > 0).sum()),
    )
    .reset_index()
)

monthly_summary.to_csv('data/summaries/weather_monthly.csv', index=False)

# --- Table 2: weather_risk_days.csv (Summer Window) ---
summer_df = df[df['month'].isin([6, 7])].copy()
total_summer = len(summer_df)

risk_data = {
    'metric': [
        'Hot Days (>=30°C)',
        'Rainy Days (>0mm)',
        'Heavy Rain Days (>20mm)',
        'Windy Days (>=20 knots)',
        'Low Visibility Days (<=5km)',
    ],
    'count': [
        (summer_df['temperature_max_c'] >= 30.0).sum(),
        (summer_df['precipitation_mm'] > 0.0).sum(),
        (summer_df['precipitation_mm'] > 20.0).sum(),
        (summer_df['wind_speed_knots'] >= 20.0).sum(),
        (summer_df['visibility_km'] <= 5.0).sum(),
    ],
    'total_summer_days': total_summer,
}

risk_df = pd.DataFrame(risk_data)
risk_df['percentage'] = (risk_df['count'] / total_summer) * 100
risk_df.to_csv('data/summaries/weather_risk_days.csv', index=False)

print('Generated weather_monthly.csv and weather_risk_days.csv!')