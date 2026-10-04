"""Unit tests for the lexer."""

from __future__ import annotations

from pydhcpcdparser.ast import BlankLine, Comment, Directive
from pydhcpcdparser.lexer import lex_line


def test_blank_line() -> None:
    node = lex_line("\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, BlankLine)
    assert node.raw == "\n"


def test_whitespace_only_line() -> None:
    node = lex_line("   \t  \n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, BlankLine)
    assert node.raw == "   \t  \n"


def test_hash_comment() -> None:
    node = lex_line("# a comment\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Comment)
    assert node.prefix == "#"
    assert node.text == " a comment"
    assert node.raw == "# a comment\n"


def test_semicolon_comment() -> None:
    node = lex_line("; another comment\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Comment)
    assert node.prefix == ";"
    assert node.text == " another comment"


def test_indented_comment() -> None:
    node = lex_line("  # indented comment\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Comment)
    assert node.prefix == "#"


def test_simple_directive_no_value() -> None:
    node = lex_line("hostname\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "hostname"
    assert node.value is None
    assert node.inline_comment is None


def test_directive_with_value() -> None:
    node = lex_line("metric 100\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "metric"
    assert node.value == "100"
    assert node.separator == " "


def test_directive_with_tab_separator() -> None:
    node = lex_line("metric\t100\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "metric"
    assert node.value == "100"
    assert node.separator == "\t"


def test_directive_with_inline_comment() -> None:
    node = lex_line("hostname # set the hostname\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "hostname"
    assert node.inline_comment is not None
    assert "# set the hostname" in node.inline_comment


def test_directive_with_value_and_inline_comment() -> None:
    node = lex_line("metric 100 # low metric\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "metric"
    assert node.value == "100"
    assert node.inline_comment is not None
    assert "# low metric" in node.inline_comment


def test_quoted_hash_not_comment() -> None:
    """Hash inside quotes must not start a comment."""
    raw = 'env foo="hello # world"\n'
    node = lex_line(raw, line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "env"
    assert node.value is not None
    assert "hello # world" in node.value


def test_quoted_hash_with_real_comment() -> None:
    """Hash inside quotes is protected; hash outside is a comment."""
    raw = 'env foo="hello # world" # real comment\n'
    node = lex_line(raw, line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "env"
    assert node.value is not None
    assert "hello # world" in node.value
    assert node.inline_comment is not None
    assert "# real comment" in node.inline_comment


def test_escaped_hash() -> None:
    """Backslash-escaped hash must not start a comment."""
    raw = "env foo=bar\\#baz\n"
    node = lex_line(raw, line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "env"
    assert node.value is not None
    assert "bar\\#baz" in node.value
    assert node.inline_comment is None


def test_leading_whitespace_preserved() -> None:
    node = lex_line("  metric 100\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.leading_whitespace == "  "
    assert node.name == "metric"


def test_static_assignment() -> None:
    node = lex_line("static ip_address=192.168.1.17/32\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "static"
    assert node.value == "ip_address=192.168.1.17/32"


def test_interface_directive() -> None:
    node = lex_line("interface eth0\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "interface"
    assert node.value == "eth0"


def test_crlf_line() -> None:
    node = lex_line("hostname\r\n", line_number=1, offset=0, newline="\r\n")
    assert isinstance(node, Directive)
    assert node.name == "hostname"
    assert node.raw == "hostname\r\n"
    assert node.newline == "\r\n"


def test_no_newline_line() -> None:
    node = lex_line("hostname", line_number=1, offset=0, newline="")
    assert isinstance(node, Directive)
    assert node.name == "hostname"
    assert node.raw == "hostname"
    assert node.newline == ""


def test_source_span() -> None:
    node = lex_line("hostname\n", line_number=3, offset=20, newline="\n")
    assert node.source_span is not None
    assert node.source_span.line == 3
    assert node.source_span.start == 20
    assert node.source_span.end == 29


def test_directive_value_with_equals() -> None:
    """static ip_address=... should keep the whole value together."""
    node = lex_line("static ip_address=192.168.0.10/24\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "static"
    assert node.value == "ip_address=192.168.0.10/24"


def test_option_with_commas() -> None:
    node = lex_line(
        "option domain_name_servers, domain_name, domain_search\n",
        line_number=1,
        offset=0,
        newline="\n",
    )
    assert isinstance(node, Directive)
    assert node.name == "option"
    assert node.value == "domain_name_servers, domain_name, domain_search"


def test_no_value_directive_with_comment_hash() -> None:
    """hostname # foo  ->  name=hostname, value=None, inline_comment has #."""
    node = lex_line("hostname # foo\n", line_number=1, offset=0, newline="\n")
    assert isinstance(node, Directive)
    assert node.name == "hostname"
    assert node.inline_comment is not None
    assert "# foo" in node.inline_comment
