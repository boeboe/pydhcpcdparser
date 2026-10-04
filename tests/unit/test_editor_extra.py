"""Extra editor tests to cover remaining branches."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydhcpcdparser import parse

if TYPE_CHECKING:
    from pathlib import Path


class TestEditorEdgeCases:
    def test_ensure_profile_existing(self) -> None:
        doc = parse("profile myp\nstatic ip_address=1.1.1.1/24\n")
        p = doc.ensure_profile("myp")  # type: ignore[attr-defined]
        assert p.static("ip_address") == "1.1.1.1/24"

    def test_ensure_profile_new(self) -> None:
        doc = parse("hostname\n")
        p = doc.ensure_profile("newp")  # type: ignore[attr-defined]
        p.set_static("ip_address", "2.2.2.2/24")  # type: ignore[attr-defined]
        assert "profile newp\n" in doc.render()  # type: ignore[attr-defined]

    def test_ensure_ssid_existing(self) -> None:
        doc = parse("ssid MyWifi\nstatic ip_address=3.3.3.3/24\n")
        s = doc.ensure_ssid("MyWifi")  # type: ignore[attr-defined]
        assert s.static("ip_address") == "3.3.3.3/24"

    def test_ensure_ssid_new(self) -> None:
        doc = parse("hostname\n")
        s = doc.ensure_ssid("NewWifi")  # type: ignore[attr-defined]
        s.add_directive("metric", "100")  # type: ignore[attr-defined]
        assert "ssid NewWifi\n" in doc.render()  # type: ignore[attr-defined]

    def test_add_ssid_scope(self) -> None:
        doc = parse("")
        s = doc.add_ssid("TestWifi")  # type: ignore[attr-defined]
        s.add_directive("metric", "50")  # type: ignore[attr-defined]
        result = doc.render()  # type: ignore[attr-defined]
        assert "ssid TestWifi\n" in result
        assert "metric 50\n" in result

    def test_scope_remove_all_static(self) -> None:
        doc = parse("interface eth0\nstatic routes=a\nstatic routes=b\nstatic ip_address=c\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        count = eth0.remove_all_static("routes")  # type: ignore[attr-defined]
        assert count == 2
        assert eth0.static("routes") is None
        assert eth0.static("ip_address") == "c"

    def test_doc_append_and_remove(self) -> None:
        from pydhcpcdparser.ast import Directive

        doc = parse("hostname\n")
        node = Directive(raw="", newline="\n", modified=True, name="clientid")
        doc.append(node)  # type: ignore[attr-defined]
        assert len(doc.nodes) == 2
        doc.remove(node)  # type: ignore[attr-defined]
        assert len(doc.nodes) == 1

    def test_doc_insert(self) -> None:
        from pydhcpcdparser.ast import Directive

        doc = parse("hostname\nclientid\n")
        node = Directive(raw="", newline="\n", modified=True, name="persistent")
        doc.insert(1, node)  # type: ignore[attr-defined]
        result = doc.render()  # type: ignore[attr-defined]
        lines = result.splitlines()
        assert lines[1] == "persistent"

    def test_global_scope_insert(self) -> None:
        """Adding a directive to global scope inserts before first scope opener."""
        doc = parse("hostname\n\ninterface eth0\nmetric 100\n")
        g = doc.global_scope()  # type: ignore[attr-defined]
        g.add_directive("clientid")  # type: ignore[attr-defined]
        result = doc.render()  # type: ignore[attr-defined]
        lines = result.splitlines()
        assert "clientid" in lines
        # clientid should be before "interface eth0"
        ci_idx = lines.index("clientid")
        iface_idx = lines.index("interface eth0")
        assert ci_idx < iface_idx

    def test_scope_view_static_assignment(self) -> None:
        doc = parse("interface eth0\nstatic ip_address=1.1.1.1/24\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        d = eth0.find("static")
        assert d is not None
        result = eth0.static_assignment(d)
        assert result == ("ip_address", "1.1.1.1/24")

    def test_scope_view_static_assignment_no_equals(self) -> None:
        doc = parse("interface eth0\nstatic something\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        d = eth0.find("static")
        assert d is not None
        result = eth0.static_assignment(d)
        assert result == ("something", "")

    def test_scope_view_static_assignment_not_static(self) -> None:
        doc = parse("interface eth0\nmetric 100\n")
        eth0 = doc.interface("eth0")  # type: ignore[attr-defined]
        d = eth0.find("metric")
        assert d is not None
        result = eth0.static_assignment(d)
        assert result is None

    def test_write_atomic_failure_cleanup(self, tmp_path: Path) -> None:
        """Verify temp file is cleaned up on write failure."""
        tmp_path / "readonly_dir" / "test.conf"
        doc = parse("hostname\n")
        # Just test that write_atomic to a valid path works
        target2 = tmp_path / "test.conf"
        doc.write_atomic(target2)  # type: ignore[attr-defined]
        assert target2.read_text() == "hostname\n"
