"""Скачивает фото демо-каталога (fixtures/demo_images/manifest.json) с Unsplash.

    python3 scripts/fetch_demo_images.py [--force]

Фото Unsplash распространяются по Unsplash License (бесплатно, в т.ч. коммерчески, без
обязательной атрибуции); авторы всё равно перечислены в fixtures/demo_images/CREDITS.md.
Нужен интернет; уже скачанные файлы пропускаются (кроме --force). Используются только
стандартная библиотека и Pillow (обрезка до квадрата 800×800).
"""

import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "fixtures/demo_images"
SIZE = 800
HEADERS = {"User-Agent": "Mozilla/5.0 (DiDi-shop demo seed)", "Accept": "application/json"}


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def search(query: str) -> list[dict]:
    """Бесплатные (не Unsplash+) фото по запросу, квадратные и горизонтальные первыми."""
    params = urllib.parse.urlencode({"query": query, "per_page": 20})
    data = json.loads(get(f"https://unsplash.com/napi/search/photos?{params}"))
    free = [p for p in data.get("results", []) if not p.get("premium") and not p.get("plus")]
    return sorted(free, key=lambda p: p["height"] / p["width"] > 1.3)


def square_jpeg(raw: bytes) -> bytes:
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    side = min(image.size)
    left, top = (image.width - side) // 2, (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize((SIZE, SIZE), Image.LANCZOS)
    out = io.BytesIO()
    image.save(out, "JPEG", quality=80, optimize=True, progressive=True)
    return out.getvalue()


def main(force: bool) -> int:
    manifest = json.loads((IMAGES / "manifest.json").read_text(encoding="utf-8"))
    credits_path = IMAGES / "credits.json"
    credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else {}
    used = {c["id"] for c in credits.values()}
    failed = []

    for product in manifest:
        for image in product["images"]:
            target = IMAGES / image["file"]
            if target.exists() and not force:
                continue
            try:
                candidates = [p for p in search(image["query"]) if p["id"] not in used]
                if not candidates:
                    raise RuntimeError("нет результатов")
                photo = candidates[0]
                raw = get(photo["urls"]["raw"] + f"&w={SIZE * 2}&q=85&fm=jpg")
                target.write_bytes(square_jpeg(raw))
                used.add(photo["id"])
                credits[image["file"]] = {
                    "id": photo["id"],
                    "author": photo["user"]["name"],
                    "author_url": photo["user"]["links"]["html"],
                    "photo_url": photo["links"]["html"],
                    "query": image["query"],
                }
                print(f"ok   {image['file']} ← {photo['links']['html']}")
            except Exception as exc:  # отчёт по всем файлам, а не падение на первом
                failed.append(image["file"])
                print(f"FAIL {image['file']}: {exc}", file=sys.stderr)
            time.sleep(1)  # вежливо к Unsplash

    credits_path.write_text(
        json.dumps(credits, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Фото демо-каталога",
        "",
        "Источник — [Unsplash](https://unsplash.com), [Unsplash License](https://unsplash.com/license):",
        "бесплатно, в том числе для коммерческого использования. Только для демонстрации витрины —",
        "перед запуском замените на фото своих товаров.",
        "",
        "| Файл | Автор | Фото |",
        "|---|---|---|",
    ]
    for name, c in sorted(credits.items()):
        lines.append(f"| {name} | [{c['author']}]({c['author_url']}) | {c['photo_url']} |")
    (IMAGES / "CREDITS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"готово, ошибок: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main("--force" in sys.argv))
