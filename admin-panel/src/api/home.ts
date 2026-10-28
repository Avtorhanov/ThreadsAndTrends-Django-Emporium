import { api, unwrap } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

export type HomeState = Schemas["AdminHome"];
export type HomeBlock = Schemas["AdminHomeBlock"];
export type HomeBlockKind = Schemas["HomeBlockKindEnum"];
export type CollectionSource = Schemas["CollectionSourceEnum"];
export type HomeBlockChanges = Schemas["PatchedAdminHomeBlockUpdateRequest"];
export type HomeLinkInput = Schemas["AdminHomeLinkRequest"];
export type HomeLinkKind = Schemas["HomeLinkKindEnum"];
export type HomeLinkPage = Schemas["HomeLinkPageEnum"];

/** Лимиты — как content.home на сервере. */
export const HOME_LIMITS = {
  title: 60,
  bannerText: 120,
  text: 1000,
  manualProducts: 12,
  bannerImages: 6,
  links: 12,
  linkTitle: 40,
} as const;

/** Вкладки ленты категорий (content.home.LINK_KIND_CHOICES / LINK_PAGES). */
export const LINK_KIND_LABELS: Record<HomeLinkKind, string> = {
  category: "Категория",
  article: "Статья",
  page: "Страница",
  url: "Ссылка",
};

export const LINK_PAGES: Record<HomeLinkPage, string> = {
  products: "Все товары",
  contacts: "Контакты",
  delivery: "Доставка и оплата",
};

/** Сохранённые вкладки блока (в схеме — свободные объекты). */
export function blockLinks(block: HomeBlock): HomeLinkInput[] {
  return block.links as unknown as HomeLinkInput[];
}

/** Готовые тона баннера; свой цвет — любой (input type=color). */
export const BANNER_TONES: { label: string; color: string }[] = [
  { label: "Лайм", color: "#DDF38A" },
  { label: "Солнце", color: "#FFE38F" },
  { label: "Мята", color: "#C4EBD3" },
  { label: "Абрикос", color: "#FFD6B0" },
  { label: "Сталь", color: "#7FA7CF" },
  { label: "Тёмный", color: "#13261C" },
];

export const BLOCK_TYPES: { kind: HomeBlockKind; label: string; hint: string }[] = [
  { kind: "banner", label: "Баннер", hint: "Фото товара или свои картинки (и GIF), заголовок на фото" },
  { kind: "collection", label: "Подборка товаров", hint: "Ряд товаров: новинки, категория или вручную" },
  { kind: "categories", label: "Лента категорий", hint: "Категории, статьи, страницы и ссылки" },
  { kind: "text", label: "Текст", hint: "Заголовок и пара абзацев" },
];

export const KIND_LABELS: Record<HomeBlockKind, string> = {
  banner: "Баннер",
  collection: "Подборка",
  categories: "Категории",
  text: "Текст",
};

export const SOURCE_LABELS: Record<CollectionSource, string> = {
  new: "Новинки",
  category: "Категория",
  manual: "Вручную",
};

/** Цвет текста на фоне баннера — как content.home.ink_for (яркость по WCAG). */
export function inkFor(color: string): string {
  if (!/^#[0-9a-f]{6}$/i.test(color)) return "#13261C";
  const channel = (index: number) => {
    const value = parseInt(color.slice(index, index + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  };
  const luminance = 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
  return luminance > 0.18 ? "#13261C" : "#FFFFFF";
}

const BASE = "/api/v1/admin/content/home/" as const;

export const homeService = {
  get(): Promise<HomeState> {
    return unwrap(api.GET(BASE));
  },
  add(kind: HomeBlockKind): Promise<HomeBlock> {
    return unwrap(api.POST("/api/v1/admin/content/home/blocks/", { body: { kind } }));
  },
  update(id: number, body: HomeBlockChanges): Promise<HomeBlock> {
    return unwrap(api.PATCH("/api/v1/admin/content/home/blocks/{id}/", { params: { path: { id } }, body }));
  },
  remove(id: number): Promise<void> {
    return unwrap(api.DELETE("/api/v1/admin/content/home/blocks/{id}/", { params: { path: { id } } })).then(
      () => undefined,
    );
  },
  uploadImage(id: number, file: File): Promise<HomeBlock> {
    return unwrap(
      api.POST("/api/v1/admin/content/home/blocks/{id}/image/", {
        params: { path: { id } },
        body: { image: file.name },
        bodySerializer: () => {
          const form = new FormData();
          form.append("image", file);
          return form;
        },
      }),
    );
  },
  reorder(ids: number[]): Promise<HomeState> {
    return unwrap(api.POST("/api/v1/admin/content/home/reorder/", { body: { ids } }));
  },
  publish(): Promise<HomeState> {
    return unwrap(api.POST("/api/v1/admin/content/home/publish/"));
  },
};
