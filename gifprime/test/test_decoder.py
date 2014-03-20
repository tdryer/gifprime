from gifprime.__main__ import GIF


def test_whitepixel():
    filename = 'gifprime/test/data/whitepixel.gif'
    gif = GIF(filename)
    assert gif.filename == filename
    assert gif.comments == ["Created with GIMP"]
    assert gif.size == (1, 1)
    assert len(gif.images) == 1
    assert gif.images[0].rgba_data == [(255, 255, 255, 255)]


def test_whitepixel_87a():
    filename = 'gifprime/test/data/whitepixel_87a.gif'
    gif = GIF(filename)
    assert gif.filename == filename
    assert gif.comments == []
    assert gif.size == (1, 1)
    assert len(gif.images) == 1
    assert gif.images[0].rgba_data == [(255, 255, 255, 255)]


def test_8x8gradient():
    filename = 'gifprime/test/data/8x8gradient.gif'
    gif = GIF(filename)
    assert gif.filename == filename
    assert gif.comments == ["Created with GIMP"]
    assert gif.size == (8, 8)
    assert len(gif.images) == 1
    # TODO check image data


def test_8x8gradientanim():
    filename = 'gifprime/test/data/8x8gradientanim.gif'
    gif = GIF(filename)
    assert gif.filename == filename
    assert gif.comments == ["Created with GIMP"]
    assert gif.size == (8, 8)
    assert len(gif.images) == 3
    # TODO check image data
