# Examples

## Parse and inspect

```python
from pydhcpcdparser import parse

text = open("/etc/dhcpcd.conf").read()
doc = parse(text)

# List interfaces
print(doc.interfaces())  # ["eth0", "eth1"]

# Inspect a specific interface
eth0 = doc.interface("eth0")
print(eth0.static("ip_address"))    # "192.168.1.17/32"
print(eth0.static("routers"))       # "192.168.1.1"
print(eth0.find("fallback"))        # Directive or None
```

## Round-trip guarantee

```python
from pydhcpcdparser import parse, render

source = open("/etc/dhcpcd.conf").read()
doc = parse(source)
assert render(doc) == source  # byte-for-byte
```

## Minimal-diff editing

```python
doc = parse(open("/etc/dhcpcd.conf").read())
eth0 = doc.interface("eth0")

# Only the static ip_address line changes
eth0.set_static("ip_address", "192.168.1.20/24")

doc.write_atomic("/etc/dhcpcd.conf")
```

## Create a config from scratch

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

## Profile fallback pattern

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

## Unknown directives are preserved

```python
text = "hostname\nfuture_dhcpcd_option foo bar\n"
doc = parse(text)

d = doc.find("future_dhcpcd_option")
print(d.name)   # "future_dhcpcd_option"
print(d.value)  # "foo bar"

assert doc.render() == text  # unchanged
```

## Validation

```python
from pydhcpcdparser import parse, validate

doc = parse("interface\nfuture_thing value\nnogateway\nnogateway\n")
for d in validate(doc):
    print(d)
# error: line 1: "interface" requires a value
# warning: line 2: Unknown dhcpcd directive "future_thing"
# warning: line 4: Multiple values found for "nogateway" where normally only one is expected
```

## Effective configuration

```python
doc = parse(open("/etc/dhcpcd.conf").read())

# What directives apply to eth0?
eff = doc.effective_config(interface="eth0")
print(eff.static("ip_address"))
print(eff.find_all("option"))
```
