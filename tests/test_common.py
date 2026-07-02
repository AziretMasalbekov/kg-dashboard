import pytest

from common import merge_series, validate_series


def s(*points):
    return [{"date": d, "value": v} for d, v in points]


def test_merge_dedupes_and_sorts():
    merged = merge_series(
        s(("2026-07-01", 1.0), ("2026-07-02", 2.0)),
        s(("2026-07-02", 2.5), ("2026-06-30", 0.5)),
    )
    assert merged == s(("2026-06-30", 0.5), ("2026-07-01", 1.0), ("2026-07-02", 2.5))


def test_validate_ok_with_weekend_gap():
    validate_series(
        s(("2026-07-03", 87.0), ("2026-07-06", 87.1)),  # пятница → понедельник
        min_value=30, max_value=300, max_gap_days=7,
    )


def test_validate_rejects_out_of_range():
    with pytest.raises(ValueError, match="вне диапазона"):
        validate_series(s(("2026-07-01", 0.0)), min_value=30, max_value=300, max_gap_days=7)


def test_validate_rejects_large_gap():
    with pytest.raises(ValueError, match="разрыв"):
        validate_series(
            s(("2026-06-01", 87.0), ("2026-07-01", 87.1)),
            min_value=30, max_value=300, max_gap_days=7,
        )


def test_validate_rejects_empty():
    with pytest.raises(ValueError, match="пустая"):
        validate_series([], min_value=0, max_value=1, max_gap_days=1)
