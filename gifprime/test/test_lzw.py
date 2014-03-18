from gifprime import lzw


def test_decompress_simple():
    assert ''.join(lzw.decompress('D\x01', 2)) == '\x00\x00\x00'


def test_compress_simple():
    # TODO: this fails (uses data from whitepixel gif)
    assert ''.join(lzw.compress('\x00\x00\x00', 2)) == 'D\x01'


def test_decompress_5pixels():
    # TODO: fails with exception inside decompress (not completely sure what the result should be)
    assert ''.join(lzw.decompress('D\x1e\x05', 2)) == '\x00\x01\x01\x01\x01'


def test_compress_5pixels():
    # TODO: not completely sure about the correct output
    assert ''.join(lzw.compress('\x00\x01\x01\x01\x01', 2)) == 'D\x1e\x05'
