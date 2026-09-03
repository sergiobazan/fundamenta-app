import json
from pathlib import Path

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


def test_project_catalog_has_two_consecutive_years_per_company() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "notes" / "sources.json"

    sources = load_note_sources(path)

    assert len(sources) == 8
    coverage = {(source.company_rpj, source.fiscal_year) for source in sources}
    assert coverage == {
        ("B20003", 2024),
        ("B20003", 2025),
        ("A20032", 2024),
        ("A20032", 2025),
        ("CM0001", 2024),
        ("CM0001", 2025),
        ("B20041", 2024),
        ("B20041", 2025),
    }


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
        ("Eventos posteriores a la fecha del estado consolidado", "subsequent_events"),
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


def test_recovers_known_note_three_heading_with_missing_number_glyph() -> None:
    pages = [
        """Notas a los estados financieros consolidados
1. Identificación y actividad económica
Contenido uno suficientemente extenso.
""",
        """Notas a los estados financieros consolidados
2. Bases de preparación y políticas contables
Contenido dos suficientemente extenso.
""",
        """Notas a los estados financieros consolidados
. Juicios, estimados y supuestos contables significativos
Contenido tres suficientemente extenso.
3.1. Juicios
Este subtítulo no debe crear otra nota.
""",
        """Notas a los estados financieros consolidados
4. Normas emitidas pero aún no efectivas
Contenido cuatro suficientemente extenso.
""",
        """Notas a los estados financieros consolidados
5. Transacciones en moneda extranjera
Contenido cinco suficientemente extenso.
""",
    ]

    notes = extract_notes_from_pages(pages)

    assert [note.note_number for note in notes] == [1, 2, 3, 4, 5]
    assert notes[2].original_title == "Juicios, estimados y supuestos contables significativos"


def test_extracts_undotted_uppercase_headings_without_matching_dates() -> None:
    pages = [
        """NOTAS A LOS ESTADOS FINANCIEROS CONSOLIDADOS
1 IDENTIFICACIÓN Y ACTIVIDAD ECONÓMICA
Contenido uno.
2 POLÍTICAS CONTABLES SIGNIFICATIVAS
Contenido dos.
""",
        """3 ESTIMADOS Y CRITERIOS CONTABLES
Contenido tres al 31 de diciembre de 2025.
4 EFECTIVO Y EQUIVALENTES AL EFECTIVO
Contenido cuatro.
5 HECHOS POSTERIORES
Contenido cinco.
""",
    ]

    notes = extract_notes_from_pages(pages)

    assert [note.note_number for note in notes] == [1, 2, 3, 4, 5]
    assert notes[2].original_title == "ESTIMADOS Y CRITERIOS CONTABLES"


def test_stops_the_last_note_before_a_supplementary_appendix() -> None:
    pages = [
        """NOTAS A LOS ESTADOS FINANCIEROS CONSOLIDADOS
1 PRIMERA NOTA
Contenido uno.
2 SEGUNDA NOTA
Contenido dos.
3 TERCERA NOTA
Contenido tres.
4 CUARTA NOTA
Contenido cuatro.
5 EVENTOS POSTERIORES
No ocurrieron otros eventos posteriores.
""",
        """Información Suplementaria - Recursos Minerales y Reservas
Esta página no pertenece a la nota cinco.
""",
    ]

    notes = extract_notes_from_pages(pages)

    assert notes[-1].note_number == 5
    assert notes[-1].end_page == 1
    assert "Información Suplementaria" not in notes[-1].content_text


def test_completes_a_financial_position_title_wrapped_by_the_pdf() -> None:
    pages = [
        """NOTAS A LOS ESTADOS FINANCIEROS CONSOLIDADOS
1 PRIMERA NOTA
Contenido uno.
2 SEGUNDA NOTA
Contenido dos.
3 TERCERA NOTA
Contenido tres.
4 CUARTA NOTA
Contenido cuatro.
5 EVENTOS POSTERIORES A LA FECHA DEL ESTADO CONSOLIDADO DE SITUACIÓN
FINANCIERA
No ocurrieron otros eventos posteriores.
""",
    ]

    notes = extract_notes_from_pages(pages)

    assert notes[-1].original_title.endswith("SITUACIÓN FINANCIERA")
    assert notes[-1].content_text.startswith("No ocurrieron")
