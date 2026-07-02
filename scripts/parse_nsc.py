"""Открытые данные НСК КР (stat.gov.kg), годовые показатели.

Источник: https://stat.gov.kg/ru/opendata/category/<id>/json — единый формат:
{"data": [{"title_ru", "title_kg", "title_en", "values": [{"key": год, "value": число}]}]}
Строки — регионы (или показатели, как в категории 316). Единицы измерения
взяты из официальных Excel-файлов тех же категорий (в JSON их нет).

Пишет data/nsc_<slug>.json: series — ряд по Кыргызской Республике для карточки,
regions — все строки датасета для страниц деталей.

Лицензия данных: CC BY-NC-SA 4.0, атрибуция НСК КР обязательна.
"""

from __future__ import annotations

import sys

import requests

from common import DATA_DIR, build_payload, write_payload

BASE = "https://stat.gov.kg"
SOURCE_NAME = "Национальный статистический комитет Кыргызской Республики"

# slug → категория открытых данных НСК.
# kr_row: точное title_ru строки с республиканским значением (или его префикс).
# min/max — правдоподобные диапазоны для валидации.
CATEGORIES = {
    "nsc_cpi": {
        "id": 127,
        "unit": "% к предыдущему году",
        "kr_row": "Кыргызская Республика",
        "min": 50.0,
        "max": 200.0,
    },
    "nsc_wage": {
        "id": 112,
        "unit": "сомов",
        "kr_row": "Кыргызская Республика",
        "min": 1000.0,
        "max": 500000.0,
    },
    "nsc_unemployment": {
        "id": 113,
        "unit": "%",
        "kr_row": "Кыргызская Республика",
        "min": 0.0,
        "max": 50.0,
    },
    "nsc_poverty": {
        "id": 120,
        "unit": "%",
        "kr_row": "Кыргызская Республика",
        "min": 0.0,
        "max": 80.0,
    },
    "nsc_subsistence": {
        "id": 119,
        "unit": "сомов в месяц",
        "kr_row": "Кыргызская Республика",
        "min": 1000.0,
        "max": 100000.0,
    },
    "nsc_population": {
        "id": 316,
        "unit": "тыс. человек",
        "kr_row": "Численность населения на начало года",
        "min": 4000.0,
        "max": 15000.0,
    },
}


def to_series(values: list[dict]) -> list[dict]:
    """values НСК → отсортированная серия {date: 'YYYY', value}; None-значения
    (ещё не опубликованные годы) отбрасываются."""
    points = [
        {"date": str(v["key"]), "value": float(v["value"])}
        for v in values
        if v["value"] is not None
    ]
    return sorted(points, key=lambda p: p["date"])


def validate_annual(series: list[dict], *, min_value: float, max_value: float) -> None:
    """Годовой аналог common.validate_series: диапазон + непрерывность лет."""
    if not series:
        raise ValueError("пустая серия")
    years = [int(p["date"]) for p in series]
    if years != sorted(set(years)):
        raise ValueError("годы не отсортированы или дублируются")
    for p in series:
        if not (min_value <= p["value"] <= max_value):
            raise ValueError(
                f"{p['date']}: значение {p['value']!r} вне диапазона [{min_value}, {max_value}]"
            )
    for prev, cur in zip(years, years[1:]):
        if cur - prev != 1:
            raise ValueError(f"пропущен год между {prev} и {cur}")


def parse_category(slug: str, cfg: dict, raw: dict) -> dict:
    """JSON категории НСК → payload метрики."""
    rows = raw["data"]
    kr_rows = [r for r in rows if r["title_ru"].strip().startswith(cfg["kr_row"])]
    if len(kr_rows) != 1:
        raise ValueError(
            f"{slug}: ожидалась одна строка «{cfg['kr_row']}», найдено {len(kr_rows)}"
        )
    series = to_series(kr_rows[0]["values"])
    validate_annual(series, min_value=cfg["min"], max_value=cfg["max"])

    regions = [
        {
            "name_ru": r["title_ru"].strip(),
            "name_ky": r["title_kg"].strip(),
            "name_en": r["title_en"].strip(),
            "series": to_series(r["values"]),
        }
        for r in rows
    ]

    payload = build_payload(
        metric=slug,
        unit=cfg["unit"],
        source_name=SOURCE_NAME,
        source_url=f"{BASE}/ru/opendata/category/{cfg['id']}/",
        data_date=series[-1]["date"],
        series=series,
    )
    payload["regions"] = regions
    return payload


def main() -> None:
    for slug, cfg in CATEGORIES.items():
        resp = requests.get(f"{BASE}/ru/opendata/category/{cfg['id']}/json", timeout=90)
        resp.raise_for_status()
        payload = parse_category(slug, cfg, resp.json())
        write_payload(DATA_DIR / f"{slug}.json", payload)
        last = payload["series"][-1]
        print(f"{slug}: {last['value']} ({last['date']}), строк: {len(payload['regions'])}")


if __name__ == "__main__":
    sys.exit(main())
