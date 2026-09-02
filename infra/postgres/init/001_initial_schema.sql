BEGIN;

CREATE TABLE IF NOT EXISTS source_fetches (
    id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    operation TEXT NOT NULL,
    request_parameters JSONB NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_sha256 CHAR(64) NOT NULL,
    row_count INTEGER NOT NULL CHECK (row_count >= 0),
    raw_response TEXT NOT NULL,
    UNIQUE (provider, operation, payload_sha256)
);

CREATE TABLE IF NOT EXISTS companies (
    id BIGSERIAL PRIMARY KEY,
    smv_rpj TEXT NOT NULL UNIQUE,
    ruc TEXT,
    legal_name TEXT NOT NULL,
    company_type TEXT,
    sector TEXT,
    ciiu TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS filings (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    source_fetch_id BIGINT NOT NULL REFERENCES source_fetches(id),
    statement_type TEXT NOT NULL CHECK (
        statement_type IN ('balance_sheet', 'income_statement', 'cash_flow')
    ),
    fiscal_year INTEGER NOT NULL,
    period_code TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('individual', 'consolidated')),
    information_type_raw TEXT NOT NULL,
    currency_code TEXT,
    currency_raw TEXT NOT NULL,
    reported_scale TEXT NOT NULL DEFAULT 'unknown' CHECK (
        reported_scale IN ('unknown', 'units', 'thousands', 'millions')
    ),
    scale_source_url TEXT,
    cash_flow_method_raw TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (company_id, statement_type, fiscal_year, period_code, scope)
);

CREATE TABLE IF NOT EXISTS financial_facts (
    id BIGSERIAL PRIMARY KEY,
    filing_id BIGINT NOT NULL REFERENCES filings(id) ON DELETE CASCADE,
    account_code TEXT NOT NULL,
    original_label TEXT NOT NULL,
    normalized_concept TEXT,
    current_amount NUMERIC(30, 6) NOT NULL,
    comparative_amount NUMERIC(30, 6),
    value_kind TEXT NOT NULL DEFAULT 'monetary' CHECK (
        value_kind IN ('monetary', 'per_share', 'shares', 'other')
    ),
    fact_scale TEXT NOT NULL DEFAULT 'unknown' CHECK (
        fact_scale IN ('unknown', 'units', 'thousands', 'millions')
    ),
    normalization_status TEXT NOT NULL CHECK (
        normalization_status IN ('mapped', 'unmapped', 'excluded')
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (filing_id, account_code)
);

CREATE TABLE IF NOT EXISTS validation_results (
    id BIGSERIAL PRIMARY KEY,
    filing_id BIGINT NOT NULL REFERENCES filings(id) ON DELETE CASCADE,
    rule_code TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed', 'not_applicable')),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (filing_id, rule_code)
);

CREATE INDEX IF NOT EXISTS financial_facts_normalized_concept_idx
    ON financial_facts (normalized_concept)
    WHERE normalized_concept IS NOT NULL;

CREATE INDEX IF NOT EXISTS filings_company_period_idx
    ON filings (company_id, fiscal_year DESC, period_code, statement_type);

COMMIT;
