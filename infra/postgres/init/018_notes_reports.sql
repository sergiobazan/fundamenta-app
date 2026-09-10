BEGIN;

CREATE TABLE notes_reports (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    fiscal_year INTEGER NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('individual', 'consolidated')),
    requested_by BIGINT NOT NULL REFERENCES app_users(id),
    input_sha256 TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'retrying', 'completed', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    manual_retries INTEGER NOT NULL DEFAULT 0,
    input JSONB NOT NULL,
    result JSONB,
    error_message TEXT,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, fiscal_year, scope, input_sha256, model, prompt_version)
);
CREATE INDEX notes_reports_queue_idx ON notes_reports(next_attempt_at, id)
    WHERE status IN ('queued', 'retrying', 'running');

COMMIT;
