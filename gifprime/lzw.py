"""Provides LZW compression and decompression."""

import math

import bitstring

__all__ = ['compress', 'decompress']


class LZWDecompressionTable(object):
    """LZW Decompression Code Table"""

    def __init__(self, lzw_min):
        self.lzw_min = lzw_min
        self.reinitialize()

    def reinitialize(self):
        """Re-initialize the code table.

        Should only be called (again) when you encounter a CLEAR CODE.
        """
        next_code = 2 ** self.lzw_min
        self.codes = self._make_codes(next_code)
        self.clear_code = self.codes[next_code] = next_code
        self.end_code = self.codes[next_code + 1] = next_code + 1
        self.next_code = next_code + 2

    def _make_codes(self, next_code):
        return {i: chr(i) for i in xrange(next_code)}

    def __contains__(self, key):
        return key in self.codes

    def show(self):
        for key in sorted(self.codes):
            print key, '|', repr(self.codes[key])

    @property
    def code_size(self):
        """Returns the # bits required to represent the largest code."""
        return int(math.floor(math.log(self.next_code, 2)) + 1)

    def get(self, key):
        """Returns the code associated with key."""
        return self.codes[key]

    def add(self, value):
        """Maps the next largest code to value."""
        self.codes[self.next_code] = value
        self.next_code += 1


class LZWCompressionTable(LZWDecompressionTable):
    """LZW Compression Code Table"""

    def _make_codes(self, next_code):
        return {chr(i): i for i in xrange(next_code)}

    @property
    def code_size(self):
        """Returns the # bits required to represent the largest code."""
        return int(math.floor(math.log(self.next_code - 1, 2)) + 1)

    def add(self, key):
        """Maps key to the next largest code."""
        self.codes[key] = self.next_code
        self.next_code += 1


class CodeStream(object):
    """Integer code unpacker for LZW compressed data."""

    def __init__(self, data):
        self.bits = bitstring.BitArray('0x' + data[::-1].encode('hex'))
        self.end = len(self.bits)

    def get(self, size):
        """Returns the next integer code using size_of(num)-bits."""
        code = self.bits[self.end - size:self.end].uint
        self.end -= size

        # If there aren't enough bits, then it's just padding.
        if self.end < size:
            self.bits.clear()

        return code

    def empty(self):
        """Returns True iff. there are no bits left."""
        return not len(self.bits)


def compress(data, lzw_min):
    """Generate compressed data using LZW."""
    table = LZWCompressionTable(lzw_min)

    def _compress():
        # Always emit a CLEAR CODE first
        yield table.get(table.clear_code)

        prev = ''
        for char in data:
            if prev + char in table:
                prev += char
            else:
                yield table.get(prev)
                table.add(prev + char)
                prev = char

        if prev:
            yield table.get(prev)

        # Always emit an END OF INFORMATION CODE last
        yield table.get(table.end_code)

    # Pack variably-sized codes into bytes
    remainder = bitstring.BitArray()
    for code in _compress():
        size = table.code_size
        remainder.prepend(bitstring.BitArray(uint=code, length=size))

    # TODO: Maybe there's a nice way to incorporate this with the previous
    #       loop.
    while len(remainder) > 0:
        yield chr(remainder[-8:].uint)
        del remainder[-8:]


def decompress(data, lzw_min):
    """Generate decompressed data using LZW."""
    table = LZWDecompressionTable(lzw_min)
    stream = CodeStream(data)

    # First thing we get should be a CLEAR code
    assert stream.get(table.code_size) == table.clear_code

    prev = stream.get(table.code_size)
    yield table.get(prev)

    while True:
        code = stream.get(table.code_size)

        if code == table.end_code:
            break
        elif code == table.clear_code:
            table.reinitialize()
            prev = stream.get(table.code_size)
            yield table.get(prev)
            continue
        elif stream.empty():
            raise ValueError('Reached end of stream without END code')
        elif code in table:
            yield table.get(code)
            table.add(table.get(prev) + table.get(code)[0])
        else:
            yield table.get(prev) + table.get(prev)[0]
            table.add(table.get(prev) + table.get(prev)[0])

        prev = code
