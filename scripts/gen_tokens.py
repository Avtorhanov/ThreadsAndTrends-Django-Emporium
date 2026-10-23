"""Токены «Лайм-тек»: docs/design/lime-tech/tokens.json → код клиентов.

    python3 scripts/gen_tokens.py           # перегенерировать файлы
    python3 scripts/gen_tokens.py --check   # CI: файлы актуальны и контраст текста ≥ 4.5:1

Выход:
- mobile/src/theme/tokens.ts — типизированные токены для приложения (React Native);
- docs/design/lime-tech/tokens.css — CSS-переменные (справочная копия рядом с tokens.json);
- web/static/web/css/tokens.css — те же переменные для веб-витрины (статика Django);
- admin-panel/src/tokens.css — те же переменные для панели администратора (React + Vite).

Единственный источник значений — tokens.json; сгенерированные файлы руками не правятся.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs/design/lime-tech/tokens.json"
TS_OUT = ROOT / "mobile/src/theme/tokens.ts"
CSS_OUT = ROOT / "docs/design/lime-tech/tokens.css"
WEB_CSS_OUT = ROOT / "web/static/web/css/tokens.css"
ADMIN_CSS_OUT = ROOT / "admin-panel/src/tokens.css"
HEADER = (
    "Сгенерировано scripts/gen_tokens.py из docs/design/lime-tech/tokens.json — не редактировать."
)

THEMES = ("light", "dark")
STOPS_TYPE = "readonly [string, string, string] | null"

# Пары «текст → фон», которые обязаны держать контраст ≥ 4.5:1 в обеих темах (WCAG AA).
# Фон «card» в тёмной теме — градиент: проверяются все его остановки.
TEXT_PAIRS = [
    ("ink", "bg"),
    ("ink", "surface"),
    ("ink", "card"),
    ("muted", "bg"),
    ("muted", "surface"),
    ("muted", "card"),
    ("brand", "bg"),
    ("brand", "surface"),
    ("brandInk", "brand"),
    ("onAccent", "accent"),
    ("segOnInk", "segOnBg"),
    ("tagInk", "tag"),
    ("navInk", "nav"),
    ("navActiveInk", "accent"),
    ("ctaInk", "ctaBg"),
    ("ctaDoneInk", "ctaFill"),
    ("neutral", "neutralBg"),
    ("danger", "dangerBg"),
    ("danger", "surface"),
    ("danger", "bg"),
    ("success", "successBg"),
    ("success", "surface"),
    ("warning", "warningBg"),
    ("info", "infoBg"),
]
# Зачёркнутая старая цена — декоративный текст рядом с основной ценой: достаточно 3:1.
LARGE_PAIRS = [("strike", "card"), ("strike", "surface")]


def camel_to_kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def hex_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def luminance(value: str) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in hex_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def backgrounds(palette: dict, key: str) -> list[str]:
    if key == "card" and "cardStops" in palette:
        return list(palette["cardStops"])
    return [palette[key]]


def check_contrast(tokens: dict) -> list[str]:
    problems = []
    for theme in THEMES:
        palette = tokens["color"][theme]
        for pairs, minimum in ((TEXT_PAIRS, 4.5), (LARGE_PAIRS, 3.0)):
            for fg, bg in pairs:
                for bg_value in backgrounds(palette, bg):
                    ratio = contrast(palette[fg], bg_value)
                    if ratio < minimum:
                        problems.append(
                            f"{theme}: {fg} {palette[fg]} на {bg} {bg_value}"
                            f" — {ratio:.2f} < {minimum}"
                        )
    return problems


def bezier(value: str) -> list[float]:
    match = re.fullmatch(r"cubic-bezier\(([^)]*)\)", value)
    if not match:
        raise ValueError(f"ожидалась cubic-bezier(...): {value}")
    return [float(part) for part in match.group(1).split(",")]


def palette_for_native(palette: dict) -> dict:
    """RN не понимает CSS-градиент в backgroundColor: card — сплошной цвет (средняя остановка),
    сам градиент — cardStops (null, если карточка сплошная)."""
    result = {key: value for key, value in palette.items() if key not in ("card", "cardStops")}
    stops = palette.get("cardStops")
    result["card"] = stops[1] if stops else palette["card"]
    result["cardStops"] = stops
    return result


def ts(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def render_ts(tokens: dict) -> str:
    palettes = {theme: palette_for_native(tokens["color"][theme]) for theme in THEMES}
    keys = sorted(set(palettes["light"]) | set(palettes["dark"]))
    missing = {theme: [k for k in keys if k not in palettes[theme]] for theme in THEMES}
    if any(missing.values()):
        raise SystemExit(f"в темах разный набор цветов: {missing}")

    palette_type = "\n".join(
        f"  {key}: {STOPS_TYPE if key == 'cardStops' else 'string'};" for key in keys
    )
    shadow_keys = sorted(tokens["shadow"]["light"])
    shadow_type = "\n".join(f"  {key}: string;" for key in shadow_keys)
    tones = {k: v for k, v in tokens["color"]["productTones"].items() if k != "comment"}
    motion = dict(tokens["motion"])
    easing = {name: bezier(motion.pop(name)) for name in ("easeOut", "easeSoft", "easeTab")}

    return f"""// {HEADER}
// Версия токенов: {tokens["version"]} ({tokens["updated"]}).

export type ThemeName = "light" | "dark";

export type Palette = {{
{palette_type}
}};

export type Shadows = {{
{shadow_type}
}};

export const palettes: Record<ThemeName, Palette> = {ts(palettes)};

/** CSS box-shadow (несколько слоёв, inset) — стиль `boxShadow` React Native (новая архитектура). */
export const shadows: Record<ThemeName, Shadows> = {ts(tokens["shadow"])};

/** Фон плашки фото: [светлая тема, тёмная тема]. */
export const productTones = {ts(tones)} as const;

export type ProductTone = keyof typeof productTones;

export const radius = {ts(tokens["radius"])} as const;

export const space = {ts(tokens["space"])} as const;

export const size = {ts(tokens["size"])} as const;

export const font = {ts(tokens["font"])} as const;

/** Кривые cubic-bezier(x1, y1, x2, y2) — для Easing.bezier. */
export const easing = {ts(easing)} as const;

export const motion = {ts(motion)} as const;
"""


def css_vars(palette: dict, shadow: dict, indent: str) -> list[str]:
    lines = [
        f"{indent}--{camel_to_kebab(key)}: {value};"
        for key, value in palette.items()
        if key != "cardStops"
    ]
    lines += [f"{indent}--shadow-{camel_to_kebab(key)}: {value};" for key, value in shadow.items()]
    return lines


def render_css(tokens: dict) -> str:
    light, dark = tokens["color"]["light"], tokens["color"]["dark"]
    tones = {k: v for k, v in tokens["color"]["productTones"].items() if k != "comment"}
    common = [f"  --radius-{camel_to_kebab(k)}: {v}px;" for k, v in tokens["radius"].items()]
    common += [f"  --space-{camel_to_kebab(k)}: {v}px;" for k, v in tokens["space"].items()]
    common += [f"  --size-{camel_to_kebab(k)}: {v}px;" for k, v in tokens["size"].items()]
    common += [
        f"  --font-display: '{tokens['font']['display']['family']}', system-ui, sans-serif;",
        f"  --font-text: '{tokens['font']['text']['family']}', system-ui, sans-serif;",
    ]
    common += [
        f"  --{camel_to_kebab(k)}: {tokens['motion'][k]};"
        for k in ("easeOut", "easeSoft", "easeTab")
    ]
    light_tones = [f"  --tone-{k}: {v[0]};" for k, v in tones.items()]
    dark_tones = [f"  --tone-{k}: {v[1]};" for k, v in tones.items()]

    def block(selector: str, lines: list[str]) -> str:
        return selector + " {\n" + "\n".join(lines) + "\n}\n"

    dark_lines = css_vars(dark, tokens["shadow"]["dark"], "  ") + dark_tones
    nested = [line.replace("  ", "    ", 1) for line in dark_lines]
    return (
        f"/* {HEADER} */\n"
        f"/* Версия токенов: {tokens['version']} ({tokens['updated']}).\n"
        '   Тёмная тема — data-theme="dark"\n'
        "   или системная (prefers-color-scheme), если data-theme не задан явно. */\n\n"
        + block(":root", common + css_vars(light, tokens["shadow"]["light"], "  ") + light_tones)
        + "\n"
        + block(':root[data-theme="dark"]', dark_lines)
        + "\n@media (prefers-color-scheme: dark) {\n"
        + '  :root:not([data-theme="light"]) {\n'
        + "\n".join(nested)
        + "\n  }\n}\n"
    )


def main() -> int:
    check = "--check" in sys.argv[1:]
    tokens = json.loads(SOURCE.read_text(encoding="utf-8"))
    problems = check_contrast(tokens)
    css = render_css(tokens)
    outputs = {
        TS_OUT: render_ts(tokens),
        CSS_OUT: css,
        WEB_CSS_OUT: css,
        ADMIN_CSS_OUT: css,
    }

    if check:
        for path, content in outputs.items():
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                problems.append(f"{path.relative_to(ROOT)} устарел: python3 scripts/gen_tokens.py")
    else:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"записан {path.relative_to(ROOT)}")

    for problem in problems:
        print(f"ошибка: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
