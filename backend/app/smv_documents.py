"""Discover annual attachments through SMV's public financial-information form."""

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from app.notes import _normalized

FINANCIAL_FORM = (
    "https://www.smv.gob.pe/SIMV/Frm_InformacionFinanciera"
    "?data=A70181B60967D74090DCD93C4920AA1D769614EC12"
)
PREFIX = "ctl00$MainContent$"
HOSTS = {"www.smv.gob.pe", "smv.gob.pe"}


def company_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalized(name))


class FinancialForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = {}
        self.companies = []
        self.links = []
        self._companies = False
        self._option = None
        self._label = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("type") == "hidden" and attrs.get("name"):
            self.hidden[attrs["name"]] = attrs.get("value", "")
        if tag == "select":
            self._companies = attrs.get("name") == PREFIX + "cboDenominacionSocial"
        if tag == "option" and self._companies:
            self._option = attrs.get("value")
            self._label = []
        if tag == "a" and "grdInfoFinanciera" in attrs.get("id", ""):
            href = attrs.get("href", "").strip()
            if "XBRL" not in attrs.get("title", "").upper():
                self.links.append(href)

    def handle_data(self, data):
        if self._option is not None:
            self._label.append(data)

    def handle_endtag(self, tag):
        if tag == "option" and self._option is not None:
            self.companies.append((self._option, "".join(self._label).strip()))
            self._option = None
        if tag == "select":
            self._companies = False


def _request(client, method, data=None):
    # The form must remain on SMV. Never follow a redirect with POST/cookies.
    with client.stream(method, FINANCIAL_FORM, data=data) as response:
        response.raise_for_status()
        chunks = []
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > 4_000_000:
                raise ValueError("Formulario SMV demasiado grande")
            chunks.append(chunk)
    form = FinancialForm()
    form.feed(b"".join(chunks).decode("utf-8", errors="replace"))
    return form


def discover_smv_documents(name: str, year: int, scope: str, timeout=20) -> list[str]:
    if scope not in {"individual", "consolidated"}:
        raise ValueError("Alcance documental no compatible")
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        form = _request(client, "GET")
        matches = [
            code for code, label in form.companies if company_key(label) == company_key(name)
        ]
        if len(matches) != 1:
            raise ValueError("La SMV no devolvió una coincidencia única para la empresa")
        fields = dict(form.hidden)
        fields.update(
            {
                PREFIX + "cboDenominacionSocial": matches[0],
                PREFIX + "TextBox1": name,
                PREFIX + "cboTipo": "I" if scope == "individual" else "C",
                PREFIX + "cboPeriodo": "A",
                PREFIX + "cboAnio": str(year),
                PREFIX + "cboTrimestre": "-1",
                PREFIX + "cbBuscar": "Buscar",
            }
        )
        result = _request(client, "POST", fields)
    urls = []
    for href in result.links:
        url = urljoin(FINANCIAL_FORM, href)
        parsed = urlparse(url)
        if (
            parsed.scheme == "https"
            and parsed.hostname in HOSTS
            and not parsed.username
            and not parsed.password
            and parsed.port in (None, 443)
            and (
                parsed.path.lower().endswith(".pdf")
                or parsed.path.lower() == "/consultasp8/documento.aspx"
            )
        ):
            urls.append(url)
    # These are candidates, not validated evidence. The PDF verifier checks
    # company, year, scope and exact reported figures independently.
    return list(dict.fromkeys(urls))[:12]
