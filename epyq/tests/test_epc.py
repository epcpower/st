import pytest

def test_range_limit():
    pytest.skip("as a skip example")


def test_pass():
    pass


def test_fail():
    print('red')
    assert 17 == 2**3, 'ack'
