import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Set visual style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'

# Ensure output directory exists
os.makedirs('reports/figures', exist_ok=True)

# 1. Load Datasets
clean_df = pd.read_csv('data/processed/daily_weather_clean.csv')
risk_df = pd.read_csv('data/summaries/weather_risk_days.csv')
integration_df = pd.read_csv(
    'data/summaries/finalflow_weather_integration.csv'
)

clean_df['date'] = pd.to_datetime(clean_df['date'])

# =============================================================================
# FIGURE 1: Cleaned Precipitation Distribution (Data Quality Validation)
# =============================================================================
fig1, ax1 = plt.subplots(figsize=(8, 5))
sample_clean = clean_df['precipitation_mm']

ax1.hist(
    sample_clean[sample_clean > 0],
    bins=35,
    color='#2b5c8f',
    edgecolor='black',
    alpha=0.8,
)
ax1.set_title(
    'Figure 1: Cleaned Precipitation Distribution (Excluding Sentinels)',
    fontweight='bold',
    fontsize=11,
)
ax1.set_xlabel('Precipitation Amount (mm)', fontweight='bold')
ax1.set_ylabel('Observation Frequency (Log Scale)', fontweight='bold')
ax1.set_yscale('log')  # Log scale highlights heavy rainfall tail
ax1.axvline(
    20.0,
    color='#e41a1c',
    linestyle='--',
    linewidth=2,
    label='Heavy Rain Threshold (20 mm)',
)
ax1.legend(loc='upper right')

plt.tight_layout()
fig1_path = 'reports/figures/fig1_precipitation_quality.png'
plt.savefig(fig1_path, dpi=300)
plt.close()
print(f'Saved: {fig1_path}')

# =============================================================================
# FIGURE 2: World Cup Window Weather Risk Frequency (Baseline Vulnerability)
# =============================================================================
fig2, ax2 = plt.subplots(figsize=(8, 5))
colors = ['#e41a1c', '#377eb8', '#7570b3', '#ff7f00', '#984ea3']
bars = ax2.bar(
    risk_df['metric'],
    risk_df['percentage'],
    color=colors,
    edgecolor='black',
    alpha=0.85,
)

ax2.set_title(
    'Figure 2: World Cup Window (June–July) Weather Risk Frequency (%)',
    fontweight='bold',
    fontsize=11,
)
ax2.set_ylabel('Percentage of Tournament Days (%)', fontweight='bold')
ax2.set_ylim(0, 70)
ax2.set_xticks(range(len(risk_df['metric'])))
ax2.set_xticklabels(
    risk_df['metric'], rotation=15, ha='right', fontweight='bold', fontsize=9
)

for bar, count in zip(bars, risk_df['count']):
  yval = bar.get_height()
  ax2.text(
      bar.get_x() + bar.get_width() / 2.0,
      yval + 1.2,
      f'{yval:.1f}%\n({count:,} days)',
      ha='center',
      va='bottom',
      fontweight='bold',
      fontsize=8.5,
  )

plt.tight_layout()
fig2_path = 'reports/figures/fig2_summer_risk_days.png'
plt.savefig(fig2_path, dpi=300)
plt.close()
print(f'Saved: {fig2_path}')

# =============================================================================
# FIGURE 3: Summer Heat & Humidity Matrix (Spectator Comfort & Safety)
# =============================================================================
fig3, ax3 = plt.subplots(figsize=(8, 5))
summer_clean = clean_df[clean_df['date'].dt.month.isin([6, 7])].dropna(
    subset=['temperature_max_c', 'relative_humidity_pct']
)

hb = ax3.hexbin(
    summer_clean['temperature_max_c'],
    summer_clean['relative_humidity_pct'],
    gridsize=25,
    cmap='YlOrRd',
    mincnt=1,
)
cb = fig3.colorbar(hb, ax=ax3)
cb.set_label('Observation Density', fontweight='bold')

ax3.axvline(
    30.0,
    color='red',
    linestyle='--',
    linewidth=2,
    label='Heat Risk Threshold (30°C)',
)
ax3.set_title(
    'Figure 3: Summer Heat & Humidity Matrix', fontweight='bold', fontsize=11
)
ax3.set_xlabel('Max Temperature (°C)', fontweight='bold')
ax3.set_ylabel('Relative Humidity (%)', fontweight='bold')
ax3.legend(loc='lower left')

plt.tight_layout()
fig3_path = 'reports/figures/fig3_heat_humidity_matrix.png'
plt.savefig(fig3_path, dpi=300)
plt.close()
print(f'Saved: {fig3_path}')

# =============================================================================
# FIGURE 4: FinalFlow Risk Level Classification (Operational Logic Integration)
# =============================================================================
fig4, ax4 = plt.subplots(figsize=(8, 5))
risk_counts = integration_df['weather_risk_level'].value_counts()
level_colors = {'Low': '#4daf4a', 'Medium': '#ff7f00', 'High': '#e41a1c'}
bar_colors = [level_colors.get(x, '#377eb8') for x in risk_counts.index]

bars4 = ax4.bar(
    risk_counts.index,
    risk_counts.values,
    color=bar_colors,
    edgecolor='black',
    alpha=0.85,
)
ax4.set_title(
    'Fig 4: FinalFlow Operational Risk Classification Distribution',
    fontweight='bold',
    fontsize=11,
)
ax4.set_xlabel('Assigned Weather Risk Level', fontweight='bold')
ax4.set_ylabel('Total Observation Days', fontweight='bold')

for bar in bars4:
  yval = bar.get_height()
  ax4.text(
      bar.get_x() + bar.get_width() / 2.0,
      yval + 500,
      f'{yval:,}\n({yval/len(integration_df)*100:.1f}%)',
      ha='center',
      va='bottom',
      fontweight='bold',
      fontsize=9,
  )

plt.tight_layout()
fig4_path = 'reports/figures/fig4_risk_levels_breakdown.png'
plt.savefig(fig4_path, dpi=300)
plt.close()
print(f'Saved: {fig4_path}')

# =============================================================================
# FIGURE 5: Monthly Climate Baseline
# =============================================================================
monthly_df = pd.read_csv('data/summaries/weather_monthly.csv')

# Set visual style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'

# Ensure output folder exists
os.makedirs('reports/figures', exist_ok=True)

fig, ax1 = plt.subplots(figsize=(8, 5))
months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
]

# Left axis: Avg Max Temperature (°C)
color_temp = '#d95f02'
ax1.set_xlabel('Month', fontweight='bold', fontsize=10)
ax1.set_ylabel(
    'Avg Max Temperature (°C)', color=color_temp, fontweight='bold', fontsize=10
)
line1 = ax1.plot(
    months,
    monthly_df['temp_max_avg'],
    color=color_temp,
    marker='o',
    linewidth=2.5,
    label='Avg Max Temp (°C)',
)
ax1.tick_params(axis='y', labelcolor=color_temp)

# Highlight June & July World Cup Window
ax1.axvspan(5, 6, color='gold', alpha=0.3, label='World Cup Window (Jun-Jul)')

# Right axis: Rainy Days Count
ax2 = ax1.twinx()
color_rain = '#2b5c8f'
ax2.set_ylabel(
    'Number of Rainy Days', color=color_rain, fontweight='bold', fontsize=10
)
line2 = ax2.plot(
    months,
    monthly_df['rainy_days'],
    color=color_rain,
    marker='s',
    linestyle='--',
    linewidth=2,
    label='Rainy Days Count',
)
ax2.tick_params(axis='y', labelcolor=color_rain)

# Combined legend
lines = line1 + line2
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper left')

ax1.set_title(
    'Figure 5: Monthly Climate Baseline (weather_monthly.csv)',
    fontweight='bold',
    fontsize=11,
)

plt.tight_layout()
fig5_path = "reports/figures/fig5_monthly_baseline.png"
plt.savefig(fig5_path, dpi=300)
plt.close()
print(f'Saved: {fig5_path}')


print(
    '\nAll 5 figures generated and saved successfully to reports/figures/!'
)