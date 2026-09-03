from typing import Any

from psycopg import Connection


def escape_like(value: str) -> str:
    """Escapa comodines para que la búsqueda literal no amplíe resultados."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_source_fragments(
    connection: Connection,
    *,
    query: str,
    company_rpj: str | None = None,
    topic: str | None = None,
    fiscal_year: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    normalized_query = " ".join(query.split())
    conditions = [
        "nd.is_current",
        "(sf.search_vector @@ search_query.value "
        "OR sf.heading_text ILIKE %s ESCAPE '\\' "
        "OR sf.content_text ILIKE %s ESCAPE '\\')",
    ]
    literal_search = f"%{escape_like(normalized_query)}%"
    parameters: list[object] = [normalized_query, literal_search, literal_search]

    if company_rpj:
        conditions.append("c.smv_rpj = %s")
        parameters.append(company_rpj)
    if topic:
        conditions.append("fn.topic = %s")
        parameters.append(topic)
    if fiscal_year:
        conditions.append("nd.fiscal_year = %s")
        parameters.append(fiscal_year)

    parameters.extend([limit, offset])
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            WITH search_query AS (
                SELECT WEBSEARCH_TO_TSQUERY('spanish'::REGCONFIG, %s) AS value
            )
            SELECT
                sf.id,
                c.smv_rpj,
                c.legal_name,
                nd.fiscal_year,
                nd.period_code,
                nd.scope,
                nd.document_name,
                nd.source_url,
                nd.source_sha256,
                nd.version AS document_version,
                fn.note_number,
                fn.original_title,
                fn.topic,
                fn.is_priority,
                sf.page_number,
                sf.fragment_order,
                REPLACE(
                    REGEXP_REPLACE(
                        TS_HEADLINE(
                            'spanish'::REGCONFIG,
                            sf.content_text,
                            search_query.value,
                            'MaxFragments=2, MinWords=12, MaxWords=38, FragmentDelimiter=__CUT__'
                        ),
                        '</?b>',
                        '',
                        'g'
                    ),
                    '__CUT__',
                    ' … '
                ) AS excerpt,
                ROUND(TS_RANK_CD(sf.search_vector, search_query.value)::NUMERIC, 6) AS rank,
                COUNT(*) OVER() AS total_count
            FROM source_fragments sf
            JOIN companies c ON c.id = sf.company_id
            JOIN note_documents nd ON nd.id = sf.note_document_id
            JOIN financial_notes fn ON fn.id = sf.financial_note_id
            CROSS JOIN search_query
            WHERE {' AND '.join(conditions)}
            ORDER BY
                TS_RANK_CD(sf.search_vector, search_query.value) DESC,
                fn.is_priority DESC,
                c.legal_name,
                fn.note_number,
                sf.page_number,
                sf.fragment_order
            LIMIT %s OFFSET %s
            """,
            parameters,
        )
        rows = list(cursor.fetchall())

    total = rows[0]["total_count"] if rows else 0
    for row in rows:
        row.pop("total_count")
    return {
        "query": normalized_query,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "company_rpj": company_rpj,
            "topic": topic,
            "fiscal_year": fiscal_year,
        },
        "results": rows,
    }
