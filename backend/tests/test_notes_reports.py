import asyncio
import copy
import json

import httpx
import pytest
from app import notes_reports as reports
from app.config import Settings
from fastapi import HTTPException
from pydantic import ValidationError


@pytest.fixture
def source():
    return {
        "year": 2025,
        "scope": "consolidated",
        "company": {"id": 1, "legal_name": "Empresa"},
        "documents": [
            {
                "id": 1,
                "fiscal_year": 2025,
                "extraction_status": "extracted",
                "source_url": "https://www.smv.gob.pe/documento.pdf",
                "document_name": "Notas 2025",
            }
        ],
        "fragments": [
            {
                "id": 10,
                "note_document_id": 1,
                "fiscal_year": 2025,
                "page_number": 12,
                "note_number": 7,
                "content_text": "La compañía mantiene procesos judiciales pendientes.",
            }
        ],
    }


def raw_report(source, **changes):
    finding = {
        "kind": "risk",
        "priority": "medium",
        "title": "Procesos pendientes",
        "observed_fact": "La compañía reporta procesos judiciales pendientes.",
        "interpretation": "La resolución podría afectar a la compañía; requiere revisión.",
        "question": "¿Cuál es la exposición asociada?",
        "citations": [{"fragment_id": 10, "quote": source["fragments"][0]["content_text"]}],
    }
    finding.update(changes)
    return json.dumps({"findings": [finding], "limitations": []})


def test_valid_citation_enriched_only_from_stored_source(source):
    result = reports.validate_report(raw_report(source), source)
    assert result["findings"][0]["citations"][0]["page"] == 12
    assert result["status"] == "generated"
    assert result["comparison_available"] is False
    assert any("año anterior" in text for text in result["limitations"])


def test_preview_is_bounded_and_explicitly_labeled(source):
    source["fragments"] = [
        {
            **source["fragments"][0],
            "id": n,
            "note_number": n,
            "content_text": "Texto de prueba. " * 500,
        }
        for n in range(1, 10)
    ]
    preview = reports.preview_input(source)
    assert len(preview["fragments"]) == 9
    assert all(len(f["content_text"]) <= 2500 for f in preview["fragments"])
    result = reports.validate_report('{"findings":[],"limitations":[]}', preview)
    assert "COBERTURA LIMITADA" in result["limitations"][0]


@pytest.mark.parametrize(
    "citation",
    [
        {"fragment_id": 99, "quote": "Una cita completamente inventada por el modelo."},
        {"fragment_id": 10, "quote": "Una cita completamente inventada por el modelo."},
    ],
)
def test_rejects_unknown_or_fabricated_evidence(source, citation):
    result = reports.validate_report(raw_report(source, citations=[citation]), source)
    assert result["findings"] == []
    assert result["rejected_findings"] == 1


def test_change_requires_both_years(source):
    result = reports.validate_report(raw_report(source, kind="change"), source)
    assert not result["findings"]
    previous_doc = {**source["documents"][0], "id": 2, "fiscal_year": 2024}
    previous_fragment = {
        **source["fragments"][0],
        "id": 20,
        "note_document_id": 2,
        "fiscal_year": 2024,
    }
    source["documents"].append(previous_doc)
    source["fragments"].append(previous_fragment)
    citations = [{"fragment_id": f["id"], "quote": f["content_text"]} for f in source["fragments"]]
    result = reports.validate_report(raw_report(source, kind="change", citations=citations), source)
    assert result["findings"][0]["kind"] == "change"
    assert result["comparison_available"]


def test_partial_extraction_visible(source):
    source["documents"][0]["extraction_status"] = "warning"
    result = reports.validate_report(raw_report(source), source)
    assert any("Extracción parcial" in item for item in result["limitations"])


def test_invalid_schema_never_published(source):
    with pytest.raises(ValidationError):
        reports.validate_report('{"summary":"sin evidencia"}', source)


def test_focused_selection_limits_years_and_prioritizes_risk(source):
    base = source["fragments"][0]
    source["fragments"] = [
        {
            **base,
            "id": year * 100 + n,
            "note_number": n,
            "fiscal_year": year,
            "original_title": "Contingencias" if n == 20 else "General",
            "topic": "contingencies" if n == 20 else "other",
        }
        for year in (2025, 2024)
        for n in range(1, 21)
    ]
    selected = reports.preview_input(source)["fragments"]
    assert sum(f["fiscal_year"] == 2025 for f in selected) == 20
    assert sum(f["fiscal_year"] == 2024 for f in selected) == 12
    assert selected[0]["note_number"] == 20
    assert len(source["fragments"]) == 40


def test_generic_notes_deprioritized_but_material_exceptions_preserved(source):
    base = source["fragments"][0]
    source["fragments"] = [
        {**base, "id": 1, "note_number": 1, "original_title": "Información general"},
        {
            **base,
            "id": 2,
            "note_number": 2,
            "original_title": "Préstamos y garantías",
            "topic": "debt",
        },
        {
            **base,
            "id": 3,
            "note_number": 3,
            "original_title": "Bases de preparación",
            "content_text": "Existe incertidumbre material sobre empresa en marcha.",
        },
    ]
    selected = reports.preview_input(source)["fragments"]
    assert [f["id"] for f in selected] == [3, 2, 1]


def test_priority_selection_has_total_character_budget(source):
    base = source["fragments"][0]
    source["fragments"] = [
        {
            **base,
            "id": year * 100 + n,
            "note_number": n,
            "fiscal_year": year,
            "content_text": "a" * 5000,
        }
        for year in (2025, 2024)
        for n in range(1, 30)
    ]
    selected = reports.preview_input(source)["fragments"]
    assert len(selected) == 32
    assert sum(len(f["content_text"]) for f in selected) <= 75000


def test_hash_invalidates_changed_text_and_previous_year(source):
    original = reports.input_hash(source)
    changed = copy.deepcopy(source)
    changed["fragments"][0]["content_text"] += " Nueva información."
    assert reports.input_hash(changed) != original
    assert reports.input_hash(dict(reversed(list(source.items())))) == original


def test_missing_key_fails_before_database(monkeypatch):
    monkeypatch.setattr(reports, "get_settings", lambda: Settings(_env_file=None))
    with pytest.raises(HTTPException) as caught:
        reports.request_report("B30006", reports.ReportRequest(year=2025), {"id": 1})
    assert caught.value.status_code == 503


def test_provider_errors_are_sanitized():
    request = httpx.Request("POST", "https://integrate.api.nvidia.com/v1/chat/completions")
    for code, retryable in [(401, False), (403, False), (400, False), (429, True), (503, True)]:
        response = httpx.Response(code, request=request, text="SECRET_KEY_AND_PRIVATE_BODY")
        error = httpx.HTTPStatusError("SECRET_KEY", request=request, response=response)
        message, retry = reports.safe_error(error)
        assert "SECRET" not in message
        assert retry == retryable


def test_total_timeout_is_enforced(monkeypatch, source):
    async def slow(*args):
        await asyncio.sleep(1)

    monkeypatch.setattr(reports, "call_nvidia", slow)
    with pytest.raises(TimeoutError):
        asyncio.run(
            reports.generate(
                source, Settings(_env_file=None, notes_report_timeout_seconds=0.01), "test-model"
            )
        )


def test_nvidia_request_uses_configured_model_and_ignores_reasoning(monkeypatch, source):
    real_client = httpx.AsyncClient

    def handle(request):
        body = json.loads(request.content)
        assert body["model"] == "deepseek-ai/deepseek-v4-pro-0813"
        assert "reasoning_effort" not in body
        assert body["stream"] is False
        assert request.headers["Authorization"] == "Bearer test-only"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": raw_report(source),
                            "reasoning_content": "PRIVATE_REASONING",
                        },
                    }
                ]
            },
        )

    monkeypatch.setattr(
        reports.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw),
    )
    settings = Settings(_env_file=None, nvidia_api_key="test-only")
    result = asyncio.run(reports.generate(source, settings, settings.nvidia_model))
    assert "PRIVATE_REASONING" not in json.dumps(result)
    assert result["findings"]


def test_untrusted_endpoint_cannot_receive_key(source):
    settings = Settings(
        _env_file=None, nvidia_api_key="test-only", nvidia_base_url="https://untrusted.example/v1"
    )
    with pytest.raises(ValueError, match="no está permitido"):
        asyncio.run(reports.call_nvidia(source, settings, settings.nvidia_model))


def test_truncated_model_response_rejected(monkeypatch, source):
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "length", "message": {"content": raw_report(source)}}]
            },
        )
    )
    monkeypatch.setattr(
        reports.httpx, "AsyncClient", lambda **kw: real_client(transport=transport, **kw)
    )
    settings = Settings(_env_file=None, nvidia_api_key="test-only")
    with pytest.raises(ValueError, match="incompleta"):
        asyncio.run(reports.generate(source, settings, settings.nvidia_model))
