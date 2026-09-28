import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api, type Booking } from "../api";
import ErrorBanner from "../components/ErrorBanner";
import StatusPill from "../components/StatusPill";

export default function Checkout() {
  const { bookingId } = useParams<{ bookingId: string }>();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.getBooking(bookingId ?? "");
        if (!cancelled) setBooking(data);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof ApiError ? err.message : "Failed to load booking");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [bookingId]);

  async function onPay(e: FormEvent) {
    e.preventDefault();
    if (paying) return;
    setPaying(true);
    setError(null);
    try {
      // Mock provider: ~2s processing, then 70/30 SUCCESS/FAILED.
      const res = await api.mockCharge(bookingId ?? "");
      setResult(res.booking_status);
      setBooking((prev) =>
        prev ? { ...prev, status: res.booking_status } : prev,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Payment failed");
    } finally {
      setPaying(false);
    }
  }

  if (loading) {
    return (
      <section className="card">
        <h1>Checkout</h1>
        <p className="muted">Loading booking…</p>
      </section>
    );
  }

  if (!booking) {
    return (
      <section className="card">
        <h1>Checkout</h1>
        <ErrorBanner message={error ?? "Booking not found"} />
      </section>
    );
  }

  return (
    <>
      <div className="page-head">
        <h1>Checkout — Booking #{booking.id}</h1>
        <p>Simulated payment. Pick an outcome to test both paths.</p>
      </div>
      <section className="card">
        <div className="kv">
          <span className="muted">Amount due</span>
          <span className="amount">₹{Number(booking.amount).toFixed(2)}</span>
        </div>
        <div className="kv">
          <span className="muted">Status</span>
          <StatusPill status={booking.status} />
        </div>
        <div className="kv">
          <span className="muted">Appointment</span>
          <span>{booking.appointment_datetime}</span>
        </div>
      </section>
      <section className="card">
        <ErrorBanner message={error} />
        {result ? (
          <div>
            <p>
              Payment result: <StatusPill status={result} />
            </p>
            <Link className="btn btn-ghost" to="/bookings">
              Back to bookings
            </Link>
          </div>
        ) : (
          <form onSubmit={onPay}>
            <div>
              <button type="submit" disabled={paying}>
                {paying
                  ? "Processing payment…"
                  : `Proceed to Payment ₹${Number(booking.amount).toFixed(2)}`}
              </button>
            </div>
          </form>
        )}
      </section>
    </>
  );
}
