import pytest
import pytest_asyncio
import asyncio
from unittest.mock import MagicMock, patch

from app.gemini_analyzer import GeminiAnalyzer

@pytest.fixture
def mock_genai():
    with patch("app.gemini_analyzer.genai") as mock_genai:
        yield mock_genai

@pytest.fixture
def sample_deals():
    return [
        {
            "store_name": "Test Store",
            "name": "Test Item",
            "price": "1.99",
            "description": "A test item"
        }
    ]

@pytest.mark.asyncio
async def test_gemini_analyzer_api_error_fallback(mock_genai, sample_deals):
    # Setup the environment so it doesn't default to mock mode
    with patch("os.getenv", return_value="dummy_api_key"):
        # Initialize GeminiAnalyzer
        analyzer = GeminiAnalyzer()

        # Ensure mock mode is False, meaning it will attempt API call
        assert analyzer.mock_mode is False

        # Mock generate_content to raise an Exception (simulating API failure)
        analyzer.model = MagicMock()
        analyzer.model.generate_content.side_effect = Exception("API Error")

        # Mock _mock_analyze to track if it's called and to return a known value
        expected_mock_result = {"scored_deals": ["mocked"], "best_store": "mocked"}

        # We need to spy on or mock _mock_analyze. The easiest way is to mock it on the instance
        with patch.object(analyzer, "_mock_analyze", return_value=expected_mock_result) as mock_analyze:
            # Call analyze_deals
            result = await analyzer.analyze_deals(sample_deals)

            # Assert _mock_analyze was called
            mock_analyze.assert_called_once_with(sample_deals)

            # Assert the result is exactly what _mock_analyze returned
            assert result == expected_mock_result
