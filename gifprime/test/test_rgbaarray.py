from gifprime import rgbaarray

ONE = (1, 2, 3, 4)
TWO = (5, 6, 7, 8)

def test_init():
    a = rgbaarray.RGBAArray()
    assert list(a) == []
    a = rgbaarray.RGBAArray(rgba_list=[ONE, TWO])
    assert list(a) == [ONE, TWO]

def test_append():
    a = rgbaarray.RGBAArray()
    a.append(ONE)
    assert a[0] == ONE
    a.append(TWO)
    assert a[0] == ONE
    assert a[1] == TWO

def test_extend():
    a = rgbaarray.RGBAArray()
    a.extend(rgba for rgba in [ONE, TWO])

def test_len():
    a = rgbaarray.RGBAArray()
    assert len(a) == 0
    a.append(ONE)
    a.append(TWO)
    assert len(a) == 2

def test_iter():
    a = rgbaarray.RGBAArray()
    a.append(ONE)
    a.append(TWO)
    assert list(a) == [ONE, TWO]
