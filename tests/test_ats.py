import db
from collectors.ats import country_of, wanted_title, _row


def test_country_of():
    assert country_of("Dubai") == "ae"
    assert country_of("Remote - Canada") == "ca"
    assert country_of("Berlin, Germany") == "de"
    assert country_of("Singapore") == "sg"
    assert country_of("Paris, France") == "fr"
    assert country_of("Remote") is None
    assert country_of("London, United Kingdom") is None
    assert country_of("Paris, Texas / Dublin") is None  # two countries: ambiguous, dropped
    assert country_of("Indiana") is None  # "ny"/"us" must not match inside words


def test_wanted_title_and_row_saves():
    assert wanted_title("Senior Data Engineer") and not wanted_title("Account Executive")
    r = _row("lever", "acme", "Acme", {"id": 1}, 1, "Data Analyst", "Dubai", "d", None, "u", None)
    assert r["country"] == "ae" and _row("lever", "acme", "Acme", {}, 2, "Chef", "Dubai", "d", None, "u", None) is None
    con = db.connect(":memory:")
    assert db.upsert(con, [r]) == 1
