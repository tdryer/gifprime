from argparse import ArgumentParser

from gifprime.core import GIF
from gifprime.gui import GIFViewer


def parse_args():
    parser = ArgumentParser('gifprime')
    subparser = parser.add_subparsers()

    # Encoder
    encoder = subparser.add_parser('encode', help='create a gif')
    encoder.add_argument('images', nargs='+', help='image frame for gif')
    encoder.add_argument('--output', '-o', help='output filename')
    encoder.set_defaults(command='encode')

    # Decoder
    decoder = subparser.add_parser('decode', help='view a gif')
    decoder.add_argument('filename')
    decoder.set_defaults(command='decode')

    return parser.parse_args()


def run_encoder(args):
    print 'TODO: hook up the gif encoder'


def run_decoder(args):
    gif = GIF(args.filename)
    viewer = GIFViewer(gif)
    viewer.show()


def main():
    args = parse_args()

    if args.command == 'encode':
        run_encoder(args)
    elif args.command == 'decode':
        run_decoder(args)


if __name__ == '__main__':
    main()
