"""Lexer for dhcpcd.conf files.

Follows upstream ``get_line()`` from ``src/common.c`` for comment detection,
quote handling, and escape semantics, but preserves all raw text for lossless
round-tripping.
"""

from __future__ import annotations

from pydhcpcdparser.ast import BlankLine, Comment, Directive, Node, SourceSpan


def _find_inline_comment(text: str) -> int | None:
    """Return the index of an unquoted, unescaped ``#`` or *None*.

    Mirrors upstream ``get_line()`` logic: backslash escapes the next
    character, double-quotes toggle quoting, and ``#`` outside quotes
    starts a comment.
    """
    quoted = False
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if ch == "\\":
            i += 2  # skip escaped character
            continue
        if ch == '"':
            quoted = not quoted
        elif ch == "#" and not quoted:
            return i
        i += 1
    return None


def lex_line(
    raw_line: str,
    line_number: int,
    offset: int,
    newline: str,
) -> Node:
    """Classify and parse a single raw line (without its line ending) into a ``Node``.

    *raw_line* is the content of the line **including** its trailing newline
    characters (which are also passed separately as *newline* for the node).
    """
    content = raw_line
    if content.endswith("\r\n"):
        content = content[:-2]
    elif content.endswith("\n") or content.endswith("\r"):
        content = content[:-1]

    span = SourceSpan(
        line=line_number,
        column=0,
        start=offset,
        end=offset + len(raw_line),
    )

    # Blank / whitespace-only line
    if content.strip() == "":
        return BlankLine(source_span=span, raw=raw_line, newline=newline)

    # Find first non-whitespace character
    stripped = content.lstrip(" \t")
    first_char = stripped[0] if stripped else ""

    # Comment line: first non-space is # or ;
    if first_char in ("#", ";"):
        return Comment(
            source_span=span,
            raw=raw_line,
            newline=newline,
            text=stripped[1:] if len(stripped) > 1 else "",
            prefix=first_char,
        )

    # Directive line
    leading_ws = content[: len(content) - len(stripped)]

    # Split name from value: first whitespace after the directive name
    name_end = 0
    for i, ch in enumerate(stripped):
        if ch in (" ", "\t"):
            name_end = i
            break
    else:
        name_end = len(stripped)

    name = stripped[:name_end]
    rest = stripped[name_end:]

    if rest:
        # Capture the exact separator (whitespace between name and value+comment)
        sep_end = 0
        for j, ch in enumerate(rest):
            if ch not in (" ", "\t"):
                sep_end = j
                break
        else:
            sep_end = len(rest)

        separator = rest[:sep_end]
        value_and_comment = rest[sep_end:]
    else:
        separator = ""
        value_and_comment = ""

    # Detect inline comment in value_and_comment
    value: str | None
    inline_comment: str | None = None
    if value_and_comment:
        comment_pos = _find_inline_comment(value_and_comment)
        if comment_pos is not None and comment_pos > 0:
            # There may be trailing whitespace before the comment
            value_part = value_and_comment[:comment_pos]
            inline_comment = value_and_comment[comment_pos:]
            # Trim trailing whitespace from value part (upstream trims it)
            # but keep it in raw — we reconstruct from raw anyway
            value = value_part.rstrip(" \t") if value_part.strip() else None
            # Keep whitespace between value and comment in the inline_comment
            # so rendering is lossless from raw
            trailing_ws = value_part[len(value_part.rstrip(" \t")) :] if value else value_part
            inline_comment = trailing_ws + inline_comment
        elif comment_pos == 0:
            # The entire "value" is actually a comment (e.g. ``hostname # foo``)
            # but upstream would interpret ``#`` as starting a comment,
            # so there is no value, only separator then comment.
            value = None
            inline_comment = value_and_comment
        else:
            value = value_and_comment
    else:
        value = value_and_comment if value_and_comment else None

    return Directive(
        source_span=span,
        raw=raw_line,
        newline=newline,
        name=name,
        value=value if value else None,
        leading_whitespace=leading_ws,
        separator=separator,
        inline_comment=inline_comment,
    )
