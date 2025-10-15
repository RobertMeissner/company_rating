import pytest

from src.application.services.job_orchestrator import JobOrchestrator
from src.domain.value_objects.company import Company
from src.infrastructure.scrapers.company_scraper_manager import (
    CompanyScraperManager,
)
from src.infrastructure.scrapers.glassdoor_scraper import GlassdoorScraper
from src.infrastructure.scrapers.kununu_scraper import KununuScraper


@pytest.fixture
def scraper_manager():
    return CompanyScraperManager([KununuScraper, GlassdoorScraper])


@pytest.fixture
def kununu_company_full():
    return Company(
        name="Test Company",
        kununu_rating=4.2,
        kununu_review_count=150,
        kununu_career_rating=4.0,
        kununu_work_life_balance_rating=4.5,
        kununu_salary_benefits_rating=3.8,
        kununu_management_rating=3.9,
        kununu_culture_rating=4.3,
        kununu_recommend_percent=85.0,
        website="https://test-company.com",
        industry="Software",
        company_size="500-1000",
    )


@pytest.fixture
def glassdoor_company_full():
    return Company(
        name="Test Company",
        glassdoor_rating=4.0,
        glassdoor_review_count=200,
        glassdoor_url="https://glassdoor.com/test-company",
        website="https://test-company.com",
        industry="Technology",
        company_size="500-1000",
        location="Berlin, Germany",
    )


@pytest.fixture
def kununu_company_partial():
    return Company(
        name="Test Company",
        kununu_rating=3.5,
        kununu_review_count=50,
        website="https://test-company.com",
    )


@pytest.fixture
def glassdoor_company_partial():
    return Company(
        name="Test Company",
        glassdoor_rating=3.8,
        glassdoor_review_count=75,
    )


@pytest.fixture
def empty_company():
    """Company with no ratings"""
    return Company(name="Test Company")


class TestMergeCombineAll:
    def test_merge_combines_all_fields_from_both_sources(
        self, kununu_company_full, glassdoor_company_full, scraper_manager
    ):
        results = [
            ("KununuScraper", kununu_company_full),
            ("GlassdoorScraper", glassdoor_company_full),
        ]

        merged = scraper_manager._combined_scraper_results("Test Company", results)

        # Should have Kununu ratings
        assert merged.kununu_rating == 4.2
        assert merged.kununu_review_count == 150
        assert merged.kununu_career_rating == 4.0
        assert merged.kununu_work_life_balance_rating == 4.5
        assert merged.kununu_recommend_percent == 85.0

        # Should have Glassdoor ratings
        assert merged.glassdoor_rating == 4.0
        assert merged.glassdoor_review_count == 200
        assert merged.glassdoor_url == "https://glassdoor.com/test-company"

        # Should have common fields (later scraper wins)
        assert merged.website == "https://test-company.com"
        assert merged.industry == "Technology"  # Glassdoor was second
        assert merged.company_size == "500-1000"

    def test_merge_preserves_source_specific_ratings(
        self, kununu_company_full, glassdoor_company_full, scraper_manager
    ):
        # Create conflicting data (Kununu scraper shouldn't have glassdoor_rating)
        kununu_with_wrong_glassdoor = Company(
            name="Test Company",
            kununu_rating=4.2,
            glassdoor_rating=5.0,  # This shouldn't be used!
        )

        results = [
            ("KununuScraper", kununu_with_wrong_glassdoor),
            ("GlassdoorScraper", glassdoor_company_full),
        ]

        merged = scraper_manager._combined_scraper_results("Test Company", results)

        assert merged.kununu_rating == 4.2
        assert merged.glassdoor_rating == 4.0

    def test_merge_fills_gaps_from_both_sources(
        self, kununu_company_partial, glassdoor_company_partial, scraper_manager
    ):

        results = [
            ("KununuScraper", kununu_company_partial),
            ("GlassdoorScraper", glassdoor_company_partial),
        ]

        merged = scraper_manager._combined_scraper_results("Test Company", results)

        # Should have both ratings
        assert merged.kununu_rating == 3.5
        assert merged.glassdoor_rating == 3.8

        # Should have website from Kununu (only source)
        assert merged.website == "https://test-company.com"

    def test_merge_handles_empty_results(self, empty_company, scraper_manager):

        results = [
            ("KununuScraper", empty_company),
            ("GlassdoorScraper", empty_company),
        ]

        merged = scraper_manager._combined_scraper_results("Test Company", results)

        assert merged.name == "Test Company"
        assert merged.kununu_rating is None
        assert merged.glassdoor_rating is None

    def test_merge_skips_empty_values(self, kununu_company_full, scraper_manager):
        """Should not overwrite good values with None/0/empty"""

        # Second scraper has empty values
        empty_glassdoor = Company(
            name="Test Company",
            glassdoor_rating=None,  # Empty
            website="",  # Empty string
            industry=None,
        )

        results = [
            ("KununuScraper", kununu_company_full),
            ("GlassdoorScraper", empty_glassdoor),
        ]

        merged = scraper_manager._combined_scraper_results("Test Company", results)

        # Should keep Kununu values (not overwritten by empty Glassdoor)
        assert merged.website == "https://test-company.com"
        assert merged.industry == "Software"


class TestCreateScraperManager:
    """Test the factory function for creating scraper managers"""

    def test_creates_manager_with_valid_scrapers(self, scraper_manager):
        assert isinstance(scraper_manager, CompanyScraperManager)
        assert len(scraper_manager.scraper_factories) == 2


class TestEdgeCases:

    def test_merge_with_no_results(self, kununu_company_full, scraper_manager):

        merged = scraper_manager._combined_scraper_results("Test Company", [])

        assert merged.name == "Test Company"
        assert merged.kununu_rating is None

    def test_merge_with_single_result(self, kununu_company_full, scraper_manager):
        """Should handle merging with only one scraper result"""

        results = [("KununuScraper", kununu_company_full)]

        merged = scraper_manager._combined_scraper_results("Test Company", results)

        assert merged.kununu_rating == 4.2
        assert merged.kununu_review_count == 150

    def test_merge_preserves_company_name(self, kununu_company_full, scraper_manager):
        wrong_name_company = Company(
            name="Different Name",
            kununu_rating=4.0,
        )

        results = [("KununuScraper", wrong_name_company)]

        merged = scraper_manager._combined_scraper_results("Correct Name", results)

        assert merged.name == "Correct Name"

    def test_merge_with_alternative_names(self, scraper_manager):
        """Should handle companies with alternative names"""

        company_with_alternatives = Company(
            name="Test Company",
            alternative_names=["Test Corp", "TC GmbH"],
            kununu_rating=4.0,
        )

        results = [("KununuScraper", company_with_alternatives)]

        merged = scraper_manager._combined_scraper_results("Test Company", results)

        assert merged.alternative_names == ["Test Corp", "TC GmbH"]
        assert merged.kununu_rating == 4.0


class TestAlternativeNameCapture:
    """Test capturing scraped names as alternative names"""

    def test_captures_scraped_name_as_alternative(self, scraper_manager):
        """Should capture scraped company name as alternative name"""
        # Scraper returns different name than what we searched for
        scraped_company = Company(
            name="SAP SE",  # Different from search term
            kununu_rating=4.0,
        )

        results = [("KununuScraper", scraped_company)]

        merged = scraper_manager._combined_scraper_results("SAP", results)

        # Should preserve our name
        assert merged.name == "SAP"
        # Should capture scraped name as alternative
        assert "SAP SE" in merged.alternative_names

    def test_combines_alternative_names_from_multiple_scrapers(self, scraper_manager):
        """Should combine alternative names from all scrapers"""
        kununu_company = Company(
            name="SAP-SE",  # Kununu format
            kununu_rating=4.0,
            alternative_names=["SAP GmbH"],
        )

        glassdoor_company = Company(
            name="SAP SE",  # Glassdoor format
            glassdoor_rating=3.8,
        )

        results = [
            ("KununuScraper", kununu_company),
            ("GlassdoorScraper", glassdoor_company),
        ]

        merged = scraper_manager._combined_scraper_results("SAP", results)

        # Should have all unique alternative names
        assert "SAP-SE" in merged.alternative_names
        assert "SAP SE" in merged.alternative_names
        assert "SAP GmbH" in merged.alternative_names
        assert len(merged.alternative_names) == 3

    def test_avoids_duplicate_alternative_names(self, scraper_manager):
        """Should not add duplicate alternative names"""
        kununu_company = Company(
            name="SAP SE",
            kununu_rating=4.0,
            alternative_names=["SAP SE"],  # Already has this name
        )

        glassdoor_company = Company(
            name="SAP SE",  # Same name again
            glassdoor_rating=3.8,
        )

        results = [
            ("KununuScraper", kununu_company),
            ("GlassdoorScraper", glassdoor_company),
        ]

        merged = scraper_manager._combined_scraper_results("SAP", results)

        assert merged.alternative_names.count("SAP SE") == 1

    def test_does_not_add_search_name_as_alternative(self, scraper_manager):
        scraped_company = Company(
            name="SAP",
            kununu_rating=4.0,
        )

        results = [("KununuScraper", scraped_company)]

        merged = scraper_manager._combined_scraper_results("SAP", results)

        assert merged.alternative_names == []


@pytest.fixture
def empty_orchestrator():
    return JobOrchestrator(
        job_query_port=None,
        job_command_port=None,
        company_query_port=None,
        company_command_port=None,
        company_scraper=CompanyScraperManager([KununuScraper, GlassdoorScraper]),
        job_scraper_port=None,
        company_blacklist_port=None,
        job_blacklist_port=None,
    )


class TestCompanyDataMerging:
    """Test company data merging with alternative names"""

    def test_combines_alternative_names_from_existing_and_scraped(
        self, empty_orchestrator
    ):
        """Should combine alternative names from both existing and scraped data"""

        existing = Company(
            name="SAP",
            alternative_names=["SAP AG"],
            kununu_rating=4.0,
        )

        scraped = Company(
            name="SAP",
            alternative_names=["SAP SE", "SAP GmbH"],
            kununu_rating=4.2,
        )

        merged = empty_orchestrator._company_scraper_port._merge_company_data(
            existing, scraped
        )

        # Should have all unique alternative names
        assert "SAP AG" in merged.alternative_names
        assert "SAP SE" in merged.alternative_names
        assert "SAP GmbH" in merged.alternative_names
        assert len(merged.alternative_names) == 3

    def test_avoids_duplicate_alternative_names_in_merge(self, empty_orchestrator):
        """Should not duplicate alternative names"""

        existing = Company(
            name="SAP",
            alternative_names=["SAP SE", "SAP AG"],
            kununu_rating=4.0,
        )

        scraped = Company(
            name="SAP",
            alternative_names=["SAP SE", "SAP GmbH"],  # "SAP SE" is duplicate
            glassdoor_rating=3.8,
        )

        merged = empty_orchestrator._company_scraper_port._merge_company_data(
            existing, scraped
        )

        # Should only have one instance of "SAP SE"
        assert merged.alternative_names.count("SAP SE") == 1
        assert "SAP AG" in merged.alternative_names
        assert "SAP GmbH" in merged.alternative_names

    def test_preserves_empty_alternative_names(self, empty_orchestrator):
        existing = Company(
            name="SAP",
            alternative_names=[],
            kununu_rating=4.0,
        )

        scraped = Company(
            name="SAP",
            alternative_names=[],
            glassdoor_rating=3.8,
        )

        merged = empty_orchestrator._company_scraper_port._merge_company_data(
            existing, scraped
        )

        assert merged.alternative_names == []

    def test_adds_scraped_alternative_names_when_existing_empty(
        self, empty_orchestrator
    ):
        """Should add scraped alternative names when existing has none"""

        existing = Company(
            name="SAP",
            alternative_names=[],
            kununu_rating=4.0,
        )

        scraped = Company(
            name="SAP",
            alternative_names=["SAP SE"],
            glassdoor_rating=3.8,
        )

        merged = empty_orchestrator._company_scraper_port._merge_company_data(
            existing, scraped
        )

        assert "SAP SE" in merged.alternative_names
        assert len(merged.alternative_names) == 1

    def test_merges_ratings_from_different_sources(self, empty_orchestrator):
        """Should preserve ratings from different sources"""

        existing = Company(
            name="SAP",
            kununu_rating=4.0,
            kununu_review_count=100,
        )

        scraped = Company(
            name="SAP",
            glassdoor_rating=3.8,
            glassdoor_review_count=200,
        )

        merged = empty_orchestrator._company_scraper_port._merge_company_data(
            existing, scraped
        )

        # Should have both ratings
        assert merged.kununu_rating == 4.0
        assert merged.kununu_review_count == 100
        assert merged.glassdoor_rating == 3.8
        assert merged.glassdoor_review_count == 200
