import os


def readable_size(num_bytes):
    for suffix in ['bytes', 'KB', 'MB', 'GB']:
        if num_bytes < 1024:
            return '{:3.1f} {}'.format(num_bytes, suffix)

        num_bytes /= 1024.0

    return '{:3.1f} {}'.format(num_bytes, 'TB')


def static_path(filename):
    base = os.path.join(os.path.dirname(__file__), 'static')
    return os.path.join(base, filename)
