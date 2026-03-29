import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from app.gemini_analyzer import GeminiAnalyzer

# Simple test to verify pytest works
def test_pytest():
    assert True

@pytest.mark.asyncio
async def test_analyze_deals_empty_list():
    analyzer = GeminiAnalyzer()
    result = await analyzer.analyze_deals([])
    assert result == {"scored_deals": [], "best_store": None}

@pytest.mark.asyncio
async def test_analyze_deals_mock_mode():
    analyzer = GeminiAnalyzer()
    analyzer.mock_mode = True

    # Mock the _mock_analyze method to verify it's called
    with patch.object(analyzer, '_mock_analyze', return_value={"mocked": True}) as mock_method:
        deals = [{"store_name": "Test", "name": "Apple", "price": "1.00"}]
        result = await analyzer.analyze_deals(deals)

        mock_method.assert_called_once_with(deals)
        assert result == {"mocked": True}

@pytest.mark.asyncio
async def test_analyze_deals_normal_mode():
    analyzer = GeminiAnalyzer()
    analyzer.mock_mode = False

    # Mock the Gemini GenerativeModel
    mock_model = MagicMock()
    analyzer.model = mock_model

    # Setup the mock response
    mock_response = MagicMock()
    mock_response_json = {
        "scored_deals": [
            {
                "store_name": "Test Store",
                "item_name": "Apples",
                "sale_price": "1.00",
                "category": "produce", # lowercase to test mapping
                "score": 8,
                "explanation": "Good price"
            },
            {
                "store_name": "Test Store",
                "item_name": "Weird Thing",
                "sale_price": "5.00",
                "category": "unknown_category", # test default mapping
                "score": 5,
                "explanation": "Okay"
            }
        ],
        "best_store": {
            "store_name": "Test Store",
            "summary": "Good store",
            "strengths": "Apples",
            "weaknesses": "None",
            "score": 9
        }
    }
    mock_response.text = json.dumps(mock_response_json)
    mock_model.generate_content.return_value = mock_response

    deals = [
        {"store_name": "Test Store", "name": "Apples", "price": "1.00", "description": "Fresh"}
    ]

    result = await analyzer.analyze_deals(deals)

    # Verify the model was called
    mock_model.generate_content.assert_called_once()

    # Verify category mapping
    assert len(result["scored_deals"]) == 2
    assert result["scored_deals"][0]["category"] == "Produce"
    assert result["scored_deals"][1]["category"] == "Pantry" # default for unknown
    assert result["best_store"]["score"] == 9

@pytest.mark.asyncio
async def test_analyze_deals_api_error():
    analyzer = GeminiAnalyzer()
    analyzer.mock_mode = False

    # Mock the Gemini GenerativeModel to raise an exception
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("API error")
    analyzer.model = mock_model

    # Mock _mock_analyze to verify fallback
    with patch.object(analyzer, '_mock_analyze', return_value={"mocked_fallback": True}) as mock_method:
        deals = [{"store_name": "Test", "name": "Apple", "price": "1.00"}]
        result = await analyzer.analyze_deals(deals)

        # Verify it caught the error and used fallback
        mock_method.assert_called_once_with(deals)
        assert result == {"mocked_fallback": True}

@pytest.mark.asyncio
async def test_analyze_deals_markdown_parsing():
    analyzer = GeminiAnalyzer()
    analyzer.mock_mode = False

    # Mock the Gemini GenerativeModel
    mock_model = MagicMock()
    analyzer.model = mock_model

    # Setup the mock response with markdown formatting
    mock_response = MagicMock()
    json_data = {
        "scored_deals": [
            {
                "store_name": "Test Store",
                "item_name": "Apples",
                "sale_price": "1.00",
                "category": "Produce",
                "score": 8,
                "explanation": "Good price"
            }
        ],
        "best_store": {"score": 10}
    }
    mock_response.text = f"```json\n{json.dumps(json_data)}\n```"
    mock_model.generate_content.return_value = mock_response

    deals = [{"store_name": "Test Store", "name": "Apples", "price": "1.00", "description": "Fresh"}]

    result = await analyzer.analyze_deals(deals)

    # Verify the markdown was stripped and JSON parsed correctly
    assert result["scored_deals"][0]["item_name"] == "Apples"
    assert result["best_store"]["score"] == 10
