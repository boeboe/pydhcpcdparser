"""Unit tests for the parser."""

from __future__ import annotations

import pytest

from pydhcpcdparser import parse
from pydhcpcdparser.ast import BlankLine, Comment, Directive
from pydhcpcdparser.exceptions import DhcpcdParseError
from pydhcpcdparser.renderer import render


def test_empty_input() -> None:
    doc = parse("")
    assert doc.nodes == []
    assert render(doc) == ""


def test_single_directive() -> None:
    doc = parse("hostname\n")
    assert len(doc.nodes) == 1
    assert isinstance(doc.nodes[0], Directive)
    assert doc.nodes[0].name == "hostname"


def test_multiple_lines() -> None:
    text = "hostname\nclientid\n"
    doc = parse(text)
    assert len(doc.nodes) == 2
    assert all(isinstance(n, Directive) for n in doc.nodes)


def test_comments_and_blanks() -> None:
    text = "# comment\n\nhostname\n"
    doc = parse(text)
    assert len(doc.nodes) == 3
    assert isinstance(doc.nodes[0], Comment)
    assert isinstance(doc.nodes[1], BlankLine)
    assert isinstance(doc.nodes[2], Directive)


def test_newline_detection_lf() -> None:
    doc = parse("a\nb\n")
    assert doc.newline == "\n"


def test_newline_detection_crlf() -> None:
    doc = parse("a\r\nb\r\n")
    assert doc.newline == "\r\n"


def test_no_final_newline() -> None:
    text = "hostname\nclientid"
    doc = parse(text)
    assert len(doc.nodes) == 2
    output = render(doc)
    assert output == text


def test_strict_unterminated_quote() -> None:
    with pytest.raises(DhcpcdParseError, match="Unterminated quote"):
        parse('env foo="unterminated\n', strict=True)


def test_non_strict_unterminated_quote() -> None:
    doc = parse('env foo="unterminated\n', strict=False)
    assert len(doc.nodes) == 1


def test_unknown_directive_parses() -> None:
    doc = parse("future_option foo bar\n")
    assert len(doc.nodes) == 1
    assert isinstance(doc.nodes[0], Directive)
    assert doc.nodes[0].name == "future_option"
    assert doc.nodes[0].value == "foo bar"


def test_preserve_node_order() -> None:
    text = "# comment\nhostname\n\ninterface eth0\nmetric 100\n"
    doc = parse(text)
    types = [type(n).__name__ for n in doc.nodes]
    assert types == ["Comment", "Directive", "BlankLine", "Directive", "Directive"]
