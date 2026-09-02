from decimal import Decimal

import pytest
from app.normalization import (
    concept_for,
    decimal_amount,
    fact_scale_for,
    normalize_currency,
    normalize_scope,
    value_kind_for,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Soles", "PEN"), ("Dólares", "USD"), ("D lares", "USD"), ("USD", "USD")],
)
def test_normalize_currency(raw: str, expected: str) -> None:
    assert normalize_currency(raw) == expected


def test_balance_concept_mapping() -> None:
    assert concept_for("balance_sheet", "1D020T") == "total_assets"
    assert concept_for("balance_sheet", "unmapped") is None


def test_income_and_cash_flow_concept_mapping() -> None:
    assert concept_for("income_statement", "2D01ST") == "revenue"
    assert concept_for("income_statement", "2D07ST") == "net_profit"
    assert concept_for("cash_flow", "3D01ST") == "operating_cash_flow"
    assert concept_for("cash_flow", "3D0401") == "net_change_before_exchange_rate_effects"
    assert concept_for("cash_flow", "3D0404") == "exchange_rate_effect_on_cash"
    assert concept_for("cash_flow", "3D04ST") == "closing_cash"


def test_earnings_per_share_uses_units_instead_of_filing_scale() -> None:
    assert value_kind_for("income_statement", "2D0911") == "per_share"
    assert fact_scale_for("income_statement", "2D0911", "thousands") == "units"
    assert fact_scale_for("income_statement", "2D07ST", "thousands") == "thousands"


def test_scope_validation() -> None:
    assert normalize_scope("C") == "consolidated"
    assert normalize_scope("I") == "individual"
    with pytest.raises(ValueError):
        normalize_scope("X")


def test_decimal_amount_avoids_float_math() -> None:
    assert decimal_amount({"Monto1": 12.5}, "Monto1") == Decimal("12.5")
