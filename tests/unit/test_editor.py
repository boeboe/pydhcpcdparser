"""Unit tests for the editor module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydhcpcdparser import Document, parse

if TYPE_CHECKING:
    from pathlib import Path

# -- Minimal-diff mutation test (requirements §37) ---------------------------


class TestMinimalDiffMutation:
    def test_change_static_ip_only_changes_one_line(self) -> None:
        source = (
            "# Customer configuration\n"
            "hostname\n"
            "\n"
            "interface eth0\n"
            "static ip_address=192.168.0.10/24\n"
            "metric 100\n"
            "\n"
            "# custom unsupported setting\n"
            "foobar something\n"
        )
        expected = (
            "# Customer configuration\n"
            "hostname\n"
            "\n"
            "interface eth0\n"
            "static ip_address=192.168.0.20/24\n"
            "metric 100\n"
            "\n"
            "# custom unsupported setting\n"
            "foobar something\n"
        )
        doc = parse(source)
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        eth0.set_static("ip_address", "192.168.0.20/24")  # type: ignore[attr-defined]
        result = doc.render()  # type: ignore[attr-defined]
        assert result == expected

    def test_only_changed_line_differs(self) -> None:
        source = (
            "hostname\n"
            "\n"
            "interface eth0\n"
            "static ip_address=192.168.0.10/24\n"
            "static routers=192.168.0.1\n"
        )
        doc = parse(source)
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        eth0.set_static("ip_address", "10.0.0.1/24")  # type: ignore[attr-defined]
        result = doc.render()  # type: ignore[attr-defined]

        source_lines = source.splitlines(True)
        result_lines = result.splitlines(True)
        assert len(source_lines) == len(result_lines)
        for i, (s, r) in enumerate(zip(source_lines, result_lines)):
            if i == 3:  # the static ip_address line
                assert r == "static ip_address=10.0.0.1/24\n"
            else:
                assert s == r, f"Line {i} changed unexpectedly"


# -- ScopeView editing -------------------------------------------------------


class TestScopeViewEditing:
    def test_set_new_directive(self) -> None:
        doc = parse("interface eth0\nmetric 100\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        eth0.set("nogateway")  # type: ignore[attr-defined]
        result = doc.render()  # type: ignore[attr-defined]
        assert "nogateway\n" in result

    def test_set_existing_directive(self) -> None:
        doc = parse("interface eth0\nmetric 100\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        eth0.set("metric", "200")  # type: ignore[attr-defined]
        result = doc.render()  # type: ignore[attr-defined]
        assert "metric 200\n" in result
        assert "metric 100" not in result

    def test_set_static(self) -> None:
        doc = parse("interface eth0\nstatic ip_address=1.1.1.1/24\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        eth0.set_static("ip_address", "2.2.2.2/24")  # type: ignore[attr-defined]
        assert eth0.static("ip_address") == "2.2.2.2/24"

    def test_set_static_new(self) -> None:
        doc = parse("interface eth0\nmetric 100\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        eth0.set_static("ip_address", "1.1.1.1/24")  # type: ignore[attr-defined]
        result = doc.render()  # type: ignore[attr-defined]
        assert "static ip_address=1.1.1.1/24\n" in result

    def test_remove(self) -> None:
        doc = parse("interface eth0\nmetric 100\nnogateway\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        assert eth0.remove("nogateway")  # type: ignore[attr-defined]
        result = doc.render()  # type: ignore[attr-defined]
        assert "nogateway" not in result

    def test_remove_not_found(self) -> None:
        doc = parse("interface eth0\nmetric 100\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        assert not eth0.remove("nonexistent")  # type: ignore[attr-defined]

    def test_remove_all(self) -> None:
        doc = parse("interface eth0\nstatic routes=a\nstatic routes=b\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        count = eth0.remove_all("static")  # type: ignore[attr-defined]
        assert count == 2
        assert "static" not in doc.render()  # type: ignore[attr-defined]

    def test_remove_static(self) -> None:
        doc = parse("interface eth0\nstatic ip_address=1.1.1.1/24\nstatic routers=1.1.1.1\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        assert eth0.remove_static("ip_address")  # type: ignore[attr-defined]
        assert eth0.static("ip_address") is None
        assert eth0.static("routers") == "1.1.1.1"

    def test_replace_first(self) -> None:
        doc = parse("interface eth0\noption dns\noption ntp\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        d = eth0.replace_first("option", "domain_name")  # type: ignore[attr-defined]
        assert d is not None
        assert d.value == "domain_name"
        # Second option unchanged
        options = eth0.find_all("option")
        assert options[1].value == "ntp"

    def test_replace_all(self) -> None:
        doc = parse("interface eth0\noption dns\noption ntp\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        result = eth0.replace_all("option", "replaced")  # type: ignore[attr-defined]
        assert len(result) == 2
        assert all(d.value == "replaced" for d in result)


# -- Document-level editing ---------------------------------------------------


class TestDocumentEditing:
    def test_add_directive(self) -> None:
        doc = parse("")
        doc.add_directive("hostname")  # type: ignore[attr-defined]
        assert doc.render() == "hostname\n"  # type: ignore[attr-defined]

    def test_add_directive_with_value(self) -> None:
        doc = parse("")
        doc.add_directive("metric", "100")  # type: ignore[attr-defined]
        assert doc.render() == "metric 100\n"  # type: ignore[attr-defined]

    def test_add_blank(self) -> None:
        doc = parse("hostname\n")
        doc.add_blank()  # type: ignore[attr-defined]
        assert doc.render() == "hostname\n\n"  # type: ignore[attr-defined]

    def test_add_comment(self) -> None:
        doc = parse("")
        doc.add_comment(" a comment")  # type: ignore[attr-defined]
        assert doc.render() == "# a comment\n"  # type: ignore[attr-defined]

    def test_add_interface(self) -> None:
        doc = parse("hostname\n")
        eth0 = doc.add_interface("eth0")  # type: ignore[attr-defined]
        eth0.add_directive("metric", "100")  # type: ignore[attr-defined]
        result = doc.render()  # type: ignore[attr-defined]
        assert "interface eth0\n" in result
        assert "metric 100\n" in result

    def test_add_profile(self) -> None:
        doc = parse("")
        p = doc.add_profile("static_eth0")  # type: ignore[attr-defined]
        p.add_directive("static", "ip_address=1.1.1.1/24")  # type: ignore[attr-defined]
        result = doc.render()  # type: ignore[attr-defined]
        assert "profile static_eth0\n" in result

    def test_ensure_interface_existing(self) -> None:
        doc = parse("interface eth0\nmetric 100\n")
        eth0 = doc.ensure_interface("eth0")  # type: ignore[attr-defined]
        assert eth0.find("metric") is not None

    def test_ensure_interface_new(self) -> None:
        doc = parse("hostname\n")
        eth0 = doc.ensure_interface("eth0")  # type: ignore[attr-defined]
        eth0.add_directive("metric", "100")  # type: ignore[attr-defined]
        assert "interface eth0\n" in doc.render()  # type: ignore[attr-defined]

    def test_creation_from_scratch(self) -> None:
        """Requirements §19: programmatic document creation."""
        doc = Document()
        doc.add_directive("hostname")  # type: ignore[attr-defined]
        doc.add_directive("clientid")  # type: ignore[attr-defined]
        doc.add_blank()  # type: ignore[attr-defined]
        eth0 = doc.add_interface("eth0")  # type: ignore[attr-defined]
        eth0.add_directive("nogateway")  # type: ignore[attr-defined]
        eth0.set_static("ip_address", "192.168.1.17/32")  # type: ignore[attr-defined]

        result = doc.render()  # type: ignore[attr-defined]
        expected = (
            "hostname\nclientid\n\ninterface eth0\nnogateway\nstatic ip_address=192.168.1.17/32\n"
        )
        assert result == expected


# -- File I/O ----------------------------------------------------------------


class TestFileIO:
    def test_write(self, tmp_path: Path) -> None:
        doc = parse("hostname\n")
        target = tmp_path / "test.conf"
        doc.write(target)  # type: ignore[attr-defined]
        assert target.read_text() == "hostname\n"

    def test_write_atomic(self, tmp_path: Path) -> None:
        target = tmp_path / "test.conf"
        target.write_text("old content")
        target.chmod(0o644)

        doc = parse("hostname\n")
        doc.write_atomic(target)  # type: ignore[attr-defined]
        assert target.read_text() == "hostname\n"
        # Permissions preserved
        assert oct(target.stat().st_mode & 0o777) == oct(0o644)

    def test_write_atomic_new_file(self, tmp_path: Path) -> None:
        target = tmp_path / "new.conf"
        doc = parse("hostname\n")
        doc.write_atomic(target)  # type: ignore[attr-defined]
        assert target.read_text() == "hostname\n"

    def test_from_path(self, tmp_path: Path) -> None:
        target = tmp_path / "test.conf"
        target.write_text("hostname\nclientid\n")
        doc = Document.from_path(target)  # type: ignore[attr-defined]
        assert len(doc.nodes) == 2
        assert doc.render() == "hostname\nclientid\n"  # type: ignore[attr-defined]
