# pydhcpcdparser

[![CI](https://github.com/boeboe/pydhcpcdparser/actions/workflows/ci.yml/badge.svg)](https://github.com/boeboe/pydhcpcdparser/actions/workflows/ci.yml)
[![PyPI release workflow](https://github.com/boeboe/pydhcpcdparser/actions/workflows/release.yml/badge.svg)](https://github.com/boeboe/pydhcpcdparser/actions/workflows/release.yml)
[![Coverage](https://codecov.io/gh/boeboe/pydhcpcdparser/graph/badge.svg)](https://codecov.io/gh/boeboe/pydhcpcdparser)
[![PyPI version](https://img.shields.io/pypi/v/pydhcpcdparser?logo=pypi&logoColor=white)](https://pypi.org/project/pydhcpcdparser/)
[![Python versions](https://img.shields.io/pypi/pyversions/pydhcpcdparser?logo=python&logoColor=white)](https://pypi.org/project/pydhcpcdparser/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Parse, inspect, edit, validate, and render `dhcpcd.conf` files with **lossless round-tripping**.

`pydhcpcdparser` is a pure-Python library. It does **not** configure network interfaces or invoke `dhcpcd`.

## Table of Contents

- [pydhcpcdparser](#pydhcpcdparser)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Installation](#installation)
  - [Quick Start](#quick-start)
    - [Parse and Inspect](#parse-and-inspect)
    - [Create From Scratch](#create-from-scratch)
  - [Major Functionality Blocks](#major-functionality-blocks)
    - [Parsing and Rendering](#parsing-and-rendering)
    - [Scope Access](#scope-access)
    - [Query API](#query-api)
    - [Editor API](#editor-api)
    - [File I/O](#file-io)
    - [Validation](#validation)
    - [Effective Configuration](#effective-configuration)
  - [Error Handling](#error-handling)
  - [Examples](#examples)
  - [API Reference](#api-reference)
  - [Development](#development)
  - [Release](#release)
  - [Upstream Reference](#upstream-reference)
  - [License](#license)

## Features

- **Lossless round-trip** — comments, blank lines, indentation, unknown directives, and duplicate entries are preserved byte-for-byte
- **Minimal-diff editing** — only the changed directive is rewritten; everything else stays identical
- **Scope-aware queries** — `interface`, `ssid`, and `profile` blocks follow upstream `dhcpcd` semantics
- **Unknown-directive preservation** — forward-compatible with future `dhcpcd` options
- **Separate validation** — parsing never fails on unknown content; validation reports diagnostics
- **Effective configuration** — compute which directives apply for a given interface/ssid/profile
- **Zero runtime dependencies** — pure Python, works on 3.9+
- **Fully typed** — ships `py.typed` with complete type annotations

## Installation

```bash
pip install pydhcpcdparser
```

## Quick Start

### Parse and Inspect

```python
from pydhcpcdparser import parse

source = open("/etc/dhcpcd.conf").read()
doc = parse(source)

# Round-trip: unmodified render matches the original byte-for-byte
assert doc.render() == source

# Inspect interfaces
for name in doc.interfaces():
    print(name)

eth0 = doc.interface("eth0")
print(eth0.static("ip_address"))   # "192.168.1.17/32"
print(eth0.static("routers"))      # "192.168.1.1"

# Edit with minimal diff — only the changed line is rewritten
eth0.set_static("ip_address", "192.168.1.20/24")
doc.write_atomic("/etc/dhcpcd.conf")
```

### Create From Scratch

```python
from pydhcpcdparser import Document

doc = Document()
doc.add_directive("hostname")
doc.add_directive("clientid")
doc.add_blank()

eth0 = doc.add_interface("eth0")
eth0.add_directive("nogateway")
eth0.set_static("ip_address", "192.168.1.17/32")
eth0.set_static("routers", "192.168.1.1")
eth0.set_static("domain_name_servers", "8.8.8.8 8.8.4.4")

print(doc.render())
```

## Major Functionality Blocks

- Parsing with lossless AST and scope derivation:
    - Lexer following upstream `get_line()` semantics (comment detection, quoting, escaping).
    - Flat ordered AST with scope blocks derived from `interface`, `ssid`, `profile` directives.
- Query and inspection:
    - Document-wide and scope-scoped `find`, `find_all`, `static`, `static_all` queries.
    - Interface/profile/ssid listing, physical blocks vs logical views.
- Minimal-diff editing:
    - `set`, `remove`, `replace_first`, `replace_all`, `set_static`, `remove_static`.
    - Only modified nodes are rewritten; unmodified nodes preserve original raw text.
- Validation and effective configuration:
    - Directive registry with ~90 known directives and argument requirements.
    - `validate()` returns diagnostics without modifying the document.
    - `effective_config()` approximates upstream `read_config()` directive selection.

### Parsing and Rendering

| Function | Description |
|----------|-------------|
| `parse(text, strict=False)` | Parse text into a `Document` |
| `render(doc)` | Render a `Document` back to text |
| `doc.render()` | Method form of `render(doc)` |

### Scope Access

| Method | Description |
|--------|-------------|
| `doc.interface(name)` | Logical view combining all `interface` blocks for `name` |
| `doc.interface_blocks(name)` | Each physical `interface` block separately |
| `doc.profile(name)` | Logical view combining all `profile` blocks for `name` |
| `doc.profile_blocks(name)` | Each physical `profile` block separately |
| `doc.ssid(name)` | Logical view combining all `ssid` blocks for `name` |
| `doc.ssid_blocks(name)` | Each physical `ssid` block separately |
| `doc.global_scope()` | The global (leading) scope |
| `doc.scopes()` | Every scope block as a `ScopeView` |

### Query API

| Method | Description |
|--------|-------------|
| `doc.find(name)` | First directive matching `name`, or `None` |
| `doc.find_all(name)` | All directives matching `name` |
| `doc.interfaces()` | Distinct interface names in file order |
| `doc.profiles()` | Distinct profile names in file order |
| `doc.ssids()` | Distinct ssid names in file order |
| `scope.find(name)` | First directive in scope, or `None` |
| `scope.find_all(name)` | All directives in scope |
| `scope.static(key)` | Last `static key=...` value, or `None` |
| `scope.static_all(key)` | All `static key=...` values |

### Editor API

| Method | Description |
|--------|-------------|
| `scope.set(name, value=None)` | Set or append a directive |
| `scope.set_static(key, value)` | Set or append `static key=value` |
| `scope.add_directive(name, value=None)` | Always append a new directive |
| `scope.remove(name)` | Remove first occurrence |
| `scope.remove_all(name)` | Remove all occurrences |
| `scope.remove_static(key)` | Remove first `static key=...` |
| `scope.remove_all_static(key)` | Remove all `static key=...` |
| `scope.replace_first(name, value)` | Replace first match |
| `scope.replace_all(name, value)` | Replace all matches |
| `doc.add_directive(name, value=None)` | Append directive to document |
| `doc.add_blank()` | Append blank line |
| `doc.add_comment(text)` | Append comment line |
| `doc.add_interface(name)` | Append `interface` block |
| `doc.add_profile(name)` | Append `profile` block |
| `doc.add_ssid(name)` | Append `ssid` block |
| `doc.ensure_interface(name)` | Get or create interface scope |
| `doc.ensure_profile(name)` | Get or create profile scope |
| `doc.ensure_ssid(name)` | Get or create ssid scope |

### File I/O

| Method | Description |
|--------|-------------|
| `Document.from_path(path)` | Parse a document from a file |
| `doc.write(path)` | Write the rendered document |
| `doc.write_atomic(path)` | Atomic write (temp file + fsync + replace) |

### Validation

```python
from pydhcpcdparser import parse, validate

doc = parse("interface\nfuture_thing value\nnogateway\nnogateway\n")
for d in validate(doc):
    print(d)
# error: line 1: "interface" requires a value
# warning: line 2: Unknown dhcpcd directive "future_thing"
# warning: line 4: Multiple values found for "nogateway" ...
```

Diagnostic codes: `missing-value`, `unknown-directive`, `duplicate-singleton`.

### Effective Configuration

```python
eff = doc.effective_config(interface="eth0")
eff = doc.effective_config(interface="eth0", ssid="Office WiFi")
eff = doc.effective_config(profile="static_eth0")

eff.find("metric")
eff.static("ip_address")
eff.static_all("routes")
```

## Error Handling

```python
from pydhcpcdparser import (
    parse,
    DhcpcdParseError,
    ScopeNotFoundError,
)

# Strict parsing
try:
    doc = parse('env val="unterminated', strict=True)
except DhcpcdParseError:
    print("Malformed syntax")

# Missing scope
try:
    eth0 = doc.interface("eth99")
except ScopeNotFoundError:
    print("Interface not found")
```

All library errors inherit from `DhcpcdParserError`:

- `DhcpcdParseError` — malformed syntax in strict mode
- `DhcpcdValidationError` — validation failures
- `ScopeNotFoundError` — requested scope does not exist
- `AmbiguousScopeError` — ambiguous scope reference

## Examples

See [EXAMPLES.md](EXAMPLES.md) for:

- parsing, inspection, and round-trip examples
- minimal-diff editing workflows
- creating configurations from scratch
- profile fallback patterns
- validation and effective configuration usage

## API Reference

For the complete public surface inventory, see [API.md](API.md):

- all public functions
- all public classes and methods
- all AST node types
- all error classes

## Development

```bash
# Show available targets
make help

# Create local virtual environment and install dependencies
make venv

# Run tests in Docker
make test

# Lint and type-check in Docker
make lint
make typecheck

# Run all checks (lint, typecheck, docs, security, tests)
make check

# Format code
make format

# Remove local virtual environment
make venv-clean
```

## Release

GitHub Actions workflow in [.github/workflows/release.yml](.github/workflows/release.yml)
handles package publishing via PyPI trusted publisher.

One-time setup:

- Configure a Trusted Publisher in PyPI for
    [.github/workflows/release.yml](.github/workflows/release.yml).

Release flow:

```bash
# Tag a release (must match version in pyproject.toml)
git tag v0.1.0
git push origin v0.1.0
```

The release workflow validates that the tag version matches the package version in
[pyproject.toml](pyproject.toml), builds distributions, creates a GitHub Release
with auto-generated notes, and publishes to PyPI.

## Upstream Reference

Parser behavior is verified against [NetworkConfiguration/dhcpcd](https://github.com/NetworkConfiguration/dhcpcd) at commit `5a91691c65f063551553116ca73f2163ad951c9c`.

See [docs/upstream-compatibility.md](docs/upstream-compatibility.md) for detailed behavioral notes.

## License

MIT License - see [LICENSE](LICENSE) for details.
