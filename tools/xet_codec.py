"""Read-only XET v1 texture inspection; never rewrites game image resources.

Container fields measured at guest handlers 08c1e21c/08c1e450. PSP pixel
formats and 16-byte by 8-row swizzle agree with the pinned PPSSPP decoder.
"""
from dataclasses import dataclass
import struct


def extent(data, offset, size):
    if offset < 48 or size < 0 or offset + size > len(data):
        raise ValueError('Texture extent outside resource')
    return data[offset:offset+size]


def swizzled_offset(stride, bits, x, y):
    """Byte offset used by the pinned PSP sampler's 32-bit subtiles."""
    per_tile = 32//bits
    tile = x//per_tile
    tile_index = ((y%8)*4 + (y//8)*((stride*bits//32)*8) + tile%4 + (tile//4)*32)
    return tile_index*4 + ((x%per_tile)*bits//8)


def swizzled_extent(mip, bits):
    return max(swizzled_offset(mip.stride,bits,mip.width-1,y)
               for y in range(mip.height))+max(1,bits//8)


@dataclass(frozen=True)
class Mip:
    width: int
    height: int
    stride: int
    reserved: int
    offset: int


@dataclass(frozen=True)
class Texture:
    name: str
    format: int
    palette_index: int
    mips: tuple


@dataclass(frozen=True)
class Xet:
    data: bytes
    textures: tuple
    palettes: tuple

    @classmethod
    def parse(cls, data):
        if len(data) < 48 or data[:8] != b'XET.\x01\0\0\0':
            raise ValueError('Unknown XET header/version')
        count, palette_count, flags, descriptors, palettes, names = struct.unpack_from('<HH4I', data, 8)
        # Bit 1 is the copy-capable container flag checked at 08c1dfac;
        # it does not change the on-disc descriptor or pixel representation.
        if flags not in (0, 2):
            raise ValueError('Unsupported texture container flags')
        extent(data, descriptors, count*16)
        extent(data, palettes, palette_count*8)
        if names:
            extent(data, names, 1)
        textures = []
        name_cursor = names
        for index in range(count):
            fmt, max_level, palette_index, reserved, unknown, mip_offset = struct.unpack_from('<4H2I', data, descriptors+index*16)
            if max_level > 7:
                raise ValueError('Unsupported mip count')
            extent(data, mip_offset, (max_level+1)*12)
            mips = []
            for level in range(max_level+1):
                mip = Mip(*struct.unpack_from('<4HI', data, mip_offset+level*12))
                if not 0 < mip.width <= mip.stride <= 4096 or not 0 < mip.height <= 4096:
                    raise ValueError('Invalid mip dimensions')
                mips.append(mip)
            raw_name = b''
            if names:
                end = data.find(b'\0', name_cursor)
                if end < 0:
                    raise ValueError('Unterminated texture name')
                raw_name = data[name_cursor:end]
                name_cursor = end+1
            textures.append(Texture(raw_name.decode('ascii', errors='backslashreplace'), fmt, palette_index, tuple(mips)))
        palette_records = tuple(struct.unpack_from('<4BI', data, palettes+i*8) for i in range(palette_count))
        return cls(data, tuple(textures), palette_records)

    @staticmethod
    def rgba(raw, fmt):
        if fmt == 3:
            return raw[:4]
        value = int.from_bytes(raw[:2], 'little')
        if fmt == 0:
            r, g, b = value & 31, (value >> 5) & 63, (value >> 11) & 31
            return bytes(((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2), 255))
        if fmt == 1:
            r, g, b = value & 31, (value >> 5) & 31, (value >> 10) & 31
            return bytes(((r << 3) | (r >> 2), (g << 3) | (g >> 2), (b << 3) | (b >> 2), 255 if value & 0x8000 else 0))
        if fmt == 2:
            return bytes(((value & 15)*17, ((value >> 4) & 15)*17, ((value >> 8) & 15)*17, ((value >> 12) & 15)*17))
        raise ValueError('Unsupported palette/direct colour format')

    def preview(self, index, limit=256):
        """Decode first mip to RGBA, optionally sampling for a private audit sheet."""
        return self.preview_mip(index, 0, limit)

    def preview_mip(self, index, level, limit=512):
        """Decode an authored mip using the pinned PSP sampler's padded tiles."""
        if type(limit) is not int or limit < 1 or limit > 4096:
            raise ValueError('Invalid preview limit')
        texture = self.textures[index]
        if type(level) is not int or not 0 <= level < len(texture.mips):
            raise ValueError('Mip level outside descriptor')
        fmt = texture.format & 15
        if texture.format & ~0x10f or fmt > 7:
            raise ValueError('Unsupported texture pixel format')
        mip = texture.mips[level]
        bits = (16, 16, 16, 32, 4, 8, 16, 32)[fmt]
        # ge.c::texel_offset / PPSSPP Software/Sampler.cpp. Short rows and
        # levels still occupy padded tiles, not stride*height packed bytes.
        pixels = extent(self.data, mip.offset, swizzled_extent(mip,bits))
        palette = None
        if fmt >= 4:
            if texture.palette_index >= len(self.palettes):
                raise ValueError('Palette index outside resource')
            colour, shift, mask, blocks, offset = self.palettes[texture.palette_index]
            # GE LOADCLUT counts 32-byte blocks in every colour format:
            # eight RGBA8888 colours, or sixteen 16-bit colours per block.
            palette = extent(self.data, offset, blocks*32)
        scale = max(1, (max(mip.width, mip.height)+limit-1)//limit)
        width, height = (mip.width+scale-1)//scale, (mip.height+scale-1)//scale
        output = bytearray()
        for y in range(0, mip.height, scale):
            for x in range(0, mip.width, scale):
                start_address = swizzled_offset(mip.stride,bits,x,y)
                raw = pixels[start_address:start_address+max(1, bits//8)]
                if palette is not None:
                    value = int.from_bytes(raw, 'little')
                    if fmt == 4:
                        value = (value >> (4*(x%2))) & 15
                    entry = (value >> shift) & mask
                    start = entry*(4 if colour == 3 else 2)
                    if start+(4 if colour == 3 else 2) > len(palette):
                        raise ValueError('Palette lookup outside allocation')
                    raw = palette[start:start+(4 if colour == 3 else 2)]
                    output.extend(self.rgba(raw, colour))
                else:
                    output.extend(self.rgba(raw, fmt))
        return width, height, bytes(output)

    def replace_text_regions(self, index, rgba, rectangles):
        """Change approved single-mip T4/T8 pixels; retain neighbours and metadata."""
        texture = self.textures[index]
        if texture.format not in (4, 5) or len(texture.mips) != 1:
            raise ValueError('Text editing supports only measured single-mip T4/T8 textures')
        mip = texture.mips[0]
        if len(rgba) != mip.width*mip.height*4 or not rectangles:
            raise ValueError('Replacement pixel extent or regions differ')
        if texture.palette_index >= len(self.palettes):
            raise ValueError('Palette index outside resource')
        colour, shift, mask, blocks, offset = self.palettes[texture.palette_index]
        if colour != 3 or shift != 0:
            raise ValueError('Text editing requires an unshifted RGBA8888 palette')
        palette = extent(self.data, offset, blocks*8*4)
        nibble = texture.format == 4
        pitch = mip.stride//2 if nibble else mip.stride
        colours = [palette[i*4:(i+1)*4] for i in range(min(blocks*8, mask+1, 16 if nibble else 256))]
        if not colours or (nibble and mip.stride % 2) or pitch % 16 or mip.height % 8:
            raise ValueError('Unsupported text palette or swizzle extent')
        extent(self.data, mip.offset, pitch*mip.height)
        output, cache = bytearray(self.data), {}
        for x0, y0, width, height in rectangles:
            if min(x0, y0) < 0 or min(width, height) <= 0 or x0+width > mip.width or y0+height > mip.height:
                raise ValueError('Approved text region exceeds image')
            for y in range(y0, y0+height):
                for x in range(x0, x0+width):
                    start = (y*mip.width+x)*4
                    pixel = bytes(rgba[start:start+4])
                    if pixel not in cache:
                        cache[pixel] = min(range(len(colours)), key=lambda i: sum((a-b)**2 for a, b in zip(pixel, colours[i])))
                    byte_x = x//2 if nibble else x
                    address = mip.offset+((y//8)*(pitch//16)+byte_x//16)*128+(y%8)*16+byte_x%16
                    if nibble:
                        shift = (x%2)*4
                        output[address] = (output[address] & (0xff ^ (15 << shift))) | (cache[pixel] << shift)
                    else:
                        output[address] = cache[pixel]
        parsed = Xet.parse(bytes(output))
        if parsed.textures != self.textures or parsed.palettes != self.palettes:
            raise ValueError('Text edit changed texture metadata')
        return bytes(output)
