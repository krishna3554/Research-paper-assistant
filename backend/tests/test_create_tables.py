from unittest.mock import MagicMock, patch

from create_tables import main


@patch("create_tables.engine")
@patch("create_tables.Base")
def test_main(mock_base, mock_engine, capsys):
    mock_metadata = MagicMock()
    mock_base.metadata = mock_metadata

    main()

    mock_metadata.create_all.assert_called_once_with(bind=mock_engine)
    captured = capsys.readouterr()
    assert "Tables created successfully" in captured.out
