import { api, unwrap } from "../api/client";
import { ApiError } from "../api/errors";
import type { components } from "../api/schema";

export type StaffUser = components["schemas"]["StaffUser"];

export const authService = {
  /** Cookie csrftoken до первого POST (вход). */
  async ensureCsrf(): Promise<void> {
    await unwrap(api.GET("/api/v1/admin/auth/csrf/"));
  },

  /** Текущий администратор или null, если сессии нет. */
  async me(): Promise<StaffUser | null> {
    try {
      return await unwrap(api.GET("/api/v1/admin/auth/me/"));
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null;
      throw error;
    }
  },

  login(email: string, password: string): Promise<StaffUser> {
    return unwrap(api.POST("/api/v1/admin/auth/login/", { body: { email, password } }));
  },

  async logout(): Promise<void> {
    await unwrap(api.POST("/api/v1/admin/auth/logout/"));
  },
};
