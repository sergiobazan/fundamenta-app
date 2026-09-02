from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse

from psycopg import Connection

EVENT_CATEGORIES = {
    "dividends",
    "management",
    "meetings",
    "debt",
    "operations",
    "litigation",
    "production",
    "other",
}

REQUIRED_FIELDS = {
    "company_rpj",
    "source_provider",
    "external_id",
    "category",
    "title",
    "summary",
    "published_at",
    "source_url",
}


def validate_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(field for field in REQUIRED_FIELDS if not payload.get(field))
    if missing:
        raise ValueError(f"Faltan campos obligatorios: {', '.join(missing)}")

    category = str(payload["category"]).strip()
    if category not in EVENT_CATEGORIES:
        raise ValueError(f"Categoría no soportada: {category}")

    source_url = str(payload["source_url"]).strip()
    parsed_url = urlparse(source_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("La fuente del evento debe ser una URL HTTPS absoluta")

    published_at = datetime.fromisoformat(str(payload["published_at"]))
    if published_at.tzinfo is None:
        raise ValueError("published_at debe incluir zona horaria")

    effective_date = payload.get("effective_date")
    if effective_date:
        date.fromisoformat(str(effective_date))

    normalized = {
        "company_rpj": str(payload["company_rpj"]).strip(),
        "source_provider": str(payload["source_provider"]).strip(),
        "external_id": str(payload["external_id"]).strip(),
        "category": category,
        "title": str(payload["title"]).strip(),
        "summary": str(payload["summary"]).strip(),
        "published_at": published_at.isoformat(),
        "effective_date": str(effective_date) if effective_date else None,
        "source_url": source_url,
        "source_document_name": str(payload.get("source_document_name") or "").strip()
        or None,
        "source_metadata": payload.get("source_metadata") or {},
    }
    if len(normalized["title"]) > 240:
        raise ValueError("El título del evento no puede superar 240 caracteres")
    if len(normalized["summary"]) > 1200:
        raise ValueError("El resumen del evento no puede superar 1200 caracteres")
    return normalized


def event_payload_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def import_events(connection: Connection, payloads: list[dict[str, Any]]) -> dict[str, Any]:
    imported = 0
    unchanged = 0
    versioned = 0
    results: list[dict[str, Any]] = []

    with connection.cursor() as cursor:
        for raw_payload in payloads:
            payload = validate_event_payload(raw_payload)
            digest = event_payload_sha256(payload)
            cursor.execute(
                "SELECT id, legal_name FROM companies WHERE smv_rpj = %s",
                (payload["company_rpj"],),
            )
            company = cursor.fetchone()
            if company is None:
                raise ValueError(f"No existe la empresa RPJ {payload['company_rpj']}")

            cursor.execute(
                """
                SELECT id, version, source_sha256
                FROM corporate_events
                WHERE source_provider = %s AND external_id = %s AND is_current
                FOR UPDATE
                """,
                (payload["source_provider"], payload["external_id"]),
            )
            current = cursor.fetchone()
            if current and current["source_sha256"] == digest:
                unchanged += 1
                results.append(
                    {
                        "event_id": current["id"],
                        "external_id": payload["external_id"],
                        "status": "unchanged",
                        "version": current["version"],
                    }
                )
                continue

            next_version = (current["version"] + 1) if current else 1
            if current:
                cursor.execute(
                    "UPDATE corporate_events SET is_current = FALSE WHERE id = %s",
                    (current["id"],),
                )
                versioned += 1

            cursor.execute(
                """
                INSERT INTO corporate_events (
                    company_id, source_provider, external_id, version, category,
                    title, summary, published_at, effective_date, source_url,
                    source_document_name, source_sha256, source_payload
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    company["id"],
                    payload["source_provider"],
                    payload["external_id"],
                    next_version,
                    payload["category"],
                    payload["title"],
                    payload["summary"],
                    payload["published_at"],
                    payload["effective_date"],
                    payload["source_url"],
                    payload["source_document_name"],
                    digest,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            event_id = cursor.fetchone()["id"]
            imported += 1
            results.append(
                {
                    "event_id": event_id,
                    "external_id": payload["external_id"],
                    "status": "versioned" if current else "imported",
                    "version": next_version,
                }
            )

    return {
        "received": len(payloads),
        "imported": imported,
        "unchanged": unchanged,
        "versioned": versioned,
        "events": results,
    }
