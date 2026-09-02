from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from typing import Any

BALANCE_CONCEPTS = {
    "1D0109": "cash_and_cash_equivalents",
    "1D01ST": "current_assets",
    "1D0309": "current_borrowings",
    "1D020T": "total_assets",
    "1D03ST": "current_liabilities",
    "1D0401": "non_current_borrowings",
    "1D040T": "total_liabilities",
    "1D07ST": "total_equity",
    "1D070T": "total_liabilities_and_equity",
}

INCOME_CONCEPTS = {
    "2D01ST": "revenue",
    "2D0201": "cost_of_sales",
    "2D02ST": "gross_profit",
    "2D0302": "selling_expenses",
    "2D0301": "administrative_expenses",
    "2D0403": "other_operating_income",
    "2D0404": "other_operating_expenses",
    "2D03ST": "operating_profit",
    "2D0401": "finance_income",
    "2D0402": "finance_costs",
    "2D0406": "share_of_profit_associates",
    "2D0410": "foreign_exchange_result",
    "2D04ST": "profit_before_tax",
    "2D0502": "income_tax_expense",
    "2D0503": "profit_continuing_operations",
    "2D0504": "profit_discontinued_operations",
    "2D07ST": "net_profit",
    "2D0802": "net_profit_owners",
    "2D0803": "net_profit_non_controlling",
    "2D0911": "basic_earnings_per_common_share",
}

CASH_FLOW_CONCEPTS = {
    "3D01ST": "operating_cash_flow",
    "3D0206": "purchases_property_plant_equipment",
    "3D02ST": "investing_cash_flow",
    "3D0325": "borrowings_received",
    "3D0330": "debt_repayments",
    "3D0305": "dividends_paid",
    "3D03ST": "financing_cash_flow",
    "3D0401": "net_change_before_exchange_rate_effects",
    "3D0404": "exchange_rate_effect_on_cash",
    "3D0405": "net_change_in_cash",
    "3D0402": "opening_cash",
    "3D04ST": "closing_cash",
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", ascii_text).strip()


def normalize_currency(raw_currency: str | None) -> str | None:
    normalized = normalize_text(raw_currency).lower()
    if normalized == "soles" or "sol" in normalized:
        return "PEN"
    if normalized == "dolares" or "lares" in normalized or normalized == "usd":
        return "USD"
    return None


def normalize_scope(scope_code: str) -> str:
    scopes = {"I": "individual", "C": "consolidated"}
    try:
        return scopes[scope_code.upper()]
    except KeyError as exc:
        raise ValueError("Tipo debe ser I (individual) o C (consolidada)") from exc


def concept_for(statement_type: str, account_code: str) -> str | None:
    concepts = {
        "balance_sheet": BALANCE_CONCEPTS,
        "income_statement": INCOME_CONCEPTS,
        "cash_flow": CASH_FLOW_CONCEPTS,
    }
    return concepts.get(statement_type, {}).get(account_code)


def value_kind_for(statement_type: str, account_code: str) -> str:
    if statement_type == "income_statement" and account_code.startswith("2D09"):
        return "per_share"
    return "monetary"


def fact_scale_for(statement_type: str, account_code: str, filing_scale: str) -> str:
    if value_kind_for(statement_type, account_code) == "per_share":
        return "units"
    return filing_scale


def decimal_amount(row: dict[str, Any], field: str) -> Decimal | None:
    value = row.get(field)
    if value is None:
        return None
    return Decimal(str(value))
