"""Semantic layer: scope derivation, query helpers, and static-assignment access.

The AST stays flat.  This module derives logical scopes by walking directive
nodes, following the same rules as upstream ``read_config()`` in
``src/if-options.c``.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from pydhcpcdparser.ast import Directive, Document, Node
from pydhcpcdparser.exceptions import ScopeNotFoundError

if TYPE_CHECKING:
    from collections.abc import Sequence

# Directives that open a new scope block
_SCOPE_OPENERS = frozenset({"interface", "ssid", "profile"})


class ScopeKind(Enum):
    """The kind of scope block in a dhcpcd.conf file."""

    GLOBAL = "global"
    INTERFACE = "interface"
    PROFILE = "profile"
    SSID = "ssid"


@dataclass(frozen=True)
class ScopeBlock:
    """A contiguous physical block of nodes sharing a scope.

    *start_index* is the index of the scope-opening directive (or 0 for the
    global scope).  *end_index* is exclusive.
    """

    kind: ScopeKind
    name: str | None
    start_index: int
    end_index: int


class ScopeView:
    """A read-only view over one or more physical scope blocks.

    Provides query helpers such as :meth:`find`, :meth:`find_all`,
    :meth:`static`, and :meth:`static_all`.
    """

    def __init__(self, doc: Document, blocks: Sequence[ScopeBlock]) -> None:
        self._doc = doc
        self._blocks = list(blocks)

    @property
    def blocks(self) -> list[ScopeBlock]:
        """The physical scope blocks backing this view."""
        return list(self._blocks)

    @property
    def kind(self) -> ScopeKind:
        """The scope kind (global, interface, ssid, or profile)."""
        return self._blocks[0].kind

    @property
    def name(self) -> str | None:
        """The scope name, or ``None`` for the global scope."""
        return self._blocks[0].name

    # -- iteration -----------------------------------------------------------

    @property
    def directives(self) -> list[Directive]:
        """All :class:`Directive` nodes inside the scope (excluding the opener)."""
        result: list[Directive] = []
        for block in self._blocks:
            start = block.start_index
            # Skip the scope-opening directive itself (interface/ssid/profile)
            if block.kind != ScopeKind.GLOBAL:
                start += 1
            for node in self._doc.nodes[start : block.end_index]:
                if isinstance(node, Directive):
                    result.append(node)
        return result

    @property
    def nodes(self) -> list[Node]:
        """All nodes inside the scope (including comments/blanks, excluding opener)."""
        result: list[Node] = []
        for block in self._blocks:
            start = block.start_index
            if block.kind != ScopeKind.GLOBAL:
                start += 1
            result.extend(self._doc.nodes[start : block.end_index])
        return result

    # -- query helpers -------------------------------------------------------

    def find(self, name: str) -> Directive | None:
        """Return the first directive matching *name*, or ``None``."""
        for d in self.directives:
            if d.name == name:
                return d
        return None

    def find_all(self, name: str) -> list[Directive]:
        """Return every directive matching *name*."""
        return [d for d in self.directives if d.name == name]

    def static(self, key: str) -> str | None:
        """Return the value of the last ``static key=...`` assignment, or ``None``.

        For example, ``scope.static("ip_address")`` returns ``"192.168.1.17/32"``
        if the scope contains ``static ip_address=192.168.1.17/32``.
        """
        result: str | None = None
        prefix = f"{key}="
        for d in self.directives:
            if d.name == "static" and d.value is not None and d.value.startswith(prefix):
                result = d.value[len(prefix) :]
        return result

    def static_all(self, key: str) -> list[str]:
        """Return every ``static key=...`` value."""
        prefix = f"{key}="
        return [
            d.value[len(prefix) :]
            for d in self.directives
            if d.name == "static" and d.value is not None and d.value.startswith(prefix)
        ]

    def static_assignment(self, directive: Directive) -> tuple[str, str] | None:
        """Split a ``static`` directive's value into ``(key, value)``."""
        if directive.name != "static" or directive.value is None:
            return None
        eq = directive.value.find("=")
        if eq == -1:
            return (directive.value, "")
        return (directive.value[:eq], directive.value[eq + 1 :])


# ---------------------------------------------------------------------------
# Scope derivation
# ---------------------------------------------------------------------------


def derive_scopes(doc: Document) -> list[ScopeBlock]:
    """Walk *doc* and return an ordered list of physical scope blocks.

    Comments and blank lines do not affect scope boundaries.  A new
    ``interface``, ``ssid``, or ``profile`` directive ends the previous block
    and starts a new one.
    """
    blocks: list[ScopeBlock] = []
    current_kind = ScopeKind.GLOBAL
    current_name: str | None = None
    current_start = 0

    for i, node in enumerate(doc.nodes):
        if isinstance(node, Directive) and node.name in _SCOPE_OPENERS:
            # Close the previous block
            blocks.append(
                ScopeBlock(
                    kind=current_kind,
                    name=current_name,
                    start_index=current_start,
                    end_index=i,
                )
            )
            # Open a new block
            current_kind = ScopeKind(node.name)
            current_name = node.value
            current_start = i

    # Close the final block
    blocks.append(
        ScopeBlock(
            kind=current_kind,
            name=current_name,
            start_index=current_start,
            end_index=len(doc.nodes),
        )
    )

    return blocks


def _kind_for_name(name: str) -> ScopeKind:
    """Convert a directive name to its corresponding ``ScopeKind``."""
    return ScopeKind(name)


# ---------------------------------------------------------------------------
# Document query helpers (added as methods by the editor module)
# ---------------------------------------------------------------------------


def scopes(doc: Document) -> list[ScopeView]:
    """Return every scope block as a :class:`ScopeView`."""
    return [ScopeView(doc, [b]) for b in derive_scopes(doc)]


def _matching_blocks(
    doc: Document,
    kind: ScopeKind,
    name: str,
) -> list[ScopeBlock]:
    """Return physical blocks of *kind* whose name matches *name*."""
    result: list[ScopeBlock] = []
    for block in derive_scopes(doc):
        if block.kind != kind:
            continue
        if block.name is None:
            continue
        if kind == ScopeKind.INTERFACE:
            # Upstream uses fnmatch: the file text is the pattern
            if fnmatch.fnmatchcase(name, block.name):
                result.append(block)
        else:
            # ssid and profile use exact match
            if block.name == name:
                result.append(block)
    return result


def interface_blocks(doc: Document, name: str) -> list[ScopeView]:
    """Return each physical ``interface`` block matching *name*."""
    blocks = _matching_blocks(doc, ScopeKind.INTERFACE, name)
    return [ScopeView(doc, [b]) for b in blocks]


def interface(doc: Document, name: str) -> ScopeView:
    """Return a logical view combining all ``interface`` blocks for *name*.

    Raises :exc:`ScopeNotFoundError` if no matching block exists.
    """
    blocks = _matching_blocks(doc, ScopeKind.INTERFACE, name)
    if not blocks:
        raise ScopeNotFoundError(f"No interface block found for {name!r}")
    return ScopeView(doc, blocks)


def profile_blocks(doc: Document, name: str) -> list[ScopeView]:
    """Return each physical ``profile`` block matching *name*."""
    blocks = _matching_blocks(doc, ScopeKind.PROFILE, name)
    return [ScopeView(doc, [b]) for b in blocks]


def profile(doc: Document, name: str) -> ScopeView:
    """Return a logical view combining all ``profile`` blocks for *name*."""
    blocks = _matching_blocks(doc, ScopeKind.PROFILE, name)
    if not blocks:
        raise ScopeNotFoundError(f"No profile block found for {name!r}")
    return ScopeView(doc, blocks)


def ssid_blocks(doc: Document, name: str) -> list[ScopeView]:
    """Return each physical ``ssid`` block matching *name*."""
    blocks = _matching_blocks(doc, ScopeKind.SSID, name)
    return [ScopeView(doc, [b]) for b in blocks]


def ssid(doc: Document, name: str) -> ScopeView:
    """Return a logical view combining all ``ssid`` blocks for *name*."""
    blocks = _matching_blocks(doc, ScopeKind.SSID, name)
    if not blocks:
        raise ScopeNotFoundError(f"No ssid block found for {name!r}")
    return ScopeView(doc, blocks)


def _unique_names(doc: Document, kind: ScopeKind) -> list[str]:
    """Return distinct literal names for scope blocks of *kind*, in file order."""
    seen: set[str] = set()
    result: list[str] = []
    for block in derive_scopes(doc):
        if block.kind == kind and block.name is not None and block.name not in seen:
            seen.add(block.name)
            result.append(block.name)
    return result


def interfaces(doc: Document) -> list[str]:
    """Return distinct interface names in file order."""
    return _unique_names(doc, ScopeKind.INTERFACE)


def profiles(doc: Document) -> list[str]:
    """Return distinct profile names in file order."""
    return _unique_names(doc, ScopeKind.PROFILE)


def ssids(doc: Document) -> list[str]:
    """Return distinct ssid names in file order."""
    return _unique_names(doc, ScopeKind.SSID)


def global_scope(doc: Document) -> ScopeView:
    """Return the global (leading) scope."""
    blocks = [b for b in derive_scopes(doc) if b.kind == ScopeKind.GLOBAL]
    if not blocks:
        # Edge case: the file starts with an interface directive
        blocks = [ScopeBlock(ScopeKind.GLOBAL, None, 0, 0)]
    return ScopeView(doc, blocks)


# ---------------------------------------------------------------------------
# Attach convenience methods to Document
# ---------------------------------------------------------------------------


def _doc_scopes(self: Document) -> list[ScopeView]:
    """Return every scope block as a :class:`ScopeView`."""
    return scopes(self)


def _doc_interface(self: Document, name: str) -> ScopeView:
    """Return a logical view combining all ``interface`` blocks for *name*."""
    return interface(self, name)


def _doc_interface_blocks(self: Document, name: str) -> list[ScopeView]:
    """Return each physical ``interface`` block matching *name*."""
    return interface_blocks(self, name)


def _doc_profile(self: Document, name: str) -> ScopeView:
    """Return a logical view combining all ``profile`` blocks for *name*."""
    return profile(self, name)


def _doc_profile_blocks(self: Document, name: str) -> list[ScopeView]:
    """Return each physical ``profile`` block matching *name*."""
    return profile_blocks(self, name)


def _doc_ssid(self: Document, name: str) -> ScopeView:
    """Return a logical view combining all ``ssid`` blocks for *name*."""
    return ssid(self, name)


def _doc_ssid_blocks(self: Document, name: str) -> list[ScopeView]:
    """Return each physical ``ssid`` block matching *name*."""
    return ssid_blocks(self, name)


def _doc_interfaces(self: Document) -> list[str]:
    """Return distinct interface names in file order."""
    return interfaces(self)


def _doc_profiles(self: Document) -> list[str]:
    """Return distinct profile names in file order."""
    return profiles(self)


def _doc_ssids(self: Document) -> list[str]:
    """Return distinct ssid names in file order."""
    return ssids(self)


def _doc_global_scope(self: Document) -> ScopeView:
    """Return the global (leading) scope."""
    return global_scope(self)


def _doc_find(self: Document, name: str) -> Directive | None:
    """Find the first directive matching *name* across the whole document."""
    for node in self.nodes:
        if isinstance(node, Directive) and node.name == name:
            return node
    return None


def _doc_find_all(self: Document, name: str) -> list[Directive]:
    """Find all directives matching *name* across the whole document."""
    return [n for n in self.nodes if isinstance(n, Directive) and n.name == name]


def _doc_render(self: Document) -> str:
    """Render the document back to its text representation."""
    from pydhcpcdparser.renderer import render

    return render(self)


# Monkey-patch Document with convenience methods
Document.scopes = _doc_scopes  # type: ignore[attr-defined]
Document.interface = _doc_interface  # type: ignore[attr-defined]
Document.interface_blocks = _doc_interface_blocks  # type: ignore[attr-defined]
Document.profile = _doc_profile  # type: ignore[attr-defined]
Document.profile_blocks = _doc_profile_blocks  # type: ignore[attr-defined]
Document.ssid = _doc_ssid  # type: ignore[attr-defined]
Document.ssid_blocks = _doc_ssid_blocks  # type: ignore[attr-defined]
Document.interfaces = _doc_interfaces  # type: ignore[attr-defined]
Document.profiles = _doc_profiles  # type: ignore[attr-defined]
Document.ssids = _doc_ssids  # type: ignore[attr-defined]
Document.global_scope = _doc_global_scope  # type: ignore[attr-defined]
Document.find = _doc_find  # type: ignore[attr-defined]
Document.find_all = _doc_find_all  # type: ignore[attr-defined]
Document.render = _doc_render  # type: ignore[attr-defined]
