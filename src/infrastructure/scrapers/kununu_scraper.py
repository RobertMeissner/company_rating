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
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KununuScraper:
    """

    Implements CompanyScraperPort

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
            logger.debug("Browser started successfully")

        except Exception as e:
            logger.debug(f"Failed to start browser: {e}")
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

    async def update(self, company_name: str) -> Company:
        scraped_company = await self._scrape_company(company_name)
        return Company(
            name=scraped_company.company_name,
            location=scraped_company.company_location or "",
            # Overall ratings
            kununu_rating=scraped_company.rating,
            kununu_review_count=scraped_company.review_count,
            # Sub-ratings
            kununu_career_rating=scraped_company.career_rating,
            kununu_work_life_balance_rating=scraped_company.work_life_balance_rating,
            kununu_salary_benefits_rating=scraped_company.salary_benefits_rating,
            kununu_management_rating=scraped_company.management_rating,
            kununu_culture_rating=scraped_company.culture_rating,
            # Recommendation
            kununu_recommend_percent=scraped_company.recommend_percent,
            # Company details
            industry=scraped_company.industry,
            company_size=scraped_company.company_size,
            # URLs
            url=scraped_company.profile_url or "",
            website=scraped_company.company_website or "",
        )

    async def _scrape_rating(self) -> float:
        """Extract company rating from the page."""
        try:
            rating = 0
            rating_text = await self.page.inner_text("#ph-kununu-score .h2")
            if rating_text:
                rating = float(rating_text.strip().replace(",", "."))
            return rating
        except Exception as e:
            logger.debug(f"Could not extract rating: {e}")
            return 0

    async def _review_count(self) -> int:
        """Extract review count from the page."""
        try:
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
        except Exception as e:
            logger.debug(f"Could not extract review count: {e}")
            return 0

    async def _company_website(self) -> str:
        """Extract company website URL from the page"""
        try:
            # Look for the link with id="company-link-website"
            website_element = await self.page.query_selector("#company-link-website")
            if website_element:
                href = await website_element.get_attribute("href")
                return href if href else ""
            return ""
        except Exception as e:
            logger.debug(f"Could not extract company website: {e}")
            return ""

    async def _scrape_sub_ratings(self) -> dict[str, float]:
        """
        Extract sub-ratings from Kununu (career, work-life balance, salary, management, culture).
        Returns dict with rating category names as keys.
        """
        sub_ratings = {}
        try:
            # Kununu typically shows sub-ratings with specific selectors or data attributes
            # Common patterns: .rating-item, .category-rating, data-rating-type, etc.

            # Try multiple selector patterns
            selectors = [
                # Modern data attribute approach
                "[data-rating-category]",
                # Class-based approach
                ".rating-category-item",
                ".sub-rating-item",
                # Nested structure
                ".rating-categories .rating-item",
            ]

            for selector in selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    for element in elements:
                        try:
                            # Extract category name
                            category = await element.get_attribute(
                                "data-rating-category"
                            )
                            if not category:
                                # Try to get from text content
                                category_elem = await element.query_selector(
                                    ".category-name, .rating-label"
                                )
                                if category_elem:
                                    category = await category_elem.inner_text()

                            # Extract rating value
                            rating_elem = await element.query_selector(
                                ".rating-value, [data-rating-value], .score"
                            )
                            if rating_elem:
                                rating_text = await rating_elem.inner_text()
                                rating = float(rating_text.strip().replace(",", "."))

                                if category:
                                    sub_ratings[category.lower().strip()] = rating
                        except Exception as e:
                            logger.debug(
                                f"Could not extract sub-rating from element: {e}"
                            )
                            continue
                    break  # If we found elements, don't try other selectors

        except Exception as e:
            logger.debug(f"Could not extract sub-ratings: {e}")

        return sub_ratings

    async def _scrape_recommend_percent(self) -> float:
        """Extract recommendation percentage (% who would recommend)."""
        try:
            # Common selectors for recommendation metrics
            selectors = [
                '[data-testid="recommendation-rate"]',
                ".recommendation-rate",
                ".would-recommend",
                "text=/\\d+%.*empfehlen/i",  # German: "XX% empfehlen"
            ]

            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        # Extract percentage number
                        import re

                        match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", text)
                        if match:
                            return float(match.group(1).replace(",", "."))
                except Exception:
                    continue

            return 0
        except Exception as e:
            logger.debug(f"Could not extract recommendation percentage: {e}")
            return 0

    async def _scrape_company_size(self) -> str:
        """Extract company size (e.g., '1001-5000 employees')."""
        try:
            selectors = [
                '[data-testid="company-size"]',
                ".company-size",
                ".company-employees",
                "text=/\\d+[\\s-]+\\d+.*Mitarbeiter/i",  # German
                "text=/\\d+[\\s-]+\\d+.*employees/i",
            ]

            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        return text.strip()
                except Exception:
                    continue

            return ""
        except Exception as e:
            logger.debug(f"Could not extract company size: {e}")
            return ""

    async def _scrape_industry(self) -> str:
        """Extract company industry/sector."""
        try:
            selectors = [
                '[data-testid="company-industry"]',
                ".company-industry",
                ".company-sector",
                ".industry-label",
            ]

            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        return text.strip()
                except Exception:
                    continue

            return ""
        except Exception as e:
            logger.debug(f"Could not extract industry: {e}")
            return ""

    async def _random_delay(self):
        await asyncio.sleep(random.uniform(*self.random_human_delay_range))

    async def _scrape_company(self, company_name: str) -> ScraperModel:
        start_time = time.time()
        result = ScraperModel(company_name=company_name, scraper=SCRAPERS.KUNUNU)

        logger.info(f"Starting scrape for company: {company_name}")

        url = f"{self.BASE_URL}/de/{company_name}"

        try:
            response = await self.page.goto(
                url, wait_until="domcontentloaded", timeout=10_000
            )

            if response.status == 200:
                # Extract basic ratings
                result.rating = await self._scrape_rating()
                result.review_count = await self._review_count()
                result.company_website = await self._company_website()

                # Extract sub-ratings
                sub_ratings = await self._scrape_sub_ratings()
                # Map sub-ratings to result fields (adjust keys based on actual Kununu labels)
                result.career_rating = sub_ratings.get(
                    "karriere", sub_ratings.get("career")
                )
                result.work_life_balance_rating = sub_ratings.get(
                    "work-life-balance", sub_ratings.get("work life balance")
                )
                result.salary_benefits_rating = sub_ratings.get(
                    "gehalt", sub_ratings.get("salary", sub_ratings.get("vergütung"))
                )
                result.management_rating = sub_ratings.get(
                    "führung",
                    sub_ratings.get(
                        "management", sub_ratings.get("vorgesetztenverhalten")
                    ),
                )
                result.culture_rating = sub_ratings.get(
                    "kultur",
                    sub_ratings.get("culture", sub_ratings.get("arbeitsatmosphäre")),
                )

                # Extract additional company info
                result.recommend_percent = await self._scrape_recommend_percent()
                result.company_size = await self._scrape_company_size()
                result.industry = await self._scrape_industry()

                result.success = True
                logger.info(
                    f"Successfully scraped {company_name}: "
                    f"rating={result.rating}, reviews={result.review_count}, "
                    f"recommend={result.recommend_percent}%"
                )
            elif response.status == 404:
                logger.debug(f"Company page not found (404): {company_name}")
                result.success = False
            else:
                logger.warning(
                    f"Unexpected status {response.status} for company: {company_name}"
                )
                result.success = False

        except Exception as e:
            logger.error(f"Error scraping company {company_name}: {e}")
            result.success = False
            result.error_message = str(e)

        result.scrape_duration = time.time() - start_time

        await self._random_delay()
        return result
