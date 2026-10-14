"""Скачивает фото демо-каталога (fixtures/demo_images/manifest.json) из интернета.

    python3 scripts/fetch_demo_images.py [--force]

Источники по очереди: Unsplash (Unsplash License — бесплатно, в т.ч. коммерчески) и
Openverse (только лицензии, разрешающие коммерческое использование: CC0, CC BY, CC BY-SA).
Авторы и лицензии записываются в fixtures/demo_images/CREDITS.md. Уже скачанные файлы
пропускаются (кроме --force). Нужны интернет и Pillow (обрезка до квадрата 800×800).
"""

import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "fixtures/demo_images"
SIZE = 800
BROWSER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36"


def get(url: str, accept: str = "*/*") -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER, "Accept": accept})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def unsplash(query: str) -> list[dict]:
    """Фото со страницы поиска Unsplash (без Unsplash+ — у них адрес premium_photo-…)."""
    slug = re.sub(r"\s+", "-", query.strip().lower())
    html = get(f"https://unsplash.com/s/photos/{urllib.parse.quote(slug)}", "text/html").decode()
    ids = list(dict.fromkeys(re.findall(r"images\.unsplash\.com/(photo-[0-9]+-[0-9a-f]+)", html)))
    return [
        {
            "id": f"unsplash:{photo}",
            "url": f"https://images.unsplash.com/{photo}?w={SIZE * 2}&q=85&fm=jpg",
            "author": "Unsplash",
            "author_url": "https://unsplash.com",
            "source": f"https://images.unsplash.com/{photo}",
            "license": "Unsplash License",
        }
        for photo in ids
    ]


def openverse(query: str) -> list[dict]:
    params = urllib.parse.urlencode(
        {"q": query, "license_type": "commercial", "mature": "false", "page_size": 20}
    )
    data = json.loads(get(f"https://api.openverse.org/v1/images/?{params}", "application/json"))
    return [
        {
            "id": f"openverse:{item['id']}",
            "url": item["url"],
            "author": item.get("creator") or "неизвестен",
            "author_url": item.get("creator_url") or item.get("foreign_landing_url") or "",
            "source": item.get("foreign_landing_url") or item["url"],
            "license": f"CC {item['license'].upper()} {item.get('license_version') or ''}".strip(),
        }
        for item in data.get("results", [])
        if (item.get("width") or 0) >= 600 and (item.get("height") or 0) >= 600
    ]


def square_jpeg(raw: bytes) -> bytes:
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    side = min(image.size)
    left, top = (image.width - side) // 2, (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize((SIZE, SIZE), Image.LANCZOS)
    out = io.BytesIO()
    image.save(out, "JPEG", quality=80, optimize=True, progressive=True)
    return out.getvalue()


def fetch_one(query: str, used: set[str]) -> tuple[dict, bytes]:
    errors = []
    for source in (unsplash, openverse):
        try:
            for candidate in source(query)[:6]:
                if candidate["id"] in used:
                    continue
                try:
                    return candidate, square_jpeg(get(candidate["url"], "image/*"))
                except Exception as exc:  # битая ссылка — следующий кандидат
                    errors.append(f"{candidate['url']}: {exc}")
        except Exception as exc:
            errors.append(f"{source.__name__}: {exc}")
    raise RuntimeError("; ".join(errors) or "нет результатов")


def main(force: bool) -> int:
    manifest = json.loads((IMAGES / "manifest.json").read_text(encoding="utf-8"))
    credits_path = IMAGES / "credits.json"
    credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else {}
    files = {image["file"] for product in manifest for image in product["images"]}
    credits = {name: c for name, c in credits.items() if name in files and "license" in c}
    used = {c["id"] for c in credits.values()}
    failed = []

    for product in manifest:
        for image in product["images"]:
            target = IMAGES / image["file"]
            if target.exists() and image["file"] in credits and not force:
                continue
            try:
                photo, data = fetch_one(image["query"], used)
                target.write_bytes(data)
                used.add(photo["id"])
                credits[image["file"]] = {**photo, "query": image["query"]}
                print(f"ok   {image['file']} ← {photo['source']}")
            except Exception as exc:  # отчёт по всем файлам, а не падение на первом
                failed.append(image["file"])
                print(f"FAIL {image['file']}: {exc}", file=sys.stderr)
            time.sleep(1)  # вежливо к источникам

    credits_path.write_text(
        json.dumps(credits, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Фото демо-каталога",
        "",
        "Только для демонстрации витрины — перед запуском замените на фото своих товаров.",
        "Источники: [Unsplash](https://unsplash.com/license) и [Openverse](https://openverse.org)",
        "(лицензии, разрешающие коммерческое использование).",
        "",
        "| Файл | Автор | Лицензия | Источник |",
        "|---|---|---|---|",
    ]
    for name, c in sorted(credits.items()):
        author = f"[{c['author']}]({c['author_url']})" if c["author_url"] else c["author"]
        lines.append(f"| {name} | {author} | {c['license']} | {c['source']} |")
    (IMAGES / "CREDITS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"готово, ошибок: {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main("--force" in sys.argv))
