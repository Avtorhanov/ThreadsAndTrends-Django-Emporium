"""Вкладка «Контакты»: каналы связи и статьи магазина; страница статьи."""

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render

from content import site
from content.contacts import ContactKind, get_contacts
from content.models import Article, ArticleImage

from ..seo import article_json_ld

# Простые значки в стиле «Лайм-тек» (не фирменные логотипы сервисов).
CONTACT_ICONS = {
    ContactKind.WHATSAPP: "chat",
    ContactKind.TELEGRAM: "send",
    ContactKind.VK: "people",
    ContactKind.PHONE: "phone",
    ContactKind.EMAIL: "mail",
}
ARTICLES_ON_CONTACTS = 24


def _articles():
    return Article.objects.published().prefetch_related(
        Prefetch("images", queryset=ArticleImage.objects.order_by("position", "id"))
    )


def contacts(request):
    # Сырые значения блоков (номер, @имя, своя подпись) — для правки администратором на сайте.
    raw = site.blocks("contacts")
    channels = [
        {
            "contact": contact,
            "icon": CONTACT_ICONS[contact.kind],
            "value": raw[contact.index].value,
            "note": raw[contact.index].note,
        }
        for contact in get_contacts()
    ]
    return render(
        request,
        "web/content/contacts.html",
        {
            "channels": channels,
            "articles": _articles().order_by("-published_at", "-id")[:ARTICLES_ON_CONTACTS],
            "tab": "contacts",
        },
    )


def article(request, slug: str):
    found = get_object_or_404(_articles(), slug=slug)
    images = list(found.images.all())
    return render(
        request,
        "web/content/article.html",
        {
            "article": found,
            "images": images,
            "json_ld": article_json_ld(request, found, images),
            "tab": "contacts",
        },
    )
