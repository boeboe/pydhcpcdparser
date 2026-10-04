"""Fuzz-style tests for the parser.

The parser must never raise unexpected exceptions in non-strict mode,
regardless of input content.
"""

from __future__ import annotations

import string

from hypothesis import given, settings
from hypothesis import strategies as st

from pydhcpcdparser import parse
from pydhcpcdparser.renderer import render

# Alphabet that exercises all the tricky characters
_FUZZ_ALPHABET = string.printable + "\r\x00"


@given(st.text(alphabet=_FUZZ_ALPHABET, min_size=0, max_size=500))
@settings(max_examples=500)
def test_parse_never_crashes(text: str) -> None:
    """parse() with strict=False must never raise for any input."""
    doc = parse(text, strict=False)
    assert doc is not None


@given(st.text(alphabet=_FUZZ_ALPHABET, min_size=0, max_size=500))
@settings(max_examples=500)
def test_roundtrip_idempotent(text: str) -> None:
    """render(parse(text)) == text for any input."""
    doc = parse(text)
    output = render(doc)
    assert output == text


@given(st.text(alphabet=_FUZZ_ALPHABET, min_size=0, max_size=500))
@settings(max_examples=200)
def test_double_roundtrip(text: str) -> None:
    """render(parse(render(parse(text)))) == text."""
    doc1 = parse(text)
    mid = render(doc1)
    doc2 = parse(mid)
    output = render(doc2)
    assert output == text


def test_very_long_line() -> None:
    line = "static value=" + "x" * 10000 + "\n"
    doc = parse(line)
    assert render(doc) == line


def test_thousands_of_directives() -> None:
    lines = [f"option opt{i}\n" for i in range(2000)]
    text = "".join(lines)
    doc = parse(text)
    assert len(doc.nodes) == 2000
    assert render(doc) == text


def test_many_backslashes() -> None:
    text = "env val=" + "\\\\" * 100 + "\n"
    doc = parse(text)
    assert render(doc) == text


def test_many_quotes() -> None:
    text = 'env val="' + 'a"b"c' * 50 + '"\n'
    doc = parse(text)
    assert render(doc) == text


def test_unicode_content() -> None:
    text = "env name=日本語テスト\n"
    doc = parse(text)
    assert render(doc) == text


def test_mixed_newlines() -> None:
    text = "hostname\r\nclientid\ninterface eth0\r\nmetric 100\n"
    doc = parse(text)
    assert render(doc) == text


def test_null_bytes() -> None:
    text = "hostname\x00value\n"
    doc = parse(text)
    assert render(doc) == text


def test_empty_lines_only() -> None:
    text = "\n\n\n\n\n"
    doc = parse(text)
    assert render(doc) == text
    assert len(doc.nodes) == 5
