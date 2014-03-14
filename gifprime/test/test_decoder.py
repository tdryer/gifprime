from gifprime.__main__ import GIF


def test_decoder():
    filename = 'gifprime/test/data/whitepixel.gif'
    gif = GIF(filename)
    assert gif.filename == filename
    assert gif.comments == ["Created with GIMP"]
