from decimal import Decimal

from app.company_analysis import classify_support, merge_catalog_rows
from app.smv.client import SmvResponse


def response(rows: list[dict]) -> SmvResponse:
    return SmvResponse(
        endpoint="https://smv.example.test",
        operation="obtener_BalanceGeneral",
        request_parameters={"Ejercicio": "2025", "Periodo": "A", "Tipo": "C"},
        raw_xml="<xml />",
        rows=rows,
        payload_sha256="a" * 64,
    )


def test_classifies_mining_non_financial_and_financial_companies() -> None:
    assert classify_support({"RPJ": "NEW01", "NombreEmpresa": "Compañía Minera Andina"}) == "full"
    assert classify_support({"RPJ": "B20010", "NombreEmpresa": "Nexa Resources Perú"}) == "full"
    assert classify_support({"RPJ": "NEW02", "NombreEmpresa": "Industria de Alimentos"}) == "basic"
    assert (
        classify_support({"RPJ": "NEW03", "NombreEmpresa": "Banco del Pacífico"})
        == "unsupported"
    )
    assert (
        classify_support({"RPJ": "NEW04", "NombreEmpresa": "Holding", "CIIU": "6419"})
        == "unsupported"
    )


def test_merges_catalog_scopes_without_duplicating_companies() -> None:
    consolidated = response(
        [
            {
                "RPJ": "CM0001",
                "RUC": "1",
                "NombreEmpresa": "Volcan Compañía Minera S.A.A.",
                "TipoSector": "Minería",
                "Cuenta": "1D020T",
                "Monto1": Decimal("1"),
            }
        ]
    )
    individual = response(
        [
            {
                "RPJ": "CM0001",
                "RUC": "1",
                "NombreEmpresa": "Volcan Compañía Minera S.A.A.",
                "TipoSector": "Minería",
                "Cuenta": "1D020T",
                "Monto1": Decimal("1"),
            },
            {
                "RPJ": "IND01",
                "RUC": "2",
                "NombreEmpresa": "Industria Peruana S.A.",
                "TipoSector": "Industrial",
                "Cuenta": "1D020T",
                "Monto1": Decimal("1"),
            },
        ]
    )

    catalog = merge_catalog_rows(
        [("consolidated", consolidated), ("individual", individual)]
    )

    assert len(catalog) == 2
    volcan = next(company for company in catalog if company["smv_rpj"] == "CM0001")
    industry = next(company for company in catalog if company["smv_rpj"] == "IND01")
    assert volcan["available_scopes"] == ["consolidated", "individual"]
    assert volcan["preferred_scope"] == "consolidated"
    assert volcan["support_level"] == "full"
    assert industry["available_scopes"] == ["individual"]
    assert industry["preferred_scope"] == "individual"
    assert industry["support_level"] == "basic"
