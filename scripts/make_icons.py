"""Иконки магазина в стиле «Лайм-тек»: приложение (Android/iOS), адаптивная иконка Android,
заставка, веб-витрина (фавикон и «На экран Домой»).

    cd mobile && npm ci && cd .. && python3 scripts/make_icons.py

Знак — «Di» шрифтом Unbounded Bold, лайм (accent) на почти чёрном зелёном (ink) — значения
из docs/design/lime-tech/tokens.json. Шрифт берётся из пакета @expo-google-fonts/unbounded
(mobile/node_modules), поэтому сначала нужен npm ci. Нужен Pillow.
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "mobile/assets"
# Веб-витрина (Django-статика): фавикон и иконки «На экран Домой».
STOREFRONT = ROOT / "web/static/web/icons"
TOKENS = json.loads((ROOT / "docs/design/lime-tech/tokens.json").read_text(encoding="utf-8"))
FONT = ROOT / "mobile/node_modules/@expo-google-fonts/unbounded/700Bold/Unbounded_700Bold.ttf"
SS = 4  # суперсэмплинг для гладких краёв


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


INK = rgb(TOKENS["color"]["light"]["ink"])  # #13261C
LIME = rgb(TOKENS["color"]["light"]["accent"])  # #C6F432
WHITE = (255, 255, 255)


def wordmark(size: int, color, scale: float) -> Image.Image:
    """«Di» по центру прозрачного холста; scale — доля ширины холста под надпись."""
    if not FONT.exists():
        raise SystemExit(f"нет шрифта {FONT.relative_to(ROOT)}: выполните npm ci в mobile/")
    big = size * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_size = int(big * scale * 0.62)
    font = ImageFont.truetype(str(FONT), font_size)
    # Оптический центр: «Di» без нижних выносных — центрируем по рамке глифов.
    left, top, right, bottom = draw.textbbox((0, 0), "Di", font=font)
    x = (big - (right - left)) / 2 - left
    y = (big - (bottom - top)) / 2 - top
    draw.text((x, y), "Di", font=font, fill=color)
    return img.resize((size, size), Image.LANCZOS)


def solid(size: int, scale: float) -> Image.Image:
    base = Image.new("RGBA", (size, size), INK + (255,))
    base.alpha_composite(wordmark(size, LIME, scale))
    return base.convert("RGB")


def plate(size: int, plate_scale: float, mark_scale: float) -> Image.Image:
    """Скруглённая плашка ink с лаймовым «Di» на прозрачном фоне (заставка, favicon)."""
    big = size * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    side = big * plate_scale
    offset = (big - side) / 2
    ImageDraw.Draw(img).rounded_rectangle(
        (offset, offset, offset + side, offset + side), radius=side * 0.3, fill=INK + (255,)
    )
    img = img.resize((size, size), Image.LANCZOS)
    img.alpha_composite(wordmark(size, LIME, mark_scale))
    return img


def main() -> None:
    solid(1024, 0.5).save(ASSETS / "icon.png", optimize=True)
    # Адаптивная иконка Android: система обрезает края, знак — в центральных ~60%.
    Image.new("RGB", (512, 512), INK).save(ASSETS / "android-icon-background.png")
    wordmark(512, LIME, 0.36).save(ASSETS / "android-icon-foreground.png", optimize=True)
    wordmark(512, WHITE, 0.36).save(ASSETS / "android-icon-monochrome.png", optimize=True)
    # Заставка: плашка видна и на светлом (#EBF1E2), и на тёмном (#070E0A) фоне.
    plate(1024, 0.72, 0.42).save(ASSETS / "splash-icon.png", optimize=True)
    # Витрина (PWA): обычные иконки, maskable (с полями) и иконка для iPhone (без прозрачности).
    STOREFRONT.mkdir(parents=True, exist_ok=True)
    plate(48, 1.0, 0.62).save(STOREFRONT / "favicon-48.png", optimize=True)
    solid(192, 0.5).save(STOREFRONT / "icon-192.png", optimize=True)
    solid(512, 0.5).save(STOREFRONT / "icon-512.png", optimize=True)
    solid(512, 0.36).save(STOREFRONT / "icon-maskable-512.png", optimize=True)
    solid(180, 0.5).save(STOREFRONT / "apple-touch-icon.png", optimize=True)
    print("иконки готовы")


if __name__ == "__main__":
    main()
