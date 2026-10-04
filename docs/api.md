# API Reference

## Parsing

```python
from pydhcpcdparser import parse

doc = parse(text)               # lenient (default)
doc = parse(text, strict=True)  # raises DhcpcdParseError on malformed syntax
```

## Rendering

```python
from pydhcpcdparser import render

text = render(doc)
# or
text = doc.render()
```

For unmodified documents: `render(parse(text)) == text`.

## Document queries

```python
doc.find("hostname")          # first Directive with that name, or None
doc.find_all("option")        # all Directives with that name

doc.interfaces()              # ["eth0", "eth1", ...]
doc.profiles()                # ["static_eth0", ...]
doc.ssids()                   # ["Office WiFi", ...]
```

## Scope access

```python
eth0 = doc.interface("eth0")  # ScopeView (raises ScopeNotFoundError if missing)
prof = doc.profile("static_eth0")
wifi = doc.ssid("Office WiFi")
glob = doc.global_scope()

# Physical blocks (one per block, not merged)
blocks = doc.interface_blocks("eth0")
```

## ScopeView queries

```python
eth0.find("nogateway")              # first match or None
eth0.find_all("static")             # all matches
eth0.static("ip_address")           # last static ip_address=... value
eth0.static_all("routes")           # all static routes=... values
eth0.directives                     # all Directive nodes in scope
eth0.nodes                          # all nodes (including comments/blanks)
```

## Editing

```python
# Scope editing
eth0.set("nogateway")                              # set or append
eth0.set("metric", "200")                          # update existing or append
eth0.set_static("ip_address", "192.168.1.20/24")   # set static key=value
eth0.add_directive("nogateway")                     # always append
eth0.remove("nogateway")                            # remove first occurrence
eth0.remove_all("static")                           # remove all occurrences
eth0.remove_static("ip_address")                    # remove first static key=...
eth0.replace_first("option", "new_value")           # replace first
eth0.replace_all("option", "new_value")             # replace all
```

## Document editing

```python
doc.add_directive("hostname")
doc.add_directive("metric", "100")
doc.add_blank()
doc.add_comment(" a comment")

eth0 = doc.add_interface("eth0")
prof = doc.add_profile("static_eth0")
wifi = doc.add_ssid("Office WiFi")

eth0 = doc.ensure_interface("eth0")  # get or create
```

## File I/O

```python
doc = Document.from_path("/etc/dhcpcd.conf")
doc.write("/etc/dhcpcd.conf")
doc.write_atomic("/etc/dhcpcd.conf")  # safe: temp file + fsync + replace
```

## Validation

```python
from pydhcpcdparser import validate

diagnostics = validate(doc)
for d in diagnostics:
    print(d)  # e.g. "warning: line 5: Unknown dhcpcd directive "foobar""
```

Diagnostic codes: `missing-value`, `unknown-directive`, `duplicate-singleton`.

## Effective configuration

```python
eff = doc.effective_config(interface="eth0")
eff = doc.effective_config(interface="eth0", ssid="Office WiFi")
eff = doc.effective_config(profile="static_eth0")

eff.find("metric")
eff.static("ip_address")
eff.static_all("routes")
```

## AST nodes

| Node type | Fields |
|---|---|
| `Directive` | `name`, `value`, `leading_whitespace`, `separator`, `inline_comment` |
| `Comment` | `text`, `prefix` (`#` or `;`) |
| `BlankLine` | — |
| `InvalidLine` | `error` |

All nodes share: `source_span`, `raw`, `modified`, `newline`.
