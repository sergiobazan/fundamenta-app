from decimal import Decimal

import pytest
from app.document_scale import document_identity, explicit_scale, official_url, verify_statement
from app.notes import find_note_headings


def test_notes_skip_table_of_contents_with_page_references():
    index = "Contenido Página\nNotas a los estados financieros\n"
    index += "\n".join(f"{i}. Información contable {i + 10}" for i in range(1, 7))
    body = "Notas a los estados financieros\n"
    body += "\n".join(f"{i}. Información contable\nContenido real." for i in range(1, 7))
    headings = find_note_headings([index, body])
    assert len(headings) == 6
    assert all(h.page_index == 1 for h in headings)


@pytest.mark.parametrize("identity_ok", [True, False])
def test_discovered_notes_do_not_require_verified_scales(monkeypatch, identity_ok):
    from types import SimpleNamespace

    from app import document_scale as module

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, query, args=None):
            self.query = query

        def fetchone(self):
            return {"legal_name": "Empresa S.A."}

        def fetchall(self):
            if "SELECT * FROM filings" in self.query:
                return [{"id": 1, "reported_scale": "unknown"}]
            return []

    connection = SimpleNamespace(cursor=Cursor, commit=lambda: None)
    job = dict(company_id=1, smv_rpj="TEST", fiscal_year=2025,
               period_code="A", scope="consolidated")
    url = "https://www.smv.gob.pe/report.pdf"
    registered = []
    monkeypatch.setattr("app.smv_documents.discover_smv_documents", lambda *args: [url])
    monkeypatch.setattr(module, "fetch_official", lambda *args: b"%PDF-test")
    monkeypatch.setattr(module, "read_pages", lambda *args: ["document"])
    monkeypatch.setattr(module, "document_identity", lambda *args: identity_ok)
    monkeypatch.setattr("app.notes_scale.verify_notes_policy", lambda *args: {})
    monkeypatch.setattr(module, "verify_statement", lambda *args: None)
    monkeypatch.setattr(module, "extract_notes_from_pdf",
                        lambda *args: SimpleNamespace(notes=["note"]))
    monkeypatch.setattr("app.notes_jobs.register_note_sources",
                        lambda conn, sources: registered.extend(sources))
    result = module.verify_company_scales(
        connection, job, SimpleNamespace(notes_max_pdf_bytes=1000)
    )
    assert result["verified"] == 0
    assert result["pending"] == 1
    assert bool(registered) == identity_ok
    assert bool(result["documents"]) == identity_ok


@pytest.mark.parametrize(
    "text,currency,scale",
    [
        ("US$(000)", "USD", "thousands"),
        ("Miles de soles", "PEN", "thousands"),
        ("Millones de dólares", "USD", "millions"),
        ("Expresados en soles", "PEN", "units"),
        ("US$", "USD", None),
        ("US$(000)", "PEN", None),
        ("Miles de soles y millones de soles", "PEN", None),
    ],
)
def test_explicit_scale_requires_unambiguous_currency_and_unit(text, currency, scale):
    assert explicit_scale(text, currency) == scale


def test_identity_rejects_wrong_company_primary_year_and_scope():
    pages = [
        "Empresa Andina S.A. Estados financieros consolidados al 31 de diciembre de 2025 y de 2024"
    ]
    assert document_identity(pages, "Empresa Andina S.A.", 2025, "consolidated")
    assert not document_identity(pages, "Otra Empresa S.A.", 2025, "consolidated")
    assert not document_identity(pages, "Empresa Andina S.A.", 2024, "consolidated")
    assert not document_identity(pages, "Empresa Andina S.A.", 2025, "individual")


def test_statement_requires_labels_and_current_comparative_pairs():
    filing = {"statement_type": "balance_sheet", "currency_code": "USD", "fiscal_year": 2025}
    facts = [
        dict(
            account_code=str(i),
            original_label=label,
            current_amount=Decimal(value),
            comparative_amount=Decimal("100"),
        )
        for i, (label, value) in enumerate(
            [("Inventarios", "1000"), ("Total Activos", "2000"), ("Total Pasivos", "3000")]
        )
    ]
    page = (
        "Estado de situación financiera\nAl 31 de diciembre de 2025 y 2024\nUS$(000)\n"
        "Inventarios 1,000 100\nTotal Activos 2,000 100\nTotal Pasivos 3,000 100"
    )
    assert verify_statement([page], filing, facts)["scale"] == "thousands"
    assert verify_statement([page.replace("Inventarios", "Otra cuenta")], filing, facts) is None
    assert verify_statement([page.replace("1,000 100", "1,000 200")], filing, facts) is None
    assert verify_statement([page.replace("US$(000)", "US$")], filing, facts) is None
    assert verify_statement([page.replace("2025", "2023")], filing, facts) is None


def test_downloads_reject_unregistered_hosts_credentials_and_http():
    hosts = {"www.smv.gob.pe"}
    assert official_url("https://www.smv.gob.pe/report.pdf", hosts)
    for url in [
        "http://www.smv.gob.pe/report.pdf",
        "https://127.0.0.1/report.pdf",
        "https://www.smv.gob.pe.evil.test/report.pdf",
        "https://user:password@www.smv.gob.pe/report.pdf",
    ]:
        assert not official_url(url, hosts)


def test_individual_notes_accept_undotted_financial_instruments_heading():
    text = "Notas a los estados financieros\n"
    text += "\n".join(f"{i}. Cuenta contable\nContenido." for i in range(1, 6))
    text += "\n6 Jerarquía y valor razonable de los instrumentos financieros\nContenido."
    text += "\n7. Hechos posteriores\nContenido."
    assert len(find_note_headings([text])) == 7


def test_notes_do_not_silently_drop_later_sections_after_a_gap():
    text = "Notas a los estados financieros\n"
    text += "\n".join(f"{i}. Cuenta contable\nContenido." for i in range(1, 6))
    text += "\n7. Hechos posteriores\nContenido."
    with pytest.raises(ValueError, match="secuencia de notas"):
        find_note_headings([text])
