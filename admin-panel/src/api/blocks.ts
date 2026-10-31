import { api, unwrap } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

export type SiteBlock = Schemas["AdminBlock"];
export type BlockKind = Schemas["BlockKindEnum"];
export type BlockArea = Schemas["BlockAreaEnum"];

const URL = "/api/v1/admin/content/blocks/" as const;

/**
 * Блоки разделов сайта («Контакты», «Помощь», подвал) — те же, что правятся на сайте
 * двойным нажатием. Пока раздел не меняли, сервер отдаёт значения по умолчанию (.env)
 * без id; первое изменение переносит их в БД (`customize`).
 */
export const blocksService = {
  list(area: BlockArea): Promise<SiteBlock[]> {
    return unwrap(api.GET(URL, { params: { query: { area } } }));
  },
  customize(area: BlockArea): Promise<SiteBlock[]> {
    return unwrap(api.POST("/api/v1/admin/content/blocks/customize/", { body: { area } }));
  },
  create(body: { area: BlockArea; kind: BlockKind; title: string; value: string; note: string }): Promise<SiteBlock> {
    return unwrap(api.POST(URL, { body: { ...body, icon: "" } }));
  },
  update(id: number, body: { kind?: BlockKind; title?: string; value?: string; note?: string }): Promise<SiteBlock> {
    return unwrap(api.PATCH("/api/v1/admin/content/blocks/{id}/", { params: { path: { id } }, body }));
  },
  remove(id: number): Promise<unknown> {
    return unwrap(api.DELETE("/api/v1/admin/content/blocks/{id}/", { params: { path: { id } } }));
  },
  reorder(area: BlockArea, ids: number[]): Promise<SiteBlock[]> {
    return unwrap(api.POST("/api/v1/admin/content/blocks/reorder/", { body: { area, ids } }));
  },
};
