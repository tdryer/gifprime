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

        if filename != None:
            with open(filename, 'rb') as f:
                data_stream = f.read()
            parsed_data = gifprime.parser.gif.parse(data_stream)
            self.comments = [parsed_data.comment_extension.comment]
            #print parsed_data
            #assert False

    def save(self, filename):
        """Encode a GIF and save it to a file."""
        raise NotImplementedError
