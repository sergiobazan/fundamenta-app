BEGIN;

CREATE TABLE IF NOT EXISTS narrative_comparisons (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    current_note_document_id BIGINT NOT NULL REFERENCES note_documents(id) ON DELETE CASCADE,
    previous_note_document_id BIGINT NOT NULL REFERENCES note_documents(id) ON DELETE CASCADE,
    generator_name TEXT NOT NULL,
    generator_version INTEGER NOT NULL CHECK (generator_version > 0),
    status TEXT NOT NULL CHECK (status IN ('generated', 'partial', 'insufficient_evidence')),
    confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    confidence_reason TEXT NOT NULL,
    information_cutoff DATE NOT NULL,
    input_sha256 CHAR(64) NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (current_note_document_id <> previous_note_document_id),
    UNIQUE (
        current_note_document_id,
        previous_note_document_id,
        generator_name,
        generator_version
    )
);

CREATE TABLE IF NOT EXISTS narrative_comparison_notes (
    id BIGSERIAL PRIMARY KEY,
    narrative_comparison_id BIGINT NOT NULL
        REFERENCES narrative_comparisons(id) ON DELETE CASCADE,
    current_financial_note_id BIGINT REFERENCES financial_notes(id) ON DELETE CASCADE,
    previous_financial_note_id BIGINT REFERENCES financial_notes(id) ON DELETE CASCADE,
    current_cited_summary_id BIGINT REFERENCES cited_summaries(id) ON DELETE SET NULL,
    previous_cited_summary_id BIGINT REFERENCES cited_summaries(id) ON DELETE SET NULL,
    match_status TEXT NOT NULL CHECK (
        match_status IN ('matched', 'current_only', 'previous_only')
    ),
    match_method TEXT NOT NULL CHECK (
        match_method IN ('normalized_title', 'title_similarity', 'none')
    ),
    similarity_score NUMERIC(5, 4) NOT NULL CHECK (
        similarity_score >= 0 AND similarity_score <= 1
    ),
    confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    confidence_reason TEXT NOT NULL,
    item_order INTEGER NOT NULL CHECK (item_order >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (current_financial_note_id IS NOT NULL OR previous_financial_note_id IS NOT NULL),
    CHECK (
        (match_status = 'matched'
            AND current_financial_note_id IS NOT NULL
            AND previous_financial_note_id IS NOT NULL)
        OR (match_status = 'current_only'
            AND current_financial_note_id IS NOT NULL
            AND previous_financial_note_id IS NULL)
        OR (match_status = 'previous_only'
            AND current_financial_note_id IS NULL
            AND previous_financial_note_id IS NOT NULL)
    ),
    UNIQUE (narrative_comparison_id, item_order)
);

CREATE INDEX IF NOT EXISTS idx_narrative_comparisons_company
    ON narrative_comparisons (company_id, information_cutoff DESC);

CREATE INDEX IF NOT EXISTS idx_narrative_comparison_notes_comparison
    ON narrative_comparison_notes (narrative_comparison_id, item_order);

COMMIT;
