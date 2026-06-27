import os
from uuid import uuid4

import boto3
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()

STORAGE_PROVIDER = os.getenv("STORAGE_PROVIDER", "minio")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

def get_storage_client():
    if not S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME is not set")
    
    if not S3_ACCESS_KEY_ID or not S3_SECRET_ACCESS_KEY:
        raise RuntimeError("S3 credentials not set")

    client_kwargs = {
        "service_name": "s3",
        "aws_access_key_id": S3_ACCESS_KEY_ID,
        "aws_secret_access_key": S3_SECRET_ACCESS_KEY,
        "region_name": S3_REGION,
        "config": Config(signature_version="s3v4")
    }

    if S3_ENDPOINT_URL:
        client_kwargs["endpoint_url"] = S3_ENDPOINT_URL

    return boto3.client(**client_kwargs)

def build_paper_storage_key(filename: str) -> str:
    unique_id = uuid4().hex
    safe_filename = filename.replace("/","_").replace("\\", "_")
    return f"papers/{unique_id}/{safe_filename}"


def upload_pdf_to_storage(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> str:
    storage_key = build_paper_storage_key(filename)
    client = get_storage_client()

    client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=storage_key,
        Body=file_bytes,
        ContentType=content_type,
    )

    return storage_key