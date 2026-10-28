import { useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";

import { imagesService, productsService } from "../api/catalog";
import { ApiError } from "../api/errors";
import { ImagesEditor } from "../components/catalog/ImagesEditor";
import { MAX_PRODUCT_IMAGES, PendingPhotos } from "../components/catalog/PendingPhotos";
import { ProductForm, type ProductFormValues } from "../components/catalog/ProductForm";
import { VariantsEditor } from "../components/catalog/VariantsEditor";
import { useCategories, useLabels, useProduct } from "../hooks/useCatalog";

type CreatedState = { photosFailed?: string[] } | null;

export function ProductEditPage() {
  const params = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const productId = params.id && /^\d+$/.test(params.id) ? Number(params.id) : null;
  const categories = useCategories();
  const labels = useLabels();
  const product = useProduct(productId);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pending, setPending] = useState<File[]>([]);
  const [uploading, setUploading] = useState<string | null>(null);
  const failed = (location.state as CreatedState)?.photosFailed ?? [];

  async function save({ sizes, ...values }: ProductFormValues) {
    if (productId === null) {
      const created = await productsService.create({
        ...values,
        variants: sizes.length ? sizes.map((size) => ({ size })) : undefined,
      });
      // Фото — после создания, по одному: порядок загрузки = порядок в галерее, ошибка одного
      // файла не теряет остальные и уже введённые данные (товар создан).
      const photosFailed: string[] = [];
      for (const [index, file] of pending.entries()) {
        setUploading(`Загрузка фото ${index + 1} из ${pending.length}…`);
        try {
          await imagesService.upload(created.id, file);
        } catch {
          photosFailed.push(file.name);
        }
      }
      setUploading(null);
      setPending([]);
      navigate(`/catalog/products/${created.id}`, { replace: true, state: { photosFailed } });
    } else {
      product.set(await productsService.update(productId, values));
    }
  }

  async function toggleDeleted() {
    if (productId === null || !product.data) return;
    const deleted = Boolean(product.data.deleted_at);
    if (!deleted && !window.confirm("Удалить товар? Он пропадёт с витрины, история заказов сохранится.")) return;
    setActionError(null);
    try {
      if (deleted) product.set(await productsService.restore(productId));
      else {
        await productsService.remove(productId);
        product.reload();
      }
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Действие не выполнено.");
    }
  }

  const current = product.data;
  const loading = categories.loading || product.loading || labels.loading;
  const error = categories.error ?? product.error ?? labels.error;
  const ready = categories.data && labels.data && (productId === null || product.data);

  return (
    <section className="stack">
      <div className="page-header">
        <Link to="/catalog/products" className="muted">
          ← Товары
        </Link>
        <h1>{productId === null ? "Новый товар" : (product.data?.name ?? "Товар")}</h1>
        {product.data?.deleted_at ? <span className="badge badge-deleted">Удалён</span> : null}
        {product.data && !product.data.deleted_at && product.data.is_active ? (
          <a className="button button-ghost" href={`/product/${product.data.slug}/`} target="_blank" rel="noreferrer">
            Открыть на сайте
          </a>
        ) : null}
        {product.data ? (
          <button
            type="button"
            className={product.data.deleted_at ? "button header-action" : "button button-danger header-action"}
            onClick={() => void toggleDeleted()}
          >
            {product.data.deleted_at ? "Восстановить" : "Удалить"}
          </button>
        ) : null}
      </div>

      {error ? <p className="alert">{error}</p> : null}
      {actionError ? <p className="alert">{actionError}</p> : null}
      {failed.length ? (
        <p className="alert">
          Товар создан, но не загрузились фото: {failed.join(", ")}. Добавьте их ещё раз в группе «Фото».
        </p>
      ) : null}
      {uploading ? <p className="note note-info">{uploading}</p> : null}
      {loading && !ready ? <p className="muted">Загрузка…</p> : null}

      {ready && categories.data && labels.data ? (
        <ProductForm
          // Новый ключ после сохранения/восстановления — форма берёт свежие значения.
          key={product.data ? `${product.data.id}:${product.data.updated_at}` : "new"}
          product={product.data}
          categories={categories.data}
          labels={labels.data}
          extraDirty={pending.length > 0}
          onSubmit={save}
          photos={
            current ? (
              <ImagesEditor
                images={current.images}
                hint={`Первое фото — обложка в каталоге. JPEG, PNG или WebP до 5 МБ, не больше ${MAX_PRODUCT_IMAGES} штук.`}
                service={{
                  upload: (file) => imagesService.upload(current.id, file),
                  reorder: (ids) => imagesService.reorder(current.id, ids),
                  remove: (id) => imagesService.remove(id),
                }}
                onChanged={product.reload}
              />
            ) : (
              <PendingPhotos files={pending} onChange={setPending} />
            )
          }
          stock={
            current ? (
              <VariantsEditor productId={current.id} variants={current.variants} onChanged={product.reload} />
            ) : null
          }
        />
      ) : null}
    </section>
  );
}
