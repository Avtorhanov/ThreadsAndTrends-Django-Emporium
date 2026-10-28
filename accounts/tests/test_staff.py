"""Сотрудники панели: приглашение, права по разделам на каждом эндпоинте, отключение."""

import re

import pytest
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.test import APIClient

from accounts import staff
from accounts.api import admin_views
from accounts.models import StaffAccess, User

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

STAFF = "/api/v1/admin/staff/"
# Эндпоинты входа доступны любому сотруднику — раздела у них нет.
AUTH_VIEWS = {
    admin_views.AdminCsrfView,
    admin_views.AdminLoginView,
    admin_views.AdminLogoutView,
    admin_views.AdminMeView,
}


def admin_views_from_urls():
    """Классы всех view под /api/v1/admin/ (по таблице URL, а не по списку в тесте)."""
    found = {}

    def walk(patterns, prefix):
        for entry in patterns:
            route = prefix + str(entry.pattern)
            if isinstance(entry, URLResolver):
                walk(entry.url_patterns, route)
            elif isinstance(entry, URLPattern) and route.startswith("api/v1/admin/"):
                view = getattr(entry.callback, "cls", None)
                if view is not None:
                    found.setdefault(view, route)

    walk(get_resolver().url_patterns, "")
    return found


def client_for(user):
    client = APIClient()
    client.force_login(user)
    return client


def make_staff(email="worker@example.com", **levels):
    user = User.objects.create_user(email=email, password=PASSWORD, is_staff=True)
    StaffAccess.objects.create(user=user, permissions=staff.clean_permissions(levels))
    return user


def test_every_admin_endpoint_declares_section():
    views = admin_views_from_urls()
    assert len(views) > 15
    missing = [
        f"{view.__name__} ({route})"
        for view, route in views.items()
        if view not in AUTH_VIEWS and getattr(view, "section", None) not in staff.ALL_SECTIONS
    ]
    assert missing == [], "у эндпоинтов панели нет раздела прав: " + ", ".join(missing)


# Матрица: (метод, адрес, раздел). Ответ для разрешённого уровня не важен (404/400 тоже
# значит «права пропустили»), важно — 403 при недостаточном.
MATRIX = [
    ("get", "/api/v1/admin/summary/", "summary"),
    ("get", "/api/v1/admin/orders/", "orders"),
    ("post", "/api/v1/admin/orders/999/transition/", "orders"),
    ("get", "/api/v1/admin/catalog/products/", "products"),
    ("post", "/api/v1/admin/catalog/products/bulk/", "products"),
    ("get", "/api/v1/admin/catalog/statuses/", "products"),
    ("post", "/api/v1/admin/catalog/categories/", "categories"),
    ("get", "/api/v1/admin/content/articles/", "articles"),
    ("post", "/api/v1/admin/content/articles/", "articles"),
    ("get", "/api/v1/admin/content/home/", "storefront"),
    ("post", "/api/v1/admin/content/home/publish/", "storefront"),
    ("put", "/api/v1/admin/content/theme/", "storefront"),
    ("put", "/api/v1/admin/content/texts/footer.copy/", "storefront"),
    ("get", "/api/v1/admin/customers/", "customers"),
    ("post", "/api/v1/admin/customers/999/block/", "customers"),
]


@pytest.mark.parametrize(("method", "url", "section"), MATRIX)
@pytest.mark.parametrize("level", [staff.NONE, staff.VIEW, staff.EDIT])
def test_section_matrix(method, url, section, level):
    user = make_staff(**{section: level})
    response = getattr(client_for(user), method)(url, {}, format="json")
    need = staff.VIEW if method == "get" else staff.EDIT
    allowed = staff._RANK[level] >= staff._RANK[need]
    assert (response.status_code != 403) is allowed, (url, level, response.status_code)


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/v1/admin/content/settings/"),
        ("put", "/api/v1/admin/content/settings/"),
        ("get", STAFF),
        ("post", STAFF),
    ],
)
def test_owner_sections_closed_to_any_staff(method, url):
    user = make_staff(**dict.fromkeys(staff.SECTIONS, staff.EDIT))
    assert getattr(client_for(user), method)(url, {}, format="json").status_code == 403


def test_categories_readable_from_products_section():
    user = make_staff(products=staff.VIEW)
    client = client_for(user)
    assert client.get("/api/v1/admin/catalog/categories/").status_code == 200
    assert client.post("/api/v1/admin/catalog/categories/", {}, format="json").status_code == 403


def test_owner_and_legacy_admin_have_full_access(superuser, staff):  # noqa: F811
    for user in (superuser, staff):
        me = client_for(user).get("/api/v1/admin/auth/me/").json()
        assert me["is_owner"] is True
        assert set(me["permissions"].values()) == {"edit"}


def test_me_returns_permissions_for_staff():
    user = make_staff(orders=staff.EDIT, customers=staff.VIEW)
    me = client_for(user).get("/api/v1/admin/auth/me/").json()
    assert me["is_owner"] is False
    assert me["permissions"]["orders"] == "edit" and me["permissions"]["customers"] == "view"
    assert me["permissions"]["settings"] == "none" and me["permissions"]["staff"] == "none"


def test_invite_sets_password_and_logs_into_panel(
    superuser, client, django_capture_on_commit_callbacks
):
    owner = client_for(superuser)
    body = {
        "email": "Manager@Example.com",
        "first_name": "Ольга",
        "permissions": {"orders": "edit"},
    }
    with django_capture_on_commit_callbacks(execute=True):
        response = owner.post(STAFF, body, format="json")
    assert response.status_code == 201, response.content
    member = response.json()
    assert member["email"] == "manager@example.com" and member["invited"] is True
    assert member["permissions"]["orders"] == "edit" and member["permissions"]["articles"] == "none"

    letter = mail.outbox[-1]
    assert letter.to == ["manager@example.com"] and "приглашение" in letter.subject
    code = re.search(r"\b(\d{6})\b", letter.body).group(1)
    confirm = client.post(
        "/password-reset/confirm/",
        {
            "email": "manager@example.com",
            "code": code,
            "new_password": "Brand-New-Pass-42",
            "new_password_confirm": "Brand-New-Pass-42",
        },
    )
    assert confirm.status_code == 302 and confirm["Location"] == "/panel/"
    login = APIClient().post(
        "/api/v1/admin/auth/login/",
        {"email": "manager@example.com", "password": "Brand-New-Pass-42"},
        format="json",
    )
    assert login.status_code == 200 and login.json()["permissions"]["orders"] == "edit"


def test_invite_rejects_existing_email_and_owner_sections(superuser):
    with pytest.raises(ValidationError):
        staff.invite(superuser, email=superuser.email, permissions={})
    with pytest.raises(ValidationError):
        staff.invite(superuser, email="new@example.com", permissions={"settings": "edit"})


def test_only_owner_manages_staff(superuser):
    worker = make_staff(orders=staff.EDIT)
    other = make_staff("other@example.com")
    with pytest.raises(PermissionDenied):
        staff.update(worker, other, permissions={"orders": "edit"})
    with pytest.raises(ValidationError):
        staff.update(superuser, superuser, is_active=False)


def test_disable_ends_sessions(superuser):
    worker = make_staff(orders=staff.EDIT)
    session = client_for(worker)
    assert session.get("/api/v1/admin/orders/").status_code == 200
    response = client_for(superuser).patch(
        f"{STAFF}{worker.pk}/", {"is_active": False}, format="json"
    )
    assert response.status_code == 200 and response.json()["is_active"] is False
    # Старая сессия больше не пускает: неактивного пользователя Django не загружает.
    assert session.get("/api/v1/admin/orders/").status_code in (401, 403)


def test_owner_changes_permissions(superuser):
    worker = make_staff(orders=staff.VIEW)
    response = client_for(superuser).patch(
        f"{STAFF}{worker.pk}/",
        {"permissions": {"orders": "edit", "articles": "view"}},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["permissions"]["articles"] == "view"
    assert client_for(worker).post("/api/v1/admin/orders/1/transition/", {}).status_code != 403


def test_staff_list_for_owner(superuser):
    make_staff(orders=staff.EDIT)
    rows = client_for(superuser).get(STAFF).json()
    assert [row["email"] for row in rows] == [superuser.email, "worker@example.com"]
    assert rows[0]["is_owner"] is True and rows[1]["is_owner"] is False
