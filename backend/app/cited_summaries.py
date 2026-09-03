from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Any

from psycopg import Connection

GENERATOR_NAME = "fundamenta-extractive"
GENERATOR_VERSION = 5
MAX_FACTS = 3

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "debt": ("deuda", "obligacion", "prestamo", "bono", "financiam", "covenant", "credito"),
    "segments": ("segmento", "unidad", "operacion", "produccion", "venta", "ingreso"),
    "capex_assets": ("activo", "propiedad", "planta", "equipo", "desarrollo", "capex", "inversion"),
    "impairment": ("deterioro", "recuperable", "desvaloriz", "valor en uso", "provision"),
    "provisions_closure": ("provision", "cierre", "remediacion", "ambiental", "desmantel"),
    "contingencies": ("contingencia", "proceso", "litigio", "sunat", "demanda", "reclamacion"),
    "related_parties": ("relacionad", "vinculad", "directorio", "gerencia", "accionista"),
    "estimates": ("estimacion", "supuesto", "juicio", "incertidumbre", "sensibilidad"),
    "subsequent_events": ("posterior", "subsecuente", "dividendo", "emision", "directorio"),
    "other": ("increment", "disminu", "saldo", "importe", "resultado", "operacion"),
}

MATERIAL_TERMS = (
    "increment",
    "disminu",
    "cumpl",
    "pendiente",
    "significativ",
    "restric",
    "riesgo",
    "vencimiento",
    "cancel",
    "pago",
    "emision",
    "aprobo",
    "acordo",
    "no ha hecho uso",
)
NARRATIVE_VERBS = (
    "acordo",
    "aprobo",
    "asciende",
    "cancel",
    "considera",
    "corresponde",
    "efectuo",
    "emitio",
    "firmo",
    "mantiene",
    "reconocio",
    "registro",
    "suscribio",
    "tiene",
)
SENTENCE_BOUNDARY_RE = re.compile(
    r"(?<=[.!?])\s+(?=(?:-\s*[A-ZÁÉÍÓÚÑ0-9]|\([a-z]\)|[A-ZÁÉÍÓÚÑ0-9]))"
)
LEADING_PAGE_RE = re.compile(r"^\s*\d{1,3}\s+(?=[A-ZÁÉÍÓÚÑ(\-])")
INVESTMENT_ADVICE_RE = re.compile(
    r"\b(?:comprar|vender|mantener)\b.{0,50}\b(?:accion|acciones|valor|valores|inversion)\b"
)


@dataclass(frozen=True)
class SummaryEvidence:
    source_fragment_id: int
    page_number: int
    fragment_order: int
    statement_text: str
    score: float


def _searchable(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _clean_text(value: str) -> str:
    value = LEADING_PAGE_RE.sub("", value)
    return " ".join(value.split())


def _sentences(value: str) -> list[str]:
    cleaned = _clean_text(value)
    if not cleaned:
        return []
    return [part.strip(" -") for part in SENTENCE_BOUNDARY_RE.split(cleaned) if part.strip(" -")]


def _is_narrative(sentence: str) -> bool:
    if not 70 <= len(sentence) <= 560:
        return False
    if sentence.count("_") > 3:
        return False
    numeric_tokens = len(re.findall(r"\b\d[\d.,]*", sentence))
    if numeric_tokens > 10:
        return False
    letters = sum(character.isalpha() for character in sentence)
    digits = sum(character.isdigit() for character in sentence)
    if letters / len(sentence) < 0.48 or digits / len(sentence) > 0.18:
        return False
    words = sentence.split()
    if len(words) < 11:
        return False
    searchable = _searchable(sentence)
    if numeric_tokens >= 4 and not any(verb in searchable for verb in NARRATIVE_VERBS):
        return False
    if INVESTMENT_ADVICE_RE.search(searchable):
        return False
    if searchable.startswith(("a continuacion presentamos", "a continuacion se presenta")):
        return False
    return True


def _score_sentence(sentence: str, *, topic: str, fiscal_year: int) -> float:
    searchable = _searchable(sentence)
    score = 1.0
    hits = sum(keyword in searchable for keyword in TOPIC_KEYWORDS.get(topic, ()))
    score += min(hits, 3) * 1.6
    if re.search(r"(?:US\$|S/|%|\b\d{1,3}(?:[.,]\d{3})+)", sentence):
        score += 1.8
    if str(fiscal_year) in sentence:
        score += 0.8
    score += min(sum(term in searchable for term in MATERIAL_TERMS), 2) * 1.0
    if 110 <= len(sentence) <= 380:
        score += 0.5
    if "normas internacionales de informacion financiera" in searchable:
        score -= 1.5
    return score


def _word_set(value: str) -> set[str]:
    return {word for word in re.findall(r"[a-záéíóúñ]{4,}", value.lower())}


def _too_similar(candidate: str, selected: list[SummaryEvidence]) -> bool:
    candidate_words = _word_set(candidate)
    for evidence in selected:
        selected_words = _word_set(evidence.statement_text)
        union = candidate_words | selected_words
        if union and len(candidate_words & selected_words) / len(union) >= 0.62:
            return True
    return False


def select_summary_evidence(
    fragments: list[dict[str, Any]],
    *,
    topic: str,
    fiscal_year: int,
    max_items: int = MAX_FACTS,
) -> list[SummaryEvidence]:
    candidates: list[SummaryEvidence] = []
    for fragment in fragments:
        for sentence_order, sentence in enumerate(_sentences(fragment["content_text"])):
            if not _is_narrative(sentence):
                continue
            candidates.append(
                SummaryEvidence(
                    source_fragment_id=fragment["id"],
                    page_number=fragment["page_number"],
                    fragment_order=fragment["fragment_order"] * 100 + sentence_order,
                    statement_text=sentence,
                    score=_score_sentence(sentence, topic=topic, fiscal_year=fiscal_year),
                )
            )

    candidates.sort(key=lambda item: (-item.score, item.page_number, item.fragment_order))
    selected: list[SummaryEvidence] = []
    fragment_usage: dict[int, int] = {}
    for candidate in candidates:
        if fragment_usage.get(candidate.source_fragment_id, 0) >= 2:
            continue
        if _too_similar(candidate.statement_text, selected):
            continue
        selected.append(candidate)
        fragment_usage[candidate.source_fragment_id] = (
            fragment_usage.get(candidate.source_fragment_id, 0) + 1
        )
        if len(selected) == max_items:
            break
    return selected


def information_cutoff(fiscal_year: int, period_code: str) -> date:
    month_and_day = {
        "1": (3, 31),
        "2": (6, 30),
        "3": (9, 30),
        "4": (12, 31),
        "A": (12, 31),
    }
    month, day = month_and_day[period_code]
    return date(fiscal_year, month, day)


def _confidence(facts: list[SummaryEvidence]) -> tuple[str, str, str]:
    distinct_pages = len({fact.page_number for fact in facts})
    if len(facts) == 3 and distinct_pages >= 2:
        return (
            "generated",
            "high",
            "Se seleccionaron tres hechos narrativos respaldados por más de una página.",
        )
    if len(facts) >= 2:
        return (
            "generated",
            "medium",
            "Se encontraron al menos dos hechos narrativos citables en el documento.",
        )
    if facts:
        return (
            "partial",
            "low",
            "Sólo se encontró un hecho narrativo suficientemente legible para citar.",
        )
    return (
        "insufficient_evidence",
        "low",
        "No se encontró texto narrativo suficientemente legible para resumir sin inferencias.",
    )


def generate_and_store_cited_summary(
    connection: Connection,
    financial_note_id: int,
) -> dict[str, Any]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM cited_summaries
            WHERE financial_note_id = %s
              AND generator_name = %s
              AND generator_version = %s
            """,
            (financial_note_id, GENERATOR_NAME, GENERATOR_VERSION),
        )
        if cursor.fetchone() is not None:
            return {"status": "unchanged", "financial_note_id": financial_note_id}

        cursor.execute(
            """
            SELECT
                fn.id, fn.note_number, fn.topic, fn.content_text,
                nd.company_id, nd.fiscal_year, nd.period_code, nd.scope,
                nd.source_sha256
            FROM financial_notes fn
            JOIN note_documents nd ON nd.id = fn.note_document_id
            WHERE fn.id = %s
            """,
            (financial_note_id,),
        )
        note = cursor.fetchone()
        if note is None:
            raise ValueError("La nota financiera no existe")

        cursor.execute(
            """
            SELECT id, page_number, fragment_order, content_text
            FROM source_fragments
            WHERE financial_note_id = %s
            ORDER BY page_number, fragment_order
            """,
            (financial_note_id,),
        )
        fragments = list(cursor.fetchall())
        facts = select_summary_evidence(
            fragments,
            topic=note["topic"],
            fiscal_year=note["fiscal_year"],
        )
        status, confidence, confidence_reason = _confidence(facts)

        cursor.execute(
            """
            INSERT INTO cited_summaries (
                financial_note_id, generator_name, generator_version,
                generation_method, status, confidence, confidence_reason,
                information_cutoff, input_sha256
            ) VALUES (%s, %s, %s, 'extractive', %s, %s, %s, %s, %s)
            ON CONFLICT (financial_note_id, generator_name, generator_version)
            DO NOTHING
            RETURNING id
            """,
            (
                financial_note_id,
                GENERATOR_NAME,
                GENERATOR_VERSION,
                status,
                confidence,
                confidence_reason,
                information_cutoff(note["fiscal_year"], note["period_code"]),
                note["source_sha256"],
            ),
        )
        inserted = cursor.fetchone()
        if inserted is None:
            return {"status": "unchanged", "financial_note_id": financial_note_id}
        summary_id = inserted["id"]

        for item_order, fact in enumerate(facts):
            cursor.execute(
                """
                INSERT INTO cited_summary_items (
                    cited_summary_id, section_kind, item_order,
                    statement_text, source_fragment_id
                ) VALUES (%s, 'observed_fact', %s, %s, %s)
                """,
                (summary_id, item_order, fact.statement_text, fact.source_fragment_id),
            )

        missing_data: list[str] = []
        if any("US$(000)" in fragment["content_text"] for fragment in fragments):
            missing_data.append(
                "La nota contiene tablas cuya estructura todavía no está reconstruida; "
                "confirma importes, columnas y escala en el PDF."
            )
        if len(facts) < 2:
            missing_data.append(
                "El texto narrativo recuperable es limitado y no permite un resumen completo."
            )
        for item_order, statement in enumerate(missing_data):
            cursor.execute(
                """
                INSERT INTO cited_summary_items (
                    cited_summary_id, section_kind, item_order, statement_text
                ) VALUES (%s, 'missing_data', %s, %s)
                """,
                (summary_id, item_order, statement),
            )

    return {
        "status": "created",
        "financial_note_id": financial_note_id,
        "summary_id": summary_id,
        "facts": len(facts),
        "confidence": confidence,
    }


def sync_cited_summaries(connection: Connection) -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT fn.id
            FROM financial_notes fn
            JOIN note_documents nd ON nd.id = fn.note_document_id
            WHERE nd.is_current
            ORDER BY fn.id
            """
        )
        note_ids = [row["id"] for row in cursor.fetchall()]

    created = 0
    unchanged = 0
    for note_id in note_ids:
        result = generate_and_store_cited_summary(connection, note_id)
        if result["status"] == "created":
            created += 1
        else:
            unchanged += 1
    return {"notes": len(note_ids), "created": created, "unchanged": unchanged}


def fetch_cited_summary(connection: Connection, financial_note_id: int) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM cited_summaries
            WHERE financial_note_id = %s
            ORDER BY generator_version DESC, generated_at DESC, id DESC
            LIMIT 1
            """,
            (financial_note_id,),
        )
        summary = cursor.fetchone()
        if summary is None:
            return None
    return fetch_cited_summary_by_id(connection, summary["id"])


def fetch_cited_summary_by_id(
    connection: Connection, cited_summary_id: int
) -> dict[str, Any] | None:
    return fetch_cited_summaries_by_ids(connection, [cited_summary_id]).get(cited_summary_id)


def fetch_cited_summaries_by_ids(
    connection: Connection, cited_summary_ids: list[int]
) -> dict[int, dict[str, Any]]:
    if not cited_summary_ids:
        return {}
    unique_ids = sorted(set(cited_summary_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id, generator_name, generator_version, generation_method,
                status, confidence, confidence_reason, information_cutoff,
                input_sha256, generated_at
            FROM cited_summaries
            WHERE id = ANY(%s)
            """,
            (unique_ids,),
        )
        summaries = {summary["id"]: summary for summary in cursor.fetchall()}
        cursor.execute(
            """
            SELECT
                item.cited_summary_id, item.section_kind, item.item_order,
                item.statement_text,
                sf.id AS source_fragment_id, sf.page_number,
                nd.document_name, nd.source_url, nd.version AS document_version
            FROM cited_summary_items item
            LEFT JOIN source_fragments sf ON sf.id = item.source_fragment_id
            LEFT JOIN note_documents nd ON nd.id = sf.note_document_id
            WHERE item.cited_summary_id = ANY(%s)
            ORDER BY item.cited_summary_id, item.section_kind, item.item_order
            """,
            (unique_ids,),
        )
        items = list(cursor.fetchall())

    items_by_summary: dict[int, list[dict[str, Any]]] = {}
    for item in items:
        items_by_summary.setdefault(item["cited_summary_id"], []).append(item)

    payloads = {}
    for summary_id, stored_summary in summaries.items():
        summary = {key: value for key, value in stored_summary.items() if key != "id"}
        observed_facts = []
        interpretations = []
        missing_data = []
        for item in items_by_summary.get(summary_id, []):
            payload = {"text": item["statement_text"], "item_order": item["item_order"]}
            if item["section_kind"] == "observed_fact":
                payload["citation"] = {
                    "source_fragment_id": item["source_fragment_id"],
                    "page_number": item["page_number"],
                    "document_name": item["document_name"],
                    "source_url": item["source_url"],
                    "document_version": item["document_version"],
                }
                observed_facts.append(payload)
            elif item["section_kind"] == "interpretation":
                interpretations.append(payload)
            else:
                missing_data.append(payload)
        payloads[summary_id] = {
            **summary,
            "observed_facts": observed_facts,
            "interpretations": interpretations,
            "interpretation_status": (
                "not_generated" if not interpretations else "generated"
            ),
            "missing_data": missing_data,
        }
    return payloads
