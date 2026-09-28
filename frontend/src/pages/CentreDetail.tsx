import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError, api, type CentreDetail } from "../api";
import { useAuth } from "../auth";
import ErrorBanner from "../components/ErrorBanner";

/** `datetime-local` value format: YYYY-MM-DDTHH:MM (local time). */
function toLocalInputValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

export default function CentreDetail() {
  const { id } = useParams<{ id: string }>();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [centre, setCentre] = useState<CentreDetail | null>(null);
  const [testId, setTestId] = useState<number | null>(null);
  const [when, setWhen] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bookingError, setBookingError] = useState<string | null>(null);
  const [booking, setBooking] = useState(false);

  const min = useMemo(() => toLocalInputValue(new Date()), []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.centreDetail(id ?? "");
        if (!cancelled) {
          setCentre(data);
          setTestId(data.tests[0]?.id ?? null);
        }
      } catch (err) {
        if (!cancelled)
          setError(err instanceof ApiError ? err.message : "Failed to load centre");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function onBook(e: FormEvent) {
    e.preventDefault();
    setBookingError(null);
    if (!token) {
      navigate(`/login?next=${encodeURIComponent(`/centres/${id}`)}`);
      return;
    }
    if (testId === null) {
      setBookingError("Select a test to book");
      return;
    }
    if (!when) {
      setBookingError("Choose a date and time");
      return;
    }
    if (new Date(when).getTime() <= Date.now()) {
      setBookingError("Appointment must be in the future");
      return;
    }
    setBooking(true);
    try {
      // datetime-local has no zone; interpret as local time → ISO for backend.
      const iso = new Date(when).toISOString();
      const created = await api.createBooking(Number(id), testId, iso);
      navigate(`/checkout/${created.id}`);
    } catch (err) {
      setBookingError(err instanceof ApiError ? err.message : "Booking failed");
    } finally {
      setBooking(false);
    }
  }

  if (loading) {
    return (
      <section className="card">
        <p className="muted">Loading centre…</p>
      </section>
    );
  }

  if (!centre) {
    return (
      <section className="card">
        <h1>Centre not found</h1>
        <ErrorBanner message={error} />
      </section>
    );
  }

  return (
    <>
      <div className="page-head">
        <h1>{centre.name}</h1>
        <p>{centre.location}</p>
      </div>
      <ErrorBanner message={error} />
      <section className="card">
        <h2>Tests &amp; prices</h2>
      {centre.tests.length === 0 ? (
        <p className="muted">No tests available at this centre.</p>
      ) : (
        <form onSubmit={onBook}>
          <div className="radio-group" role="radiogroup" aria-label="Tests">
            {centre.tests.map((t) => (
              <label key={t.id} className="radio-card">
                <input
                  type="radio"
                  name="test"
                  checked={testId === t.id}
                  onChange={() => setTestId(t.id)}
                />
                <span>{t.name}</span>
                <span className="price">₹{Number(t.price).toFixed(2)}</span>
              </label>
            ))}
          </div>
          <label className="field">
            Appointment date &amp; time
            <input
              type="datetime-local"
              value={when}
              min={min}
              onChange={(e) => setWhen(e.target.value)}
            />
          </label>
          <ErrorBanner message={bookingError} />
          <button type="submit" disabled={booking}>
            {booking ? "Booking…" : token ? "Book" : "Book (login required)"}
          </button>
        </form>
      )}
    </section>
    </>
  );
}
