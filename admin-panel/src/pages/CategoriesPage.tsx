import { type FormEvent, useState } from "react";

import { type Category, categoriesService } from "../api/catalog";
import { ApiError } from "../api/errors";
import { sortCategoryTree, useCategories } from "../hooks/useCatalog";

function message(error: unknown): string {
  if (!(error instanceof ApiError)) return "Действие не выполнено.";
  const first = Object.values(error.fieldErrors)[0]?.[0];
  return first ?? error.message;
}

export function CategoriesPage() {
  const { data, loading, error, reload } = useCategories();
  const [name, setName] = useState("");
  const [parent, setParent] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const tree = data ? sortCategoryTree(data) : [];
  const roots = tree.filter((category) => category.depth === 0);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setActionError(null);
    try {
      await action();
      reload();
    } catch (err) {
      setActionError(message(err));
    } finally {
      setBusy(false);
    }
  }

  function onCreate(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    void run(async () => {
      await categoriesService.create({
        name: name.trim(),
        parent: parent ? Number(parent) : null,
      });
      setName("");
    });
  }

  function rename(category: Category) {
    const next = window.prompt("Новое название (адрес страницы не изменится)", category.name);
    if (next && next.trim() && next.trim() !== category.name) {
      void run(() => categoriesService.update(category.id, { name: next.trim() }));
    }
  }

  function remove(category: Category) {
    if (window.confirm(`Удалить категорию «${category.name}»?`)) {
      void run(() => categoriesService.remove(category.id));
    }
  }

  return (
    <section>
      <div className="page-header">
        <h1>Категории</h1>
        <span className="muted">Два уровня; товары — только в категориях без подкатегорий</span>
      </div>

      <form className="filters" onSubmit={onCreate}>
        <input
          placeholder="Название новой категории"
          value={name}
          maxLength={100}
          onChange={(event) => setName(event.target.value)}
        />
        <select value={parent} onChange={(event) => setParent(event.target.value)}>
          <option value="">Корневая категория</option>
          {roots.map((root) => (
            <option key={root.id} value={root.id}>
              Внутри «{root.name}»
            </option>
          ))}
        </select>
        <button type="submit" className="button" disabled={busy || !name.trim()}>
          Добавить
        </button>
      </form>

      {error ? <p className="alert">{error}</p> : null}
      {actionError ? <p className="alert">{actionError}</p> : null}

      <div className="table-wrap">
        <table className={loading || busy ? "table is-loading" : "table"}>
          <thead>
            <tr>
              <th>Название</th>
              <th>Адрес (slug)</th>
              <th>Товаров</th>
              <th>Порядок</th>
              <th>Видимость</th>
              <th aria-label="Действия" />
            </tr>
          </thead>
          <tbody>
            {tree.map((category) => (
              <tr key={category.id}>
                <td className={category.depth ? "indent" : "strong"}>{category.name}</td>
                <td className="muted">{category.slug}</td>
                <td>{category.products_count}</td>
                <td>
                  <input
                    className="input-narrow"
                    type="number"
                    min={0}
                    defaultValue={category.position ?? 0}
                    disabled={busy}
                    onBlur={(event) => {
                      const position = Number(event.target.value);
                      if (Number.isInteger(position) && position >= 0 && position !== category.position) {
                        void run(() => categoriesService.update(category.id, { position }));
                      }
                    }}
                  />
                </td>
                <td>
                  <span className={`badge ${category.is_active ? "badge-active" : "badge-deleted"}`}>
                    {category.is_active ? "Показана" : "Скрыта"}
                  </span>
                </td>
                <td className="actions">
                  <button type="button" className="button button-ghost" disabled={busy} onClick={() => rename(category)}>
                    Переименовать
                  </button>
                  <button
                    type="button"
                    className="button button-ghost"
                    disabled={busy}
                    onClick={() =>
                      void run(() =>
                        categoriesService.update(category.id, { is_active: !category.is_active }),
                      )
                    }
                  >
                    {category.is_active ? "Скрыть" : "Показать"}
                  </button>
                  <button
                    type="button"
                    className="button button-danger"
                    disabled={busy || category.children_count > 0}
                    title={category.children_count > 0 ? "Сначала удалите подкатегории" : undefined}
                    onClick={() => remove(category)}
                  >
                    Удалить
                  </button>
                </td>
              </tr>
            ))}
            {data && data.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty">
                  Категорий пока нет
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
