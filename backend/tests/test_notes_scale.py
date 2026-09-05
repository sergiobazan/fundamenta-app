from decimal import Decimal

import pytest
from app.notes_scale import presentation_policy, verify_notes_policy


def sample():
    policy = (
        "Bases de preparación\nLos estados financieros consolidados se presentan en soles "
        "y todos los valores se redondean a miles S/(000), "
        "excepto donde se indique de otro modo."
    )
    tables = (
        "6. Efectivo y equivalentes del efectivo\n2025 2024\nS/(000) S/(000)\n"
        "Caja 100 90 _________\n110 100\n"
        "7. Otra cuenta\n2025 2024 2023\nS/(000) S/(000) S/(000)\n"
        "Utilidad antes de impuesto a la renta 200 180 160\n"
        "Total impuesto a la renta (20) (18) (16)\n"
    )
    filings = [
        dict(id=i, currency_code="PEN", fiscal_year=2025, scope="consolidated", period_code="A")
        for i in [1, 2, 3]
    ]

    def fact(filing, code, label, concept, current, previous):
        return dict(
            filing_id=filing,
            account_code=code,
            original_label=label,
            normalized_concept=concept,
            value_kind="monetary",
            current_amount=Decimal(current),
            comparative_amount=Decimal(previous),
        )

    facts = {
        1: [fact(1, "cash", "Efectivo", "cash_and_cash_equivalents", "110", "100")],
        2: [
            fact(2, "profit", "Ganancia antes de impuestos", "profit_before_tax", "200", "180"),
            fact(2, "tax", "Impuesto", "income_tax_expense", "-20", "-18"),
        ],
        3: [fact(3, "closing", "Efectivo al cierre", "closing_cash", "110", "100")],
    }
    return [policy, tables], filings, facts


def test_general_policy_matches_year_columns_and_each_filing():
    pages, filings, facts = sample()
    result = verify_notes_policy(pages, filings, facts)
    assert set(result) == {1, 2, 3}
    assert result[3]["scale"] == "thousands"
    assert result[3]["page"] == 1
    assert result[3]["filing_matches"][0]["page"] == 2
    assert result[2]["filing_matches"][0]["years"] == [2025, 2024, 2023]
    assert result[1]["exception"] == "excepto donde se indique de otro modo"


@pytest.mark.parametrize("change", ["year", "unit", "currency", "magnitude", "no_policy"])
def test_ambiguous_or_inconsistent_evidence_does_not_verify(change):
    pages, filings, facts = sample()
    if change == "year":
        pages[1] = pages[1].replace("2025 2024", "2024 2025")
    elif change == "unit":
        pages[1] = pages[1].replace("S/(000)", "millones de soles")
    elif change == "currency":
        pages[1] = pages[1].replace("S/(000)", "US$(000)")
    elif change == "magnitude":
        pages[1] = pages[1].replace("200 180 160", "0.2 0.18 0.16")
    else:
        pages[0] = "La tabla de inventarios se presenta en miles de soles."
    assert verify_notes_policy(pages, filings, facts) == {}


def test_no_scale_is_assigned_to_a_filing_without_its_own_anchor():
    pages, filings, facts = sample()
    facts[3][0]["current_amount"] = Decimal("999")
    assert set(verify_notes_policy(pages, filings, facts)) == {1, 2}


def test_specific_exception_and_conflicting_policies_require_review():
    pages, _, _ = sample()
    assert (
        presentation_policy(
            [pages[0].replace("donde se indique de otro modo", "el flujo de efectivo")], "PEN"
        )
        is None
    )
    assert (
        presentation_policy(
            [pages[0], pages[0].replace("miles S/(000)", "millones de soles")], "PEN"
        )
        is None
    )
