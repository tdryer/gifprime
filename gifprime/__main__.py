import struct
import ctypes


class GIF(object):

    def __init__(self, filename):
        # signature for the GIF data stream
        self.signature = None
        # GIF version
        self.version = None
        # size of the GIF data stream in bytes
        self.size = None
        # width of the logical screen in pixels
        self.width = None
        # height of the logical screen in pixels
        self.height = None
        # flag indicating the presence of a Global Color Table
        self.gct_flag = None
        # number of bits per primary color available to the original image,
        # minus 1
        self.colour_res = None
        # indicates whether the Global Color Table is sorted
        self.sort_flag = None
        # if the Global Color Table Flag is set to 1, the value in this field
        # is used to calculate the number of bytes contained in the Global
        # Color Table
        self.gct_size = None
        # index into the Global Color Table for the Background Color
        self.bg_col_index = None
        # factor used to compute an approximation of the aspect ratio of the
        # pixel in the original image
        self.pixel_aspect = None
        # Global Color Table used by images without a Local Color Table
        self.gct = None
        # any number of textual comments
        self.comments = None

        with open(filename, 'rb') as f:
            data_stream = f.read()
        self.size = len(data_stream)
        self.signature, self.version = struct.unpack('<3s3s', data_stream[:6])
        if self.signature != 'GIF':
            raise ValueError("'{}' is invalid GIF signature.".format(self.signature))
        elif self.version != '89a':
            raise ValueError("'{}' is unsupported GIF version.".format(self.version))

        #self.logical_screen_width, self.logical_screen_height
        lsd = struct.unpack('<HHBBB', data_stream[6:6+7])
        self.width, self.height, packed, self.bg_col_index, self.pixel_aspect = lsd

        class BitField(ctypes.Structure):
            _fields_ = [
                ("gct_flag", ctypes.c_bool, 1),
                ("colour_res", ctypes.c_int, 3),
                ("sort_flag", ctypes.c_bool, 1),
                ("gct_size", ctypes.c_int, 3),
            ]
        bitfield = BitField(packed)
        self.gct_flag = bitfield.gct_flag
        self.colour_res = bitfield.colour_res
        self.sort_flag = bitfield.sort_flag
        self.gct_size = bitfield.gct_size

        # parse GCT
        self.gct = []
        if self.gct_flag:
            gct_size_bytes = 3 * pow(2, self.gct_size + 1)
            cursor = 13
            for _ in range(gct_size_bytes / 3):
                r, g, b = struct.unpack('<BBB', data_stream[cursor:cursor + 3])
                self.gct.append((r, g, b))
                cursor += 3

        # parse comment extension
        ext_intro, comm_label, comm_size = struct.unpack('<BBB', data_stream[cursor:cursor + 3])
        assert ext_intro == 33
        assert comm_label == 254
        print 'comment length is {}'.format(comm_size)
        cursor += 3

        comment_txt, terminator = struct.unpack(
            '<{}sB'.format(comm_size), data_stream[cursor:cursor + comm_size + 1]
        )
        cursor += comm_size + 1
        assert terminator == 0
        self.comments = []
        self.comments.append(comment_txt)

        # parse image descriptor
        img_desc = struct.unpack('<BHHHHB', data_stream[cursor:cursor + 10])
        cursor += 10
        img_sep, img_left, img_top, img_width, img_height, packed = img_desc
        assert img_sep == 44

        print 'img left, top: {}, {}'.format(img_left, img_top)
        print 'img width, height: {}, {}'.format(img_width, img_height)
        # TODO parse packed data
        class ImgDescBitField(ctypes.Structure):
            _fields_ = [
                ("lct_flag", ctypes.c_bool, 1),
                ("interlace_flag", ctypes.c_bool, 1),
                ("sort_flag", ctypes.c_bool, 1),
                ("reserved", ctypes.c_int, 2),
                ("lct_size", ctypes.c_int, 3),
            ]
        bitfield = ImgDescBitField(packed)
        print (bitfield.lct_flag, bitfield.interlace_flag, bitfield.sort_flag,
               bitfield.reserved, bitfield.lct_size)

        # parse image data
        img_data = struct.unpack('<BB', data_stream[cursor:cursor + 2])
        cursor += 2
        min_code_size, block_size = img_data
        print 'min code size: {}'.format(min_code_size)
        print 'block_size: {}'.format(block_size)
        lzw_data = struct.unpack('<{}sB'.format(block_size),
                                 data_stream[cursor:cursor + block_size + 1])
        cursor += block_size + 1
        lzw_img_data, terminator = lzw_data
        assert terminator == 0
        print 'lzw image data: {}'.format(lzw_img_data)

        # TODO: parse trailer
        trailer = struct.unpack('<B', data_stream[cursor:cursor + 1])
        assert trailer[0] == 59
