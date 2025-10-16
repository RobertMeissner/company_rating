import pytest

from src.application.services.job_orchestrator import JobOrchestrator
from src.domain.value_objects.company import Company
from src.infrastructure.scrapers.company_scraper_manager import (
    CompanyScraperManager,
)
from src.infrastructure.scrapers.glassdoor_scraper import GlassdoorScraper
from src.infrastructure.scrapers.kununu_scraper import KununuScraper
from src.models.scraper_model import SCRAPERS


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
        results = {
            SCRAPERS.KUNUNU: kununu_company_full,
            SCRAPERS.GLASSDOOR: glassdoor_company_full,
        }

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

        results = {
            SCRAPERS.KUNUNU: kununu_with_wrong_glassdoor,
            SCRAPERS.GLASSDOOR: glassdoor_company_full,
        }

        merged = scraper_manager._combined_scraper_results("Test Company", results)

        assert merged.kununu_rating == 4.2
        assert merged.glassdoor_rating == 4.0

    def test_merge_fills_gaps_from_both_sources(
        self, kununu_company_partial, glassdoor_company_partial, scraper_manager
    ):
        results = {
            SCRAPERS.KUNUNU: kununu_company_partial,
            SCRAPERS.GLASSDOOR: glassdoor_company_partial,
        }

        merged = scraper_manager._combined_scraper_results("Test Company", results)

        # Should have both ratings
        assert merged.kununu_rating == 3.5
        assert merged.glassdoor_rating == 3.8

        # Should have website from Kununu (only source)
        assert merged.website == "https://test-company.com"

    def test_merge_handles_empty_results(self, empty_company, scraper_manager):
        results = {
            SCRAPERS.KUNUNU: empty_company,
            SCRAPERS.GLASSDOOR: empty_company,
        }

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

        results = {
            SCRAPERS.KUNUNU: kununu_company_full,
            SCRAPERS.GLASSDOOR: empty_glassdoor,
        }

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
        merged = scraper_manager._combined_scraper_results("Test Company", {})

        assert merged.name == "Test Company"
        assert merged.kununu_rating is None

    def test_merge_with_single_result(self, kununu_company_full, scraper_manager):
        """Should handle merging with only one scraper result"""

        results = {SCRAPERS.KUNUNU: kununu_company_full}

        merged = scraper_manager._combined_scraper_results("Test Company", results)

        assert merged.kununu_rating == 4.2
        assert merged.kununu_review_count == 150

    def test_merge_preserves_company_name(self, kununu_company_full, scraper_manager):
        wrong_name_company = Company(
            name="Different Name",
            kununu_rating=4.0,
        )

        results = {SCRAPERS.KUNUNU: wrong_name_company}

        merged = scraper_manager._combined_scraper_results("Correct Name", results)

        assert merged.name == "Correct Name"

    def test_merge_with_alternative_names(self, scraper_manager):
        """Should handle companies with scraper_identifiers"""

        company_with_alternatives = Company(
            name="Test Company",
            scraper_identifiers={SCRAPERS.KUNUNU.value: "Test Corp"},
            kununu_rating=4.0,
        )

        results = {SCRAPERS.KUNUNU: company_with_alternatives}

        merged = scraper_manager._combined_scraper_results("Test Company", results)

        assert merged.scraper_identifiers == {
            SCRAPERS.GLASSDOOR.value: "Test Company",
            SCRAPERS.KUNUNU.value: "Test Company",
        }
        assert merged.kununu_rating == 4.0


class TestScraperIdentifiers:
    """Test capturing scraped names in scraper_identifiers dict"""

    def test_captures_scraped_names_from_each_scraper(self, scraper_manager):
        """Should capture company name from each scraper separately"""
        kununu_company = Company(
            name="SAP SE",  # Kununu returns this
            kununu_rating=4.0,
        )

        glassdoor_company = Company(
            name="SAP Inc",  # Glassdoor returns this
            glassdoor_rating=3.8,
        )

        results = {
            SCRAPERS.KUNUNU: kununu_company,
            SCRAPERS.GLASSDOOR: glassdoor_company,
        }

        merged = scraper_manager._combined_scraper_results("SAP", results)

        # Should preserve our search name
        assert merged.name == "SAP"
        # Should capture each scraper's name separately
        assert merged.scraper_identifiers[SCRAPERS.KUNUNU.value] == "SAP SE"
        assert merged.scraper_identifiers[SCRAPERS.GLASSDOOR.value] == "SAP Inc"
        assert len(merged.scraper_identifiers) == 2

    def test_captures_scraper_identifier_with_single_scraper(self, scraper_manager):
        """Should handle single scraper result"""
        kununu_company = Company(
            name="SAP SE",
            kununu_rating=4.0,
        )

        results = {SCRAPERS.KUNUNU: kununu_company}

        merged = scraper_manager._combined_scraper_results("SAP", results)

        # Should preserve our search name
        assert merged.name == "SAP"
        # Should have kununu identifier
        assert merged.scraper_identifiers[SCRAPERS.KUNUNU.value] == "SAP SE"
        # Should have fallback for glassdoor (not scraped)
        assert merged.scraper_identifiers[SCRAPERS.GLASSDOOR.value] == "SAP"

    def test_each_scraper_has_own_identifier(self, scraper_manager):
        """Each scraper should have exactly one identifier"""
        kununu_company = Company(
            name="SAP-SE",  # Kununu format with hyphen
            kununu_rating=4.0,
        )

        glassdoor_company = Company(
            name="SAP SE",  # Glassdoor format with space
            glassdoor_rating=3.8,
        )

        results = {
            SCRAPERS.KUNUNU: kununu_company,
            SCRAPERS.GLASSDOOR: glassdoor_company,
        }

        merged = scraper_manager._combined_scraper_results("SAP", results)

        # Each scraper has its own unique identifier
        assert merged.scraper_identifiers[SCRAPERS.KUNUNU.value] == "SAP-SE"
        assert merged.scraper_identifiers[SCRAPERS.GLASSDOOR.value] == "SAP SE"
        # No conflicts - each scraper gets its own key
        assert len(merged.scraper_identifiers) == 2

    def test_uses_search_name_when_scraper_returns_same_name(self, scraper_manager):
        """When scraped name matches search name, still capture it"""
        kununu_company = Company(
            name="SAP",  # Same as search term
            kununu_rating=4.0,
        )

        glassdoor_company = Company(
            name="SAP",  # Same as search term
            glassdoor_rating=3.8,
        )

        results = {
            SCRAPERS.KUNUNU: kununu_company,
            SCRAPERS.GLASSDOOR: glassdoor_company,
        }

        merged = scraper_manager._combined_scraper_results("SAP", results)

        # Should still capture identifiers even if they match search name
        assert merged.scraper_identifiers[SCRAPERS.KUNUNU.value] == "SAP"
        assert merged.scraper_identifiers[SCRAPERS.GLASSDOOR.value] == "SAP"
        assert len(merged.scraper_identifiers) == 2


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
    """Test company data merging with scraper identifiers"""

    def test_combines_scraper_identifiers_from_existing_and_scraped(
        self, empty_orchestrator
    ):
        """Should combine scraper identifiers from both existing and scraped data"""

        existing = Company(
            name="SAP",
            scraper_identifiers={SCRAPERS.KUNUNU.value: "SAP AG"},
            kununu_rating=4.0,
        )

        scraped = Company(
            name="SAP",
            scraper_identifiers={
                SCRAPERS.KUNUNU.value: "SAP SE",
                SCRAPERS.GLASSDOOR.value: "SAP GmbH",
            },
            kununu_rating=4.2,
        )

        merged = empty_orchestrator._company_scraper_port._merge_company_data(
            existing, scraped
        )

        # Should have scraped data overwrite existing for same scraper
        assert merged.scraper_identifiers[SCRAPERS.KUNUNU.value] == "SAP SE"
        assert merged.scraper_identifiers[SCRAPERS.GLASSDOOR.value] == "SAP GmbH"
        assert merged.kununu_rating == 4.2
        assert len(merged.scraper_identifiers) == 2

    def test_scraped_identifiers_overwrite_existing_for_same_scraper(
        self, empty_orchestrator
    ):
        """Should overwrite existing scraper identifiers when rescraped"""

        existing = Company(
            name="SAP",
            scraper_identifiers={
                SCRAPERS.KUNUNU.value: "SAP AG",
                SCRAPERS.GLASSDOOR.value: "SAP Inc",
            },
            kununu_rating=4.0,
        )

        scraped = Company(
            name="SAP",
            scraper_identifiers={
                SCRAPERS.KUNUNU.value: "SAP SE"
            },  # Updated kununu identifier
            glassdoor_rating=3.8,
        )

        merged = empty_orchestrator._company_scraper_port._merge_company_data(
            existing, scraped
        )

        # Scraped kununu identifier should overwrite existing
        assert merged.scraper_identifiers[SCRAPERS.KUNUNU.value] == "SAP SE"
        # Existing glassdoor identifier should be preserved
        assert merged.scraper_identifiers[SCRAPERS.GLASSDOOR.value] == "SAP Inc"

    def test_preserves_empty_scraper_identifiers(self, empty_orchestrator):
        existing = Company(
            name="SAP",
            scraper_identifiers={},
            kununu_rating=4.0,
        )

        scraped = Company(
            name="SAP",
            scraper_identifiers={},
            glassdoor_rating=3.8,
        )

        merged = empty_orchestrator._company_scraper_port._merge_company_data(
            existing, scraped
        )

        assert merged.scraper_identifiers == {}

    def test_adds_scraped_identifiers_when_existing_empty(self, empty_orchestrator):
        """Should add scraped identifiers when existing has none"""

        existing = Company(
            name="SAP",
            scraper_identifiers={},
            kununu_rating=4.0,
        )

        scraped = Company(
            name="SAP",
            scraper_identifiers={SCRAPERS.KUNUNU.value: "SAP SE"},
            glassdoor_rating=3.8,
        )

        merged = empty_orchestrator._company_scraper_port._merge_company_data(
            existing, scraped
        )

        assert merged.scraper_identifiers[SCRAPERS.KUNUNU.value] == "SAP SE"
        assert len(merged.scraper_identifiers) == 1

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

    def test_replace_none_rating(self, empty_orchestrator):
        """Should replace None rating with scraped rating"""

        existing = Company(
            name="SAP",
            scraper_identifiers={SCRAPERS.KUNUNU.value: "SAP AG"},
            kununu_rating=None,
        )

        scraped = Company(
            name="SAP",
            scraper_identifiers={
                SCRAPERS.KUNUNU.value: "SAP SE",
                SCRAPERS.GLASSDOOR.value: "SAP GmbH",
            },
            kununu_rating=4.2,
        )

        merged = empty_orchestrator._company_scraper_port._merge_company_data(
            existing, scraped
        )

        # Should replace None rating with scraped rating
        assert merged.kununu_rating == 4.2
        # Should have both scraper identifiers
        assert merged.scraper_identifiers[SCRAPERS.KUNUNU.value] == "SAP SE"
        assert merged.scraper_identifiers[SCRAPERS.GLASSDOOR.value] == "SAP GmbH"
        assert len(merged.scraper_identifiers) == 2
