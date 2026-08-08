from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api import resolve_source_url


@patch("api.urlparse")
@patch("api.Request")
@patch("api.urlopen")
def test_resolve_source_url_arxiv_abs(mock_urlopen, mock_request, mock_urlparse):
    mock_parsed = MagicMock()
    mock_parsed.scheme = "https"
    mock_parsed.netloc = "arxiv.org"
    mock_parsed.path = "/abs/1234.5678"
    mock_urlparse.return_value = mock_parsed

    mock_response = MagicMock()
    mock_response.headers.get.return_value = "application/pdf"
    mock_response.read.return_value = b"pdf content"
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = resolve_source_url("https://arxiv.org/abs/1234.5678")

    assert result[0] == b"pdf content"
    assert result[1] == "1234.5678.pdf"
    assert result[2] == "application/pdf"


@patch("api.urlparse")
def test_resolve_source_url_invalid_scheme(mock_urlparse):
    mock_parsed = MagicMock()
    mock_parsed.scheme = "ftp"
    mock_urlparse.return_value = mock_parsed

    with pytest.raises(HTTPException) as exc_info:
        resolve_source_url("ftp://example.com/paper.pdf")

    assert exc_info.value.status_code == 400
    assert "http or https" in exc_info.value.detail


@patch("api.urlparse")
def test_resolve_source_url_non_pdf(mock_urlparse):
    mock_parsed = MagicMock()
    mock_parsed.scheme = "https"
    mock_parsed.netloc = "example.com"
    mock_parsed.path = "/paper.txt"
    mock_urlparse.return_value = mock_parsed

    with pytest.raises(HTTPException) as exc_info:
        resolve_source_url("https://example.com/paper.txt")

    assert exc_info.value.status_code == 400
    assert "Only direct PDF URLs" in exc_info.value.detail
