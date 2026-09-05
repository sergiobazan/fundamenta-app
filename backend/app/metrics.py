from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from psycopg import Connection

FORMULA_VERSION = 1
METRIC_QUANTUM = Decimal("0.000000000001")

METRIC_KINDS = {
    "revenue_growth": "percentage",
    "gross_margin": "percentage",
    "operating_margin": "percentage",
    "net_margin": "percentage",
    "current_ratio": "ratio",
    "working_capital": "monetary",
    "total_debt": "monetary",
    "net_debt": "monetary",
    "debt_to_equity": "ratio",
    "liabilities_to_equity": "ratio",
    "return_on_assets": "percentage",
    "return_on_equity": "percentage",
    "operating_cash_flow_margin": "percentage",
    "free_cash_flow": "monetary",
    "free_cash_flow_margin": "percentage",
}


@dataclass(frozen=True)
class FinancialFact:
    concept: str
    current: Decimal
    comparative: Decimal | None
    currency_code: str | None
    scale: str
    filing_id: int


@dataclass(frozen=True)
class MetricResult:
    code: str
    status: str
    value: Decimal | None
    currency_code: str | None
    scale: str | None
    reason: str | None
    inputs: dict[str, Any]


def comparative_metric(metric: dict) -> dict:
    """Recompute with comparative inputs, never substitute closing for average balances."""
    facts = {
        concept: FinancialFact(
            concept=concept, current=Decimal(str(item["comparative"])), comparative=None,
            currency_code=item["currency_code"], scale=item["scale"],
            filing_id=item["filing_id"],
        )
        for concept, item in metric["inputs"].items()
        if item.get("comparative") is not None
    }
    result = next(item for item in compute_metrics(facts) if item.code == metric["metric_code"])
    reason = result.reason
    if metric["metric_code"] in {"revenue_growth", "return_on_assets", "return_on_equity"}:
        reason = "Se necesitan datos de un ejercicio adicional para calcular el año anterior"
    return {
        "status": result.status, "value": result.value,
        "currency_code": result.currency_code, "value_scale": result.scale,
        "reason": reason, "inputs": result.inputs,
    }


def compute_metrics(facts: dict[str, FinancialFact]) -> list[MetricResult]:
    revenue = facts.get("revenue")
    current_assets = facts.get("current_assets")
    current_liabilities = facts.get("current_liabilities")
    current_borrowings = facts.get("current_borrowings")
    non_current_borrowings = facts.get("non_current_borrowings")
    cash = facts.get("cash_and_cash_equivalents")
    equity = facts.get("total_equity")
    liabilities = facts.get("total_liabilities")
    operating_cash_flow = facts.get("operating_cash_flow")
    capex = facts.get("purchases_property_plant_equipment")

    total_debt_value = _linear_value(
        [(current_borrowings, Decimal(1)), (non_current_borrowings, Decimal(1))]
    )
    free_cash_flow_value = _linear_value([(operating_cash_flow, Decimal(1)), (capex, Decimal(1))])

    return [
        _growth("revenue_growth", revenue),
        _ratio("gross_margin", facts.get("gross_profit"), revenue),
        _ratio("operating_margin", facts.get("operating_profit"), revenue),
        _ratio("net_margin", facts.get("net_profit"), revenue),
        _ratio("current_ratio", current_assets, current_liabilities),
        _monetary_linear(
            "working_capital",
            [(current_assets, Decimal(1)), (current_liabilities, Decimal(-1))],
        ),
        _monetary_linear(
            "total_debt",
            [(current_borrowings, Decimal(1)), (non_current_borrowings, Decimal(1))],
        ),
        _monetary_linear(
            "net_debt",
            [
                (current_borrowings, Decimal(1)),
                (non_current_borrowings, Decimal(1)),
                (cash, Decimal(-1)),
            ],
        ),
        _ratio_value(
            "debt_to_equity",
            total_debt_value,
            equity.current if equity else None,
            [current_borrowings, non_current_borrowings, equity],
        ),
        _ratio("liabilities_to_equity", liabilities, equity),
        _average_balance_ratio(
            "return_on_assets", facts.get("net_profit"), facts.get("total_assets")
        ),
        _average_balance_ratio("return_on_equity", facts.get("net_profit"), equity),
        _ratio("operating_cash_flow_margin", operating_cash_flow, revenue),
        _monetary_linear(
            "free_cash_flow",
            [(operating_cash_flow, Decimal(1)), (capex, Decimal(1))],
        ),
        _ratio_value(
            "free_cash_flow_margin",
            free_cash_flow_value,
            revenue.current if revenue else None,
            [operating_cash_flow, capex, revenue],
        ),
    ]


def calculate_and_store_metrics(
    connection: Connection,
    smv_rpj: str,
    fiscal_year: int,
    period_code: str,
    scope: str,
) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, legal_name FROM companies WHERE smv_rpj = %s", (smv_rpj,))
        company = cursor.fetchone()
        if company is None:
            raise ValueError(f"No existe la empresa RPJ {smv_rpj}")

        facts = _load_facts(cursor, company["id"], fiscal_year, period_code, scope)
        if not facts:
            raise ValueError("No existen conceptos normalizados para el periodo solicitado")

        results = compute_metrics(facts)
        for result in results:
            cursor.execute(
                """
                INSERT INTO metric_values (
                    company_id, fiscal_year, period_code, scope, metric_code,
                    formula_version, status, value, currency_code, value_scale,
                    reason, inputs
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (
                    company_id, fiscal_year, period_code, scope, metric_code,
                    formula_version
                ) DO UPDATE SET
                    status = EXCLUDED.status,
                    value = EXCLUDED.value,
                    currency_code = EXCLUDED.currency_code,
                    value_scale = EXCLUDED.value_scale,
                    reason = EXCLUDED.reason,
                    inputs = EXCLUDED.inputs,
                    calculated_at = NOW()
                """,
                (
                    company["id"],
                    fiscal_year,
                    period_code,
                    scope,
                    result.code,
                    FORMULA_VERSION,
                    result.status,
                    result.value,
                    result.currency_code,
                    result.scale,
                    result.reason,
                    json.dumps(result.inputs),
                ),
            )

    return {
        "company": company["legal_name"],
        "fiscal_year": fiscal_year,
        "period_code": period_code,
        "scope": scope,
        "formula_version": FORMULA_VERSION,
        "computed": sum(result.status == "computed" for result in results),
        "not_available": sum(result.status == "not_available" for result in results),
        "metrics": [
            {
                "code": result.code,
                "status": result.status,
                "value": str(result.value) if result.value is not None else None,
                "currency_code": result.currency_code,
                "scale": result.scale,
                "reason": result.reason,
            }
            for result in results
        ],
    }


def _load_facts(
    cursor: Any,
    company_id: int,
    fiscal_year: int,
    period_code: str,
    scope: str,
) -> dict[str, FinancialFact]:
    cursor.execute(
        """
        SELECT
            ff.normalized_concept, ff.current_amount, ff.comparative_amount,
            f.currency_code, ff.fact_scale, f.id AS filing_id
        FROM filings f
        JOIN financial_facts ff ON ff.filing_id = f.id
        WHERE f.company_id = %s
          AND f.fiscal_year = %s
          AND f.period_code = %s
          AND f.scope = %s
          AND ff.normalized_concept IS NOT NULL
        """,
        (company_id, fiscal_year, period_code, scope),
    )
    facts: dict[str, FinancialFact] = {}
    for row in cursor.fetchall():
        concept = row["normalized_concept"]
        if concept in facts:
            raise ValueError(f"Concepto normalizado duplicado: {concept}")
        facts[concept] = FinancialFact(
            concept=concept,
            current=row["current_amount"],
            comparative=row["comparative_amount"],
            currency_code=row["currency_code"],
            scale=row["fact_scale"],
            filing_id=row["filing_id"],
        )
    return facts


def _growth(code: str, fact: FinancialFact | None) -> MetricResult:
    if fact is None or fact.comparative is None:
        return _unavailable(code, "Falta el importe actual o comparativo", [fact])
    if fact.comparative == 0:
        return _unavailable(code, "El importe comparativo es cero", [fact])
    return _computed(code, (fact.current / fact.comparative) - Decimal(1), [fact])


def _ratio(
    code: str,
    numerator: FinancialFact | None,
    denominator: FinancialFact | None,
) -> MetricResult:
    return _ratio_value(
        code,
        numerator.current if numerator else None,
        denominator.current if denominator else None,
        [numerator, denominator],
    )


def _average_balance_ratio(
    code: str,
    numerator: FinancialFact | None,
    balance: FinancialFact | None,
) -> MetricResult:
    if numerator is None or balance is None or balance.comparative is None:
        return _unavailable(
            code, "Faltan importes para calcular el saldo promedio", [numerator, balance]
        )
    average = (balance.current + balance.comparative) / Decimal(2)
    return _ratio_value(code, numerator.current, average, [numerator, balance])


def _ratio_value(
    code: str,
    numerator: Decimal | None,
    denominator: Decimal | None,
    facts: list[FinancialFact | None],
) -> MetricResult:
    present = [fact for fact in facts if fact is not None]
    if numerator is None or denominator is None:
        return _unavailable(code, "Faltan conceptos requeridos", facts)
    if denominator <= 0:
        return _unavailable(code, "El denominador es cero o negativo", facts)
    if not _compatible_units(present):
        return _unavailable(code, "Las unidades o monedas de los insumos no coinciden", facts)
    return _computed(code, numerator / denominator, facts)


def _monetary_linear(
    code: str,
    terms: list[tuple[FinancialFact | None, Decimal]],
) -> MetricResult:
    facts = [fact for fact, _coefficient in terms]
    present = [fact for fact in facts if fact is not None]
    value = _linear_value(terms)
    if value is None:
        return _unavailable(code, "Faltan conceptos requeridos", facts)
    if not _compatible_units(present):
        return _unavailable(code, "Las unidades o monedas de los insumos no coinciden", facts)
    first = present[0]
    return _computed(
        code,
        value,
        facts,
        currency_code=first.currency_code,
        # Keep the raw reported magnitude when SMV does not provide a verified
        # scale. A NULL value_scale is surfaced as an explicit UI warning and
        # must never be interpreted as units, thousands, or millions.
        scale=None if first.scale == "unknown" else first.scale,
    )


def _linear_value(terms: list[tuple[FinancialFact | None, Decimal]]) -> Decimal | None:
    if any(fact is None for fact, _coefficient in terms):
        return None
    return sum(
        (fact.current * coefficient for fact, coefficient in terms if fact is not None),
        start=Decimal(0),
    )


def _compatible_units(facts: list[FinancialFact]) -> bool:
    if not facts:
        return False
    currencies = {fact.currency_code for fact in facts}
    scales = {fact.scale for fact in facts}
    return len(currencies) == 1 and len(scales) == 1


def _computed(
    code: str,
    value: Decimal,
    facts: list[FinancialFact | None],
    currency_code: str | None = None,
    scale: str | None = None,
) -> MetricResult:
    if code not in METRIC_KINDS:
        raise ValueError(f"Metrica no registrada: {code}")
    return MetricResult(
        code=code,
        status="computed",
        value=value.quantize(METRIC_QUANTUM),
        currency_code=currency_code,
        scale=scale,
        reason=None,
        inputs=_serialize_inputs(facts),
    )


def _unavailable(
    code: str,
    reason: str,
    facts: list[FinancialFact | None],
) -> MetricResult:
    if code not in METRIC_KINDS:
        raise ValueError(f"Metrica no registrada: {code}")
    return MetricResult(
        code=code,
        status="not_available",
        value=None,
        currency_code=None,
        scale=None,
        reason=reason,
        inputs=_serialize_inputs(facts),
    )


def _serialize_inputs(facts: list[FinancialFact | None]) -> dict[str, Any]:
    return {
        fact.concept: {
            "current": str(fact.current),
            "comparative": str(fact.comparative) if fact.comparative is not None else None,
            "currency_code": fact.currency_code,
            "scale": fact.scale,
            "filing_id": fact.filing_id,
        }
        for fact in facts
        if fact is not None
    }
