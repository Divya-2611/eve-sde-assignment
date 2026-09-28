import { Link } from "react-router-dom";

export default function Forbidden() {
  return (
    <section className="card">
      <h1>403 — Admin access required</h1>
      <p className="muted">
        You are signed in but do not have admin privileges. Contact an
        administrator if you need access.
      </p>
      <div className="card-actions">
        <Link className="btn btn-ghost" to="/">
          Back to centres
        </Link>
        <Link className="btn btn-ghost" to="/login">
          Switch account
        </Link>
      </div>
    </section>
  );
}
