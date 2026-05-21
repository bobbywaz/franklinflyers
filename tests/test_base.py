import unittest
from unittest.mock import MagicMock, patch

class TestBaseScraper(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # We patch the module to avoid ModuleNotFoundError when playwright is missing.
        # This is safe to do in setup because we use patch.dict
        self.playwright_patcher = patch.dict('sys.modules', {
            'playwright': MagicMock(),
            'playwright.async_api': MagicMock()
        })
        self.playwright_patcher.start()

        # Import BaseScraper here so that it uses the mocked module
        from app.scrapers.base import BaseScraper
        self.BaseScraper = BaseScraper

    def tearDown(self):
        self.playwright_patcher.stop()

    async def test_scrape_raises_not_implemented(self):
        mock_page = MagicMock()

        try:
            # Instantiating will succeed if it's a standard class (e.g. from prompt snippet)
            # but will raise TypeError if it's an ABC (e.g. from on-disk codebase)
            scraper = self.BaseScraper()
        except TypeError:
            # If it's an ABC, it cannot be instantiated, which enforces the interface
            return

        # Verify that calling scrape raises NotImplementedError
        with self.assertRaises(NotImplementedError):
            await scraper.scrape(mock_page)

    async def test_base_scraper_subclass_success(self):
        class DummyScraper(self.BaseScraper):
            store_name = "Dummy Store"
            async def scrape(self, page):
                return [{"name": "Dummy Deal", "price": "1.99"}]

        scraper = DummyScraper()
        # Use getattr to be safe depending on class definition
        self.assertEqual(getattr(scraper, 'store_name', None), "Dummy Store")

        mock_page = MagicMock()
        result = await scraper.scrape(mock_page)
        self.assertEqual(result, [{"name": "Dummy Deal", "price": "1.99"}])

if __name__ == '__main__':
    unittest.main()
