import json

from django import template
from django.templatetags.static import static
from django.utils.html import format_html, format_html_join, linebreaks
from django.utils.safestring import mark_safe

from content import site
from orders.models import OrderStatus
from store.services.storefront import category_tree

from ..seo import absolute_url

register = template.Library()

# Порядок — как в tokens.json (productTones): тот же тон, что у товара в приложении.
TONES = ("lime", "sun", "mint", "apricot", "sage", "aqua")

STATUS_TONES = {
    OrderStatus.AWAITING_PAYMENT: "warning",
    OrderStatus.CONFIRMED: "tag",
    OrderStatus.PAID: "tag",
    OrderStatus.ASSEMBLED: "tag",
    OrderStatus.SHIPPED: "info",
    OrderStatus.READY_FOR_PICKUP: "info",
    OrderStatus.DELIVERED: "success",
    OrderStatus.CANCELLED: "neutral",
}


@register.filter
def tone(slug: str) -> str:
    """Тон плашки фото по slug: FNV-1a, как toneFor() в mobile/src/theme/tone.ts."""
    value = 0x811C9DC5
    for char in str(slug):  # slug — латиница: ord() совпадает с charCodeAt() в JS
        value ^= ord(char)
        value = (value * 0x01000193) & 0xFFFFFFFF
    return TONES[value % len(TONES)]


@register.filter
def discount(product) -> int:
    """Скидка в процентах от старой цены, целым числом без float."""
    old, price = product.compare_at_kopecks, product.price_kopecks
    if not old or old <= price:
        return 0
    return ((old - price) * 100 + old // 2) // old


@register.filter
def schema_price(kopecks) -> str:
    """Цена для schema.org: 1990.00."""
    rubles, rest = divmod(int(kopecks), 100)
    return f"{rubles}.{rest:02d}"


@register.filter
def status_tone(status: str) -> str:
    return STATUS_TONES.get(status, "neutral")


@register.simple_tag(takes_context=True)
def absolute(context, path: str) -> str:
    """Полный адрес для canonical и Open Graph: основной домен из SITE_URL."""
    return absolute_url(context["request"], path)


@register.simple_tag(takes_context=True)
def absolute_static(context, path: str) -> str:
    return absolute_url(context["request"], static(path))


@register.filter
def ld_json(data) -> str:
    """schema.org JSON-LD. Символы <, >, & экранируются: строка из данных товара не закроет
    <script>. Блок данных (не исполняемый скрипт) — CSP его не блокирует."""
    raw = json.dumps(data, ensure_ascii=False)
    raw = raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return mark_safe(f'<script type="application/ld+json">{raw}</script>')


@register.filter
def subcategories(root) -> list[dict]:
    """Активные подкатегории корня из кэшированного дерева (без запроса к БД)."""
    for node in category_tree():
        if node["slug"] == root.slug:
            return node["children"]
    return []


@register.filter
def delivery_cost(method: str, options) -> int:
    """Стоимость выбранного способа доставки из вариантов экрана оформления."""
    for option in options:
        if option.method == method:
            return option.cost_kopecks
    return options[0].cost_kopecks if options else 0


@register.filter
def ru_plural(number, forms: str) -> str:
    """{{ n|ru_plural:"товар,товара,товаров" }} → «5 товаров»."""
    one, few, many = forms.split(",")
    n = abs(int(number))
    if n % 10 == 1 and n % 100 != 11:
        word = one
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        word = few
    else:
        word = many
    return f"{number} {word}"


@register.simple_tag
def field_input(bound_field, placeholder: str = ""):
    """Виджет поля с классом input, placeholder и связью с текстом ошибки для экранных дикторов."""
    attrs = {"class": "input"}
    if placeholder:
        attrs["placeholder"] = placeholder
    if bound_field.errors:
        attrs["aria-invalid"] = "true"
        attrs["aria-describedby"] = f"{bound_field.id_for_label}-error"
    return bound_field.as_widget(attrs=attrs)


@register.simple_tag
def product_img(image, sizes: str, css: str = "", eager: bool = False, alt: str = ""):
    """<img> фото товара: srcset из уменьшенных копий WebP, размеры против сдвига вёрстки,
    ленивая загрузка (кроме первого экрана: eager=True)."""
    sources = image.sources
    attrs = {"src": sources[0][0]}
    if all(width for _, width in sources) and len(sources) > 1:
        attrs["srcset"] = ", ".join(f"{url} {width}w" for url, width in sources)
        attrs["sizes"] = sizes
    if image.width and image.height:
        attrs["width"], attrs["height"] = image.width, image.height
    attrs.update(
        alt=alt,
        loading="eager" if eager else "lazy",
        fetchpriority="high" if eager else "auto",
        decoding="async",
    )
    if css:
        attrs["class"] = css
    return format_html("<img {}>", format_html_join(" ", '{}="{}"', attrs.items()))


# --- Тексты, которые администратор правит на сайте двойным нажатием ---


def is_editor(context) -> bool:
    request = context.get("request")
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.is_staff)


class SiteTextNode(template.Node):
    def __init__(self, key: str, nodelist, multiline: bool):
        self.key, self.nodelist, self.multiline = key, nodelist, multiline

    def render(self, context):
        values = site.texts()
        if self.key in values:
            # Изменённый текст — обычный текст: экранируется, абзацы — через пустую строку.
            value = values[self.key]
            if self.multiline:
                html = linebreaks(value, autoescape=True)
            else:
                html = format_html("{}", value)
        else:
            html = self.nodelist.render(context).strip()
        if not is_editor(context):
            return html
        tag = "div" if self.multiline else "span"
        if not html:
            return format_html(
                '<{} class="sx sx--hidden" data-text="{}" title="Скрыт — двойное нажатие, чтобы '
                'вернуть">скрыто</{}>',
                tag,
                self.key,
                tag,
            )
        return format_html(
            '<{} class="sx" data-text="{}"{}>{}</{}>',
            tag,
            self.key,
            mark_safe(' data-multiline="1"') if self.multiline else "",
            mark_safe(html),
            tag,
        )


@register.tag
def sitetext(parser, token):
    """{% sitetext "footer.copy" %}текст по умолчанию{% endsitetext %} — администратор меняет
    или скрывает текст двойным нажатием на сайте. {% sitetext "key" multiline %} — абзацы."""
    bits = token.split_contents()
    quoted = len(bits) > 1 and bits[1][0] in "\"'" and bits[1][-1] == bits[1][0]
    if len(bits) not in (2, 3) or not quoted or (len(bits) == 3 and bits[2] != "multiline"):
        raise template.TemplateSyntaxError('{% sitetext "ключ" [multiline] %}…{% endsitetext %}')
    key = bits[1][1:-1]
    if not site.TEXT_KEY.match(key):
        raise template.TemplateSyntaxError(f"Неверный ключ текста: {key}")
    nodelist = parser.parse(("endsitetext",))
    parser.delete_first_token()
    return SiteTextNode(key, nodelist, multiline=len(bits) == 3)


@register.simple_tag(takes_context=True)
def site_blocks(context, area: str):
    """Блоки раздела (Помощь, подвал) — один раз на страницу."""
    cache = context.render_context.setdefault("site_blocks", {})
    if area not in cache:
        cache[area] = site.blocks(area)
    return cache[area]


@register.simple_tag(takes_context=True)
def blocks_attrs(context, area: str):
    """Атрибуты контейнера блоков для редактора на сайте (только администратору)."""
    if not is_editor(context):
        return ""
    return format_html(
        ' data-blocks="{}" data-customized="{}"', area, "1" if site.is_customized(area) else ""
    )
