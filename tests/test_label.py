from pipeline.label import prf


def test_prf():
    res, acc = prf([("a", "a"), ("a", "b"), ("b", "b"), ("b", "b")])
    assert res["a"] == (1.0, 0.5, 2) and res["b"] == (2 / 3, 1.0, 2) and acc == 0.75
