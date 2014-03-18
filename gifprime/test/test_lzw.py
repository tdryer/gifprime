from gifprime import lzw


def test_decompress_simple():
    assert ''.join(lzw.decompress('D\x01', 2)) == '\x00\x00\x00'


def test_compress_simple():
    # TODO: this fails (uses data from whitepixel gif)
    assert ''.join(lzw.compress('\x00\x00\x00', 2)) == 'D\x01'
