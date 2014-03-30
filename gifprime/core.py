from math import log, ceil, pow
import construct
import itertools
import numpy
import requests
import scipy.cluster.vq


import gifprime.parser


def flatten(lst):
    """Flatten a list of lists."""
    return list(itertools.chain.from_iterable(lst))


def blit_rgba(source, source_size, pos, dest, dest_size, transparency=True):
    """Blit source onto dest and return the result.

    source and dest are lists of RGBA tuples.

    If transparency is False, blitting a transparent pixel will overwrite the
    pixel under it with transparency.
    """
    window_x = (pos[0], pos[0] + source_size[0])
    window_y = (pos[1], pos[1] + source_size[1])
    res = []
    for y in xrange(dest_size[1]):
        for x in xrange(dest_size[0]):
            source_x = x - pos[0]
            source_y = y - pos[1]
            dest_pix = dest[y * dest_size[0] + x]
            if source_x >= 0 and source_x < source_size[0] and \
                    source_y >= 0 and source_y < source_size[1]:
                source_pix = source[source_y * source_size[0] + source_x]
                if transparency and source_pix[3] != 255:
                    res.append(dest_pix)
                else:
                    res.append(source_pix)
            else:
                res.append(dest_pix)
    return res


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

    @classmethod
    def from_file(cls, filename):
        with open(filename, 'rb') as file_:
            data_stream = file_.read()
        return cls(data_stream, filename)

    @classmethod
    def from_url(cls, url):
        response = requests.get(url)
        assert response.headers['content-type'] == 'image/gif', 'must be a gif'
        return cls(response.content, response.url.rsplit('/', 1)[-1])

    def __init__(self, data_stream=None, filename=None):
        """Create a new GIF or decode one from a file."""
        self.images = []
        self.comment = None
        self.filename = filename
        self.size = (0, 0)
        # number of times to show the animation, or 0 to loop forever
        self.loop_count = 1

        if data_stream is not None:
            parsed_data = gifprime.parser.gif.parse(data_stream)
            lsd = parsed_data.logical_screen_descriptor
            self.size = (lsd.logical_width, lsd.logical_height)

            if lsd.gct_flag:
                gct = parsed_data.gct
                # XXX Modern GIF implementations disregard the spec and use
                # transparency as the background colour. This is significant
                # for the prev and bg disposal methods. The 'correct' code is
                # commented out below:
                # bg_colour = tuple(gct[lsd.bg_col_index]) + (255,)
                bg_colour = (0, 0, 0, 0)
            else:
                gct = None
                # XXX: this spec is not clear on what this should be
                bg_colour = (0, 0, 0, 255)

            # the most recent GCE block since the last image block.
            active_gce = None

            # initialize the previous state
            prev_state = [bg_colour] * (self.size[0] * self.size[1])

            for block in parsed_data.body:
                if 'block_type' not in block:  # it's an image

                    lct = (block.lct if block.image_descriptor.lct_flag
                           else None)

                    # Select the active colour table.
                    if lct is not None:
                        active_colour_table = lct
                    elif gct is not None:
                        active_colour_table = gct
                    else:
                        raise NotImplementedError, (
                            'TODO: supply a default colour table')

                    # set transparency index
                    if active_gce is not None:
                        if active_gce.transparent_colour_flag:
                            trans_index = active_gce.transparent_colour_index
                        else:
                            trans_index = None
                        delay_ms = active_gce.delay_time * 10
                        disposal_method = active_gce.disposal_method
                    else:
                        trans_index = None
                        delay_ms = 0
                        disposal_method = 0

                    indexes = block.pixels
                    rgba_data = [
                        tuple(active_colour_table[i]) +
                        ((0,) if i == trans_index else (255,))
                        for i in indexes
                    ]
                    image_size = (block.image_descriptor.width,
                                  block.image_descriptor.height)
                    image_pos = (block.image_descriptor.left,
                                 block.image_descriptor.top)

                    new_state = blit_rgba(rgba_data, image_size, image_pos,
                                          prev_state, self.size)

                    if disposal_method in [0, 1]:
                        # disposal method is unspecified or none
                        # do not restore the previous frame in any way
                        prev_state = new_state
                    elif disposal_method == 2:
                        # disposal method is background
                        # restore the used area to the background colour
                        fill_rgba = ([bg_colour] *
                                     (image_size[0] * image_size[1]))
                        prev_state = blit_rgba(fill_rgba, image_size,
                                               image_pos, new_state, self.size,
                                               transparency=False)
                    elif disposal_method == 3:
                        # disposal method is previous
                        # restore to previous frame after drawing on it
                        pass # prev_state is unchanged
                    else:
                        raise ValueError('Unknown disposal method: {}'
                                         .format(disposal_method))

                    self.images.append(Image(new_state, image_size, delay_ms))

                    # the GCE goes out of scope after being used once
                    active_gce = None

                elif block.block_type == 'gce':
                    active_gce = block
                elif block.block_type == 'comment':
                    # If there are multiple comment blocks, we ignore all but
                    # the last (this is unspecified behaviour).
                    self.comment = block.comment
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
        all_pixels = flatten(img.rgba_data for img in self.images)
        use_transparency = any(col for col in all_pixels if col[3] != 255)
        transparent_col_index = 0
        if use_transparency:
            # if we need transparency, make index 0 the transparent colour
            colour_table = [(0, 0, 0)]
            num_colours = 255
        else:
            colour_table = []
            num_colours = 256

        colours = list(set((r, g, b) for r, g, b, _ in all_pixels))

        if len(colours) > num_colours:
            colour_array = numpy.array(colours)
            mean_colours, labels = scipy.cluster.vq.kmeans2(colour_array,
                                                            num_colours,
                                                            minit='points')
            colour_table += numpy.round(mean_colours).tolist()
            colour_map = {tuple(pixel): idx
                          for pixel, idx in itertools.izip(colours, labels)}
        else:
            colour_table += colours
            colour_map = {pixel: i for i, pixel in enumerate(colour_table)}

        # pad colour table to nearest power of two length
        # colour table length must also be at least 2
        colour_table_len = max(2, int(pow(2, ceil(log(len(colour_table), 2)))))
        colour_table += [(0, 0, 0)] * (colour_table_len - len(colour_table))

        if self.comment is not None:
            comment_containers = [
                construct.Container(
                    block_type = 'comment',
                    ext_intro = 0x21,
                    ext_label = 0xFE,
                    comment = self.comment,
                )
            ]
        else:
            comment_containers = []

        image_containers = flatten([
            [
                construct.Container(
                    block_type = 'gce',
                    ext_intro = 0x21,
                    ext_label = 0xF9,
                    block_size = 4,
                    disposal_method = 0,
                    user_input_flag = False,
                    transparent_colour_flag = use_transparency,
                    delay_time = int(image.delay_ms / 10),
                    transparent_colour_index = transparent_col_index,
                    terminator = 0,
                ),
                construct.Container(
                    image_descriptor = construct.Container(
                        img_sep = 0x2C,
                        left = 0,
                        top = 0,
                        width = image.size[0],
                        height = image.size[1],
                        lct_flag = False,
                        interlace_flag = False,
                        sort_flag = False,
                        lct_size = 0,
                    ),
                    lct = None,
                    lzw_min = max(2, int(log(len(colour_table), 2))),
                    pixels = [
                        colour_map[(r, g, b)] if a == 255 else 0
                        for r, g, b, a in image.rgba_data
                    ],
                ),
            ] for image in self.images
        ])

        app_ext_containers = []
        # if this gif loops, add the application extension for looping
        if self.loop_count != 1:
            if self.loop_count == 0:
                real_count = 0
            else:
                real_count = self.loop_count - 1
            data = construct.Struct(
                'loop',
                construct.ULInt8('id'),
                construct.ULInt16('count'),
            ).build(construct.Container(id=1, count=real_count))
            app_ext_containers.append(
                construct.Container(
                    block_type = 'application_extension',
                    ext_intro = 0x21,
                    ext_label = 0xFF,
                    block_size = 11,
                    app_id = 'NETSCAPE',
                    app_auth_code = '2.0',
                    app_data = data,
                )
            )

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
            body = comment_containers + image_containers + app_ext_containers,
            trailer = 0x3B,
        ))
        file_.write(gif)
