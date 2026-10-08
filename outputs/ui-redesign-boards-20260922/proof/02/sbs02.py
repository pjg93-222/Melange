"""Build 02 side-by-sides: each board left, each capture right, both at 1 image px = 1 CSS px.

    python sbs02.py            (after node capture.cjs)

Boards in ..\\..\\boards: the 2026-09-22 boards (M4, G1-G5) are 2000x1131 for a
1600x900 CSS frame (1.25x); approved_board5 is 2688x1520 for the same frame
(1.68x). Each is scaled by its own factor to 1600 CSS px wide, so the board and
the build are at one scale and a length on one is a length on the other. The
build is the viewport capture at 1440x900 or 1920x1080, unscaled. Writes
02_<state>_<width>.png into this folder.
"""
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BOARDS = HERE.parent.parent / 'boards'
SHOTS = HERE / 'shots'
FACTOR = {'approved_board5_downstream_drawer.webp': 2688 / 1600}
STATES = [
    ('M4_overview', 'M4_graph_default.webp'),
    ('more_menu', 'M4_graph_default.webp'),
    ('drawer_default', 'approved_board5_downstream_drawer.webp'),
    ('G1_industry', 'G1_compare_industry.webp'),
    ('G2_cycle', 'G2_compare_cycle.webp'),
    ('G3_company', 'G3_compare_company.webp'),
    ('G4_three', 'G4_compare_three.webp'),
    ('G5_candidates_table', 'G5_candidates_table.webp'),
    ('drawer_compare', 'approved_board5_downstream_drawer.webp'),
]


def font(size, bold=False):
    for name in (('arialbd.ttf',) if bold else ('arial.ttf',)):
        try:
            return ImageFont.truetype(os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', name), size)
        except OSError:
            pass
    return ImageFont.load_default()


def main():
    made = []
    for state, board_name in STATES:
        board_src = Image.open(BOARDS / board_name).convert('RGB')
        factor = FACTOR.get(board_name, 1.25)
        board = board_src.resize((round(board_src.width / factor), round(board_src.height / factor)), Image.LANCZOS)
        for width, height in ((1440, 900), (1920, 1080)):
            shot = SHOTS / f'{state}_{width}x{height}.png'
            if not shot.exists():
                print('missing', shot.name)
                continue
            build = Image.open(shot).convert('RGB')
            pad, gap, bar = 16, 24, 40
            panel_h = max(board.height, build.height)
            canvas = Image.new('RGB', (pad + board.width + gap + build.width + pad, pad + bar + panel_h + pad), (34, 32, 38))
            draw = ImageDraw.Draw(canvas)
            left, right, top = pad, pad + board.width + gap, pad + bar
            draw.text((left, pad + 4), 'BOARD  ' + board_name, fill=(255, 214, 102), font=font(18, True))
            draw.text((left, pad + 24), f'{board_src.width}x{board_src.height} scaled 1/{factor:.3g} to {board.width}x{board.height} CSS px (a 1600x900 frame)',
                      fill=(205, 205, 205), font=font(12))
            draw.text((right, pad + 4), f'BUILD  {state} at {width}x{height}', fill=(125, 211, 252), font=font(18, True))
            draw.text((right, pad + 24), 'read-only console, 1 image px = 1 CSS px; preview notices hidden', fill=(205, 205, 205), font=font(12))
            canvas.paste(board, (left, top))
            canvas.paste(build, (right, top))
            out = HERE / f'02_{state}_{width}.png'
            canvas.save(out)
            made.append(out.name)
    print(json.dumps(made))
    return 0


if __name__ == '__main__':
    sys.exit(main())
