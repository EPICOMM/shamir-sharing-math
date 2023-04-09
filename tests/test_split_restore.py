from secret_sharing import Configuration, Part


def test_split_or():
    conf = Configuration(modulo=101, formula="a | b | c")
    splitted = conf.split(42)
    assert splitted == [Part("a", [42]), Part("b", [42]), Part("c", [42])]
    assert conf.restore(splitted) == 42


def test_split_and():
    conf = Configuration(modulo=101, formula="a & b & c")
    splitted = conf.split(42, seed=0)
    assert splitted == [Part("a", [49]), Part("b", [97]), Part("c", [98])]
    assert (49 + 97 + 98) % 101 == 42
    assert conf.restore(splitted) == 42

def test_split_small_threshold():
    conf = Configuration(modulo=101, formula="T2(a, b, c)")
    splitted = conf.split(42, seed=0)
    assert splitted == [
        Part("a", [91]),
        Part("b", [39]),
        Part("c", [88])
    ]
    assert conf.restore(splitted) == 42


def test_split_threshold():
    conf = Configuration(modulo=101, formula="T3(a, b, c, d, e)")
    splitted = conf.split(42, seed=0)
    assert splitted == [
        Part("a", [87]),
        Part("b", [23]),
        Part("c", [52]),
        Part("d", [73]),
        Part("e", [86]),
    ]
    assert conf.restore(splitted) == 42


def test_split_complex():
    conf = Configuration(modulo=101, formula="(XXX & T2(x & y, b | c, d, e)) | (b & c & d & e)")
    splitted = conf.split(42, seed=0)
    assert splitted == [
        Part(name="XXX", values=[49]),
        Part(name="x", values=[53]),
        Part(name="y", values=[37]),
        Part(name="b", values=[86, 5]),
        Part(name="c", values=[86, 33]),
        Part(name="d", values=[82, 65]),
        Part(name="e", values=[78, 40]),
    ]
    assert conf.restore(splitted) == 42


def test_restore_partial():
    conf = Configuration(modulo=101, formula="(XXX & T2(x & y, b | c, d, e)) | (b & c & d & e)")
    splitted = conf.split(42, seed=0)
    # x & y
    assert 42 == conf.restore([
        Part(name="XXX", values=[49]),
        Part(name="x", values=[53]),
        Part(name="y", values=[37]),
        Part(name="e", values=[78, 40]),
    ])
    assert None == conf.restore([
        Part(name="XXX", values=[49]),
        Part(name="x", values=[53]),
        Part(name="e", values=[78, 40]),
    ])
    assert None == conf.restore([
        Part(name="XXX", values=[49]),
        Part(name="y", values=[53]),
        Part(name="e", values=[78, 40]),
    ])

    # b | c
    assert 42 == conf.restore([
        Part(name="XXX", values=[49]),
        Part(name="b", values=[86, 5]),
        Part(name="d", values=[82, 65]),
    ])
    assert 42 == conf.restore([
        Part(name="XXX", values=[49]),
        Part(name="c", values=[86, 33]),
        Part(name="d", values=[82, 65]),
    ])
