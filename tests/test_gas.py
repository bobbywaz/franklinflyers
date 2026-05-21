import pytest
from app.scrapers.gas import GasScraper
import httpx
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_gas_scraper_httpx_timeout():
    scraper = GasScraper()
    with patch('httpx.AsyncClient.post') as mock_post:
        # Mock the response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'ok',
            'solution': {'cookies': 'test_cookies', 'userAgent': 'test_ua'}
        }
        mock_post.return_value = mock_response

        cookies, ua = await scraper._get_flaresolverr_cookies('http://test.com')

        assert cookies == 'test_cookies'
        assert ua == 'test_ua'
        mock_post.assert_called_once()
