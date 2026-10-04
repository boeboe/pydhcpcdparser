"""Renderer that reconstructs dhcpcd.conf text from a ``Document``.

Unmodified nodes emit their original ``raw`` text.  Modified or newly
created nodes are rendered from their structured fields.
"""

from __future__ import annotations

from pydhcpcdparser.ast import BlankLine, Comment, Directive, Document, Node


def render_node(node: Node, doc_newline: str = "\n") -> str:
    """Render a single *node* to its text representation.

    Unmodified nodes return their stored ``raw`` text verbatim.
    Modified or newly created nodes (``raw == ""``) are rebuilt from
    structured fields.
    """
    if node.raw and not node.modified:
        return node.raw

    nl = node.newline if node.newline else doc_newline

    if isinstance(node, BlankLine):
        return nl

    if isinstance(node, Comment):
        return f"{node.prefix}{node.text}{nl}"

    if isinstance(node, Directive):
        parts: list[str] = [node.leading_whitespace, node.name]
        if node.value is not None:
            sep = node.separator if node.separator else " "
            parts.append(sep)
            parts.append(node.value)
        if node.inline_comment is not None:
            parts.append(node.inline_comment)
        parts.append(nl)
        return "".join(parts)

    # Fallback for InvalidLine or unknown node types
    return node.raw if node.raw else ""


def render(doc: Document) -> str:
    """Render a full *doc* back to text.

    For an unmodified document: ``render(parse(text)) == text``.
    """
    return "".join(render_node(node, doc.newline) for node in doc.nodes)
