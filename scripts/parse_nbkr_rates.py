"""Официальные курсы НБКР (USD/EUR/RUB/KZT к сому), ежедневно.

Источник: https://www.nbkr.kg/XML/daily.xml (windows-1251, десятичная запятая,
дата DD.MM.YYYY — дата, на которую действует курс). Формат описан НБКР в
https://www.nbkr.kg/docs/xml_desc_ru.rtf

Пишет data/kgs_<валюта>.json, дописывая точку к существующей серии.
Любая ошибка сети/формата/валидации → исключение → non-zero exit.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from common import (
    DATA_DIR,
    build_payload,
    load_series,
    merge_series,
    validate_series,
    write_payload,
)

DAILY_XML_URL = "https://www.nbkr.kg/XML/daily.xml"
SOURCE_NAME = "Национальный банк Кыргызской Республики"
# Человекочитаемая страница официальных курсов — для ссылки «Источник» в UI
SOURCE_URL = "https://www.nbkr.kg/index1.jsp?item=1562&lang=RUS"

# Правдоподобные диапазоны (сом за единицу валюты) — щедрые, чтобы не давать
# ложных тревог, но отсекать мусор вроде 0 или перепутанных полей.
CURRENCIES = {
    "USD": {"min": 30.0, "max": 300.0},
    "EUR": {"min": 30.0, "max": 400.0},
    "RUB": {"min": 0.2, "max": 5.0},
    "KZT": {"min": 0.02, "max": 1.0},
}
# Курсы устанавливаются по рабочим дням: разрывы на выходные/праздники нормальны.
MAX_GAP_DAYS = 7


def parse_daily_xml(content: bytes) -> tuple[str, dict[str, float]]:
    """Разбирает daily.xml → (ISO-дата, {ISO-код: курс за 1 единицу})."""
    root = ET.fromstring(content)  # кодировку берёт из XML-декларации
    data_date = datetime.strptime(root.attrib["Date"], "%d.%m.%Y").date().isoformat()
    rates: dict[str, float] = {}
    for cur in root.iter("Currency"):
        code = cur.attrib["ISOCode"]
        if code not in CURRENCIES:
            continue
        nominal = int(cur.findtext("Nominal").strip())
        value = float(cur.findtext("Value").strip().replace(",", "."))
        rates[code] = round(value / nominal, 4)
    missing = set(CURRENCIES) - set(rates)
    if missing:
        raise ValueError(f"в daily.xml нет валют: {sorted(missing)}")
    return data_date, rates


def main() -> None:
    resp = requests.get(DAILY_XML_URL, timeout=30)
    resp.raise_for_status()
    data_date, rates = parse_daily_xml(resp.content)

    for code, value in rates.items():
        metric = f"kgs_{code.lower()}"
        path = DATA_DIR / f"{metric}.json"
        series = merge_series(load_series(path), [{"date": data_date, "value": value}])
        validate_series(
            series,
            min_value=CURRENCIES[code]["min"],
            max_value=CURRENCIES[code]["max"],
            max_gap_days=MAX_GAP_DAYS,
        )
        payload = build_payload(
            metric=metric,
            unit=f"сом за 1 {code}",
            source_name=SOURCE_NAME,
            source_url=SOURCE_URL,
            data_date=data_date,
            series=series,
        )
        write_payload(path, payload)
        print(f"{metric}: {value} ({data_date}), точек в серии: {len(series)}")


if __name__ == "__main__":
    sys.exit(main())
