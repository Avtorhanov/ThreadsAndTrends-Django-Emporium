import { useMemo, useState } from "react";
import { Link, useLocation } from "react-router";

import { type ProductRow, productsService } from "../api/catalog";
import { ApiError } from "../api/errors";
import { BackLink } from "../components/BackLink";
import { Icon } from "../components/Icon";
import { type BatchCategory, batchCategories, categoryLabel, drafts as draftsText, isReady } from "../components/catalog/batch";
import { CategorySheet } from "../components/catalog/CategorySheet";
import { useCategories, useLabels, useLoader } from "../hooks/useCatalog";
import { formatKopecks, parseRublesToKopecks } from "../lib/money";
import { BatchSteps, type BatchResult } from "./ProductBatchPage";

const MAX_PAGES = 20; // 20 × 20 — с запасом больше любой пачки

async function loadDrafts(): Promise<ProductRow[]> {
  const rows: ProductRow[] = [];
  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const data = await productsService.list({ search: "", status: "draft", label: "", category: null, stock: "", page });
    rows.push(...data.results);
    if (!data.next) break;
  }
  return rows;
}

function errorText(error: unknown): string {
  if (!(error instanceof ApiError)) return "Действие не выполнено.";
  return Object.values(error.fieldErrors)[0]?.[0] ?? error.message;
}

type Filter = "all" | "todo" | "ready" | `c${number}`;

/** Черновики из «Добавить пачкой»: правка по одному или сразу нескольким, публикация готовых. */
export function ProductDraftsPage() {
  const location = useLocation();
  const result = location.state as BatchResult | null;
  const categories = useCategories();
  const labels = useLabels();
  const list = useLoader(loadDrafts, "drafts", "Не удалось загрузить черновики.");
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [massPrice, setMassPrice] = useState("");
  const [sheet, setSheet] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const all = categories.data ?? [];
  const leaf = useMemo(() => batchCategories(all), [all]);
  const tone = new Map(leaf.map((item) => [item.id, item.tone]));
  const labelName = new Map((labels.data ?? []).map((item) => [item.id, item.name]));
  const rows = list.data ?? [];
  const readyRows = rows.filter(isReady);

  const shown = rows.filter((row) => {
    if (filter === "ready") return isReady(row);
    if (filter === "todo") return !isReady(row);
    if (filter.startsWith("c")) return row.category === Number(filter.slice(1));
    return true;
  });
  const checked = rows.filter((row) => selected.has(row.id));
  const readyChecked = checked.filter(isReady);
  const counts = new Map<number, number>();
  for (const row of rows) counts.set(row.category, (counts.get(row.category) ?? 0) + 1);

  const filters: { key: Filter; label: string; tone?: number }[] = [
    { key: "all", label: `Все · ${rows.length}` },
    { key: "todo", label: `Нет цены · ${rows.length - readyRows.length}` },
    { key: "ready", label: `Готовые · ${readyRows.length}` },
    ...leaf
      .filter((category) => counts.get(category.id))
      .map((category) => ({
        key: `c${category.id}` as Filter,
        label: `${categoryLabel(category, all)} · ${counts.get(category.id)}`,
        tone: category.tone,
      })),
  ];

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setActionError(null);
    setNotice(null);
    try {
      setNotice(await action());
      setSelected(new Set());
      list.reload();
    } catch (err) {
      setActionError(errorText(err));
      list.reload();
    } finally {
      setBusy(false);
    }
  }

  function applyPrice() {
    const kopecks = parseRublesToKopecks(massPrice);
    if (kopecks === null || kopecks <= 0) {
      setActionError("Цена — например 2490 или 2490,50.");
      return;
    }
    void run(async () => {
      for (const row of checked) await productsService.update(row.id, { price_kopecks: kopecks });
      setMassPrice("");
      return `Цена ${formatKopecks(kopecks)} задана: ${draftsText(checked.length)}`;
    });
  }

  function applyCategory(category: BatchCategory) {
    setSheet(false);
    void run(async () => {
      const done = await productsService.bulk({ ids: checked.map((row) => row.id), category: category.id });
      return `Перенесено в «${category.name}»: ${draftsText(done.updated)}`;
    });
  }

  function publish(ids: number[]) {
    void run(async () => {
      const done = await productsService.bulk({ ids, is_active: true });
      return `Опубликовано: ${done.updated}. Товары уже на витрине.`;
    });
  }

  function remove() {
    if (!window.confirm(`Удалить ${draftsText(checked.length)}? Их можно будет восстановить в «Товары → Удалённые».`)) return;
    void run(async () => {
      for (const row of checked) await productsService.remove(row.id);
      return `Удалено: ${draftsText(checked.length)}`;
    });
  }

  const order = shown.map((row) => row.id);

  return (
    <section className="batch">
      <div className="page-header">
        <BackLink to="/catalog/products" label="Товары" />
        <h1>Черновики</h1>
        {rows.length ? (
          <span className="muted">
            Готово {readyRows.length} из {rows.length}
          </span>
        ) : null}
        <Link to="/catalog/products/batch" className="button button-ghost header-action">
          <Icon name="plus" size={16} /> Добавить пачкой
        </Link>
      </div>
      {/* Шаги — когда пришли из «Добавить пачкой»; открытым из «Товаров» спискам они ни к чему. */}
      {result ? <BatchSteps current={2} /> : null}

      {result && (result.created || result.failed.length) ? (
        <p className={result.failed.length ? "note note-warning" : "note note-success"} role="status">
          Создано {draftsText(result.created)}.
          {result.failed.length ? ` Не получилось: ${result.failed.join("; ")}.` : ""}
        </p>
      ) : null}
      {list.error ? <p className="alert">{list.error}</p> : null}
      {actionError ? <p className="alert">{actionError}</p> : null}
      {notice ? (
        <p className="note note-success" role="status">
          {notice}
        </p>
      ) : null}
      {list.loading && !list.data ? <p className="muted">Загрузка…</p> : null}

      {list.data && rows.length === 0 ? (
        <div className="card batch-empty-list">
          <h2>Черновиков нет</h2>
          <p className="muted">Добавьте сразу несколько товаров по фото — они появятся здесь до публикации.</p>
          <Link to="/catalog/products/batch" className="button button-accent">
            Добавить пачкой
          </Link>
        </div>
      ) : null}

      {rows.length ? (
        <>
          <div className="batch-chips" role="group" aria-label="Показать">
            {filters.map((item) => (
              <button
                key={item.key}
                type="button"
                className="batch-chip"
                aria-pressed={filter === item.key}
                onClick={() => {
                  setFilter(item.key);
                  setSelected(new Set());
                }}
              >
                {item.tone !== undefined ? <span className={`cat-dot cat-tone-${item.tone}`} aria-hidden="true" /> : null}
                {item.label}
              </button>
            ))}
          </div>

          <div className="batch-toolbar">
            <strong className="batch-toolbar-text" aria-live="polite">
              {checked.length ? `Выбрано: ${checked.length}` : draftsText(shown.length)}
            </strong>
            {shown.length && !shown.every((row) => selected.has(row.id)) ? (
              <button type="button" className="button button-ghost button-small" onClick={() => setSelected(new Set(order))}>
                Выбрать все
              </button>
            ) : null}
            {checked.length ? (
              <button type="button" className="bulk-text" onClick={() => setSelected(new Set())}>
                Снять
              </button>
            ) : null}
          </div>

          <div className="draft-list">
            {shown.map((row) => {
              const ready = isReady(row);
              const isChecked = selected.has(row.id);
              const toneId = tone.get(row.category);
              return (
                <article key={row.id} className={isChecked ? "draft-card is-selected" : "draft-card"}>
                  <Link to={`/catalog/products/${row.id}`} state={{ drafts: order }} className="draft-open">
                    {row.cover_url ? (
                      <img className="draft-cover" src={row.cover_url} alt="" loading="lazy" />
                    ) : (
                      <span className="draft-cover thumb-empty" aria-hidden="true" />
                    )}
                    <span className="draft-body">
                      <strong className="draft-title">{row.name}</strong>
                      <span className="draft-meta">
                        <span className={`cat-dot ${toneId === undefined ? "cat-none" : `cat-tone-${toneId}`}`} aria-hidden="true" />
                        {row.category_name}
                        {row.status !== null && labelName.get(row.status) ? ` · ${labelName.get(row.status)}` : ""}
                      </span>
                      <span className="draft-price">{ready ? formatKopecks(row.price_kopecks) : "Цена —"}</span>
                      <span className="muted small">Остаток: {row.total_stock}</span>
                      <span className={ready ? "badge badge-success" : "badge badge-warning"}>
                        {ready ? "Готов к публикации" : "Нет цены"}
                      </span>
                    </span>
                  </Link>
                  <label className="draft-check">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      aria-label={`Выбрать ${row.name}`}
                      onChange={() => toggle(row.id)}
                    />
                  </label>
                </article>
              );
            })}
            {shown.length === 0 ? <p className="muted">В этом фильтре пусто.</p> : null}
          </div>

          {checked.length ? (
            <div className="batch-dock batch-actions" role="region" aria-label="Действия с отмеченными черновиками">
              <form
                className="batch-price"
                onSubmit={(event) => {
                  event.preventDefault();
                  applyPrice();
                }}
              >
                <label className="sr-only" htmlFor="mass-price">
                  Цена для выбранных, ₽
                </label>
                <input
                  id="mass-price"
                  inputMode="decimal"
                  value={massPrice}
                  placeholder="Цена для выбранных, ₽"
                  onChange={(event) => setMassPrice(event.target.value)}
                />
                <button type="submit" className="button button-accent" disabled={busy || !massPrice.trim()}>
                  Задать
                </button>
              </form>
              <div className="batch-actions-grid batch-actions-grid-3">
                <button type="button" className="batch-action" disabled={busy} onClick={() => setSheet(true)}>
                  <Icon name="folder" />
                  Категория
                </button>
                <button type="button" className="batch-action" disabled={busy} onClick={remove}>
                  <Icon name="trash" />
                  Удалить
                </button>
                <button
                  type="button"
                  className="batch-action is-primary"
                  disabled={busy || readyChecked.length === 0}
                  onClick={() => publish(readyChecked.map((row) => row.id))}
                >
                  <Icon name="check" />
                  {readyChecked.length ? `Опубликовать · ${readyChecked.length}` : "Нет готовых"}
                </button>
              </div>
            </div>
          ) : (
            <div className="batch-dock batch-next">
              <span className="muted small">
                {readyRows.length
                  ? "Черновики хранятся на сервере — можно закончить на компьютере."
                  : "Отметьте черновики, чтобы задать цену или категорию сразу нескольким."}
              </span>
              <button
                type="button"
                className="button button-accent batch-cta"
                disabled={busy || readyRows.length === 0}
                onClick={() => publish(readyRows.map((row) => row.id))}
              >
                {readyRows.length ? `Опубликовать готовые · ${readyRows.length}` : "Нет готовых к публикации"}
              </button>
            </div>
          )}
        </>
      ) : null}

      {sheet ? (
        <CategorySheet
          title={`Категория · ${draftsText(checked.length)}`}
          categories={leaf}
          all={all}
          counts={counts}
          onPick={applyCategory}
          onClose={() => setSheet(false)}
        />
      ) : null}
    </section>
  );
}
