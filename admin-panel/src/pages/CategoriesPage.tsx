import { type FormEvent, useState } from "react";

import { type Category, categoriesService } from "../api/catalog";
import { ApiError } from "../api/errors";
import { sortCategoryTree, useCategories } from "../hooks/useCatalog";
import { Icon } from "../components/Icon";
import { Table } from "../components/Table";
import { Editable } from "../components/ViewOnly";

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
  const [editing, setEditing] = useState<{ id: number; name: string } | null>(null);

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

  function saveName() {
    if (!editing) return;
    const next = editing.name.trim();
    const current = tree.find((category) => category.id === editing.id);
    setEditing(null);
    if (current && next && next !== current.name) {
      void run(() => categoriesService.update(current.id, { name: next }));
    }
  }

  /** Стрелки меняют место среди соседей (корневые — между собой, подкатегории — внутри своей).
   * Номера записываются заново всем, у кого изменились: одинаковые «0» у старых категорий
   * не мешают. */
  function move(category: Category, step: -1 | 1) {
    const siblings = tree.filter((item) => (item.parent ?? null) === (category.parent ?? null));
    const from = siblings.findIndex((item) => item.id === category.id);
    const to = from + step;
    const moved = siblings[from];
    if (!moved || to < 0 || to >= siblings.length) return;
    const next = [...siblings];
    next.splice(from, 1);
    next.splice(to, 0, moved);
    void run(async () => {
      for (const [position, item] of next.entries()) {
        if (item.position !== position) await categoriesService.update(item.id, { position });
      }
    });
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

      <Editable>
        <form className="filters" onSubmit={onCreate}>
          <input
            aria-label="Название новой категории"
            placeholder="Название новой категории"
            value={name}
            maxLength={100}
            onChange={(event) => setName(event.target.value)}
          />
          <select aria-label="Где создать" value={parent} onChange={(event) => setParent(event.target.value)}>
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
      </Editable>

      {error ? <p className="alert">{error}</p> : null}
      {actionError ? <p className="alert">{actionError}</p> : null}

      <Editable>
        <Table loading={loading || busy} className="table-categories">
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
            {tree.map((category) => {
              const siblings = tree.filter((item) => (item.parent ?? null) === (category.parent ?? null));
              const index = siblings.findIndex((item) => item.id === category.id);
              return (
                <tr key={category.id}>
                  <td className={category.depth ? "indent" : "strong"}>
                    {editing?.id === category.id ? (
                      <span className="cat-rename">
                        <input
                          autoFocus
                          aria-label={`Новое название: ${category.name}`}
                          value={editing.name}
                          maxLength={100}
                          onChange={(event) => setEditing({ id: category.id, name: event.target.value })}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") saveName();
                            if (event.key === "Escape") setEditing(null);
                          }}
                        />
                        <button type="button" className="row-tool" aria-label="Сохранить название" title="Сохранить" onClick={saveName}>
                          <Icon name="check" size={18} />
                        </button>
                        <button type="button" className="row-tool" aria-label="Не менять" title="Не менять" onClick={() => setEditing(null)}>
                          <Icon name="close" size={18} />
                        </button>
                      </span>
                    ) : (
                      category.name
                    )}
                  </td>
                  <td className="muted">{category.slug}</td>
                  <td>{category.products_count}</td>
                  <td>
                    <span className="order-arrows">
                      <button
                        type="button"
                        className="row-tool"
                        aria-label={`Выше: ${category.name}`}
                        title="Выше"
                        disabled={busy || index === 0}
                        onClick={() => move(category, -1)}
                      >
                        <Icon name="up" size={18} />
                      </button>
                      <button
                        type="button"
                        className="row-tool"
                        aria-label={`Ниже: ${category.name}`}
                        title="Ниже"
                        disabled={busy || index === siblings.length - 1}
                        onClick={() => move(category, 1)}
                      >
                        <Icon name="down" size={18} />
                      </button>
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${category.is_active ? "badge-active" : "badge-deleted"}`}>
                      {category.is_active ? "Показана" : "Скрыта"}
                    </span>
                  </td>
                  <td className="actions">
                    <span className="row-tools">
                      <button
                        type="button"
                        className="row-tool"
                        disabled={busy}
                        aria-label={`Переименовать ${category.name}`}
                        title="Переименовать (адрес страницы не изменится)"
                        onClick={() => setEditing({ id: category.id, name: category.name })}
                      >
                        <Icon name="pencil" size={18} />
                      </button>
                      <button
                        type="button"
                        className="row-tool"
                        disabled={busy}
                        aria-label={`${category.is_active ? "Скрыть" : "Показать"} ${category.name}`}
                        title={category.is_active ? "Скрыть" : "Показать"}
                        onClick={() =>
                          void run(() => categoriesService.update(category.id, { is_active: !category.is_active }))
                        }
                      >
                        <Icon name={category.is_active ? "eyeOff" : "eye"} size={18} />
                      </button>
                      <button
                        type="button"
                        className="row-tool row-tool-danger"
                        disabled={busy || category.children_count > 0}
                        aria-label={`Удалить ${category.name}`}
                        title={category.children_count > 0 ? "Сначала удалите подкатегории" : "Удалить"}
                        onClick={() => remove(category)}
                      >
                        <Icon name="trash" size={18} />
                      </button>
                    </span>
                  </td>
                </tr>
              );
            })}
            {data && data.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty">
                  Категорий пока нет
                </td>
              </tr>
            ) : null}
          </tbody>
          </Table>
      </Editable>
    </section>
  );
}
