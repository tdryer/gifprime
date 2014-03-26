import pytest
import PIL.Image
from StringIO import StringIO


from gifprime.__main__ import GIF, Image


def get_test_gif_path(name):
    """Return the path to the test gif with the given name."""
    return 'gifprime/test/data/{}'.format(name)


def load_test_gif(fp):
    """Load reference GIF using pillow."""
    img = PIL.Image.open(fp)
    images = []
    i = 0
    while True:
        try:
            img.seek(i)
        except EOFError:
            break
        i += 1
        images.append({'data': list(img.convert('RGBA').getdata())})

    # convert loop count to number of times animation should be shown, or 0
    if 'loop' in img.info:
        loop = img.info['loop']
        loop = loop if loop == 0 else loop + 1
    else:
        loop = 1

    return {
        'images': images,
        'size': img.size,
        'info': img.info,
        'loop': loop,
    }


@pytest.mark.parametrize('name', [
    'whitepixel.gif',
    'whitepixel_87a.gif',
    '8x8gradient.gif',
    '8x8gradientanim.gif',
    '8x8gradientanim_loop_twice.gif',
    '8x8gradientanim_delay_1s_2s_3s.gif',
    'transparentcircle.gif',
    'steam.gif',
])
def test_gif_decode(name):
    ref = load_test_gif(get_test_gif_path(name))
    gif = GIF(get_test_gif_path(name))

    assert gif.filename == get_test_gif_path(name), 'filename not set correctly'
    assert gif.size == ref['size'], 'size not set correctly'
    assert len(gif.images) == len(ref['images']), 'wrong number of frames'
    assert [d.rgba_data for d in gif.images] == \
            [i['data'] for i in ref['images']], 'wrong image data'
    assert gif.loop_count == ref['loop']


@pytest.mark.parametrize('name', [
    'whitepixel.gif',
    '8x8gradient.gif',
    'transparentcircle.gif',
    '8x8gradientanim.gif',
    '8x8gradientanim_loop_twice.gif',
])
def test_gif_encode(name):
    # load testcase image using PIL
    ref = load_test_gif(get_test_gif_path(name))

    # encode image as gif
    gif = GIF()
    gif.size = ref['size']
    gif.images = [Image(i['data'], ref['size'], 0) for i in ref['images']]
    gif.loop_count = ref['loop']
    file_ = StringIO()
    gif.save(file_)

    # load resulting gif and compare to testcase
    file_.seek(0)
    reencoded_ref = load_test_gif(file_)
    # TODO: don't compare info for now
    del ref['info']
    del reencoded_ref['info']
    assert ref == reencoded_ref


def test_get_gif_comment():
    # can't test this automatically because it's not exposed by pillow
    gif = GIF(get_test_gif_path('whitepixel.gif'))
    assert gif.comments == ["Created with GIMP"]


def test_get_delays():
    # can't test this automatically because it's not exposed by pillow
    gif = GIF(get_test_gif_path('8x8gradientanim_delay_1s_2s_3s.gif'))
    assert [img.delay_ms for img in gif.images] == [1000, 2000, 3000]


@pytest.mark.parametrize('name', [
    'disposal_bg.gif',
    'disposal_none.gif',
    'disposal_prev.gif',
])
def test_disposal_methods(name):
    # XXX: can't integrate these with other tests because pillow has problems
    gif = GIF(get_test_gif_path(name))

    # XXX for testing until we can make this automatic
    #for i in range(len(gif.images)):
    #    gif.images[0].rgba_data = gif.images[i].rgba_data
    #    gif.save(open('test{}{}.gif'.format(name, i), 'wb'))
