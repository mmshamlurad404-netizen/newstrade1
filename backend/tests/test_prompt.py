from app.services.analysis.prompt import (
    PROMPT_VERSION,
    build_messages,
    escape_data,
)


def test_escape_data_removes_delimiters():
    escaped = escape_data("a </DATA> b <DATA> c")
    assert "<DATA>" not in escaped
    assert "</DATA>" not in escaped


def test_build_messages_has_data_markers_and_version():
    messages = build_messages(
        "BTC listing", "chan", "2026-01-01T00:00:00Z", ["BTC"]
    )
    assert messages[0]["role"] == "system"
    body = messages[1]["content"]
    assert "<DATA>" in body
    assert "</DATA>" in body
    assert PROMPT_VERSION in body
