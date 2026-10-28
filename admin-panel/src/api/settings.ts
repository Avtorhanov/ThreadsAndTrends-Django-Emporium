import { api, unwrap } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

export type ShopSettings = Schemas["AdminShopSettings"];
export type ShopSettingsInput = Schemas["AdminShopSettingsWriteRequest"];

const URL = "/api/v1/admin/content/settings/" as const;

export const shopSettingsService = {
  get(): Promise<ShopSettings> {
    return unwrap(api.GET(URL));
  },
  save(body: ShopSettingsInput): Promise<ShopSettings> {
    return unwrap(api.PUT(URL, { body }));
  },
};

export type SellerPart = { text: string; href?: string };

/** Как content.shop.clean_text на сервере: лишние пробелы и хвостовые «,;:·» убираются. */
export function cleanText(value: string): string {
  return value.split(/\s+/).filter(Boolean).join(" ").replace(/[\s,;:·]+$/, "");
}

/** Строка реквизитов в подвале сайта (как content.shop.Seller.parts): пустые не показываются. */
export function sellerParts(values: {
  name: string;
  inn: string;
  ogrn: string;
  address: string;
  phone: string;
  email: string;
}): SellerPart[] {
  const name = cleanText(values.name);
  const inn = values.inn.replace(/\D/g, "");
  const ogrn = values.ogrn.replace(/\D/g, "");
  const address = cleanText(values.address);
  const phone = cleanText(values.phone);
  const email = values.email.trim().toLowerCase();
  const parts: SellerPart[] = [];
  if (name) parts.push({ text: name });
  if (inn) parts.push({ text: `ИНН ${inn}` });
  if (ogrn) parts.push({ text: `${ogrn.length === 13 ? "ОГРН" : "ОГРНИП"} ${ogrn}` });
  if (address) parts.push({ text: address });
  if (phone) parts.push({ text: phone, href: `tel:${phone.replace(/[^\d+]/g, "")}` });
  if (email) parts.push({ text: email, href: `mailto:${email}` });
  return parts;
}
