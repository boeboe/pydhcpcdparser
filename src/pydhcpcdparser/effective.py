"""Effective configuration resolver.

Approximates the behavior of upstream ``read_config()`` in
``src/if-options.c`` to determine which directives would actually be
applied for a given interface/ssid/profile combination.

Limitations documented in ``docs/upstream-compatibility.md``:
- Does not emulate per-option override or empty-``static`` clearing.
- Does not inject embedded dhcpcd defaults.
- Does not handle ``arping``→profile auto-selection at runtime.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field

from pydhcpcdparser.ast import Directive, Document
from pydhcpcdparser.exceptions import ScopeNotFoundError


@dataclass
class EffectiveConfig:
    """Effective directives for a given filter combination.

    Contains the ordered directives that ``read_config()`` would pass to
    ``parse_config_line()``.
    """

    directives: list[Directive] = field(default_factory=list)

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
        """Return the value of the last ``static key=...`` assignment, or ``None``."""
        prefix = f"{key}="
        result: str | None = None
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


def effective_config(
    doc: Document,
    *,
    interface: str | None = None,
    ssid: str | None = None,
    profile: str | None = None,
) -> EffectiveConfig:
    """Compute the effective configuration for a filter combination.

    Mirrors the skip/new_block/had_block logic of upstream ``read_config()``:

    - ``interface``, ``ssid``, and ``profile`` lines update *skip* state
      and are **not** included in the result.
    - With all filters ``None``, only leading global directives apply
      (upstream skips every block when ``ifname`` is ``NULL``).
    - ``interface`` matching uses ``fnmatch`` (the file text is the pattern).
    - ``ssid`` and ``profile`` use exact string comparison.
    - When *profile* is requested but never matched, raises
      :exc:`ScopeNotFoundError` (upstream returns ``ENOENT``).
    - When *profile* is requested and not yet entered, ``arping`` lines
      are skipped (matching the upstream guard).
    """
    result: list[Directive] = []
    skip = 0
    have_profile = False
    new_block = False

    for node in doc.nodes:
        if not isinstance(node, Directive):
            continue

        name = node.name
        value = node.value

        # Apply new_block state
        if skip == 0 and new_block:
            new_block = False

        # Scope openers
        if name == "interface":
            new_block = True
            if value is None:
                skip = 1
                continue
            skip = 0 if interface is not None and fnmatch.fnmatchcase(interface, value) else 1
            if interface is not None:
                continue
            # When ifname is None (global-only), we still skip the block
            # but upstream collects interface names.  We skip content.
            continue

        if name == "ssid":
            new_block = True
            skip = 0 if ssid is not None and value is not None and value == ssid else 1
            continue

        if name == "profile":
            new_block = True
            if profile is not None and value is not None and value == profile:
                skip = 0
                have_profile = True
            else:
                skip = 1
            continue

        # Skip arping when a profile is requested but we haven't entered it yet
        if profile is not None and not have_profile and name == "arping":
            continue

        if skip:
            continue

        result.append(node)

    if profile is not None and not have_profile:
        raise ScopeNotFoundError(f"Profile {profile!r} not found in configuration")

    return EffectiveConfig(directives=result)


# ---------------------------------------------------------------------------
# Attach to Document
# ---------------------------------------------------------------------------


def _doc_effective_config(
    self: Document,
    *,
    interface: str | None = None,
    ssid: str | None = None,
    profile: str | None = None,
) -> EffectiveConfig:
    """Compute the effective configuration for the document."""
    return effective_config(self, interface=interface, ssid=ssid, profile=profile)


Document.effective_config = _doc_effective_config  # type: ignore[attr-defined]
