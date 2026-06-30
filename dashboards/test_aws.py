"""
AWS S3 Connection Sanity Check
Verifies that local credentials can reach the Titan Retail Data Lake.
"""
import boto3

try:
    s3 = boto3.client("s3")
    # List the contents of your target bucket
    response = s3.list_objects_v2(
        Bucket="titan-retail-datalake-srikrishna",
        Prefix="processed/",
    )

    print("✅ AWS Connection Successful!")
    print("Found files in processed zone:")
    for content in response.get("Contents", []):
        print(f"  - {content['Key']}")

except Exception as e:
    print("❌ Connection Failed. Check your credentials file or region config.")
    print(e)
