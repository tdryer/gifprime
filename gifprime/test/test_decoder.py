"""Tests for the GIF encoder and decoder."""

import pytest
from subprocess import check_output
import json
import construct
import tempfile


from gifprime.core import GIF, Image


def get_test_gif_path(name):
    """Return the path to the test gif with the given name."""
    return 'gifprime/test/data/{}'.format(name)


def load_reference_gif(filename):
    """Load a GIF that we can use as a reference for testing.

    exiftool and ImageMagick are used here as reference decoders.
    """
    run = lambda cmd, *args: check_output(cmd.format(*args).split(' '))

    # get comment, size, loop count from exiftool
    exiftool_json = json.loads(run('exiftool -j {}', filename))[0]
    comment = exiftool_json.get('Comment', None)
    size = (exiftool_json['ImageWidth'], exiftool_json['ImageHeight'])
    loop = exiftool_json.get('AnimationIterations', 0)
    loop = 0 if loop == 'Infinite' else loop + 1

    # get delay for each frame from ImageMagick
    delays = run('identify -format %T, {}', filename)
    delays = [int(d) * 10 for d in delays.split(',')[:-1]]

    # Work around bugs in ImageMagick. Animations need to be coalesced so we
    # can extract frames with disposal methods applied correctly. But for still
    # images, do not coalesce because it can corrupt the image.
    if exiftool_json.get('FrameCount', 1) > 1:
        tmp_filename = '{}.coalesced.gif'.format(filename)
        run('convert {} -coalesce {}', filename, tmp_filename)
    else:
        tmp_filename = filename

    images = []

    for i in xrange(len(delays)):

        # get the coalesced frame data as RGBA using ImageMagick
        rgba = run('convert {}[{}] rgba:-', tmp_filename, i)
        rgba_tuples = [tuple(col) for col in construct.Array(
            lambda ctx: len(rgba) / 4,
            construct.Array(4, construct.ULInt8('col')),
        ).parse(rgba)]
        images.append({
            'data': rgba_tuples,
            'delay': delays[i],
        })

    return {
        'size': size,
        'loop': loop,
        'images': images,
        'comment': comment,
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
    'disposal_bg.gif',
    'disposal_none.gif',
    'disposal_prev.gif',
    'transparent_blit.gif',
    'requires_clear_code.gif',
])
def test_gif_decode(name):
    """Decode GIF and compare it to reference decoding."""
    ref = load_reference_gif(get_test_gif_path(name))
    gif = GIF.from_file(get_test_gif_path(name))

    assert gif.filename == get_test_gif_path(name)
    assert gif.size == ref['size']
    assert len(gif.images) == len(ref['images'])
    gif_data = [d.rgba_data for d in gif.images]
    ref_data = [i['data'] for i in ref['images']]
    assert len(gif_data) == len(ref_data)
    for gif_frame, ref_frame in zip(gif_data, ref_data):
        assert gif_frame == ref_frame
    assert gif.loop_count == ref['loop']
    delays = [img.delay_ms for img in gif.images]
    ref_delays = [img['delay'] for img in ref['images']]
    assert delays == ref_delays
    assert gif.comment == ref['comment']


@pytest.mark.parametrize('name', [
    'whitepixel.gif',
    '8x8gradient.gif',
    'transparentcircle.gif',
    '8x8gradientanim.gif',
    '8x8gradientanim_loop_twice.gif',
    'requires_clear_code.gif',
])
def test_gif_encode(name):
    """Encode a GIF, load it again, and verify it."""
    # load GIF using reference decoder
    ref = load_reference_gif(get_test_gif_path(name))

    # encode image as gif
    gif = GIF()
    gif.size = ref['size']
    gif.images = [Image(i['data'], ref['size'], i['delay'])
                  for i in ref['images']]
    gif.loop_count = ref['loop']
    gif.comment = ref['comment']

    with tempfile.NamedTemporaryFile() as encoded_file:
        gif.save(encoded_file)
        encoded_file.flush()

        # load resulting gif and compare to reference
        reencoded_ref = load_reference_gif(encoded_file.name)
        assert ref == reencoded_ref
