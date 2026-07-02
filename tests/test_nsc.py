import json

import pytest

from conftest import FIXTURES
from parse_nsc import CATEGORIES, parse_category, to_series, validate_annual

# Реальные ответы stat.gov.kg /ru/opendata/category/<id>/json от 2026-07-02
FIXTURE_FILES = {
    "nsc_cpi": "127_cpi.json",
    "nsc_wage": "112_wage.json",
    "nsc_unemployment": "113_unemployment.json",
    "nsc_poverty": "120_poverty.json",
    "nsc_subsistence": "119_subsistence.json",
    "nsc_population": "316_population.json",
}


def load(slug):
    return json.loads((FIXTURES / "nsc" / FIXTURE_FILES[slug]).read_text())


@pytest.mark.parametrize("slug", list(CATEGORIES))
def test_all_categories_parse(slug):
    payload = parse_category(slug, CATEGORIES[slug], load(slug))
    assert payload["metric"] == slug
    assert payload["series"], "серия по КР не должна быть пустой"
    assert payload["regions"]
    assert payload["data_date"] == payload["series"][-1]["date"]


def test_known_values():
    cpi = parse_category("nsc_cpi", CATEGORIES["nsc_cpi"], load("nsc_cpi"))
    assert {"date": "2024", "value": 105.0} in cpi["series"]

    wage = parse_category("nsc_wage", CATEGORIES["nsc_wage"], load("nsc_wage"))
    assert wage["series"][-1] == {"date": "2024", "value": 36047.0}

    pop = parse_category("nsc_population", CATEGORIES["nsc_population"], load("nsc_population"))
    assert pop["series"][-1] == {"date": "2025", "value": 7281.8}


def test_none_values_dropped():
    # в 316 у «Число родившихся» за 2025 стоит null — не должен попасть в серию
    raw = load("nsc_population")
    births = next(r for r in raw["data"] if r["title_ru"].startswith("Число родившихся"))
    series = to_series(births["values"])
    assert all(p["value"] is not None for p in series)
    assert "2025" not in [p["date"] for p in series]


def test_validate_annual_rejects_year_gap():
    with pytest.raises(ValueError, match="пропущен год"):
        validate_annual(
            [{"date": "2020", "value": 1.0}, {"date": "2022", "value": 1.0}],
            min_value=0, max_value=10,
        )


def test_missing_kr_row_raises():
    raw = {"data": [{"title_ru": "Баткенская область", "title_kg": "", "title_en": "",
                     "values": [{"key": 2024, "value": 1.0}]}]}
    with pytest.raises(ValueError, match="ожидалась одна строка"):
        parse_category("nsc_cpi", CATEGORIES["nsc_cpi"], raw)
