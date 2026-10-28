import { api, unwrap } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

export type Category = Schemas["AdminCategory"];
export type CategoryInput = Schemas["AdminCategoryRequest"];
export type CategoryPatch = Schemas["PatchedAdminCategoryRequest"];
export type ProductRow = Schemas["AdminProduct"];
export type ProductPage = Schemas["PaginatedAdminProductList"];
export type Product = Schemas["AdminProductDetail"];
export type ProductCreate = Schemas["AdminProductCreateRequest"];
export type ProductPatch = Schemas["PatchedAdminProductUpdateRequest"];
export type Variant = Schemas["AdminVariant"];
export type VariantInput = Schemas["AdminVariantRequest"];
export type VariantPatch = Schemas["PatchedAdminVariantRequest"];
export type ProductImage = Schemas["AdminImage"];
/** Статус товара для покупателя («Под заказ»…) — справочник. */
export type ProductLabel = Schemas["AdminProductStatus"];
export type ProductLabelInput = Schemas["AdminProductStatusRequest"];
export type ProductLabelPatch = Schemas["PatchedAdminProductStatusRequest"];
export type ProductBulk = Schemas["AdminProductBulkRequest"];
export type LabelTone = "success" | "warning" | "info" | "neutral";

/** Видимость в списке панели (фильтр status API). */
export type ProductStatus = "active" | "inactive" | "deleted";
export type StockFilter = "in_stock" | "out_of_stock";

export type ProductQuery = {
  search: string;
  status: ProductStatus | "";
  /** id статуса товара или "none" — без статуса. */
  label: string;
  category: number | null;
  stock: StockFilter | "";
  page: number;
};

export const PRODUCTS_PAGE_SIZE = 20;

const PRODUCT = "/api/v1/admin/catalog/products/{id}/" as const;

export const categoriesService = {
  list(): Promise<Category[]> {
    return unwrap(api.GET("/api/v1/admin/catalog/categories/"));
  },
  create(body: CategoryInput): Promise<Category> {
    return unwrap(api.POST("/api/v1/admin/catalog/categories/", { body }));
  },
  update(id: number, body: CategoryPatch): Promise<Category> {
    return unwrap(
      api.PATCH("/api/v1/admin/catalog/categories/{id}/", { params: { path: { id } }, body }),
    );
  },
  remove(id: number): Promise<void> {
    return unwrap(
      api.DELETE("/api/v1/admin/catalog/categories/{id}/", { params: { path: { id } } }),
    ).then(() => undefined);
  },
};

export const productsService = {
  list({ search, status, label, category, stock, page }: ProductQuery): Promise<ProductPage> {
    return unwrap(
      api.GET("/api/v1/admin/catalog/products/", {
        params: {
          query: {
            search: search || undefined,
            status: status || undefined,
            label: label || undefined,
            category: category ?? undefined,
            stock: stock || undefined,
            page,
          },
        },
      }),
    );
  },
  get(id: number): Promise<Product> {
    return unwrap(api.GET(PRODUCT, { params: { path: { id } } }));
  },
  create(body: ProductCreate): Promise<Product> {
    return unwrap(api.POST("/api/v1/admin/catalog/products/", { body }));
  },
  update(id: number, body: ProductPatch): Promise<Product> {
    return unwrap(api.PATCH(PRODUCT, { params: { path: { id } }, body }));
  },
  remove(id: number): Promise<void> {
    return unwrap(api.DELETE(PRODUCT, { params: { path: { id } } })).then(() => undefined);
  },
  restore(id: number): Promise<Product> {
    return unwrap(
      api.POST("/api/v1/admin/catalog/products/{id}/restore/", { params: { path: { id } } }),
    );
  },
  bulk(body: ProductBulk): Promise<{ updated: number }> {
    return unwrap(api.POST("/api/v1/admin/catalog/products/bulk/", { body }));
  },
};

export const labelsService = {
  list(): Promise<ProductLabel[]> {
    return unwrap(api.GET("/api/v1/admin/catalog/statuses/"));
  },
  create(body: ProductLabelInput): Promise<ProductLabel> {
    return unwrap(api.POST("/api/v1/admin/catalog/statuses/", { body }));
  },
  update(id: number, body: ProductLabelPatch): Promise<ProductLabel> {
    return unwrap(
      api.PATCH("/api/v1/admin/catalog/statuses/{id}/", { params: { path: { id } }, body }),
    );
  },
  remove(id: number): Promise<void> {
    return unwrap(
      api.DELETE("/api/v1/admin/catalog/statuses/{id}/", { params: { path: { id } } }),
    ).then(() => undefined);
  },
};

export const LABEL_TONES: Record<LabelTone, string> = {
  success: "Зелёный",
  warning: "Жёлтый",
  info: "Синий",
  neutral: "Серый",
};

export const variantsService = {
  create(productId: number, body: VariantInput): Promise<Variant> {
    return unwrap(
      api.POST("/api/v1/admin/catalog/products/{id}/variants/", {
        params: { path: { id: productId } },
        body,
      }),
    );
  },
  update(id: number, body: VariantPatch): Promise<Variant> {
    return unwrap(
      api.PATCH("/api/v1/admin/catalog/variants/{id}/", { params: { path: { id } }, body }),
    );
  },
  remove(id: number): Promise<void> {
    return unwrap(
      api.DELETE("/api/v1/admin/catalog/variants/{id}/", { params: { path: { id } } }),
    ).then(() => undefined);
  },
};

export const imagesService = {
  upload(productId: number, file: File): Promise<ProductImage> {
    return unwrap(
      api.POST("/api/v1/admin/catalog/products/{id}/images/", {
        params: { path: { id: productId } },
        // Тело уходит multipart/form-data: заголовок Content-Type с boundary ставит браузер.
        body: { image: file.name },
        bodySerializer: () => {
          const form = new FormData();
          form.append("image", file);
          return form;
        },
      }),
    );
  },
  reorder(productId: number, ids: number[]): Promise<ProductImage[]> {
    return unwrap(
      api.POST("/api/v1/admin/catalog/products/{id}/images/reorder/", {
        params: { path: { id: productId } },
        body: { ids },
      }),
    );
  },
  remove(id: number): Promise<void> {
    return unwrap(
      api.DELETE("/api/v1/admin/catalog/images/{id}/", { params: { path: { id } } }),
    ).then(() => undefined);
  },
};
