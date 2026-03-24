import base64

import pytest

from app.utils.document_preparation import document_to_base64, prepare_document


def test_prepare_document_returns_typed_document():
    document = prepare_document(
        file_name="sample.pdf",
        mime_type="application/pdf",
        content_bytes=b"sample-bytes",
    )

    assert document.file_name == "sample.pdf"
    assert document.mime_type == "application/pdf"
    assert document.byte_size == len(b"sample-bytes")


def test_document_to_base64_encodes_content():
    document = prepare_document(
        file_name="sample.png",
        mime_type="image/png",
        content_bytes=b"binary-content",
    )

    assert document_to_base64(document) == base64.b64encode(b"binary-content").decode("ascii")


@pytest.mark.parametrize(
    ("file_name", "mime_type", "content_bytes"),
    [
        ("", "application/pdf", b"123"),
        ("sample.pdf", "", b"123"),
        ("sample.pdf", "application/pdf", b""),
    ],
)
def test_prepare_document_rejects_invalid_input(file_name, mime_type, content_bytes):
    with pytest.raises(ValueError):
        prepare_document(file_name=file_name, mime_type=mime_type, content_bytes=content_bytes)
