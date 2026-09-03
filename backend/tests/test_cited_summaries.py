from datetime import date

from app.cited_summaries import information_cutoff, select_summary_evidence


def test_selects_narrative_facts_and_keeps_their_citations() -> None:
    fragments = [
        {
            "id": 10,
            "page_number": 40,
            "fragment_order": 0,
            "content_text": """
                2025 2024 US$(000) US$(000) Saldo 1,087,946 1,087,919
                __________ __________ 299,263 498,101 297,573 491,110
            """,
        },
        {
            "id": 11,
            "page_number": 41,
            "fragment_order": 1,
            "content_text": """
                Al 31 de diciembre de 2025, la subsidiaria cumplió con las restricciones
                financieras de los contratos suscritos. La subsidiaria firmó un préstamo
                por US$300,000,000 para amortizar obligaciones anteriores y mantuvo una
                tasa variable vinculada a SOFR.
            """,
        },
        {
            "id": 12,
            "page_number": 42,
            "fragment_order": 2,
            "content_text": """
                Los bonos restringen determinadas transacciones, pero no exigen mantener
                ratios financieros ni niveles específicos de liquidez. El pagaré bancario
                por US$100,000,000 fue cancelado al vencimiento durante diciembre de 2025.
            """,
        },
    ]

    selected = select_summary_evidence(fragments, topic="debt", fiscal_year=2025)

    assert len(selected) == 3
    assert {item.source_fragment_id for item in selected} == {11, 12}
    assert all(item.page_number in {41, 42} for item in selected)
    assert all("__________" not in item.statement_text for item in selected)


def test_discards_sentences_that_look_like_investment_advice() -> None:
    fragments = [
        {
            "id": 1,
            "page_number": 1,
            "fragment_order": 0,
            "content_text": (
                "El documento indica que se deben comprar acciones como inversión para "
                "obtener un rendimiento futuro asegurado."
            ),
        }
    ]

    assert select_summary_evidence(fragments, topic="other", fiscal_year=2025) == []


def test_information_cutoff_uses_the_end_of_the_reporting_period() -> None:
    assert information_cutoff(2025, "1") == date(2025, 3, 31)
    assert information_cutoff(2025, "2") == date(2025, 6, 30)
    assert information_cutoff(2025, "3") == date(2025, 9, 30)
    assert information_cutoff(2025, "A") == date(2025, 12, 31)
