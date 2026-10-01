BEGIN;

ALTER TABLE note_documents
    ADD COLUMN extractor_version INTEGER NOT NULL DEFAULT 1 CHECK (extractor_version > 0),
    ADD COLUMN extraction_quality JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE note_documents DROP CONSTRAINT note_documents_note_source_id_source_sha256_key;
ALTER TABLE note_documents ADD CONSTRAINT note_documents_source_extractor_unique
    UNIQUE (note_source_id, source_sha256, extractor_version);

COMMIT;
