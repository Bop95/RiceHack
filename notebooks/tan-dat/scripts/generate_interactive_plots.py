import os
import pandas as pd
import plotly.express as px

# 1. Read directly from your cleaned CSV file
clean_csv_path = 'data/processed/daily_weather_clean.csv'
df = pd.read_csv(clean_csv_path)

# Ensure date column is proper datetime
df['date'] = pd.to_datetime(df['date'])

# Ensure output directory exists
os.makedirs('reports/figures', exist_ok=True)

# --------------------------------------------------------------------------
# Plot 1: Interactive Date Weather Explorer (Aggregated Macro Trend)
# --------------------------------------------------------------------------
# Group by date across all location IDs to get clean macro daily averages
daily_macro = (
    df.groupby('date')[
        ['temperature_max_c', 'temperature_avg_c', 'temperature_min_c']
    ]
    .mean()
    .reset_index()
)

fig1 = px.line(
    daily_macro,
    x='date',
    y=['temperature_max_c', 'temperature_avg_c', 'temperature_min_c'],
    labels={
        'date': 'Date',
        'value': 'Temperature (°C)',
        'variable': 'Temperature Metric',
    },
    title=(
        'Interactive Weather Explorer: Daily Temperature Trend (Macro'
        ' Aggregated)'
    ),
)

# Add range slider and quick time-window selection buttons
fig1.update_xaxes(
    rangeslider_visible=True,
    rangeselector=dict(
        buttons=list([
            dict(count=1, label='1m', step='month', stepmode='backward'),
            dict(count=6, label='6m', step='month', stepmode='backward'),
            dict(count=1, label='YTD', step='year', stepmode='todate'),
            dict(count=1, label='1y', step='year', stepmode='backward'),
            dict(step='all'),
        ])
    ),
)
fig1.update_layout(template='plotly_white', hovermode='x unified')

plot1_path = 'reports/figures/interactive_weather_explorer.html'
fig1.write_html(plot1_path)
print(f'Saved Plot 1 to {plot1_path}')

# --------------------------------------------------------------------------
# Plot 2: Interactive Weather-Risk Timeline & Scatter Matrix
# --------------------------------------------------------------------------
# Compute FinalFlow Risk Features
df['is_hot'] = (df['temperature_max_c'] >= 30.0).astype(int)
df['is_rainy'] = (df['precipitation_mm'] > 0.0).astype(int)
df['is_windy'] = (df['wind_speed_knots'] >= 20.0).astype(int)
df['is_low_vis'] = (df['visibility_km'] <= 5.0).astype(int)

df['weather_risk_score'] = (
    0.35 * df['is_hot']
    + 0.30 * df['is_rainy']
    + 0.15 * df['is_windy']
    + 0.20 * df['is_low_vis']
).round(2)


def assign_risk_level(score):
  if score < 0.3:
    return 'Low Risk'
  elif score < 0.6:
    return 'Medium Risk'
  else:
    return 'High Risk'


df['weather_risk_level'] = df['weather_risk_score'].apply(assign_risk_level)

# Sample 5,000 points to ensure smooth interactive browser performance
df_sample = df.sample(n=min(5000, len(df)), random_state=42).sort_values(
    'weather_risk_score'
)

fig2 = px.scatter(
    df_sample,
    x='temperature_max_c',
    y='relative_humidity_pct',
    size='precipitation_mm',
    color='weather_risk_level',
    hover_data=[
        'date',
        'location_id',
        'wind_speed_knots',
        'visibility_km',
        'weather_risk_score',
    ],
    color_discrete_map={
        'Low Risk': '#2ca02c',
        'Medium Risk': '#ff7f0e',
        'High Risk': '#d62728',
    },
    labels={
        'temperature_max_c': 'Max Temperature (°C)',
        'relative_humidity_pct': 'Relative Humidity (%)',
        'precipitation_mm': 'Precipitation (mm)',
        'weather_risk_level': 'Risk Level',
    },
    title=(
        'Interactive Weather-Risk Scatter Plot: Thermal & Precipitation Stress'
    ),
)

fig2.update_layout(template='plotly_white')

plot2_path = 'reports/figures/interactive_weather_risk_matrix.html'
fig2.write_html(plot2_path)
print(f'Saved Plot 2 to {plot2_path}')