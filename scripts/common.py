"""Общие помощники ETL: единая схема, валидация, чтение/запись JSON.

Схема данных (одна на все метрики, см. CLAUDE.md):
{metric, unit, source_name, source_url, fetched_at, data_date,
 series: [{date, value}]}
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_payload(
    metric: str,
    unit: str,
    source_name: str,
    source_url: str,
    data_date: str,
    series: list[dict],
) -> dict:
    """Собирает JSON-документ метрики; fetched_at проставляется сейчас (UTC)."""
    return {
        "metric": metric,
        "unit": unit,
        "source_name": source_name,
        "source_url": source_url,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_date": data_date,
        "series": series,
    }


def merge_series(existing: list[dict], new_points: list[dict]) -> list[dict]:
    """Объединяет серии по дате (новые значения перекрывают старые), сортирует."""
    by_date = {p["date"]: p["value"] for p in existing}
    for p in new_points:
        by_date[p["date"]] = p["value"]
    return [{"date": d, "value": by_date[d]} for d in sorted(by_date)]


def validate_series(
    series: list[dict],
    *,
    min_value: float,
    max_value: float,
    max_gap_days: int,
) -> None:
    """Проверяет правдоподобность значений и отсутствие разрывов дат.

    Бросает ValueError — вызывающий скрипт падает с non-zero exit,
    CI краснеет, сайт остаётся на последнем валидном JSON.
    """
    if not series:
        raise ValueError("пустая серия")
    dates = [date.fromisoformat(p["date"]) for p in series]
    if dates != sorted(dates):
        raise ValueError("серия не отсортирована по дате")
    if len(set(dates)) != len(dates):
        raise ValueError("дубликаты дат в серии")
    for p in series:
        v = p["value"]
        if not isinstance(v, (int, float)) or not (min_value <= v <= max_value):
            raise ValueError(
                f"{p['date']}: значение {v!r} вне диапазона [{min_value}, {max_value}]"
            )
    for prev, cur in zip(dates, dates[1:]):
        gap = (cur - prev).days
        if gap > max_gap_days:
            raise ValueError(f"разрыв {gap} дн. между {prev} и {cur} (макс. {max_gap_days})")


def load_series(path: Path) -> list[dict]:
    """Читает series из существующего JSON метрики; [] если файла ещё нет."""
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["series"]


def write_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
