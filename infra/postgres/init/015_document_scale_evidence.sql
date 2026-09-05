BEGIN;

CREATE TABLE document_origins (
    smv_rpj TEXT NOT NULL,
    page_url TEXT NOT NULL,
    allowed_hosts JSONB NOT NULL CHECK (jsonb_typeof(allowed_hosts)='array'),
    PRIMARY KEY (smv_rpj, page_url)
);

CREATE TABLE filing_scale_evidence (
    filing_id BIGINT PRIMARY KEY REFERENCES filings(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    source_sha256 CHAR(64) NOT NULL,
    evidence JSONB NOT NULL,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- These are reviewed document indexes, not assumptions about any company's scale.
INSERT INTO document_origins VALUES (
    'CM0006',
    'https://www.cerroverde.pe/mineria-cobre-molibdeno-arequipa-minera-inversionistas',
    '["www.cerroverde.pe", "cerroverde.pe"]'
);
INSERT INTO document_origins
SELECT smv_rpj, 'https://www.alicorp.com.pe/es/inversionistas/informacion-financiera',
       '["www.alicorp.com.pe", "alicorp.com.pe"]'::jsonb
FROM companies WHERE legal_name ILIKE 'ALICORP%';

COMMIT;
