"""Validation for dhcpcd.conf documents.

Parsing and validation are separate.  ``parse()`` accepts as much content
as possible; ``validate()`` then returns diagnostics without modifying the
document.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydhcpcdparser.ast import Directive, Document, Node
from pydhcpcdparser.directives import ArgumentRequirement, lookup
from pydhcpcdparser.semantics import ScopeKind, derive_scopes


class Severity(Enum):
    """Diagnostic severity level."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Diagnostic:
    """A single validation finding."""

    severity: Severity
    code: str
    message: str
    node: Node | None = None

    def __str__(self) -> str:
        loc = ""
        if self.node and self.node.source_span:
            loc = f"line {self.node.source_span.line}: "
        return f"{self.severity.value}: {loc}{self.message}"


def validate(doc: Document) -> list[Diagnostic]:
    """Validate *doc* and return a list of diagnostics.

    Does **not** modify *doc*.
    """
    diagnostics: list[Diagnostic] = []
    blocks = derive_scopes(doc)

    # Per-scope analysis
    for block in blocks:
        start = block.start_index
        if block.kind != ScopeKind.GLOBAL:
            start += 1
        _validate_block(doc.nodes[start : block.end_index], block.kind, diagnostics)

    # Also validate scope openers themselves
    for block in blocks:
        if block.kind == ScopeKind.GLOBAL:
            continue
        if block.start_index < len(doc.nodes):
            opener = doc.nodes[block.start_index]
            if isinstance(opener, Directive):
                _validate_opener(opener, diagnostics)

    return diagnostics


def _validate_opener(directive: Directive, diagnostics: list[Diagnostic]) -> None:
    """Validate a scope-opening directive (interface/ssid/profile)."""
    spec = lookup(directive.name)
    if spec and spec.argument == ArgumentRequirement.REQUIRED and directive.value is None:
        diagnostics.append(
            Diagnostic(
                severity=Severity.ERROR,
                code="missing-value",
                message=f'"{directive.name}" requires a value',
                node=directive,
            )
        )


def _validate_block(
    nodes: list[Node],
    scope_kind: ScopeKind,
    diagnostics: list[Diagnostic],
) -> None:
    """Validate directives within a single scope block."""
    seen_singletons: dict[str, Directive] = {}

    for node in nodes:
        if not isinstance(node, Directive):
            continue

        spec = lookup(node.name)

        if spec is None:
            diagnostics.append(
                Diagnostic(
                    severity=Severity.WARNING,
                    code="unknown-directive",
                    message=f'Unknown dhcpcd directive "{node.name}"',
                    node=node,
                )
            )
            continue

        # Check required value
        if spec.argument == ArgumentRequirement.REQUIRED and node.value is None:
            diagnostics.append(
                Diagnostic(
                    severity=Severity.ERROR,
                    code="missing-value",
                    message=f'"{node.name}" requires a value',
                    node=node,
                )
            )

        # Check singleton duplicates
        if spec.singleton:
            if node.name in seen_singletons:
                diagnostics.append(
                    Diagnostic(
                        severity=Severity.WARNING,
                        code="duplicate-singleton",
                        message=(
                            f'Multiple values found for "{node.name}" '
                            f"where normally only one is expected"
                        ),
                        node=node,
                    )
                )
            else:
                seen_singletons[node.name] = node
