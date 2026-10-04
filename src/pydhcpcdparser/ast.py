"""Lossless AST nodes for dhcpcd.conf documents."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceSpan:
    """Source location information for a parsed node."""

    line: int
    column: int
    start: int
    end: int


@dataclass
class Node:
    """Base class for all AST nodes."""

    source_span: SourceSpan | None = None
    raw: str = ""
    modified: bool = field(default=False, repr=False)
    newline: str = field(default="\n", repr=False)


@dataclass
class BlankLine(Node):
    """A blank or whitespace-only line."""


@dataclass
class Comment(Node):
    """A comment line (``#`` or ``;`` prefix)."""

    text: str = ""
    prefix: str = "#"


@dataclass
class Directive(Node):
    """A configuration directive with an optional value."""

    name: str = ""
    value: str | None = None
    leading_whitespace: str = ""
    separator: str = " "
    inline_comment: str | None = None


@dataclass
class InvalidLine(Node):
    """A line that could not be parsed (only emitted in strict mode diagnostics)."""

    error: str = ""


@dataclass
class Document:
    """An ordered sequence of AST nodes representing a dhcpcd.conf file."""

    nodes: list[Node] = field(default_factory=list)
    newline: str = "\n"
