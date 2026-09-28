import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type Centre } from "../api";
import ErrorBanner from "../components/ErrorBanner";

export default function Centres() {
  const [centres, setCentres] = useState<Centre[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.listCentres();
        if (!cancelled) setCentres(data);
      } catch (err) {
        if (!cancelled)
          setError(err instanceof ApiError ? err.message : "Failed to load centres");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return centres;
    return centres.filter(
      (c) =>
        c.name.toLowerCase().includes(q) || c.location.toLowerCase().includes(q),
    );
  }, [centres, filter]);

  return (
    <>
      <div className="page-head">
        <h1>Diagnostic centres</h1>
        <p>Find a centre near you and book a test in minutes.</p>
      </div>
      <label className="field search">
        Filter by name or location
        <input
          type="search"
          placeholder="e.g. Mumbai or Andheri"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </label>
      {loading ? (
        <p className="muted">Loading centres…</p>
      ) : (
        <>
          <ErrorBanner message={error} />
          {filtered.length === 0 ? (
            <p className="empty-state">No centres match your filter.</p>
          ) : (
            <ul className="card-grid">
              {filtered.map((c) => (
                <li key={c.id} className="card">
                  <h3>{c.name}</h3>
                  <span className="muted">{c.location}</span>
                  <div className="card-actions">
                    <Link className="btn btn-ghost" to={`/centres/${c.id}`}>
                      View tests
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </>
  );
}
