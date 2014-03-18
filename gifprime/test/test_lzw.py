from gifprime import lzw, lzw2


def test_decompress_simple():
    # TODO: fails
    assert ''.join(lzw2.decompress('D\x01', 2)) == '\x00'


def test_compress_simple():
    assert ''.join(lzw.compress('\x00', 2)) == 'D\x01'


def test_decompress_5pixels():
    # TODO: fails with exception inside decompress (not completely sure what the result should be)
    assert ''.join(lzw2.decompress('D\x1e\x05', 2)) == '\x00\x01\x01\x01\x01'


def test_compress_5pixels():
    assert ''.join(lzw.compress('\x00\x01\x01\x01\x01', 2)) == 'D\x1e\x05'
