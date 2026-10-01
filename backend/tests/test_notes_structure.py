import pytest
from app.notes import extract_note_document_from_pages


def indexed_pages(titles=None):
    titles = titles or ['Información general', 'Bases de preparación', 'Efectivo',
                        'Inventarios', 'Patrimonio', 'Eventos posteriores']
    index = 'Contenido\nNotas a los estados financieros\n'
    index += '\n'.join(f'{i} {title} ........ {i+1}' for i, title in enumerate(titles, 1))
    body = ['Notas a los estados financieros\n'
            + f'{i} {title}\n\nContenido exclusivo de la nota {i}.\n'
            for i, title in enumerate(titles, 1)]
    return [index, *body]


def test_index_matches_single_word_titles_and_exact_content_boundaries():
    result = extract_note_document_from_pages(indexed_pages(), ())
    assert len(result.notes) == 6
    assert result.quality['coverage_checked_against_index'] is True
    for i, note in enumerate(result.notes, 1):
        assert note.note_number == i
        assert note.start_page == i + 1
        assert f'Contenido exclusivo de la nota {i}.' in note.content_text
        assert f'Contenido exclusivo de la nota {i + 1}.' not in note.content_text


def test_index_recovers_wrapped_title_without_consuming_body():
    pages = indexed_pages()
    pages[2] = pages[2].replace('2 Bases de preparación', '2 Bases de\npreparación')
    result = extract_note_document_from_pages(pages, ())
    assert result.notes[1].original_title == 'Bases de preparación'
    assert result.notes[1].content_text == 'Contenido exclusivo de la nota 2.'


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'out_of_order'])
def test_index_ambiguity_blocks_publishing_instead_of_mixing_notes(change):
    pages = indexed_pages()
    if change == 'missing':
        pages[4] = pages[4].replace('4 Inventarios', 'Título ilegible')
    elif change == 'duplicate':
        pages[4] += '\n4 Inventarios\nEncabezado duplicado.'
    else:
        pages[3], pages[4] = pages[4], pages[3]
    with pytest.raises(ValueError, match='índice'):
        extract_note_document_from_pages(pages, ())


def test_missing_last_note_is_detected_from_index():
    with pytest.raises(ValueError, match='faltantes \\[6\\]'):
        extract_note_document_from_pages(indexed_pages()[:-1], ())


def test_table_cells_dates_and_subnotes_do_not_become_notes():
    pages = indexed_pages()
    pages[1] += '\n2 De enero de 2025\n2 1,500 3,000\n2.1 Detalle secundario\n'
    result = extract_note_document_from_pages(pages, ())
    assert len(result.notes) == 6
    assert result.notes[1].original_title == 'Bases de preparación'


def test_same_page_notes_are_split_at_source_offsets():
    pages = indexed_pages()
    pages[3] += pages.pop(4)
    result = extract_note_document_from_pages(pages, ())
    assert 'Contenido exclusivo de la nota 4' not in result.notes[2].content_text
    assert 'Contenido exclusivo de la nota 4' in result.notes[3].content_text


def test_auditor_report_after_notes_is_not_absorbed():
    pages = indexed_pages()
    pages.append('INFORME DE LOS AUDITORES INDEPENDIENTES\n'
                 'Opinión acerca de las notas a los estados financieros.\nContenido del auditor.')
    result = extract_note_document_from_pages(pages, ())
    assert result.notes[-1].end_page == 7
    assert 'auditor' not in result.notes[-1].content_text.lower()


def test_no_index_gap_does_not_publish_a_note_with_an_uncertain_end():
    pages = ['Notas a los estados financieros\n' + '\n'.join(
        f'{i}. Cuenta contable\nContenido {i}.' for i in range(1, 6)
    ) + '\n6 X\nContenido de nota ilegible.\n7. Hechos posteriores\nContenido siete.']
    result = extract_note_document_from_pages(pages, ())
    assert result.extraction_status == 'warning'
    assert [n.note_number for n in result.notes] == [1, 2, 3, 4]
    assert all('ilegible' not in n.content_text for n in result.notes)


def test_repeated_headers_do_not_create_a_fragment_on_the_next_notes_page():
    pages = indexed_pages()
    for i in range(1, len(pages)):
        pages[i] = 'Empresa S.A.\n' + pages[i].replace(
            'Notas a los estados financieros\n',
            'Notas a los estados financieros\nAl 31 de diciembre de 2025\n'
            f'Expresado en miles de dólares\nPágina {i} de 6\n',
        )
    result = extract_note_document_from_pages(pages, ())
    for i, note in enumerate(result.notes, 1):
        assert note.start_page == note.end_page == i + 1
        assert note.content_text == f'Contenido exclusivo de la nota {i}.'


def test_no_index_last_heading_before_auditor_on_same_page_is_preserved():
    page = 'Notas a los estados financieros\n' + '\n'.join(
        f'{i}. Cuenta contable\nContenido {i}.' for i in range(1, 7)
    )
    page += '\nINFORME DE LOS AUDITORES INDEPENDIENTES\n7. Otra sección\nDictamen.'
    result = extract_note_document_from_pages([page], ())
    assert len(result.notes) == 6
    assert result.notes[-1].content_text == 'Contenido 6.'
    assert result.warning is None
