"""Construct-based parser for the GIF89a file format."""


import construct


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
    construct.Struct(
        'gct',
        construct.Array(
            lambda ctx: pow(2, ctx._.logical_screen_descriptor.gct_size + 1),
            construct.Array(
                3,
                construct.ULInt8('colour_component'),
            ),
        ),
    ),
    construct.Struct(
        'comment_extension',
        construct.ULInt8('ext_intro'),
        construct.ULInt8('comm_label'),
        construct.ULInt8('comm_size'),
        construct.String(
            'comment',
            lambda ctx: ctx.comm_size,
        ),
        construct.Const(
            construct.ULInt8('terminator'),
            0,
        )
    ),
    construct.Struct(
        'image_descriptor',
        construct.ULInt8('img_sep'),
        construct.ULInt16('left'),
        construct.ULInt16('top'),
        construct.ULInt16('width'),
        construct.ULInt16('height'),
        construct.EmbeddedBitStruct(
            construct.Flag('lct_flag'),
            construct.Flag('interlace_flag'),
            construct.Flag('sort_flag'),
            construct.Padding(2), # reserved
            construct.macros.BitField('lct_size', 3),
        ),
    ),
    construct.Struct(
        'image_data',
        construct.ULInt8('lzw_min'),
        construct.ULInt8('size'),
        construct.Bytes('data', lambda ctx: ctx.size),
        construct.Const(
            construct.ULInt8('terminator'),
            0,
        )
    ),
    construct.Const(
        construct.ULInt8('trailer'),
        0x3B,
    ),
    construct.Terminator,
)
