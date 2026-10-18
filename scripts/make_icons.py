"""Иконки магазина: приложение (Android/iOS), адаптивная иконка Android, заставка, веб (PWA).

    python3 scripts/make_icons.py

Знак — белая сумка с «DiDi» на фирменном зелёном (colors.primary в mobile/src/components/theme.ts).
Нужен только Pillow. Чтобы поставить свой логотип, замените файлы в mobile/assets и
mobile/public/icons (размеры — как здесь) и пересоберите приложение.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "mobile/assets"
WEB = ROOT / "mobile/public/icons"
GREEN = (31, 77, 58)
WHITE = (255, 255, 255)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SS = 4  # суперсэмплинг для гладких краёв


def mark(size: int, color, text_color, scale: float) -> Image.Image:
    """Сумка с надписью на прозрачном фоне; scale — доля ширины холста под знак."""
    big = size * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w = big * scale
    cx, cy = big / 2, big / 2 + w * 0.08
    body = (cx - w / 2, cy - w * 0.32, cx + w / 2, cy + w * 0.5)
    draw.rounded_rectangle(body, radius=w * 0.12, fill=color)
    # Ручка — дуга над сумкой.
    hw = w * 0.36
    handle = (cx - hw / 2, cy - w * 0.62, cx + hw / 2, cy - w * 0.02)
    draw.arc(handle, start=180, end=360, fill=color, width=int(w * 0.075))
    font = ImageFont.truetype(FONT, int(w * 0.3))
    draw.text((cx, cy + w * 0.1), "DiDi", font=font, fill=text_color, anchor="mm")
    return img.resize((size, size), Image.LANCZOS)


def solid(size: int, mark_scale: float, background=GREEN) -> Image.Image:
    base = Image.new("RGBA", (size, size), background + (255,))
    base.alpha_composite(mark(size, WHITE, GREEN, mark_scale))
    return base.convert("RGB")


def main() -> None:
    WEB.mkdir(parents=True, exist_ok=True)
    solid(1024, 0.56).save(ASSETS / "icon.png", optimize=True)
    # Адаптивная иконка Android: система обрезает края, знак — в центральных ~60%.
    Image.new("RGB", (512, 512), GREEN).save(ASSETS / "android-icon-background.png")
    mark(512, WHITE, GREEN, 0.44).save(ASSETS / "android-icon-foreground.png", optimize=True)
    mark(512, WHITE, (0, 0, 0, 0), 0.44).save(ASSETS / "android-icon-monochrome.png", optimize=True)
    mark(1024, GREEN, WHITE, 0.6).save(ASSETS / "splash-icon.png", optimize=True)
    solid(48, 0.7).save(ASSETS / "favicon.png", optimize=True)
    # PWA: обычные иконки, maskable (с полями) и иконка для iPhone (без прозрачности).
    solid(192, 0.56).save(WEB / "icon-192.png", optimize=True)
    solid(512, 0.56).save(WEB / "icon-512.png", optimize=True)
    solid(512, 0.44).save(WEB / "icon-maskable-512.png", optimize=True)
    solid(180, 0.56).save(WEB / "apple-touch-icon.png", optimize=True)
    print("иконки готовы")


if __name__ == "__main__":
    main()
