import { type FormEvent, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { type Article, articleImagesService, articlesService, MAX_ARTICLE_IMAGES } from "../api/content";
import { ApiError, type FieldErrors } from "../api/errors";
import { ImagesEditor } from "../components/catalog/ImagesEditor";
import { useArticle } from "../hooks/useContent";
import { storeUrl } from "../lib/site";

function FieldError({ errors, name }: { errors: FieldErrors; name: string }) {
  const message = errors[name]?.[0];
  return message ? <span className="field-error">{message}</span> : null;
}

type FormProps = {
  article: Article | null;
  onSubmit: (values: { title: string; excerpt: string; body: string; is_published: boolean }) => Promise<void>;
};

function ArticleForm({ article, onSubmit }: FormProps) {
  const [title, setTitle] = useState(article?.title ?? "");
  const [excerpt, setExcerpt] = useState(article?.excerpt ?? "");
  const [body, setBody] = useState(article?.body ?? "");
  const [published, setPublished] = useState(article?.is_published ?? false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setErrors({});
    setFormError(null);
    setSaving(true);
    try {
      await onSubmit({ title: title.trim(), excerpt: excerpt.trim(), body, is_published: published });
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fieldErrors);
        setFormError(err.message);
      } else {
        setFormError("Не удалось сохранить статью.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card form-grid" onSubmit={submit}>
      {formError ? <p className="alert">{formError}</p> : null}
      <label className="field">
        Заголовок
        <input value={title} maxLength={200} required onChange={(e) => setTitle(e.target.value)} />
        <FieldError errors={errors} name="title" />
      </label>
      <label className="field">
        Короткое описание
        <input
          value={excerpt}
          maxLength={300}
          placeholder="Одна-две фразы под заголовком в списке статей"
          onChange={(e) => setExcerpt(e.target.value)}
        />
        <FieldError errors={errors} name="excerpt" />
      </label>
      <label className="field">
        Текст
        <textarea rows={14} value={body} maxLength={20000} onChange={(e) => setBody(e.target.value)} />
        <span className="muted">Абзацы разделяйте пустой строкой. Оформление (жирный, ссылки) не поддерживается.</span>
        <FieldError errors={errors} name="body" />
      </label>
      <label className="checkbox">
        <input type="checkbox" checked={published} onChange={(e) => setPublished(e.target.checked)} />
        Опубликована (видна на сайте и в приложении)
      </label>
      <div>
        <button type="submit" className="button" disabled={saving}>
          {saving ? "Сохранение…" : article ? "Сохранить" : "Создать статью"}
        </button>
      </div>
    </form>
  );
}

export function ArticleEditPage() {
  const params = useParams();
  const navigate = useNavigate();
  const articleId = params.id && /^\d+$/.test(params.id) ? Number(params.id) : null;
  const article = useArticle(articleId);
  const [actionError, setActionError] = useState<string | null>(null);
  const current = article.data;

  async function save(values: { title: string; excerpt: string; body: string; is_published: boolean }) {
    if (articleId === null) {
      const created = await articlesService.create(values);
      navigate(`/content/articles/${created.id}`, { replace: true });
    } else {
      article.set(await articlesService.update(articleId, values));
    }
  }

  async function toggleDeleted() {
    if (articleId === null || !current) return;
    const deleted = Boolean(current.deleted_at);
    if (!deleted && !window.confirm("Удалить статью? Она пропадёт с сайта и из приложения.")) return;
    setActionError(null);
    try {
      if (deleted) article.set(await articlesService.restore(articleId));
      else {
        await articlesService.remove(articleId);
        article.reload();
      }
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Действие не выполнено.");
    }
  }

  const ready = articleId === null || current;

  return (
    <section className="stack">
      <div className="page-header">
        <Link to="/content/articles" className="muted">
          ← Статьи
        </Link>
        <h1>{articleId === null ? "Новая статья" : (current?.title ?? "Статья")}</h1>
        {current?.deleted_at ? <span className="badge badge-deleted">Удалена</span> : null}
        {current && current.is_published && !current.deleted_at ? (
          <a className="button button-ghost" href={storeUrl(`articles/${current.slug}/`)} target="_blank" rel="noreferrer">
            Открыть на сайте
          </a>
        ) : null}
        {current ? (
          <button
            type="button"
            className={current.deleted_at ? "button header-action" : "button button-danger header-action"}
            onClick={() => void toggleDeleted()}
          >
            {current.deleted_at ? "Восстановить" : "Удалить"}
          </button>
        ) : null}
      </div>

      {article.error ? <p className="alert">{article.error}</p> : null}
      {actionError ? <p className="alert">{actionError}</p> : null}
      {article.loading && !ready ? <p className="muted">Загрузка…</p> : null}

      {ready && !current?.deleted_at ? (
        <ArticleForm
          // Новый ключ после сохранения — форма берёт свежие значения.
          key={current ? `${current.id}:${current.updated_at}` : "new"}
          article={current ?? null}
          onSubmit={save}
        />
      ) : null}

      {current && !current.deleted_at ? (
        <ImagesEditor
          images={current.images}
          hint={`Первое фото — обложка статьи, остальные показываются под текстом. JPEG, PNG или WebP до 5 МБ, не больше ${MAX_ARTICLE_IMAGES}.`}
          service={{
            upload: (file) => articleImagesService.upload(current.id, file),
            reorder: (ids) => articleImagesService.reorder(current.id, ids),
            remove: (id) => articleImagesService.remove(id),
          }}
          onChanged={article.reload}
        />
      ) : null}
    </section>
  );
}
