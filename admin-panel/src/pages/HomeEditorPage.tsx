import { useEffect, useRef, useState } from "react";

import { ApiError } from "../api/errors";
import {
  BLOCK_TYPES,
  type HomeBlock,
  type HomeBlockChanges,
  type HomeBlockKind,
  KIND_LABELS,
  homeService,
  inkFor,
} from "../api/home";
import { BlockSettings } from "../components/home/BlockSettings";
import { HomePreview } from "../components/home/HomePreview";
import { useCategories, useLoader } from "../hooks/useCatalog";

const TEXT_DELAY = 700;
const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

type View = "list" | "settings" | "preview";

function message(error: unknown): string {
  if (!(error instanceof ApiError)) return "Действие не выполнено.";
  return Object.values(error.fieldErrors)[0]?.[0] ?? error.message;
}

/**
 * Главная из блоков. Правки сохраняются в черновик сами (текст — с паузой, выбор — сразу);
 * покупатель видит только опубликованное. На телефоне список, настройки и предпросмотр —
 * отдельные экраны.
 */
export function HomeEditorPage() {
  const loader = useLoader(() => homeService.get(), "home", "Не удалось загрузить главную.");
  const categories = useCategories();
  const [blocks, setBlocks] = useState<HomeBlock[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [publishedAt, setPublishedAt] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [view, setView] = useState<View>("list");
  const [blockErrors, setBlockErrors] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(0);
  const pending = useRef(new Map<number, HomeBlockChanges>());
  const timers = useRef(new Map<number, number>());

  useEffect(() => {
    if (!loader.data) return;
    setBlocks(loader.data.blocks);
    setHasChanges(loader.data.has_changes);
    setPublishedAt(loader.data.published_at);
    setSelectedId((prev) => prev ?? loader.data?.blocks[0]?.id ?? null);
  }, [loader.data]);

  // Несохранённые правки (ещё не ушли на сервер) — предупреждение при закрытии вкладки.
  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => {
      if (pending.current.size || saving) event.preventDefault();
    };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [saving]);

  useEffect(() => {
    const active = timers.current;
    return () => active.forEach((timer) => window.clearTimeout(timer));
  }, []);

  /** Ответ сервера по блоку: если пока ждали, блок правили ещё, — берём только вычисляемое. */
  function merge(saved: HomeBlock) {
    setBlocks((prev) =>
      prev.map((block) => {
        if (block.id !== saved.id) return block;
        if (!pending.current.has(saved.id)) return saved;
        return { ...block, ink: saved.ink, image_url: saved.image_url, preview_products: saved.preview_products };
      }),
    );
  }

  function setBlockError(id: number, text: string | null) {
    setBlockErrors((prev) => {
      const next = { ...prev };
      if (text) next[id] = text;
      else delete next[id];
      return next;
    });
  }

  async function flush(id: number) {
    window.clearTimeout(timers.current.get(id));
    timers.current.delete(id);
    const changes = pending.current.get(id);
    if (!changes) return true;
    pending.current.delete(id);
    setSaving((n) => n + 1);
    try {
      merge(await homeService.update(id, changes));
      setHasChanges(true);
      setBlockError(id, null);
      return true;
    } catch (err) {
      setBlockError(id, message(err));
      return false;
    } finally {
      setSaving((n) => n - 1);
    }
  }

  function edit(id: number, changes: HomeBlockChanges, delay = TEXT_DELAY) {
    setNotice(null);
    setBlocks((prev) =>
      prev.map((block) => {
        if (block.id !== id) return block;
        const next = { ...block, ...changes } as HomeBlock;
        return changes.color ? { ...next, ink: inkFor(changes.color) } : next;
      }),
    );
    pending.current.set(id, { ...pending.current.get(id), ...changes });
    window.clearTimeout(timers.current.get(id));
    timers.current.set(
      id,
      window.setTimeout(() => void flush(id), delay),
    );
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  function add(kind: HomeBlockKind) {
    void run(async () => {
      const block = await homeService.add(kind);
      setBlocks((prev) => [...prev, block]);
      setSelectedId(block.id);
      setView("settings");
      setHasChanges(true);
    });
  }

  function move(index: number, delta: number) {
    const next = [...blocks];
    const [block] = next.splice(index, 1);
    if (!block) return;
    next.splice(index + delta, 0, block);
    setBlocks(next);
    void run(async () => {
      try {
        await homeService.reorder(next.map((item) => item.id));
        setHasChanges(true);
      } catch (err) {
        loader.reload(); // порядок мог поменяться в другой вкладке
        throw err;
      }
    });
  }

  function remove(id: number) {
    void run(async () => {
      window.clearTimeout(timers.current.get(id));
      timers.current.delete(id);
      pending.current.delete(id);
      await homeService.remove(id);
      const rest = blocks.filter((block) => block.id !== id);
      setBlocks(rest);
      setSelectedId(rest[0]?.id ?? null);
      setView("list");
      setHasChanges(true);
    });
  }

  function upload(id: number, file: File) {
    if (file.size > 5 * 1024 * 1024) {
      setBlockError(id, "Файл больше 5 МБ.");
      return;
    }
    void run(async () => {
      try {
        merge(await homeService.uploadImage(id, file));
        setHasChanges(true);
        setBlockError(id, null);
      } catch (err) {
        setBlockError(id, message(err));
      }
    });
  }

  function removeImage(id: number) {
    void run(async () => {
      try {
        merge(await homeService.removeImage(id));
        setHasChanges(true);
        setBlockError(id, null);
      } catch (err) {
        setBlockError(id, message(err));
      }
    });
  }

  function publish() {
    void run(async () => {
      const results = await Promise.all([...pending.current.keys()].map((id) => flush(id)));
      if (results.includes(false) || Object.keys(blockErrors).length) {
        setError("Не все правки сохранены — исправьте блоки с ошибкой и опубликуйте снова.");
        return;
      }
      const state = await homeService.publish();
      setHasChanges(state.has_changes);
      setPublishedAt(state.published_at);
      setNotice("Опубликовано: покупатели видят новую главную на сайте и в приложении.");
    });
  }

  const selected = blocks.find((block) => block.id === selectedId) ?? null;
  const unsaved = saving > 0 || pending.current.size > 0;
  const status = hasChanges
    ? { text: "Есть неопубликованные изменения", tone: "warn" }
    : publishedAt
      ? { text: `Опубликовано ${dateFormat.format(new Date(publishedAt))}`, tone: "ok" }
      : { text: "Ещё не опубликована", tone: "none" };

  return (
    <section className="stack">
      <div className="page-header">
        <h1>Главная витрины</h1>
        <span className={`he-status he-status-${status.tone}`}>{status.text}</span>
        <button
          type="button"
          className={hasChanges ? "button button-accent header-action" : "button button-outline header-action"}
          disabled={busy || !hasChanges}
          onClick={publish}
        >
          {busy && hasChanges ? "Публикуем…" : "Опубликовать"}
        </button>
      </div>
      <p className="muted small he-hint">
        Правки — черновик: покупатель видит только опубликованное.{" "}
        {unsaved ? "Сохраняем…" : "Все правки сохранены в черновик."}
      </p>
      <ol className="he-steps">
        <li>Добавьте блок или выберите готовый</li>
        <li>Настройте, расставьте, скройте лишнее</li>
        <li>«Опубликовать» — покупатели видят изменения</li>
      </ol>

      {loader.error ?? categories.error ? <p className="alert">{loader.error ?? categories.error}</p> : null}
      {error ? <p className="alert">{error}</p> : null}
      {notice ? <p className="note note-success">{notice}</p> : null}
      {loader.loading && !loader.data ? <p className="muted">Загрузка…</p> : null}

      {loader.data && categories.data ? (
        <div className="he" data-view={view}>
          <div className="he-list">
            <div className="card">
              <div className="he-list-head">
                <h2>Блоки на странице</h2>
                <button type="button" className="button button-outline he-phone-only" onClick={() => setView("preview")}>
                  Предпросмотр
                </button>
              </div>
              {blocks.length === 0 ? (
                <p className="muted">Блоков нет — на главной только каталог. Добавьте первый блок ниже.</p>
              ) : (
                <ol className="he-rows">
                  {blocks.map((block, index) => (
                    <li
                      key={block.id}
                      className={[
                        "he-row",
                        block.id === selectedId ? "is-selected" : "",
                        block.is_visible ? "" : "is-hidden",
                      ].join(" ")}
                    >
                      <button
                        type="button"
                        className="he-row-main"
                        onClick={() => {
                          setSelectedId(block.id);
                          setView("settings");
                        }}
                      >
                        <span className="he-row-num">{index + 1}</span>
                        <span className="he-row-text">
                          <span className="muted small">
                            {KIND_LABELS[block.kind]}
                            {block.is_visible ? "" : " · скрыт"}
                            {blockErrors[block.id] ? " · ошибка" : ""}
                          </span>
                          <strong>{block.title || "Без заголовка"}</strong>
                        </span>
                      </button>
                      <div className="he-row-actions">
                        <button
                          type="button"
                          aria-label="Выше"
                          disabled={busy || index === 0}
                          onClick={() => move(index, -1)}
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          aria-label="Ниже"
                          disabled={busy || index === blocks.length - 1}
                          onClick={() => move(index, 1)}
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          className={block.is_visible ? "he-eye is-on" : "he-eye"}
                          aria-label={block.is_visible ? "Скрыть блок" : "Показать блок"}
                          aria-pressed={block.is_visible}
                          onClick={() => edit(block.id, { is_visible: !block.is_visible }, 0)}
                        >
                          {block.is_visible ? "Виден" : "Скрыт"}
                        </button>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </div>
            <div className="card">
              <h2>Новый блок</h2>
              <div className="he-types">
                {BLOCK_TYPES.map((type) => (
                  <button
                    key={type.kind}
                    type="button"
                    className="he-type"
                    disabled={busy}
                    onClick={() => add(type.kind)}
                  >
                    <strong>+ {type.label}</strong>
                    <span className="muted small">{type.hint}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="he-preview">
            <HomePreview
              blocks={blocks}
              categories={categories.data}
              selectedId={selectedId}
              onSelect={(id) => {
                setSelectedId(id);
                setView("settings");
              }}
              onBack={() => setView("list")}
            />
          </div>

          <div className="he-settings">
            {selected ? (
              <BlockSettings
                key={selected.id}
                block={selected}
                categories={categories.data}
                error={blockErrors[selected.id] ?? null}
                busy={busy}
                onChange={(changes, delay) => edit(selected.id, changes, delay)}
                onUpload={(file) => upload(selected.id, file)}
                onRemoveImage={() => removeImage(selected.id)}
                onDelete={() => remove(selected.id)}
                onBack={() => setView("list")}
              />
            ) : (
              <div className="card">
                <p className="muted">Выберите блок слева или в предпросмотре.</p>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}
