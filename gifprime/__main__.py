import gifprime.parser


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
            self.comments = [block.comment for block in parsed_data.body
                             if 'comment' in block]
            self.size = (
                parsed_data.logical_screen_descriptor.logical_width,
                parsed_data.logical_screen_descriptor.logical_height,
            )

    def save(self, filename):
        """Encode a GIF and save it to a file."""
        raise NotImplementedError
