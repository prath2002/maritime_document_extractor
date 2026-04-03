from app.services.sync_extraction import _parse_date_or_none
from app.utils.hash import sha256_hexdigest



def test_sha256_hexdigest_returns_expected_value():
    assert sha256_hexdigest(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"



def test_parse_date_or_none_returns_date_for_ddmmyyyy_string():
    parsed = _parse_date_or_none("06/01/2027")

    assert parsed is not None
    assert parsed.isoformat() == "2027-01-06"



def test_parse_date_or_none_returns_none_for_special_values():
    assert _parse_date_or_none(None) is None
    assert _parse_date_or_none("") is None
    assert _parse_date_or_none("No Expiry") is None
    assert _parse_date_or_none("Lifetime") is None
