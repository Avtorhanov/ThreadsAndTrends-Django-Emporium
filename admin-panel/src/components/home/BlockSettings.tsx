import { type ChangeEvent, useEffect, useState } from "react";

import { type Category, type ProductRow, productsService } from "../../api/catalog";
import { type ArticleRow, articlesService } from "../../api/content";
import {
  BANNER_TONES,
  type CollectionSource,
  HOME_LIMITS,
  type HomeBlock,
  type HomeBlockChanges,
  type HomeLinkInput,
  LINK_KIND_LABELS,
  LINK_PAGES,
  SOURCE_LABELS,
  blockLinks,
  type HomeLinkKind,
  type HomeLinkPage,
} from "../../api/home";
import { sortCategoryTree } from "../../hooks/useCatalog";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { formatKopecks } from "../../lib/money";

const HEADINGS: Record<HomeBlock["kind"], string> = {
  banner: "Баннер",
  collection: "Подборка товаров",
  categories: "Лента категорий",
  text: "Текстовый блок",
};

type Props = {
  block: HomeBlock;
  categories: Category[];
  error: string | null;
  busy: boolean;
  /** delay — пауза перед сохранением: текст копится, выбор из списка сохраняется сразу. */
  onChange: (changes: HomeBlockChanges, delay?: number) => void;
  onUpload: (file: File) => void;
  onDelete: () => void;
  onBack: () => void;
};

function Counter({ value, max }: { value: string; max: number }) {
  return (
    <span className={value.length > max ? "field-error small" : "muted small"}>
      {value.length} / {max}
    </span>
  );
}

/** Настройки выбранного блока. Правки сохраняются в черновик сами — покупатель их не видит. */
export function BlockSettings(props: Props) {
  const { block, categories, error, busy, onChange, onDelete, onBack } = props;
  const [confirming, setConfirming] = useState(false);
  const tree = sortCategoryTree(categories);
  useEffect(() => setConfirming(false), [block.id]);

  return (
    <div className="card he-settings-card">
      <div className="he-settings-head">
        <button type="button" className="button button-ghost he-phone-only" onClick={onBack}>
          ← Все блоки
        </button>
        <h2>{HEADINGS[block.kind]}</h2>
        <label className="check he-visible">
          <input
            type="checkbox"
            checked={block.is_visible}
            onChange={(event) => onChange({ is_visible: event.target.checked }, 0)}
          />
          Показывать
        </label>
      </div>
      {error ? <p className="alert">Не сохранено: {error}</p> : null}


      <label className="field">
        <span className="field-head">
          Заголовок <Counter value={block.title} max={HOME_LIMITS.title} />
        </span>
        <input
          value={block.title}
          maxLength={HOME_LIMITS.title}
          placeholder={block.kind === "collection" ? "Например: Новинки" : ""}
          onChange={(event) => onChange({ title: event.target.value })}
        />
      </label>

      {block.kind === "banner" ? <BannerFields {...props} tree={tree} /> : null}
      {block.kind === "collection" ? <CollectionFields {...props} tree={tree} /> : null}
      {block.kind === "categories" ? <LinksFields {...props} tree={tree} /> : null}
      {block.kind === "text" ? (
        <label className="field">
          <span className="field-head">
            Текст <Counter value={block.text} max={HOME_LIMITS.text} />
          </span>
          <textarea
            rows={7}
            value={block.text}
            maxLength={HOME_LIMITS.text}
            placeholder="Пустая строка — новый абзац"
            onChange={(event) => onChange({ text: event.target.value })}
          />
        </label>
      ) : null}

      <div className="he-delete">
        {confirming ? (
          <div className="he-confirm" role="alertdialog" aria-label="Удаление блока">
            <span>
              Удалить блок «{block.title || HEADINGS[block.kind]}»? Его можно будет добавить заново.
            </span>
            <div className="status-actions">
              <button type="button" className="button button-ghost" onClick={() => setConfirming(false)}>
                Отмена
              </button>
              <button type="button" className="button button-danger" disabled={busy} onClick={onDelete}>
                Удалить
              </button>
            </div>
          </div>
        ) : (
          <button type="button" className="button button-ghost he-delete-btn" onClick={() => setConfirming(true)}>
            Удалить блок
          </button>
        )}
      </div>
    </div>
  );
}

type TreeProps = Props & { tree: Array<Category & { depth: number }> };

function CategorySelect({
  value,
  tree,
  empty,
  onSelect,
}: {
  value: number | null;
  tree: TreeProps["tree"];
  empty?: string;
  onSelect: (id: number | null) => void;
}) {
  return (
    <select value={value ?? ""} onChange={(event) => onSelect(event.target.value ? Number(event.target.value) : null)}>
      {empty ? <option value="">{empty}</option> : null}
      {tree.map((item) => (
        <option key={item.id} value={item.id}>
          {item.depth ? `— ${item.name}` : item.name}
          {item.is_active ? "" : " (скрыта)"}
        </option>
      ))}
    </select>
  );
}

const IMAGE_TYPES = "image/jpeg,image/png,image/webp,image/gif";

function BannerFields({ block, tree, busy, onChange, onUpload }: TreeProps) {
  const custom = !BANNER_TONES.some((tone) => tone.color === block.color.toUpperCase());
  const photo = block.preview_images.length > 0;
  const ids = block.image_ids;

  function pick(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []).slice(0, HOME_LIMITS.bannerImages - ids.length);
    event.target.value = "";
    files.forEach((file) => onUpload(file));
  }

  function move(index: number, delta: number) {
    const next = [...ids];
    const [id] = next.splice(index, 1);
    if (id === undefined) return;
    next.splice(index + delta, 0, id);
    onChange({ image_ids: next }, 0);
  }

  return (
    <>
      <label className="field">
        <span className="field-head">
          {photo ? "Текст на фото" : "Короткое описание"} <Counter value={block.text} max={HOME_LIMITS.bannerText} />
        </span>
        <textarea
          rows={2}
          value={block.text}
          maxLength={HOME_LIMITS.bannerText}
          placeholder={block.product ? "Пусто — цена товара" : ""}
          onChange={(event) => onChange({ text: event.target.value })}
        />
      </label>

      <ProductPicker block={block} onChange={onChange} />

      <div className="field">
        <span className="field-head">
          Картинки
          <span className="muted small">
            {ids.length} из {HOME_LIMITS.bannerImages}
          </span>
        </span>
        {block.images.length ? (
          <ol className="he-gallery">
            {block.images.map((image, index) => (
              <li key={image.id}>
                <img src={image.url} alt="" />
                <span className="he-gallery-actions">
                  <button type="button" aria-label="Левее" disabled={busy || index === 0} onClick={() => move(index, -1)}>
                    ←
                  </button>
                  <button
                    type="button"
                    aria-label="Правее"
                    disabled={busy || index === block.images.length - 1}
                    onClick={() => move(index, 1)}
                  >
                    →
                  </button>
                  <button
                    type="button"
                    aria-label="Убрать картинку"
                    disabled={busy}
                    onClick={() => onChange({ image_ids: ids.filter((item) => item !== image.id) }, 0)}
                  >
                    ×
                  </button>
                </span>
              </li>
            ))}
          </ol>
        ) : null}
        {ids.length < HOME_LIMITS.bannerImages ? (
          <label className="drop-zone">
            <strong>{ids.length ? "Добавить ещё" : "Выбрать картинки"}</strong>
            <span className="muted small">
              JPEG, PNG, WebP или GIF до 5 МБ · несколько картинок сменяют друг друга с плавным приближением
            </span>
            <input type="file" accept={IMAGE_TYPES} multiple hidden disabled={busy} onChange={pick} />
          </label>
        ) : null}
        {block.product && !ids.length ? (
          <span className="muted small">Без своих картинок на баннере — фото товара.</span>
        ) : null}
      </div>

      {photo ? (
        <p className="muted small">
          Фото в рамке карточки, заголовок и текст — поверх снизу. Баннеры подряд листаются каруселью.
        </p>
      ) : (
        <div className="field">
          <span>Цвет</span>
          <div className="he-tones" role="radiogroup" aria-label="Цвет баннера">
            {BANNER_TONES.map((tone) => (
              <button
                key={tone.color}
                type="button"
                role="radio"
                aria-checked={block.color.toUpperCase() === tone.color}
                className="he-tone"
                style={{ background: tone.color }}
                title={tone.label}
                onClick={() => onChange({ color: tone.color }, 0)}
              >
                <span className="sr-only">{tone.label}</span>
              </button>
            ))}
            <label className={custom ? "he-tone he-tone-custom is-on" : "he-tone he-tone-custom"} title="Свой цвет">
              <input
                type="color"
                value={/^#[0-9a-f]{6}$/i.test(block.color) ? block.color : "#FFE38F"}
                onChange={(event) => onChange({ color: event.target.value.toUpperCase() })}
              />
              Свой
            </label>
          </div>
          <span className="muted small">Баннер без картинок — цветная плашка; цвет текста подбирается сам.</span>
        </div>
      )}

      {block.product ? null : (
        <label className="field">
          <span>Переход по нажатию</span>
          <CategorySelect
            value={block.category}
            tree={tree}
            empty="Без перехода"
            onSelect={(category) => onChange({ category }, 0)}
          />
        </label>
      )}
    </>
  );
}

function useProductSearch(query: string) {
  const [results, setResults] = useState<ProductRow[]>([]);
  useEffect(() => {
    let cancelled = false;
    if (!query) {
      setResults([]);
      return;
    }
    productsService
      .list({ search: query, status: "active", label: "", category: null, stock: "", page: 1 })
      .then((page) => !cancelled && setResults(page.results.slice(0, 8)))
      .catch(() => !cancelled && setResults([]));
    return () => {
      cancelled = true;
    };
  }, [query]);
  return results;
}

function ProductPicker({ block, onChange }: Pick<Props, "block" | "onChange">) {
  const [search, setSearch] = useState("");
  const [picked, setPicked] = useState<ProductRow | null>(null);
  const results = useProductSearch(useDebouncedValue(search.trim()));
  const shown = block.preview_product;
  const name = shown?.name ?? (picked && picked.id === block.product ? picked.name : null);

  return (
    <div className="field">
      <span>Товар на баннере — необязательно</span>
      {block.product ? (
        <div className="he-picked-product">
          {shown?.cover_url ? <img className="thumb" src={shown.cover_url} alt="" /> : <span className="thumb thumb-empty" />}
          <span className={shown ? undefined : "muted"}>
            {name ?? `Товар #${block.product}`}
            {shown ? "" : " — скрыт, баннер покажет только свои картинки и текст"}
          </span>
          <button type="button" className="button button-ghost" onClick={() => onChange({ product: null }, 0)}>
            Убрать
          </button>
        </div>
      ) : (
        <>
          <input
            type="search"
            value={search}
            placeholder="Найти товар: фото товара на баннере и переход на него"
            onChange={(event) => setSearch(event.target.value)}
          />
          {results.length ? (
            <ul className="he-results">
              {results.map((product) => (
                <li key={product.id}>
                  {product.cover_url ? <img className="thumb" src={product.cover_url} alt="" /> : <span className="thumb thumb-empty" />}
                  <span>{product.name}</span>
                  <button
                    type="button"
                    className="button button-outline"
                    onClick={() => {
                      setPicked(product);
                      setSearch("");
                      onChange({ product: product.id }, 0);
                    }}
                  >
                    Выбрать
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </>
      )}
    </div>
  );
}

function CollectionFields({ block, tree, onChange }: TreeProps) {
  const sources = Object.entries(SOURCE_LABELS) as [CollectionSource, string][];

  function setSource(source: CollectionSource) {
    if (source === "category" && block.category === null) {
      const first = tree[0];
      if (!first) return;
      onChange({ source, category: first.id }, 0);
      return;
    }
    onChange({ source }, 0);
  }

  return (
    <>
      <div className="field">
        <span>Какие товары</span>
        <div className="seg-switch he-sources" role="radiogroup" aria-label="Какие товары">
          {sources.map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={block.source === value}
              className={block.source === value ? "is-on" : undefined}
              onClick={() => setSource(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {block.source === "category" ? (
        <label className="field">
          <span>Категория</span>
          <CategorySelect value={block.category} tree={tree} onSelect={(category) => onChange({ category }, 0)} />
        </label>
      ) : null}
      {block.source === "manual" ? <ManualProducts block={block} onChange={onChange} /> : null}
      <p className="muted small">
        {block.source === "manual"
          ? `До ${HOME_LIMITS.manualProducts} товаров в выбранном порядке.`
          : "До 8 товаров, сначала новые."}{" "}
        Скрытые и удалённые товары в подборку не попадают — она обновляется сама.
      </p>
    </>
  );
}

function ManualProducts({ block, onChange }: Pick<Props, "block" | "onChange">) {
  const [search, setSearch] = useState("");
  const results = useProductSearch(useDebouncedValue(search.trim()));
  const ids = block.product_ids;
  const shown = new Map(block.preview_products.map((product) => [product.id, product]));
  const [names, setNames] = useState<Map<number, string>>(new Map());

  function add(product: ProductRow) {
    if (ids.includes(product.id) || ids.length >= HOME_LIMITS.manualProducts) return;
    setNames((prev) => new Map(prev).set(product.id, product.name));
    onChange({ product_ids: [...ids, product.id] }, 0);
  }

  function move(index: number, delta: number) {
    const next = [...ids];
    const [id] = next.splice(index, 1);
    if (id === undefined) return;
    next.splice(index + delta, 0, id);
    onChange({ product_ids: next }, 0);
  }

  return (
    <div className="field">
      <span className="field-head">
        Товары подборки
        <span className="muted small">
          {ids.length} из {HOME_LIMITS.manualProducts}
        </span>
      </span>
      {ids.length ? (
        <ol className="he-picked">
          {ids.map((id, index) => {
            const product = shown.get(id);
            return (
              <li key={id}>
                <span className={product ? undefined : "muted"}>
                  {product?.name ?? names.get(id) ?? `Товар #${id}`}
                  {product ? "" : " — скрыт, покупатель не увидит"}
                </span>
                <button type="button" aria-label="Выше" disabled={index === 0} onClick={() => move(index, -1)}>
                  ↑
                </button>
                <button
                  type="button"
                  aria-label="Ниже"
                  disabled={index === ids.length - 1}
                  onClick={() => move(index, 1)}
                >
                  ↓
                </button>
                <button
                  type="button"
                  aria-label="Убрать из подборки"
                  onClick={() => onChange({ product_ids: ids.filter((item) => item !== id) }, 0)}
                >
                  ×
                </button>
              </li>
            );
          })}
        </ol>
      ) : null}
      <input
        type="search"
        value={search}
        placeholder="Найти товар по названию или артикулу"
        onChange={(event) => setSearch(event.target.value)}
      />
      {results.length ? (
        <ul className="he-results">
          {results.map((product) => (
            <li key={product.id}>
              {product.cover_url ? <img className="thumb" src={product.cover_url} alt="" /> : <span className="thumb thumb-empty" />}
              <span>
                {product.name}
                <span className="muted small">
                  {" "}
                  · {product.price_kopecks === null ? "по запросу" : formatKopecks(product.price_kopecks)}
                </span>
              </span>
              <button
                type="button"
                className="button button-outline"
                disabled={ids.includes(product.id) || ids.length >= HOME_LIMITS.manualProducts}
                onClick={() => add(product)}
              >
                {ids.includes(product.id) ? "Добавлен" : "Добавить"}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/** Лента категорий: пусто — основные категории (как в шапке); свои вкладки — категории,
 * статьи, страницы магазина и ссылки в нужном порядке. */
function LinksFields({ block, tree, busy, onChange }: TreeProps) {
  const links = blockLinks(block);
  const shown = block.preview_links;
  const [kind, setKind] = useState<HomeLinkKind>("category");
  const [ref, setRef] = useState("");
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [articles, setArticles] = useState<ArticleRow[]>([]);

  useEffect(() => {
    let cancelled = false;
    articlesService
      .list({ search: "", status: "published", page: 1 })
      .then((page) => !cancelled && setArticles(page.results))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  function save(next: HomeLinkInput[], delay = 0) {
    onChange({ links: next }, delay);
  }

  function add() {
    const item: HomeLinkInput = { kind, title: title.trim() };
    if (kind === "category" || kind === "article") item.id = Number(ref);
    else if (kind === "page") item.key = ref as HomeLinkPage;
    else item.url = url.trim();
    save([...links, item]);
    setRef("");
    setUrl("");
    setTitle("");
  }

  function move(index: number, delta: number) {
    const next = [...links];
    const [item] = next.splice(index, 1);
    if (!item) return;
    next.splice(index + delta, 0, item);
    save(next);
  }

  const ready = kind === "url" ? Boolean(url.trim() && title.trim()) : Boolean(ref);
  // Подпись по умолчанию — как увидит покупатель (снятая статья или скрытая категория пропадут).
  const label = (item: HomeLinkInput, index: number) =>
    shown.find((link, i) => i === index && link.kind === item.kind)?.title ?? item.title ?? "";

  return (
    <div className="field">
      <span className="field-head">
        Вкладки ленты
        <span className="muted small">
          {links.length} из {HOME_LIMITS.links}
        </span>
      </span>
      {links.length === 0 ? (
        <p className="muted small">
          Сейчас — все основные категории, как в шапке магазина. Добавьте свои вкладки: категории, статьи,
          страницы магазина или ссылки.
        </p>
      ) : (
        <ol className="he-picked he-links">
          {links.map((item, index) => (
            <li key={`${item.kind}-${item.id ?? item.key ?? item.url}-${index}`}>
              <span className="he-link-kind">{LINK_KIND_LABELS[item.kind]}</span>
              <input
                value={item.title ?? ""}
                maxLength={HOME_LIMITS.linkTitle}
                placeholder={label(item, index) || "Подпись"}
                aria-label="Подпись вкладки"
                onChange={(event) =>
                  save(
                    links.map((link, i) => (i === index ? { ...link, title: event.target.value } : link)),
                    600,
                  )
                }
              />
              <button type="button" aria-label="Выше" disabled={busy || index === 0} onClick={() => move(index, -1)}>
                ↑
              </button>
              <button
                type="button"
                aria-label="Ниже"
                disabled={busy || index === links.length - 1}
                onClick={() => move(index, 1)}
              >
                ↓
              </button>
              <button
                type="button"
                aria-label="Убрать вкладку"
                disabled={busy}
                onClick={() => save(links.filter((_, i) => i !== index))}
              >
                ×
              </button>
            </li>
          ))}
        </ol>
      )}

      {links.length < HOME_LIMITS.links ? (
        <div className="he-link-add">
          <select
            value={kind}
            aria-label="Вид вкладки"
            onChange={(event) => {
              setKind(event.target.value as HomeLinkKind);
              setRef("");
            }}
          >
            {(Object.keys(LINK_KIND_LABELS) as HomeLinkKind[]).map((value) => (
              <option key={value} value={value}>
                {LINK_KIND_LABELS[value]}
              </option>
            ))}
          </select>
          {kind === "category" ? (
            <select value={ref} aria-label="Категория" onChange={(event) => setRef(event.target.value)}>
              <option value="">Выберите…</option>
              {tree.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.depth ? `— ${item.name}` : item.name}
                  {item.is_active ? "" : " (скрыта)"}
                </option>
              ))}
            </select>
          ) : null}
          {kind === "article" ? (
            <select value={ref} aria-label="Статья" onChange={(event) => setRef(event.target.value)}>
              <option value="">{articles.length ? "Выберите…" : "Нет опубликованных статей"}</option>
              {articles.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          ) : null}
          {kind === "page" ? (
            <select value={ref} aria-label="Страница" onChange={(event) => setRef(event.target.value)}>
              <option value="">Выберите…</option>
              {(Object.entries(LINK_PAGES) as [HomeLinkPage, string][]).map(([value, text]) => (
                <option key={value} value={value}>
                  {text}
                </option>
              ))}
            </select>
          ) : null}
          {kind === "url" ? (
            <input
              value={url}
              placeholder="https://… или /путь/на/сайте/"
              aria-label="Адрес"
              onChange={(event) => setUrl(event.target.value)}
            />
          ) : null}
          <input
            value={title}
            maxLength={HOME_LIMITS.linkTitle}
            placeholder={kind === "url" ? "Подпись" : "Подпись — необязательно"}
            aria-label="Подпись новой вкладки"
            onChange={(event) => setTitle(event.target.value)}
          />
          <button type="button" className="button button-outline" disabled={busy || !ready} onClick={add}>
            Добавить
          </button>
        </div>
      ) : null}
      {links.length ? (
        <button type="button" className="button button-ghost he-links-reset" disabled={busy} onClick={() => save([])}>
          Вернуть основные категории
        </button>
      ) : null}
    </div>
  );
}
