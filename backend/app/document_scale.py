"""Conservative, per-statement verification against official PDF evidence.

Discovery queries SMV first, then registered official landing pages.
An unknown origin or ambiguous document leaves the reported scale unchanged.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.notes import NoteSourceConfig, _normalized, extract_notes_from_pdf

TITLES = {
    "balance_sheet": r"estado(?:s)? (?:consolidado[s]? de |de )situacion financiera",
    "income_statement": r"estado(?:s)? (?:consolidado[s]? de |de )resultados",
    "cash_flow": r"estado(?:s)? (?:consolidado[s]? de |de )flujos? de efectivo",
}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.urls.append(href)


def official_url(url: str, hosts: set[str]) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in hosts
        and parsed.port in (None, 443)
        and not parsed.username
        and not parsed.password
    )


def fetch_official(url: str, hosts: set[str], max_bytes: int, timeout: float) -> bytes:
    # Validate every redirect as well as the original URL. Hosts come only from
    # operator-reviewed origins, not from user input or PDF content.
    for _ in range(5):
        if not official_url(url, hosts):
            raise ValueError("El enlace no pertenece a los dominios oficiales registrados")
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=False) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            response.raise_for_status()
            chunks = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("Documento demasiado grande")
                chunks.append(chunk)
            return b"".join(chunks)
    raise ValueError("Demasiadas redirecciones")


def discover_pdfs(page_url: str, hosts: set[str], year: int, timeout: float) -> list[str]:
    if urlparse(page_url).path.lower().endswith(".pdf") and official_url(page_url, hosts):
        return [page_url]
    html = fetch_official(page_url, hosts, 4_000_000, timeout).decode("utf-8", errors="replace")
    links = Links()
    links.feed(html)
    urls = list(dict.fromkeys(urljoin(page_url, href) for href in links.urls))
    pdfs = [
        url
        for url in urls
        if official_url(url, hosts) and urlparse(url).path.lower().endswith(".pdf")
    ]
    # Prioritize current-year filenames but validate dates inside every PDF.
    return sorted(
        pdfs,
        key=lambda url: (
            not bool(re.search(r"financ|financial|eeff|audit", url, re.I)),
            str(year) not in url,
            url,
        ),
    )[:12]


def read_pages(data: bytes) -> list[str]:
    if not data.startswith(b"%PDF"):
        raise ValueError("La fuente no devolvió un PDF")
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted or len(reader.pages) > 350:
        raise ValueError("PDF cifrado o demasiado extenso")
    return [page.extract_text() or "" for page in reader.pages]


def document_identity(pages: list[str], name: str, year: int, scope: str) -> bool:
    cover = " ".join(_normalized(" ".join(pages[:3])).split())
    company = " ".join(_normalized(name).split())

    # Legal suffix punctuation may differ, but the full company name must match.
    def compact(value):
        return re.sub(r"[^a-z0-9]", "", value)

    if compact(company) not in compact(cover):
        return False
    match = re.search(r"estados financieros.{0,100}?31 de diciembre de (20\d{2})", cover)
    if not match or int(match.group(1)) != year:
        return False
    consolidated = "consolidad" in match.group()
    return consolidated == (scope == "consolidated")


def explicit_scale(header: str, currency: str) -> str | None:
    text = _normalized(header)
    if currency == "USD":
        currency_ok = bool(re.search(r"us\s*\$|dolares", text))
        other_currency = bool(re.search(r"s/|soles", text))
    elif currency == "PEN":
        currency_ok = bool(re.search(r"s/|soles", text))
        other_currency = bool(re.search(r"us\s*\$|dolares", text))
    else:
        return None
    if not currency_ok or other_currency:
        return None
    scales = set()
    if re.search(r"\(\s*0{3}\s*\)|\bmiles\b", text):
        scales.add("thousands")
    if re.search(r"\bmillones\b", text):
        scales.add("millions")
    if re.search(r"\bunidades\b|expresad[oa]s? en (?:soles|dolares)", text):
        scales.add("units")
    return next(iter(scales)) if len(scales) == 1 else None


def number_tokens(line: str) -> list[Decimal]:
    return [
        Decimal(token.replace(",", "").replace("(", "-").replace(")", ""))
        for token in re.findall(r"(?<![\w.])\(?-?\d[\d,]*(?:\.\d+)?\)?", line)
    ]


def verify_statement(pages: list[str], filing: dict, facts: list[dict]) -> dict | None:
    """Require an explicit header and >=3 labelled current/comparative matches.

    Matching raw magnitudes also ensures that the PDF scale applies to the SMV
    data, rather than blindly applying a differently scaled PDF presentation.
    """
    evidence = []
    for index, page in enumerate(pages):
        normalized = _normalized(page)
        title = re.search(TITLES[filing["statement_type"]], normalized[:900])
        if not title or "notas a los estados" in normalized[:160]:
            continue
        header = normalized[title.start() : title.start() + 550]
        if str(filing["fiscal_year"]) not in header:
            continue
        scale = explicit_scale(header, filing["currency_code"])
        if not scale:
            continue
        matched = []
        for fact in facts:
            if fact["current_amount"] == 0 or fact["comparative_amount"] is None:
                continue
            label_words = set(re.findall(r"[a-z]+", _normalized(fact["original_label"])))
            label_words = {"propiedad" if word == "propiedades" else word for word in label_words}
            label_words -= {"de", "del", "y", "la", "el", "los", "las", "neto", "netos"}
            if not label_words:
                continue
            for line in page.splitlines():
                line_words = set(re.findall(r"[a-z]+", _normalized(line)))
                line_words = {"propiedad" if word == "propiedades" else word for word in line_words}
                if not label_words.issubset(line_words):
                    continue
                values = number_tokens(line)
                if len(values) >= 2 and values[-2:] == [
                    fact["current_amount"],
                    fact["comparative_amount"],
                ]:
                    matched.append({"account_code": fact["account_code"], "line": line.strip()})
                    break
        if len({item["account_code"] for item in matched}) >= 3:
            evidence.append(
                {"scale": scale, "page": index + 1, "header": header, "matches": matched}
            )
    if not evidence or len({item["scale"] for item in evidence}) != 1:
        return None
    return evidence[0]


def apply_evidence(
    connection, filing: dict, facts: list[dict], evidence: dict, source_url: str, digest: str
) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT reported_scale FROM filings WHERE id = %s FOR UPDATE", (filing["id"],)
        )
        if cursor.fetchone()["reported_scale"] != "unknown":
            return False
        # Refuse stale evidence if ingestion changed the facts while downloading.
        cursor.execute(
            "SELECT account_code, current_amount, comparative_amount FROM financial_facts "
            "WHERE filing_id = %s ORDER BY account_code",
            (filing["id"],),
        )
        current = list(cursor.fetchall())
        expected = sorted(
            [
                {key: fact[key] for key in ("account_code", "current_amount", "comparative_amount")}
                for fact in facts
            ],
            key=lambda row: row["account_code"],
        )
        if current != expected:
            return False
        cursor.execute(
            "INSERT INTO filing_scale_evidence "
            "(filing_id, source_url, source_sha256, evidence) VALUES (%s,%s,%s,%s::jsonb) "
            "ON CONFLICT (filing_id) DO UPDATE SET source_url=EXCLUDED.source_url, "
            "source_sha256=EXCLUDED.source_sha256, evidence=EXCLUDED.evidence, "
            "verified_at=NOW()",
            (filing["id"], source_url, digest, json.dumps(evidence)),
        )
        cursor.execute(
            "UPDATE filings SET reported_scale=%s, scale_source_url=%s, "
            "updated_at=NOW() WHERE id=%s",
            (evidence["scale"], source_url, filing["id"]),
        )
        cursor.execute(
            "UPDATE financial_facts SET fact_scale=%s, updated_at=NOW() "
            "WHERE filing_id=%s AND value_kind='monetary'",
            (evidence["scale"], filing["id"]),
        )
    return True


def verify_company_scales(connection, job: dict, settings) -> dict:
    with connection.cursor() as cursor:
        cursor.execute("SELECT legal_name FROM companies WHERE id=%s", (job["company_id"],))
        name = cursor.fetchone()["legal_name"]
        cursor.execute(
            "SELECT * FROM filings WHERE company_id=%s AND fiscal_year=%s "
            "AND scope=%s AND period_code=%s",
            (job["company_id"], job["fiscal_year"], job["scope"], job["period_code"]),
        )
        filings = list(cursor.fetchall())
        pending = sum(filing["reported_scale"] == "unknown" for filing in filings)
        if not filings or job["period_code"] != "A":
            return {"verified": 0, "pending": pending}
        cursor.execute(
            "SELECT source_url FROM note_sources WHERE company_id=%s "
            "AND fiscal_year=%s AND scope=%s AND period_code=%s AND enabled",
            (job["company_id"], job["fiscal_year"], job["scope"], job["period_code"]),
        )
        urls = [row["source_url"] for row in cursor.fetchall()]
        cursor.execute(
            "SELECT page_url, allowed_hosts FROM document_origins WHERE smv_rpj=%s",
            (job["smv_rpj"],),
        )
        origins = list(cursor.fetchall())
        facts_by_id = {}
        for filing in filings:
            cursor.execute("SELECT * FROM financial_facts WHERE filing_id=%s", (filing["id"],))
            facts_by_id[filing["id"]] = list(cursor.fetchall())
    hosts = {"www.smv.gob.pe", "smv.gob.pe"}
    for origin in origins:
        hosts.update(origin["allowed_hosts"])
    errors = []
    from app.smv_documents import discover_smv_documents

    try:
        urls = discover_smv_documents(name, job["fiscal_year"], job["scope"]) + urls
    except (httpx.HTTPError, ValueError) as error:
        errors.append(f"Descubrimiento SMV: {str(error)[:220]}")
    for origin in origins:
        try:
            urls.extend(discover_pdfs(origin["page_url"], hosts, job["fiscal_year"], 20))
        except (httpx.HTTPError, ValueError) as error:
            errors.append(str(error)[:250])
    verified = 0
    documents = []
    for url in list(dict.fromkeys(urls))[:16]:
        try:
            data = fetch_official(url, hosts, settings.notes_max_pdf_bytes, 30)
            pages = read_pages(data)
            if not document_identity(pages, name, job["fiscal_year"], job["scope"]):
                continue
            from app.notes_scale import verify_notes_policy

            notes_evidence = verify_notes_policy(pages, filings, facts_by_id)
            for filing in filings:
                facts = facts_by_id[filing["id"]]
                evidence = verify_statement(pages, filing, facts)
                fallback = notes_evidence.get(filing["id"])
                if evidence and fallback and evidence["scale"] != fallback["scale"]:
                    errors.append("Encabezado y política de presentación tienen escalas diferentes")
                    continue
                evidence = evidence or fallback
                if evidence and apply_evidence(
                    connection, filing, facts, evidence, url, hashlib.sha256(data).hexdigest()
                ):
                    verified += 1
            # Official origin and document identity were checked above. Notes
            # extraction is independent of monetary-scale evidence. Keep the
            # first valid source (SMV first), even if later PDFs verify scales.
            if not documents:
                tokens = (name, str(job["fiscal_year"]), "Notas a los estados financieros")
                try:
                    extraction = extract_notes_from_pdf(data, tokens)
                except ValueError as error:
                    errors.append(str(error)[:250])
                else:
                    from app.notes_jobs import register_note_sources

                    source = NoteSourceConfig(
                        source_key=f"discovered-{job['smv_rpj']}-{job['fiscal_year']}-{job['scope']}",
                        company_rpj=job["smv_rpj"],
                        fiscal_year=job["fiscal_year"],
                        period_code=job["period_code"],
                        scope=job["scope"],
                        language_code="es",
                        document_name=f"{name} - Estados financieros {job['fiscal_year']}",
                        source_url=url,
                        identity_tokens=tokens,
                    )
                    register_note_sources(connection, (source,))
                    documents.append({"url": url, "notes": len(extraction.notes)})
            connection.commit()
            if verified == pending and documents:
                break
        except (httpx.HTTPError, ValueError, PdfReadError) as error:
            errors.append(str(error)[:250])
    return {
        "verified": verified,
        "pending": pending - verified,
        "errors": errors,
        "documents": documents,
    }
