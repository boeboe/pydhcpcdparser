"""Unit tests for the effective configuration resolver."""

from __future__ import annotations

import pytest

from pydhcpcdparser import parse
from pydhcpcdparser.exceptions import ScopeNotFoundError


class TestEffectiveConfig:
    def test_global_only(self) -> None:
        doc = parse("hostname\nclientid\n")
        eff = doc.effective_config()  # type: ignore[attr-defined]
        names = [d.name for d in eff.directives]
        assert names == ["hostname", "clientid"]

    def test_global_with_interface_no_filter(self) -> None:
        """Without an interface filter, only global directives apply."""
        text = "hostname\n\ninterface eth0\nmetric 100\n"
        doc = parse(text)
        eff = doc.effective_config()  # type: ignore[attr-defined]
        names = [d.name for d in eff.directives]
        assert names == ["hostname"]

    def test_interface_filter(self) -> None:
        text = "hostname\n\ninterface eth0\nmetric 100\nstatic ip_address=1.1.1.1/24\n"
        doc = parse(text)
        eff = doc.effective_config(interface="eth0")  # type: ignore[attr-defined]
        names = [d.name for d in eff.directives]
        assert "hostname" in names
        assert "metric" in names
        assert "static" in names

    def test_interface_filter_skip_other(self) -> None:
        text = "hostname\n\ninterface eth0\nmetric 100\n\ninterface eth1\nmetric 200\n"
        doc = parse(text)
        eff = doc.effective_config(interface="eth0")  # type: ignore[attr-defined]
        values = [d.value for d in eff.directives if d.name == "metric"]
        assert values == ["100"]

    def test_interface_fnmatch(self) -> None:
        text = "interface eth*\nmetric 100\n"
        doc = parse(text)
        eff = doc.effective_config(interface="eth0")  # type: ignore[attr-defined]
        assert len(eff.directives) == 1
        assert eff.directives[0].name == "metric"

    def test_interface_no_match(self) -> None:
        text = "interface eth0\nmetric 100\n"
        doc = parse(text)
        eff = doc.effective_config(interface="wlan0")  # type: ignore[attr-defined]
        assert len(eff.directives) == 0

    def test_ssid_filter(self) -> None:
        text = (
            "ssid Office WiFi\n"
            "static ip_address=10.0.0.1/24\n"
            "\n"
            "ssid Home\n"
            "static ip_address=192.168.0.1/24\n"
        )
        doc = parse(text)
        eff = doc.effective_config(ssid="Office WiFi")  # type: ignore[attr-defined]
        assert eff.static("ip_address") == "10.0.0.1/24"

    def test_profile_filter(self) -> None:
        text = (
            "profile static_eth0\n"
            "static ip_address=1.2.3.4/24\n"
            "static routers=1.2.3.1\n"
            "\n"
            "profile other\n"
            "static ip_address=5.6.7.8/24\n"
        )
        doc = parse(text)
        eff = doc.effective_config(profile="static_eth0")  # type: ignore[attr-defined]
        assert eff.static("ip_address") == "1.2.3.4/24"
        assert eff.static("routers") == "1.2.3.1"

    def test_profile_not_found(self) -> None:
        doc = parse("hostname\n")
        with pytest.raises(ScopeNotFoundError):
            doc.effective_config(profile="nonexistent")  # type: ignore[attr-defined]

    def test_arping_skipped_before_profile(self) -> None:
        """When profile is requested but not yet entered, arping is skipped."""
        text = "arping 192.168.0.1\n\nprofile myprofile\nstatic ip_address=10.0.0.1/24\n"
        doc = parse(text)
        eff = doc.effective_config(profile="myprofile")  # type: ignore[attr-defined]
        names = [d.name for d in eff.directives]
        assert "arping" not in names
        assert "static" in names

    def test_interface_without_value_skipped(self) -> None:
        text = "interface\nmetric 100\n"
        doc = parse(text)
        eff = doc.effective_config(interface="eth0")  # type: ignore[attr-defined]
        assert len(eff.directives) == 0

    def test_combined_global_and_interface(self) -> None:
        text = (
            "hostname\n"
            "clientid\n"
            "\n"
            "interface eth0\n"
            "metric 100\n"
            "nogateway\n"
            "\n"
            "interface eth1\n"
            "metric 200\n"
        )
        doc = parse(text)
        eff = doc.effective_config(interface="eth0")  # type: ignore[attr-defined]
        names = [d.name for d in eff.directives]
        assert names == ["hostname", "clientid", "metric", "nogateway"]

    def test_effective_find(self) -> None:
        doc = parse("hostname\nclientid\n")
        eff = doc.effective_config()  # type: ignore[attr-defined]
        assert eff.find("hostname") is not None
        assert eff.find("nonexistent") is None

    def test_effective_find_all(self) -> None:
        doc = parse("option dns\noption ntp\n")
        eff = doc.effective_config()  # type: ignore[attr-defined]
        assert len(eff.find_all("option")) == 2

    def test_effective_static_all(self) -> None:
        text = "interface eth0\nstatic routes=a\nstatic routes=b\n"
        doc = parse(text)
        eff = doc.effective_config(interface="eth0")  # type: ignore[attr-defined]
        assert eff.static_all("routes") == ["a", "b"]

    def test_duplicate_interface_blocks(self) -> None:
        """Both eth0 blocks contribute to effective config."""
        text = (
            "interface eth0\n"
            "metric 100\n"
            "\n"
            "interface eth1\n"
            "metric 200\n"
            "\n"
            "interface eth0\n"
            "nogateway\n"
        )
        doc = parse(text)
        eff = doc.effective_config(interface="eth0")  # type: ignore[attr-defined]
        names = [d.name for d in eff.directives]
        assert "metric" in names
        assert "nogateway" in names
