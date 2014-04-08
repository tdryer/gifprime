"""Main entry point for gifprime."""

from PIL import Image as PILImage
from argparse import ArgumentParser
from contextlib import contextmanager
import itertools
import logging
import os
import praw
import random
import requests
import time

from gifprime.core import GIF, Image
from gifprime.util import readable_size
from gifprime.viewer import GIFViewer

LOG_LEVELS = {
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'none': logging.CRITICAL,
}

logger = logging.getLogger(__name__)


@contextmanager
def measure_time(label):
    """Context manager for measuring execution time."""
    logger.debug('starting %s...', label)
    start_sec = time.time()
    start_clock = time.clock()
    yield
    elapsed_sec = time.time() - start_sec
    elapsed_clock = time.clock() - start_clock
    logger.debug('... %s complete: %.3f seconds, %.3f cpu time',
                 label, elapsed_sec, elapsed_clock)


def parse_args():
    """Parse arguments and start the program."""
    parser = ArgumentParser('gifprime')
    parser.add_argument('--log-level', default='none', choices=LOG_LEVELS,
                        help='logging level')
    subparser = parser.add_subparsers()

    # Encoder
    encoder = subparser.add_parser('encode', help='create a gif')
    encoder.add_argument('images', nargs='+', help='image frame for gif')
    encoder.add_argument('--output', '-o', help='output filename')
    encoder.add_argument('--delay', '-d', default=1000, type=int,
                         help='frame delay in ms')
    encoder.add_argument('--loop-count', '-l', default=0, type=int,
                         help='0 for infinite (default)')
    encoder.set_defaults(command='encode')

    # Decoder
    decoder = subparser.add_parser('decode', help='view a gif')
    decoder.add_argument('filename')
    decoder.add_argument('--deinterlace', '-d', help='force deinterlacing',
                         choices=['auto', 'on', 'off'], default='auto')
    decoder.set_defaults(command='decode')

    # Reddit Decoder
    reddit = subparser.add_parser('reddit', help='get a gif from reddit')
    reddit.add_argument('--subreddit', '-s', default='gifs')
    reddit.add_argument('--retries', '-r', type=int, default=10,
                        help='number of reddit submissions to try')
    reddit.set_defaults(command='reddit')

    return parser.parse_args()


def run_encoder(args):
    """Encode new GIF and open it in the viewer."""
    if args.output is None:
        raise ValueError("Output argument is required")

    gif = GIF()

    for filepath in args.images:
        image = PILImage.open(filepath).convert('RGBA')
        rgba = image.tobytes()
        rgba_data = zip(*[(ord(c) for c in rgba)] * 4)
        gif.images.append(Image(rgba_data, image.size, args.delay))

    gif.size = image.size
    gif.loop_count = args.loop_count

    with open(args.output, 'wb') as file_:
        with measure_time('encode'):
            gif.save(file_)

    return decode(args.output)


def run_decoder(args):
    """Decode GIF by opening it with the viewer."""
    force_deinterlace = (None if args.deinterlace == 'auto'
                         else args.deinterlace == 'on')
    return decode(args.filename, force_deinterlace=force_deinterlace)


def run_reddit(args):
    """Grab a random GIF from reddit."""
    client = praw.Reddit(user_agent='gifprime')
    subreddit = client.get_subreddit(args.subreddit)

    posts = list(itertools.islice(subreddit.search('url:.gif$'), args.retries))
    random.shuffle(posts)

    for post in posts:
        try:
            response = requests.head(post.url)
        except requests.ConnectionError:
            continue

        if (response.status_code == 200
                and response.headers['content-type'] == 'image/gif'):
            num_bytes = int(response.headers['content-length'])
            logger.info('Found GIF: "%s" - %s - %s',
                        post.title,
                        readable_size(num_bytes),
                        post.url)
            return decode(post.url)
    raise ValueError('Unable to find GIF on reddit')


def decode(uri, benchmark=False, force_deinterlace=None):
    """Given a URI, return a GIF."""
    with measure_time('decode'):
        if uri.startswith('http'):
            return GIF.from_url(uri, force_deinterlace=force_deinterlace)
        elif os.path.isfile(uri):
            return GIF.from_file(uri, force_deinterlace=force_deinterlace)
        else:
            raise ValueError('{} is not a filename or URL'.format(uri))


def print_exceptions(func):
    """Wrapper for function to print any tracebacks.

    This makes debugging easier when the function is to be run in a
    multiprocessing pool.
    """
    def wrapped_func():
        try:
            return func()
        except Exception as e:
            import traceback, sys
            print "".join(traceback.format_exception(*sys.exc_info()))
            raise e
    return wrapped_func


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                        level=LOG_LEVELS[args.log_level])
    logging.getLogger('requests').propagate = False

    # get a function that returns a gif
    if args.command == 'encode':
        load_gif_f = lambda: run_encoder(args)
    elif args.command == 'decode':
        load_gif_f = lambda: run_decoder(args)
    elif args.command == 'reddit':
        load_gif_f = lambda: run_reddit(args)

    # give the function to the gui, which will run it asynchronously
    viewer = GIFViewer(print_exceptions(load_gif_f))
    viewer.show()


if __name__ == '__main__':
    main()
