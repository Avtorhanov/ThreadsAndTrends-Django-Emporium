"""SEO витрины: адреса для canonical/Open Graph, schema.org, sitemap."""

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from content.models import Article
from store.models import Product
from store.services.storefront import active_categories

SITE_NAME = "DiDi-shop"


def absolute_url(request, path: str) -> str:
    """Полный адрес на основном домене (SITE_URL); без него — адрес из запроса."""
    if path.startswith(("http://", "https://")):
        return path
    if settings.SITE_URL:
        return settings.SITE_URL + path
    return request.build_absolute_uri(path)


def _price(kopecks: int) -> str:
    # schema.org ждёт число с точкой: 1990.00 (из копеек, без float).
    rubles, rest = divmod(int(kopecks), 100)
    return f"{rubles}.{rest:02d}"


def product_json_ld(request, product: Product, images, in_stock: bool) -> dict:
    url = absolute_url(request, reverse("web:product", args=[product.slug]))
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "url": url,
        "sku": str(product.pk),
        "brand": {"@type": "Brand", "name": SITE_NAME},
        "category": product.category.name,
    }
    # Цена по запросу — без Offer: предложение без цены schema.org считает ошибкой.
    if product.price_kopecks is not None:
        data["offers"] = {
            "@type": "Offer",
            "url": url,
            "priceCurrency": "RUB",
            "price": _price(product.price_kopecks),
            "availability": "https://schema.org/InStock"
            if in_stock
            else "https://schema.org/OutOfStock",
            "itemCondition": "https://schema.org/NewCondition",
        }
    if product.description:
        data["description"] = product.description[:5000]
    if images:
        data["image"] = [absolute_url(request, image.image.url) for image in images]
    return data


def article_json_ld(request, article: Article, images) -> dict:
    url = absolute_url(request, reverse("web:article", args=[article.slug]))
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article.title[:110],
        "url": url,
        "mainEntityOfPage": url,
        "datePublished": article.published_at.isoformat() if article.published_at else None,
        "dateModified": article.updated_at.isoformat(),
        "publisher": {"@type": "Organization", "name": SITE_NAME},
    }
    if article.excerpt:
        data["description"] = article.excerpt
    if images:
        data["image"] = [absolute_url(request, image.image.url) for image in images]
    return data


class _SiteSitemap(Sitemap):
    """Адреса — на основном домене (SITE_URL), если он задан."""

    def get_domain(self, site=None):
        if settings.SITE_URL:
            return settings.SITE_URL.split("://", 1)[1]
        return super().get_domain(site)

    def get_protocol(self, protocol=None):
        if settings.SITE_URL:
            return settings.SITE_URL.split("://", 1)[0]
        return super().get_protocol(protocol)


class StaticSitemap(_SiteSitemap):
    changefreq = "daily"

    def items(self):
        return ["web:home", "web:products", "web:contacts"]

    def location(self, item):
        return reverse(item)


class CategorySitemap(_SiteSitemap):
    changefreq = "daily"

    def items(self):
        return active_categories().order_by("pk")

    def location(self, item):
        return reverse("web:category", args=[item.slug])

    def lastmod(self, item):
        return item.updated_at


class ProductSitemap(_SiteSitemap):
    changefreq = "weekly"
    limit = 5000

    def items(self):
        # Только товары, видимые на витрине: скрытые и удалённые в sitemap не попадают.
        return Product.objects.live().only("slug", "updated_at").order_by("pk")

    def location(self, item):
        return reverse("web:product", args=[item.slug])

    def lastmod(self, item):
        return item.updated_at


class ArticleSitemap(_SiteSitemap):
    changefreq = "monthly"

    def items(self):
        # Только опубликованные: черновики и удалённые статьи в sitemap не попадают.
        return Article.objects.published().only("slug", "updated_at").order_by("pk")

    def location(self, item):
        return reverse("web:article", args=[item.slug])

    def lastmod(self, item):
        return item.updated_at


SITEMAPS = {
    "static": StaticSitemap,
    "categories": CategorySitemap,
    "products": ProductSitemap,
    "articles": ArticleSitemap,
}
