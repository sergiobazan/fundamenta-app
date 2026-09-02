BEGIN;

CREATE TABLE IF NOT EXISTS corporate_events (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    source_provider TEXT NOT NULL,
    external_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    category TEXT NOT NULL CHECK (
        category IN (
            'dividends', 'management', 'meetings', 'debt',
            'operations', 'litigation', 'production', 'other'
        )
    ),
    title TEXT NOT NULL CHECK (LENGTH(BTRIM(title)) > 0),
    summary TEXT NOT NULL CHECK (LENGTH(BTRIM(summary)) > 0),
    published_at TIMESTAMPTZ NOT NULL,
    effective_date DATE,
    source_url TEXT NOT NULL CHECK (source_url LIKE 'https://%'),
    source_document_name TEXT,
    source_sha256 CHAR(64) NOT NULL,
    source_payload JSONB NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_provider, external_id, version),
    UNIQUE (source_provider, external_id, source_sha256)
);

CREATE UNIQUE INDEX IF NOT EXISTS corporate_events_one_current_idx
    ON corporate_events (source_provider, external_id)
    WHERE is_current;

CREATE INDEX IF NOT EXISTS corporate_events_company_date_idx
    ON corporate_events (company_id, published_at DESC)
    WHERE is_current;

COMMIT;
