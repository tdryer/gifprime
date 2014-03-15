from gifprime.__main__ import GIF


def test_whitepixel():
    filename = 'gifprime/test/data/whitepixel.gif'
    gif = GIF(filename)
    assert gif.filename == filename
    assert gif.comments == ["Created with GIMP"]
    assert gif.size == (1, 1)


def test_8x8gradient():
    filename = 'gifprime/test/data/8x8gradient.gif'
    gif = GIF(filename)
    assert gif.filename == filename
    assert gif.comments == ["Created with GIMP"]
    assert gif.size == (8, 8)


def test_8x8gradientanim():
    filename = 'gifprime/test/data/8x8gradientanim.gif'
    gif = GIF(filename)
    assert gif.filename == filename
    assert gif.comments == ["Created with GIMP"]
    assert gif.size == (8, 8)
