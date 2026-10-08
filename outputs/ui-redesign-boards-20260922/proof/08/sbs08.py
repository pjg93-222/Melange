"""Build 08 side-by-sides: board B22 left (scaled 1/1.25 to its 1600x900 CSS frame), build right (1:1).

    python sbs08.py            (after node capture.cjs 8819)

Writes 08_<state>_<width>.png into this folder.
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BOARD = HERE.parent.parent / 'boards' / 'B22_collection_run_card.webp'
SHOTS = HERE / 'shots'
STATES = ['running', 'stopped', 'completed', 'empty', 'history', 'folder']
SIZES = ((1440, 900), (1600, 900), (1920, 1080))


def font(size):
    try:
        return ImageFont.truetype(os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arial.ttf'), size)
    except OSError:
        return ImageFont.load_default()


def main():
    src = Image.open(BOARD).convert('RGB')
    board = src.resize((round(src.width / 1.25), round(src.height / 1.25)), Image.LANCZOS)
    for state in STATES:
        for width, height in SIZES:
            shot = SHOTS / f'{state}_{width}x{height}.png'
            if not shot.exists():
                print('missing', shot.name)
                continue
            build = Image.open(shot).convert('RGB')
            pad, gap, bar = 16, 24, 40
            canvas = Image.new('RGB', (pad + board.width + gap + build.width + pad, pad + bar + max(board.height, build.height) + pad), (34, 32, 38))
            draw = ImageDraw.Draw(canvas)
            draw.text((pad, pad + 8), 'Board B22_collection_run_card (1600x900 CSS frame)', fill=(235, 230, 240), font=font(18))
            draw.text((pad + board.width + gap, pad + 8), f'Build 08 {state} at {width}x{height}', fill=(235, 230, 240), font=font(18))
            canvas.paste(board, (pad, pad + bar))
            canvas.paste(build, (pad + board.width + gap, pad + bar))
            out = HERE / f'08_{state}_{width}.png'
            canvas.save(out, optimize=True)
            print('wrote', out.name)


main()
