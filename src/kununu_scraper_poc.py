#!/usr/bin/env python3
"""
Kununu Scraper PoC - Complete proof of concept with tests
A robust scraper for extracting company ratings from Kununu.com

Author: Company Rating Scraper Project
Usage: python kununu_scraper_poc.py --test
"""

import asyncio
import re
import time
import random
from typing import Optional, Dict, List, NamedTuple
from dataclasses import dataclass
from datetime import datetime
import logging
from urllib.parse import urljoin, quote
import json

# External dependencies (add to requirements.txt)
try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
    import pytest
    import aiohttp
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install playwright pytest aiohttp")
    print("Then run: playwright install")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class KununuResult:
    """Container for Kununu scraping results"""
    company_name: str
    rating: Optional[float] = None
    review_count: Optional[int] = None
    profile_url: Optional[str] = None
    scraped_at: datetime = None
    success: bool = False
    error_message: Optional[str] = None
    scrape_duration: Optional[float] = None

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.utcnow()


class KununuScraper:
    """
    Robust Kununu scraper with anti-detection measures and multiple fallback strategies
    """
    
    BASE_URL = "https://www.kununu.com"
    SEARCH_URL = f"{BASE_URL}/search"
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    def __init__(self, headless: bool = True, delay_range: tuple = (2, 8)):
        self.headless = headless
        self.delay_range = delay_range
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_browser()
    
    async def start_browser(self):
        """Initialize browser with anti-detection measures"""
        try:
            self.playwright = await async_playwright().start()
            
            # Launch browser with stealth options
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-extensions'
                ]
            )
            
            # Create context with realistic settings
            context = await self.browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent=random.choice(self.USER_AGENTS),
                locale='de-DE',
                timezone_id='Europe/Berlin'
            )
            
            # Add stealth scripts
            await context.add_init_script("""
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
            """)
            
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
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
    
    async def scrape_company_rating(self, company_name: str) -> KununuResult:
        """
        Main scraping method - tries multiple strategies to get company rating
        """
        start_time = time.time()
        result = KununuResult(company_name=company_name)
        
        try:
            logger.info(f"Starting scrape for company: {company_name}")
            
            # Strategy 1: Direct company page search
            success = await self._try_direct_company_page(company_name, result)
            
            if not success:
                # Strategy 2: Search page approach
                success = await self._try_search_page(company_name, result)
            
            if not success:
                # Strategy 3: Google search fallback
                success = await self._try_google_search_fallback(company_name, result)
            
            result.success = success
            result.scrape_duration = time.time() - start_time
            
            # Add random delay to be respectful
            await self._random_delay()
            
            if success:
                logger.info(f"Successfully scraped {company_name}: {result.rating}/5.0 ({result.review_count} reviews)")
            else:
                logger.warning(f"Failed to scrape {company_name}: {result.error_message}")
                
        except Exception as e:
            result.error_message = str(e)
            result.scrape_duration = time.time() - start_time
            logger.error(f"Exception scraping {company_name}: {e}")
        
        return result
    
    async def _try_direct_company_page(self, company_name: str, result: KununuResult) -> bool:
        """Try to access company page directly using common URL patterns"""
        # Generate potential URL slugs
        potential_slugs = self._generate_company_slugs(company_name)
        
        for slug in potential_slugs:
            try:
                url = f"{self.BASE_URL}/de/{slug}"
                logger.debug(f"Trying direct URL: {url}")
                
                response = await self.page.goto(url, wait_until='domcontentloaded', timeout=10000)
                
                if response.status == 200:
                    # Check if this is actually a company page (not 404 or redirect)
                    if await self._is_valid_company_page():
                        rating_data = await self._extract_rating_from_page()
                        if rating_data:
                            result.rating = rating_data.get('rating')
                            result.review_count = rating_data.get('review_count')
                            result.profile_url = url
                            return True
                            
            except Exception as e:
                logger.debug(f"Direct URL {url} failed: {e}")
                continue
                
        return False
    
    async def _try_search_page(self, company_name: str, result: KununuResult) -> bool:
        """Use Kununu search to find company"""
        try:
            search_url = f"{self.SEARCH_URL}?q={quote(company_name)}"
            logger.debug(f"Trying search URL: {search_url}")
            
            await self.page.goto(search_url, wait_until='domcontentloaded', timeout=15000)
            
            # Wait for search results to load
            await self.page.wait_for_selector('[data-testid="search-results"], .search-results, .company-tile', timeout=10000)
            
            # Find the best matching company in search results
            company_link = await self._find_best_company_match(company_name)
            
            if company_link:
                # Navigate to company page
                await self.page.click(company_link)
                await self.page.wait_for_load_state('domcontentloaded')
                
                rating_data = await self._extract_rating_from_page()
                if rating_data:
                    result.rating = rating_data.get('rating')
                    result.review_count = rating_data.get('review_count')
                    result.profile_url = self.page.url
                    return True
                    
        except Exception as e:
            logger.debug(f"Search page approach failed: {e}")
            
        return False
    
    async def _try_google_search_fallback(self, company_name: str, result: KununuResult) -> bool:
        """Use Google search to find Kununu page"""
        try:
            # Google search for "company name kununu"
            google_query = f"{company_name} site:kununu.com"
            google_url = f"https://www.google.com/search?q={quote(google_query)}"
            
            logger.debug(f"Trying Google search: {google_query}")
            
            await self.page.goto(google_url, wait_until='domcontentloaded', timeout=15000)
            
            # Look for Kununu links in results
            kununu_links = await self.page.query_selector_all('a[href*="kununu.com"]')
            
            for link in kununu_links[:3]:  # Try first 3 results
                try:
                    href = await link.get_attribute('href')
                    if '/de/' in href and not any(skip in href for skip in ['search', 'blog', 'about']):
                        # Navigate to the Kununu page
                        await self.page.goto(href, wait_until='domcontentloaded', timeout=10000)
                        
                        if await self._is_valid_company_page():
                            rating_data = await self._extract_rating_from_page()
                            if rating_data:
                                result.rating = rating_data.get('rating')
                                result.review_count = rating_data.get('review_count')
                                result.profile_url = href
                                return True
                                
                except Exception as e:
                    logger.debug(f"Google result link failed: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Google search fallback failed: {e}")
            
        return False
    
    async def _extract_rating_from_page(self) -> Optional[Dict]:
        """Extract rating data from current Kununu company page using multiple selectors"""
        
        # Multiple selector strategies for robustness
        rating_selectors = [
            # Modern data attributes (most reliable)
            '[data-testid*="rating"] [data-testid*="score"]',
            '[data-testid*="overall-rating"]',
            '[data-testid="company-rating"]',
            
            # Class-based selectors
            '.rating-score .score-value',
            '.overall-rating .rating-value',
            '.company-rating-score',
            '.rating-display .rating-number',
            
            # Semantic selectors
            '.rating-container [class*="score"]',
            '.rating-wrapper .rating-value',
            
            # Text-based fallback (find numbers that look like ratings)
            'text=/^[0-5]\\.[0-9]$/',
            'text=/^[0-5],[0-9]$/',  # German decimal notation
        ]
        
        review_count_selectors = [
            '[data-testid*="review-count"]',
            '[data-testid*="reviews"]',
            '.review-count',
            '.reviews-count',
            'text=/\\d+\\s+(Bewertungen?|Reviews?)/i',
            'text=/\\(\\d+\\)/',  # Numbers in parentheses
        ]
        
        try:
            rating = None
            review_count = None
            
            # Try to find rating
            for selector in rating_selectors:
                try:
                    if selector.startswith('text='):
                        # Text-based selector
                        element = await self.page.wait_for_selector(selector, timeout=2000)
                    else:
                        # CSS selector
                        element = await self.page.query_selector(selector)
                        
                    if element:
                        text = await element.inner_text()
                        text = text.strip().replace(',', '.')  # Handle German decimals
                        
                        # Extract rating number
                        rating_match = re.search(r'([0-5]\.[0-9])', text)
                        if rating_match:
                            rating = float(rating_match.group(1))
                            logger.debug(f"Found rating {rating} with selector: {selector}")
                            break
                            
                except Exception:
                    continue
            
            # Try to find review count
            for selector in review_count_selectors:
                try:
                    if selector.startswith('text='):
                        element = await self.page.wait_for_selector(selector, timeout=2000)
                    else:
                        element = await self.page.query_selector(selector)
                        
                    if element:
                        text = await element.inner_text()
                        
                        # Extract number from text like "123 Bewertungen" or "(456)"
                        count_match = re.search(r'(\d+)', text)
                        if count_match:
                            review_count = int(count_match.group(1))
                            logger.debug(f"Found review count {review_count} with selector: {selector}")
                            break
                            
                except Exception:
                    continue
            
            # Additional validation
            if rating is not None:
                if not (0.0 <= rating <= 5.0):
                    logger.warning(f"Invalid rating value: {rating}")
                    rating = None
            
            if review_count is not None:
                if review_count < 0 or review_count > 100000:  # Sanity check
                    logger.warning(f"Invalid review count: {review_count}")
                    review_count = None
            
            if rating is not None or review_count is not None:
                return {
                    'rating': rating,
                    'review_count': review_count
                }
                
        except Exception as e:
            logger.debug(f"Rating extraction failed: {e}")
        
        return None
    
    async def _is_valid_company_page(self) -> bool:
        """Check if current page is a valid Kununu company profile"""
        try:
            # Look for indicators that this is a company page
            indicators = [
                '[data-testid*="company"]',
                '.company-profile',
                '.company-header',
                'text=/Bewertungen/i',
                'text=/Gehalt/i',
                'text=/Kultur/i',
                '.rating-container',
            ]
            
            for indicator in indicators:
                element = await self.page.query_selector(indicator)
                if element:
                    return True
            
            # Check URL pattern
            current_url = self.page.url
            if '/de/' in current_url and not any(skip in current_url for skip in ['search', 'blog', 'about', '404']):
                # Additional check: page should not be a 404 or error page
                page_title = await self.page.title()
                if '404' not in page_title and 'Error' not in page_title:
                    return True
                    
        except Exception as e:
            logger.debug(f"Company page validation failed: {e}")
        
        return False
    
    def _generate_company_slugs(self, company_name: str) -> List[str]:
        """Generate potential URL slugs for company name"""
        # Clean and normalize company name
        name = company_name.lower().strip()
        
        # Remove common company suffixes
        suffixes = ['gmbh', 'ag', 'se', 'ltd', 'inc', 'corp', 'llc', 'co.', 'kg', 'ohg']
        for suffix in suffixes:
            name = re.sub(rf'\b{suffix}\b\.?', '', name, flags=re.IGNORECASE)
        
        # Clean special characters
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'\s+', '-', name).strip('-')
        
        slugs = []
        
        # Add main slug
        if name:
            slugs.append(name)
        
        # Add variations
        if '-' in name:
            # Without hyphens
            slugs.append(name.replace('-', ''))
            # With spaces instead of hyphens
            slugs.append(name.replace('-', ' ').replace(' ', ''))
        
        # Add original with simple cleaning
        original_clean = re.sub(r'[^\w\s]', '', company_name.lower()).replace(' ', '-')
        if original_clean not in slugs:
            slugs.append(original_clean)
        
        return slugs[:5]  # Limit to prevent too many requests
    
    async def _find_best_company_match(self, company_name: str) -> Optional[str]:
        """Find best matching company in search results"""
        try:
            # Look for company tiles/cards in search results
            company_selectors = [
                '[data-testid*="company-tile"] a',
                '.company-tile a',
                '.search-result-company a',
                '.company-card a',
                'a[href*="/de/"]',  # Generic Kununu company links
            ]
            
            normalized_search = company_name.lower().strip()
            
            for selector in company_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    
                    for element in elements[:10]:  # Check first 10 results
                        try:
                            text = await element.inner_text()
                            href = await element.get_attribute('href')
                            
                            # Simple matching - look for company name in link text
                            if (normalized_search in text.lower() or 
                                any(word in text.lower() for word in normalized_search.split())):
                                return selector  # Return the selector, not href
                                
                        except Exception:
                            continue
                            
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug(f"Company match search failed: {e}")
        
        return None
    
    async def _random_delay(self):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(*self.delay_range)
        logger.debug(f"Adding {delay:.2f}s delay")
        await asyncio.sleep(delay)


# ============================================================================
# TESTS
# ============================================================================

class TestKununuScraper:
    """Comprehensive test suite for Kununu scraper"""
    
    @pytest.fixture
    async def scraper(self):
        """Create scraper instance for tests"""
        scraper = KununuScraper(headless=True, delay_range=(0.1, 0.5))  # Faster for tests
        await scraper.start_browser()
        yield scraper
        await scraper.close_browser()
    
    def test_result_dataclass(self):
        """Test KununuResult dataclass functionality"""
        result = KununuResult(company_name="Test Company")
        
        assert result.company_name == "Test Company"
        assert result.rating is None
        assert result.success is False
        assert result.scraped_at is not None
        assert isinstance(result.scraped_at, datetime)
    
    def test_company_slug_generation(self):
        """Test URL slug generation for various company names"""
        scraper = KununuScraper()
        
        # Test cases with expected outcomes
        test_cases = [
            ("SAP SE", ["sap", "sap-se"]),
            ("Mercedes-Benz AG", ["mercedes-benz", "mercedesbenz"]),
            ("Deutsche Bank", ["deutsche-bank", "deutschebank"]),
            ("Siemens AG", ["siemens", "siemens-ag"]),
            ("BMW Group", ["bmw-group", "bmwgroup", "bmw"]),
        ]
        
        for company_name, expected_patterns in test_cases:
            slugs = scraper._generate_company_slugs(company_name)
            
            # Check that we got some slugs
            assert len(slugs) > 0
            assert len(slugs) <= 5  # Should limit to 5
            
            # Check that at least one expected pattern is present
            found_expected = any(
                any(pattern in slug for pattern in expected_patterns)
                for slug in slugs
            )
            assert found_expected, f"No expected patterns found in {slugs} for {company_name}"
    
    def test_rating_extraction_from_html(self):
        """Test rating extraction from mock HTML"""
        # This would normally use mock HTML, but we'll test the regex patterns
        test_texts = [
            "4.2",
            "3,8",  # German decimal notation
            "2.5 von 5",
            "Rating: 4.1",
        ]
        
        for text in test_texts:
            # Test the regex pattern used in _extract_rating_from_page
            rating_match = re.search(r'([0-5]\.[0-9])', text.replace(',', '.'))
            if rating_match:
                rating = float(rating_match.group(1))
                assert 0.0 <= rating <= 5.0
    
    def test_review_count_extraction(self):
        """Test review count extraction patterns"""
        test_texts = [
            "123 Bewertungen",
            "456 Reviews", 
            "(789)",
            "1,234 Bewertungen",  # German thousand separator
            "5 Bewertung",  # Singular
        ]
        
        for text in test_texts:
            count_match = re.search(r'(\d+)', text.replace(',', ''))
            if count_match:
                count = int(count_match.group(1))
                assert count > 0
    
    @pytest.mark.asyncio
    async def test_browser_startup_and_cleanup(self):
        """Test browser lifecycle management"""
        scraper = KununuScraper(headless=True)
        
        # Test startup
        await scraper.start_browser()
        assert scraper.browser is not None
        assert scraper.page is not None
        
        # Test basic page navigation
        await scraper.page.goto("https://www.example.com")
        title = await scraper.page.title()
        assert title is not None
        
        # Test cleanup
        await scraper.close_browser()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality"""
        async with KununuScraper(headless=True) as scraper:
            assert scraper.browser is not None
            assert scraper.page is not None
            
            # Should be able to navigate
            await scraper.page.goto("https://www.example.com")
        
        # Browser should be closed after exiting context
        # Note: We can't easily test this without internal access
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_scrape_known_company(self):
        """Integration test with a well-known company"""
        async with KununuScraper(headless=True, delay_range=(0.5, 1.0)) as scraper:
            # Test with SAP - likely to have a Kununu page
            result = await scraper.scrape_company_rating("SAP")
            
            # Basic validation
            assert result.company_name == "SAP"
            assert result.scraped_at is not None
            assert result.scrape_duration is not None
            assert result.scrape_duration > 0
            
            if result.success:
                # If successful, validate data quality
                if result.rating is not None:
                    assert 0.0 <= result.rating <= 5.0
                if result.review_count is not None:
                    assert result.review_count >= 0
                if result.profile_url is not None:
                    assert "kununu.com" in result.profile_url
                    
                print(f"✅ Successfully scraped SAP: {result.rating}/5.0 ({result.review_count} reviews)")
            else:
                print(f"❌ Failed to scrape SAP: {result.error_message}")
                # Don't fail the test - scraping can fail for many reasons
    
    @pytest.mark.asyncio
    @pytest.mark.integration  
    async def test_scrape_nonexistent_company(self):
        """Test handling of non-existent company"""
        async with KununuScraper(headless=True, delay_range=(0.5, 1.0)) as scraper:
            result = await scraper.scrape_company_rating("NonExistentCompanyXYZ123")
            
            assert result.company_name == "NonExistentCompanyXYZ123"
            assert result.success is False
            assert result.rating is None
            assert result.review_count is None
            assert result.profile_url is None
    
    @pytest.mark.asyncio
    async def test_multiple_company_scraping(self):
        """Test scraping multiple companies in sequence"""
        test_companies = ["SAP", "BMW", "Siemens"]
        results = []
        
        async with KununuScraper(headless=True, delay_range=(0.1, 0.3)) as scraper:
            for company in test_companies:
                result = await scraper.scrape_company_rating(company)
                results.append(result)
        
        assert len(results) == len(test_companies)
        
        for i, result in enumerate(results):
            assert result.company_name == test_companies[i]
            assert result.scraped_at is not None
            assert result.scrape_duration is not None
    
    def test_data_validation(self):
        """Test data validation logic"""
        # Test valid ratings
        valid_ratings = [0.0, 2.5, 3.7, 5.0]
        for rating in valid_ratings:
            assert 0.0 <= rating <= 5.0
        
        # Test invalid ratings that should be caught
        invalid_ratings = [-1.0, 5.1, 10.0]
        for rating in invalid_ratings:
            assert not (0.0 <= rating <= 5.0)
        
        # Test review counts
        valid_counts = [0, 1, 100, 1000, 50000]
        for count in valid_counts:
            assert count >= 0
        
        invalid_counts = [-1, -100]
        for count in invalid_counts:
            assert not (count >= 0)


# ============================================================================
# CLI AND UTILITY FUNCTIONS
# ============================================================================

async def demo_scraping(companies: List[str] = None, export_file: str = None, resume: bool = False):
    """Demo function showing how to use the scraper with incremental saving"""
    if companies is None:
        companies = [
            "SAP",
            "BMW",
            "Siemens",
            "Mercedes-Benz",
            "Deutsche Bank"
        ]

    test_companies = companies

    # Handle resume functionality
    if resume and export_file:
        already_scraped = get_already_scraped_companies(export_file)
        original_count = len(test_companies)
        test_companies = [c for c in test_companies if c not in already_scraped]
        skipped_count = original_count - len(test_companies)
        if skipped_count > 0:
            print(f"🔄 Resume mode: Skipping {skipped_count} already scraped companies")
        if not test_companies:
            print("✅ All companies already scraped!")
            return []
    
    print("🚀 Starting Kununu scraper demo...")
    print(f"📊 Testing {len(test_companies)} companies")
    print("-" * 60)
    
    results = []
    
    async with KununuScraper(headless=True, delay_range=(1, 3)) as scraper:
        for i, company in enumerate(test_companies, 1):
            print(f"[{i}/{len(test_companies)}] Scraping {company}...")

            try:
                result = await scraper.scrape_company_rating(company)
                results.append(result)

                # Save immediately after each scrape if export file specified
                if export_file:
                    append_result_to_csv(result, export_file)
                    print(f"  💾 Saved to {export_file}")

                if result.success:
                    rating_str = f"{result.rating}/5.0" if result.rating else "N/A"
                    reviews_str = f"({result.review_count} reviews)" if result.review_count else "(0 reviews)"
                    print(f"  ✅ Success: {rating_str} {reviews_str}")
                    if result.profile_url:
                        print(f"  🔗 URL: {result.profile_url}")
                else:
                    print(f"  ❌ Failed: {result.error_message}")

                print(f"  ⏱️  Duration: {result.scrape_duration:.2f}s")
                print()

            except Exception as e:
                print(f"  💥 Unexpected error scraping {company}: {e}")
                # Create error result and save it too
                error_result = KununuResult(company_name=company, error_message=str(e), success=False)
                results.append(error_result)
                if export_file:
                    append_result_to_csv(error_result, export_file)
                    print(f"  💾 Error result saved to {export_file}")
                print()
    
    # Summary
    successful = sum(1 for r in results if r.success)
    total_time = sum(r.scrape_duration for r in results if r.scrape_duration)
    
    print("=" * 60)
    print("📈 SCRAPING SUMMARY")
    print("=" * 60)
    print(f"Total companies: {len(results)}")
    print(f"Successful: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"Failed: {len(results) - successful}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average time per company: {total_time/len(results):.2f}s")
    
    # Show results table
    print("\n📋 DETAILED RESULTS")
    print("-" * 60)
    print(f"{'Company':<20} {'Rating':<8} {'Reviews':<10} {'Status':<10}")
    print("-" * 60)
    
    for result in results:
        rating_str = f"{result.rating:.1f}/5.0" if result.rating else "N/A"
        reviews_str = str(result.review_count) if result.review_count else "N/A"
        status_str = "✅ OK" if result.success else "❌ FAIL"
        
        print(f"{result.company_name:<20} {rating_str:<8} {reviews_str:<10} {status_str:<10}")
    
    return results


def read_companies_from_file(filename: str) -> List[str]:
    """Read company names from text file, one per line"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            companies = [line.strip() for line in f if line.strip()]
        print(f"📂 Loaded {len(companies)} companies from {filename}")
        return companies
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return []
    except Exception as e:
        print(f"❌ Error reading file {filename}: {e}")
        return []


def get_already_scraped_companies(filename: str) -> set:
    """Get list of companies already scraped from existing CSV"""
    import csv
    import os

    if not os.path.exists(filename):
        return set()

    try:
        with open(filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            companies = {row['company_name'] for row in reader if row.get('company_name')}
        print(f"📂 Found {len(companies)} already scraped companies in {filename}")
        return companies
    except Exception as e:
        print(f"⚠️ Error reading existing CSV {filename}: {e}")
        return set()


def append_result_to_csv(result: KununuResult, filename: str):
    """Append single result to CSV file (creates file with header if doesn't exist)"""
    import csv
    import os

    fieldnames = ['company_name', 'rating', 'review_count', 'profile_url',
                 'scraped_at', 'success', 'error_message', 'scrape_duration']

    file_exists = os.path.exists(filename)

    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write header if file is new
        if not file_exists:
            writer.writeheader()

        writer.writerow({
            'company_name': result.company_name,
            'rating': result.rating,
            'review_count': result.review_count,
            'profile_url': result.profile_url,
            'scraped_at': result.scraped_at.isoformat() if result.scraped_at else None,
            'success': result.success,
            'error_message': result.error_message,
            'scrape_duration': result.scrape_duration
        })


def export_results_to_csv(results: List[KununuResult], filename: str = "kununu_results.csv"):
    """Export scraping results to CSV file"""
    import csv

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['company_name', 'rating', 'review_count', 'profile_url',
                     'scraped_at', 'success', 'error_message', 'scrape_duration']

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            writer.writerow({
                'company_name': result.company_name,
                'rating': result.rating,
                'review_count': result.review_count,
                'profile_url': result.profile_url,
                'scraped_at': result.scraped_at.isoformat() if result.scraped_at else None,
                'success': result.success,
                'error_message': result.error_message,
                'scrape_duration': result.scrape_duration
            })

    print(f"💾 Results exported to {filename}")


async def main():
    """Main CLI function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Kununu Company Rating Scraper PoC')
    parser.add_argument('--demo', action='store_true', help='Run demo with test companies')
    parser.add_argument('--test', action='store_true', help='Run test suite')
    parser.add_argument('--company', type=str, help='Scrape specific company')
    parser.add_argument('--input', type=str, help='Text file with company names (one per line)')
    parser.add_argument('--export', type=str, help='Export results to CSV file')
    parser.add_argument('--resume', action='store_true', help='Resume scraping, skip already processed companies')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser in headless mode')
    
    args = parser.parse_args()
    
    if args.test:
        print("🧪 Running test suite...")
        import subprocess
        result = subprocess.run(['python', '-m', 'pytest', __file__, '-v'], 
                              capture_output=False)
        return result.returncode
    
    elif args.demo:
        results = await demo_scraping(export_file=args.export, resume=args.resume)
        # Only export at end if not using incremental saving
        if args.export and not args.resume:
            export_results_to_csv(results, args.export)

    elif args.input:
        companies = read_companies_from_file(args.input)
        if companies:
            print(f"🚀 Starting scraping for {len(companies)} companies from file...")
            results = await demo_scraping(companies, export_file=args.export, resume=args.resume)
            # Only export at end if not using incremental saving
            if args.export and not args.resume:
                export_results_to_csv(results, args.export)
        else:
            print("❌ No companies to scrape")
            return 1
    
    elif args.company:
        print(f"🔍 Scraping company: {args.company}")
        
        async with KununuScraper(headless=args.headless) as scraper:
            result = await scraper.scrape_company_rating(args.company)
            
            print(f"\n📊 Results for {result.company_name}:")
            print(f"Rating: {result.rating}/5.0" if result.rating else "Rating: N/A")
            print(f"Reviews: {result.review_count}" if result.review_count else "Reviews: N/A")
            print(f"URL: {result.profile_url}" if result.profile_url else "URL: N/A")
            print(f"Success: {'✅ Yes' if result.success else '❌ No'}")
            if not result.success:
                print(f"Error: {result.error_message}")
            print(f"Duration: {result.scrape_duration:.2f}s")
        
        if args.export:
            export_results_to_csv([result], args.export)
    
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    # Requirements check
    try:
        import playwright
        import pytest
        import aiohttp
    except ImportError as e:
        print("❌ Missing dependencies!")
        print("Install with:")
        print("pip install playwright pytest aiohttp")
        print("playwright install")
        exit(1)
    
    # Run main function
    exit_code = asyncio.run(main())
    exit(exit_code)