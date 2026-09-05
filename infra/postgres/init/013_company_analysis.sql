BEGIN;

CREATE TABLE IF NOT EXISTS company_coverage (
    company_id BIGINT PRIMARY KEY REFERENCES companies(id) ON DELETE CASCADE,
    support_level TEXT NOT NULL DEFAULT 'basic' CHECK (
        support_level IN ('full', 'basic', 'unsupported')
    ),
    analysis_status TEXT NOT NULL DEFAULT 'not_analyzed' CHECK (
        analysis_status IN (
            'not_analyzed', 'queued', 'processing', 'partial', 'available',
            'review_required', 'failed', 'unsupported'
        )
    ),
    preferred_scope TEXT CHECK (preferred_scope IN ('individual', 'consolidated')),
    available_scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    latest_fiscal_year INTEGER CHECK (latest_fiscal_year >= 2000),
    completed_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    validation_tier TEXT NOT NULL DEFAULT 'automatic' CHECK (
        validation_tier IN ('automatic', 'verified')
    ),
    last_error TEXT,
    last_requested_at TIMESTAMPTZ,
    last_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (jsonb_typeof(available_scopes) = 'array'),
    CHECK (jsonb_typeof(completed_steps) = 'array')
);

CREATE TABLE IF NOT EXISTS analysis_jobs (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    requested_by BIGINT REFERENCES app_users(id) ON DELETE SET NULL,
    fiscal_year INTEGER NOT NULL CHECK (fiscal_year >= 2000),
    period_code TEXT NOT NULL DEFAULT 'A',
    scope TEXT NOT NULL CHECK (scope IN ('individual', 'consolidated')),
    trigger_type TEXT NOT NULL DEFAULT 'user' CHECK (
        trigger_type IN ('user', 'startup', 'refresh', 'retry')
    ),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (
        status IN ('queued', 'running', 'retrying', 'completed', 'review_required', 'failed')
    ),
    current_step TEXT CHECK (
        current_step IN ('statements', 'metrics', 'documents', 'summaries', 'complete')
    ),
    progress SMALLINT NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
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

CREATE UNIQUE INDEX IF NOT EXISTS analysis_jobs_one_active_idx
    ON analysis_jobs (company_id, fiscal_year, period_code, scope)
    WHERE status IN ('queued', 'running', 'retrying');

CREATE INDEX IF NOT EXISTS analysis_jobs_claim_idx
    ON analysis_jobs (scheduled_for, id)
    WHERE status IN ('queued', 'retrying');

CREATE TABLE IF NOT EXISTS analysis_job_steps (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    step_code TEXT NOT NULL CHECK (
        step_code IN ('statements', 'metrics', 'documents', 'summaries')
    ),
    step_order SMALLINT NOT NULL CHECK (step_order BETWEEN 1 AND 4),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'running', 'completed', 'skipped', 'failed')
    ),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (job_id, step_code),
    UNIQUE (job_id, step_order)
);

INSERT INTO company_coverage (
    company_id, support_level, analysis_status, preferred_scope,
    available_scopes, latest_fiscal_year, completed_steps, validation_tier,
    last_completed_at
)
SELECT
    c.id,
    CASE
        WHEN c.smv_rpj IN ('B20003', 'A20032', 'CM0001', 'B20041') THEN 'full'
        ELSE 'basic'
    END,
    CASE
        WHEN EXISTS (SELECT 1 FROM metric_values mv WHERE mv.company_id = c.id) THEN 'available'
        ELSE 'not_analyzed'
    END,
    COALESCE(
        (SELECT f.scope FROM filings f WHERE f.company_id = c.id
         ORDER BY f.fiscal_year DESC, (f.scope = 'consolidated') DESC LIMIT 1),
        NULL
    ),
    COALESCE(
        (SELECT jsonb_agg(scopes.scope ORDER BY scopes.scope)
         FROM (SELECT DISTINCT f.scope FROM filings f WHERE f.company_id = c.id) scopes),
        '[]'::jsonb
    ),
    (SELECT MAX(f.fiscal_year) FROM filings f WHERE f.company_id = c.id),
    CASE
        WHEN EXISTS (
            SELECT 1 FROM note_documents nd WHERE nd.company_id = c.id AND nd.is_current
        ) THEN '["statements", "metrics", "documents", "summaries"]'::jsonb
        WHEN EXISTS (SELECT 1 FROM metric_values mv WHERE mv.company_id = c.id)
            THEN '["statements", "metrics"]'::jsonb
        ELSE '[]'::jsonb
    END,
    'automatic',
    CASE
        WHEN EXISTS (SELECT 1 FROM metric_values mv WHERE mv.company_id = c.id) THEN NOW()
        ELSE NULL
    END
FROM companies c
ON CONFLICT (company_id) DO NOTHING;

COMMIT;
