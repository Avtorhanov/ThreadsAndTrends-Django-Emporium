"""Фото демо-каталога (fixtures/demo_images/manifest.json) из интернета.

    python3 scripts/fetch_demo_images.py [--force]
    python3 scripts/fetch_demo_images.py --candidates OUT --only a-1.jpg,b-1.jpg

Обычный режим: для каждого фото из manifest скачивается закреплённый кандидат ("pick":
"openverse:<id>" или "unsplash:photo-…"), а без закрепления — первый подходящий результат
поиска ("query"). Уже скачанные файлы пропускаются (кроме --force и смены "pick").

Режим --candidates: для перечисленных файлов собирает до 8 кандидатов по каждому запросу
("query" и "queries") и кладёт в OUT контактный лист с номерами и candidates.json — по нему
выбирается "pick".

Источники: Openverse (только лицензии, разрешающие коммерческое использование: CC0, PDM,
CC BY, CC BY-SA) и Unsplash (Unsplash License). Авторы и лицензии — в CREDITS.md.
Нужны интернет и Pillow (обрезка до квадрата 800×800).
"""

import argparse
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "fixtures/demo_images"
SIZE = 800
BROWSER = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140 Safari/537.36"
)
OPENVERSE = "https://api.openverse.org/v1/images/"


def get(url: str, accept: str = "*/*") -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER, "Accept": accept})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def unsplash_item(photo: str) -> dict:
    return {
        "id": f"unsplash:{photo}",
        "url": f"https://images.unsplash.com/{photo}?w={SIZE * 2}&q=85&fm=jpg",
        "thumb": f"https://images.unsplash.com/{photo}?w=300&q=70&fm=jpg",
        "author": "Unsplash",
        "author_url": "https://unsplash.com",
        "source": f"https://images.unsplash.com/{photo}",
        "license": "Unsplash License",
    }


def unsplash(query: str) -> list[dict]:
    """Фото со страницы поиска Unsplash (без Unsplash+ — у них адрес premium_photo-…)."""
    slug = re.sub(r"\s+", "-", query.strip().lower())
    html = get(f"https://unsplash.com/s/photos/{urllib.parse.quote(slug)}", "text/html").decode()
    ids = re.findall(r"images\.unsplash\.com/(photo-[0-9]+-[0-9a-f]+)", html)
    return [unsplash_item(photo) for photo in dict.fromkeys(ids)]


def openverse_item(item: dict) -> dict:
    license_name = item["license"].upper()
    if license_name not in ("CC0", "PDM"):
        license_name = f"CC {license_name} {item.get('license_version') or ''}".strip()
    return {
        "id": f"openverse:{item['id']}",
        "url": item["url"],
        "thumb": item.get("thumbnail") or item["url"],
        "author": item.get("creator") or "неизвестен",
        "author_url": item.get("creator_url") or item.get("foreign_landing_url") or "",
        "source": item.get("foreign_landing_url") or item["url"],
        "license": license_name,
    }


def openverse(query: str) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "license_type": "commercial",
            "category": "photograph",
            "mature": "false",
            "page_size": 20,
        }
    )
    data = json.loads(get(f"{OPENVERSE}?{params}", "application/json"))
    return [
        openverse_item(item)
        for item in data.get("results", [])
        if (item.get("width") or 0) >= 600 and (item.get("height") or 0) >= 600
    ]


def resolve(pick: str) -> dict:
    """Закреплённый кандидат по id из candidates.json."""
    source, _, key = pick.partition(":")
    if source == "unsplash":
        return unsplash_item(key)
    if source == "openverse":
        return openverse_item(json.loads(get(f"{OPENVERSE}{key}/", "application/json")))
    raise ValueError(f"неизвестный источник: {pick}")


def square_jpeg(raw: bytes, size: int = SIZE) -> bytes:
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    side = min(image.size)
    left, top = (image.width - side) // 2, (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
    out = io.BytesIO()
    image.save(out, "JPEG", quality=80, optimize=True, progressive=True)
    return out.getvalue()


def search_all(queries: list[str]) -> list[dict]:
    found: dict[str, dict] = {}
    for query in queries:
        for source in (unsplash, openverse):
            try:
                for item in source(query)[:8]:
                    found.setdefault(item["id"], item)
            except Exception as exc:
                print(f"     {source.__name__} «{query}»: {exc}", file=sys.stderr)
            time.sleep(3)  # лимит Openverse для анонимных запросов — 20 в минуту
    return list(found.values())


def fetch_first(queries: list[str], used: set[str]) -> tuple[dict, bytes]:
    errors = []
    for candidate in search_all(queries):
        if candidate["id"] in used:
            continue
        try:
            return candidate, square_jpeg(get(candidate["url"], "image/*"))
        except Exception as exc:  # битая ссылка — следующий кандидат
            errors.append(f"{candidate['url']}: {exc}")
    raise RuntimeError("; ".join(errors[-3:]) or "нет результатов")


def queries_of(image: dict) -> list[str]:
    return [image["query"], *image.get("queries", [])]


def candidates(manifest: list[dict], only: set[str], out: Path) -> int:
    """Контактные листы кандидатов: OUT/<файл>.jpg с номерами, OUT/candidates.json."""
    out.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    result = {}
    for product in manifest:
        for image in product["images"]:
            if image["file"] not in only:
                continue
            items = search_all(queries_of(image))[:24]
            thumbs, ids = [], []
            for item in items:
                try:
                    thumbs.append(Image.open(io.BytesIO(square_jpeg(get(item["thumb"]), 240))))
                    ids.append(item["id"])
                except Exception:
                    continue
            result[image["file"]] = ids
            cols = 6
            rows = max(1, (len(thumbs) + cols - 1) // cols)
            sheet = Image.new("RGB", (cols * 240, rows * 240 + 40), "white")
            draw = ImageDraw.Draw(sheet)
            title = f"{image['file']}: {', '.join(queries_of(image))}"
            draw.text((8, 8), title, fill="black", font=font)
            for n, thumb in enumerate(thumbs):
                x, y = (n % cols) * 240, (n // cols) * 240 + 40
                sheet.paste(thumb, (x, y))
                draw.rectangle((x, y, x + 34, y + 28), fill="yellow")
                draw.text((x + 4, y + 2), str(n), fill="black", font=font)
            sheet.save(out / image["file"], quality=75)
            print(f"кандидаты {image['file']}: {len(ids)}")
    (out / "candidates.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    return 0


def write_credits(credits: dict) -> None:
    (IMAGES / "credits.json").write_text(
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


def fetch(manifest: list[dict], force: bool) -> int:
    credits_path = IMAGES / "credits.json"
    credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else {}
    files = {image["file"] for product in manifest for image in product["images"]}
    credits = {name: c for name, c in credits.items() if name in files and "license" in c}
    used = {c["id"] for c in credits.values()}
    failed = []

    for product in manifest:
        for image in product["images"]:
            target = IMAGES / image["file"]
            pick = image.get("pick")
            current = credits.get(image["file"], {}).get("id")
            if target.exists() and current and not force and (not pick or pick == current):
                continue
            try:
                if pick:
                    photo = resolve(pick)
                    data = square_jpeg(get(photo["url"], "image/*"))
                else:
                    photo, data = fetch_first(queries_of(image), used)
                target.write_bytes(data)
                used.add(photo["id"])
                photo = {k: v for k, v in photo.items() if k != "thumb"}
                credits[image["file"]] = {**photo, "query": image["query"]}
                print(f"ok   {image['file']} ← {photo['source']}")
            except Exception as exc:  # отчёт по всем файлам, а не падение на первом
                failed.append(image["file"])
                print(f"FAIL {image['file']}: {exc}", file=sys.stderr)
            time.sleep(1)  # вежливо к источникам

    write_credits(credits)
    print(f"готово, ошибок: {len(failed)}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--force", action="store_true", help="Скачать заново все фото")
    parser.add_argument("--candidates", type=Path, help="Папка для контактных листов кандидатов")
    parser.add_argument("--only", default="", help="Файлы через запятую (для --candidates)")
    args = parser.parse_args()
    manifest = json.loads((IMAGES / "manifest.json").read_text(encoding="utf-8"))
    if args.candidates:
        return candidates(manifest, set(filter(None, args.only.split(","))), args.candidates)
    return fetch(manifest, args.force)


if __name__ == "__main__":
    sys.exit(main())
