import { api, unwrap } from "../api/client";
import type { components } from "../api/schema";
import { session } from "./session";

export type Profile = components["schemas"]["Profile"];
export type RegisterInput = components["schemas"]["RegisterRequest"];
export type LoginInput = components["schemas"]["LoginRequest"];
export type ProfileInput = components["schemas"]["PatchedProfileRequest"];
export type ChangePasswordInput = components["schemas"]["ChangePasswordRequest"];
export type ResetConfirmInput = components["schemas"]["PasswordResetConfirmRequest"];

/** Сценарии аутентификации. UI вызывает только эти функции и не знает о токенах. */
export const authService = {
  async register(input: RegisterInput): Promise<Profile> {
    const result = await unwrap(api.POST("/api/v1/auth/register/", { body: input }));
    await session.setTokens(result);
    return result.user;
  },

  async login(input: LoginInput): Promise<Profile> {
    const result = await unwrap(api.POST("/api/v1/auth/login/", { body: input }));
    await session.setTokens(result);
    return result.user;
  },

  /** Восстановление сессии при запуске: refresh из SecureStore → профиль. */
  async restore(): Promise<Profile | null> {
    if (!(await session.hasStoredSession())) return null;
    const access = await session.refresh();
    if (!access) return null;
    return authService.me();
  },

  me(): Promise<Profile> {
    return unwrap(api.GET("/api/v1/auth/me/"));
  },

  updateProfile(input: ProfileInput): Promise<Profile> {
    return unwrap(api.PATCH("/api/v1/auth/me/", { body: input }));
  },

  async logout(): Promise<void> {
    const refresh = await session.getRefresh();
    // Локальный выход выполняется всегда, даже если сервер недоступен.
    await session.clear();
    if (refresh) {
      await api.POST("/api/v1/auth/logout/", { body: { refresh } }).catch(() => undefined);
    }
  },

  async changePassword(input: ChangePasswordInput): Promise<void> {
    const tokens = await unwrap(api.POST("/api/v1/auth/password/change/", { body: input }));
    await session.setTokens(tokens);
  },

  async deleteAccount(password: string): Promise<void> {
    await unwrap(api.POST("/api/v1/auth/me/delete/", { body: { password } }));
    await session.clear();
  },

  async requestPasswordReset(email: string): Promise<void> {
    await unwrap(api.POST("/api/v1/auth/password/reset/", { body: { email } }));
  },

  async confirmPasswordReset(input: ResetConfirmInput): Promise<Profile> {
    const tokens = await unwrap(api.POST("/api/v1/auth/password/reset/confirm/", { body: input }));
    await session.setTokens(tokens);
    return authService.me();
  },
};
