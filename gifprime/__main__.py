import gifprime.parser


class Image(object):
    """A single image from a GIF."""

    def __init__(self, rgba_data, size):
        self.size = size
        self.rgba_data = rgba_data
        # animation properties:
        self.user_input_flag = False
        self.delay_time = 0


class GIF(object):
    """A GIF image or animation."""

    def __init__(self, filename=None):
        """Create a new GIF or decode one from a file."""
        self.images = []
        self.comments = []
        self.filename = filename
        self.size = (0, 0)
        self.loop_animation = False # TODO: set via the netscape extension

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
                    if block.gce is not None:
                        trans_index = block.gce.transparent_colour_index
                    else:
                        trans_index = None

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

                    self.images.append(Image(rgba_data, image_size))

                elif block.block_type == 'comment':
                    self.comments.append(block.comment)
                elif block.block_type == 'application':
                    print ("Found app extension for '{}' containing '{}'"
                           .format(block.app_id, block.app_data))

    def save(self, filename):
        """Encode a GIF and save it to a file."""
        raise NotImplementedError
