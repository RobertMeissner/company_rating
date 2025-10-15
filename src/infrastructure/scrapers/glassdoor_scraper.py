import asyncio
import logging
import random
import re
import time
from typing import Optional

from playwright.async_api import Browser, Page, async_playwright

from src.domain.value_objects.company import Company
from src.models.scraper_model import SCRAPERS, ScraperModel

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GlassdoorScraper:
    """
    Fixme: WIP Implementation
    Glassdoor company profile scraper using Playwright.

    Extracts company ratings, reviews, and profile information from Glassdoor.
    Similar to Kununu scraper but for Glassdoor platform.
    """

    BASE_URL = "https://www.glassdoor.com"
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self):
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
                locale="en-US",
                timezone_id="America/New_York",
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
                    get: () => ['en-US', 'en'],
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

    async def update(self, company_name: str) -> Company:
        """
        Scrape Glassdoor and return Company object.
        """
        scraped_company = await self._scrape_company(company_name)
        return Company(
            name=scraped_company.company_name,
            location=scraped_company.company_location or "",
            glassdoor_rating=scraped_company.rating,
            glassdoor_review_count=scraped_company.review_count,
            glassdoor_url=scraped_company.profile_url or "",
            website=scraped_company.company_website or "",
            industry=scraped_company.industry,
            company_size=scraped_company.company_size,
        )

    async def _scrape_rating(self) -> float:
        """Extract overall company rating from the page."""
        rating = 0.0
        try:
            # Glassdoor rating selectors
            selectors = [
                '[data-test="rating"]',
                ".rating-headline-average",
                '[data-test="employer-rating"]',
                ".css-1m5m32b",  # Common rating class
                "text=/^[0-5]\\.[0-9]$/",
            ]

            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        # Extract numeric rating
                        match = re.search(r"([0-5]\.[0-9])", text)
                        if match:
                            return float(match.group(1))
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Could not extract rating: {e}")
        return rating

    async def _scrape_review_count(self) -> int:
        """Extract review count from the page."""
        count = 0
        try:
            selectors = [
                '[data-test="review-count"]',
                ".rating-headline-text",
                "text=/\\d+[kK]?.*[Rr]eviews?/",
            ]

            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        # Extract number, handle "K" notation (e.g., "1.5K reviews")
                        match = re.search(r"([0-9,.]+)\s*[kK]?", text)
                        if match:
                            num_str = match.group(1).replace(",", "")
                            num = float(num_str)
                            # If "K" notation, multiply by 1000
                            if "k" in text.lower():
                                num = int(num * 1000)
                            return int(num)
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Could not extract review count: {e}")
        return count

    async def _scrape_sub_ratings(self) -> dict[str, float]:
        """
        Extract sub-ratings (Work-Life Balance, Culture, Career, Comp, Senior Management).
        Returns dict with rating category names as keys.
        """
        sub_ratings = {}
        try:
            # Glassdoor shows sub-ratings in a ratings section
            selectors = [
                '[data-test="rating-category"]',
                ".rating-list-item",
                ".ratings-item",
            ]

            for selector in selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    for element in elements:
                        try:
                            # Get category name
                            name_elem = await element.query_selector(
                                ".rating-category-name, .css-1kiw7k8"
                            )
                            if name_elem:
                                category = await name_elem.inner_text()
                                category = category.lower().strip()

                            # Get rating value
                            rating_elem = await element.query_selector(
                                '[data-test="rating-value"], .rating-value, .css-1c33izo'
                            )
                            if rating_elem:
                                rating_text = await rating_elem.inner_text()
                                rating = float(rating_text.strip())

                                if category:
                                    sub_ratings[category] = rating
                        except Exception as e:
                            logger.debug(
                                f"Could not extract sub-rating from element: {e}"
                            )
                            continue
                    break

        except Exception as e:
            logger.debug(f"Could not extract sub-ratings: {e}")

        return sub_ratings

    async def _scrape_recommend_percent(self) -> float:
        """Extract recommendation percentage."""
        try:
            selectors = [
                '[data-test="recommend-to-friend"]',
                "text=/\\d+%.*[Rr]ecommend/",
            ]

            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        match = re.search(r"(\\d+(?:\\.\\d+)?)\\s*%", text)
                        if match:
                            return float(match.group(1))
                except Exception:
                    continue

            return 0
        except Exception as e:
            logger.debug(f"Could not extract recommendation percentage: {e}")
            return 0

    async def _scrape_company_size(self) -> str:
        """Extract company size."""
        try:
            selectors = [
                '[data-test="employer-size"]',
                "text=/\\d+\\s*to\\s*\\d+.*[Ee]mployees/",
                "text=/\\d+\\+.*[Ee]mployees/",
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
        """Extract company industry."""
        try:
            selectors = [
                '[data-test="employer-industry"]',
                ".css-1cnx9af",  # Industry label class
                "text=/[Ii]ndustry.*/",
            ]

            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        # Clean up "Industry: XYZ" format
                        text = re.sub(r"[Ii]ndustry\\s*:?\\s*", "", text)
                        return text.strip()
                except Exception:
                    continue

            return ""
        except Exception as e:
            logger.debug(f"Could not extract industry: {e}")
            return ""

    async def _scrape_company_website(self) -> str:
        """Extract company website URL."""
        try:
            selectors = [
                '[data-test="employer-website"]',
                'a[href^="http"]:has-text("Website")',
            ]

            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        href = await element.get_attribute("href")
                        if href and "glassdoor" not in href.lower():
                            return href
                except Exception:
                    continue

            return ""
        except Exception as e:
            logger.debug(f"Could not extract company website: {e}")
            return ""

    async def _random_delay(self):
        """Random delay to avoid detection."""
        await asyncio.sleep(random.uniform(*self.random_human_delay_range))

    async def _scrape_company(self, company_name: str) -> ScraperModel:
        """
        Main scraping method for a company profile.
        """
        start_time = time.time()
        result = ScraperModel(company_name=company_name, scraper=SCRAPERS.GLASSDOOR)

        logger.info(f"Starting scrape for company: {company_name}")

        # Glassdoor URL format: /Overview/Working-at-{company-name}-EI_IE{id}.htm
        # We'll try a search first to find the correct company ID
        search_url = f"{self.BASE_URL}/Search/results.htm?keyword={company_name.replace(' ', '+')}"

        try:
            response = await self.page.goto(
                search_url, wait_until="domcontentloaded", timeout=15_000
            )

            if response.status == 200:
                # Try to find and click on the company overview link
                company_link = await self.page.query_selector(
                    'a[href*="/Overview/"][href*="EI_IE"]'
                )

                if company_link:
                    # Navigate to company overview page
                    await company_link.click()
                    await self.page.wait_for_load_state("domcontentloaded")

                    # Extract all data
                    result.rating = await self._scrape_rating()
                    result.review_count = await self._scrape_review_count()
                    result.company_website = await self._scrape_company_website()

                    # Extract sub-ratings
                    sub_ratings = await self._scrape_sub_ratings()
                    result.work_life_balance_rating = sub_ratings.get(
                        "work-life balance", sub_ratings.get("work/life balance")
                    )
                    result.culture_rating = sub_ratings.get(
                        "culture & values", sub_ratings.get("culture")
                    )
                    result.career_rating = sub_ratings.get(
                        "career opportunities", sub_ratings.get("career")
                    )
                    result.salary_benefits_rating = sub_ratings.get(
                        "comp & benefits", sub_ratings.get("compensation")
                    )
                    result.management_rating = sub_ratings.get(
                        "senior management", sub_ratings.get("management")
                    )

                    result.recommend_percent = await self._scrape_recommend_percent()
                    result.company_size = await self._scrape_company_size()
                    result.industry = await self._scrape_industry()
                    result.profile_url = self.page.url

                    result.success = True
                    logger.info(
                        f"Successfully scraped {company_name}: "
                        f"rating={result.rating}, reviews={result.review_count}, "
                        f"recommend={result.recommend_percent}%"
                    )
                else:
                    logger.warning(f"Company profile not found for: {company_name}")
                    result.success = False
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
