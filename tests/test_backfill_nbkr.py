import pytest

from backfill_nbkr_rates import parse_fin_stat_xls
from conftest import FIXTURES


def test_parses_history_from_real_sample():
    # Реальный ответ fin_stat.xls (USD, 25.06–02.07.2026) от 2026-07-02
    content = (FIXTURES / "nbkr" / "fin_stat_usd_sample.xls").read_bytes()
    points = parse_fin_stat_xls(content)
    assert len(points) == 8
    assert points[0] == {"date": "2026-06-25", "value": 87.45}
    assert points[-1] == {"date": "2026-07-02", "value": 87.45}
    # серия отсортирована и без дубликатов
    dates = [p["date"] for p in points]
    assert dates == sorted(set(dates))


def test_garbage_content_raises():
    with pytest.raises(Exception):
        parse_fin_stat_xls(b"not an xls at all")
