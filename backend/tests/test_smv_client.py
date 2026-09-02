import json
from decimal import Decimal

from app.smv.client import SmvClient


def test_parse_rows_from_soap_result() -> None:
    payload = [{"RPJ": "B20003", "Cuenta": "1D020T", "Monto1": 123}]
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        "<soap:Body><obtener_BalanceGeneralResponse>"
        f"<obtener_BalanceGeneralResult>{json.dumps(payload)}</obtener_BalanceGeneralResult>"
        "</obtener_BalanceGeneralResponse></soap:Body></soap:Envelope>"
    )

    rows = SmvClient._parse_rows(xml, "obtener_BalanceGeneral")
    assert rows[0]["RPJ"] == "B20003"
    assert rows[0]["Monto1"] == Decimal("123")
