import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api";
import { useAuth } from "../auth";
import ErrorBanner from "../components/ErrorBanner";

/** Return target after login: `?next=` query param (set by ProtectedRoute). */
function nextPath(searchParams: URLSearchParams, state: unknown): string {
  const next = searchParams.get("next");
  if (next && next.startsWith("/") && !next.startsWith("//")) return next;
  const from = (state as { from?: string } | null)?.from;
  if (typeof from === "string" && from.startsWith("/") && !from.startsWith("//"))
    return from;
  return "/";
}

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const from = nextPath(searchParams, location.state);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="card form-card">
      <div className="page-head">
        <h1>Login</h1>
        <p>Welcome back. Sign in to manage your bookings.</p>
      </div>
      <ErrorBanner message={error} />
      <form onSubmit={onSubmit}>
        <label className="field">
          Email
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="field">
          Password
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button type="submit" disabled={pending}>
          {pending ? "Logging in…" : "Log in"}
        </button>
      </form>
      <p className="muted">
        No account? <Link to="/signup">Sign up</Link>
      </p>
    </section>
  );
}
