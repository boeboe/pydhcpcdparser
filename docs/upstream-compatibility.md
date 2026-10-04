# Upstream compatibility

## Reference project

- Repository: https://github.com/NetworkConfiguration/dhcpcd
- Verified against commit: `5a91691c65f063551553116ca73f2163ad951c9c`

## Primary sources consulted

| File | Purpose |
|---|---|
| `src/dhcpcd.conf.5.in` | Man page defining public configuration syntax |
| `src/common.c` → `get_line()` | Lexical behavior: comment detection, quoting, escaping |
| `src/if-options.c` → `read_config()` | Scope semantics: interface/ssid/profile block handling |
| `src/if-options.c` → `parse_config_line()` | Per-directive parsing |
| `src/if-options.c` → `cf_options[]` | Known option list with argument requirements |

## Behavior replicated

- Leading whitespace stripping (semantically; preserved in raw text).
- `#` comment detection with quote and backslash escaping.
- `;` as a leading comment character.
- `interface` matching via `fnmatch` (the file text is the pattern).
- `ssid` and `profile` matching via exact string comparison.
- Scope blocks: `interface`/`ssid`/`profile` open a new block; no return to global.
- `arping` suppression when a profile is requested but not yet entered.
- Profile not found → error (upstream returns `ENOENT`).

## Intentional differences from upstream

| Upstream behavior | Library behavior | Reason |
|---|---|---|
| `get_line()` strips inline comments | Library preserves inline comments in `raw` and `inline_comment` | Lossless round-trip requirement |
| `get_line()` strips trailing whitespace from values | Library preserves trailing whitespace in `raw`; semantic `value` is trimmed | Lossless round-trip |
| `get_line()` skips blank/comment lines | Library creates `BlankLine` and `Comment` nodes | Lossless round-trip |
| Embedded dhcpcd defaults applied | Not applied | Library parses files, not runtime state |
| Per-option override and empty-`static` clearing | Not emulated in `effective_config` v1 | Complexity deferred |
| `arping` → profile auto-selection at runtime | Not emulated | Runtime behavior, not file parsing |

## Updating

When updating the parser for a new upstream version:

1. Fetch the new `src/dhcpcd.conf.5.in` and diff against the vendored copy.
2. Review `src/common.c` → `get_line()` for lexer changes.
3. Review `src/if-options.c` → `read_config()` for scope changes.
4. Update the directive registry in `directives.py`.
5. Add test fixtures for any new syntax.
6. Update the commit hash in this document.
