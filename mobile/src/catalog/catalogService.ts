import { api, unwrap } from "../api/client";
import type { components } from "../api/schema";

type Schemas = components["schemas"];

export type CategoryNode = Schemas["CatalogCategoryTree"];
export type ProductCard = Schemas["CatalogProduct"];
export type ProductPage = Schemas["PaginatedCatalogProductList"];
export type ProductDetail = Schemas["CatalogProductDetail"];

export type ProductSort = "new" | "price_asc" | "price_desc" | "relevance";

/** Фильтры ленты. Цены — копейки (как в API). */
export type ProductQuery = {
  category?: string;
  q?: string;
  priceMin?: number;
  priceMax?: number;
  inStock?: boolean;
  sort?: ProductSort;
};

/** Публичный каталог: авторизация не нужна, токен (если есть) сервер игнорирует. */
export const catalogService = {
  categories(): Promise<CategoryNode[]> {
    return unwrap(api.GET("/api/v1/catalog/categories/"));
  },
  products(query: ProductQuery & { page: number }): Promise<ProductPage> {
    return unwrap(
      api.GET("/api/v1/catalog/products/", {
        params: {
          query: {
            page: query.page,
            category: query.category || undefined,
            q: query.q?.trim() || undefined,
            price_min: query.priceMin,
            price_max: query.priceMax,
            in_stock: query.inStock || undefined,
            sort: query.sort,
          },
        },
      }),
    );
  },
  product(slug: string): Promise<ProductDetail> {
    return unwrap(api.GET("/api/v1/catalog/products/{slug}/", { params: { path: { slug } } }));
  },
};
