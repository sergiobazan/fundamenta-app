import httpx
import pytest
from app import smv_documents as smv


def install_client(monkeypatch, handler):
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    monkeypatch.setattr(smv.httpx, "Client", lambda **kwargs: client)


def test_discovers_official_attachments_using_live_company_identifier(monkeypatch):
    from urllib.parse import parse_qs

    def handler(request):
        if request.method == "GET":
            return httpx.Response(
                200,
                text="""
                <input type="hidden" name="__VIEWSTATE" value="token">
                <select name="ctl00$MainContent$cboDenominacionSocial">
                <option value="987">EMPRESA ANDINA S.A.A.</option></select>""",
            )
        fields = parse_qs(request.content.decode())
        assert fields["__VIEWSTATE"] == ["token"]
        assert fields[smv.PREFIX + "cboDenominacionSocial"] == ["987"]
        assert fields[smv.PREFIX + "cboTipo"] == ["C"]
        assert fields[smv.PREFIX + "cboAnio"] == ["2025"]
        assert fields[smv.PREFIX + "cboPeriodo"] == ["A"]
        links = [
            ("/ConsultasP8/documento.aspx?vidDoc=123   ", "Descargar Documento"),
            ("/ConsultasP8/documento.aspx?vidDoc=xbrl", "Descargar Documento XBRL"),
            ("https://evil.test/report.pdf", "Descargar Documento"),
            ("http://www.smv.gob.pe/report.pdf", "Descargar Documento"),
            ("https://www.smv.gob.pe.evil.test/report.pdf", "Descargar Documento"),
            ("/SIMV/Frm_DetalleInfoFinanciera.aspx", "Ver detalle"),
        ]
        return httpx.Response(
            200,
            text="".join(
                f'<a id="MainContent_grdInfoFinanciera_{i}" href="{url}" title="{title}">PDF</a>'
                for i, (url, title) in enumerate(links)
            ),
        )

    install_client(monkeypatch, handler)
    assert smv.discover_smv_documents("Empresa Andina SAA", 2025, "consolidated") == [
        "https://www.smv.gob.pe/ConsultasP8/documento.aspx?vidDoc=123"
    ]


@pytest.mark.parametrize(
    "options",
    [
        "",
        '<option value="2">Otra empresa</option>',
        '<option value="1">Andina</option><option value="2">ANDINA</option>',
    ],
)
def test_missing_or_ambiguous_company_is_not_guessed(monkeypatch, options):
    def handler(request):
        assert request.method == "GET"
        return httpx.Response(
            200, text=(f'<select name="{smv.PREFIX}cboDenominacionSocial">{options}</select>')
        )

    install_client(monkeypatch, handler)
    with pytest.raises(ValueError, match="coincidencia única"):
        smv.discover_smv_documents("Andina", 2025, "individual")


def test_form_does_not_follow_redirects(monkeypatch):
    install_client(
        monkeypatch,
        lambda request: httpx.Response(302, headers={"location": "https://untrusted.test"}),
    )
    with pytest.raises(httpx.HTTPStatusError):
        smv.discover_smv_documents("Andina", 2025, "individual")
