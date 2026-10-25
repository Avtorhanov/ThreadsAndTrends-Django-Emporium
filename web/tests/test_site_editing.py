"""Витрина: тексты и блоки из content.site, редактор — только администратору."""

import pytest
from django.urls import reverse

from content import site

pytestmark = pytest.mark.django_db


def test_footer_and_help_use_blocks_and_texts(client, settings):
    site.add_block(area="footer", title="Таблица размеров", value="/articles/razmery/")
    site.set_text("footer.copy", "DiDi — одежда и не только")
    site.set_text("help.title", "Покупателям")
    html = client.get(reverse("web:contacts")).content.decode()
    assert 'href="/articles/razmery/"' in html and "Таблица размеров" in html
    assert "DiDi — одежда и не только" in html
    assert "Покупателям" in html
    # Ссылка «Контакты и статьи» в «Помощи» на самой странице контактов не дублируется.
    assert html.count(f'class="menu__item" href="{reverse("web:contacts")}"') == 0


def test_deleted_help_block_disappears(client):
    blocks = site.customize("help")
    site.delete_block(blocks[2])  # «Публичная оферта»
    html = client.get(reverse("web:contacts")).content.decode()
    assert f'class="menu__item" href="{reverse("web:offer")}"' not in html


def test_editor_only_for_staff(client, customer, staff):
    assert "edit.js" not in client.get(reverse("web:contacts")).content.decode()
    client.force_login(customer)
    assert "edit.js" not in client.get(reverse("web:contacts")).content.decode()
    client.force_login(staff)
    html = client.get(reverse("web:contacts")).content.decode()
    assert "edit.js" in html and 'name="csrf-token"' in html
    assert 'data-text="contacts.title"' in html
    assert 'data-blocks="help"' in html and 'data-blocks="footer"' in html


def test_contacts_page_marks_blocks_for_editor(client, staff, settings):
    settings.CONTACT_TELEGRAM = "@didishop"
    client.force_login(staff)
    html = client.get(reverse("web:contacts")).content.decode()
    assert 'data-blocks="contacts" data-customized=""' in html
    assert 'data-kind="telegram" data-value="@didishop"' in html
