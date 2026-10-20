COUNTRIES = {
    "us": "USA", "ca": "Canada", "au": "Australia", "nz": "New Zealand", "ie": "Ireland",
    "nl": "Netherlands", "de": "Germany", "se": "Sweden", "it": "Italy", "fr": "France", "hk": "Hong Kong",
    "dk": "Denmark", "no": "Norway", "fi": "Finland", "ae": "UAE (Dubai)", "sg": "Singapore",
    "my": "Malaysia", "vn": "Vietnam",
}

CURRENCY = {
    "us": "USD", "ca": "CAD", "au": "AUD", "nz": "NZD", "ie": "EUR", "nl": "EUR",
    "de": "EUR", "se": "SEK", "it": "EUR", "fr": "EUR", "hk": "HKD",
    "dk": "DKK", "no": "NOK", "fi": "EUR", "ae": "AED", "sg": "SGD", "my": "MYR", "vn": "VND",
}

# Broad on purpose: we collect every seniority and classify entry-level later,
# otherwise we can't measure what share of the market is entry-level.
TERMS = [
    "data analyst", "business analyst", "business intelligence", "bi analyst", "analytics engineer",
    "insights analyst", "reporting analyst", "product analyst", "data scientist", "data engineer",
    "machine learning engineer", "ml engineer", "ai engineer",
]

# Local-language titles; English titles are already common in these markets.
LOCAL_TERMS = {
    "de": ["datenanalyst", "datenwissenschaftler", "dateningenieur"],
    "fr": ["analyste de données", "ingénieur données", "data analyste"],
    "it": ["analista dati"],
    "nl": ["data-analist", "data analist"],
    "se": ["dataanalytiker", "dataingenjör"],
    "dk": ["dataanalytiker", "dataingeniør"],
    "no": ["dataanalytiker", "dataingeniør"],
    "fi": ["data-analyytikko", "datainsinööri"],
    "my": ["penganalisis data"],
    "vn": ["phân tích dữ liệu", "kỹ sư dữ liệu"],
}


def terms_for(country):
    return TERMS + LOCAL_TERMS.get(country, [])
