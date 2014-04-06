import array


class RGBAArray(object):
    """Compact array of RGBA tuples."""

    def __init__(self, rgba_list=None):
        self._array = array.array('B')
        if rgba_list is not None:
            self.extend(rgba_list)

    def __getitem__(self, key):
        pos = key * 4
        return tuple(self._array[pos:pos+4])

    def __iter__(self):
        return iter(self[i] for i in xrange(len(self)))

    def __len__(self):
        return len(self._array) / 4

    def append(self, rgba):
        self._array.extend(rgba)

    def extend(self, rgba_list):
        # since array.array doesn't support generators
        for rgba in rgba_list:
            self._array.extend(rgba)


