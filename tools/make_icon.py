"""Generate assets/icon.ico and assets/icon.png (dev-only; needs Pillow).

Design: Claude-orange rounded-square tile, white speech bubble, orange checkmark.
Drawn once at 1024px and downscaled per size so edges stay smooth.

    python tools/make_icon.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ORANGE = (217, 119, 87, 255)   # #D97757
WHITE = (255, 255, 255, 255)
S = 1024                       # master canvas size
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
OUT = Path(__file__).resolve().parent.parent / "assets"


def draw_master() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Tile
    m = int(S * 0.04)
    d.rounded_rectangle([m, m, S - m, S - m], radius=int(S * 0.22), fill=ORANGE)

    # Speech bubble body + tail (tail points down-left)
    bx0, by0, bx1, by1 = int(S * 0.18), int(S * 0.20), int(S * 0.82), int(S * 0.68)
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=int(S * 0.12), fill=WHITE)
    d.polygon([
        (int(S * 0.30), by1 - 10),
        (int(S * 0.46), by1 - 10),
        (int(S * 0.27), int(S * 0.84)),
    ], fill=WHITE)

    # Checkmark, drawn as two thick strokes with round joints
    w = int(S * 0.085)
    p1, p2, p3 = (int(S * 0.33), int(S * 0.45)), (int(S * 0.45), int(S * 0.56)), (int(S * 0.67), int(S * 0.33))
    d.line([p1, p2, p3], fill=ORANGE, width=w, joint="curve")
    for x, y in (p1, p3):  # round caps
        d.ellipse([x - w // 2, y - w // 2, x + w // 2, y + w // 2], fill=ORANGE)
    return img


def main() -> None:
    OUT.mkdir(exist_ok=True)
    master = draw_master()
    master.resize((256, 256), Image.LANCZOS).save(OUT / "icon.png")
    # Pillow builds each ICO entry from the source image at the requested sizes.
    master.save(OUT / "icon.ico", sizes=[(s, s) for s in ICO_SIZES])
    print(f"wrote {OUT / 'icon.ico'} and {OUT / 'icon.png'}")


if __name__ == "__main__":
    main()
