import pandas as pd

df = pd.read_csv('data/processed/daily_weather_clean.csv')

# Define Boolean Risk Indicators
df['is_hot'] = df['temperature_max_c'] >= 30.0
df['is_rainy'] = df['precipitation_mm'] > 0.0
df['is_windy'] = df['wind_speed_knots'] >= 20.0
df['is_low_visibility'] = df['visibility_km'] <= 5.0


def calculate_risk(row):
  score = 0.0
  actions = []
  if row['is_hot']:
    score += 0.35
    actions.append('Add water points & shade')
  if row['is_rainy']:
    score += 0.30
    actions.append('Covered waiting & shuttle capacity')
  if row['is_windy']:
    score += 0.15
    actions.append('Secure temporary structures')
  if row['is_low_visibility']:
    score += 0.20
    actions.append('Slower vehicle assumptions & staff guidance')

  score = min(score, 1.0)
  if score >= 0.6:
    level = 'High'
  elif score >= 0.3:
    level = 'Medium'
  else:
    level = 'Low'

  action_str = '; '.join(actions) if actions else 'Normal operations'
  return pd.Series([score, level, action_str])


df[['weather_risk_score', 'weather_risk_level', 'recommended_action']] = (
    df.apply(calculate_risk, axis=1)
)

integration_cols = [
    'location_id',
    'date',
    'temperature_avg_c',
    'precipitation_mm',
    'relative_humidity_pct',
    'wind_speed_knots',
    'visibility_km',
    'is_hot',
    'is_rainy',
    'is_windy',
    'is_low_visibility',
    'weather_risk_score',
    'weather_risk_level',
    'recommended_action',
]

output_df = df[integration_cols]
output_file = 'data/summaries/finalflow_weather_integration.csv'
output_df.to_csv(output_file, index=False)

print(f'Successfully built integration table at {output_file}!')