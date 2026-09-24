import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from app.gemini_analyzer import GeminiAnalyzer

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

    # Mock the Gemini client
    mock_client = MagicMock()
    analyzer.client = mock_client

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
                "score": 8,
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
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    deals = [
        {"store_name": "Test Store", "name": "Apples", "price": "1.00", "description": "Fresh"}
    ]

    result = await analyzer.analyze_deals(deals)

    # Verify the model was called
    mock_client.aio.models.generate_content.assert_called_once()

    # Verify category mapping
    assert len(result["scored_deals"]) == 2
    assert result["scored_deals"][0]["category"] == "Produce"
    assert result["scored_deals"][1]["category"] == "Pantry" # default for unknown
    assert result["best_store"]["score"] == 9

@pytest.mark.asyncio
async def test_analyze_deals_api_error():
    analyzer = GeminiAnalyzer()
    analyzer.mock_mode = False

    # Mock the Gemini client to raise an exception
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("API error"))
    analyzer.client = mock_client

    # Mock _mock_analyze to verify fallback
    with patch.object(analyzer, '_mock_analyze', return_value={"mocked_fallback": True}) as mock_method:
        deals = [{"store_name": "Test Store", "name": "Apple", "price": "1.00"}]
        result = await analyzer.analyze_deals(deals)

        # Verify it caught the error and used fallback
        mock_method.assert_called_once_with(deals)
        assert result == {"mocked_fallback": True}

@pytest.mark.asyncio
async def test_analyze_deals_markdown_parsing():
    analyzer = GeminiAnalyzer()
    analyzer.mock_mode = False

    # Mock the Gemini client
    mock_client = MagicMock()
    analyzer.client = mock_client

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
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    deals = [{"store_name": "Test Store", "name": "Apples", "price": "1.00", "description": "Fresh"}]

    result = await analyzer.analyze_deals(deals)

    # Verify the markdown was stripped and JSON parsed correctly
    assert result["scored_deals"][0]["item_name"] == "Apples"
    assert result["best_store"]["score"] == 10


def test_rule_based_analyze_curates_top_deals_and_filters_filler():
    """Verify rule-based analyzer rejects filler and shows all really good deals without artificial hard cap."""
    analyzer = GeminiAnalyzer()

    # Generate 55 deals: 15 high-value BOGOs (score 9-10), 10 good deals (score 8), 30 filler (score 6)
    deals = []
    # 15 BOGOs
    for i in range(15):
        deals.append({
            "store_name": "Store A",
            "name": f"BOGO Item {i}",
            "price": "BUY 1 GET 1 FREE",
            "description": "Family Pack",
        })
    # 10 good deals
    for i in range(10):
        deals.append({
            "store_name": "Store B",
            "name": f"Chicken Breast {i}",
            "price": "$1.99/lb",
            "description": "Fresh",
        })
    # 30 filler items
    for i in range(30):
        deals.append({
            "store_name": "Store A",
            "name": f"Filler Soda {i}",
            "price": "$4.99",
            "description": "Standard",
        })

    result = analyzer._rule_based_analyze(deals)
    scored = result["scored_deals"]

    # All 25 really good deals must be included (no artificial hard number cap)
    assert len(scored) == 25

    # Every deal shown must be a really good deal (score >= 8), zero filler
    for d in scored:
        assert d["score"] >= 8
        assert "Filler Soda" not in d["item_name"]

    # Explicit cap is still respected if requested
    capped = analyzer._curate_top_deals(result["scored_deals"], max_deals=10)
    assert len(capped) == 10

@pytest.mark.asyncio
async def test_generate_recipe_empty_list():
    analyzer = GeminiAnalyzer()
    result = await analyzer.generate_recipe([])
    assert result is None

@pytest.mark.asyncio
async def test_generate_recipe_mock_mode():
    analyzer = GeminiAnalyzer()
    analyzer.mock_mode = True

    # Mock the _generate_rule_based_recipe method
    with patch.object(analyzer, '_generate_rule_based_recipe', return_value={"recipe_name": "Mock Recipe"}) as mock_method:
        deals = [{"item_name": "Chicken", "sale_price": "1.99", "category": "Meat"}]
        result = await analyzer.generate_recipe(deals)

        mock_method.assert_called_once_with(deals)
        assert result == {"recipe_name": "Mock Recipe"}

@pytest.mark.asyncio
async def test_generate_recipe_normal_mode():
    analyzer = GeminiAnalyzer()
    analyzer.mock_mode = False

    # Mock the Gemini client
    mock_client = MagicMock()
    analyzer.client = mock_client

    # Setup the mock response
    mock_response = MagicMock()
    mock_response_json = {
        "recipe_name": "Test Recipe",
        "ingredients_from_deals": ["Chicken ($1.99)"],
        "other_ingredients": ["Rice"],
        "instructions": "Cook it.",
        "cost_per_plate": "$2.00 per plate"
    }
    mock_response.text = json.dumps(mock_response_json)
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    deals = [
        {"item_name": "Chicken", "sale_price": "1.99", "category": "Meat"}
    ]

    result = await analyzer.generate_recipe(deals)

    # Verify the model was called
    mock_client.aio.models.generate_content.assert_called_once()
    assert result == mock_response_json

@pytest.mark.asyncio
async def test_generate_recipe_api_error():
    analyzer = GeminiAnalyzer()
    analyzer.mock_mode = False

    # Mock the Gemini client to raise an exception
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("API error"))
    analyzer.client = mock_client

    # Mock fallback method
    with patch.object(analyzer, '_generate_rule_based_recipe', return_value={"recipe_name": "Fallback Recipe"}) as mock_method:
        deals = [{"item_name": "Chicken", "sale_price": "1.99", "category": "Meat"}]
        result = await analyzer.generate_recipe(deals)

        # Verify it caught the error and used fallback
        mock_method.assert_called_once_with(deals)
        assert result == {"recipe_name": "Fallback Recipe"}

@pytest.mark.asyncio
async def test_generate_recipe_markdown_parsing():
    analyzer = GeminiAnalyzer()
    analyzer.mock_mode = False

    # Mock the Gemini client
    mock_client = MagicMock()
    analyzer.client = mock_client

    # Setup the mock response with markdown formatting
    mock_response = MagicMock()
    json_data = {
        "recipe_name": "Markdown Recipe",
        "ingredients_from_deals": ["Chicken ($1.99)"],
        "other_ingredients": ["Rice"],
        "instructions": "Cook it.",
        "cost_per_plate": "$2.00 per plate"
    }
    mock_response.text = f"```json\n{json.dumps(json_data)}\n```"
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    deals = [{"item_name": "Chicken", "sale_price": "1.99", "category": "Meat"}]

    result = await analyzer.generate_recipe(deals)

    # Verify the markdown was stripped and JSON parsed correctly
    assert result["recipe_name"] == "Markdown Recipe"
