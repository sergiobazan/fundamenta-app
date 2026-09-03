from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from psycopg import Connection

from app.cited_summaries import fetch_cited_summaries_by_ids, information_cutoff

GENERATOR_NAME = "fundamenta-note-matcher"
GENERATOR_VERSION = 5
MATCH_THRESHOLD = 0.48

STOP_WORDS = {
    "a",
    "al",
    "con",
    "de",
    "del",
    "el",
    "en",
    "la",
    "las",
    "los",
    "neto",
    "neta",
    "netos",
    "netas",
    "otras",
    "otros",
    "para",
    "por",
    "sobre",
    "y",
}

TOKEN_ALIASES = {
    "actividad": "actividad",
    "actividades": "actividad",
    "evento": "posterior",
    "eventos": "posterior",
    "hecho": "posterior",
    "hechos": "posterior",
    "ingreso": "ventas",
    "ingresos": "ventas",
    "ordinaria": "ventas",
    "ordinarias": "ventas",
    "posterior": "posterior",
    "posteriores": "posterior",
    "subsecuente": "posterior",
    "subsecuentes": "posterior",
    "venta": "ventas",
    "ventas": "ventas",
}


@dataclass(frozen=True)
class NoteMatch:
    current: dict[str, Any] | None
    previous: dict[str, Any] | None
    status: str
    method: str
    score: float
    confidence: str
    confidence_reason: str


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    plain = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def _title_tokens(value: str) -> set[str]:
    tokens = set()
    for token in _normalized(value).split():
        if token in STOP_WORDS or len(token) < 3:
            continue
        tokens.add(TOKEN_ALIASES.get(token, token))
    if "ventas" in tokens:
        tokens.discard("actividad")
    return tokens


def title_similarity(current_title: str, previous_title: str) -> float:
    current_normalized = _normalized(current_title)
    previous_normalized = _normalized(previous_title)
    if current_normalized == previous_normalized:
        return 1.0
    current_tokens = _title_tokens(current_title)
    previous_tokens = _title_tokens(previous_title)
    union = current_tokens | previous_tokens
    jaccard = len(current_tokens & previous_tokens) / len(union) if union else 0.0
    sequence = SequenceMatcher(None, current_normalized, previous_normalized).ratio()
    score = jaccard * 0.8 + sequence * 0.2
    # Los emisores alternan "hechos posteriores" y "eventos posteriores al
    # cierre..." para la misma clase de revelación. El alias semántico evita
    # presentar ese cambio editorial como una nota nueva o eliminada.
    if "posterior" in current_tokens and "posterior" in previous_tokens:
        score = max(score, 0.85)
    return round(min(1.0, score), 4)


def _match_confidence(score: float, method: str) -> tuple[str, str]:
    if method == "normalized_title" or score >= 0.82:
        return "high", "Los títulos normalizados coinciden de forma directa o casi exacta."
    if score >= 0.62:
        return (
            "medium",
            "Los títulos comparten suficientes términos para tratarlos como equivalentes.",
        )
    return (
        "low",
        "La equivalencia es aproximada; conviene confirmar ambos títulos y sus citas.",
    )


def match_notes(
    current_notes: list[dict[str, Any]], previous_notes: list[dict[str, Any]]
) -> list[NoteMatch]:
    remaining_current = {note["id"]: note for note in current_notes}
    remaining_previous = {note["id"]: note for note in previous_notes}
    matches: list[NoteMatch] = []

    previous_by_title: dict[str, list[dict[str, Any]]] = {}
    for note in previous_notes:
        previous_by_title.setdefault(_normalized(note["original_title"]), []).append(note)

    for current in current_notes:
        candidates = previous_by_title.get(_normalized(current["original_title"]), [])
        previous = next(
            (item for item in candidates if item["id"] in remaining_previous),
            None,
        )
        if previous is None:
            continue
        confidence, reason = _match_confidence(1.0, "normalized_title")
        matches.append(
            NoteMatch(
                current=current,
                previous=previous,
                status="matched",
                method="normalized_title",
                score=1.0,
                confidence=confidence,
                confidence_reason=reason,
            )
        )
        remaining_current.pop(current["id"])
        remaining_previous.pop(previous["id"])

    candidates: list[tuple[float, int, int]] = []
    for current in remaining_current.values():
        for previous in remaining_previous.values():
            score = title_similarity(current["original_title"], previous["original_title"])
            if current["note_number"] == previous["note_number"]:
                score = min(1.0, score + 0.05)
            if current["topic"] == previous["topic"] and current["topic"] != "other":
                score = min(1.0, score + 0.03)
            if score >= MATCH_THRESHOLD:
                candidates.append((round(score, 4), current["id"], previous["id"]))

    for score, current_id, previous_id in sorted(
        candidates, key=lambda item: (-item[0], item[1], item[2])
    ):
        current = remaining_current.get(current_id)
        previous = remaining_previous.get(previous_id)
        if current is None or previous is None:
            continue
        confidence, reason = _match_confidence(score, "title_similarity")
        matches.append(
            NoteMatch(
                current=current,
                previous=previous,
                status="matched",
                method="title_similarity",
                score=score,
                confidence=confidence,
                confidence_reason=reason,
            )
        )
        remaining_current.pop(current_id)
        remaining_previous.pop(previous_id)

    for current in remaining_current.values():
        matches.append(
            NoteMatch(
                current=current,
                previous=None,
                status="current_only",
                method="none",
                score=0.0,
                confidence="low",
                confidence_reason=(
                    "No se encontró un título suficientemente equivalente en el período anterior."
                ),
            )
        )
    for previous in remaining_previous.values():
        matches.append(
            NoteMatch(
                current=None,
                previous=previous,
                status="previous_only",
                method="none",
                score=0.0,
                confidence="low",
                confidence_reason=(
                    "No se encontró un título suficientemente equivalente en el período actual."
                ),
            )
        )

    return sorted(
        matches,
        key=lambda match: (
            match.current["note_number"] if match.current else 10_000,
            match.previous["note_number"] if match.previous else 10_000,
        ),
    )


def _document_notes(connection: Connection, document_id: int) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                fn.id, fn.note_number, fn.original_title, fn.topic, fn.is_priority,
                summary.id AS cited_summary_id,
                COALESCE(summary.observed_facts, 0) AS observed_facts
            FROM financial_notes fn
            LEFT JOIN LATERAL (
                SELECT
                    cs.id,
                    (SELECT COUNT(*) FROM cited_summary_items item
                     WHERE item.cited_summary_id = cs.id
                       AND item.section_kind = 'observed_fact') AS observed_facts
                FROM cited_summaries cs
                WHERE cs.financial_note_id = fn.id
                ORDER BY cs.generator_version DESC, cs.generated_at DESC, cs.id DESC
                LIMIT 1
            ) summary ON TRUE
            WHERE fn.note_document_id = %s
            ORDER BY fn.note_number
            """,
            (document_id,),
        )
        return list(cursor.fetchall())


def _overall_confidence(matches: list[NoteMatch]) -> tuple[str, str, str]:
    current_count = sum(match.current is not None for match in matches)
    matched = [match for match in matches if match.status == "matched"]
    coverage = len(matched) / current_count if current_count else 0.0
    with_evidence = sum(
        bool(match.current and match.previous)
        and match.current["observed_facts"] > 0
        and match.previous["observed_facts"] > 0
        for match in matched
    )
    evidence_coverage = with_evidence / len(matched) if matched else 0.0
    if coverage >= 0.9 and evidence_coverage >= 0.75:
        return (
            "generated",
            "high",
            "Al menos 90 % de las notas actuales tienen equivalente y evidencia "
            "citada en ambos períodos.",
        )
    if coverage >= 0.65 and evidence_coverage >= 0.5:
        return (
            "partial",
            "medium",
            "La mayoría de notas pudo emparejarse, aunque la cobertura citada no es completa.",
        )
    if matched:
        return (
            "partial",
            "low",
            "La cobertura de equivalencias o evidencia es limitada; no deben inferirse "
            "cambios generales.",
        )
    return (
        "insufficient_evidence",
        "low",
        "No se encontraron notas equivalentes con evidencia suficiente entre ambos períodos.",
    )


def generate_and_store_comparison(
    connection: Connection, current_document_id: int, previous_document_id: int
) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM narrative_comparisons
            WHERE current_note_document_id = %s
              AND previous_note_document_id = %s
              AND generator_name = %s
              AND generator_version = %s
            """,
            (current_document_id, previous_document_id, GENERATOR_NAME, GENERATOR_VERSION),
        )
        if cursor.fetchone() is not None:
            return {"status": "unchanged", "current_document_id": current_document_id}

        cursor.execute(
            """
            SELECT
                current.company_id,
                current.fiscal_year AS current_year,
                current.period_code,
                current.scope,
                current.source_sha256 AS current_sha256,
                previous.fiscal_year AS previous_year,
                previous.source_sha256 AS previous_sha256
            FROM note_documents current
            JOIN note_documents previous ON previous.id = %s
            WHERE current.id = %s
              AND current.company_id = previous.company_id
              AND current.period_code = previous.period_code
              AND current.scope = previous.scope
              AND previous.fiscal_year = current.fiscal_year - 1
            """,
            (previous_document_id, current_document_id),
        )
        documents = cursor.fetchone()
        if documents is None:
            raise ValueError(
                "Los documentos no representan períodos anuales consecutivos comparables"
            )

    current_notes = _document_notes(connection, current_document_id)
    previous_notes = _document_notes(connection, previous_document_id)
    matches = match_notes(current_notes, previous_notes)
    status, confidence, confidence_reason = _overall_confidence(matches)
    input_sha256 = hashlib.sha256(
        (
            f"{documents['current_sha256']}:{documents['previous_sha256']}:"
            f"{GENERATOR_NAME}:{GENERATOR_VERSION}"
        ).encode()
    ).hexdigest()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO narrative_comparisons (
                company_id, current_note_document_id, previous_note_document_id,
                generator_name, generator_version, status, confidence,
                confidence_reason, information_cutoff, input_sha256
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (
                current_note_document_id, previous_note_document_id,
                generator_name, generator_version
            ) DO NOTHING
            RETURNING id
            """,
            (
                documents["company_id"],
                current_document_id,
                previous_document_id,
                GENERATOR_NAME,
                GENERATOR_VERSION,
                status,
                confidence,
                confidence_reason,
                information_cutoff(documents["current_year"], documents["period_code"]),
                input_sha256,
            ),
        )
        inserted = cursor.fetchone()
        if inserted is None:
            return {"status": "unchanged", "current_document_id": current_document_id}
        comparison_id = inserted["id"]

        for item_order, match in enumerate(matches):
            cursor.execute(
                """
                INSERT INTO narrative_comparison_notes (
                    narrative_comparison_id,
                    current_financial_note_id, previous_financial_note_id,
                    current_cited_summary_id, previous_cited_summary_id,
                    match_status, match_method, similarity_score,
                    confidence, confidence_reason, item_order
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    comparison_id,
                    match.current["id"] if match.current else None,
                    match.previous["id"] if match.previous else None,
                    match.current["cited_summary_id"] if match.current else None,
                    match.previous["cited_summary_id"] if match.previous else None,
                    match.status,
                    match.method,
                    match.score,
                    match.confidence,
                    match.confidence_reason,
                    item_order,
                ),
            )

    return {
        "status": "created",
        "comparison_id": comparison_id,
        "current_document_id": current_document_id,
        "matched": sum(match.status == "matched" for match in matches),
        "confidence": confidence,
    }


def sync_narrative_comparisons(connection: Connection) -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT current.id AS current_id, previous.id AS previous_id
            FROM note_documents current
            JOIN note_documents previous
              ON previous.company_id = current.company_id
             AND previous.fiscal_year = current.fiscal_year - 1
             AND previous.period_code = current.period_code
             AND previous.scope = current.scope
             AND previous.is_current
            WHERE current.is_current
            ORDER BY current.company_id, current.fiscal_year
            """
        )
        document_pairs = list(cursor.fetchall())

    created = 0
    unchanged = 0
    for pair in document_pairs:
        result = generate_and_store_comparison(
            connection, pair["current_id"], pair["previous_id"]
        )
        if result["status"] == "created":
            created += 1
        else:
            unchanged += 1
    return {"pairs": len(document_pairs), "created": created, "unchanged": unchanged}


def fetch_narrative_comparison(
    connection: Connection,
    *,
    company_rpj: str,
    current_year: int,
    previous_year: int,
    period_code: str,
    scope: str,
) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                comparison.id, comparison.generator_name, comparison.generator_version,
                comparison.status, comparison.confidence, comparison.confidence_reason,
                comparison.information_cutoff, comparison.input_sha256,
                comparison.generated_at,
                company.smv_rpj, company.legal_name,
                current.fiscal_year AS current_year,
                current.document_name AS current_document_name,
                current.source_url AS current_source_url,
                current.source_sha256 AS current_source_sha256,
                current.version AS current_document_version,
                previous.fiscal_year AS previous_year,
                previous.document_name AS previous_document_name,
                previous.source_url AS previous_source_url,
                previous.source_sha256 AS previous_source_sha256,
                previous.version AS previous_document_version
            FROM narrative_comparisons comparison
            JOIN companies company ON company.id = comparison.company_id
            JOIN note_documents current ON current.id = comparison.current_note_document_id
            JOIN note_documents previous ON previous.id = comparison.previous_note_document_id
            WHERE company.smv_rpj = %s
              AND current.fiscal_year = %s
              AND previous.fiscal_year = %s
              AND current.period_code = %s
              AND current.scope = %s
              AND current.is_current
              AND previous.is_current
            ORDER BY comparison.generator_version DESC, comparison.generated_at DESC
            LIMIT 1
            """,
            (company_rpj, current_year, previous_year, period_code, scope),
        )
        comparison = cursor.fetchone()
        if comparison is None:
            return None
        comparison_id = comparison.pop("id")
        cursor.execute(
            """
            SELECT
                pair.match_status, pair.match_method, pair.similarity_score,
                pair.confidence, pair.confidence_reason, pair.item_order,
                current.id AS current_id, current.note_number AS current_note_number,
                current.original_title AS current_title, current.topic AS current_topic,
                current.is_priority AS current_is_priority,
                previous.id AS previous_id, previous.note_number AS previous_note_number,
                previous.original_title AS previous_title, previous.topic AS previous_topic,
                previous.is_priority AS previous_is_priority,
                pair.current_cited_summary_id, pair.previous_cited_summary_id
            FROM narrative_comparison_notes pair
            LEFT JOIN financial_notes current ON current.id = pair.current_financial_note_id
            LEFT JOIN financial_notes previous ON previous.id = pair.previous_financial_note_id
            WHERE pair.narrative_comparison_id = %s
            ORDER BY pair.item_order
            """,
            (comparison_id,),
        )
        pairs = list(cursor.fetchall())

    summary_ids = [
        summary_id
        for pair in pairs
        for summary_id in (
            pair["current_cited_summary_id"],
            pair["previous_cited_summary_id"],
        )
        if summary_id is not None
    ]
    summaries = fetch_cited_summaries_by_ids(connection, summary_ids)

    items = []
    for pair in pairs:
        current_summary = (
            summaries.get(pair["current_cited_summary_id"])
            if pair["current_cited_summary_id"]
            else None
        )
        previous_summary = (
            summaries.get(pair["previous_cited_summary_id"])
            if pair["previous_cited_summary_id"]
            else None
        )
        items.append(
            {
                "match_status": pair["match_status"],
                "match_method": pair["match_method"],
                "similarity_score": float(pair["similarity_score"]),
                "confidence": pair["confidence"],
                "confidence_reason": pair["confidence_reason"],
                "is_priority": bool(
                    pair["current_is_priority"] or pair["previous_is_priority"]
                ),
                "current": (
                    {
                        "note_number": pair["current_note_number"],
                        "title": pair["current_title"],
                        "topic": pair["current_topic"],
                        "summary": current_summary,
                    }
                    if pair["current_id"]
                    else None
                ),
                "previous": (
                    {
                        "note_number": pair["previous_note_number"],
                        "title": pair["previous_title"],
                        "topic": pair["previous_topic"],
                        "summary": previous_summary,
                    }
                    if pair["previous_id"]
                    else None
                ),
            }
        )

    matched = sum(item["match_status"] == "matched" for item in items)
    current_only = sum(item["match_status"] == "current_only" for item in items)
    previous_only = sum(item["match_status"] == "previous_only" for item in items)
    return {
        **comparison,
        "coverage": {
            "matched": matched,
            "current_only": current_only,
            "previous_only": previous_only,
            "current_total": matched + current_only,
            "previous_total": matched + previous_only,
        },
        "interpretation_status": "not_generated",
        "items": items,
    }
