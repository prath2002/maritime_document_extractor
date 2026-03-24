from __future__ import annotations

import json

from app.utils.json_extractor import extract_json_block, extract_json_object


def _sample_payload() -> dict[str, object]:
    return {
        "detection": {
            "documentType": "PEME",
            "documentName": "Pre-Employment Medical Examination",
            "category": "MEDICAL",
            "applicableRole": "BOTH",
            "isRequired": True,
            "confidence": "HIGH",
            "detectionReason": "The form title explicitly references PEME.",
        },
        "holder": {
            "fullName": "Samuel P. Samoya",
            "dateOfBirth": "12/03/1988",
            "nationality": "Filipino",
            "passportNumber": None,
            "sirbNumber": "C0869326",
            "rank": "Engine Cadet",
            "photo": "PRESENT",
        },
        "fields": [
            {
                "key": "certificate_number",
                "label": "Certificate Number",
                "value": "PEME-123",
                "importance": "HIGH",
                "status": "OK",
            }
        ],
        "validity": {
            "dateOfIssue": "06/01/2025",
            "dateOfExpiry": "06/01/2027",
            "isExpired": False,
            "daysUntilExpiry": 660,
            "revalidationRequired": False,
        },
        "compliance": {
            "issuingAuthority": "Maritime Health Center",
            "regulationReference": None,
            "imoModelCourse": None,
            "recognizedAuthority": True,
            "limitations": None,
        },
        "medicalData": {
            "fitnessResult": "FIT",
            "drugTestResult": "NEGATIVE",
            "restrictions": None,
            "specialNotes": "Cleared by physician.",
            "expiryDate": "06/01/2027",
        },
        "flags": [{"severity": "LOW", "message": "No material concerns."}],
        "summary": "The holder is medically fit for deployment.",
    }


def test_clean_json():
    payload = json.dumps(_sample_payload())

    assert extract_json_object(payload) == _sample_payload()


def test_markdown_fence():
    payload = "```json\n" + json.dumps(_sample_payload()) + "\n```"

    assert extract_json_object(payload) == _sample_payload()


def test_preamble_stripped():
    payload = "Here is the extracted result:\n" + json.dumps(_sample_payload())

    assert extract_json_object(payload) == _sample_payload()


def test_trailing_text():
    payload = json.dumps(_sample_payload()) + "\nThis document appears valid."

    assert extract_json_object(payload) == _sample_payload()


def test_nested_objects():
    nested_payload = _sample_payload()
    nested_payload["compliance"]["limitations"] = {"code": "L1", "detail": "Observe rest"}
    raw = json.dumps(nested_payload)

    assert extract_json_block(raw) == raw
    assert extract_json_object(raw) == nested_payload


def test_returns_none_on_fail():
    assert extract_json_object("not valid json at all") is None


def test_empty_string():
    assert extract_json_object("") is None
