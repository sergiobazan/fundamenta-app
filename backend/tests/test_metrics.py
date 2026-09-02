from decimal import Decimal

from app.metrics import FinancialFact, compute_metrics


def fact(
    concept: str,
    current: str,
    comparative: str | None = None,
    currency: str = "USD",
    scale: str = "thousands",
) -> FinancialFact:
    return FinancialFact(
        concept=concept,
        current=Decimal(current),
        comparative=Decimal(comparative) if comparative is not None else None,
        currency_code=currency,
        scale=scale,
        filing_id=1,
    )


def buenaventura_facts() -> dict[str, FinancialFact]:
    return {
        "revenue": fact("revenue", "1731639", "1154605"),
        "gross_profit": fact("gross_profit", "782391", "359287"),
        "operating_profit": fact("operating_profit", "633206", "445655"),
        "net_profit": fact("net_profit", "830188", "416263"),
        "current_assets": fact("current_assets", "1156516", "838362"),
        "current_liabilities": fact("current_liabilities", "575990", "479738"),
        "current_borrowings": fact("current_borrowings", "8929", "9169"),
        "non_current_borrowings": fact("non_current_borrowings", "735962", "645884"),
        "cash_and_cash_equivalents": fact("cash_and_cash_equivalents", "529839", "478435"),
        "total_equity": fact("total_equity", "4267465", "3559701"),
        "total_liabilities": fact("total_liabilities", "1755371", "1488202"),
        "total_assets": fact("total_assets", "6022836", "5047903"),
        "operating_cash_flow": fact("operating_cash_flow", "577320", "486059"),
        "purchases_property_plant_equipment": fact(
            "purchases_property_plant_equipment", "-473008", "-337743"
        ),
    }


def test_compute_all_metrics_for_buenaventura() -> None:
    results = {result.code: result for result in compute_metrics(buenaventura_facts())}

    assert len(results) == 15
    assert all(result.status == "computed" for result in results.values())
    assert results["working_capital"].value == Decimal("580526")
    assert results["total_debt"].value == Decimal("744891")
    assert results["net_debt"].value == Decimal("215052")
    assert results["free_cash_flow"].value == Decimal("104312")
    assert results["free_cash_flow"].currency_code == "USD"
    assert results["free_cash_flow"].scale == "thousands"


def test_zero_comparative_revenue_is_not_available() -> None:
    facts = buenaventura_facts()
    facts["revenue"] = fact("revenue", "100", "0")
    result = next(item for item in compute_metrics(facts) if item.code == "revenue_growth")

    assert result.status == "not_available"
    assert result.value is None
    assert result.reason == "El importe comparativo es cero"


def test_incompatible_scale_blocks_free_cash_flow() -> None:
    facts = buenaventura_facts()
    facts["purchases_property_plant_equipment"] = fact(
        "purchases_property_plant_equipment", "-473.008", scale="millions"
    )
    result = next(item for item in compute_metrics(facts) if item.code == "free_cash_flow")

    assert result.status == "not_available"
    assert result.reason == "Las unidades o monedas de los insumos no coinciden"
