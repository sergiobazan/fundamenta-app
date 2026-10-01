BEGIN;

ALTER TABLE app_users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE admin_audit_events (
    id BIGSERIAL PRIMARY KEY,
    actor_id BIGINT REFERENCES app_users(id) ON DELETE SET NULL,
    actor_label TEXT NOT NULL,
    action TEXT NOT NULL,
    job_id BIGINT REFERENCES analysis_jobs(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX admin_audit_job_idx ON admin_audit_events(job_id, id DESC);

-- Snapshots are appended by the database, including worker recovery and retries.
CREATE TABLE analysis_job_events (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('job', 'step', 'baseline')),
    step_code TEXT,
    snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX analysis_job_events_job_idx ON analysis_job_events(job_id, id DESC);

INSERT INTO analysis_job_events(job_id, kind, snapshot)
SELECT id, 'baseline', to_jsonb(analysis_jobs) FROM analysis_jobs;
INSERT INTO analysis_job_events(job_id, kind, step_code, snapshot)
SELECT job_id, 'baseline', step_code, to_jsonb(analysis_job_steps) FROM analysis_job_steps;

CREATE FUNCTION record_analysis_job_event() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' OR
       (to_jsonb(NEW) - 'updated_at') IS DISTINCT FROM (to_jsonb(OLD) - 'updated_at') THEN
        IF TG_TABLE_NAME = 'analysis_jobs' THEN
            INSERT INTO analysis_job_events(job_id, kind, snapshot)
            VALUES (NEW.id, 'job', to_jsonb(NEW));
        ELSE
            INSERT INTO analysis_job_events(job_id, kind, step_code, snapshot)
            VALUES (NEW.job_id, 'step', NEW.step_code, to_jsonb(NEW));
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER analysis_job_history AFTER INSERT OR UPDATE ON analysis_jobs
FOR EACH ROW EXECUTE FUNCTION record_analysis_job_event();
CREATE TRIGGER analysis_step_history AFTER INSERT OR UPDATE ON analysis_job_steps
FOR EACH ROW EXECUTE FUNCTION record_analysis_job_event();

COMMIT;
