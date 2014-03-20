import pytest
import PIL.Image
from StringIO import StringIO


from gifprime.__main__ import GIF


def get_test_gif_path(name):
    """Return the path to the test gif with the given name."""
    return 'gifprime/test/data/{}'.format(name)


def load_test_gif(name):
    """Load reference GIF using pillow."""
    img = PIL.Image.open(get_test_gif_path(name))
    images = []
    i = 0
    while True:
        try:
            img.seek(i)
        except EOFError:
            break
        i += 1
        images.append({'data': list(img.convert('RGBA').getdata())})
    return {
        'images': images,
        'size': img.size,
        'info': img.info,
    }


@pytest.mark.parametrize('name', [
    'whitepixel.gif',
    'whitepixel_87a.gif',
    '8x8gradient.gif',
    '8x8gradientanim.gif',
    'transparentcircle.gif',
])
def test_gif_decode(name):
    ref = load_test_gif(name)
    gif = GIF(get_test_gif_path(name))

    assert gif.filename == get_test_gif_path(name), 'filename not set correctly'
    assert gif.size == ref['size'], 'size not set correctly'
    assert len(gif.images) == len(ref['images']), 'wrong number of frames'
    assert [d.rgba_data for d in gif.images] == \
            [i['data'] for i in ref['images']], 'wrong image data'


def test_get_gif_comment():
    gif = GIF(get_test_gif_path('whitepixel.gif'))
    assert gif.comments == ["Created with GIMP"]

def test_save():
    # TODO: more and better encoding tests
    gif = GIF()
    gif.size = (1, 1)
    gif.images.append([(255, 255, 255, 255)])
    file_ = StringIO()
    gif.save(file_)
    assert len(file_.getvalue()) > 0
