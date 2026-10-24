import { api, unwrap } from "./client";
import type { components } from "./schema";

export type AdminSummary = components["schemas"]["AdminSummary"];

export const summaryService = {
  get(): Promise<AdminSummary> {
    return unwrap(api.GET("/api/v1/admin/summary/"));
  },
};
