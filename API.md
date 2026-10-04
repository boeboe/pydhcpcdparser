# API Reference

This document is the canonical inventory of the public pydhcpcdparser surface:

- public functions
- public classes
- public methods
- public errors

For usage examples, see [EXAMPLES.md](EXAMPLES.md).

## Table of Contents

- [Public Package Exports](#public-package-exports)
- [Core Functions](#core-functions)
  - [parse()](#parse)
  - [render()](#render)
  - [validate()](#validate)
- [Document](#document)
  - [Construction](#construction)
  - [Scope Access](#scope-access)
  - [Query Methods](#query-methods)
  - [Listing Methods](#listing-methods)
  - [Editing Methods](#editing-methods)
  - [Creation Methods](#creation-methods)
  - [Get-or-Create Methods](#get-or-create-methods)
  - [File I/O](#file-io)
  - [Rendering](#rendering)
  - [Effective Configuration](#effective-configuration)
- [ScopeView](#scopeview)
  - [Properties](#scopeview-properties)
  - [Query Methods](#scopeview-query-methods)
  - [Static Assignment Helpers](#static-assignment-helpers)
  - [Editing Methods](#scopeview-editing-methods)
- [EffectiveConfig](#effectiveconfig)
- [AST Node Classes](#ast-node-classes)
  - [Node (base)](#node-base)
  - [Directive](#directive)
  - [Comment](#comment)
  - [BlankLine](#blankline)
  - [InvalidLine](#invalidline)
  - [SourceSpan](#sourcespan)
- [Semantic Classes](#semantic-classes)
  - [ScopeKind](#scopekind)
  - [ScopeBlock](#scopeblock)
- [Validation Classes](#validation-classes)
  - [Diagnostic](#diagnostic)
  - [Severity](#severity)
- [Directive Registry](#directive-registry)
  - [DirectiveSpec](#directivespec)
  - [ArgumentRequirement](#argumentrequirement)
  - [Registry Functions](#registry-functions)
- [Error Classes](#error-classes)

## Public Package Exports

From `pydhcpcdparser`:

- `parse`
- `render`
- `validate`
- `Document`
- `Node`
- `Directive`
- `Comment`
- `BlankLine`
- `InvalidLine`
- `ScopeKind`
- `ScopeView`
- `Diagnostic`
- `Severity`
- `DhcpcdParserError`
- `DhcpcdParseError`
- `DhcpcdValidationError`
- `ScopeNotFoundError`
- `AmbiguousScopeError`
- `__version__`

## Core Functions

### parse()

```python
parse(text: str, *, strict: bool = False) -> Document
```

Parse `text` into a `Document`. With `strict=False` (default) the parser accepts as much content as possible. Strict mode raises `DhcpcdParseError` on clearly malformed syntax such as unterminated quotes.

### render()

```python
render(doc: Document) -> str
```

Render a `Document` back to text. For an unmodified document: `render(parse(text)) == text`.

### validate()

```python
validate(doc: Document) -> list[Diagnostic]
```

Validate a `Document` and return a list of diagnostics. Does **not** modify the document.

Diagnostic codes: `missing-value`, `unknown-directive`, `duplicate-singleton`.

## Document

An ordered sequence of AST nodes representing a `dhcpcd.conf` file.

### Construction

- `Document(nodes=[], newline="\n")`
- `Document.from_path(path)` — parse a document from a file path

### Scope Access

- `scopes()` — return every scope block as a `ScopeView`
- `global_scope()` — return the global (leading) scope
- `interface(name)` — return a logical view combining all `interface` blocks for `name` (raises `ScopeNotFoundError` if missing)
- `interface_blocks(name)` — return each physical `interface` block matching `name`
- `profile(name)` — return a logical view combining all `profile` blocks for `name` (raises `ScopeNotFoundError` if missing)
- `profile_blocks(name)` — return each physical `profile` block matching `name`
- `ssid(name)` — return a logical view combining all `ssid` blocks for `name` (raises `ScopeNotFoundError` if missing)
- `ssid_blocks(name)` — return each physical `ssid` block matching `name`

### Query Methods

- `find(name)` — return the first `Directive` matching `name` across the whole document, or `None`
- `find_all(name)` — return all `Directive` nodes matching `name` across the whole document

### Listing Methods

- `interfaces()` — return distinct interface names in file order
- `profiles()` — return distinct profile names in file order
- `ssids()` — return distinct ssid names in file order

### Editing Methods

- `append(node)` — append a node to the end of the document
- `insert(index, node)` — insert a node at a given index
- `remove(node)` — remove a node from the document

### Creation Methods

- `add_directive(name, value=None)` — append a new directive
- `add_blank()` — append a blank line
- `add_comment(text, *, prefix="#")` — append a comment line
- `add_interface(name)` — append a new `interface` block and return its `ScopeView`
- `add_profile(name)` — append a new `profile` block and return its `ScopeView`
- `add_ssid(name)` — append a new `ssid` block and return its `ScopeView`

### Get-or-Create Methods

- `ensure_interface(name)` — return the interface scope for `name`, creating one if it doesn't exist
- `ensure_profile(name)` — return the profile scope for `name`, creating one if it doesn't exist
- `ensure_ssid(name)` — return the ssid scope for `name`, creating one if it doesn't exist

### File I/O

- `write(path)` — write the rendered document to `path`
- `write_atomic(path)` — atomically write using a temporary file, `fsync`, and `os.replace`; preserves existing file permissions

### Rendering

- `render()` — render the document back to its text representation

### Effective Configuration

- `effective_config(*, interface=None, ssid=None, profile=None)` — compute the effective configuration for a filter combination, returning an `EffectiveConfig`

## ScopeView

A read-only view over one or more physical scope blocks. Provides query and editing helpers.

### ScopeView Properties

- `blocks` — the physical `ScopeBlock` instances backing this view
- `kind` — the scope kind (`ScopeKind`)
- `name` — the scope name, or `None` for the global scope
- `directives` — all `Directive` nodes inside the scope (excluding the opener)
- `nodes` — all nodes inside the scope (including comments/blanks, excluding the opener)

### ScopeView Query Methods

- `find(name)` — return the first directive matching `name`, or `None`
- `find_all(name)` — return every directive matching `name`

### Static Assignment Helpers

- `static(key)` — return the value of the last `static key=...` assignment, or `None`
- `static_all(key)` — return every `static key=...` value
- `static_assignment(directive)` — split a `static` directive's value into `(key, value)`

### ScopeView Editing Methods

- `set(name, value=None)` — set or append a directive
- `set_static(key, value)` — set or append a `static key=value` directive
- `add_directive(name, value=None)` — always append a new directive
- `remove(name)` — remove the first directive matching `name` (returns `bool`)
- `remove_all(name)` — remove all directives matching `name` (returns count)
- `remove_static(key)` — remove the first `static key=...` (returns `bool`)
- `remove_all_static(key)` — remove all `static key=...` (returns count)
- `replace_first(name, value)` — replace the value of the first directive matching `name`
- `replace_all(name, value)` — replace the value of every directive matching `name`

## EffectiveConfig

The ordered directives that upstream `read_config()` would pass to `parse_config_line()` for a given filter combination.

- `find(name)` — return the first directive matching `name`, or `None`
- `find_all(name)` — return every directive matching `name`
- `static(key)` — return the value of the last `static key=...` assignment, or `None`
- `static_all(key)` — return every `static key=...` value
- `directives` — the ordered list of effective `Directive` nodes

## AST Node Classes

### Node (base)

Base class for all AST nodes.

| Field | Type | Description |
|---|---|---|
| `source_span` | `SourceSpan \| None` | Source location information |
| `raw` | `str` | Original raw text (empty for newly created nodes) |
| `modified` | `bool` | Whether the node has been modified |
| `newline` | `str` | The newline sequence for this node |

### Directive

A configuration directive with an optional value.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Directive name |
| `value` | `str \| None` | Directive value |
| `leading_whitespace` | `str` | Whitespace before the directive name |
| `separator` | `str` | Whitespace between name and value |
| `inline_comment` | `str \| None` | Inline comment (including the `#` prefix) |

### Comment

A comment line (`#` or `;` prefix).

| Field | Type | Description |
|---|---|---|
| `text` | `str` | Comment text after the prefix character |
| `prefix` | `str` | Comment prefix: `#` or `;` |

### BlankLine

A blank or whitespace-only line. No additional fields.

### InvalidLine

A line that could not be parsed (only emitted in strict mode diagnostics).

| Field | Type | Description |
|---|---|---|
| `error` | `str` | Error description |

### SourceSpan

Source location information for a parsed node.

| Field | Type | Description |
|---|---|---|
| `line` | `int` | 1-based line number |
| `column` | `int` | 0-based column |
| `start` | `int` | Start offset in the source text |
| `end` | `int` | End offset in the source text |

## Semantic Classes

### ScopeKind

Enum of scope block types:

- `ScopeKind.GLOBAL`
- `ScopeKind.INTERFACE`
- `ScopeKind.PROFILE`
- `ScopeKind.SSID`

### ScopeBlock

A contiguous physical block of nodes sharing a scope (frozen dataclass).

| Field | Type | Description |
|---|---|---|
| `kind` | `ScopeKind` | The type of scope |
| `name` | `str \| None` | The scope name |
| `start_index` | `int` | Start index in the document's node list |
| `end_index` | `int` | End index (exclusive) |

## Validation Classes

### Diagnostic

A single validation finding (frozen dataclass).

| Field | Type | Description |
|---|---|---|
| `severity` | `Severity` | `INFO`, `WARNING`, or `ERROR` |
| `code` | `str` | Machine-readable diagnostic code |
| `message` | `str` | Human-readable description |
| `node` | `Node \| None` | The node that triggered the diagnostic |

### Severity

Enum of diagnostic severity levels:

- `Severity.INFO`
- `Severity.WARNING`
- `Severity.ERROR`

## Directive Registry

From `pydhcpcdparser.directives`:

### DirectiveSpec

Metadata for a known dhcpcd directive (frozen dataclass).

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Directive name |
| `argument` | `ArgumentRequirement` | Whether a value is required, optional, or forbidden |
| `contexts` | `frozenset[ScopeKind] \| None` | Valid scope contexts |
| `singleton` | `bool` | Whether the directive should appear at most once per scope |

### ArgumentRequirement

Enum:

- `ArgumentRequirement.NONE` — no value allowed
- `ArgumentRequirement.REQUIRED` — value required
- `ArgumentRequirement.OPTIONAL` — value optional

### Registry Functions

- `lookup(name)` — look up a directive by name, returns `DirectiveSpec | None`
- `is_known(name)` — return whether `name` is a known dhcpcd directive

The registry contains ~90 directives seeded from upstream `cf_options[]` and the `dhcpcd.conf.5.in` man page.

## Error Classes

All library errors inherit from `DhcpcdParserError`.

- `DhcpcdParserError` — base exception for all pydhcpcdparser errors
- `DhcpcdParseError` — raised when the parser encounters malformed syntax in strict mode
- `DhcpcdValidationError` — raised for validation failures
- `ScopeNotFoundError` — raised when a requested interface/profile/ssid scope does not exist
- `AmbiguousScopeError` — raised when a scope reference is ambiguous
