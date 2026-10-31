import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { onUnauthorized } from "../api/client";
import { authService, type StaffUser } from "./authService";
import { STORE_URL } from "../lib/site";

type Status = "loading" | "error" | "signedIn" | "signedOut";

type AuthContextValue = {
  status: Status;
  user: StaffUser | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  retry: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<StaffUser | null>(null);

  const signOut = useCallback(() => {
    setUser(null);
    setStatus("signedOut");
  }, []);

  const bootstrap = useCallback(async () => {
    setStatus("loading");
    try {
      await authService.ensureCsrf();
      const current = await authService.me();
      setUser(current);
      setStatus(current ? "signedIn" : "signedOut");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void bootstrap();
    onUnauthorized(signOut);
    return () => onUnauthorized(null);
  }, [bootstrap, signOut]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      retry: () => void bootstrap(),
      login: async (email, password) => {
        const staff = await authService.login(email, password);
        setUser(staff);
        setStatus("signedIn");
      },
      logout: async () => {
        await authService.logout().catch(() => undefined);
        // Вышел из панели — остаётся в магазине гостем (сессия Django уже закрыта).
        window.location.assign(STORE_URL);
      },
    }),
    [status, user, bootstrap, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth вызывается вне AuthProvider");
  return context;
}
