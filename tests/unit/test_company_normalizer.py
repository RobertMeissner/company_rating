from src.domain.value_objects.company import Company
from src.utils.company_name_normalizer import normalized_company_name


class TestCompanyNameNormalizer:

    def test_basic_normalization(self):
        company_name = "Robert For Present"
        company = Company(name=company_name, alternative_names=["rfp"])
        assert set(normalized_company_name(company)) == {"robert-for-present", "rfp"}

    def test_unnecessary_whitespace(self):
        company_name = "  Robert For Present  "
        company = Company(name=company_name)
        assert normalized_company_name(company) == ["robert-for-present"]
