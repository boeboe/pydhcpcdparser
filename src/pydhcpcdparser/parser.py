"""Parser for dhcpcd.conf text into a lossless ``Document``."""

from __future__ import annotations

from pydhcpcdparser.ast import Document, Node
from pydhcpcdparser.exceptions import DhcpcdParseError
from pydhcpcdparser.lexer import lex_line


def _detect_newline(text: str) -> str:
    """Detect the dominant line ending in *text*."""
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    if crlf > lf:
        return "\r\n"
    return "\n"


def _split_lines(text: str) -> list[str]:
    """Split *text* into lines, each retaining its line ending.

    The final element may lack a trailing newline when the source has
    no final newline.
    """
    lines: list[str] = []
    i = 0
    length = len(text)
    while i < length:
        nl = text.find("\n", i)
        if nl == -1:
            # Remaining text has no newline — last line without final newline
            lines.append(text[i:])
            break
        # Include the \n (and a preceding \r if present)
        lines.append(text[i : nl + 1])
        i = nl + 1
    return lines


def parse(text: str, *, strict: bool = False) -> Document:
    """Parse *text* into a :class:`Document`.

    With *strict=False* (default) the parser accepts as much content as
    possible.  Strict mode raises :exc:`DhcpcdParseError` on clearly
    malformed syntax such as unterminated quotes.
    """
    if not text:
        return Document(nodes=[], newline="\n")

    dominant_newline = _detect_newline(text)
    raw_lines = _split_lines(text)

    nodes: list[Node] = []
    offset = 0
    for line_no, raw_line in enumerate(raw_lines, start=1):
        # Determine this line's actual newline
        if raw_line.endswith("\r\n"):
            line_nl = "\r\n"
        elif raw_line.endswith("\n"):
            line_nl = "\n"
        else:
            line_nl = ""

        node = lex_line(raw_line, line_number=line_no, offset=offset, newline=line_nl)
        nodes.append(node)
        offset += len(raw_line)

    if strict:
        _strict_check(nodes)

    return Document(nodes=nodes, newline=dominant_newline)


def _strict_check(nodes: list[Node]) -> None:
    """Raise for clearly malformed syntax."""
    from pydhcpcdparser.ast import Directive

    for node in nodes:
        if not isinstance(node, Directive):
            continue
        # Check for unterminated quotes
        raw_value = node.value or ""
        if node.inline_comment:
            raw_value = raw_value + node.inline_comment
        quoted = False
        i = 0
        while i < len(raw_value):
            ch = raw_value[i]
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                quoted = not quoted
            i += 1
        if quoted:
            span = node.source_span
            loc = f"line {span.line}" if span else "unknown location"
            raise DhcpcdParseError(f"Unterminated quote at {loc}")
