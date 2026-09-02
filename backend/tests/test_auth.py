from app.auth import hash_session_token, normalize_email, password_hasher


def test_normalize_email() -> None:
    assert normalize_email("  Demo@Fundamenta.PE ") == "demo@fundamenta.pe"


def test_session_tokens_are_hashed_deterministically() -> None:
    assert hash_session_token("session") == (
        "3f3af1ecebbd1410ab417ec0d27bbfcb5d340e177ae159b59fc8626c2dfd9175"
    )


def test_password_hash_is_not_plaintext() -> None:
    encoded = password_hasher.hash("Prueba-segura-2026")
    assert encoded != "Prueba-segura-2026"
    assert password_hasher.verify("Prueba-segura-2026", encoded)
