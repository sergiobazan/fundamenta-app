from app.bootstrap import is_bootstrap_complete


def complete_status() -> dict[str, int]:
    return {
        "companies": 2,
        "filings": 6,
        "facts": 300,
        "computed_metrics": 30,
        "unavailable_metrics": 0,
        "failed_validations": 0,
        "events": 4,
        "note_documents": 2,
        "notes": 10,
    }


def test_bootstrap_status_requires_every_initial_dataset() -> None:
    assert is_bootstrap_complete(complete_status(), expected_events=4, expected_note_sources=2)


def test_bootstrap_status_is_incomplete_when_one_dataset_is_missing() -> None:
    for field in (
        "companies",
        "filings",
        "facts",
        "computed_metrics",
        "events",
        "note_documents",
        "notes",
    ):
        status = complete_status()
        status[field] -= 1
        assert not is_bootstrap_complete(status, expected_events=4, expected_note_sources=2)

    for field in ("unavailable_metrics", "failed_validations"):
        status = complete_status()
        status[field] = 1
        assert not is_bootstrap_complete(status, expected_events=4, expected_note_sources=2)
