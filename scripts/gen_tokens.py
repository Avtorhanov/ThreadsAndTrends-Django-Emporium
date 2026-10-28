"""Токены «Лайм-тек»: docs/design/lime-tech/tokens.json → код клиентов.

    python3 scripts/gen_tokens.py           # перегенерировать файлы
    python3 scripts/gen_tokens.py --check   # CI: файлы актуальны и контраст текста ≥ 4.5:1
                                            #     во всех палитрах и акцентах «Своей»

Выход:
- mobile/src/theme/tokens.ts — типизированные токены для приложения (React Native);
- web/static/web/css/tokens.css — CSS-переменные обеих тем для веб-витрины (статика Django);
- admin-panel/src/tokens.css — те же переменные для панели администратора (React + Vite);
- content/palettes.json — список палитр и акцентов для сервера (белый список, цвета образцов).

Палитры покупателя (tokens.json → palettes): переопределения цветов базовой «Лайм-тек»;
«Своя» (custom) — нейтральная основа + один из проверенных акцентов (accents). Тени палитр
тонируются автоматически: зелёные оттенки базы заменяются на accent/brand/ink палитры.
На сайте палитру выбирают атрибуты <html>: data-palette, data-accent, data-radius, data-text.

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
WEB_CSS_OUT = ROOT / "web/static/web/css/tokens.css"
ADMIN_CSS_OUT = ROOT / "admin-panel/src/tokens.css"
PY_JSON_OUT = ROOT / "content/palettes.json"
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


def entries(section: dict) -> dict:
    """Раздел tokens.json без служебного ключа comment."""
    return {key: value for key, value in section.items() if key != "comment"}


def resolve(tokens: dict, theme: str, palette: str = "lime", accent: str | None = None) -> dict:
    """Полная палитра темы: база → переопределения палитры → акцент «Своей»."""
    result = dict(tokens["color"][theme])
    result.update(tokens["palettes"][palette][theme])
    if accent is not None:
        result.update(tokens["accents"][accent][theme])
    return result


def variants(tokens: dict):
    """(название, тема, палитра, акцент) — всё, что может увидеть покупатель."""
    for name in entries(tokens["palettes"]):
        accents = list(entries(tokens["accents"])) if name == "custom" else [None]
        for accent in accents:
            for theme in THEMES:
                label = f"{name}/{accent}" if accent else name
                yield label, theme, name, accent


def check_contrast(tokens: dict) -> list[str]:
    problems = []
    for label, theme, name, accent in variants(tokens):
        palette = resolve(tokens, theme, name, accent)
        for pairs, minimum in ((TEXT_PAIRS, 4.5), (LARGE_PAIRS, 3.0)):
            for fg, bg in pairs:
                for bg_value in backgrounds(palette, bg):
                    ratio = contrast(palette[fg], bg_value)
                    if ratio < minimum:
                        problems.append(
                            f"{label} {theme}: {fg} {palette[fg]} на {bg} {bg_value}"
                            f" — {ratio:.2f} < {minimum}"
                        )
    return problems


def rgb_triplet(value: str) -> str:
    return ",".join(str(round(c * 255)) for c in hex_rgb(value))


# Оттенки базовых теней «Лайм-тек» → цвета палитры.
SHADOW_TINTS = (("198,244,50", "accent"), ("31,77,58", "brand"), ("19,38,28", "ink"))


def tinted_shadows(tokens: dict, theme: str, palette: dict) -> dict:
    result = {}
    for key, value in tokens["shadow"][theme].items():
        for source, color_key in SHADOW_TINTS:
            # В тёмной теме brand = accent, а тени — чёрные: тонируется только ореол акцента.
            if theme == "dark" and color_key != "accent":
                continue
            value = value.replace(source, rgb_triplet(palette[color_key]))
        result[key] = value
    return result


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

    palette_names = list(entries(tokens["palettes"]))
    accent_names = list(entries(tokens["accents"]))
    palette_union = " | ".join(json.dumps(name) for name in palette_names)
    accent_union = " | ".join(json.dumps(name) for name in accent_names)
    palette_list = [
        {"key": key, "name": value["name"], "group": value["group"], "note": value["note"]}
        for key, value in entries(tokens["palettes"]).items()
    ]
    palette_themes = {
        name: {theme: palette_for_native(resolve(tokens, theme, name)) for theme in THEMES}
        for name in palette_names
    }
    palette_shadows = {
        name: {
            theme: tinted_shadows(tokens, theme, resolve(tokens, theme, name)) for theme in THEMES
        }
        for name in palette_names
    }
    accent_map = {
        key: {
            "name": value["name"],
            "color": value["color"],
            "light": value["light"],
            "dark": value["dark"],
        }
        for key, value in entries(tokens["accents"]).items()
    }
    accent_shadows = {
        key: {
            theme: tinted_shadows(tokens, theme, resolve(tokens, theme, "custom", key))
            for theme in THEMES
        }
        for key in accent_names
    }

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

export type PaletteName = {palette_union};
export type AccentName = {accent_union};
export type PaletteGroup = "bright" | "calm" | "custom";

export type PaletteInfo = {{
  key: PaletteName;
  name: string;
  group: PaletteGroup;
  note: string;
}};

export type AccentInfo = {{
  name: string;
  color: string;
  light: Partial<Palette>;
  dark: Partial<Palette>;
}};

type ByTheme<T> = Record<ThemeName, T>;

/** Палитры покупателя по порядку показа (профиль, панель → «Тема»). */
export const paletteList: readonly PaletteInfo[] = {ts(palette_list)};

/** Полные палитры обеих тем для каждой палитры покупателя. */
export const paletteThemes: Record<PaletteName, ByTheme<Palette>> = {ts(palette_themes)};

export const paletteShadows: Record<PaletteName, ByTheme<Shadows>> = {ts(palette_shadows)};

/** Акценты «Своей»: цвет, подпись и переопределения поверх paletteThemes.custom. */
export const accents: Record<AccentName, AccentInfo> = {ts(accent_map)};

export const accentShadows: Record<AccentName, ByTheme<Shadows>> = {ts(accent_shadows)};

/** Углы: множитель радиусов. Размер текста: множитель кегля (поверх системного). */
export const radiusScale = {ts(entries(tokens["radiusScale"]))} as const;

export type RadiusMode = keyof typeof radiusScale;

export const textScale = {ts(entries(tokens["textScale"]))} as const;

export type TextMode = keyof typeof textScale;

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
        f"  --font-secondary: '{tokens['font']['secondary']['family']}', system-ui, sans-serif;",
    ]
    common += [
        f"  --{camel_to_kebab(k)}: {tokens['motion'][k]};"
        for k in ("easeOut", "easeSoft", "easeTab")
    ]
    light_tones = [f"  --tone-{k}: {v[0]};" for k, v in tones.items()]
    dark_tones = [f"  --tone-{k}: {v[1]};" for k, v in tones.items()]

    def block(selector: str, lines: list[str]) -> str:
        return selector + " {\n" + "\n".join(lines) + "\n}\n"

    common += ["  --radius-scale: 1;", "  --text-scale: 1;"]
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
        + render_palettes_css(tokens)
        + render_scales_css(tokens)
    )


def override_block(tokens: dict, selector: str, palette: str, accent: str | None) -> str:
    """Переопределения палитры (и акцента) для обеих тем. Набор ключей в светлой и тёмной
    одинаковый: иначе светлое значение палитры «протекло» бы в тёмную тему."""
    layers = [tokens["palettes"][palette]]
    if accent is not None:
        layers = [tokens["accents"][accent]]
    keys = sorted({key for layer in layers for theme in THEMES for key in layer[theme]})
    out = []
    lines_by_theme = {}
    for theme in THEMES:
        full = resolve(tokens, theme, palette, accent)
        colors = {key: full[key] for key in keys if key != "cardStops"}
        shadow = tinted_shadows(tokens, theme, full)
        lines_by_theme[theme] = css_vars(colors, shadow, "  ")
    out.append(selector + " {\n" + "\n".join(lines_by_theme["light"]) + "\n}\n")
    out.append(
        f'{selector}[data-theme="dark"]' + " {\n" + "\n".join(lines_by_theme["dark"]) + "\n}\n"
    )
    nested = [line.replace("  ", "    ", 1) for line in lines_by_theme["dark"]]
    out.append(
        "@media (prefers-color-scheme: dark) {\n"
        + f'  {selector}:not([data-theme="light"])'
        + " {\n"
        + "\n".join(nested)
        + "\n  }\n}\n"
    )
    return "\n".join(out)


def render_palettes_css(tokens: dict) -> str:
    parts = ["\n/* Палитры покупателя: <html data-palette=…> (lime — без атрибута). */\n"]
    for name in entries(tokens["palettes"]):
        if name == "lime":
            continue
        parts.append(override_block(tokens, f':root[data-palette="{name}"]', name, None))
    parts.append("\n/* «Своя»: проверенный акцент — <html data-palette=custom data-accent=…>. */\n")
    for accent in entries(tokens["accents"]):
        selector = f':root[data-palette="custom"][data-accent="{accent}"]'
        parts.append(override_block(tokens, selector, "custom", accent))
    return "\n".join(parts)


def render_scales_css(tokens: dict) -> str:
    parts = ["\n/* Углы: data-radius=sharp|soft (normal — без атрибута). */\n"]
    for mode, scale in entries(tokens["radiusScale"]).items():
        if scale == 1:
            continue
        lines = [
            f"  --radius-{camel_to_kebab(key)}: {round(value * scale)}px;"
            for key, value in tokens["radius"].items()
        ]
        lines.append(f"  --radius-scale: {scale};")
        parts.append(f':root[data-radius="{mode}"]' + " {\n" + "\n".join(lines) + "\n}\n")
    parts.append("\n/* Размер текста: data-text=m|l (s — без атрибута). */\n")
    for mode, scale in entries(tokens["textScale"]).items():
        if scale == 1:
            continue
        parts.append(f':root[data-text="{mode}"] {{\n  --text-scale: {scale};\n}}\n')
    return "\n".join(parts)


def render_palettes_json(tokens: dict) -> str:
    """Что нужно серверу: белый список палитр/акцентов/углов/размеров и цвета образцов."""
    palettes = []
    for key, value in entries(tokens["palettes"]).items():
        light, dark = resolve(tokens, "light", key), resolve(tokens, "dark", key)
        palettes.append(
            {
                "key": key,
                "name": value["name"],
                "group": value["group"],
                "note": value["note"],
                "accent": light["accent"],
                "brand": light["brand"],
                "bg": {"light": light["bg"], "dark": dark["bg"]},
            }
        )
    accents = [
        {
            "key": key,
            "name": value["name"],
            "color": value["color"],
            "on": value["light"]["onAccent"],
        }
        for key, value in entries(tokens["accents"]).items()
    ]
    data = {
        "comment": HEADER,
        "palettes": palettes,
        "accents": accents,
        "radius": entries(tokens["radiusScale"]),
        "text": entries(tokens["textScale"]),
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    check = "--check" in sys.argv[1:]
    tokens = json.loads(SOURCE.read_text(encoding="utf-8"))
    problems = check_contrast(tokens)
    css = render_css(tokens)
    outputs = {
        TS_OUT: render_ts(tokens),
        WEB_CSS_OUT: css,
        ADMIN_CSS_OUT: css,
        PY_JSON_OUT: render_palettes_json(tokens),
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
