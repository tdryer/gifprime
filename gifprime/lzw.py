"""Provides LZW compression and decompression."""

import math
import bitarray
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
        """Returns the # bits required to represent the largest code so far."""
        return int(math.floor(math.log(self.next_code - 1, 2)) + 1)

    @property
    def next_code_size(self):
        """Returns the # bits required to represent the next code."""
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

    def add(self, key):
        """Maps key to the next largest code."""
        self.codes[key] = self.next_code
        self.next_code += 1


class CodeStream(object):
    """Unpacker for code stream with variable bit lengths.

    The code stream is assumed to be little-endian.
    """

    def __init__(self, data):
        self.bits = bitarray.bitarray(endian='little')
        self.bits.frombytes(data)
        self.pos = 0

    def get(self, size):
        """Returns the next integer code using size bits."""
        code = self.bitlist_to_int(self.bits[self.pos:self.pos + size])
        self.pos += size
        return code

    @staticmethod
    def bitlist_to_int(bitlist):
        """Convert list of bits to integer."""
        out = 0
        for bit in reversed(bitlist):
            out = (out << 1) | bit
        return out

    def empty(self):
        """Return true if the end of the code stream has been reached."""
        return self.pos >= len(self.bits)


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


def decompress(data, lzw_min, max_code_size=12):
    """Generate decompressed data using LZW."""
    table = LZWDecompressionTable(lzw_min)
    stream = CodeStream(data)

    prev = None
    while True:
        code = stream.get(min(table.next_code_size, max_code_size))

        if code == table.end_code:
            break
        elif code == table.clear_code:
            table.reinitialize()
            prev = None
            continue
        elif stream.empty():
            raise ValueError('Reached end of stream without END code')
        elif code in table:
            yield table.get(code)
            if prev is not None:
                table.add(table.get(prev) + table.get(code)[0])
        elif prev is None:
            raise ValueError('First code after a reset must be in the table')
        else:
            yield table.get(prev) + table.get(prev)[0]
            table.add(table.get(prev) + table.get(prev)[0])

        prev = code
