BEGIN;

CREATE TABLE IF NOT EXISTS note_sources (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    source_key TEXT NOT NULL UNIQUE,
    fiscal_year INTEGER NOT NULL CHECK (fiscal_year >= 2000),
    period_code TEXT NOT NULL DEFAULT 'A',
    scope TEXT NOT NULL CHECK (scope IN ('individual', 'consolidated')),
    language_code TEXT NOT NULL DEFAULT 'es',
    document_name TEXT NOT NULL CHECK (LENGTH(BTRIM(document_name)) > 0),
    source_url TEXT NOT NULL CHECK (source_url LIKE 'https://%'),
    identity_tokens JSONB NOT NULL DEFAULT '[]'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_checked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, fiscal_year, period_code, scope)
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id BIGSERIAL PRIMARY KEY,
    job_type TEXT NOT NULL CHECK (job_type IN ('notes_sync')),
    note_source_id BIGINT NOT NULL REFERENCES note_sources(id),
    dedupe_key TEXT NOT NULL UNIQUE,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('startup', 'monthly', 'retry')),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (
        status IN ('queued', 'running', 'retrying', 'completed', 'failed')
    ),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
    scheduled_for TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    next_retry_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ingestion_jobs_claim_idx
    ON ingestion_jobs (scheduled_for, id)
    WHERE status IN ('queued', 'retrying');

CREATE TABLE IF NOT EXISTS note_documents (
    id BIGSERIAL PRIMARY KEY,
    note_source_id BIGINT NOT NULL REFERENCES note_sources(id),
    company_id BIGINT NOT NULL REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,
    period_code TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('individual', 'consolidated')),
    version INTEGER NOT NULL CHECK (version > 0),
    document_name TEXT NOT NULL,
    source_url TEXT NOT NULL CHECK (source_url LIKE 'https://%'),
    source_sha256 CHAR(64) NOT NULL,
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes > 0),
    page_count INTEGER NOT NULL CHECK (page_count > 0),
    notes_count INTEGER NOT NULL CHECK (notes_count > 0),
    extraction_status TEXT NOT NULL CHECK (
        extraction_status IN ('extracted', 'reviewed', 'warning')
    ),
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (note_source_id, version),
    UNIQUE (note_source_id, source_sha256)
);

CREATE UNIQUE INDEX IF NOT EXISTS note_documents_one_current_idx
    ON note_documents (note_source_id)
    WHERE is_current;

CREATE TABLE IF NOT EXISTS financial_notes (
    id BIGSERIAL PRIMARY KEY,
    note_document_id BIGINT NOT NULL REFERENCES note_documents(id) ON DELETE CASCADE,
    note_number INTEGER NOT NULL CHECK (note_number > 0),
    original_title TEXT NOT NULL CHECK (LENGTH(BTRIM(original_title)) > 0),
    topic TEXT NOT NULL CHECK (
        topic IN (
            'debt', 'segments', 'capex_assets', 'impairment',
            'provisions_closure', 'contingencies', 'related_parties',
            'estimates', 'subsequent_events', 'other'
        )
    ),
    is_priority BOOLEAN NOT NULL DEFAULT FALSE,
    start_page INTEGER NOT NULL CHECK (start_page > 0),
    end_page INTEGER NOT NULL CHECK (end_page >= start_page),
    content_text TEXT NOT NULL CHECK (LENGTH(BTRIM(content_text)) > 0),
    extraction_status TEXT NOT NULL DEFAULT 'extracted' CHECK (
        extraction_status IN ('extracted', 'reviewed', 'warning')
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (note_document_id, note_number)
);

CREATE INDEX IF NOT EXISTS financial_notes_document_topic_idx
    ON financial_notes (note_document_id, is_priority DESC, topic, note_number);

CREATE TABLE IF NOT EXISTS note_sections (
    id BIGSERIAL PRIMARY KEY,
    financial_note_id BIGINT NOT NULL REFERENCES financial_notes(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL CHECK (page_number > 0),
    section_order INTEGER NOT NULL CHECK (section_order >= 0),
    content_text TEXT NOT NULL CHECK (LENGTH(BTRIM(content_text)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (financial_note_id, page_number, section_order)
);

COMMIT;
