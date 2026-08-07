import pandas as pd
import os

def export_integration_schema():
    print("=== DUC ANH: EXPORT API & POWER BI INTEGRATION ===")
    
    df_final = pd.DataFrame({
        'zone_id': ['ZONE_001', 'ZONE_002'],
        'business_opportunity_score': [85.5, 90.0],
        'mobility_risk_score': [22.1, 88.5],
        'placement_class': ['Recommended', 'Avoided'],
        'reason': ['High foot traffic, wide corridor', 'Causes egress chokepoint'],
        'data_confidence': ['High', 'High']
    })
    
    os.makedirs('../data_clean', exist_ok=True)
    df_final.to_csv('../data_clean/finalflow_business_integration.csv', index=False)
    print("Output generated: ../data_clean/finalflow_business_integration.csv")

if __name__ == '__main__':
    export_integration_schema()
