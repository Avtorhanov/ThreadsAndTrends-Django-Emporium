/** Адрес витрины: панель живёт в /panel/ (на превью GitHub Pages — /<репозиторий>/panel/). */
export const STORE_URL = import.meta.env.BASE_URL.replace(/panel\/?$/, "");

/** Ссылка на страницу витрины: storeUrl("product/slug/") → "/product/slug/" (на превью — с путём). */
export function storeUrl(path: string): string {
  return STORE_URL + path.replace(/^\/+/, "");
}
