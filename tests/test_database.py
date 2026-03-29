import pytest
from unittest.mock import patch, MagicMock
from app.database import get_db

def test_get_db_yields_session_and_closes():
    """Test that get_db yields a database session and closes it afterwards."""
    # Create a mock session object
    mock_session = MagicMock()

    # Patch SessionLocal to return our mock session
    with patch("app.database.SessionLocal", return_value=mock_session):
        # Create the generator
        db_generator = get_db()

        # Get the first yielded value
        yielded_db = next(db_generator)

        # Verify it yielded our mock session
        assert yielded_db is mock_session

        # Verify close has not been called yet
        mock_session.close.assert_not_called()

        # Exhaust the generator to trigger the finally block
        with pytest.raises(StopIteration):
            next(db_generator)

        # Verify that close was called on the session
        mock_session.close.assert_called_once()
