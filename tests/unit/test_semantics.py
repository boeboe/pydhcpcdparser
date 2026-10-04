"""Unit tests for scope derivation and query APIs."""

from __future__ import annotations

import pytest

from pydhcpcdparser import parse
from pydhcpcdparser.exceptions import ScopeNotFoundError
from pydhcpcdparser.semantics import ScopeKind, derive_scopes

# -- scope derivation -------------------------------------------------------


class TestDeriveScopes:
    def test_global_only(self) -> None:
        doc = parse("hostname\nclientid\n")
        blocks = derive_scopes(doc)
        assert len(blocks) == 1
        assert blocks[0].kind == ScopeKind.GLOBAL
        assert blocks[0].name is None

    def test_global_then_interface(self) -> None:
        doc = parse("hostname\n\ninterface eth0\nmetric 100\n")
        blocks = derive_scopes(doc)
        assert len(blocks) == 2
        assert blocks[0].kind == ScopeKind.GLOBAL
        assert blocks[1].kind == ScopeKind.INTERFACE
        assert blocks[1].name == "eth0"

    def test_multiple_interfaces(self) -> None:
        doc = parse("interface eth0\nmetric 100\n\ninterface eth1\nmetric 200\n")
        blocks = derive_scopes(doc)
        # global (empty) + eth0 + eth1
        assert len(blocks) == 3
        assert blocks[1].kind == ScopeKind.INTERFACE
        assert blocks[1].name == "eth0"
        assert blocks[2].kind == ScopeKind.INTERFACE
        assert blocks[2].name == "eth1"

    def test_profile_scope(self) -> None:
        doc = parse("profile static_eth0\nstatic ip_address=1.2.3.4/24\n")
        blocks = derive_scopes(doc)
        assert blocks[-1].kind == ScopeKind.PROFILE
        assert blocks[-1].name == "static_eth0"

    def test_ssid_scope(self) -> None:
        doc = parse("ssid Office WiFi\nstatic ip_address=10.0.0.1/24\n")
        blocks = derive_scopes(doc)
        assert blocks[-1].kind == ScopeKind.SSID
        assert blocks[-1].name == "Office WiFi"

    def test_duplicate_interface_blocks(self) -> None:
        text = (
            "interface eth0\nmetric 100\n\n"
            "interface eth1\nmetric 200\n\n"
            "interface eth0\nnogateway\n"
        )
        doc = parse(text)
        blocks = derive_scopes(doc)
        eth0_blocks = [b for b in blocks if b.kind == ScopeKind.INTERFACE and b.name == "eth0"]
        assert len(eth0_blocks) == 2

    def test_commented_interface_not_scope(self) -> None:
        text = "# interface eth0\nhostname\n"
        doc = parse(text)
        blocks = derive_scopes(doc)
        assert len(blocks) == 1
        assert blocks[0].kind == ScopeKind.GLOBAL

    def test_no_return_to_global(self) -> None:
        """After the first scope-opening directive, there is no global scope."""
        text = "hostname\ninterface eth0\nmetric 100\nhostname\n"
        doc = parse(text)
        blocks = derive_scopes(doc)
        # The second 'hostname' is inside eth0, not global
        assert blocks[0].kind == ScopeKind.GLOBAL
        assert blocks[0].end_index == 1  # only 'hostname'
        assert blocks[1].kind == ScopeKind.INTERFACE

    def test_interface_without_value(self) -> None:
        """An interface directive with no value opens a block with name None."""
        doc = parse("interface\nmetric 100\n")
        blocks = derive_scopes(doc)
        iface_blocks = [b for b in blocks if b.kind == ScopeKind.INTERFACE]
        assert len(iface_blocks) == 1
        assert iface_blocks[0].name is None


# -- Document convenience methods -------------------------------------------


class TestDocumentMethods:
    def test_interfaces(self) -> None:
        doc = parse("interface eth0\nmetric 100\n\ninterface eth1\nmetric 200\n")
        assert doc.interfaces() == ["eth0", "eth1"]  # type: ignore[attr-defined]

    def test_interfaces_dedup(self) -> None:
        text = (
            "interface eth0\nmetric 100\ninterface eth1\nmetric 200\ninterface eth0\nnogateway\n"
        )
        doc = parse(text)
        assert doc.interfaces() == ["eth0", "eth1"]  # type: ignore[attr-defined]

    def test_profiles(self) -> None:
        text = "profile static_eth0\nstatic ip_address=1.2.3.4/24\n"
        doc = parse(text)
        assert doc.profiles() == ["static_eth0"]  # type: ignore[attr-defined]

    def test_ssids(self) -> None:
        text = "ssid Office WiFi\nstatic ip_address=10.0.0.1/24\n"
        doc = parse(text)
        assert doc.ssids() == ["Office WiFi"]  # type: ignore[attr-defined]

    def test_interface_view(self) -> None:
        text = "hostname\n\ninterface eth0\nmetric 100\nstatic ip_address=1.2.3.4/24\n"
        doc = parse(text)
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        assert eth0.kind == ScopeKind.INTERFACE
        assert eth0.name == "eth0"
        directives = eth0.directives
        assert len(directives) == 2
        assert directives[0].name == "metric"
        assert directives[1].name == "static"

    def test_interface_not_found(self) -> None:
        doc = parse("hostname\n")
        with pytest.raises(ScopeNotFoundError):
            doc.interface("eth99")  # type: ignore[attr-defined]

    def test_profile_view(self) -> None:
        text = "profile static_eth0\nstatic ip_address=1.2.3.4/24\nstatic routers=1.2.3.1\n"
        doc = parse(text)
        p = doc.profile("static_eth0")  # type: ignore[attr-defined]
        assert p.static("ip_address") == "1.2.3.4/24"
        assert p.static("routers") == "1.2.3.1"

    def test_ssid_view(self) -> None:
        text = "ssid Office WiFi\nstatic ip_address=10.0.0.1/24\n"
        doc = parse(text)
        s = doc.ssid("Office WiFi")  # type: ignore[attr-defined]
        assert s.static("ip_address") == "10.0.0.1/24"

    def test_find(self) -> None:
        doc = parse("hostname\nclientid\n")
        d = doc.find("clientid")  # type: ignore[attr-defined]
        assert d is not None
        assert d.name == "clientid"

    def test_find_not_found(self) -> None:
        doc = parse("hostname\n")
        assert doc.find("nope") is None  # type: ignore[attr-defined]

    def test_find_all(self) -> None:
        text = "option dns\noption ntp\noption dns\n"
        doc = parse(text)
        results = doc.find_all("option")  # type: ignore[attr-defined]
        assert len(results) == 3

    def test_render_method(self) -> None:
        text = "hostname\n"
        doc = parse(text)
        assert doc.render() == text  # type: ignore[attr-defined]


# -- ScopeView query helpers -------------------------------------------------


class TestScopeView:
    def test_find(self) -> None:
        text = "interface eth0\nmetric 100\nnogateway\n"
        doc = parse(text)
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        assert eth0.find("metric") is not None
        assert eth0.find("nogateway") is not None
        assert eth0.find("hostname") is None

    def test_find_all(self) -> None:
        text = "interface eth0\nstatic routes=1.0.0.0/8 1.1.1.1\nstatic routes=2.0.0.0/8 2.2.2.2\n"
        doc = parse(text)
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        statics = eth0.find_all("static")
        assert len(statics) == 2

    def test_static(self) -> None:
        text = "interface eth0\nstatic ip_address=192.168.1.17/32\nstatic routers=192.168.1.1\n"
        doc = parse(text)
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        assert eth0.static("ip_address") == "192.168.1.17/32"
        assert eth0.static("routers") == "192.168.1.1"
        assert eth0.static("nonexistent") is None

    def test_static_all(self) -> None:
        text = "interface eth0\nstatic routes=1.0.0.0/8 gw1\nstatic routes=2.0.0.0/8 gw2\n"
        doc = parse(text)
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        assert eth0.static_all("routes") == ["1.0.0.0/8 gw1", "2.0.0.0/8 gw2"]

    def test_static_returns_last(self) -> None:
        """static() returns the *last* assignment, matching upstream override."""
        text = "interface eth0\nstatic ip_address=1.1.1.1/24\nstatic ip_address=2.2.2.2/24\n"
        doc = parse(text)
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        assert eth0.static("ip_address") == "2.2.2.2/24"

    def test_duplicate_interface_combined(self) -> None:
        text = (
            "interface eth0\nmetric 100\n\n"
            "interface eth1\nmetric 200\n\n"
            "interface eth0\nnogateway\n"
        )
        doc = parse(text)
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        names = [d.name for d in eth0.directives]
        assert "metric" in names
        assert "nogateway" in names

    def test_global_scope(self) -> None:
        text = "hostname\nclientid\n\ninterface eth0\nmetric 100\n"
        doc = parse(text)
        g = doc.global_scope()  # type: ignore[attr-defined]
        assert g.kind == ScopeKind.GLOBAL
        directives = g.directives
        assert len(directives) == 2
        assert directives[0].name == "hostname"
        assert directives[1].name == "clientid"

    def test_interface_blocks_separate(self) -> None:
        text = "interface eth0\nmetric 100\n\ninterface eth0\nnogateway\n"
        doc = parse(text)
        blocks = doc.interface_blocks("eth0")  # type: ignore[attr-defined]
        assert len(blocks) == 2
        assert len(blocks[0].directives) == 1
        assert blocks[0].directives[0].name == "metric"
        assert len(blocks[1].directives) == 1
        assert blocks[1].directives[0].name == "nogateway"


# -- fnmatch interface patterns ----------------------------------------------


class TestInterfaceFnmatch:
    def test_wildcard_pattern(self) -> None:
        text = "interface eth*\nmetric 100\n"
        doc = parse(text)
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        assert eth0.find("metric") is not None

    def test_wildcard_no_match(self) -> None:
        text = "interface eth*\nmetric 100\n"
        doc = parse(text)
        with pytest.raises(ScopeNotFoundError):
            doc.interface("wlan0")  # type: ignore[attr-defined]

    def test_question_mark_pattern(self) -> None:
        text = "interface eth?\nmetric 100\n"
        doc = parse(text)
        assert doc.interface("eth0").find("metric") is not None  # type: ignore[attr-defined]
        assert doc.interface("eth1").find("metric") is not None  # type: ignore[attr-defined]
        with pytest.raises(ScopeNotFoundError):
            doc.interface("eth10")  # type: ignore[attr-defined]
