from secret_sharing import Configuration, Part


def test_add_to_or():
    before = Configuration(modulo=101, formula="a | b")
    new = Configuration(modulo=101, formula="a | b | c")
    parts = [Part("a", [42])]
    after = before.modify(new, parts, seed=0)
    assert after == [Part("a", [42]), Part("b", [42]), Part("c", [42])]


def test_remove_from_or():
    # TODO: this is not secure and cannot be
    before = Configuration(modulo=101, formula="a | b | c")
    new = Configuration(modulo=101, formula="a | b")
    parts = [Part("a", [42])]
    after = before.modify(new, parts, seed=0)
    assert after == [Part("a", [42]), Part("b", [42]), Part("c", [None])]


def test_add_to_and():
    # TODO: `a` alone is able to do that, but we currently require to be able to restore a secret
    before = Configuration(modulo=101, formula="a & b")
    new = Configuration(modulo=101, formula="a & b & c")
    parts = [Part("a", [0]), Part("b", [42])]
    after = before.modify(new, parts, seed=1)
    assert after == [Part("a", [17]), Part("b", [42]), Part("c", [84])]
    assert (17 + 42 + 84) % 101 == 42


def test_remove_from_and():
    # TODO: This is not working currently :(
    before = Configuration(modulo=101, formula="a & b & c")
    new = Configuration(modulo=101, formula="a & b")
    parts = [Part("a", [17]), Part("b", [42]), Part("c", [84])]
    after = before.modify(new, parts, seed=0)
    assert after == [Part("a", [17]), Part("b", [42])]
    assert (17 + 42 + 84) % 101 == 42


def test_add_to_threshold():
    before = Configuration(modulo=101, formula="T2(a, b, c)")
    new = Configuration(modulo=101, formula="T2(a, b, c, d)")
    parts = [Part("a", [91]), Part("b", [39])]  # c is 88
    after = before.modify(new, parts, seed=1)
    assert after == [Part("a", [91]), Part("b", [39]), Part("c", [88]), Part("d", [36])]


def test_remove_from_threshold():
    # TODO: This is not secure, but should be
    before = Configuration(modulo=101, formula="T3(a, b, c, d, e)")
    new = Configuration(modulo=101, formula="T3(a, b, c, d)")
    parts = [Part("a", [87]), Part("b", [23]), Part("c", [52]), Part("d", [73])]  # e is 86
    after = before.modify(new, parts, seed=1)
    assert after == [Part("a", [87]), Part("b", [23]), Part("c", [52]), Part("d", [73])]
