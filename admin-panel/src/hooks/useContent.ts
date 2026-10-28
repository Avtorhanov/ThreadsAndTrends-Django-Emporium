import { type Article, type ArticlePage, type ArticleQuery, articlesService } from "../api/content";
import { type ShopSettings, shopSettingsService } from "../api/settings";
import { useLoader } from "./useCatalog";

export function useArticles(query: ArticleQuery) {
  return useLoader<ArticlePage>(
    () => articlesService.list(query),
    JSON.stringify(query),
    "Не удалось загрузить статьи.",
  );
}

export function useArticle(id: number | null) {
  return useLoader<Article | null>(
    () => (id === null ? Promise.resolve(null) : articlesService.get(id)),
    String(id),
    "Не удалось загрузить статью.",
  );
}

export function useShopSettings() {
  return useLoader<ShopSettings>(() => shopSettingsService.get(), "shop-settings", "Не удалось загрузить настройки.");
}
