"""
Inspect the actual column names of each table in the Athena database.
"""
import pandas as pd
from pyathena import connect

conn = connect(
    region_name="us-east-1",
    s3_staging_dir="s3://titan-retail-datalake-srikrishna/athena-results/",
    schema_name="titan_retail_processed_db",
)

for table in ["sales", "products", "customers"]:
    print(f"\n{'='*50}")
    print(f"TABLE: {table}")
    print(f"{'='*50}")
    df = pd.read_sql(f"SELECT * FROM {table} LIMIT 3", conn)
    print(f"Columns: {list(df.columns)}")
    print(f"Dtypes:\n{df.dtypes}")
    print(f"\nSample data:")
    print(df.to_string())
