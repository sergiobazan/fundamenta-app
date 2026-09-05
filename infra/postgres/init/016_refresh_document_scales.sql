BEGIN;

INSERT INTO document_origins VALUES (
    'B30006', 'https://www.alicorp.com.pe/es/inversionistas/informacion-financiera',
    '["www.alicorp.com.pe", "alicorp.com.pe"]'
) ON CONFLICT DO NOTHING;
INSERT INTO document_origins VALUES (
    'B30006', 'https://www.smv.gob.pe/ConsultasP8/temp/Informe%20Consolidado%202025.pdf',
    '["www.smv.gob.pe"]'
) ON CONFLICT DO NOTHING;

-- Preserve completed financial work and retry only the documentary stages.
WITH jobs AS (
    INSERT INTO analysis_jobs (company_id, fiscal_year, period_code, scope, trigger_type, result)
    SELECT DISTINCT f.company_id, f.fiscal_year, f.period_code, f.scope, 'refresh',
           '{"document_scale_version":1}'::jsonb
    FROM filings f JOIN companies c ON c.id=f.company_id
    WHERE f.reported_scale='unknown' AND f.period_code='A'
      AND EXISTS (SELECT 1 FROM metric_values m WHERE m.company_id=f.company_id
                  AND m.fiscal_year=f.fiscal_year AND m.period_code=f.period_code AND m.scope=f.scope)
      AND (EXISTS (SELECT 1 FROM document_origins o WHERE o.smv_rpj=c.smv_rpj)
           OR EXISTS (SELECT 1 FROM note_sources n WHERE n.company_id=f.company_id
                      AND n.fiscal_year=f.fiscal_year AND n.scope=f.scope AND n.enabled))
    ON CONFLICT DO NOTHING
    RETURNING id
)
INSERT INTO analysis_job_steps (job_id, step_code, step_order, status)
SELECT jobs.id, s.code, s.ord, s.status FROM jobs CROSS JOIN (VALUES
    ('statements',1,'completed'), ('metrics',2,'completed'),
    ('documents',3,'pending'), ('summaries',4,'pending')
) AS s(code,ord,status);

COMMIT;
