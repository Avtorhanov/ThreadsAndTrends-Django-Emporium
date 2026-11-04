import { api, unwrap } from "../api/client";
import { ApiError } from "../api/errors";
import type { components } from "../api/schema";

export type StaffUser = components["schemas"]["StaffUser"];
export type EmailPending = components["schemas"]["EmailChangePending"];

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

  /** Смена своего пароля: эта сессия остаётся, другие браузеры и приложение выходят. */
  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await unwrap(
      api.POST("/api/v1/admin/auth/password/change/", {
        body: { old_password: oldPassword, new_password: newPassword },
      }),
    );
  },

  /** Своё имя и фамилия. */
  updateProfile(firstName: string, lastName: string): Promise<StaffUser> {
    return unwrap(
      api.PATCH("/api/v1/admin/auth/me/", { body: { first_name: firstName, last_name: lastName } }),
    );
  },

  /** Действующий запрос смены email или null. */
  async pendingEmail(): Promise<EmailPending | null> {
    const { data, response } = await api.GET("/api/v1/admin/auth/email/change/");
    if (response.status === 204 || !data) return null;
    return data;
  },

  /** Смена email, шаг 1: пароль + новый адрес → код на новый адрес. */
  requestEmailChange(newEmail: string, password: string): Promise<EmailPending> {
    return unwrap(
      api.POST("/api/v1/admin/auth/email/change/", { body: { new_email: newEmail, password } }),
    );
  },

  /** Смена email, шаг 2: код из письма. Сессия панели остаётся. */
  confirmEmailChange(code: string): Promise<StaffUser> {
    return unwrap(api.POST("/api/v1/admin/auth/email/change/confirm/", { body: { code } }));
  },

  async cancelEmailChange(): Promise<void> {
    await unwrap(api.DELETE("/api/v1/admin/auth/email/change/"));
  },

  async logout(): Promise<void> {
    await unwrap(api.POST("/api/v1/admin/auth/logout/"));
  },
};
