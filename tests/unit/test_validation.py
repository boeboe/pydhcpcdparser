"""Unit tests for validation and directive registry."""

from __future__ import annotations

from pydhcpcdparser import parse, validate
from pydhcpcdparser.directives import ArgumentRequirement, is_known, lookup
from pydhcpcdparser.validation import Severity

# -- directive registry ------------------------------------------------------


class TestDirectiveRegistry:
    def test_known_directives(self) -> None:
        assert is_known("hostname")
        assert is_known("interface")
        assert is_known("static")
        assert is_known("nogateway")
        assert is_known("option")
        assert is_known("profile")

    def test_unknown_directive(self) -> None:
        assert not is_known("future_unknown_thing")

    def test_lookup_returns_spec(self) -> None:
        spec = lookup("hostname")
        assert spec is not None
        assert spec.name == "hostname"
        assert spec.argument == ArgumentRequirement.OPTIONAL
        assert spec.singleton is True

    def test_lookup_unknown_returns_none(self) -> None:
        assert lookup("nonexistent") is None

    def test_interface_requires_value(self) -> None:
        spec = lookup("interface")
        assert spec is not None
        assert spec.argument == ArgumentRequirement.REQUIRED

    def test_nogateway_no_argument(self) -> None:
        spec = lookup("nogateway")
        assert spec is not None
        assert spec.argument == ArgumentRequirement.NONE
        assert spec.singleton is True

    def test_static_requires_value(self) -> None:
        spec = lookup("static")
        assert spec is not None
        assert spec.argument == ArgumentRequirement.REQUIRED


# -- validation diagnostics --------------------------------------------------


class TestValidation:
    def test_valid_config_no_diagnostics(self) -> None:
        text = "hostname\nclientid\n\ninterface eth0\nmetric 100\n"
        doc = parse(text)
        diags = validate(doc)
        assert len(diags) == 0

    def test_unknown_directive_warning(self) -> None:
        text = "future_option foo bar\n"
        doc = parse(text)
        diags = validate(doc)
        assert len(diags) == 1
        assert diags[0].severity == Severity.WARNING
        assert diags[0].code == "unknown-directive"
        assert "future_option" in diags[0].message

    def test_missing_value_error(self) -> None:
        text = "interface\n"
        doc = parse(text)
        diags = validate(doc)
        errors = [d for d in diags if d.code == "missing-value"]
        assert len(errors) == 1
        assert errors[0].severity == Severity.ERROR

    def test_missing_static_value_error(self) -> None:
        text = "interface eth0\nstatic\n"
        doc = parse(text)
        diags = validate(doc)
        errors = [d for d in diags if d.code == "missing-value"]
        assert len(errors) == 1

    def test_duplicate_singleton_warning(self) -> None:
        text = "interface eth0\nnogateway\nnogateway\n"
        doc = parse(text)
        diags = validate(doc)
        dups = [d for d in diags if d.code == "duplicate-singleton"]
        assert len(dups) == 1
        assert dups[0].severity == Severity.WARNING

    def test_duplicate_non_singleton_ok(self) -> None:
        """option can appear multiple times — no warning."""
        text = "option dns\noption ntp\n"
        doc = parse(text)
        diags = validate(doc)
        assert all(d.code != "duplicate-singleton" for d in diags)

    def test_validation_does_not_modify(self) -> None:
        text = "future_option foo\n"
        doc = parse(text)
        original = doc.render()  # type: ignore[attr-defined]
        validate(doc)
        assert doc.render() == original  # type: ignore[attr-defined]

    def test_diagnostic_str(self) -> None:
        text = "future_option foo\n"
        doc = parse(text)
        diags = validate(doc)
        s = str(diags[0])
        assert "warning" in s
        assert "line 1" in s

    def test_multiple_scopes(self) -> None:
        text = "hostname\n\ninterface eth0\nfuture_thing value\n\ninterface eth1\nmetric 100\n"
        doc = parse(text)
        diags = validate(doc)
        unknowns = [d for d in diags if d.code == "unknown-directive"]
        assert len(unknowns) == 1
        assert "future_thing" in unknowns[0].message
