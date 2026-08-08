from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from storage import (
    build_paper_storage_key,
    download_file_from_storage,
    get_storage_client,
    upload_pdf_to_storage,
)


@patch("storage.settings")
@patch("storage.boto3")
def test_get_storage_client(mock_boto3, mock_settings):
    mock_settings.s3_bucket_name = "test-bucket"
    mock_settings.s3_access_key_id = "test-key"
    mock_settings.s3_secret_access_key = "test-secret"
    mock_settings.s3_region = "us-east-1"
    mock_settings.s3_endpoint_url = None

    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    client = get_storage_client()

    assert client is mock_client
    mock_boto3.client.assert_called_once()
    call_kwargs = mock_boto3.client.call_args.kwargs
    assert call_kwargs["service_name"] == "s3"
    assert call_kwargs["aws_access_key_id"] == "test-key"
    assert "endpoint_url" not in call_kwargs


@patch("storage.settings")
@patch("storage.boto3")
def test_get_storage_client_with_endpoint(mock_boto3, mock_settings):
    mock_settings.s3_bucket_name = "test-bucket"
    mock_settings.s3_access_key_id = "test-key"
    mock_settings.s3_secret_access_key = "test-secret"
    mock_settings.s3_region = "us-east-1"
    mock_settings.s3_endpoint_url = "http://localhost:9000"

    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    client = get_storage_client()

    assert client is mock_client
    call_kwargs = mock_boto3.client.call_args.kwargs
    assert call_kwargs["endpoint_url"] == "http://localhost:9000"


@patch("storage.settings")
def test_get_storage_client_missing_bucket(mock_settings):
    mock_settings.s3_bucket_name = None
    mock_settings.s3_access_key_id = "test-key"
    mock_settings.s3_secret_access_key = "test-secret"

    with pytest.raises(RuntimeError, match="S3_BUCKET_NAME"):
        get_storage_client()


@patch("storage.settings")
def test_get_storage_client_missing_credentials(mock_settings):
    mock_settings.s3_bucket_name = "test-bucket"
    mock_settings.s3_access_key_id = None
    mock_settings.s3_secret_access_key = None

    with pytest.raises(RuntimeError, match="S3 credentials"):
        get_storage_client()


def test_build_paper_storage_key():
    key = build_paper_storage_key("paper.pdf")
    assert key.startswith("papers/")
    assert key.endswith("/paper.pdf")
    assert len(key.split("/")) == 3


def test_build_paper_storage_key_sanitizes_path():
    key = build_paper_storage_key("path/to/paper.pdf")
    assert "_" in key.replace("papers/", "").split("/")[1]


@patch("storage.get_storage_client")
def test_upload_pdf_to_storage(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    result = upload_pdf_to_storage(b"pdf content", "test.pdf", "application/pdf")

    assert result.startswith("papers/")
    mock_client.put_object.assert_called_once()
    call_kwargs = mock_client.put_object.call_args.kwargs
    assert call_kwargs["Bucket"] is not None
    assert call_kwargs["Body"] == b"pdf content"
    assert call_kwargs["ContentType"] == "application/pdf"


@patch("storage.get_storage_client")
def test_download_file_from_storage(mock_get_client, tmp_path):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    destination = tmp_path / "downloads" / "paper.pdf"
    download_file_from_storage("papers/abc/test.pdf", destination)

    assert destination.parent.exists()
    mock_client.download_file.assert_called_once()
    call_kwargs = mock_client.download_file.call_args.kwargs
    assert call_kwargs["Key"] == "papers/abc/test.pdf"
    assert call_kwargs["Filename"] == str(destination)
