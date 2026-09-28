import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type AdminBooking } from "../../api";
import ErrorBanner from "../../components/ErrorBanner";
import StatusPill from "../../components/StatusPill";

const STATUS_OPTIONS = ["", "PENDING", "CONFIRMED", "FAILED", "CANCELLED"];

export default function AdminBookings() {
  const [bookings, setBookings] = useState<AdminBooking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [centreId, setCentreId] = useState("");
  const [user, setUser] = useState("");

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const trimmedCentre = centreId.trim();
      const centreIdParam =
        /^\d+$/.test(trimmedCentre) && Number(trimmedCentre) > 0
          ? Number(trimmedCentre)
          : undefined;
      const data = await api.adminBookings({
        status: status || undefined,
        centre_id: centreIdParam,
        user: user.trim() || undefined,
        limit: 200,
      });
      setBookings(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load bookings");
    } finally {
      setLoading(false);
    }
  }, [status, centreId, user]);

  useEffect(() => {
    void fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <div className="page-head">
        <h1>All bookings</h1>
        <p>Read-only view of every booking across users.</p>
      </div>
      <form
        className="toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          void fetchAll();
        }}
      >
        <label className="field">
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s === "" ? "All" : s}</option>
            ))}
          </select>
        </label>
        <label className="field">
          Centre ID
          <input
            type="text"
            inputMode="numeric"
            placeholder="e.g. 1"
            value={centreId}
            onChange={(e) => setCentreId(e.target.value)}
          />
        </label>
        <label className="field">
          User (email or id)
          <input
            type="search"
            placeholder="user@example.com"
            value={user}
            onChange={(e) => setUser(e.target.value)}
          />
        </label>
        <button type="submit" disabled={loading}>Apply filters</button>
      </form>
      <ErrorBanner message={error} />
      {loading ? (
        <p className="muted">Loading bookings…</p>
      ) : bookings.length === 0 ? (
        <p className="empty-state">No bookings match these filters.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>User email</th>
                <th>Centre</th>
                <th>Test</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Appointment</th>
              </tr>
            </thead>
            <tbody>
              {bookings.map((b) => (
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
