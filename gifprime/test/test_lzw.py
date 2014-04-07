"""Tests for LZW compression and decompression."""

import bitarray

from gifprime import lzw


def test_decompress_simple():
    assert ''.join(lzw.decompress('D\x01', 2)) == '\x00'


def test_compress_simple():
    assert ''.join(lzw.compress('\x00', 2)) == 'D\x01'


def test_decompress_5pixels():
    assert ''.join(lzw.decompress('D\x1e\x05', 2)) == '\x00\x01\x01\x01\x01'


def test_compress_5pixels():
    assert ''.join(lzw.compress('\x00\x01\x01\x01\x01', 2)) == 'D\x1e\x05'
