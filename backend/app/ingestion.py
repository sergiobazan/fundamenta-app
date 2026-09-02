from __future__ import annotations

import json
from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from psycopg import Connection

from app.normalization import (
    concept_for,
    decimal_amount,
    fact_scale_for,
    normalize_currency,
    normalize_scope,
    value_kind_for,
)
from app.smv.client import SmvResponse


def filter_company_rows(rows: Iterable[dict[str, Any]], smv_rpj: str) -> list[dict[str, Any]]:
    matches = [row for row in rows if str(row.get("RPJ", "")).strip() == smv_rpj]
    if not matches:
        raise ValueError(f"No se encontraron observaciones para RPJ {smv_rpj}")
    return matches


def store_statement(
    connection: Connection,
    response: SmvResponse,
    rows: list[dict[str, Any]],
    statement_type: str,
    fiscal_year: int,
    period_code: str,
    scope_code: str,
    reported_scale: str = "unknown",
    scale_source_url: str | None = None,
) -> dict[str, Any]:
    first = rows[0]
    with connection.cursor() as cursor:
        source_fetch_id = _upsert_source_fetch(cursor, response)
        company_id = _upsert_company(cursor, first)
        filing_id = _upsert_filing(
            cursor,
            company_id=company_id,
            source_fetch_id=source_fetch_id,
            statement_type=statement_type,
            fiscal_year=fiscal_year,
            period_code=period_code,
            scope_code=scope_code,
            reported_scale=reported_scale,
            scale_source_url=scale_source_url,
            row=first,
        )
        cursor.execute("DELETE FROM financial_facts WHERE filing_id = %s", (filing_id,))
        mapped_count = _insert_facts(cursor, filing_id, statement_type, reported_scale, rows)
        cursor.execute("DELETE FROM validation_results WHERE filing_id = %s", (filing_id,))
        validations = _run_validations(cursor, filing_id, statement_type)

    return {
        "company_id": company_id,
        "filing_id": filing_id,
        "source_fetch_id": source_fetch_id,
        "company": first.get("NombreEmpresa"),
        "facts": len(rows),
        "mapped_facts": mapped_count,
        "reported_scale": reported_scale,
        "scale_source_url": scale_source_url,
        "validations": validations,
    }


def _upsert_source_fetch(cursor: Any, response: SmvResponse) -> int:
    cursor.execute(
        """
        INSERT INTO source_fetches (
            provider, endpoint, operation, request_parameters, payload_sha256,
            row_count, raw_response
        ) VALUES ('smv_open_data', %s, %s, %s, %s, %s, %s)
        ON CONFLICT (provider, operation, payload_sha256)
        DO UPDATE SET retrieved_at = NOW()
        RETURNING id
        """,
        (
            response.endpoint,
            response.operation,
            json.dumps(response.request_parameters),
            response.payload_sha256,
            len(response.rows),
            response.raw_xml,
        ),
    )
    return cursor.fetchone()["id"]


def _upsert_company(cursor: Any, row: dict[str, Any]) -> int:
    cursor.execute(
        """
        INSERT INTO companies (smv_rpj, ruc, legal_name, company_type, sector, ciiu)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (smv_rpj) DO UPDATE SET
            ruc = EXCLUDED.ruc,
            legal_name = EXCLUDED.legal_name,
            company_type = EXCLUDED.company_type,
            sector = EXCLUDED.sector,
            ciiu = EXCLUDED.ciiu,
            updated_at = NOW()
        RETURNING id
        """,
        (
            row.get("RPJ"),
            row.get("RUC"),
            row.get("NombreEmpresa"),
            row.get("TipoEmpresa"),
            row.get("TipoSector"),
            row.get("CIIU"),
        ),
    )
    return cursor.fetchone()["id"]


def _upsert_filing(
    cursor: Any,
    company_id: int,
    source_fetch_id: int,
    statement_type: str,
    fiscal_year: int,
    period_code: str,
    scope_code: str,
    reported_scale: str,
    scale_source_url: str | None,
    row: dict[str, Any],
) -> int:
    cursor.execute(
        """
        INSERT INTO filings (
            company_id, source_fetch_id, statement_type, fiscal_year, period_code,
            scope, information_type_raw, currency_code, currency_raw,
            reported_scale, scale_source_url, cash_flow_method_raw
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (company_id, statement_type, fiscal_year, period_code, scope)
        DO UPDATE SET
            source_fetch_id = EXCLUDED.source_fetch_id,
            information_type_raw = EXCLUDED.information_type_raw,
            currency_code = EXCLUDED.currency_code,
            currency_raw = EXCLUDED.currency_raw,
            reported_scale = EXCLUDED.reported_scale,
            scale_source_url = EXCLUDED.scale_source_url,
            cash_flow_method_raw = EXCLUDED.cash_flow_method_raw,
            updated_at = NOW()
        RETURNING id
        """,
        (
            company_id,
            source_fetch_id,
            statement_type,
            fiscal_year,
            period_code,
            normalize_scope(scope_code),
            row.get("TipoInformacion") or "",
            normalize_currency(row.get("Moneda")),
            row.get("Moneda") or "",
            reported_scale,
            scale_source_url,
            row.get("MetodoFlujoEfectivo"),
        ),
    )
    return cursor.fetchone()["id"]


def _insert_facts(
    cursor: Any,
    filing_id: int,
    statement_type: str,
    reported_scale: str,
    rows: list[dict[str, Any]],
) -> int:
    mapped = 0
    for row in rows:
        account_code = str(row.get("Cuenta") or "").strip()
        concept = concept_for(statement_type, account_code)
        mapped += concept is not None
        cursor.execute(
            """
            INSERT INTO financial_facts (
                filing_id, account_code, original_label, normalized_concept,
                current_amount, comparative_amount, value_kind, fact_scale,
                normalization_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                filing_id,
                account_code,
                row.get("DescripcionCuenta") or account_code,
                concept,
                decimal_amount(row, "Monto1") or Decimal(0),
                decimal_amount(row, "Monto2"),
                value_kind_for(statement_type, account_code),
                fact_scale_for(statement_type, account_code, reported_scale),
                "mapped" if concept else "unmapped",
            ),
        )
    return mapped


def _run_validations(cursor: Any, filing_id: int, statement_type: str) -> list[dict[str, Any]]:
    values = _concept_values(cursor, filing_id)
    rules: list[tuple[str, str, dict[str, Any]]] = []

    if statement_type == "balance_sheet":
        assets = values.get("total_assets")
        liabilities_and_equity = values.get("total_liabilities_and_equity")
        if liabilities_and_equity is None:
            liabilities = values.get("total_liabilities")
            equity = values.get("total_equity")
            if liabilities is not None and equity is not None:
                liabilities_and_equity = liabilities + equity
        rules.append(
            _equality_rule(
                "balance_equation",
                assets,
                liabilities_and_equity,
                "assets",
                "liabilities_and_equity",
            )
        )

    if statement_type == "income_statement":
        revenue = values.get("revenue")
        cost_of_sales = values.get("cost_of_sales")
        expected_gross_profit = (
            revenue + cost_of_sales if revenue is not None and cost_of_sales is not None else None
        )
        rules.append(
            _equality_rule(
                "gross_profit_reconciliation",
                values.get("gross_profit"),
                expected_gross_profit,
                "reported_gross_profit",
                "revenue_plus_cost_of_sales",
            )
        )
        continuing = values.get("profit_continuing_operations")
        discontinued = values.get("profit_discontinued_operations")
        expected_net_profit = (
            continuing + discontinued
            if continuing is not None and discontinued is not None
            else None
        )
        rules.append(
            _equality_rule(
                "net_profit_reconciliation",
                values.get("net_profit"),
                expected_net_profit,
                "reported_net_profit",
                "continuing_plus_discontinued",
            )
        )

    if statement_type == "cash_flow":
        operating = values.get("operating_cash_flow")
        investing = values.get("investing_cash_flow")
        financing = values.get("financing_cash_flow")
        expected_change_before_fx = (
            operating + investing + financing
            if operating is not None and investing is not None and financing is not None
            else None
        )
        rules.append(
            _equality_rule(
                "cash_flow_activity_reconciliation",
                values.get("net_change_before_exchange_rate_effects"),
                expected_change_before_fx,
                "reported_net_change_before_fx",
                "operating_plus_investing_plus_financing",
            )
        )
        change_before_fx = values.get("net_change_before_exchange_rate_effects")
        exchange_rate_effect = values.get("exchange_rate_effect_on_cash")
        expected_net_change = (
            change_before_fx + exchange_rate_effect
            if change_before_fx is not None and exchange_rate_effect is not None
            else None
        )
        rules.append(
            _equality_rule(
                "cash_flow_exchange_reconciliation",
                values.get("net_change_in_cash"),
                expected_net_change,
                "reported_net_change",
                "change_before_fx_plus_exchange_effect",
            )
        )
        opening = values.get("opening_cash")
        change = values.get("net_change_in_cash")
        expected_closing = opening + change if opening is not None and change is not None else None
        rules.append(
            _equality_rule(
                "cash_rollforward",
                values.get("closing_cash"),
                expected_closing,
                "reported_closing_cash",
                "opening_plus_net_change",
            )
        )
        rules.append(_cash_matches_balance_rule(cursor, filing_id, values.get("closing_cash")))

    results = []
    for rule_code, status, details in rules:
        _store_validation(cursor, filing_id, rule_code, status, details)
        results.append({"rule": rule_code, "status": status, "details": details})
    return results


def _concept_values(cursor: Any, filing_id: int) -> dict[str, Decimal]:
    cursor.execute(
        """
        SELECT normalized_concept, current_amount
        FROM financial_facts
        WHERE filing_id = %s AND normalized_concept IS NOT NULL
        """,
        (filing_id,),
    )
    return {row["normalized_concept"]: row["current_amount"] for row in cursor.fetchall()}


def _equality_rule(
    rule_code: str,
    actual: Decimal | None,
    expected: Decimal | None,
    actual_label: str,
    expected_label: str,
) -> tuple[str, str, dict[str, Any]]:
    if actual is None or expected is None:
        return rule_code, "not_applicable", {"reason": "Required concepts are missing"}
    difference = actual - expected
    return (
        rule_code,
        "passed" if difference == 0 else "failed",
        {
            actual_label: str(actual),
            expected_label: str(expected),
            "difference": str(difference),
        },
    )


def _cash_matches_balance_rule(
    cursor: Any, filing_id: int, closing_cash: Decimal | None
) -> tuple[str, str, dict[str, Any]]:
    cursor.execute(
        """
        SELECT balance_fact.current_amount
        FROM filings cash_filing
        JOIN filings balance_filing
          ON balance_filing.company_id = cash_filing.company_id
         AND balance_filing.fiscal_year = cash_filing.fiscal_year
         AND balance_filing.period_code = cash_filing.period_code
         AND balance_filing.scope = cash_filing.scope
         AND balance_filing.statement_type = 'balance_sheet'
        JOIN financial_facts balance_fact
          ON balance_fact.filing_id = balance_filing.id
         AND balance_fact.normalized_concept = 'cash_and_cash_equivalents'
        WHERE cash_filing.id = %s
        """,
        (filing_id,),
    )
    row = cursor.fetchone()
    balance_cash = row["current_amount"] if row else None
    return _equality_rule(
        "cash_matches_balance",
        closing_cash,
        balance_cash,
        "cash_flow_closing_cash",
        "balance_cash",
    )


def _store_validation(
    cursor: Any,
    filing_id: int,
    rule_code: str,
    status: str,
    details: dict[str, Any],
) -> None:
    cursor.execute(
        """
        INSERT INTO validation_results (filing_id, rule_code, status, details)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (filing_id, rule_code) DO UPDATE SET
            status = EXCLUDED.status,
            details = EXCLUDED.details,
            checked_at = NOW()
        """,
        (filing_id, rule_code, status, json.dumps(details)),
    )
