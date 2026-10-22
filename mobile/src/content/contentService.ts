import { api, unwrap } from "../api/client";
import type { components } from "../api/schema";
import { API_URL } from "../config";

type Schemas = components["schemas"];

export type Article = Schemas["Article"];
export type ArticleDetail = Schemas["ArticleDetail"];
export type Contact = Schemas["Contact"];
export type ContactKind = Schemas["ContactKindEnum"];

/** Статьи и контакты магазина — публичные, без входа. */
export const contentService = {
  articles(): Promise<Article[]> {
    return unwrap(api.GET("/api/v1/content/articles/"));
  },
  article(slug: string): Promise<ArticleDetail> {
    return unwrap(api.GET("/api/v1/content/articles/{slug}/", { params: { path: { slug } } }));
  },
  contacts(): Promise<Contact[]> {
    return unwrap(api.GET("/api/v1/content/contacts/"));
  },
};

/** Страницы сайта магазина (оферта, политика, доставка) — тот же адрес, что у API. */
export const SITE_PAGES = {
  delivery: `${API_URL}/legal/delivery/`,
  offer: `${API_URL}/legal/offer/`,
  privacy: `${API_URL}/legal/privacy/`,
};
