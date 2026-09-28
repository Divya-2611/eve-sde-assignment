import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type Booking } from "../api";
import ConfirmDialog from "../components/ConfirmDialog";
import ErrorBanner from "../components/ErrorBanner";
import StatusPill from "../components/StatusPill";

const PAYABLE = new Set(["PENDING", "FAILED"]);
const ACTIVE = new Set(["PENDING", "FAILED", "CONFIRMED"]);

/** `datetime-local` value format: YYYY-MM-DDTHH:MM (local time). */
function toLocalInputValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

export default function Bookings() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [reschedulingId, setReschedulingId] = useState<number | null>(null);
  const [newWhen, setNewWhen] = useState("");
  const [savingId, setSavingId] = useState<number | null>(null);
  const [confirmCancel, setConfirmCancel] = useState<Booking | null>(null);
  const [confirmReschedule, setConfirmReschedule] = useState<Booking | null>(null);

  const fetchBookings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.myBookings();
      setBookings(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load bookings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.myBookings();
        if (!cancelled) setBookings(data);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof ApiError ? err.message : "Failed to load bookings");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function onCancel(id: number) {
    setPendingId(id);
    setError(null);
    try {
      await api.cancelBooking(id);
      setConfirmCancel(null);
      await fetchBookings();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Cancel failed");
    } finally {
      setPendingId(null);
    }
  }

  async function onReschedule(id: number) {
    setSavingId(id);
    setError(null);
    try {
      await api.rescheduleBooking(id, new Date(newWhen).toISOString());
      setReschedulingId(null);
      setConfirmReschedule(null);
      setNewWhen("");
      await fetchBookings();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reschedule failed");
    } finally {
      setSavingId(null);
    }
  }

  function askReschedule(booking: Booking) {
    if (!newWhen) {
      setError("Choose a new date and time");
      return;
    }
    // datetime-local has no zone; interpret as local time → ISO for backend.
    if (new Date(newWhen).getTime() <= Date.now()) {
      setError("Appointment must be in the future");
      return;
    }
    setConfirmReschedule(booking);
  }

  if (loading) {
    return (
      <section className="card">
        <h1>My bookings</h1>
        <p className="muted">Loading bookings…</p>
      </section>
    );
  }

  return (
    <>
      <div className="page-head">
        <h1>My bookings</h1>
        <p>Track, pay for, or cancel your diagnostic appointments.</p>
      </div>
      <ErrorBanner message={error} />
      {bookings.length === 0 ? (
        <p className="empty-state">
          No bookings yet. <Link to="/">Find a centre</Link> to get started.
        </p>
      ) : (
        <ul className="card-grid">
          {bookings.map((b) => (
            <li key={b.id} className="card">
              <h3>Booking #{b.id}</h3>
              <StatusPill status={b.status} />
              <div>
                <div className="kv">
                  <span className="muted">Amount</span>
                  <strong>₹{Number(b.amount).toFixed(2)}</strong>
                </div>
                <div className="kv">
                  <span className="muted">Appointment</span>
                  <span>{b.appointment_datetime}</span>
                </div>
              </div>
              <div className="card-actions">
                {PAYABLE.has(b.status.toUpperCase()) && (
                  <Link className="btn btn-primary" to={`/checkout/${b.id}`}>
                    Pay
                  </Link>
                )}
                {ACTIVE.has(b.status.toUpperCase()) && (
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={() => setConfirmCancel(b)}
                    disabled={pendingId === b.id}
                  >
                    {pendingId === b.id ? "Cancelling…" : "Cancel"}
                  </button>
                )}
                {ACTIVE.has(b.status.toUpperCase()) && (
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => {
                      setReschedulingId(reschedulingId === b.id ? null : b.id);
                      setNewWhen("");
                    }}
                  >
                    Reschedule
                  </button>
                )}
              </div>
              {reschedulingId === b.id && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    askReschedule(b);
                  }}
                >
                  <label className="field">
                    New date &amp; time
                    <input
                      type="datetime-local"
                      value={newWhen}
                      min={toLocalInputValue(new Date())}
                      onChange={(e) => setNewWhen(e.target.value)}
                    />
                  </label>
                  <div className="card-actions">
                    <button type="submit" disabled={savingId === b.id}>
                      {savingId === b.id ? "Saving…" : "Save new date"}
                    </button>
                  </div>
                </form>
              )}
            </li>
          ))}
        </ul>
      )}
      {confirmCancel && (
        <ConfirmDialog
          title={`Cancel booking #${confirmCancel.id}?`}
          message={
            confirmCancel.status.toUpperCase() === "CONFIRMED"
              ? `Amount ₹${Number(confirmCancel.amount).toFixed(2)} will be refunded to your original payment method within 5–7 business days.`
              : "This will cancel your appointment. This action cannot be undone."
          }
          confirmLabel="Yes, cancel it"
          pending={pendingId === confirmCancel.id}
          onBack={() => setConfirmCancel(null)}
          onConfirm={() => onCancel(confirmCancel.id)}
        />
      )}
      {confirmReschedule && (
        <ConfirmDialog
          title={`Reschedule booking #${confirmReschedule.id}?`}
          message={`Move your appointment to ${new Date(newWhen).toLocaleString()}? Your payment and booking status stay unchanged.`}
          confirmLabel="Yes, reschedule"
          pending={savingId === confirmReschedule.id}
          onBack={() => setConfirmReschedule(null)}
          onConfirm={() => onReschedule(confirmReschedule.id)}
        />
      )}
    </>
  );
}
