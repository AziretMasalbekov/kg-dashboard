import pytest

from conftest import FIXTURES
from parse_nbkr_rates import parse_daily_xml


@pytest.fixture(scope="module")
def daily_xml() -> bytes:
    # Реальный ответ https://www.nbkr.kg/XML/daily.xml от 2026-07-02
    return (FIXTURES / "nbkr" / "daily.xml").read_bytes()


def test_parses_date(daily_xml):
    data_date, _ = parse_daily_xml(daily_xml)
    assert data_date == "2026-07-03"


def test_parses_all_four_currencies(daily_xml):
    _, rates = parse_daily_xml(daily_xml)
    assert rates == {
        "USD": 87.45,
        "EUR": 99.8679,
        "RUB": 1.1239,
        "KZT": 0.1842,
    }


def test_missing_currency_raises():
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CurrencyRates Name="Daily Exchange Rates" Date="03.07.2026">'
        "<Currency ISOCode=\"USD\"><Nominal>1</Nominal><Value>87,45</Value></Currency>"
        "</CurrencyRates>"
    ).encode()
    with pytest.raises(ValueError, match="EUR"):
        parse_daily_xml(xml)
