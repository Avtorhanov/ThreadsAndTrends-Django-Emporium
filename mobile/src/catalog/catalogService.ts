import { api, unwrap } from "../api/client";
import type { components } from "../api/schema";

type Schemas = components["schemas"];

export type CategoryNode = Schemas["CatalogCategoryTree"];
export type ProductCard = Schemas["CatalogProduct"];
export type ProductPage = Schemas["PaginatedCatalogProductList"];
export type ProductDetail = Schemas["CatalogProductDetail"];

/** Публичный каталог: авторизация не нужна, токен (если есть) сервер игнорирует. */
export const catalogService = {
  categories(): Promise<CategoryNode[]> {
    return unwrap(api.GET("/api/v1/catalog/categories/"));
  },
  products(params: { category?: string; page: number }): Promise<ProductPage> {
    return unwrap(
      api.GET("/api/v1/catalog/products/", {
        params: { query: { category: params.category, page: params.page } },
      }),
    );
  },
  product(slug: string): Promise<ProductDetail> {
    return unwrap(api.GET("/api/v1/catalog/products/{slug}/", { params: { path: { slug } } }));
  },
};
