#!/usr/bin/env python3
"""PeopleCoral store screenshots in the approved house style (soft gradient,
headline + subtitle, phone frame), built from raw device captures.

Usage: compose_house.py <work_dir>
  reads  <work_dir>/raw/{ios,android}/<name>.png
  writes <work_dir>/out/{ios,ios65,android}/NN_<name>.png and out/android/feature_graphic.png
"""
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()


def workhub():
    script = (
        Path(__file__).resolve().parents[2]
        / "peoplecoral-release"
        / "scripts"
        / "workhub.sh"
    )
    return Path(subprocess.check_output(
        ["bash", "-c", 'source "$1" && workhub', "workhub", str(script)],
        text=True,
    ).strip())


REPO = workhub()
FONTS = REPO / "assets" / "fonts"
HEAD_FONT = FONTS / "circular-std-medium-500.ttf"
SUB_FONT = FONTS / "lexend-regular.ttf"
if not HEAD_FONT.is_file() or not SUB_FONT.is_file():
    sys.exit(f"missing house-style fonts under {FONTS}")

NAVY = (16, 40, 78)
SUB = (74, 88, 120)
TOP = (240, 242, 252)
BOTTOM = (214, 220, 248)

SLIDES = [
    ("01_home", "Everything at Work,\nin One App", "Time off, payslips, expenses and more"),
    ("02_timeoff_approved", "Request Time Off\nin Seconds", "Track every request and approval"),
    ("05_payslips", "Your Payslips,\nAlways at Hand", "Browse and download by month"),
    ("09_attendance", "See Your\nWork Week", "Workdays and hours at a glance"),
    ("06_expenses", "Claim Expenses\nOn the Go", "Snap the receipt and submit"),
    ("07_chat_list", "Stay Connected\nWith Your Team", "Secure internal chat"),
    ("10_notifications", "Never Miss\nan Update", "Approvals and payslips, instantly"),
    ("12_manager_home", "Approve Requests\nFrom Anywhere", "Built for managers too"),
]

# output folder -> (raw capture folder, size)
TARGETS = {
    "ios": ("ios", (1320, 2868)),
    "ios65": ("ios", (1284, 2778)),
    "android": ("android", (1080, 1920)),
}


def gradient(size):
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        c = tuple(int(TOP[i] * (1 - t) + BOTTOM[i] * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    glow = Image.new("L", size, 0)
    ImageDraw.Draw(glow).ellipse((int(w * 0.25), int(h * 0.30), int(w * 1.25), int(h * 1.0)), fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(w // 6))
    img.paste((255, 255, 255), mask=glow)
    return img


def rounded(im, r):
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.width, im.height), r, fill=255)
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def phone(shot, width):
    scale = width / shot.width
    screen = shot.convert("RGB").resize((width, int(shot.height * scale)), Image.LANCZOS)
    bezel = int(width * 0.035)
    radius = int(width * 0.13)
    body = Image.new("RGBA", (screen.width + 2 * bezel, screen.height + 2 * bezel), (0, 0, 0, 0))
    ImageDraw.Draw(body).rounded_rectangle((0, 0, body.width, body.height), radius + bezel, fill=(22, 24, 30, 255))
    body.alpha_composite(rounded(screen, radius), (bezel, bezel))
    return body


def shadow(layer, blur):
    s = Image.new("RGBA", (layer.width + blur * 4, layer.height + blur * 4), (0, 0, 0, 0))
    a = layer.split()[3].point(lambda v: 70 if v else 0)
    s.paste((20, 30, 70, 255), (blur * 2, blur * 2), a)
    return s.filter(ImageFilter.GaussianBlur(blur))


def fit_text(draw, text, font_path, max_w, start):
    size = start
    while size > 10:
        f = ImageFont.truetype(str(font_path), size)
        if max(draw.textlength(l, font=f) for l in text.split("\n")) <= max_w:
            return f
        size -= 2
    return ImageFont.truetype(str(font_path), size)


def compose(raw, head, sub, size):
    w, h = size
    canvas = gradient(size).convert("RGBA")
    d = ImageDraw.Draw(canvas)
    hf = fit_text(d, head, HEAD_FONT, w * 0.86, int(w * 0.085))
    sf = fit_text(d, sub, SUB_FONT, w * 0.84, int(w * 0.042))
    y = int(h * 0.065)
    for line in head.split("\n"):
        tw = d.textlength(line, font=hf)
        d.text(((w - tw) / 2, y), line, font=hf, fill=NAVY)
        y += int(hf.size * 1.12)
    y += int(h * 0.012)
    tw = d.textlength(sub, font=sf)
    d.text(((w - tw) / 2, y), sub, font=sf, fill=SUB)
    y += int(sf.size * 1.6)

    dev = phone(Image.open(raw), int(w * 0.70))
    top = max(y + int(h * 0.02), int(h * 0.25))
    x = (w - dev.width) // 2
    sh = shadow(dev, int(w * 0.03))
    canvas.alpha_composite(sh, (x - int(w * 0.06), top - int(w * 0.04)))
    canvas.alpha_composite(dev, (x, top))
    return canvas.convert("RGB")


def feature_graphic(out):
    w, h = 1024, 500
    canvas = gradient((w, h)).convert("RGBA")
    d = ImageDraw.Draw(canvas)
    hf = ImageFont.truetype(str(HEAD_FONT), 54)
    sf = ImageFont.truetype(str(SUB_FONT), 26)
    d.text((60, 150), "Your workday,\nin one app", font=hf, fill=NAVY, spacing=10)
    d.text((60, 310), "Time off · Payslips · Expenses · Chat", font=sf, fill=SUB)
    for i, name in enumerate(("01_home", "05_payslips")):
        dev = phone(Image.open(ROOT / "raw/android" / f"{name}.png"), 230)
        canvas.alpha_composite(dev, (600 + i * 190, 60 + i * 60))
    canvas.convert("RGB").save(out)


def main():
    for target, (platform, size) in TARGETS.items():
        out_dir = ROOT / "out" / target
        out_dir.mkdir(parents=True, exist_ok=True)
        for idx, (name, head, sub) in enumerate(SLIDES, 1):
            raw = ROOT / "raw" / platform / f"{name}.png"
            compose(raw, head, sub, size).save(out_dir / f"{idx:02d}_{name}.png")
    feature_graphic(ROOT / "out" / "android" / "feature_graphic.png")


if __name__ == "__main__":
    main()
