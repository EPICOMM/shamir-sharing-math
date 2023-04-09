from secret_sharing.boolean import BooleanNode
from secret_sharing.parse import parse

node = BooleanNode.var


def test_and():
    assert parse("a & b") == node("a") & node("b")


def test_and_many():
    assert parse("a & b & c & d & e") == node("a") & node("b") & node("c") & node("d") & node("e")


def test_and_no_ws():
    assert parse("a&b&c") == node("a") & node("b") & node("c")


def test_and_complex_name():
    assert parse("John Doe & Bill Smyth") == node("John Doe") & node("Bill Smyth")


def test_threshold():
    assert parse("T3(a, b, c)") == BooleanNode.thresh(3, node("a"), node("b"), node("c"))


def test_plain_t():
    assert parse("T & T9000(a, b)") == node("T") & BooleanNode.thresh(9000, node("a"), node("b"))


def test_priority():
    assert parse("a & b | c & d") == node("a") & node("b") | node("c") & node("d")
    assert parse("a & b | c & d") == (node("a") & node("b")) | (node("c") & node("d"))


def test_parentheses():
    assert parse("a & (b | c) & d") == node("a") & (node("b") | node("c")) & node("d")


def test_complex():
    assert parse("a & (b | c) & T2(x | y, q, w&e)") == (
        node("a")
        & (node("b") | node("c"))
        & BooleanNode.thresh(2, node("x") | node("y"), node("q"), node("w") & node("e"))
    )
