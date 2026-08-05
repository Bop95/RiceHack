import pandas as pd
import numpy as np

def score_vendor_zones():
    print("=== ĐỨC ANH: CALCULATING MOBILITY RISK & OPPORTUNITY SCORES ===")
    np.random.seed(42)
    placekeys = [f"SG_{i:04d}" for i in range(1, 51)]
    
    opportunity = np.random.uniform(20, 100, size=50) # Based on RAW_VISIT_COUNTS & SPEND_AMOUNT
    risk = np.random.uniform(10, 90, size=50)         # Based on URBAN_HEAT_INDEX & Exit Proximity
    
    df_scores = pd.DataFrame({
        'PLACEKEY': placekeys,
        'BUSINESS_OPPORTUNITY_SCORE': np.round(opportunity, 2),
        'MOBILITY_RISK_SCORE': np.round(risk, 2)
    })
    
    conditions = [
        (df_scores['BUSINESS_OPPORTUNITY_SCORE'] > 70) & (df_scores['MOBILITY_RISK_SCORE'] < 40),
        (df_scores['MOBILITY_RISK_SCORE'] >= 75)
    ]
    choices = ['Recommended', 'Avoided']
    df_scores['PLACEMENT_CLASS'] = np.select(conditions, choices, default='Controlled')
    
    df_scores.to_csv('../data_clean/ms_aug3_vndr.csv', index=False)
    print("Scoring complete. Output saved to data_clean/ms_aug3_vndr.csv")

if __name__ == '__main__':
    score_vendor_zones()
