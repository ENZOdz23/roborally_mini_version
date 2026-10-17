"""Draws the 48x48 PNG images used by the window (robo_rally/ui/assets/).

The images are already in the project; run this only to change their look.
Needs Pillow:  pip install pillow    then    python tools/make_assets.py
Everything is drawn 4x bigger and scaled down, which smooths the edges.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 48
S = 4 * SIZE                       # drawing size
OUT = Path(__file__).resolve().parent.parent / "robo_rally" / "ui" / "assets"

FLOOR = (176, 182, 186)
FLOOR_LINE = (150, 156, 161)
BELT = (38, 92, 160)
BELT_DARK = (24, 60, 110)
ARROW = (235, 240, 245)
HAZARD = (242, 194, 0)
DARK = (34, 36, 40)
ROBOT_COLORS = {"a": (30, 110, 230), "b": (90, 185, 245), "C": (215, 45, 45), "D": (245, 140, 40)}
BONUS_COLORS = {"S": (60, 160, 230), "T": (240, 120, 20), "K": (40, 170, 90), "J": (150, 80, 200)}
ROTATE = {"N": 0, "E": -90, "S": 180, "W": 90}    # PIL rotates counter-clockwise


def font(size):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def canvas(color=FLOOR):
    img = Image.new("RGBA", (S, S), color + (255,))
    d = ImageDraw.Draw(img)
    return img, d


def floor_base():
    img, d = canvas()
    d.rectangle([0, 0, S - 1, S - 1], outline=FLOOR_LINE, width=6)
    for x, y in [(18, 18), (S - 18, 18), (18, S - 18), (S - 18, S - 18)]:     # rivets
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=FLOOR_LINE)
    return img, d


def save(img, name):
    img.resize((SIZE, SIZE), Image.LANCZOS).save(OUT / f"{name}.png")


def text_center(d, text, size, fill, cy=S // 2):
    f = font(size)
    box = d.textbbox((0, 0), text, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((S - w) / 2 - box[0], cy - h / 2 - box[1]), text, font=f, fill=fill)


def arrow_north(d, cx, top, bottom, width=34):
    """Arrow pointing up, centred on cx."""
    d.rectangle([cx - width // 3, top + width, cx + width // 3, bottom], fill=ARROW)
    d.polygon([(cx, top), (cx - width, top + width + 6), (cx + width, top + width + 6)], fill=ARROW)


def make_tiles():
    img, d = floor_base()
    save(img, "floor")

    img, d = canvas(DARK)                                      # wall: hazard stripes
    for i in range(-S, S, 48):
        d.polygon([(i, S), (i + 24, S), (i + 24 + S, 0), (i + S, 0)], fill=HAZARD)
    d.rectangle([10, 10, S - 11, S - 11], outline=DARK, width=10)
    save(img, "wall")

    img, d = floor_base()                                      # hole: dark pit with depth
    for i, shade in enumerate([70, 50, 32, 18, 8]):
        m = 14 + i * 14
        d.rectangle([m, m, S - m, S - m], fill=(shade, shade, shade + 4))
    save(img, "hole")

    # conveyors: belt pointing NORTH, then rotated
    belt, d = canvas(BELT)
    d.rectangle([0, 0, 22, S], fill=BELT_DARK)
    d.rectangle([S - 22, 0, S, S], fill=BELT_DARK)
    for y in range(8, S, 32):
        d.line([(26, y), (S - 26, y)], fill=BELT_DARK, width=4)
    arrow_north(d, S // 2, 30, S - 30)
    for direction, angle in ROTATE.items():
        save(belt.rotate(angle), f"conveyor_{direction}")

    # curved conveyors: belt pointing NORTH + a curved mark showing the turn (r = right, l = left)
    for turn in ("r", "l"):
        img, d = canvas(BELT)
        d.rectangle([0, 0, 22, S], fill=BELT_DARK)
        d.rectangle([S - 22, 0, S, S], fill=BELT_DARK)
        arrow_north(d, S // 2, 30, S - 60)
        x0, x1 = (40, S - 40)
        arc_box = [x0, S - 110, x1, S + 50]
        d.arc(arc_box, start=180 if turn == "r" else 270, end=270 if turn == "r" else 360, fill=HAZARD, width=14)
        text_center(d, "R" if turn == "r" else "L", 44, HAZARD, cy=S - 40)
        for direction, angle in ROTATE.items():
            save(img.rotate(angle), f"conveyor_{turn}_{direction}")

    for n in (1, 2, 3):                                        # checkpoints
        img, d = floor_base()
        d.ellipse([16, 16, S - 16, S - 16], fill=(205, 225, 40), outline=DARK, width=8)
        d.ellipse([40, 40, S - 40, S - 40], fill=DARK)
        text_center(d, str(n), 92, (205, 225, 40))
        save(img, f"checkpoint_{n}")

    for letter, color in BONUS_COLORS.items():                 # bonuses
        img, d = floor_base()
        d.rounded_rectangle([34, 34, S - 34, S - 34], radius=30, fill=color, outline=DARK, width=6)
        text_center(d, letter, 84, (255, 255, 255))
        save(img, f"bonus_{letter}")


def make_robots():
    for label, color in ROBOT_COLORS.items():
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([22, 30, S - 22, S - 14], fill=(0, 0, 0, 70))                      # shadow
        d.ellipse([20, 20, S - 20, S - 20], fill=color, outline=DARK, width=8)        # body
        d.polygon([(S // 2, 4), (S // 2 - 34, 56), (S // 2 + 34, 56)], fill=DARK)    # nose = direction
        d.polygon([(S // 2, 18), (S // 2 - 22, 52), (S // 2 + 22, 52)], fill=(255, 255, 255))
        text_center(d, label.upper(), 70, (255, 255, 255), cy=S // 2 + 12)
        for direction, angle in ROTATE.items():
            out = img.rotate(angle) if direction == "N" else _rotate_keep_label(img, label, color, angle)
            save(out, f"robot_{label}_{direction}")


def _rotate_keep_label(img, label, color, angle):
    """Rotate the body and nose, but keep the letter upright."""
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    d.ellipse([22, 30, S - 22, S - 14], fill=(0, 0, 0, 70))
    d.ellipse([20, 20, S - 20, S - 20], fill=color, outline=DARK, width=8)
    d.polygon([(S // 2, 4), (S // 2 - 34, 56), (S // 2 + 34, 56)], fill=DARK)
    d.polygon([(S // 2, 18), (S // 2 - 22, 52), (S // 2 + 22, 52)], fill=(255, 255, 255))
    base = base.rotate(angle)
    text_center(ImageDraw.Draw(base), label.upper(), 70, (255, 255, 255), cy=S // 2 + 6)
    return base


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    make_tiles()
    make_robots()
    print(f"{len(list(OUT.glob('*.png')))} images in {OUT}")
