BEGIN;

CREATE TABLE IF NOT EXISTS cited_summaries (
    id BIGSERIAL PRIMARY KEY,
    financial_note_id BIGINT NOT NULL REFERENCES financial_notes(id) ON DELETE CASCADE,
    generator_name TEXT NOT NULL,
    generator_version INTEGER NOT NULL CHECK (generator_version > 0),
    generation_method TEXT NOT NULL CHECK (generation_method IN ('extractive', 'ai')),
    status TEXT NOT NULL CHECK (status IN ('generated', 'partial', 'insufficient_evidence')),
    confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    confidence_reason TEXT NOT NULL,
    information_cutoff DATE NOT NULL,
    input_sha256 CHAR(64) NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (financial_note_id, generator_name, generator_version)
);

CREATE TABLE IF NOT EXISTS cited_summary_items (
    id BIGSERIAL PRIMARY KEY,
    cited_summary_id BIGINT NOT NULL REFERENCES cited_summaries(id) ON DELETE CASCADE,
    section_kind TEXT NOT NULL
        CHECK (section_kind IN ('observed_fact', 'interpretation', 'missing_data')),
    item_order INTEGER NOT NULL CHECK (item_order >= 0),
    statement_text TEXT NOT NULL CHECK (BTRIM(statement_text) <> ''),
    source_fragment_id BIGINT REFERENCES source_fragments(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (section_kind = 'observed_fact' AND source_fragment_id IS NOT NULL)
        OR (section_kind <> 'observed_fact' AND source_fragment_id IS NULL)
    ),
    UNIQUE (cited_summary_id, section_kind, item_order)
);

CREATE INDEX IF NOT EXISTS idx_cited_summaries_note
    ON cited_summaries (financial_note_id, generator_version DESC);

CREATE INDEX IF NOT EXISTS idx_cited_summary_items_summary
    ON cited_summary_items (cited_summary_id, section_kind, item_order);

COMMIT;
