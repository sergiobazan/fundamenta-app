import pytest
from app.events import event_payload_sha256, validate_event_payload


def sample_event() -> dict:
    return {
        "company_rpj": "A20032",
        "source_provider": "smv",
        "external_id": "event-1",
        "category": "dividends",
        "title": "Distribución de dividendos",
        "summary": "El directorio acordó una distribución de dividendos.",
        "published_at": "2026-05-11T13:49:06-05:00",
        "effective_date": "2026-06-19",
        "source_url": "https://www.smv.gob.pe/documento.pdf",
    }


def test_event_payload_is_normalized_and_hash_is_stable() -> None:
    first = validate_event_payload(sample_event())
    second = validate_event_payload(dict(reversed(list(sample_event().items()))))
    assert first["published_at"] == "2026-05-11T13:49:06-05:00"
    assert event_payload_sha256(first) == event_payload_sha256(second)


def test_event_requires_supported_category_and_https_source() -> None:
    invalid_category = sample_event() | {"category": "recommendation"}
    with pytest.raises(ValueError, match="Categoría no soportada"):
        validate_event_payload(invalid_category)

    invalid_url = sample_event() | {"source_url": "http://example.com/event"}
    with pytest.raises(ValueError, match="HTTPS"):
        validate_event_payload(invalid_url)


def test_event_requires_timezone() -> None:
    payload = sample_event() | {"published_at": "2026-05-11T13:49:06"}
    with pytest.raises(ValueError, match="zona horaria"):
        validate_event_payload(payload)
