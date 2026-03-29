import pytest
from unittest.mock import MagicMock
import sys

# Mock google.generativeai before importing GeminiAnalyzer
mock_genai = MagicMock()
sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = mock_genai

from app.gemini_analyzer import GeminiAnalyzer

@pytest.fixture
def analyzer():
    return GeminiAnalyzer()

def test_mock_analyze_structure(analyzer):
    deals = [{"name": "Apple", "price": "$1.00", "store_name": "Store A"}]
    result = analyzer._mock_analyze(deals)
    assert "scored_deals" in result
    assert "best_store" in result

def test_mock_analyze_deal_fields(analyzer):
    deals = [{"name": "Apple", "price": "$1.00", "store_name": "Store A"}]
    result = analyzer._mock_analyze(deals)
    deal = result["scored_deals"][0]
    expected_keys = {"store_name", "item_name", "sale_price", "category", "score", "explanation"}
    assert set(deal.keys()) == expected_keys

def test_mock_analyze_sampling_limit(analyzer):
    deals = [{"name": f"Item {i}", "price": "$1.00", "store_name": "Store A"} for i in range(25)]
    result = analyzer._mock_analyze(deals)
    assert len(result["scored_deals"]) == 20

def test_mock_analyze_empty_input(analyzer):
    deals = []
    result = analyzer._mock_analyze(deals)
    assert result["scored_deals"] == []
    assert result["best_store"]["store_name"] == "Unknown"

@pytest.mark.parametrize("name, expected_category", [
    ("apple", "Produce"),
    ("beef", "Meat and Seafood"),
    ("milk", "Dairy"),
    ("cola", "Beverages"),
    ("cereal", "Pantry"),
    ("ham", "Deli"),
    ("can", "Canned Goods"),
    ("pizza", "Frozen"),
    ("soap", "Household"),
    ("random_item", "Pantry")
])
def test_mock_analyze_category_mapping(analyzer, name, expected_category):
    deals = [{"name": name, "price": "$1.00", "store_name": "Store A"}]
    result = analyzer._mock_analyze(deals)
    assert result["scored_deals"][0]["category"] == expected_category

def test_mock_analyze_best_store_fields(analyzer):
    deals = [{"name": "Apple", "price": "$1.00", "store_name": "Store A"}]
    result = analyzer._mock_analyze(deals)
    best_store = result["best_store"]
    expected_keys = {"store_name", "summary", "strengths", "weaknesses", "score"}
    assert set(best_store.keys()) == expected_keys
