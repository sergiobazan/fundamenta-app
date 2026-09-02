from datetime import UTC, datetime, timedelta

from app.notes_jobs import monthly_slot, monthly_sync_due, retry_delay


def test_monthly_slot_uses_lima_calendar_month() -> None:
    utc_new_month = datetime(2026, 10, 1, 2, 0, tzinfo=UTC)

    assert monthly_slot(utc_new_month, "America/Lima") == "2026-09"


def test_monthly_sync_waits_until_configured_local_time() -> None:
    before = datetime(2026, 9, 1, 10, 59, tzinfo=UTC)
    at_time = datetime(2026, 9, 1, 11, 0, tzinfo=UTC)

    assert not monthly_sync_due(before, day=1, hour=6, timezone_name="America/Lima")
    assert monthly_sync_due(at_time, day=1, hour=6, timezone_name="America/Lima")


def test_retry_delay_is_exponential_and_capped() -> None:
    assert retry_delay(1) == timedelta(minutes=5)
    assert retry_delay(2) == timedelta(minutes=10)
    assert retry_delay(10) == timedelta(minutes=60)
