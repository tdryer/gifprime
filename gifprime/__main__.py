import gifprime.parser


def decompress_lzw(data):
    return None # TODO


class Image(object):
    """A single image from a GIF."""

    def __init__(self):
        self.image_data = None
        self.user_input_flag = False
        self.delay_time = 0
        # TODO: likely we can abstract these away:
        self.transparent_colour = None
        self.disposal_method = None


class GIF(object):
    """A GIF image or animation."""

    def __init__(self, filename=None):
        """Create a new GIF or decode one from a file."""
        self.images = []
        self.comments = []
        self.filename = filename
        self.size = (0, 0)

        if filename is not None:
            with open(filename, 'rb') as f:
                data_stream = f.read()
            parsed_data = gifprime.parser.gif.parse(data_stream)
            self.size = (
                parsed_data.logical_screen_descriptor.logical_width,
                parsed_data.logical_screen_descriptor.logical_height,
            )

            for block in parsed_data.body:
                if block.block_type == 'image':
                    self.images.append(None)
                    lzw_data = ''.join(dsb.data_values for dsb
                                       in block.data_subblocks)
                    # TODO Might want to make this a Construct adapter so we
                    # can also parse the decompressed data.
                    image_data = decompress_lzw(lzw_data)
                elif block.block_type == 'comment_extension':
                    self.comments.append(block.comment)
                elif block.block_type == 'application_extension':
                    data = ''.join(dsb.data_values for dsb
                                   in block.data_subblocks)
                    print ("Found app extension for '{}' containing '{}'"
                           .format(block.app_id, data))

    def save(self, filename):
        """Encode a GIF and save it to a file."""
        raise NotImplementedError
