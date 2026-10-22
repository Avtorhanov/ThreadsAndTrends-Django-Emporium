import { api, unwrap } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

export type ArticleRow = Schemas["AdminArticle"];
export type ArticlePage = Schemas["PaginatedAdminArticleList"];
export type Article = Schemas["AdminArticleDetail"];
export type ArticleInput = Schemas["AdminArticleWriteRequest"];
export type ArticlePatch = Schemas["PatchedAdminArticleWriteRequest"];
export type ArticleImage = Schemas["AdminArticleImage"];

export type ArticleStatus = "published" | "draft" | "deleted";

export type ArticleQuery = { search: string; status: ArticleStatus | ""; page: number };

export const ARTICLES_PAGE_SIZE = 20;
export const MAX_ARTICLE_IMAGES = 6;

const ARTICLE = "/api/v1/admin/content/articles/{id}/" as const;

export const articlesService = {
  list({ search, status, page }: ArticleQuery): Promise<ArticlePage> {
    return unwrap(
      api.GET("/api/v1/admin/content/articles/", {
        params: { query: { search: search || undefined, status: status || undefined, page } },
      }),
    );
  },
  get(id: number): Promise<Article> {
    return unwrap(api.GET(ARTICLE, { params: { path: { id } } }));
  },
  create(body: ArticleInput): Promise<Article> {
    return unwrap(api.POST("/api/v1/admin/content/articles/", { body }));
  },
  update(id: number, body: ArticlePatch): Promise<Article> {
    return unwrap(api.PATCH(ARTICLE, { params: { path: { id } }, body }));
  },
  remove(id: number): Promise<void> {
    return unwrap(api.DELETE(ARTICLE, { params: { path: { id } } })).then(() => undefined);
  },
  restore(id: number): Promise<Article> {
    return unwrap(
      api.POST("/api/v1/admin/content/articles/{id}/restore/", { params: { path: { id } } }),
    );
  },
};

export const articleImagesService = {
  upload(articleId: number, file: File): Promise<ArticleImage> {
    return unwrap(
      api.POST("/api/v1/admin/content/articles/{id}/images/", {
        params: { path: { id: articleId } },
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
  reorder(articleId: number, ids: number[]): Promise<ArticleImage[]> {
    return unwrap(
      api.POST("/api/v1/admin/content/articles/{id}/images/reorder/", {
        params: { path: { id: articleId } },
        body: { ids },
      }),
    );
  },
  remove(id: number): Promise<void> {
    return unwrap(
      api.DELETE("/api/v1/admin/content/article-images/{id}/", { params: { path: { id } } }),
    ).then(() => undefined);
  },
};
