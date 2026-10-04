# Architecture

`pydhcpcdparser` has three layers, each with a single responsibility:

```
                      ┌─────────────────────┐
                      │ Application model   │
                      │ NOT part of library │
                      └──────────┬──────────┘
                                 │ adapter
                                 ▼
┌────────────────────────────────────────────────────┐
│                pydhcpcdparser                      │
│                                                    │
│  semantic/query layer (semantics.py, effective.py) │
│          ↓                                         │
│  lossless AST / document model (ast.py)           │
│          ↓                                         │
│  lexer/parser + renderer (lexer.py, parser.py,    │
│                           renderer.py)             │
└────────────────────────────────────────────────────┘
                                 │
                                 ▼
                         dhcpcd.conf
```

## Modules

| Module | Purpose |
|---|---|
| `ast.py` | Dataclass nodes: `Document`, `Directive`, `Comment`, `BlankLine`, `InvalidLine` |
| `lexer.py` | Single-line lexer that classifies raw lines into AST nodes |
| `parser.py` | `parse()` — splits text into lines, detects newline style, produces a `Document` |
| `renderer.py` | `render()` — reconstructs text from nodes; unmodified nodes emit `raw` verbatim |
| `semantics.py` | Scope derivation (`interface`, `ssid`, `profile`) and query helpers (`find`, `static`) |
| `editor.py` | Mutation operations (`set`, `remove`, `set_static`) on documents and scopes |
| `effective.py` | `effective_config()` — approximates upstream `read_config()` directive selection |
| `directives.py` | Registry of known dhcpcd directives with argument requirements |
| `validation.py` | `validate()` — returns diagnostics without modifying the document |
| `exceptions.py` | Library-specific exception classes |

## Design principles

1. **Lossless round-trip** — `render(parse(text)) == text`, byte-for-byte.
2. **Flat AST** — the node list is ordered, not nested. Scopes are derived views.
3. **Minimal-diff editing** — only the modified node is rewritten; unmodified nodes keep their original `raw` text.
4. **Forward-compatible** — unknown directives parse successfully and round-trip unchanged.
5. **Separate parsing from validation** — `parse()` accepts everything; `validate()` reports problems.
