"""Unit tests for the renderer."""

from __future__ import annotations

from pydhcpcdparser.ast import BlankLine, Comment, Directive, Document
from pydhcpcdparser.renderer import render, render_node


def test_render_blank_line() -> None:
    node = BlankLine(raw="\n", newline="\n")
    assert render_node(node) == "\n"


def test_render_comment() -> None:
    node = Comment(raw="# hello\n", newline="\n", text=" hello", prefix="#")
    assert render_node(node) == "# hello\n"


def test_render_directive_no_value() -> None:
    node = Directive(raw="hostname\n", newline="\n", name="hostname")
    assert render_node(node) == "hostname\n"


def test_render_directive_with_value() -> None:
    node = Directive(raw="metric 100\n", newline="\n", name="metric", value="100", separator=" ")
    assert render_node(node) == "metric 100\n"


def test_render_modified_directive() -> None:
    node = Directive(
        raw="metric 100\n",
        newline="\n",
        name="metric",
        value="200",
        separator=" ",
        modified=True,
    )
    result = render_node(node)
    assert result == "metric 200\n"


def test_render_new_directive() -> None:
    node = Directive(
        raw="",
        newline="\n",
        name="nogateway",
        modified=True,
    )
    result = render_node(node)
    assert result == "nogateway\n"


def test_render_new_directive_with_value() -> None:
    node = Directive(
        raw="",
        newline="\n",
        name="metric",
        value="100",
        separator=" ",
        modified=True,
    )
    result = render_node(node)
    assert result == "metric 100\n"


def test_render_preserves_leading_whitespace() -> None:
    node = Directive(
        raw="",
        newline="\n",
        name="metric",
        value="200",
        separator=" ",
        leading_whitespace="  ",
        modified=True,
    )
    result = render_node(node)
    assert result == "  metric 200\n"


def test_render_preserves_inline_comment() -> None:
    node = Directive(
        raw="",
        newline="\n",
        name="metric",
        value="100",
        separator=" ",
        inline_comment=" # important",
        modified=True,
    )
    result = render_node(node)
    assert result == "metric 100 # important\n"


def test_render_document() -> None:
    doc = Document(
        nodes=[
            Comment(raw="# comment\n", newline="\n", text=" comment", prefix="#"),
            Directive(raw="hostname\n", newline="\n", name="hostname"),
        ],
        newline="\n",
    )
    assert render(doc) == "# comment\nhostname\n"


def test_render_empty_document() -> None:
    doc = Document(nodes=[], newline="\n")
    assert render(doc) == ""


def test_render_crlf() -> None:
    node = Directive(raw="hostname\r\n", newline="\r\n", name="hostname")
    assert render_node(node) == "hostname\r\n"
