"""Construct-based parser for the GIF89a file format.

Based on specification:
http://www.w3.org/Graphics/GIF/spec-gif89a.txt
"""


import construct


# common representation of blocks of data (includes terminator)
_data_subblocks = construct.Struct(
    '_data_subblocks',
    construct.OptionalGreedyRange(
        construct.Struct(
            'data_subblock',
            construct.NoneOf(construct.ULInt8('block_size'), [0]),
            construct.Bytes('data_values', lambda ctx: ctx.block_size),
        ),
    ),
    construct.Const(construct.ULInt8('terminator'), 0),
)


gif = construct.Struct(
    'GIF',
    construct.Magic('GIF89a'),
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
                lambda ctx: pow(2, ctx._.logical_screen_descriptor.gct_size + 1),
                construct.Array(3, construct.ULInt8('colour_component')),
            ),
        ),
    ),
    construct.GreedyRange(
        construct.Select(
            'body',
            construct.Struct(
                'application_extension',
                construct.Const(construct.ULInt8('ext_intro'), 0x21),
                construct.Const(construct.ULInt8('comm_label'), 0xFF),
                construct.Const(construct.ULInt8('block_size'), 11),
                construct.String('app_id', 8),
                construct.Bytes('app_auth_code', 3),
                _data_subblocks,
            ),
            construct.Struct(
                'comment_extension',
                construct.Const(construct.ULInt8('ext_intro'), 0x21),
                construct.Const(construct.ULInt8('comm_label'), 0xFE),
                construct.ULInt8('comm_size'),
                construct.String('comment', lambda ctx: ctx.comm_size),
                construct.Const(construct.ULInt8('terminator'), 0)
            ),
            construct.Struct(
                'image',
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
                            lambda ctx: pow(2, ctx._.image_descriptor.lct_size + 1),
                            construct.Array(
                                3,
                                construct.ULInt8('colour_component'),
                            ),
                        ),
                    ),
                ),
                construct.ULInt8('lzw_min'),
                _data_subblocks,
            ),
        ),
    ),
    construct.Const(
        construct.ULInt8('trailer'),
        0x3B,
    ),
    construct.Terminator,
)
