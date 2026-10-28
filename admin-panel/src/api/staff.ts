import { api, unwrap } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

export type StaffMember = Schemas["StaffMember"];
export type StaffPermissions = Schemas["StaffPermissionsInputRequest"];
export type AccessLevel = Schemas["StaffLevelEnum"];
export type StaffSection = keyof StaffPermissions;

/** Разделы, которые владелец открывает сотруднику (как accounts.staff.SECTIONS). */
export const STAFF_SECTIONS: { key: StaffSection; label: string }[] = [
  { key: "summary", label: "Сводка и выручка" },
  { key: "orders", label: "Заказы" },
  { key: "products", label: "Товары и статусы" },
  { key: "categories", label: "Категории" },
  { key: "articles", label: "Статьи" },
  { key: "storefront", label: "Главная и тема" },
  { key: "customers", label: "Клиенты" },
];

export const LEVEL_LABELS: Record<AccessLevel, string> = { none: "Нет", view: "Смотреть", edit: "Менять" };

const all = (level: AccessLevel): StaffPermissions =>
  Object.fromEntries(STAFF_SECTIONS.map((item) => [item.key, level])) as StaffPermissions;

/** Шаблоны прав (как accounts.staff.PRESETS). */
export const PRESETS: { key: string; label: string; permissions: StaffPermissions }[] = [
  {
    key: "orders_manager",
    label: "Менеджер заказов",
    permissions: { ...all("none"), summary: "view", orders: "edit", products: "view", customers: "view" },
  },
  {
    key: "content",
    label: "Контент и витрина",
    permissions: { ...all("none"), products: "view", categories: "view", articles: "edit", storefront: "edit" },
  },
  { key: "all", label: "Всё, кроме владельца", permissions: all("edit") },
];

export function sectionsOf(member: Pick<StaffMember, "permissions">): StaffPermissions {
  return Object.fromEntries(
    STAFF_SECTIONS.map((item) => [item.key, member.permissions[item.key]]),
  ) as StaffPermissions;
}

export const staffService = {
  list(): Promise<StaffMember[]> {
    return unwrap(api.GET("/api/v1/admin/staff/"));
  },
  invite(body: { email: string; first_name: string; permissions: StaffPermissions }): Promise<StaffMember> {
    return unwrap(api.POST("/api/v1/admin/staff/", { body }));
  },
  update(
    id: number,
    body: { first_name?: string; is_active?: boolean; permissions?: StaffPermissions },
  ): Promise<StaffMember> {
    return unwrap(api.PATCH("/api/v1/admin/staff/{id}/", { params: { path: { id } }, body }));
  },
  resend(id: number): Promise<void> {
    return unwrap(api.POST("/api/v1/admin/staff/{id}/resend/", { params: { path: { id } } })).then(
      () => undefined,
    );
  },
};
