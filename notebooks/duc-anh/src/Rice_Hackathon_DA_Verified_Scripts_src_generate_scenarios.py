import pandas as pd
import numpy as np
import os

def score_scenarios():
    print("=== DUC ANH: GENERATING SYNTHETIC SCENARIOS ===")
    np.random.seed(42) # Guide strict requirement
    
    df_scenarios = pd.DataFrame({
        'zone_id': [f"ZONE_{i:03d}" for i in range(1, 31)],
        'business_opportunity_score': np.random.uniform(20, 100, 30),
        'mobility_risk_score': np.random.uniform(10, 90, 30)
    })
    
    conditions = [
        (df_scenarios['business_opportunity_score'] > 70) & (df_scenarios['mobility_risk_score'] < 40),
        (df_scenarios['mobility_risk_score'] >= 75)
    ]
    df_scenarios['placement_class'] = np.select(conditions, ['Recommended', 'Avoided'], default='Controlled')
    
    os.makedirs('../data_clean', exist_ok=True)
    df_scenarios.to_csv('../data_clean/vendor_zone_scenarios.csv', index=False)
    print("Output generated: ../data_clean/vendor_zone_scenarios.csv")

if __name__ == '__main__':
    score_scenarios()
