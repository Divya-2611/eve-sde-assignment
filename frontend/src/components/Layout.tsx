import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";

function AuthState() {
  const { token, user_email, logout } = useAuth();
  if (!token) return null;
  return (
    <span>
      {user_email ?? "Signed in"}{" "}
      <button type="button" onClick={logout}>
        Log out
      </button>
    </span>
  );
}

export default function Layout() {
  const { token, is_admin } = useAuth();
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="brand">
          EVE Healthcare
        </Link>
        <nav className="nav">
          <NavLink to="/">Centres</NavLink>
          <NavLink to="/bookings">Bookings</NavLink>
          {is_admin && <NavLink to="/admin">Admin</NavLink>}
          {!token && <NavLink to="/login">Login</NavLink>}
          {!token && <NavLink to="/signup">Sign up</NavLink>}
        </nav>
        <div className="auth-slot" data-testid="auth-state">
          <AuthState />
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
