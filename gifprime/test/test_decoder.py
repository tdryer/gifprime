from gifprime.__main__ import GIF


def test_decoder():
    gif = GIF('gifprime/test/data/whitepixel.gif')
    assert gif.signature == 'GIF'
    assert gif.version == '89a'
    assert gif.size == 56
    assert gif.width == 1
    assert gif.height == 1
    assert gif.gct_flag == True
    assert gif.colour_res == 0
    assert gif.sort_flag == False
    assert gif.gct_size == 0
    assert gif.bg_col_index == 0
    assert gif.pixel_aspect == 0
    assert gif.gct == [
        (255, 255, 255),
        (255, 255, 255),
    ]
    assert gif.comments == ['Created with GIMP']
