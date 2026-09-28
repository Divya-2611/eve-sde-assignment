import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Navigate, useLocation } from "react-router-dom";
import { TOKEN_KEY, UNAUTHORIZED_EVENT, api } from "./api";
import Forbidden from "./pages/admin/Forbidden";

const EMAIL_KEY = "eve_email";

/** Best-effort decode of the JWT payload (no verification — display only). */
export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const [, payload] = token.split(".");
    if (!payload) return null;
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
    return JSON.parse(atob(padded)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/** Admin flag from JWT `is_admin` claim (set at login; display/guard only). */
export function isAdminFor(token: string | null): boolean {
  if (!token) return false;
  const payload = decodeJwtPayload(token);
  return payload?.is_admin === true;
}
/** Display identity: stored email if known, else JWT `email`/`sub` claim. */
function identityFor(token: string | null, storedEmail: string | null): string | null {
  if (storedEmail) return storedEmail;
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  if (!payload) return null;
  const email = payload.email;
  if (typeof email === "string" && email) return email;
  const sub = payload.sub;
  if (typeof sub === "string" && sub) return sub;
  return null;
}

interface AuthContextValue {
  token: string | null;
  user_email: string | null;
  is_admin: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStored(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => readStored(TOKEN_KEY));
  const [storedEmail, setStoredEmail] = useState<string | null>(() =>
    readStored(EMAIL_KEY),
  );

  const persist = useCallback((nextToken: string | null, email: string | null) => {
    setToken(nextToken);
    setStoredEmail(email);
    try {
      if (nextToken) localStorage.setItem(TOKEN_KEY, nextToken);
      else localStorage.removeItem(TOKEN_KEY);
      if (email) localStorage.setItem(EMAIL_KEY, email);
      else localStorage.removeItem(EMAIL_KEY);
    } catch {
      // storage unavailable (private mode) — session still works in memory
    }
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login(email, password);
      persist(res.access_token, email.trim().toLowerCase());
    },
    [persist],
  );

  const signup = useCallback(
    async (name: string, email: string, password: string) => {
      await api.signup(name, email, password);
    },
    [],
  );

  const logout = useCallback(() => persist(null, null), [persist]);

  // A 401 in api.request() clears storage; also reset in-memory state here
  // so the UI reflects logged-out immediately (no reload required).
  useEffect(() => {
    const onUnauthorized = () => persist(null, null);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, [persist]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user_email: identityFor(token, storedEmail),
      is_admin: isAdminFor(token),
      login,
      signup,
      logout,
    }),
    [token, storedEmail, login, signup, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const location = useLocation();
  if (!token) {
    return (
      <Navigate
        to={`/login?next=${encodeURIComponent(location.pathname)}`}
        replace
      />
    );
  }
  return <>{children}</>;
}

export function AdminRoute({ children }: { children: ReactNode }) {
  const { token, is_admin } = useAuth();
  const location = useLocation();
  if (!token) {
    return (
      <Navigate
        to={`/login?next=${encodeURIComponent(location.pathname)}`}
        replace
      />
    );
  }
  if (!is_admin) return <Forbidden />;
  return <>{children}</>;
}
