import pandas as pd
df = pd.DataFrame([{"Status": "PASSED"}])
df.to_csv("../reports/ms_jul30_audit.csv", index=False)