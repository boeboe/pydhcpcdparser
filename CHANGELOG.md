# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added

- Initial release of `pydhcpcdparser`.
- Lossless round-trip parsing and rendering of `dhcpcd.conf` files:
    - Byte-for-byte preservation of comments, blank lines, indentation, unknown directives, duplicate entries, and quote styles.
    - LF, CRLF, and no-final-newline support.
- Flat ordered AST with `Document`, `Directive`, `Comment`, `BlankLine`, and `InvalidLine` node types.
- Lexer following upstream `get_line()` semantics from `src/common.c`:
    - `#` and `;` comment detection, quote handling, backslash escaping.
    - Inline comment extraction with proper quote awareness.
- Scope derivation following upstream `read_config()` from `src/if-options.c`:
    - `interface` (fnmatch pattern matching), `ssid` (exact match), `profile` (exact match).
    - Global scope, repeated interface blocks, scope views.
- Query API:
    - `find`, `find_all`, `static`, `static_all` on scopes and documents.
    - `interfaces()`, `profiles()`, `ssids()` listing.
- Minimal-diff editing:
    - `set`, `set_static`, `remove`, `remove_all`, `remove_static`, `replace_first`, `replace_all`.
    - Only modified nodes are rewritten; unmodified nodes preserve original raw text.
- Creation API for building configurations from scratch:
    - `add_directive`, `add_blank`, `add_comment`, `add_interface`, `add_profile`, `add_ssid`.
    - `ensure_interface`, `ensure_profile`, `ensure_ssid` get-or-create helpers.
- File I/O:
    - `Document.from_path()`, `write()`, `write_atomic()` (temp file + fsync + os.replace).
- Effective configuration resolver:
    - `effective_config(interface=, ssid=, profile=)` approximating upstream `read_config()` directive selection.
- Directive registry with ~90 known dhcpcd directives and argument requirements.
- Validation:
    - `validate()` returns diagnostics (`missing-value`, `unknown-directive`, `duplicate-singleton`) without modifying the document.
- Strict parsing mode (`strict=True`) for detecting unterminated quotes.
- Full type annotations with `py.typed` marker (PEP 561).
- Zero runtime dependencies; pure Python 3.9+.
