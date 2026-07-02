"""Разовый бэкфилл истории курсов НБКР (для спарклайнов 1г/5л).

Источник: официальный экспорт «Справка» https://www.nbkr.kg/fin_stat.xls
(бинарный .xls, Java Excel API; строки «DD.MM.YYYY | курс», курс указан
на каждый календарный день). Ежедневное обновление дальше делает
parse_nbkr_rates.py по daily.xml — этот скрипт запускается вручную один раз:

    python scripts/backfill_nbkr_rates.py [лет=5] [валюты через запятую=все]
"""

from __future__ import annotations

import re
import sys
import time
from datetime import date, datetime, timedelta

import requests
import xlrd

from common import DATA_DIR, build_payload, load_series, merge_series, validate_series, write_payload
from parse_nbkr_rates import CURRENCIES, MAX_GAP_DAYS, SOURCE_NAME, SOURCE_URL

FIN_STAT_URL = "https://www.nbkr.kg/fin_stat.xls"
# id валют из формы «Динамика официальных курсов» на nbkr.kg
VALUTA_IDS = {"USD": 15, "EUR": 20, "KZT": 40, "RUB": 44}

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")


def parse_fin_stat_xls(content: bytes) -> list[dict]:
    """Извлекает серию {date, value} из листа «Справка»."""
    sheet = xlrd.open_workbook(file_contents=content).sheet_by_index(0)
    points = []
    for r in range(sheet.nrows):
        row = [sheet.cell_value(r, c) for c in range(sheet.ncols)]
        texts = [v for v in row if isinstance(v, str) and DATE_RE.match(v.strip())]
        nums = [v for v in row if isinstance(v, float)]
        if len(texts) == 1 and len(nums) == 1:
            d = datetime.strptime(texts[0].strip(), "%d.%m.%Y").date().isoformat()
            points.append({"date": d, "value": round(nums[0], 4)})
    if not points:
        raise ValueError("в fin_stat.xls не найдено ни одной строки «дата | курс»")
    return sorted(points, key=lambda p: p["date"])


def fetch_history(valuta_id: int, beg: date, end: date) -> list[dict]:
    params = {
        "lang": "RUS",
        "valuta_id": valuta_id,
        "beg_day": f"{beg.day:02d}", "beg_month": f"{beg.month:02d}", "beg_year": beg.year,
        "end_day": f"{end.day:02d}", "end_month": f"{end.month:02d}", "end_year": end.year,
    }
    # сервер НБКР небыстрый и, похоже, троттлит частые запросы — ретраим с паузой
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.get(FIN_STAT_URL, params=params, timeout=90)
            resp.raise_for_status()
            return parse_fin_stat_xls(resp.content)
        except requests.RequestException as e:
            last_err = e
            time.sleep(10 * (attempt + 1))
    raise last_err


def main() -> None:
    years = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    wanted = sys.argv[2].upper().split(",") if len(sys.argv) > 2 else list(VALUTA_IDS)
    end = date.today()
    beg = end - timedelta(days=365 * years)

    for code, valuta_id in VALUTA_IDS.items():
        if code not in wanted:
            continue
        # запрашиваем по годовым кускам — не полагаемся на лимиты эндпоинта
        points: list[dict] = []
        chunk_beg = beg
        while chunk_beg < end:
            chunk_end = min(chunk_beg + timedelta(days=365), end)
            points = merge_series(points, fetch_history(valuta_id, chunk_beg, chunk_end))
            chunk_beg = chunk_end + timedelta(days=1)
            time.sleep(2)  # не долбим сервер

        metric = f"kgs_{code.lower()}"
        path = DATA_DIR / f"{metric}.json"
        # свежие точки из daily.xml имеют приоритет над бэкфиллом
        series = merge_series(points, load_series(path))
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
            data_date=series[-1]["date"],
            series=series,
        )
        write_payload(path, payload)
        print(f"{metric}: {len(series)} точек, {series[0]['date']} … {series[-1]['date']}")


if __name__ == "__main__":
    sys.exit(main())
