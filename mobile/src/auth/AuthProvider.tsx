import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  authService,
  type ChangePasswordInput,
  type LoginInput,
  type Profile,
  type ProfileInput,
  type RegisterInput,
  type ResetConfirmInput,
} from "./authService";
import { OfflineError, session } from "./session";

type AuthStatus = "loading" | "offline" | "signedIn" | "signedOut";

type AuthContextValue = {
  status: AuthStatus;
  user: Profile | null;
  retry: () => void;
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => Promise<void>;
  updateProfile: (input: ProfileInput) => Promise<void>;
  changePassword: (input: ChangePasswordInput) => Promise<void>;
  deleteAccount: (password: string) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  confirmPasswordReset: (input: ResetConfirmInput) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<Profile | null>(null);

  const signIn = useCallback((profile: Profile) => {
    setUser(profile);
    setStatus("signedIn");
  }, []);

  const signOut = useCallback(() => {
    setUser(null);
    setStatus("signedOut");
  }, []);

  const restore = useCallback(async () => {
    setStatus("loading");
    try {
      const profile = await authService.restore();
      if (profile) signIn(profile);
      else signOut();
    } catch (error) {
      // Без сети не разлогиниваем: refresh остаётся в SecureStore, показываем повтор.
      if (error instanceof OfflineError) setStatus("offline");
      else signOut();
    }
  }, [signIn, signOut]);

  useEffect(() => {
    void restore();
    return session.onExpired(signOut);
  }, [restore, signOut]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      retry: () => void restore(),
      login: async (input) => signIn(await authService.login(input)),
      register: async (input) => signIn(await authService.register(input)),
      logout: async () => {
        await authService.logout();
        signOut();
      },
      updateProfile: async (input) => setUser(await authService.updateProfile(input)),
      changePassword: (input) => authService.changePassword(input),
      deleteAccount: async (password) => {
        await authService.deleteAccount(password);
        signOut();
      },
      requestPasswordReset: (email) => authService.requestPasswordReset(email),
      confirmPasswordReset: async (input) => signIn(await authService.confirmPasswordReset(input)),
    }),
    [status, user, restore, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth вызывается вне AuthProvider");
  return context;
}
