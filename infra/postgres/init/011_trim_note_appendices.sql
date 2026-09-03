BEGIN;

DELETE FROM source_fragments fragment
USING financial_notes note, note_documents document, companies company
WHERE fragment.financial_note_id = note.id
  AND note.note_document_id = document.id
  AND document.company_id = company.id
  AND company.smv_rpj = 'B20041'
  AND document.fiscal_year = 2025
  AND note.note_number = 38
  AND fragment.page_number >= 79
  AND lower(fragment.content_text) LIKE 'informaci%n suplementaria%';

DELETE FROM note_sections section
USING financial_notes note, note_documents document, companies company
WHERE section.financial_note_id = note.id
  AND note.note_document_id = document.id
  AND document.company_id = company.id
  AND company.smv_rpj = 'B20041'
  AND document.fiscal_year = 2025
  AND note.note_number = 38
  AND section.page_number >= 79
  AND lower(section.content_text) LIKE 'informaci%n suplementaria%';

UPDATE financial_notes note
SET content_text = BTRIM(SPLIT_PART(note.content_text, 'Información Suplementaria', 1)),
    end_page = 78
FROM note_documents document, companies company
WHERE note.note_document_id = document.id
  AND document.company_id = company.id
  AND company.smv_rpj = 'B20041'
  AND document.fiscal_year = 2025
  AND note.note_number = 38
  AND note.content_text LIKE '%Información Suplementaria%';

COMMIT;
