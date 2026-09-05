BEGIN;

-- Official notes PDF; its scale is verified from content, never assigned here.
INSERT INTO document_origins VALUES (
    'CD0005', 'https://www.smv.gob.pe/ConsultasP8/temp/CPSAA%20Consolidado%204Q%202025.pdf',
    '["www.smv.gob.pe"]'
) ON CONFLICT DO NOTHING;

WITH jobs AS (
    INSERT INTO analysis_jobs (company_id, fiscal_year, period_code, scope, trigger_type, result)
    SELECT DISTINCT f.company_id, f.fiscal_year, f.period_code, f.scope, 'refresh',
           '{"notes_scale_version":1}'::jsonb
    FROM filings f JOIN companies c ON c.id=f.company_id
    WHERE c.smv_rpj='CD0005' AND f.fiscal_year=2025 AND f.period_code='A'
      AND f.reported_scale='unknown'
      AND EXISTS (SELECT 1 FROM metric_values m WHERE m.company_id=f.company_id
                  AND m.fiscal_year=f.fiscal_year AND m.period_code=f.period_code AND m.scope=f.scope)
    ON CONFLICT DO NOTHING
    RETURNING id
)
INSERT INTO analysis_job_steps (job_id, step_code, step_order, status)
SELECT jobs.id, s.code, s.ord, s.status FROM jobs CROSS JOIN (VALUES
    ('statements',1,'completed'), ('metrics',2,'completed'),
    ('documents',3,'pending'), ('summaries',4,'pending')
) AS s(code,ord,status);

COMMIT;
