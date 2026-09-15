"""Write icon-180.png with the standard library only (zlib + struct).

180x180, ivory #f7ede4 rounded-square ground, plum #342649 serif "M".
The M is assembled from convex polygons (two stems, two diagonals, four
serifs) and rendered with 4x supersampling, so no font or imaging library
is required.
"""
import struct
import zlib
from pathlib import Path

SIZE = 180
SUPERSAMPLE = 4
IVORY = (0xF7, 0xED, 0xE4)
PLUM = (0x34, 0x26, 0x49)
PAPER = (0xFC, 0xF7, 0xF4)
RADIUS = 38.0

# Glyph geometry in a 0..100 box, mapped into the icon below.
STEM_TOP, STEM_BOTTOM = 0.0, 100.0
SHAPES = [
    # left stem, right stem
    [(10, 0), (23, 0), (23, 100), (10, 100)],
    [(77, 0), (90, 0), (90, 100), (77, 100)],
    # left diagonal: inner top-left down to the apex
    [(20, 0), (33, 0), (56, 74), (50, 88), (44, 74)],
    # right diagonal: apex back up to inner top-right
    [(67, 0), (80, 0), (56, 74), (50, 88), (44, 74)],
    # top serifs
    [(3, 0), (30, 0), (30, 9), (3, 9)],
    [(70, 0), (97, 0), (97, 9), (70, 9)],
    # bottom serifs
    [(1, 91), (32, 91), (32, 100), (1, 100)],
    [(68, 91), (99, 91), (99, 100), (68, 100)],
]
GLYPH_LEFT, GLYPH_WIDTH = 34.0, 112.0
GLYPH_TOP, GLYPH_HEIGHT = 47.0, 86.0


def inside_polygon(x, y, polygon):
    """True when (x, y) is on the same side of every edge (convex polygons)."""
    sign = 0
    count = len(polygon)
    for index in range(count):
        ax, ay = polygon[index]
        bx, by = polygon[(index + 1) % count]
        cross = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        if cross > 1e-9:
            if sign < 0:
                return False
            sign = 1
        elif cross < -1e-9:
            if sign > 0:
                return False
            sign = -1
    return True


def inside_rounded_square(x, y):
    low, high = RADIUS, SIZE - RADIUS
    if low <= x <= high or low <= y <= high:
        return 0.0 <= x <= SIZE and 0.0 <= y <= SIZE
    cx = low if x < low else high
    cy = low if y < low else high
    return (x - cx) ** 2 + (y - cy) ** 2 <= RADIUS ** 2


def glyph_shapes():
    out = []
    for polygon in SHAPES:
        out.append([(GLYPH_LEFT + px / 100.0 * GLYPH_WIDTH,
                     GLYPH_TOP + py / 100.0 * GLYPH_HEIGHT) for px, py in polygon])
    return out


def render():
    shapes = glyph_shapes()
    step = 1.0 / SUPERSAMPLE
    samples = SUPERSAMPLE * SUPERSAMPLE
    rows = []
    for row in range(SIZE):
        line = bytearray()
        for column in range(SIZE):
            ground_hits = 0
            ink_hits = 0
            for sy in range(SUPERSAMPLE):
                y = row + (sy + 0.5) * step
                for sx in range(SUPERSAMPLE):
                    x = column + (sx + 0.5) * step
                    if not inside_rounded_square(x, y):
                        continue
                    ground_hits += 1
                    if any(inside_polygon(x, y, shape) for shape in shapes):
                        ink_hits += 1
            ground = ground_hits / samples
            ink = ink_hits / samples
            for channel in range(3):
                value = (PAPER[channel] * (1.0 - ground)
                         + IVORY[channel] * (ground - ink)
                         + PLUM[channel] * ink)
                line.append(max(0, min(255, int(round(value)))))
        rows.append(bytes(line))
    return rows


def write_png(path, rows):
    raw = b''.join(b'\x00' + row for row in rows)

    def chunk(tag, payload):
        body = tag + payload
        return struct.pack('>I', len(payload)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack('>IIBBBBB', SIZE, SIZE, 8, 2, 0, 0, 0)  # 8-bit truecolor RGB
    data = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    Path(path).write_bytes(data)
    return len(data)


if __name__ == '__main__':
    target = Path(__file__).with_name('icon-180.png')
    size = write_png(target, render())
    print('wrote {} ({} bytes)'.format(target, size))
