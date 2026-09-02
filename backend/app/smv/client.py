from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

OPERATIONS = {
    "balance_sheet": "obtener_BalanceGeneral",
    "income_statement": "obtener_GanciaPerdida",
    "cash_flow": "obtener_FlujoEfectivo",
}


@dataclass(frozen=True)
class SmvResponse:
    endpoint: str
    operation: str
    request_parameters: dict[str, str]
    raw_xml: str
    rows: list[dict[str, Any]]
    payload_sha256: str


class SmvClient:
    def __init__(self, base_url: str, timeout_seconds: float = 120) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def fetch_statement(
        self,
        statement_type: str,
        fiscal_year: int,
        period_code: str,
        scope_code: str,
    ) -> SmvResponse:
        try:
            operation = OPERATIONS[statement_type]
        except KeyError as exc:
            supported = ", ".join(sorted(OPERATIONS))
            raise ValueError(f"Estado no soportado. Opciones: {supported}") from exc

        parameters = {
            "Ejercicio": str(fiscal_year),
            "Periodo": period_code,
            "Tipo": scope_code,
        }
        envelope = self._soap_envelope(operation, parameters)
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f"http://tempuri.org/{operation}",
        }

        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = client.post(self.base_url, content=envelope.encode(), headers=headers)
            response.raise_for_status()

        raw_xml = response.text
        rows = self._parse_rows(raw_xml, operation)
        digest = hashlib.sha256(response.content).hexdigest()
        return SmvResponse(
            endpoint=self.base_url,
            operation=operation,
            request_parameters=parameters,
            raw_xml=raw_xml,
            rows=rows,
            payload_sha256=digest,
        )

    @staticmethod
    def _soap_envelope(operation: str, parameters: dict[str, str]) -> str:
        parameter_xml = "".join(f"<{name}>{value}</{name}>" for name, value in parameters.items())
        return (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<soap:Body><{operation} xmlns="http://tempuri.org/">'
            f"{parameter_xml}</{operation}></soap:Body></soap:Envelope>"
        )

    @staticmethod
    def _parse_rows(raw_xml: str, operation: str) -> list[dict[str, Any]]:
        root = ET.fromstring(raw_xml)
        expected_suffix = f"{operation}Result"
        result = next(
            (element for element in root.iter() if element.tag.endswith(expected_suffix)),
            None,
        )
        if result is None or not result.text:
            raise ValueError(f"La respuesta SOAP no contiene {expected_suffix}")

        parsed = json.loads(result.text, parse_float=Decimal, parse_int=Decimal)
        if not isinstance(parsed, list):
            raise ValueError("La SMV no devolvio una lista de observaciones")
        return parsed
