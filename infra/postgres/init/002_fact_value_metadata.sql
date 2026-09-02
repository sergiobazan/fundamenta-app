BEGIN;

ALTER TABLE financial_facts
    ADD COLUMN IF NOT EXISTS value_kind TEXT NOT NULL DEFAULT 'monetary';

ALTER TABLE financial_facts
    ADD COLUMN IF NOT EXISTS fact_scale TEXT NOT NULL DEFAULT 'unknown';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'financial_facts_value_kind_check'
    ) THEN
        ALTER TABLE financial_facts
            ADD CONSTRAINT financial_facts_value_kind_check
            CHECK (value_kind IN ('monetary', 'per_share', 'shares', 'other'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'financial_facts_fact_scale_check'
    ) THEN
        ALTER TABLE financial_facts
            ADD CONSTRAINT financial_facts_fact_scale_check
            CHECK (fact_scale IN ('unknown', 'units', 'thousands', 'millions'));
    END IF;
END $$;

COMMIT;

