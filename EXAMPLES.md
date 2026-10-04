# Examples

Usage examples for pydhcpcdparser, organized by feature area.

For the complete public SDK surface (methods, classes, errors), see [API.md](API.md).

## Table of Contents

- [Prerequisites](#prerequisites)
- [Parsing](#parsing)
  - [Parse from string](#parse-from-string)
  - [Parse from file](#parse-from-file)
  - [Strict mode](#strict-mode)
- [Round-Trip Guarantee](#round-trip-guarantee)
- [Inspecting](#inspecting)
  - [List interfaces, profiles, ssids](#list-interfaces-profiles-ssids)
  - [Access scope directives](#access-scope-directives)
  - [Query static assignments](#query-static-assignments)
  - [Document-wide queries](#document-wide-queries)
  - [Physical blocks vs logical views](#physical-blocks-vs-logical-views)
- [Editing](#editing)
  - [Minimal-diff editing](#minimal-diff-editing)
  - [Set and remove directives](#set-and-remove-directives)
  - [Replace directives](#replace-directives)
  - [Static assignment editing](#static-assignment-editing)
- [Creating Configurations](#creating-configurations)
  - [Build from scratch](#build-from-scratch)
  - [Profile fallback pattern](#profile-fallback-pattern)
  - [Ensure (get-or-create)](#ensure-get-or-create)
- [File I/O](#file-io)
  - [Read and write](#read-and-write)
  - [Atomic write](#atomic-write)
- [Validation](#validation)
- [Effective Configuration](#effective-configuration)
- [Unknown Directives](#unknown-directives)
- [Raw AST Access](#raw-ast-access)
- [Newline Handling](#newline-handling)

## Prerequisites

```bash
pip install pydhcpcdparser
```

No runtime dependencies required.

## Parsing

### Parse from string

```python
from pydhcpcdparser import parse

text = """\
hostname
clientid

interface eth0
static ip_address=192.168.1.17/32
static routers=192.168.1.1
"""

doc = parse(text)
print(len(doc.nodes))  # 6
```

### Parse from file

```python
from pydhcpcdparser import Document

doc = Document.from_path("/etc/dhcpcd.conf")
print(doc.interfaces())
```

### Strict mode

```python
from pydhcpcdparser import parse, DhcpcdParseError

try:
    doc = parse('env val="unterminated', strict=True)
except DhcpcdParseError as e:
    print(e)  # Unterminated quote at line 1
```

## Round-Trip Guarantee

For any unmodified document, rendering produces the exact original text byte-for-byte:

```python
from pydhcpcdparser import parse, render

source = open("/etc/dhcpcd.conf").read()
doc = parse(source)

assert render(doc) == source       # functional form
assert doc.render() == source      # method form
```

This includes preservation of comments, blank lines, indentation, unknown directives, inline comments, quote styles, LF vs CRLF, and final newline presence/absence.

## Inspecting

### List interfaces, profiles, ssids

```python
doc = parse(text)

print(doc.interfaces())  # ["eth0", "eth1"]
print(doc.profiles())    # ["static_eth0"]
print(doc.ssids())       # ["Office WiFi"]
```

### Access scope directives

```python
eth0 = doc.interface("eth0")

for d in eth0.directives:
    print(f"{d.name} = {d.value}")

# Access the global scope
glob = doc.global_scope()
print(glob.find("hostname"))
```

### Query static assignments

```python
eth0 = doc.interface("eth0")

print(eth0.static("ip_address"))           # "192.168.1.17/32"
print(eth0.static("routers"))              # "192.168.1.1"
print(eth0.static("domain_name_servers"))  # "8.8.8.8 8.8.4.4"
print(eth0.static_all("routes"))           # all static routes=... values
```

### Document-wide queries

```python
doc.find("hostname")       # first Directive with that name, or None
doc.find_all("option")     # all Directives with that name
doc.find_all("static")     # every static directive in the file
```

### Physical blocks vs logical views

A single interface can appear in multiple physical blocks:

```python
text = """\
interface eth0
metric 100

interface eth1
metric 200

interface eth0
nogateway
"""

doc = parse(text)

# Each physical block separately
blocks = doc.interface_blocks("eth0")
print(len(blocks))  # 2

# Logical view combining all blocks
eth0 = doc.interface("eth0")
print(len(eth0.directives))  # 2 (metric + nogateway)
```

## Editing

### Minimal-diff editing

Only the changed line is rewritten; everything else stays byte-identical:

```python
text = """\
# Customer configuration
hostname

interface eth0
static ip_address=192.168.0.10/24
metric 100

# custom unsupported setting
foobar something
"""

doc = parse(text)
eth0 = doc.interface("eth0")
eth0.set_static("ip_address", "192.168.0.20/24")

output = doc.render()
# Only the static ip_address line changed.
# Comments, unknown directives, spacing — all preserved.
```

### Set and remove directives

```python
eth0 = doc.interface("eth0")

# set: update existing or append if missing
eth0.set("nogateway")
eth0.set("metric", "200")

# remove: remove first occurrence (returns True if found)
eth0.remove("nogateway")

# remove_all: remove all occurrences (returns count)
count = eth0.remove_all("option")
```

### Replace directives

```python
eth0 = doc.interface("eth0")

# Replace value of the first matching directive
eth0.replace_first("metric", "300")

# Replace value of every matching directive
eth0.replace_all("option", "new_value")
```

### Static assignment editing

```python
eth0 = doc.interface("eth0")

# Set (update first existing or append)
eth0.set_static("ip_address", "192.168.1.20/24")
eth0.set_static("routers", "192.168.1.1")

# Remove
eth0.remove_static("ip_address")         # first match
eth0.remove_all_static("routes")         # all matches
```

## Creating Configurations

### Build from scratch

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

Output:

```
hostname
clientid

interface eth0
nogateway
static ip_address=192.168.1.17/32
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
```

### Profile fallback pattern

```python
doc = Document()

prof = doc.add_profile("static_eth0")
prof.set_static("ip_address", "192.168.1.16/24")
prof.set_static("routers", "192.168.1.1")

doc.add_blank()

eth0 = doc.add_interface("eth0")
eth0.add_directive("fallback", "static_eth0")

print(doc.render())
```

Output:

```
profile static_eth0
static ip_address=192.168.1.16/24
static routers=192.168.1.1

interface eth0
fallback static_eth0
```

### Ensure (get-or-create)

```python
doc = parse(text)

# Returns existing scope, or creates a new one if it doesn't exist
eth0 = doc.ensure_interface("eth0")
prof = doc.ensure_profile("static_eth0")
wifi = doc.ensure_ssid("Office WiFi")
```

## File I/O

### Read and write

```python
from pydhcpcdparser import Document

doc = Document.from_path("/etc/dhcpcd.conf")
# ... modify ...
doc.write("/etc/dhcpcd.conf")
```

### Atomic write

Safe write using a temporary file, `fsync`, and `os.replace`. Preserves original file permissions:

```python
doc.write_atomic("/etc/dhcpcd.conf")
```

## Validation

Parsing and validation are separate. `parse()` accepts as much content as possible; `validate()` reports diagnostics without modifying the document:

```python
from pydhcpcdparser import parse, validate

doc = parse("interface\nfuture_thing value\nnogateway\nnogateway\n")

for d in validate(doc):
    print(d)
# error: line 1: "interface" requires a value
# warning: line 2: Unknown dhcpcd directive "future_thing"
# warning: line 4: Multiple values found for "nogateway" where normally only one is expected
```

Diagnostic codes:

| Code | Severity | Meaning |
|---|---|---|
| `missing-value` | ERROR | Directive requires a value but none was provided |
| `unknown-directive` | WARNING | Directive name not in the known registry |
| `duplicate-singleton` | WARNING | Singleton directive appears more than once in a scope |

## Effective Configuration

Approximate what directives upstream `read_config()` would apply for a given interface/ssid/profile combination:

```python
doc = parse(open("/etc/dhcpcd.conf").read())

# What directives apply to eth0?
eff = doc.effective_config(interface="eth0")
print(eff.static("ip_address"))
print(eff.find("metric"))
print(eff.find_all("option"))

# Combined filters
eff = doc.effective_config(interface="eth0", ssid="Office WiFi")

# Profile lookup (raises ScopeNotFoundError if not found)
eff = doc.effective_config(profile="static_eth0")
print(eff.static_all("routes"))
```

## Unknown Directives

Unknown directives are accepted, preserved, and round-tripped — ensuring forward compatibility with future dhcpcd versions:

```python
text = "hostname\nfuture_dhcpcd_option foo bar baz\n"
doc = parse(text)

d = doc.find("future_dhcpcd_option")
print(d.name)   # "future_dhcpcd_option"
print(d.value)  # "foo bar baz"

assert doc.render() == text  # unchanged
```

## Raw AST Access

Every node preserves its original raw text for lossless round-tripping:

```python
doc = parse(text)

for node in doc.nodes:
    print(repr(node.raw))
    if node.source_span:
        print(f"  line {node.source_span.line}")
```

## Newline Handling

LF, CRLF, and no-final-newline are all detected and preserved:

```python
# CRLF file
doc = parse("hostname\r\nclientid\r\n")
print(doc.newline)  # "\r\n"
assert doc.render() == "hostname\r\nclientid\r\n"

# No final newline
doc = parse("hostname")
assert doc.render() == "hostname"
```
