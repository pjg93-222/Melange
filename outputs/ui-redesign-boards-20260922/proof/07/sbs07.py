"""Build 07 side-by-sides: board left (scaled 1/1.25 to its 1600x900 CSS frame), build right (1:1).

    python sbs07.py            (after node capture.cjs)

Writes 07_<state>_<width>.png into this folder.
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BOARDS = HERE.parent.parent / 'boards'
SHOTS = HERE / 'shots'
STATES = [
    ('B20_typing', 'B20_loading_step1_typing.webp'),
    ('L1_upload', 'L1_loading_step1_upload.webp'),
    ('L2_decisions', 'L2_loading_step2_review.webp'),
    ('L2_settled', 'L2_loading_step2_review.webp'),
    ('L3_cycles', 'L3_loading_step3_cycles.webp'),
    ('L4_grid', 'L4_loading_coverage_grid.webp'),
    ('L4_real', 'L4_loading_coverage_grid.webp'),
]


def font(size):
    try:
        return ImageFont.truetype(os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arial.ttf'), size)
    except OSError:
        return ImageFont.load_default()


def main():
    for state, board_name in STATES:
        src = Image.open(BOARDS / board_name).convert('RGB')
        board = src.resize((round(src.width / 1.25), round(src.height / 1.25)), Image.LANCZOS)
        for width, height in ((1440, 900), (1920, 1080)):
            shot = SHOTS / f'{state}_{width}x{height}.png'
            if not shot.exists():
                print('missing', shot.name)
                continue
            build = Image.open(shot).convert('RGB')
            pad, gap, bar = 16, 24, 40
            canvas = Image.new('RGB', (pad + board.width + gap + build.width + pad, pad + bar + max(board.height, build.height) + pad), (34, 32, 38))
            draw = ImageDraw.Draw(canvas)
            draw.text((pad, pad + 8), f'Board {board_name} (1600x900 CSS frame)', fill=(235, 230, 240), font=font(18))
            draw.text((pad + board.width + gap, pad + 8), f'Build 07 {state} at {width}x{height}', fill=(235, 230, 240), font=font(18))
            canvas.paste(board, (pad, pad + bar))
            canvas.paste(build, (pad + board.width + gap, pad + bar))
            out = HERE / f'07_{state}_{width}.png'
            canvas.save(out, optimize=True)
            print('wrote', out.name)


main()
