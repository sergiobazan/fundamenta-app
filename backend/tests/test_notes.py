import json

import pytest
from app.notes import (
    classify_note_topic,
    extract_notes_from_pages,
    load_note_sources,
    validate_source_payload,
)


def source_payload() -> dict:
    return {
        "source_key": "company-2025-consolidated",
        "company_rpj": "A20032",
        "fiscal_year": 2025,
        "period_code": "A",
        "scope": "consolidated",
        "language_code": "es",
        "document_name": "Estados financieros auditados.pdf",
        "source_url": "https://www.smv.gob.pe/document.pdf",
        "identity_tokens": ["Minsur", "31 de diciembre de 2025"],
    }


def test_source_requires_an_absolute_https_url() -> None:
    payload = source_payload()
    payload["source_url"] = "http://example.com/document.pdf"

    with pytest.raises(ValueError, match="HTTPS"):
        validate_source_payload(payload)


def test_source_file_rejects_duplicate_keys(tmp_path) -> None:
    path = tmp_path / "sources.json"
    path.write_text(json.dumps([source_payload(), source_payload()]), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicados"):
        load_note_sources(path)


@pytest.mark.parametrize(
    ("title", "topic"),
    [
        ("Obligaciones financieras", "debt"),
        ("Información por segmentos", "segments"),
        ("Propiedad, planta y equipo", "capex_assets"),
        ("Deterioro de activos", "impairment"),
        ("Provisiones por cierre de minas", "provisions_closure"),
        ("Compromisos y contingencias", "contingencies"),
        ("Transacciones con partes relacionadas", "related_parties"),
        ("Juicios y estimaciones contables significativas", "estimates"),
        ("Hechos posteriores", "subsequent_events"),
        ("Efectivo y equivalentes de efectivo", "other"),
    ],
)
def test_classifies_relevant_note_topics(title: str, topic: str) -> None:
    assert classify_note_topic(title) == topic


def test_extracts_sequential_notes_and_ignores_a_false_heading() -> None:
    pages = [
        "Portada",
        (
            "NOTAS A LOS ESTADOS FINANCIEROS CONSOLIDADOS\n"
            "1. Efectivo y equivalentes de efectivo\nContenido uno\n"
            "2. Cuentas por cobrar\nContenido dos"
        ),
        (
            "NOTAS A LOS ESTADOS FINANCIEROS CONSOLIDADOS\n"
            "3. Los presentes estados se preparan respecto del\n"
            "3. Juicios y estimaciones contables significativas\nContenido tres\n"
            "4. Propiedad, planta y equipo\nContenido cuatro"
        ),
        (
            "NOTAS A LOS ESTADOS FINANCIEROS CONSOLIDADOS\n"
            "5. Hechos posteriores\nContenido cinco"
        ),
    ]

    notes = extract_notes_from_pages(pages)

    assert [note.note_number for note in notes] == [1, 2, 3, 4, 5]
    assert notes[2].original_title == "Juicios y estimaciones contables significativas"
    assert notes[2].is_priority is True
    assert notes[2].start_page == 3
    assert notes[4].topic == "subsequent_events"
    assert "Contenido cinco" in notes[4].content_text
