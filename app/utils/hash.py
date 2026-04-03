from __future__ import annotations

import hashlib


def sha256_hexdigest(content_bytes: bytes) -> str:
    return hashlib.sha256(content_bytes).hexdigest()
