"""Provides LZW decompression."""

import math

import bitstring


def _make_lzw_table(lzw_min):
    """Generates the initial LZW dictionary."""
    next_code = 2 ** lzw_min
    codes = {i: chr(i) for i in xrange(next_code)}
    clear_code = codes[next_code] = next_code
    end_code = codes[next_code + 1] = next_code + 1

    return clear_code, end_code, next_code + 2, codes


class CodeUnpacker(object):
    """Integer code unpacker for LZW compressed data."""

    def __init__(self, data):
        self.bits = bitstring.BitArray('0x' + data[::-1].encode('hex'))

    @staticmethod
    def size_of(num):
        """Computes the number of bits required to represent an integer."""
        return int(math.ceil(math.log(num, 2)))

    def get(self, num):
        """Returns the next integer code using size_of(num)-bits."""
        size = self.size_of(num)
        code = self.bits[-size:].uint
        del self.bits[-size:]
        return code

    def empty(self):
        """Returns True iff. there are no bits left."""
        return not len(self.bits)


def decompress(data, lzw_min):
    """Decompresses an LZW data stream."""
    clear_code, end_code, next_code, decodes = _make_lzw_table(lzw_min)
    unpacker = CodeUnpacker(data)

    prev = None

    while not unpacker.empty():
        code = unpacker.get(next_code - 1)

        # CLEAR CODE
        if code == clear_code:
            clear_code, end_code, next_code, decodes = _make_lzw_table(lzw_min)
            continue

        # END OF INFORMATION CODE
        if code == end_code:
            # XXX: Should probably raise an exception if we get this and there
            #      is still data left to parse.
            continue

        # Special case for getting the first non-CLEAR CODE
        if prev is None:
            prev = decodes[code]
            yield prev
            continue

        # Usual case
        if code in decodes:
            yield decodes[code]
        else:
            yield prev + decodes[code][0]

        decodes[next_code] = prev + decodes[code][0]
        next_code += 1
        prev = decodes[code]
