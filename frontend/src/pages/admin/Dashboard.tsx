import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type AdminBooking, type AdminBookingStats } from "../../api";
import ErrorBanner from "../../components/ErrorBanner";
import StatusPill from "../../components/StatusPill";

const STATUSES = ["PENDING", "CONFIRMED", "FAILED", "CANCELLED"] as const;

export default function Dashboard() {
  const [stats, setStats] = useState<AdminBookingStats | null>(null);
  const [recent, setRecent] = useState<AdminBooking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [s, r] = await Promise.all([
          api.adminBookingStats(),
          api.adminBookings({ order: "desc", limit: 10 }),
        ]);
        if (!cancelled) {
          setStats(s);
          setRecent(r);
        }
      } catch (err) {
        if (!cancelled)
          setError(err instanceof ApiError ? err.message : "Failed to load dashboard");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const counts = stats?.counts ?? {};
  const confirmedSum = stats?.confirmed_sum ?? 0;

  if (loading) {
    return (
      <section className="card">
        <h1>Admin dashboard</h1>
        <p className="muted">Loading…</p>
      </section>
    );
  }

  return (
    <>
      <div className="page-head">
        <h1>Admin dashboard</h1>
        <p>Booking status overview and recent activity (read-only).</p>
        <div className="toolbar">
          <Link className="btn btn-ghost" to="/admin/bookings">All bookings</Link>
          <Link className="btn btn-ghost" to="/admin/catalogue">Catalogue</Link>
        </div>
      </div>
      <ErrorBanner message={error} />
      <div className="stat-cards">
        {STATUSES.map((s) => (
          <div key={s} className="card stat-card">
            <span className="stat-label">{s}</span>
            <strong className="stat-value">{counts[s] ?? 0}</strong>
          </div>
        ))}
        <div className="card stat-card">
          <span className="stat-label">CONFIRMED revenue</span>
          <strong className="stat-value">₹{Number(confirmedSum).toFixed(2)}</strong>
        </div>
      </div>
      <h2>Recent bookings (10)</h2>
      {recent.length === 0 ? (
        <p className="empty-state">No bookings yet.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>User</th>
                <th>Centre</th>
                <th>Test</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Appointment</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((b) => (
                <tr key={b.id}>
                  <td>{b.id}</td>
                  <td>{b.user_email}</td>
                  <td>{b.centre_name}</td>
                  <td>{b.test_name}</td>
                  <td>₹{Number(b.amount).toFixed(2)}</td>
                  <td><StatusPill status={b.status} /></td>
                  <td>{String(b.appointment_datetime)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
