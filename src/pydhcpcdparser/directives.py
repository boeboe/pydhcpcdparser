"""Registry of known dhcpcd directives and their argument requirements.

Seeded from upstream ``cf_options[]`` in ``src/if-options.c`` and the
man page ``dhcpcd.conf.5.in`` at commit ``5a91691c65f063551553116ca73f2163ad951c9c``.

Unknown directive names remain legal — the registry is advisory, used by
:func:`pydhcpcdparser.validation.validate` to emit diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydhcpcdparser.semantics import ScopeKind


class ArgumentRequirement(Enum):
    """Whether a directive requires, optionally takes, or forbids a value."""

    NONE = "none"
    REQUIRED = "required"
    OPTIONAL = "optional"


@dataclass(frozen=True)
class DirectiveSpec:
    """Metadata for a known dhcpcd directive."""

    name: str
    argument: ArgumentRequirement
    contexts: frozenset[ScopeKind] | None = None
    singleton: bool = False

    def __repr__(self) -> str:
        return f"DirectiveSpec({self.name!r}, {self.argument.value})"


# Shorthand constructors
_NONE = ArgumentRequirement.NONE
_REQ = ArgumentRequirement.REQUIRED
_OPT = ArgumentRequirement.OPTIONAL

_ALL_SCOPES: frozenset[ScopeKind] = frozenset(ScopeKind)
_IFACE_SCOPES: frozenset[ScopeKind] = frozenset(
    {
        ScopeKind.GLOBAL,
        ScopeKind.INTERFACE,
        ScopeKind.SSID,
        ScopeKind.PROFILE,
    }
)
_GLOBAL_ONLY: frozenset[ScopeKind] = frozenset({ScopeKind.GLOBAL})

# ---------------------------------------------------------------------------
# Registry — populated from upstream sources
# ---------------------------------------------------------------------------

_REGISTRY_LIST: list[DirectiveSpec] = [
    # Scope openers (conf-file only)
    DirectiveSpec("interface", _REQ, _ALL_SCOPES),
    DirectiveSpec("ssid", _REQ, _ALL_SCOPES),
    DirectiveSpec("profile", _REQ, _ALL_SCOPES),
    # Global-only
    DirectiveSpec("allowinterfaces", _REQ, _GLOBAL_ONLY),
    DirectiveSpec("denyinterfaces", _REQ, _GLOBAL_ONLY),
    DirectiveSpec("controlgroup", _REQ, _GLOBAL_ONLY),
    DirectiveSpec("readgroup", _REQ, _GLOBAL_ONLY),
    DirectiveSpec("dev", _REQ, _GLOBAL_ONLY),
    DirectiveSpec("logfile", _REQ, _GLOBAL_ONLY),
    DirectiveSpec("script", _REQ, _GLOBAL_ONLY),
    # Boolean flags (no argument)
    DirectiveSpec("anonymous", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("randomise_hwaddr", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("background", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("bootp", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("broadcast", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("clientid", _OPT, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("debug", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("dhcp", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("dhcp6", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("duid", _OPT, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("gateway", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("hostname", _OPT, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("hostname_short", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("inform6", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("ipv4", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("ipv6", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("ipv4only", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("ipv6only", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("ipv6ra_autoconf", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("ipv6ra_noautoconf", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("ipv6ra_fork", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("ipv6rs", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("lastlease", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("lastleaseextend", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("noalias", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("noarp", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("arp_persistdefence", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("noauthrequired", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("nodelay", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("nodev", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("nodhcp", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("nodhcp6", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("nogateway", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("noipv4", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("noipv4ll", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("noipv6", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("noipv6rs", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("nolink", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("nosyslog", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("noup", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("persistent", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("quiet", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("release", _NONE, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("xidhwaddr", _NONE, _IFACE_SCOPES, singleton=True),
    # Directives with required arguments
    DirectiveSpec("arping", _REQ, _IFACE_SCOPES),
    DirectiveSpec("authprotocol", _REQ, _IFACE_SCOPES),
    DirectiveSpec("authtoken", _REQ, _IFACE_SCOPES),
    DirectiveSpec("blacklist", _REQ, _IFACE_SCOPES),
    DirectiveSpec("whitelist", _REQ, _IFACE_SCOPES),
    DirectiveSpec("env", _REQ, _IFACE_SCOPES),
    DirectiveSpec("fallback", _REQ, _IFACE_SCOPES),
    DirectiveSpec("iaid", _REQ, _IFACE_SCOPES),
    DirectiveSpec("metric", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("mudurl", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("nohook", _REQ, _IFACE_SCOPES),
    DirectiveSpec("option", _REQ, _IFACE_SCOPES),
    DirectiveSpec("allow", _REQ, _IFACE_SCOPES),
    DirectiveSpec("nooption", _REQ, _IFACE_SCOPES),
    DirectiveSpec("require", _REQ, _IFACE_SCOPES),
    DirectiveSpec("reject", _REQ, _IFACE_SCOPES),
    DirectiveSpec("destination", _REQ, _IFACE_SCOPES),
    DirectiveSpec("static", _REQ, _IFACE_SCOPES),
    DirectiveSpec("userclass", _REQ, _IFACE_SCOPES),
    DirectiveSpec("msuserclass", _REQ, _IFACE_SCOPES),
    DirectiveSpec("vendor", _REQ, _IFACE_SCOPES),
    DirectiveSpec("vsio", _REQ, _IFACE_SCOPES),
    DirectiveSpec("vsio6", _REQ, _IFACE_SCOPES),
    DirectiveSpec("vendorclassid", _OPT, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("vendclass", _REQ, _IFACE_SCOPES),
    # Directives with optional arguments
    DirectiveSpec("inform", _OPT, _IFACE_SCOPES),
    DirectiveSpec("request", _OPT, _IFACE_SCOPES),
    DirectiveSpec("fqdn", _OPT, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("slaac", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("waitip", _OPT, _IFACE_SCOPES, singleton=True),
    # Time/numeric directives (required argument, singleton)
    DirectiveSpec("initial_interval", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("backoff_cutoff", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("backoff_jitter", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("fallback_time", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("ipv4ll_time", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("leasetime", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("link_rcvbuf", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("reboot", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("request_time", _REQ, _IFACE_SCOPES, singleton=True),
    DirectiveSpec("timeout", _REQ, _IFACE_SCOPES, singleton=True),
    # IA directives
    DirectiveSpec("ia_na", _OPT, _IFACE_SCOPES),
    DirectiveSpec("ia_ta", _OPT, _IFACE_SCOPES),
    DirectiveSpec("ia_pd", _OPT, _IFACE_SCOPES),
    # Custom option definition directives
    DirectiveSpec("define", _REQ, _IFACE_SCOPES),
    DirectiveSpec("definend", _REQ, _IFACE_SCOPES),
    DirectiveSpec("define6", _REQ, _IFACE_SCOPES),
    DirectiveSpec("vendopt", _REQ, _IFACE_SCOPES),
    DirectiveSpec("embed", _REQ, _IFACE_SCOPES),
    DirectiveSpec("encap", _REQ, _IFACE_SCOPES),
]

REGISTRY: dict[str, DirectiveSpec] = {spec.name: spec for spec in _REGISTRY_LIST}


def lookup(name: str) -> DirectiveSpec | None:
    """Look up a directive by name.  Returns ``None`` for unknown directives."""
    return REGISTRY.get(name)


def is_known(name: str) -> bool:
    """Return whether *name* is a known dhcpcd directive."""
    return name in REGISTRY
