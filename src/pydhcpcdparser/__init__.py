"""pydhcpcdparser — parse, inspect, edit, validate, and render dhcpcd.conf files."""

from __future__ import annotations

import pydhcpcdparser.editor as _editor  # noqa: F401 — registers Document/ScopeView methods
import pydhcpcdparser.effective as _effective  # noqa: F401 — registers Document.effective_config
from pydhcpcdparser.ast import BlankLine, Comment, Directive, Document, InvalidLine, Node
from pydhcpcdparser.exceptions import (
    AmbiguousScopeError,
    DhcpcdParseError,
    DhcpcdParserError,
    DhcpcdValidationError,
    ScopeNotFoundError,
)
from pydhcpcdparser.parser import parse
from pydhcpcdparser.renderer import render
from pydhcpcdparser.semantics import (
    ScopeKind,
    ScopeView,
)
from pydhcpcdparser.validation import Diagnostic, Severity, validate

__version__ = "0.1.0"

__all__ = [
    "AmbiguousScopeError",
    "BlankLine",
    "Comment",
    "DhcpcdParseError",
    "DhcpcdParserError",
    "DhcpcdValidationError",
    "Diagnostic",
    "Directive",
    "Document",
    "InvalidLine",
    "Node",
    "ScopeKind",
    "ScopeNotFoundError",
    "ScopeView",
    "Severity",
    "parse",
    "render",
    "validate",
]
