"""Round-trip tests: parse(text).render() == text for every fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from pydhcpcdparser import parse
from pydhcpcdparser.renderer import render

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _fixture_files() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*.conf"))


@pytest.fixture(params=_fixture_files(), ids=lambda p: p.name)
def fixture_path(request: pytest.FixtureRequest) -> Path:
    return request.param  # type: ignore[return-value]


def test_roundtrip(fixture_path: Path) -> None:
    source = fixture_path.read_text(encoding="utf-8", errors="surrogateescape")
    doc = parse(source)
    output = render(doc)
    assert output == source, (
        f"Round-trip failed for {fixture_path.name}:\n"
        f"--- expected ---\n{source!r}\n"
        f"--- got ---\n{output!r}"
    )


def test_roundtrip_binary(fixture_path: Path) -> None:
    """Verify round-trip works via bytes with surrogateescape."""
    raw = fixture_path.read_bytes()
    source = raw.decode("utf-8", errors="surrogateescape")
    doc = parse(source)
    output = render(doc)
    assert output.encode("utf-8", errors="surrogateescape") == raw
