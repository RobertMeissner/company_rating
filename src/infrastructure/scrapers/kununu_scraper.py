import asyncio
import logging
import random
import time
from typing import Optional

from playwright.async_api import Browser, Page, async_playwright

from src.domain.value_objects.company import Company
from src.models.scraper_model import SCRAPERS, ScraperModel

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KununuScraper:
    """

    Implements CompanyScraper

    """

    BASE_URL = "https://www.kununu.com"
    SEARCH_URL = f"{BASE_URL}/search"
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    RATING_SELECTORS = [
        # Modern data attributes (most reliable)
        '[data-testid*="rating"] [data-testid*="score"]',
        '[data-testid*="overall-rating"]',
        '[data-testid="company-rating"]',
        # Class-based selectors
        ".rating-score .score-value",
        ".overall-rating .rating-value",
        ".company-rating-score",
        ".rating-display .rating-number",
        # Semantic selectors
        '.rating-container [class*="score"]',
        ".rating-wrapper .rating-value",
        # Text-based fallback (find numbers that look like ratings)
        "text=/^[0-5]\\.[0-9]$/",
        "text=/^[0-5],[0-9]$/",  # German decimal notation
    ]

    def __init__(
        self,
    ):
        self.headless = True
        self.random_human_delay_range = (1, 5)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        await self.start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_browser()

    async def start_browser(self):
        """Initialize browser with anti-detection measures"""
        try:
            self.playwright = await async_playwright().start()

            # Launch browser with stealth options
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-extensions",
                ],
            )

            # Create context with realistic settings
            context = await self.browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent=random.choice(self.USER_AGENTS),
                locale="de-DE",
                timezone_id="Europe/Berlin",
            )

            # Add stealth scripts
            await context.add_init_script(
                """
                // Remove webdriver property
                delete Object.getPrototypeOf(navigator).webdriver;

                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['de-DE', 'de', 'en-US', 'en'],
                });
            """
            )

            self.page = await context.new_page()
            logger.info("Browser started successfully")

        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise

    async def close_browser(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, "playwright"):
                await self.playwright.stop()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

    async def get(self, company_name: str) -> Company:
        raise NotImplementedError
        return Company(name=company_name)

    async def update(self, company_name: str) -> Company:
        scraped_company = await self._scrape_company(company_name)
        return Company(
            name=scraped_company.company_name,
            location=scraped_company.company_location,
            kununu_rating=scraped_company.rating,
            url=scraped_company.profile_url,
            kununu_review_count=scraped_company.review_count,
        )

    async def _scrape_rating(self) -> float:
        rating = 0
        rating_text = await self.page.inner_text("#ph-kununu-score .h2")
        if rating_text:
            rating = float(rating_text.strip().replace(",", "."))
        return rating

    async def _review_count(self) -> int:
        count = 0
        count_text = await self.page.inner_text("#ph-kununu-score .helper-regular")
        if count_text:
            count = int(
                count_text.strip()
                .replace(".", "")
                .replace("Bewertungen", "")
                .replace("Eine Bewertung", "1")
            )
        return count

    async def _random_delay(self):
        await asyncio.sleep(random.uniform(*self.random_human_delay_range))

    async def _scrape_company(self, company_name: str) -> ScraperModel:
        start_time = time.time()
        result = ScraperModel(company_name=company_name, scraper=SCRAPERS.KUNUNU)

        logger.info(f"Starting scrape for company: {company_name}")

        url = f"{self.BASE_URL}/de/{company_name}"

        response = await self.page.goto(
            url, wait_until="domcontentloaded", timeout=10_000
        )

        if response.status == 200:
            result.rating = await self._scrape_rating()
            result.review_count = await self._review_count()
            result.success = True

        result.scrape_duration = time.time() - start_time

        await self._random_delay()
        return result
