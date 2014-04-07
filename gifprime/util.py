"""Utility functions that didn't fit anywhere else."""


import os


def readable_size(num_bytes):
    """Return readable string for num_bytes."""
    for suffix in ['bytes', 'KB', 'MB', 'GB']:
        if num_bytes < 1024:
            return '{:3.1f} {}'.format(num_bytes, suffix)

        num_bytes /= 1024.0

    return '{:3.1f} {}'.format(num_bytes, 'TB')


def static_path(filename):
    """Return path to filename in the static assets directory."""
    base = os.path.join(os.path.dirname(__file__), 'static')
    return os.path.join(base, filename)


class LazyList(object):
    """A lazily-loaded list that is built from an iterator."""

    def __init__(self, iterator, size):
        self._values = []
        self._iterator = iterator
        self._max_size = size
        self._consumed = False

    def __len__(self):
        if self._consumed:
            return len(self._values)
        else:
            return self._max_size

    def __getitem__(self, index):
        if self._consumed:
            return self._values[index]
        else:
            if index >= self._max_size:
                raise IndexError('{} is out of range'.format(index))

            while len(self._values) <= index:
                self._values.append(next(self._iterator))

            if len(self._values) == self._max_size:
                self._consume_remaining()

            return self._values[index]

    def __delitem__(self, index):
        if not self._consumed:
            self._consume_remaining()

        del self._values[index]

    def __iter__(self):
        for i in xrange(len(self)):
            yield self[i]

    def _consume_remaining(self):
        self._consumed = True
        list(self)
        try:
            next(self._iterator)
        except StopIteration:
            pass

    def append(self, item):
        if not self._consumed:
            self._consume_remaining()

        self._values.append(item)
