"""Construct-based parser for the GIF file format.

Only uses constructs that don't require seeking, so we can parse streams that
don't support it without buffering.

Based on specifications:
http://www.w3.org/Graphics/GIF/spec-gif89a.txt
http://www.w3.org/Graphics/GIF/spec-gif87.txt
"""


import construct

import gifprime.lzw


def DataSubBlocks(name):
    """Return Adapter to parse GIF data sub-blocks."""
    return construct.ExprAdapter(
        construct.Struct(
            name,
            construct.RepeatUntil(
                lambda obj, ctx: obj.block_size == 0x00,
                construct.Struct(
                    'blocks',
                    construct.ULInt8('block_size'),
                    construct.Bytes('data_values', lambda ctx: ctx.block_size),
                ),
            ),
        ),
        # from comment string, build Containers
        encoder=lambda obj, ctx: construct.Container(
            blocks = [
                construct.Container(
                    block_size = len(chunk),
                    data_values = chunk,
                ) for chunk in [obj[i:i+255] for i in xrange(0, len(obj), 255)]
            ] + [construct.Container(block_size = 0, data_values = '')],
        ),
        # from Containers, build comment string
        decoder=lambda obj, ctx: ''.join(dsb.data_values for dsb in obj.blocks),
    )


_image_block = construct.Struct(
    'image',
    construct.Value('block_type', lambda ctx: 'image'),
    construct.Struct(
        'image_descriptor',
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
        construct.Array(
            lambda ctx: pow(2, ctx.image_descriptor.lct_size + 1),
            construct.Array(3, construct.ULInt8('lct')),
        ),
    ),
    construct.ULInt8('lzw_min'),
    DataSubBlocks('compressed_indices'),
)


_application_extension = construct.Struct(
    'application_extension',
    construct.Value('block_type', lambda ctx: 'application'),
    construct.Const(construct.ULInt8('block_size'), 11),
    construct.String('app_id', 8),
    construct.Bytes('app_auth_code', 3),
    DataSubBlocks('app_data'),
)


_comment_extension = construct.Struct(
    'comment_extension',
    construct.Value('block_type', lambda ctx: 'comment'),
    DataSubBlocks('comment'),
)


_gce_extension = construct.Struct(
    'gce_extension',
    construct.Value('block_type', lambda ctx: 'gce'),
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
)


_unknown_extension = construct.Struct(
    'unknown_extension',
    construct.Value('block_type', lambda ctx: 'unknown'),
    DataSubBlocks('unknown_data'),
)


_logical_screen_descriptor = construct.Struct(
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
)


_gct = construct.Array(
    lambda ctx: pow(2, ctx.logical_screen_descriptor.gct_size + 1),
    construct.Array(3, construct.ULInt8('gct')),
)


gif = construct.Struct(
    'GIF',
    construct.Select(
        'magic',
        construct.Magic('GIF89a'),
        construct.Magic('GIF87a'),
    ),
    _logical_screen_descriptor,
    construct.If(lambda ctx: ctx.logical_screen_descriptor.gct_flag, _gct),
    construct.RepeatUntil(
        lambda obj, ctx: obj.block_start == 0x3B,
        construct.Struct(
            'body',
            construct.ULInt8('block_start'),
            construct.Embedded(
                construct.Switch('block', lambda ctx: ctx.block_start,
                    {
                        0x3B: construct.Struct(
                            # workaround for Pass not working
                            'terminator',
                            construct.Value('terminator',
                                            lambda ctx: 'terminator'),
                        ),
                        0x2C: _image_block,
                        0x21: construct.Struct(
                            'ext',
                            construct.ULInt8('ext_label'),
                            construct.Embedded(
                                construct.Switch(
                                    'extension',
                                    lambda ctx: ctx.ext_label,
                                    {
                                        0xFF: _application_extension,
                                        0xFE: _comment_extension,
                                        0xF9: _gce_extension,
                                    },
                                    default = _unknown_extension,
                                ),
                            ),
                        ),
                    },
                ),
            ),
        ),
    ),
    construct.Terminator,
)
