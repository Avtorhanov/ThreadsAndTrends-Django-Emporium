import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { imagesService, productsService } from "../api/catalog";
import { ApiError } from "../api/errors";
import { ImagesEditor } from "../components/catalog/ImagesEditor";
import { ProductForm, type ProductFormValues } from "../components/catalog/ProductForm";
import { VariantsEditor } from "../components/catalog/VariantsEditor";
import { useCategories, useProduct } from "../hooks/useCatalog";

export function ProductEditPage() {
  const params = useParams();
  const navigate = useNavigate();
  const productId = params.id && /^\d+$/.test(params.id) ? Number(params.id) : null;
  const categories = useCategories();
  const product = useProduct(productId);
  const [actionError, setActionError] = useState<string | null>(null);

  async function save({ sizes, ...values }: ProductFormValues) {
    if (productId === null) {
      const created = await productsService.create({
        ...values,
        variants: sizes.length ? sizes.map((size) => ({ size })) : undefined,
      });
      navigate(`/catalog/products/${created.id}`, { replace: true });
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
  const loading = categories.loading || product.loading;
  const error = categories.error ?? product.error;
  const ready = categories.data && (productId === null || product.data);

  return (
    <section className="stack">
      <div className="page-header">
        <Link to="/catalog/products" className="muted">
          ← Товары
        </Link>
        <h1>{productId === null ? "Новый товар" : (product.data?.name ?? "Товар")}</h1>
        {product.data?.deleted_at ? <span className="badge badge-deleted">Удалён</span> : null}
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
      {loading && !ready ? <p className="muted">Загрузка…</p> : null}

      {ready && categories.data ? (
        <ProductForm
          // Новый ключ после сохранения/восстановления — форма берёт свежие значения.
          key={product.data ? `${product.data.id}:${product.data.updated_at}` : "new"}
          product={product.data}
          categories={categories.data}
          onSubmit={save}
        />
      ) : null}

      {current ? (
        <>
          <VariantsEditor
            productId={current.id}
            variants={current.variants}
            onChanged={product.reload}
          />
          <ImagesEditor
            images={current.images}
            hint="Первое фото — обложка в каталоге. JPEG, PNG или WebP до 5 МБ, не больше 10 штук."
            service={{
              upload: (file) => imagesService.upload(current.id, file),
              reorder: (ids) => imagesService.reorder(current.id, ids),
              remove: (id) => imagesService.remove(id),
            }}
            onChanged={product.reload}
          />
        </>
      ) : null}
    </section>
  );
}
