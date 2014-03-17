import gifprime.parser


class Image(object):
    """A single image from a GIF."""

    def __init__(self, image_data):
        self.image_data = image_data
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

            # XXX: LOL!
            height, width = self.size[::-1]

            for block in parsed_data.body:
                if 'block_type' not in block:  # it's an image
                    # TODO: Map index to RGB value.
                    image_data = [[block.pixels[(i * width) + j]
                                  for j in xrange(width)]
                                  for i in xrange(height)]
                    self.images.append(Image(image_data))
                elif block.block_type == 'comment':
                    self.comments.append(block.comment)
                elif block.block_type == 'application':
                    print ("Found app extension for '{}' containing '{}'"
                           .format(block.app_id, block.app_data))

    def save(self, filename):
        """Encode a GIF and save it to a file."""
        raise NotImplementedError
