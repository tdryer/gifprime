import bitarray

from gifprime import lzw


def test_decompress_simple():
    # TODO: fails
    assert ''.join(lzw.decompress('D\x01', 2)) == '\x00'


def test_compress_simple():
    assert ''.join(lzw.compress('\x00', 2)) == 'D\x01'


def test_decompress_5pixels():
    # TODO: fails with exception inside decompress (not completely sure what the result should be)
    assert ''.join(lzw.decompress('D\x1e\x05', 2)) == '\x00\x01\x01\x01\x01'


def test_compress_5pixels():
    assert ''.join(lzw.compress('\x00\x01\x01\x01\x01', 2)) == 'D\x1e\x05'


def test_CodeStream():
    cs = lzw.CodeStream(bitarray.bitarray('0000110000000100').tobytes())
    assert cs.get(3) == 4
    assert cs.get(4) == 1
    assert cs.get(5) == 8
    assert not cs.empty()
    assert cs.get(4) == 0
    assert cs.empty()
