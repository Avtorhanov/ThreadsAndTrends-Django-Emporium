"""Тексты и блоки витрины, которые администратор правит прямо на сайте.

Тексты: `{% sitetext "ключ" %}текст по умолчанию{% endsitetext %}` в шаблоне; изменённые
хранятся в SiteText (пусто — скрыт, удаление записи — вернуть исходный).

Блоки — списки разделов: «Контакты» (каналы связи), «Помощь» и ссылки подвала. Пока раздел не
меняли, блоки берутся из значений по умолчанию (контакты — из .env, как раньше). При первом
изменении раздел переносится в БД целиком (CustomizedArea) — дальше им управляет администратор.

Не зависит от DRF: ошибки — django ValidationError.
"""

import re
from dataclasses import dataclass

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.urls import reverse

from content.models import Block, BlockArea, BlockKind, CustomizedArea, SiteText

TEXTS_CACHE_KEY = "content:site-texts"
TEXT_KEY = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}$")
MAX_TEXT = 2000
MAX_BLOCKS_PER_AREA = 20
ICONS = {"box", "chat", "help", "send", "people", "phone", "mail", "grid", "bag", "user"}
# Ссылка блока: страница сайта, https, телефон или почта — без javascript: и data:.
SAFE_LINK = re.compile(r"^(/(?!/)\S*|https://\S+|tel:\+?[\d\- ()]{5,20}|mailto:[^@\s]+@[^@\s]+)$")


# --- Тексты ---


def texts() -> dict[str, str]:
    """Все изменённые тексты одним запросом, в общем кэше до следующего изменения."""
    values = cache.get(TEXTS_CACHE_KEY)
    if values is None:
        values = dict(SiteText.objects.values_list("key", "value"))
        cache.set(TEXTS_CACHE_KEY, values, 60 * 60)
    return values


def _invalidate_texts() -> None:
    cache.delete(TEXTS_CACHE_KEY)
    transaction.on_commit(lambda: cache.delete(TEXTS_CACHE_KEY))


def _check_key(key: str) -> None:
    if not TEXT_KEY.match(key):
        raise ValidationError({"key": "Ключ: латиница, цифры, точка, дефис, до 80 символов."})


def set_text(key: str, value: str) -> SiteText:
    """Сохранить текст. Пустая строка — текст скрыт на сайте."""
    _check_key(key)
    value = value.strip()
    if len(value) > MAX_TEXT:
        raise ValidationError({"value": f"Не длиннее {MAX_TEXT} символов."})
    text, _ = SiteText.objects.update_or_create(key=key, defaults={"value": value})
    _invalidate_texts()
    return text


def reset_text(key: str) -> None:
    """Вернуть текст из шаблона."""
    _check_key(key)
    SiteText.objects.filter(key=key).delete()
    _invalidate_texts()


# --- Блоки ---


@dataclass(frozen=True)
class BlockDefault:
    kind: str
    title: str
    value: str
    note: str = ""
    icon: str = ""


def _defaults(area: str) -> list[BlockDefault]:
    if area == BlockArea.CONTACTS:
        # Каналы из настроек (.env): так было до управления блоками с сайта.
        from content.contacts import default_values

        return [BlockDefault(kind, "", value, note) for kind, value, note in default_values()]
    if area == BlockArea.HELP:
        return [
            BlockDefault(
                BlockKind.LINK, "Доставка, оплата и возврат", reverse("web:delivery"), icon="box"
            ),
            BlockDefault(BlockKind.LINK, "Контакты и статьи", reverse("web:contacts"), icon="chat"),
            BlockDefault(BlockKind.LINK, "Публичная оферта", reverse("web:offer"), icon="help"),
            BlockDefault(
                BlockKind.LINK, "Политика обработки данных", reverse("web:privacy"), icon="help"
            ),
        ]
    if area == BlockArea.FOOTER:
        return [
            BlockDefault(BlockKind.LINK, "Доставка, оплата и возврат", reverse("web:delivery")),
            BlockDefault(BlockKind.LINK, "Публичная оферта", reverse("web:offer")),
            BlockDefault(
                BlockKind.LINK, "Политика обработки персональных данных", reverse("web:privacy")
            ),
        ]
    raise ValueError(area)


def is_customized(area: str) -> bool:
    return CustomizedArea.objects.filter(area=area).exists()


def blocks(area: str) -> list[Block]:
    """Блоки раздела в порядке показа. Значения по умолчанию — несохранённые Block (без id)."""
    if is_customized(area):
        return list(Block.objects.filter(area=area).order_by("position", "id"))
    return blocks_from_defaults(area)


@transaction.atomic
def customize(area: str) -> list[Block]:
    """Перенести раздел в БД (один раз): дальше блоки меняет администратор."""
    if area not in BlockArea.values:
        raise ValidationError({"area": "Неизвестный раздел."})
    _, created = CustomizedArea.objects.get_or_create(area=area)
    if created:
        for block in blocks_from_defaults(area):
            block.save()
    return list(Block.objects.filter(area=area).order_by("position", "id"))


def blocks_from_defaults(area: str) -> list[Block]:
    return [
        Block(
            area=area,
            kind=d.kind,
            title=d.title,
            value=d.value,
            note=d.note,
            icon=d.icon,
            position=n,
        )
        for n, d in enumerate(_defaults(area))
    ]


def _validate(area: str, kind: str, title: str, value: str, icon: str) -> None:
    from content.contacts import PARSERS

    errors = {}
    if area == BlockArea.CONTACTS:
        if kind not in PARSERS:
            errors["kind"] = "Выберите канал: WhatsApp, Telegram, ВКонтакте, телефон или почта."
        elif PARSERS[kind](value) is None:
            errors["value"] = "Не похоже на номер, имя или адрес для этого канала."
    else:
        if kind != BlockKind.LINK:
            errors["kind"] = "В этом разделе — только ссылки."
        if not title.strip():
            errors["title"] = "Введите название."
        if not SAFE_LINK.match(value.strip()):
            errors["value"] = "Ссылка: страница сайта (/…), https://…, tel: или mailto:."
    if icon and icon not in ICONS:
        errors["icon"] = "Неизвестный значок."
    if errors:
        raise ValidationError(errors)


@transaction.atomic
def add_block(
    *,
    area: str,
    kind: str = BlockKind.LINK,
    title: str = "",
    value: str,
    note: str = "",
    icon: str = "",
) -> Block:
    customize(area)
    _validate(area, kind, title, value, icon)
    if Block.objects.filter(area=area).count() >= MAX_BLOCKS_PER_AREA:
        raise ValidationError(f"В разделе может быть не больше {MAX_BLOCKS_PER_AREA} блоков.")
    last = Block.objects.filter(area=area).aggregate(Max("position"))["position__max"]
    return Block.objects.create(
        area=area,
        kind=kind,
        title=title.strip(),
        value=value.strip(),
        note=note.strip(),
        icon=icon,
        position=0 if last is None else last + 1,
    )


@transaction.atomic
def update_block(block: Block, **changes) -> Block:
    allowed = {"kind", "title", "value", "note", "icon"}
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"Неизвестные поля блока: {sorted(unknown)}")
    for field, value in changes.items():
        setattr(block, field, value.strip() if isinstance(value, str) else value)
    _validate(block.area, block.kind, block.title, block.value, block.icon)
    block.save()
    return block


def delete_block(block: Block) -> None:
    block.delete()


@transaction.atomic
def reorder_blocks(area: str, ids: list[int]) -> list[Block]:
    current = list(Block.objects.select_for_update().filter(area=area))
    if sorted(ids) != sorted(b.pk for b in current):
        raise ValidationError({"ids": "Передайте все блоки раздела ровно по одному разу."})
    by_id = {b.pk: b for b in current}
    for position, pk in enumerate(ids):
        by_id[pk].position = position
    Block.objects.bulk_update(current, ["position"])
    return sorted(current, key=lambda b: b.position)
