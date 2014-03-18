"""LZW Decompressor."""


import bitstring


class CodeStream(object):
    """Integer code unpacker for LZW compressed data."""

    def __init__(self, data):
        self.bits = bitstring.BitArray('0x' + data[::-1].encode('hex'))

    def get(self, size):
        """Returns the next integer code using size_of(num)-bits."""
        code = self.bits[-size:].uint
        del self.bits[-size:]

        # If there aren't enough bits, then it's just padding.
        if len(self.bits) < size:
            self.bits.clear()

        return code

    def empty(self):
        """Returns True iff. there are no bits left."""
        return not len(self.bits)


# TODO: possibly useful for testing without worrying about unpacking
class DummyCodeStream(object):

    def __init__(self, data):
        self.data = data
        self.i = 0

    def get(self, size):
        d = self.data[self.i]
        self.i += 1
        return d

    def empty(self):
        return self.i >= len(self.data)


def get_code_table(min_code):
    table = range(pow(2, min_code) + 2)
    table = [(chr(i),) for i in table]
    return table, len(table) - 2, len(table) - 1

def print_code_table(code_table, clear_code, end_code):
    for code, colour in enumerate(code_table):
        if colour == (clear_code,):
            colour = 'CLEAR'
        elif colour == (end_code,):
            colour = 'END'
        print '{} | {}'.format(code, colour)

def decompress(data, min_code_size, cs=CodeStream):
    code_stream = cs(data)
    code_table, clear_code, end_code = get_code_table(min_code_size)

    print_code_table(code_table, clear_code, end_code)

    code_size = min_code_size + 1

    assert code_stream.get(code_size) == clear_code, 'first code should be CLEAR'

    prev_code = code_stream.get(code_size)
    for i in code_table[prev_code]:
        yield i

    while True:
        code = code_stream.get(code_size)
        print 'code = {}'.format(code)
        if code == end_code:
            # the code stream may not be empty at this point because of padding
            break
        elif code == clear_code:
            # TODO: only occurs if code size hits the limit, so need test for this
            assert False
        elif code_stream.empty():
            raise ValueError('Reached end of stream without END code')
        elif code in range(0, len(code_table)):
            for i in code_table[code]:
                yield i
            k = code_table[code][0]
            code_table.append(code_table[prev_code] + (k,))
        else:
            k = code_table[prev_code][0]
            for i in code_table[prev_code] + (k,):
                yield i
            code_table.append(code_table[prev_code] + (k,))

        if len(code_table) - 1 == (2 ** code_size) - 1:
            code_size += 1

        prev_code = code
