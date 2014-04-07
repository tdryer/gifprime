from math import log, ceil
import construct
import itertools
import requests
import struct


import gifprime.parser
from gifprime.quantize import quantize
from gifprime.util import LazyList
from gifprime import lzw


def flatten(lst):
    """Flatten a list of lists."""
    return list(itertools.chain.from_iterable(lst))


def blit_rgba(source, source_size, pos, dest, dest_size, transparency=True):
    """Blit source onto dest and return the result.

    source and dest are lists of RGBA tuples.

    If transparency is False, blitting a transparent pixel will overwrite the
    pixel under it with transparency.

    This is an attempt at an optimized implementation. The conditionals are
    ordered to take advantage of short-circuiting.
    """
    # if the source completely covers the destination, we don't have to check
    # each time whether the current pixel is inside the source
    full_coverage = pos == (0, 0) and source_size == dest_size

    return [
        # use source pixel
        source[(y - pos[1]) * source_size[0] + (x - pos[0])]
        # if ((full_coverage or pos_in_source) and not
        #     (transp and source_is_transp))
        if ((full_coverage or
             (x >= pos[0] and y >= pos[1] and
              x < pos[0] + source_size[0] and y < pos[1] + source_size[1]))
            and not (
                transparency and
                source[(y - pos[1]) * source_size[0] + (x - pos[0])][3] != 255
            ))
        # else use dest pixel
        else dest[y * dest_size[0] + x]
        # for every (x, y) position
        for y in xrange(dest_size[1]) for x in xrange(dest_size[0])
    ]


class Image(object):
    """A single image from a GIF."""

    def __init__(self, rgba_data, size, delay_ms):
        self.size = size
        self.rgba_data = rgba_data
        # number of milliseconds to show this frame, or 0 if not set
        self.delay_ms = delay_ms


class GIF(object):
    """A GIF image or animation."""

    @classmethod
    def from_file(cls, filename, **kwargs):
        """Load GIF from the given filename."""
        with open(filename, 'rb') as stream:
            return cls(stream, filename=filename, **kwargs)

    @classmethod
    def from_url(cls, url, **kwargs):
        """Load GIF from the given URL."""
        res = requests.get(url, stream=True)
        if res.headers['content-type'] != 'image/gif':
            raise ValueError('Content type is not image/gif: {}'.format(url))

        # XXX: Apparently reading 0 bytes causes some operating systems to
        #      close the file descriptor. We are not sure why Construct ever
        #      has to read 0 bytes but this monkey-patched socket prevents it
        #      from doing this.
        orig_read = res.raw.read
        res.raw.read = lambda c: '' if not c else orig_read(c)

        return cls(res.raw, res.url.rsplit('/', 1)[-1], **kwargs)

    def __init__(self, stream=None, filename=None, force_deinterlace=None):
        """Create a new GIF or decode one from a file-like object.

        filename is only used to optionally set the name of the file the GIF
        was loaded from.
        """
        self.images = []
        self.comment = None
        self.filename = filename
        self.size = (0, 0)
        # number of times to show the animation, or 0 to loop forever
        self.loop_count = 1

        if stream is not None:
            parsed_data = gifprime.parser.gif.parse_stream(stream)
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

            def generate_images():
                # the most recent GCE block since the last image block.
                active_gce = None

                # initialize the previous state
                prev_state = [bg_colour] * (self.size[0] * self.size[1])

                for block in parsed_data.body:
                    if 'block_type' not in block:  # it's just the terminator
                        pass
                    elif block.block_type == 'image':

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

                        # if not specified, deinterlace the images only if necessary
                        if force_deinterlace is None:
                            deinterlace = block.image_descriptor.interlace_flag
                        else:
                            deinterlace = force_deinterlace

                        # get the decompressed colour indices
                        indices_bytes = ''.join(lzw.decompress(
                            block.compressed_indices, block.lzw_min))
                        indices = struct.unpack('{}B'.format(len(indices_bytes)),
                                                indices_bytes)

                        # de-interlace the colour indices if necessary
                        if deinterlace:
                            indices = self._de_interlace(
                                indices,
                                block.image_descriptor.height,
                                block.image_descriptor.width,
                            )

                        # interpret colour indices
                        rgba_data = [
                            tuple(active_colour_table[i]) +
                            ((0,) if i == trans_index else (255,))
                            for i in indices
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

                        yield Image(new_state, image_size, delay_ms)

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
                    else:
                        print ('Found unknown extension block: {}'
                               .format(hex(block.ext_label)))

            num_images = len([block for block in parsed_data.body
                              if getattr(block, 'block_type', None) == 'image'])
            self.images = LazyList(generate_images(), num_images)

        self.compressed_size = stream.tell() if stream is not None else 0
        self.uncompressed_size = 1.0

    @staticmethod
    def _de_interlace(indices, height, width):
        rows = itertools.chain(
            xrange(0, height, 8),
            xrange(4, height, 8),
            xrange(2, height, 4),
            xrange(1, height, 2),
        )
        ordered = sorted(((row, i) for i, row in enumerate(rows)),
                         key=lambda e: e[0])

        for _, row in ordered:
            for index in indices[row * width:(row + 1) * width]:
                yield index

    def save(self, stream):
        """Encode GIF to a file-like object."""
        # create one list of pixels and alpha mask for all images
        alpha_mask = flatten([a != 255 for r, g, b, a in img.rgba_data]
                             for img in self.images)
        rgb = flatten([(r, g, b) for r, g, b, a in img.rgba_data]
                      for img in self.images)

        # if there is any alpha, need to reverse space for a transparent colour
        use_transparency = any(alpha_mask)
        max_colours = 255 if use_transparency else 256

        # quantize to get colour table and map
        colour_table, colour_map = quantize(rgb, max_colours)

        # add transparent colour to the table if necessary
        if use_transparency:
            transparent_col_index = len(colour_table)
            colour_table.append((0, 0, 0))
        else:
            transparent_col_index = 0

        # pad colour table to nearest power of two length
        # colour table length must also be at least 2
        colour_table_len = max(2, int(pow(2, ceil(log(len(colour_table), 2)))))
        colour_table += [(0, 0, 0)] * (colour_table_len - len(colour_table))

        if self.comment is not None:
            comment_containers = [
                construct.Container(
                    block_type = 'comment',
                    block_start = 0x21,
                    ext_label = 0xFE,
                    comment = self.comment,
                )
            ]
        else:
            comment_containers = []

        lzw_min = max(2, int(log(len(colour_table), 2)))

        image_containers = flatten([
            [
                construct.Container(
                    block_type = 'gce',
                    block_start = 0x21,
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
                    block_type = 'image',
                    block_start = 0x2C,
                    image_descriptor = construct.Container(
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
                    lzw_min = lzw_min,
                    compressed_indices = lzw.compress(''.join(
                        chr(colour_map[(r, g, b)]) if a == 255
                        else chr(transparent_col_index)
                        for r, g, b, a in image.rgba_data
                    ), lzw_min),
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
                    block_start = 0x21,
                    ext_label = 0xFF,
                    block_size = 11,
                    app_id = 'NETSCAPE',
                    app_auth_code = '2.0',
                    app_data = data,
                )
            )

        trailer = [construct.Container(block_start = 0x3B,
                                       terminator = 'terminator')]

        gif = gifprime.parser.gif.build_stream(construct.Container(
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
            body = (comment_containers + image_containers + app_ext_containers
                    + trailer),
        ), stream)
