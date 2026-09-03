BEGIN;

CREATE TABLE IF NOT EXISTS source_fragments (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    note_document_id BIGINT NOT NULL REFERENCES note_documents(id) ON DELETE CASCADE,
    financial_note_id BIGINT NOT NULL REFERENCES financial_notes(id) ON DELETE CASCADE,
    fragment_kind TEXT NOT NULL DEFAULT 'note_section'
        CHECK (fragment_kind IN ('note_section')),
    fragment_order INTEGER NOT NULL CHECK (fragment_order >= 0),
    page_number INTEGER NOT NULL CHECK (page_number > 0),
    heading_text TEXT NOT NULL,
    content_text TEXT NOT NULL CHECK (BTRIM(content_text) <> ''),
    search_vector TSVECTOR GENERATED ALWAYS AS (
        SETWEIGHT(TO_TSVECTOR('spanish'::REGCONFIG, COALESCE(heading_text, '')), 'A') ||
        SETWEIGHT(TO_TSVECTOR('spanish'::REGCONFIG, COALESCE(content_text, '')), 'B')
    ) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (note_document_id, financial_note_id, page_number, fragment_order)
);

CREATE INDEX IF NOT EXISTS idx_source_fragments_search
    ON source_fragments USING GIN (search_vector);

CREATE INDEX IF NOT EXISTS idx_source_fragments_company_page
    ON source_fragments (company_id, note_document_id, page_number);

INSERT INTO source_fragments (
    company_id,
    note_document_id,
    financial_note_id,
    fragment_order,
    page_number,
    heading_text,
    content_text
)
SELECT
    nd.company_id,
    nd.id,
    fn.id,
    ns.section_order,
    ns.page_number,
    fn.original_title,
    ns.content_text
FROM note_sections ns
JOIN financial_notes fn ON fn.id = ns.financial_note_id
JOIN note_documents nd ON nd.id = fn.note_document_id
ON CONFLICT (note_document_id, financial_note_id, page_number, fragment_order)
DO UPDATE SET
    heading_text = EXCLUDED.heading_text,
    content_text = EXCLUDED.content_text;

COMMIT;
