"""Разбор XML без потерь: смещения, BOM, сущности, CRLF, защита от DTD и внешних сущностей."""

from __future__ import annotations

import pytest

from cds2astra import xmltree as X

DOC = '<?xml version="1.0"?>\n<a x="1&gt;2"><b/><c>t&lt;x</c>\r\n<d><![CDATA[q<w]]></d></a>'


def test_offsets_slice_elements() -> None:
    raw = DOC.encode()
    doc = X.parse(raw)
    a = doc.root
    assert raw[a.start : a.end].startswith(b"<a ") and raw[a.start : a.end].endswith(b"</a>")
    b, c, d = a.children
    assert raw[b.start : b.end] == b"<b/>" and b.empty
    assert raw[c.start : c.end] == b"<c>t&lt;x</c>"
    assert c.text == "t<x"
    assert d.text == "q<w"
    assert a.attrs["x"] == "1>2"


def test_bom_offsets() -> None:
    raw = b"\xef\xbb\xbf" + DOC.encode()
    doc = X.parse(raw)
    assert doc.has_bom
    c = doc.root.children[1]
    assert raw[c.start : c.end] == b"<c>t&lt;x</c>"


def test_text_map_entities_crlf_cdata() -> None:
    raw = b"<r><x>a&amp;b\r\nc&#1071;</x><y><![CDATA[z<]]></y></r>"
    doc = X.parse(raw)
    x, y = doc.root.children
    tm = X.text_map(doc, x)
    assert tm.text == "a&b\ncЯ"
    assert raw[tm.offsets[1] : tm.offsets[2]] == b"&amp;"
    assert raw[tm.offsets[3] : tm.offsets[4]] == b"\r\n"
    assert X.text_map(doc, y).text == "z<"


def test_billion_laughs_rejected() -> None:
    bomb = (
        b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;">]><lolz>&lol2;</lolz>'
    )
    with pytest.raises(X.XmlSecurityError):
        X.parse(bomb)


def test_external_entity_rejected() -> None:
    xxe = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY e SYSTEM "file:///etc/passwd">]><r>&e;</r>'
    with pytest.raises(X.XmlSecurityError):
        X.parse(xxe)


def test_broken_xml_has_position() -> None:
    with pytest.raises(X.XmlError) as exc:
        X.parse(b"<a><b></a>")
    assert exc.value.line == 1


def test_escape_round_trip() -> None:
    assert X.escape_text("a<b>&c\nd", "\r\n") == b"a&lt;b&gt;&amp;c\r\nd"
    assert X.escape_attr('x"y') == "x&quot;y"


def test_path_and_data_helpers() -> None:
    raw = b'<p><addData><data name="http://www.3s-software.com/plcopenxml/pou"><q/></data></addData></p>'
    doc = X.parse(raw)
    d = doc.root.data("pou")
    assert d is not None and d.child("q") is not None
    assert d.path() == "/p/addData/data[pou]"
    assert doc.root.datas("pou") == [d]
    assert doc.root.data("missing") is None
