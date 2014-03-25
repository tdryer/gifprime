import construct
from math import log, ceil, pow


import gifprime.parser


class Image(object):
    """A single image from a GIF."""

    def __init__(self, rgba_data, size, delay_ms):
        self.size = size
        self.rgba_data = rgba_data
        # animation properties:
        self.user_input_flag = False
        # number of milliseconds to show this frame, or 0 if not set
        self.delay_ms = delay_ms


class GIF(object):
    """A GIF image or animation."""

    def __init__(self, filename=None):
        """Create a new GIF or decode one from a file."""
        self.images = []
        self.comments = []
        self.filename = filename
        self.size = (0, 0)
        # number of times to show the animation, or 0 to loop forever
        self.loop_count = 1

        if filename is not None:
            with open(filename, 'rb') as f:
                data_stream = f.read()
            parsed_data = gifprime.parser.gif.parse(data_stream)
            self.size = (
                parsed_data.logical_screen_descriptor.logical_width,
                parsed_data.logical_screen_descriptor.logical_height,
            )

            gct = (parsed_data.gct if
                   parsed_data.logical_screen_descriptor.gct_flag else None)
            # the most recent GCE block since the last image block.
            active_gce = None

            for block in parsed_data.body:
                if 'block_type' not in block:  # it's an image

                    lct = (block.lct if block.image_descriptor.lct_flag
                           else None)

                    # Select the active colour table.
                    if lct is not None:
                        active_colour_table = lct
                        assert False, 'TODO: test this'
                    elif gct is not None:
                        active_colour_table = gct
                    else:
                        raise NotImplementedError, (
                            'TODO: supply a default colour table')

                    # set transparency index
                    if active_gce is not None:
                        trans_index = active_gce.transparent_colour_index
                        delay_ms = active_gce.delay_time * 10
                    else:
                        trans_index = None
                        delay_ms = 0

                    # TODO handle different disposal methods
                    indexes = block.pixels
                    rgba_data = [
                        tuple(active_colour_table[i]) +
                        ((0,) if i == trans_index else (255,))
                        for i in indexes
                    ]
                    image_size = (block.image_descriptor.width,
                                  block.image_descriptor.height)
                    assert self.size == image_size, (
                        'TODO: allow image size smaller than gif size')

                    self.images.append(Image(rgba_data, image_size, delay_ms))

                    # the GCE goes out of scope after being used once
                    active_gce = None

                elif block.block_type == 'gce':
                    active_gce = block
                elif block.block_type == 'comment':
                    self.comments.append(block.comment)
                elif block.block_type == 'application':
                    if (block.app_id == 'NETSCAPE' and
                        block.app_auth_code == '2.0'):
                        contents = construct.Struct(
                            'loop',
                            construct.ULInt8('id'),
                            construct.ULInt16('count'),
                        ).parse(block.app_data)
                        assert contents.id == 1, 'Unknown NETSCAPE extension'
                        self.loop_count = (contents.count + 1
                                           if contents.count != 0 else 0)
                    else:
                        print ('Found unknown app extension: {}'
                               .format((block.app_id, block.app_auth_code)))

    def save(self, file_):
        """Encode a GIF and save it to a file."""
        # TODO: all this does so far is create a 1x1 pixel white image
        colour_table = list(set([(r, g, b) for r, g, b, a in
                                 self.images[0].rgba_data]))
        assert len(colour_table) <= 256, 'TODO: colour quantization'

        # pad colour table to nearest power of two length
        # colour table length must also be at least 2
        colour_table_len = max(2, int(pow(2, ceil(log(len(colour_table), 2)))))
        colour_table += [(0, 0, 0)] * (colour_table_len - len(colour_table))

        gif = gifprime.parser.gif.build(construct.Container(
            magic = 'GIF89a',
            logical_screen_descriptor = construct.Container(
                logical_width = self.size[0],
                logical_height = self.size[1],
                gct_flag = True,
                colour_res = 7,
                sort_flag = True,
                gct_size = int(log(len(colour_table), 2)) - 1,
                bg_col_index = 0,
                pixel_aspect = 0,
            ),
            gct = colour_table,
            body = [
                construct.Container(
                    block_type = 'comment',
                    ext_intro = 0x21,
                    ext_label = 0xFE,
                    comment = 'This is a test.'
                ),
                construct.Container(
                    gce = None,
                    image_descriptor = construct.Container(
                        img_sep = 0x2C,
                        left = 0,
                        top = 0,
                        width = self.size[0],
                        height = self.size[1],
                        lct_flag = False,
                        interlace_flag = False,
                        sort_flag = False,
                        lct_size = 0,
                    ),
                    lct = None,
                    lzw_min = max(2, int(log(len(colour_table), 2))),
                    pixels = [colour_table.index((r, g, b)) for r, g, b, a
                                                 in self.images[0].rgba_data]
                ),
            ],
            trailer = 0x3B,
        ))
        file_.write(gif)
