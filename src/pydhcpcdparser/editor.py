"""Editing operations for Document and ScopeView.

All mutations go through this module so that:
- only the changed node is marked ``modified``
- unmodified nodes retain their ``raw`` text for lossless rendering
- the flat AST order is maintained
"""

from __future__ import annotations

import contextlib
import os
import stat
import tempfile
from pathlib import Path

from pydhcpcdparser.ast import BlankLine, Comment, Directive, Document, Node
from pydhcpcdparser.renderer import render
from pydhcpcdparser.semantics import (
    _SCOPE_OPENERS,
    ScopeKind,
    ScopeView,
)

# ---------------------------------------------------------------------------
# Low-level node helpers
# ---------------------------------------------------------------------------


def _make_directive(
    name: str,
    value: str | None = None,
    *,
    newline: str = "\n",
    leading_whitespace: str = "",
    separator: str = " ",
    inline_comment: str | None = None,
) -> Directive:
    """Create a new ``Directive`` node marked as modified."""
    return Directive(
        raw="",
        newline=newline,
        modified=True,
        name=name,
        value=value,
        leading_whitespace=leading_whitespace,
        separator=separator,
        inline_comment=inline_comment,
    )


def _make_blank(newline: str = "\n") -> BlankLine:
    """Create a new ``BlankLine`` node marked as modified."""
    return BlankLine(raw="", newline=newline, modified=True)


def _make_comment(text: str, *, prefix: str = "#", newline: str = "\n") -> Comment:
    """Create a new ``Comment`` node marked as modified."""
    return Comment(raw="", newline=newline, modified=True, text=text, prefix=prefix)


def _update_directive_value(directive: Directive, new_value: str | None) -> None:
    """Update a directive's value in-place and mark it as modified."""
    directive.value = new_value
    directive.modified = True


# ---------------------------------------------------------------------------
# ScopeView editing helpers
# ---------------------------------------------------------------------------


def _scope_last_block_end(scope: ScopeView) -> int:
    """Return the exclusive end index of the last physical block in *scope*."""
    return scope.blocks[-1].end_index


def _scope_insert_index(doc: Document, scope: ScopeView) -> int:
    """Return the index at which a new directive should be appended in *scope*.

    Re-derives scope boundaries from the live node list so inserts remain
    correct after earlier mutations.
    """
    # Find the scope-opening directive node in the current node list
    last_block = scope.blocks[-1]
    if last_block.kind == ScopeKind.GLOBAL:
        # Global scope: insert before the first scope-opening directive
        for i, node in enumerate(doc.nodes):
            if isinstance(node, Directive) and node.name in _SCOPE_OPENERS:
                return i
        return len(doc.nodes)

    # For interface/ssid/profile scopes, find the opener in the live list
    # and scan forward to the next scope opener
    opener_idx: int | None = None
    for block in scope.blocks:
        if block.start_index < len(doc.nodes):
            candidate = doc.nodes[block.start_index]
            if isinstance(candidate, Directive) and candidate.name in _SCOPE_OPENERS:
                opener_idx = block.start_index

    if opener_idx is None:
        # Opener was moved; search by identity from the last block
        return len(doc.nodes)

    # Scan from the opener to the next scope-opening directive
    for i in range(opener_idx + 1, len(doc.nodes)):
        node = doc.nodes[i]
        if isinstance(node, Directive) and node.name in _SCOPE_OPENERS:
            return i
    return len(doc.nodes)


def scope_add_directive(
    doc: Document,
    scope: ScopeView,
    name: str,
    value: str | None = None,
) -> Directive:
    """Append a new directive at the end of *scope*."""
    node = _make_directive(name, value, newline=doc.newline)
    idx = _scope_insert_index(doc, scope)
    doc.nodes.insert(idx, node)
    return node


def scope_set(
    doc: Document,
    scope: ScopeView,
    name: str,
    value: str | None = None,
) -> Directive:
    """Set the first directive named *name* in *scope*, or append one."""
    existing = scope.find(name)
    if existing is not None:
        _update_directive_value(existing, value)
        return existing
    return scope_add_directive(doc, scope, name, value)


def scope_set_static(
    doc: Document,
    scope: ScopeView,
    key: str,
    value: str,
) -> Directive:
    """Set the first ``static key=value`` in *scope*, or append one."""
    prefix = f"{key}="
    for d in scope.directives:
        if d.name == "static" and d.value is not None and d.value.startswith(prefix):
            _update_directive_value(d, f"{key}={value}")
            return d
    return scope_add_directive(doc, scope, "static", f"{key}={value}")


def scope_remove(doc: Document, scope: ScopeView, name: str) -> bool:
    """Remove the first directive named *name* from *scope*.  Returns True if found."""
    for d in scope.directives:
        if d.name == name:
            doc.nodes.remove(d)
            return True
    return False


def scope_remove_all(doc: Document, scope: ScopeView, name: str) -> int:
    """Remove all directives named *name* from *scope*.  Returns the count removed."""
    to_remove = [d for d in scope.directives if d.name == name]
    for d in to_remove:
        doc.nodes.remove(d)
    return len(to_remove)


def scope_remove_static(doc: Document, scope: ScopeView, key: str) -> bool:
    """Remove the first ``static key=...`` from *scope*."""
    prefix = f"{key}="
    for d in scope.directives:
        if d.name == "static" and d.value is not None and d.value.startswith(prefix):
            doc.nodes.remove(d)
            return True
    return False


def scope_remove_all_static(doc: Document, scope: ScopeView, key: str) -> int:
    """Remove all ``static key=...`` from *scope*."""
    prefix = f"{key}="
    to_remove = [
        d
        for d in scope.directives
        if d.name == "static" and d.value is not None and d.value.startswith(prefix)
    ]
    for d in to_remove:
        doc.nodes.remove(d)
    return len(to_remove)


def scope_replace_first(
    doc: Document,
    scope: ScopeView,
    name: str,
    value: str | None,
) -> Directive | None:
    """Replace the value of the first directive named *name*."""
    d = scope.find(name)
    if d is not None:
        _update_directive_value(d, value)
    return d


def scope_replace_all(
    doc: Document,
    scope: ScopeView,
    name: str,
    value: str | None,
) -> list[Directive]:
    """Replace the value of every directive named *name*."""
    result: list[Directive] = []
    for d in scope.directives:
        if d.name == name:
            _update_directive_value(d, value)
            result.append(d)
    return result


# ---------------------------------------------------------------------------
# Document-level editing
# ---------------------------------------------------------------------------


def doc_append(doc: Document, node: Node) -> None:
    """Append *node* to the end of the document."""
    doc.nodes.append(node)


def doc_insert(doc: Document, index: int, node: Node) -> None:
    """Insert *node* at *index*."""
    doc.nodes.insert(index, node)


def doc_remove(doc: Document, node: Node) -> None:
    """Remove *node* from the document."""
    doc.nodes.remove(node)


def doc_add_directive(
    doc: Document,
    name: str,
    value: str | None = None,
) -> Directive:
    """Append a new directive to the document."""
    node = _make_directive(name, value, newline=doc.newline)
    doc.nodes.append(node)
    return node


def doc_add_blank(doc: Document) -> BlankLine:
    """Append a blank line."""
    node = _make_blank(doc.newline)
    doc.nodes.append(node)
    return node


def doc_add_comment(doc: Document, text: str, *, prefix: str = "#") -> Comment:
    """Append a comment line."""
    node = _make_comment(text, prefix=prefix, newline=doc.newline)
    doc.nodes.append(node)
    return node


def _doc_add_scope(
    doc: Document,
    kind_name: str,
    name: str,
) -> ScopeView:
    """Add a new scope-opening directive and return a ScopeView for it."""
    node = _make_directive(kind_name, name, newline=doc.newline)
    doc.nodes.append(node)
    # Build a temporary view pointing at the just-added node
    from pydhcpcdparser.semantics import ScopeBlock
    from pydhcpcdparser.semantics import ScopeView as ScopeViewCls

    idx = len(doc.nodes) - 1
    block = ScopeBlock(
        kind=ScopeKind(kind_name),
        name=name,
        start_index=idx,
        end_index=idx + 1,
    )
    return ScopeViewCls(doc, [block])


def doc_add_interface(doc: Document, name: str) -> ScopeView:
    """Append a new ``interface`` block and return its ScopeView."""
    return _doc_add_scope(doc, "interface", name)


def doc_add_profile(doc: Document, name: str) -> ScopeView:
    """Append a new ``profile`` block and return its ScopeView."""
    return _doc_add_scope(doc, "profile", name)


def doc_add_ssid(doc: Document, name: str) -> ScopeView:
    """Append a new ``ssid`` block and return its ScopeView."""
    return _doc_add_scope(doc, "ssid", name)


def doc_ensure_interface(doc: Document, name: str) -> ScopeView:
    """Return the interface scope for *name*, creating one if it doesn't exist."""
    from pydhcpcdparser.exceptions import ScopeNotFoundError
    from pydhcpcdparser.semantics import interface

    try:
        return interface(doc, name)
    except ScopeNotFoundError:
        return doc_add_interface(doc, name)


def doc_ensure_profile(doc: Document, name: str) -> ScopeView:
    """Return the profile scope for *name*, creating one if it doesn't exist."""
    from pydhcpcdparser.exceptions import ScopeNotFoundError
    from pydhcpcdparser.semantics import profile

    try:
        return profile(doc, name)
    except ScopeNotFoundError:
        return doc_add_profile(doc, name)


def doc_ensure_ssid(doc: Document, name: str) -> ScopeView:
    """Return the ssid scope for *name*, creating one if it doesn't exist."""
    from pydhcpcdparser.exceptions import ScopeNotFoundError
    from pydhcpcdparser.semantics import ssid

    try:
        return ssid(doc, name)
    except ScopeNotFoundError:
        return doc_add_ssid(doc, name)


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


def doc_write(doc: Document, path: str | Path) -> None:
    """Write the rendered document to *path*."""
    Path(path).write_text(render(doc), encoding="utf-8", errors="surrogateescape")


def doc_write_atomic(doc: Document, path: str | Path) -> None:
    """Atomically write the rendered document to *path*.

    Uses a temporary file in the same directory, ``fsync``, then
    ``os.replace``.  Preserves the existing file's permission mode
    when the target already exists.
    """
    target = Path(path)
    text = render(doc)
    encoded = text.encode("utf-8", errors="surrogateescape")

    # Capture existing mode
    try:
        existing_mode = target.stat().st_mode
    except FileNotFoundError:
        existing_mode = None

    fd = -1
    tmp_path: str | None = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=str(target.parent), prefix=".dhcpcd_tmp_")
        os.write(fd, encoded)
        os.fsync(fd)
        os.close(fd)
        fd = -1

        if existing_mode is not None:
            os.chmod(tmp_path, stat.S_IMODE(existing_mode))

        os.replace(tmp_path, str(target))
        tmp_path = None  # successfully moved
    finally:
        if fd >= 0:
            os.close(fd)
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)


def doc_from_path(path: str | Path) -> Document:
    """Parse a document from a file path."""
    from pydhcpcdparser.parser import parse

    text = Path(path).read_text(encoding="utf-8", errors="surrogateescape")
    return parse(text)


# ---------------------------------------------------------------------------
# Attach methods to Document and ScopeView
# ---------------------------------------------------------------------------


def _sv_set(self: ScopeView, name: str, value: str | None = None) -> Directive:
    """Set a directive in this scope, creating it if absent."""
    return scope_set(self._doc, self, name, value)


def _sv_add_directive(self: ScopeView, name: str, value: str | None = None) -> Directive:
    """Append a new directive to this scope."""
    return scope_add_directive(self._doc, self, name, value)


def _sv_set_static(self: ScopeView, key: str, value: str) -> Directive:
    """Set a ``static key=value`` in this scope, creating it if absent."""
    return scope_set_static(self._doc, self, key, value)


def _sv_remove(self: ScopeView, name: str) -> bool:
    """Remove the first directive named *name* from this scope."""
    return scope_remove(self._doc, self, name)


def _sv_remove_all(self: ScopeView, name: str) -> int:
    """Remove all directives named *name* from this scope."""
    return scope_remove_all(self._doc, self, name)


def _sv_remove_static(self: ScopeView, key: str) -> bool:
    """Remove the first ``static key=...`` from this scope."""
    return scope_remove_static(self._doc, self, key)


def _sv_remove_all_static(self: ScopeView, key: str) -> int:
    """Remove all ``static key=...`` from this scope."""
    return scope_remove_all_static(self._doc, self, key)


def _sv_replace_first(self: ScopeView, name: str, value: str | None) -> Directive | None:
    """Replace the value of the first directive named *name* in this scope."""
    return scope_replace_first(self._doc, self, name, value)


def _sv_replace_all(self: ScopeView, name: str, value: str | None) -> list[Directive]:
    """Replace the value of every directive named *name* in this scope."""
    return scope_replace_all(self._doc, self, name, value)


ScopeView.set = _sv_set  # type: ignore[attr-defined]
ScopeView.add_directive = _sv_add_directive  # type: ignore[attr-defined]
ScopeView.set_static = _sv_set_static  # type: ignore[attr-defined]
ScopeView.remove = _sv_remove  # type: ignore[attr-defined]
ScopeView.remove_all = _sv_remove_all  # type: ignore[attr-defined]
ScopeView.remove_static = _sv_remove_static  # type: ignore[attr-defined]
ScopeView.remove_all_static = _sv_remove_all_static  # type: ignore[attr-defined]
ScopeView.replace_first = _sv_replace_first  # type: ignore[attr-defined]
ScopeView.replace_all = _sv_replace_all  # type: ignore[attr-defined]


def _doc_append_method(self: Document, node: Node) -> None:
    """Append a node to the document."""
    doc_append(self, node)


def _doc_insert_method(self: Document, index: int, node: Node) -> None:
    """Insert a node at the given index."""
    doc_insert(self, index, node)


def _doc_remove_method(self: Document, node: Node) -> None:
    """Remove a node from the document."""
    doc_remove(self, node)


def _doc_add_directive_method(self: Document, name: str, value: str | None = None) -> Directive:
    """Append a new directive to the document."""
    return doc_add_directive(self, name, value)


def _doc_add_blank_method(self: Document) -> BlankLine:
    """Append a blank line to the document."""
    return doc_add_blank(self)


def _doc_add_comment_method(self: Document, text: str, *, prefix: str = "#") -> Comment:
    """Append a comment line to the document."""
    return doc_add_comment(self, text, prefix=prefix)


def _doc_add_interface_method(self: Document, name: str) -> ScopeView:
    """Append a new ``interface`` block to the document."""
    return doc_add_interface(self, name)


def _doc_add_profile_method(self: Document, name: str) -> ScopeView:
    """Append a new ``profile`` block to the document."""
    return doc_add_profile(self, name)


def _doc_add_ssid_method(self: Document, name: str) -> ScopeView:
    """Append a new ``ssid`` block to the document."""
    return doc_add_ssid(self, name)


def _doc_ensure_interface_method(self: Document, name: str) -> ScopeView:
    """Return or create the ``interface`` scope for *name*."""
    return doc_ensure_interface(self, name)


def _doc_ensure_profile_method(self: Document, name: str) -> ScopeView:
    """Return or create the ``profile`` scope for *name*."""
    return doc_ensure_profile(self, name)


def _doc_ensure_ssid_method(self: Document, name: str) -> ScopeView:
    """Return or create the ``ssid`` scope for *name*."""
    return doc_ensure_ssid(self, name)


def _doc_write_method(self: Document, path: str | Path) -> None:
    """Write the rendered document to *path*."""
    doc_write(self, path)


def _doc_write_atomic_method(self: Document, path: str | Path) -> None:
    """Atomically write the rendered document to *path*."""
    doc_write_atomic(self, path)


Document.append = _doc_append_method  # type: ignore[attr-defined]
Document.insert = _doc_insert_method  # type: ignore[attr-defined]
Document.remove = _doc_remove_method  # type: ignore[attr-defined]
Document.add_directive = _doc_add_directive_method  # type: ignore[attr-defined]
Document.add_blank = _doc_add_blank_method  # type: ignore[attr-defined]
Document.add_comment = _doc_add_comment_method  # type: ignore[attr-defined]
Document.add_interface = _doc_add_interface_method  # type: ignore[attr-defined]
Document.add_profile = _doc_add_profile_method  # type: ignore[attr-defined]
Document.add_ssid = _doc_add_ssid_method  # type: ignore[attr-defined]
Document.ensure_interface = _doc_ensure_interface_method  # type: ignore[attr-defined]
Document.ensure_profile = _doc_ensure_profile_method  # type: ignore[attr-defined]
Document.ensure_ssid = _doc_ensure_ssid_method  # type: ignore[attr-defined]
Document.write = _doc_write_method  # type: ignore[attr-defined]
Document.write_atomic = _doc_write_atomic_method  # type: ignore[attr-defined]
Document.from_path = staticmethod(doc_from_path)  # type: ignore[attr-defined]
