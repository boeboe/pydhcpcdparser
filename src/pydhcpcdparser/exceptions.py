"""Library-specific exceptions for pydhcpcdparser."""

from __future__ import annotations


class DhcpcdParserError(Exception):
    """Base exception for all pydhcpcdparser errors."""


class DhcpcdParseError(DhcpcdParserError):
    """Raised when the parser encounters malformed syntax in strict mode."""


class DhcpcdValidationError(DhcpcdParserError):
    """Raised for validation failures."""


class ScopeNotFoundError(DhcpcdParserError):
    """Raised when a requested interface/profile/ssid scope does not exist."""


class AmbiguousScopeError(DhcpcdParserError):
    """Raised when a scope reference is ambiguous."""
