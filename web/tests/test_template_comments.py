"""Комментарий `{# … #}` в Django однострочный: перенос строки выводит его в HTML как текст."""

from pathlib import Path

from django.conf import settings


def test_no_multiline_hash_comments():
    roots = list(Path(settings.BASE_DIR).glob("*/templates"))
    broken = [
        f"{path.relative_to(settings.BASE_DIR)}:{number}"
        for root in roots
        if root.is_dir()
        for path in root.rglob("*.html")
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if line.count("{#") > line.count("#}")
    ]
    assert not broken, "многострочный {# #} — используйте {% comment %}: " + ", ".join(broken)
