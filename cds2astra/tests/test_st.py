"""Лексер ST без потерь и правки по диапазонам (в т. ч. свойства hypothesis)."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as hs

from cds2astra.ir import st


def kinds(text: str) -> list[tuple[str, str]]:
    return [(t.kind, t.text) for t in st.tokenize(text) if t.kind not in st.TRIVIA]


def test_lossless_basic() -> None:
    src = "(* a (* b *) c *)\nx := UTF8#'Hi'; // c\n{attribute 'x'}\ny := w.%B1 + T#5S + 16#FF; z AT %IX0.3 : BOOL;"
    assert "".join(t.text for t in st.tokenize(src)) == src


def test_utf8_and_partial_tokens() -> None:
    k = kinds("s := UTF8#'Привет'; b := w.%X3; c := d.%B0;")
    assert (st.TK_UTF8, "UTF8#'Привет'") in k
    assert (st.TK_PARTIAL, "%X3") in k and (st.TK_PARTIAL, "%B0") in k


def test_address_and_typed_literals() -> None:
    k = kinds("x AT %QW10 : WORD := 16#00FF; t := TIME#1S500MS;")
    assert (st.TK_ADDRESS, "%QW10") in k
    assert any(kind == st.TK_TYPED and text.startswith("TIME#") for kind, text in k)


def test_nested_comments() -> None:
    toks = st.tokenize("(* outer (* inner *) still *)x")
    assert toks[0].kind == st.TK_COMMENT and toks[0].text.endswith("still *)")


def test_apply_edits_conflicts_are_dropped() -> None:
    text = "abcdef"
    out, applied, conflicts = st.apply_edits(
        text, [st.Edit(0, 3, "X", "A"), st.Edit(2, 4, "Y", "B"), st.Edit(5, 6, "Z", "C")]
    )
    assert out == "abcdeZ"
    assert {c.rule for c in conflicts} == {"A", "B"}
    assert [e.rule for e in applied] == ["C"]


def test_statement_anchor_and_comment_safe() -> None:
    from cds2astra.session import statement_start

    text = "a := 1;\nb := f(1,\n      g(2));\n"
    pos = text.index("g(")
    assert text[statement_start(text, pos) :].startswith("b :=")
    assert st.comment_safe("a *) b (* c") == "a * ) b ( * c"


@settings(max_examples=150, deadline=None)
@given(hs.text(alphabet=hs.sampled_from(list("abxyz019 :=;.%()*/'\"{}\n\t#IQXBW_")), max_size=120))
def test_lexer_lossless_property(src: str) -> None:
    assert "".join(t.text for t in st.tokenize(src)) == src


@settings(max_examples=100, deadline=None)
@given(
    hs.lists(
        hs.tuples(hs.integers(0, 20), hs.integers(0, 5), hs.text(alphabet="XYZ", max_size=3)),
        max_size=6,
    ),
    hs.randoms(use_true_random=False),
)
def test_edits_order_independent(spec: list[tuple[int, int, str]], rnd: object) -> None:
    text = "0123456789abcdefghij"
    edits = [st.Edit(a, min(a + n, len(text)), rep, f"R{i}") for i, (a, n, rep) in enumerate(spec) if a <= len(text)]
    shuffled = list(edits)
    rnd.shuffle(shuffled)  # type: ignore[attr-defined]
    assert st.apply_edits(text, edits)[0] == st.apply_edits(text, shuffled)[0]
