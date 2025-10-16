from src.utils.company_name_normalizer import normalized_company_name


class TestCompanyNameNormalizer:

    def test_basic_normalization(self):
        company_name = "Robert For Present"
        assert normalized_company_name(company_name) == "robert-for-present"

    def test_unnecessary_whitespace(self):
        company_name = "  Robert For Present  "
        assert normalized_company_name(company_name) == "robert-for-present"
