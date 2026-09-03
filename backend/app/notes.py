from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from psycopg import Connection
from pypdf import PdfReader

from app.cited_summaries import generate_and_store_cited_summary

NOTE_HEADING_RE = re.compile(r"(?m)^[ \t]*(\d{1,2})(\.)?[ \t]+([^\n]{3,180})")
MALFORMED_NOTE_HEADING_RE = re.compile(
    r"(?m)^[ \t]*\.[ \t]+(Juicios, estimados y supuestos contables significativos)[ \t]*$",
    re.IGNORECASE,
)
NOTES_MARKER = "notas a los estados financieros consolidados"
APPENDIX_HEADING_RE = re.compile(
    r"(?im)^[ \t]*(?:informaci[oó]n suplementaria|recursos minerales y reservas "
    r"probadas y probables)\b"
)
WRAPPED_FINANCIAL_POSITION_TITLE_RE = re.compile(
    r"\r?\n[ \t]*(FINANCIERA)[ \t]*(?:\r?\n|$)"
)
TRAILING_STOP_WORDS = {
    "al",
    "con",
    "de",
    "del",
    "el",
    "en",
    "la",
    "las",
    "los",
    "o",
    "para",
    "por",
    "que",
    "un",
    "una",
    "y",
}


@dataclass(frozen=True)
class NoteSourceConfig:
    source_key: str
    company_rpj: str
    fiscal_year: int
    period_code: str
    scope: str
    language_code: str
    document_name: str
    source_url: str
    identity_tokens: tuple[str, ...]


@dataclass(frozen=True)
class ExtractedSection:
    page_number: int
    section_order: int
    content_text: str


@dataclass(frozen=True)
class ExtractedNote:
    note_number: int
    original_title: str
    topic: str
    is_priority: bool
    start_page: int
    end_page: int
    content_text: str
    sections: tuple[ExtractedSection, ...]


@dataclass(frozen=True)
class ExtractionResult:
    page_count: int
    notes: tuple[ExtractedNote, ...]


@dataclass(frozen=True)
class _Heading:
    note_number: int
    title: str
    page_index: int
    start_offset: int
    end_offset: int


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} es obligatorio")
    return value.strip()


def validate_source_payload(payload: dict[str, Any]) -> NoteSourceConfig:
    source_url = _required_text(payload.get("source_url"), "source_url")
    parsed_url = urlparse(source_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("source_url debe ser una URL HTTPS absoluta")

    fiscal_year = payload.get("fiscal_year")
    if not isinstance(fiscal_year, int) or fiscal_year < 2000:
        raise ValueError("fiscal_year no es válido")
    period_code = _required_text(payload.get("period_code", "A"), "period_code")
    if period_code not in {"A", "1", "2", "3", "4"}:
        raise ValueError("period_code no es válido")
    scope = _required_text(payload.get("scope"), "scope")
    if scope not in {"individual", "consolidated"}:
        raise ValueError("scope no es válido")

    raw_tokens = payload.get("identity_tokens")
    if not isinstance(raw_tokens, list) or len(raw_tokens) < 2:
        raise ValueError("identity_tokens debe contener al menos dos textos")
    tokens = tuple(_required_text(token, "identity_tokens") for token in raw_tokens)

    return NoteSourceConfig(
        source_key=_required_text(payload.get("source_key"), "source_key"),
        company_rpj=_required_text(payload.get("company_rpj"), "company_rpj"),
        fiscal_year=fiscal_year,
        period_code=period_code,
        scope=scope,
        language_code=_required_text(payload.get("language_code", "es"), "language_code"),
        document_name=_required_text(payload.get("document_name"), "document_name"),
        source_url=source_url,
        identity_tokens=tokens,
    )


def load_note_sources(path: Path) -> tuple[NoteSourceConfig, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("El archivo de fuentes de notas debe contener una lista")
    sources = tuple(validate_source_payload(item) for item in payload)
    source_keys = {source.source_key for source in sources}
    if len(source_keys) != len(sources):
        raise ValueError("Las fuentes de notas contienen source_key duplicados")
    return sources


def classify_note_topic(title: str) -> str:
    normalized = _normalized(title)
    rules = (
        (
            "subsequent_events",
            ("hechos posteriores", "eventos posteriores", "eventos subsecuentes"),
        ),
        ("segments", ("segmento",)),
        ("contingencies", ("contingenc", "compromiso")),
        ("related_parties", ("relacionad", "entidades asociadas", "partes relacionadas")),
        ("estimates", ("juicios", "estimad", "supuestos significativos")),
        ("impairment", ("deterioro",)),
        ("provisions_closure", ("provisiones", "cierre de minas", "cierre de unidades")),
        ("debt", ("obligaciones financieras", "deuda", "borrowings")),
        (
            "capex_assets",
            (
                "propiedad, planta",
                "property, plant",
                "concesiones mineras",
                "costos de desarrollo",
            ),
        ),
    )
    for topic, keywords in rules:
        if any(keyword in normalized for keyword in keywords):
            return topic
    return "other"


def _clean_title(value: str) -> str:
    return " ".join(value.split()).rstrip(" –-:")


def _complete_wrapped_title(
    page_text: str, *, title: str, end_offset: int
) -> tuple[str, int]:
    """Recupera la última palabra cuando el PDF parte un título entre líneas."""
    if not _normalized(title).endswith("estado consolidado de situacion"):
        return title, end_offset
    continuation = WRAPPED_FINANCIAL_POSITION_TITLE_RE.match(page_text, end_offset)
    if continuation is None:
        return title, end_offset
    return f"{title} {continuation.group(1)}", continuation.end()


def _plausible_title(value: str, *, dotted_heading: bool = True) -> bool:
    if not value or len(value) > 120:
        return False
    # Algunos informes auditados (por ejemplo, Volcan) omiten el punto después
    # del número de nota. En ese formato los títulos son versales. Exigirlas
    # evita interpretar fechas como "31 de diciembre..." como una nota.
    if not dotted_heading and value != value.upper():
        return False
    last_word = value.rstrip(". ").split()[-1].lower()
    return last_word not in TRAILING_STOP_WORDS


def find_note_headings(page_texts: list[str]) -> tuple[_Heading, ...]:
    start_page = next(
        (
            index
            for index, text in enumerate(page_texts)
            if NOTES_MARKER in _normalized(text)
            and re.search(r"(?m)^\s*1(?:\.|\s)\s*", text)
        ),
        None,
    )
    if start_page is None:
        raise ValueError("No se encontró el inicio de las notas consolidadas")

    headings: list[_Heading] = []
    expected_number = 1
    for page_index in range(start_page, len(page_texts)):
        candidates = [
            (
                match.start(),
                match.end(),
                int(match.group(1)),
                match.group(3),
                match.group(2) is not None,
            )
            for match in NOTE_HEADING_RE.finditer(page_texts[page_index])
        ]
        # Algunos PDFs oficiales tienen glifos sin mapa Unicode. En el informe de
        # Buenaventura 2024 el "3" del encabezado de la nota 3 desaparece, aunque
        # sus subapartados 3.1 y 3.2 sí están presentes. Sólo reparamos este título
        # contable conocido y únicamente cuando la secuencia espera la nota 3.
        candidates.extend(
            (match.start(), match.end(), 3, match.group(1), True)
            for match in MALFORMED_NOTE_HEADING_RE.finditer(page_texts[page_index])
        )
        for start_offset, end_offset, note_number, raw_title, dotted_heading in sorted(
            candidates
        ):
            title = _clean_title(raw_title)
            title, end_offset = _complete_wrapped_title(
                page_texts[page_index], title=title, end_offset=end_offset
            )
            if note_number != expected_number or not _plausible_title(
                title, dotted_heading=dotted_heading
            ):
                continue
            headings.append(
                _Heading(
                    note_number=note_number,
                    title=title,
                    page_index=page_index,
                    start_offset=start_offset,
                    end_offset=end_offset,
                )
            )
            expected_number += 1

    if len(headings) < 5:
        raise ValueError(
            f"Sólo se detectaron {len(headings)} notas; el documento requiere revisión"
        )
    return tuple(headings)


def _clean_section_text(value: str) -> str:
    lines = []
    for raw_line in value.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        if _normalized(line).startswith(NOTES_MARKER):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def extract_notes_from_pages(page_texts: list[str]) -> tuple[ExtractedNote, ...]:
    headings = find_note_headings(page_texts)
    notes_pages = [
        index for index, text in enumerate(page_texts) if NOTES_MARKER in _normalized(text)
    ]
    last_notes_page = max(notes_pages)
    # Algunos emisores sólo imprimen el rótulo "Notas..." en la primera página.
    # Si hay encabezados posteriores, el documento auditado continúa hasta el
    # final y no debemos recortar la última nota en su propia página.
    if last_notes_page < headings[-1].page_index:
        last_notes_page = len(page_texts) - 1
    notes: list[ExtractedNote] = []

    for heading_index, heading in enumerate(headings):
        next_heading = headings[heading_index + 1] if heading_index + 1 < len(headings) else None
        final_page_index = next_heading.page_index if next_heading else last_notes_page
        sections: list[ExtractedSection] = []

        for page_index in range(heading.page_index, final_page_index + 1):
            start_offset = heading.end_offset if page_index == heading.page_index else 0
            end_offset = len(page_texts[page_index])
            if next_heading and page_index == next_heading.page_index:
                end_offset = next_heading.start_offset
            appendix_heading = None if next_heading else APPENDIX_HEADING_RE.search(
                page_texts[page_index], start_offset
            )
            if appendix_heading:
                end_offset = appendix_heading.start()
            section_text = _clean_section_text(page_texts[page_index][start_offset:end_offset])
            if section_text:
                sections.append(
                    ExtractedSection(
                        page_number=page_index + 1,
                        section_order=len(sections),
                        content_text=section_text,
                    )
                )
            if appendix_heading:
                break

        if not sections:
            raise ValueError(f"La nota {heading.note_number} no contiene texto extraíble")
        topic = classify_note_topic(heading.title)
        notes.append(
            ExtractedNote(
                note_number=heading.note_number,
                original_title=heading.title,
                topic=topic,
                is_priority=topic != "other",
                start_page=heading.page_index + 1,
                end_page=sections[-1].page_number,
                content_text="\n\n".join(section.content_text for section in sections),
                sections=tuple(sections),
            )
        )
    return tuple(notes)


def extract_notes_from_pdf(pdf_bytes: bytes, identity_tokens: tuple[str, ...]) -> ExtractionResult:
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("La fuente no devolvió un PDF válido")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if reader.is_encrypted:
        raise ValueError("El PDF está cifrado y no puede procesarse")
    page_texts = [(page.extract_text() or "") for page in reader.pages]
    document_text = _normalized("\n".join(page_texts))
    missing_tokens = [token for token in identity_tokens if _normalized(token) not in document_text]
    if missing_tokens:
        raise ValueError(f"El PDF no coincide con la fuente esperada: {missing_tokens}")
    notes = extract_notes_from_pages(page_texts)
    return ExtractionResult(page_count=len(reader.pages), notes=notes)


def download_pdf(source_url: str, *, timeout_seconds: float, max_bytes: int) -> bytes:
    headers = {
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
        "User-Agent": "Fundamenta/0.1 financial-notes-sync",
    }
    chunks: list[bytes] = []
    downloaded = 0
    with httpx.stream(
        "GET",
        source_url,
        headers=headers,
        follow_redirects=True,
        timeout=timeout_seconds,
    ) as response:
        response.raise_for_status()
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > max_bytes:
            raise ValueError("El PDF supera el límite configurado")
        for chunk in response.iter_bytes():
            downloaded += len(chunk)
            if downloaded > max_bytes:
                raise ValueError("El PDF supera el límite configurado")
            chunks.append(chunk)
    return b"".join(chunks)


def store_note_document(
    connection: Connection,
    *,
    source: dict[str, Any],
    pdf_bytes: bytes,
) -> dict[str, Any]:
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, version, notes_count
            FROM note_documents
            WHERE note_source_id = %s AND source_sha256 = %s
            """,
            (source["id"], digest),
        )
        existing = cursor.fetchone()
        cursor.execute(
            "UPDATE note_sources SET last_checked_at = NOW(), updated_at = NOW() WHERE id = %s",
            (source["id"],),
        )
        if existing:
            return {
                "status": "unchanged",
                "document_id": existing["id"],
                "version": existing["version"],
                "notes_count": existing["notes_count"],
                "source_sha256": digest,
            }

    identity_tokens = tuple(source["identity_tokens"])
    extraction = extract_notes_from_pdf(pdf_bytes, identity_tokens)

    with connection.cursor() as cursor:
        # Serializa la creación de versiones por fuente sin bloquear una consulta agregada.
        cursor.execute("SELECT id FROM note_sources WHERE id = %s FOR UPDATE", (source["id"],))
        cursor.execute(
            """
            SELECT COALESCE(MAX(version), 0) AS latest_version
            FROM note_documents
            WHERE note_source_id = %s
            """,
            (source["id"],),
        )
        next_version = cursor.fetchone()["latest_version"] + 1
        cursor.execute(
            "UPDATE note_documents SET is_current = FALSE WHERE note_source_id = %s AND is_current",
            (source["id"],),
        )
        cursor.execute(
            """
            INSERT INTO note_documents (
                note_source_id, company_id, fiscal_year, period_code, scope,
                version, document_name, source_url, source_sha256,
                file_size_bytes, page_count, notes_count, extraction_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'extracted')
            RETURNING id
            """,
            (
                source["id"],
                source["company_id"],
                source["fiscal_year"],
                source["period_code"],
                source["scope"],
                next_version,
                source["document_name"],
                source["source_url"],
                digest,
                len(pdf_bytes),
                extraction.page_count,
                len(extraction.notes),
            ),
        )
        document_id = cursor.fetchone()["id"]

        for note in extraction.notes:
            cursor.execute(
                """
                INSERT INTO financial_notes (
                    note_document_id, note_number, original_title, topic, is_priority,
                    start_page, end_page, content_text, extraction_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'extracted')
                RETURNING id
                """,
                (
                    document_id,
                    note.note_number,
                    note.original_title,
                    note.topic,
                    note.is_priority,
                    note.start_page,
                    note.end_page,
                    note.content_text,
                ),
            )
            note_id = cursor.fetchone()["id"]
            cursor.executemany(
                """
                INSERT INTO note_sections (
                    financial_note_id, page_number, section_order, content_text
                ) VALUES (%s, %s, %s, %s)
                """,
                [
                    (note_id, section.page_number, section.section_order, section.content_text)
                    for section in note.sections
                ],
            )
            cursor.executemany(
                """
                INSERT INTO source_fragments (
                    company_id, note_document_id, financial_note_id,
                    fragment_order, page_number, heading_text, content_text
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        source["company_id"],
                        document_id,
                        note_id,
                        section.section_order,
                        section.page_number,
                        note.original_title,
                        section.content_text,
                    )
                    for section in note.sections
                ],
            )
            generate_and_store_cited_summary(connection, note_id)

    return {
        "status": "imported" if next_version == 1 else "versioned",
        "document_id": document_id,
        "version": next_version,
        "notes_count": len(extraction.notes),
        "page_count": extraction.page_count,
        "source_sha256": digest,
    }
