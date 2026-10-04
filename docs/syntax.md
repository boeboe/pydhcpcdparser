# dhcpcd.conf syntax

This document describes the `dhcpcd.conf` syntax as understood by `pydhcpcdparser`, based on upstream `dhcpcd` behavior.

## Line types

Each physical line is one of:

- **Blank line** — whitespace-only or empty.
- **Comment** — first non-whitespace character is `#` or `;`.
- **Directive** — a configuration directive with an optional value.

## Directive structure

```
[leading-whitespace] name [separator value] [inline-comment] newline
```

- **Leading whitespace** — spaces and tabs; semantically ignored, preserved for round-trip.
- **Name** — the first non-whitespace token (e.g. `hostname`, `static`, `interface`).
- **Separator** — whitespace between name and value (one or more spaces/tabs).
- **Value** — the rest of the line until an unquoted `#` or end of line.
- **Inline comment** — `#` and everything after it, when not inside quotes or escaped.

## Quoting and escaping

- `"..."` protects `#` from being interpreted as a comment start.
- `\` escapes the following character, including `"` and `#`.
- There is no backslash line continuation.

Example:
```
env foo="hello # world" # real comment
```
Parses as: name=`env`, value=`foo="hello # world"`, inline comment=`# real comment`.

## Scope blocks

Three directives change the scope of subsequent lines:

- `interface <pattern>` — subsequent options apply to matching interfaces (fnmatch).
- `ssid <name>` — subsequent options apply to this wireless SSID (exact match).
- `profile <name>` — subsequent options apply to this profile (exact match).

There is no explicit block close and no return to global scope. A new scope-opening directive ends the previous block.

## Newlines

Both LF (`\n`) and CRLF (`\r\n`) are supported. The parser detects the dominant style and preserves each line's actual ending.

A missing final newline is preserved.
