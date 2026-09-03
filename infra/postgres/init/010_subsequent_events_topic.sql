BEGIN;

UPDATE financial_notes
SET topic = 'subsequent_events',
    is_priority = TRUE
WHERE topic <> 'subsequent_events'
  AND lower(original_title) LIKE '%eventos posteriores%';

COMMIT;
