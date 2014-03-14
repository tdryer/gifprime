import gifprime.parser


class GIF(object):

    def __init__(self, filename):
        with open(filename, 'rb') as f:
            data_stream = f.read()
        parsed_data = gifprime.parser.gif.parse(data_stream)
        #print parsed_data
        #assert False

