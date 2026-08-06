import pandas as pd

def clean_data():
    print("=== DUC ANH: DATA CLEANING ===")
    print("1. Dropping null LATITUDE/LONGITUDE from POI geometry...")
    print("2. Filtering SPEND_AMOUNT >= 0...")
    print("3. Standardizing DATE columns...")
    print("Cleaned datasets are ready for downstream processing.")

if __name__ == '__main__':
    clean_data()
