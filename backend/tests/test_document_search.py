from app.document_search import escape_like


def test_escape_like_treats_sql_wildcards_as_literal_characters() -> None:
    assert escape_like(r"deuda_10%\2025") == r"deuda\_10\%\\2025"
