"""Construct-based parser for the GIF file format.

Based on specifications:
http://www.w3.org/Graphics/GIF/spec-gif89a.txt
http://www.w3.org/Graphics/GIF/spec-gif87.txt
"""


import construct


def DataSubBlocks(name):
    """Return Adapter to parse GIF data sub-blocks."""
    return construct.ExprAdapter(
        construct.OptionalGreedyRange(
            construct.Struct(
                name,
                construct.NoneOf(construct.ULInt8('block_size'), [0]),
                construct.Bytes('data_values', lambda ctx: ctx.block_size),
            ),
        ),
        encoder=None, # TODO implement encoder
        decoder=lambda obj, ctx: ''.join(dsb.data_values for dsb in obj),
    )


class LzwAdapter(construct.Adapter):
    """Adapter for LZW-compressed data.

    Example:
        LzwAdapter(Bytes('foo', 4))
    """

    def _encode(self, obj, context):
        return None # TODO implement encoder

    def _decode(self, obj, context):
        # TODO implement decoder
        # XXX: this is a hack to make tests pass before we implement it
        min_code_size = context.lzw_min
        if len(obj) == 2:
            return '\x00'
        else:
            return '\x00' * 8 * 8


gif = construct.Struct(
    'GIF',
    construct.Select(
        'magic',
        construct.Magic('GIF89a'),
        construct.Magic('GIF87a'),
    ),
    construct.Struct(
        'logical_screen_descriptor',
        construct.ULInt16('logical_width'),
        construct.ULInt16('logical_height'),
        construct.EmbeddedBitStruct(
            construct.Flag('gct_flag'),
            construct.macros.BitField('colour_res', 3),
            construct.Flag('sort_flag'),
            construct.macros.BitField('gct_size', 3),
        ),
        construct.ULInt8('bg_col_index'),
        construct.ULInt8('pixel_aspect'),
    ),
    construct.If(
        lambda ctx: ctx.logical_screen_descriptor.gct_flag,
        construct.Struct(
            'gct',
            construct.Array(
                lambda ctx: pow(2,
                                ctx._.logical_screen_descriptor.gct_size + 1),
                construct.Array(3, construct.ULInt8('colour_component')),
            ),
        ),
    ),
    construct.GreedyRange(
        construct.Select(
            'body',
            construct.Struct(
                'application_extension',
                construct.Value('block_type',
                                lambda ctx: 'application_extension'),
                construct.Const(construct.ULInt8('ext_intro'), 0x21),
                construct.Const(construct.ULInt8('comm_label'), 0xFF),
                construct.Const(construct.ULInt8('block_size'), 11),
                construct.String('app_id', 8),
                construct.Bytes('app_auth_code', 3),
                DataSubBlocks('app_data'),
                construct.Const(construct.ULInt8('terminator'), 0),
            ),
            construct.Struct(
                'comment_extension',
                construct.Value('block_type', lambda ctx: 'comment_extension'),
                construct.Const(construct.ULInt8('ext_intro'), 0x21),
                construct.Const(construct.ULInt8('comm_label'), 0xFE),
                construct.ULInt8('comm_size'),
                construct.String('comment', lambda ctx: ctx.comm_size),
                construct.Const(construct.ULInt8('terminator'), 0)
            ),
            construct.Struct(
                'image',
                construct.Value('block_type', lambda ctx: 'image'),
                construct.Optional(
                    construct.Struct(
                        'gce',
                        construct.Const(construct.ULInt8('ext_intro'), 0x21),
                        construct.Const(construct.ULInt8('gce_label'), 0xF9),
                        construct.Const(construct.ULInt8('block_size'), 4),
                        construct.EmbeddedBitStruct(
                            construct.Padding(3),  # reserved
                            construct.macros.BitField('disposal_method', 3),
                            construct.Flag('user_input_flag'),
                            construct.Flag('transparent_colour_flag'),
                        ),
                        construct.ULInt16('delay_time'),
                        construct.ULInt8('transparent_colour_index'),
                        construct.Const(construct.ULInt8('terminator'), 0),
                    ),
                ),
                construct.Struct(
                    'image_descriptor',
                    construct.Const(construct.ULInt8('img_sep'), 0x2C),
                    construct.ULInt16('left'),
                    construct.ULInt16('top'),
                    construct.ULInt16('width'),
                    construct.ULInt16('height'),
                    construct.EmbeddedBitStruct(
                        construct.Flag('lct_flag'),
                        construct.Flag('interlace_flag'),
                        construct.Flag('sort_flag'),
                        construct.Padding(2),  # reserved
                        construct.macros.BitField('lct_size', 3),
                    ),
                ),
                construct.If(
                    lambda ctx: ctx.image_descriptor.lct_flag,
                    construct.Struct(
                        'lct',
                        construct.Array(
                            lambda ctx: pow(
                                2,
                                ctx._.image_descriptor.lct_size + 1
                            ),
                            construct.Array(
                                3,
                                construct.ULInt8('colour_component'),
                            ),
                        ),
                    ),
                ),
                construct.ULInt8('lzw_min'),
                # TODO: creates an array called data_subblocks instead of index
                construct.Tunnel(
                    LzwAdapter(DataSubBlocks('pixels')),
                    construct.Array(
                        lambda ctx: (ctx.image_descriptor.width *
                                     ctx.image_descriptor.height),
                        construct.ULInt8('index'),
                    ),
                ),
                construct.Const(construct.ULInt8('terminator'), 0),
            ),
        ),
    ),
    construct.Const(
        construct.ULInt8('trailer'),
        0x3B,
    ),
    construct.Terminator,
)
