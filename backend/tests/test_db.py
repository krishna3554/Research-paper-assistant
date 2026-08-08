from unittest.mock import MagicMock, patch

from db import get_db


@patch("db.SessionLocal")
def test_get_db_yields_session(mock_session_local):
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    gen = get_db()
    db = next(gen)

    assert db is mock_db
    mock_session_local.assert_called_once()


@patch("db.SessionLocal")
def test_get_db_closes_session(mock_session_local):
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    gen = get_db()
    next(gen)

    # Exhaust the generator to trigger finally block
    try:
        next(gen)
    except StopIteration:
        pass

    mock_db.close.assert_called_once()
