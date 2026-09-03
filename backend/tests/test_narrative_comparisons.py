from app.narrative_comparisons import match_notes, title_similarity


def _note(
    note_id: int, number: int, title: str, topic: str = "other"
) -> dict[str, object]:
    return {
        "id": note_id,
        "note_number": number,
        "original_title": title,
        "topic": topic,
        "is_priority": topic != "other",
        "cited_summary_id": note_id + 100,
        "observed_facts": 2,
    }


def test_title_similarity_normalizes_accents_and_revenue_aliases() -> None:
    assert title_similarity("Situación tributaria", "Situacion tributaria") == 1
    assert title_similarity("Ventas netas", "Ingresos de actividades ordinarias") >= 0.8


def test_matches_hechos_and_eventos_posteriores_as_the_same_disclosure() -> None:
    current = [
        _note(
            1,
            38,
            "Eventos posteriores a la fecha del estado consolidado de situación financiera",
            "subsequent_events",
        )
    ]
    previous = [_note(11, 39, "Hechos posteriores", "subsequent_events")]

    matches = match_notes(current, previous)

    assert len(matches) == 1
    assert matches[0].status == "matched"
    assert matches[0].score >= 0.85


def test_matches_shifted_note_numbers_by_title() -> None:
    current = [
        _note(1, 14, "Provisiones", "provisions_closure"),
        _note(2, 15, "Obligaciones financieras", "debt"),
    ]
    previous = [
        _note(11, 15, "Provisiones", "provisions_closure"),
        _note(12, 16, "Obligaciones financieras", "debt"),
    ]

    matches = match_notes(current, previous)

    assert [(match.current["id"], match.previous["id"]) for match in matches] == [
        (1, 11),
        (2, 12),
    ]
    assert all(match.method == "normalized_title" for match in matches)


def test_keeps_unmatched_notes_visible_instead_of_inventing_an_equivalence() -> None:
    current = [_note(1, 38, "Hechos posteriores", "subsequent_events")]

    matches = match_notes(current, [])

    assert len(matches) == 1
    assert matches[0].status == "current_only"
    assert matches[0].previous is None
    assert matches[0].confidence == "low"
