"""Tests based on examples from the upstream dhcpcd.conf.5.in man page.

These are real-world configuration patterns from the upstream documentation.
"""

from __future__ import annotations

from pydhcpcdparser import parse
from pydhcpcdparser.renderer import render


class TestUpstreamExamples:
    def test_static_configuration(self) -> None:
        """Man page example: static address configuration."""
        text = (
            "interface eth0\n"
            "noipv6rs\n"
            "static ip_address=192.168.0.10/24\n"
            "static broadcast_address=192.168.0.63\n"
            "static ip6_address=fd51:42f8:caae:d92e::ff/64\n"
            "static routers=192.168.0.1\n"
            "static domain_name_servers=192.168.0.1 fd51:42f8:caae:d92e::1\n"
        )
        doc = parse(text)
        assert render(doc) == text

        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        assert eth0.static("ip_address") == "192.168.0.10/24"
        assert eth0.static("broadcast_address") == "192.168.0.63"
        assert eth0.static("routers") == "192.168.0.1"
        assert eth0.find("noipv6rs") is not None

    def test_ppp_destination(self) -> None:
        """Man page example: PPP with destination keyword."""
        text = "interface ppp0\nstatic ip_address=0.0.0.0\ndestination routers\n"
        doc = parse(text)
        assert render(doc) == text

        ppp0 = doc.interface("ppp0")  # type: ignore[attr-defined]
        assert ppp0.static("ip_address") == "0.0.0.0"
        assert ppp0.find("destination") is not None

    def test_arping_profile_selection(self) -> None:
        """Man page example: arping with profile fallback."""
        text = (
            "interface bge0\n"
            "arping 192.168.0.1\n"
            "\n"
            "# My specific 192.168.0.1 network\n"
            "profile dd:ee:aa:dd:bb:ee\n"
            "static ip_address=192.168.0.10/24\n"
            "\n"
            "# A generic 192.168.0.1 network\n"
            "profile 192.168.0.1\n"
            "static ip_address=192.168.0.98/24\n"
        )
        doc = parse(text)
        assert render(doc) == text

        profiles = doc.profiles()  # type: ignore[attr-defined]
        assert "dd:ee:aa:dd:bb:ee" in profiles
        assert "192.168.0.1" in profiles

        p1 = doc.profile("dd:ee:aa:dd:bb:ee")  # type: ignore[attr-defined]
        assert p1.static("ip_address") == "192.168.0.10/24"

    def test_ia_pd_delegation(self) -> None:
        """Man page example: prefix delegation."""
        text = "interface eth0\nia_pd 1 eth1/0/64 eth2/1/64\n"
        doc = parse(text)
        assert render(doc) == text

        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        d = eth0.find("ia_pd")
        assert d is not None
        assert d.value == "1 eth1/0/64 eth2/1/64"

    def test_nohook_example(self) -> None:
        """Man page example: nohook."""
        text = "nohook resolv.conf, wpa_supplicant\n"
        doc = parse(text)
        assert render(doc) == text
        d = doc.find("nohook")  # type: ignore[attr-defined]
        assert d is not None
        assert d.value == "resolv.conf, wpa_supplicant"

    def test_env_examples(self) -> None:
        """Man page example: env directives."""
        text = "env force_hostname=YES\nenv wpa_supplicant_driver=nl80211\n"
        doc = parse(text)
        assert render(doc) == text
        envs = doc.find_all("env")  # type: ignore[attr-defined]
        assert len(envs) == 2
        assert envs[0].value == "force_hostname=YES"

    def test_fallback_profile(self) -> None:
        """Typical fallback pattern."""
        text = (
            "profile static_eth0\n"
            "static ip_address=192.168.1.16/24\n"
            "static routers=192.168.1.1\n"
            "static domain_name_servers=192.168.1.1\n"
            "\n"
            "interface eth0\n"
            "fallback static_eth0\n"
        )
        doc = parse(text)
        assert render(doc) == text

        p = doc.profile("static_eth0")  # type: ignore[attr-defined]
        assert p.static("ip_address") == "192.168.1.16/24"

        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        assert eth0.find("fallback") is not None
        assert eth0.find("fallback").value == "static_eth0"  # type: ignore[union-attr]
