BEGIN;

UPDATE financial_notes note
SET original_title = note.original_title || ' FINANCIERA',
    content_text = REGEXP_REPLACE(note.content_text, '^FINANCIERA[[:space:]]+', '')
FROM note_documents document, companies company
WHERE note.note_document_id = document.id
  AND document.company_id = company.id
  AND company.smv_rpj = 'B20041'
  AND document.fiscal_year = 2025
  AND note.note_number = 38
  AND note.original_title LIKE '%ESTADO CONSOLIDADO DE SITUACIÓN'
  AND note.content_text LIKE 'FINANCIERA%';

UPDATE source_fragments fragment
SET heading_text = note.original_title,
    content_text = REGEXP_REPLACE(fragment.content_text, '^FINANCIERA[[:space:]]+', '')
FROM financial_notes note, note_documents document, companies company
WHERE fragment.financial_note_id = note.id
  AND note.note_document_id = document.id
  AND document.company_id = company.id
  AND company.smv_rpj = 'B20041'
  AND document.fiscal_year = 2025
  AND note.note_number = 38
  AND fragment.page_number = 78;

UPDATE note_sections section
SET content_text = REGEXP_REPLACE(section.content_text, '^FINANCIERA[[:space:]]+', '')
FROM financial_notes note, note_documents document, companies company
WHERE section.financial_note_id = note.id
  AND note.note_document_id = document.id
  AND document.company_id = company.id
  AND company.smv_rpj = 'B20041'
  AND document.fiscal_year = 2025
  AND note.note_number = 38
  AND section.page_number = 78;

COMMIT;
