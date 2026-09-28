import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, api, type AdminTest, type Centre, type CentreDetail } from "../../api";
import ErrorBanner from "../../components/ErrorBanner";

function inUseMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 409) return `Cannot delete — in use: ${err.message}`;
  return err instanceof ApiError ? err.message : "Request failed";
}

export default function Catalogue() {
  const [centres, setCentres] = useState<Centre[]>([]);
  const [details, setDetails] = useState<Record<number, CentreDetail>>({});
  const [adminTests, setAdminTests] = useState<AdminTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [newCentreName, setNewCentreName] = useState("");
  const [newCentreLoc, setNewCentreLoc] = useState("");
  const [newTestName, setNewTestName] = useState("");
  const [editCentre, setEditCentre] = useState<Record<number, { name: string; location: string }>>({});
  const [priceEdits, setPriceEdits] = useState<Record<string, string>>({});
  const [priceError, setPriceError] = useState<string | null>(null);
  const [addOffering, setAddOffering] = useState<Record<number, { test_id: string; price: string }>>({});
  const [renameTest, setRenameTest] = useState<Record<number, string>>({});

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, tests] = await Promise.all([api.listCentres(), api.adminTests()]);
      setCentres(c);
      setAdminTests(tests);
      const d = await Promise.all(c.map((x) => api.centreDetail(x.id)));
      const m: Record<number, CentreDetail> = {};
      for (const det of d) m[det.id] = det;
      setDetails(m);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load catalogue");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const knownTests = useMemo(
    () => [...adminTests].sort((a, b) => a.id - b.id),
    [adminTests],
  );

  async function onAddCentre(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    try {
      await api.adminCreateCentre(newCentreName.trim(), newCentreLoc.trim());
      setNewCentreName("");
      setNewCentreLoc("");
      setNotice("Centre added.");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add centre");
    }
  }

  async function onSaveCentre(id: number) {
    const draft = editCentre[id];
    if (!draft) return;
    setError(null);
    setNotice(null);
    try {
      await api.adminUpdateCentre(id, {
        name: draft.name.trim() || undefined,
        location: draft.location.trim() || undefined,
      });
      setNotice(`Centre #${id} updated.`);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update centre");
    }
  }

  async function onDeleteCentre(id: number, name: string) {
    if (!window.confirm(`Delete centre "${name}" (#${id})?`)) return;
    setError(null);
    setNotice(null);
    try {
      await api.adminDeleteCentre(id);
      setNotice(`Centre #${id} deleted.`);
      await refresh();
    } catch (err) {
      setError(inUseMessage(err));
    }
  }

  async function onSavePrice(centreId: number, testId: number) {
    const key = `${centreId}:${testId}`;
    const raw = (priceEdits[key] ?? "").trim();
    const price = Number(raw);
    if (!raw || !Number.isFinite(price) || price <= 0) {
      setPriceError("Price must be a number greater than 0.");
      return;
    }
    setPriceError(null);
    setError(null);
    try {
      await api.adminUpsertOffering(centreId, testId, price);
      setNotice(`Price updated (centre #${centreId}, test #${testId}).`);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update price");
    }
  }

  async function onAddOffering(centreId: number) {
    const draft = addOffering[centreId];
    const testId = Number(draft?.test_id);
    const price = Number(draft?.price);
    if (!Number.isInteger(testId) || testId <= 0) {
      setError("Choose a test to offer at this centre.");
      return;
    }
    if (!Number.isFinite(price) || price <= 0) {
      setError("Price must be a number greater than 0.");
      return;
    }
    setError(null);
    try {
      await api.adminUpsertOffering(centreId, testId, price);
      setNotice(`Offering saved (centre #${centreId}, test #${testId}).`);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save offering");
    }
  }

  async function onCreateTest(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    try {
      await api.adminCreateTest(newTestName.trim());
      setNewTestName("");
      setNotice("Test added.");
      await refresh();
    } catch (err) {
      setError(inUseMessage(err));
    }
  }

  async function onRenameTest(id: number) {
    const name = (renameTest[id] ?? "").trim();
    if (!name) {
      setError("Test name cannot be empty.");
      return;
    }
    setError(null);
    try {
      await api.adminUpdateTest(id, { name });
      setNotice(`Test #${id} renamed.`);
      await refresh();
    } catch (err) {
      setError(inUseMessage(err));
    }
  }

  async function onDeleteTest(id: number, name: string) {
    if (!window.confirm(`Delete test "${name}" (#${id})?`)) return;
    setError(null);
    try {
      await api.adminDeleteTest(id);
      setNotice(`Test #${id} deleted.`);
      await refresh();
    } catch (err) {
      setError(inUseMessage(err));
    }
  }

  if (loading) {
    return (
      <section className="card">
        <h1>Catalogue</h1>
        <p className="muted">Loading catalogue…</p>
      </section>
    );
  }

  return (
    <>
      <div className="page-head">
        <h1>Catalogue</h1>
        <p>Manage centres, tests, and per-centre prices.</p>
      </div>
      <ErrorBanner message={error} />
      {priceError && <p className="alert-error" role="alert">{priceError}</p>}
      {notice && <p className="muted" role="status">{notice}</p>}

      <section className="card">
        <h2>Add centre</h2>
        <form className="toolbar" onSubmit={onAddCentre}>
          <label className="field">
            Name
            <input type="text" value={newCentreName} onChange={(e) => setNewCentreName(e.target.value)} required />
          </label>
          <label className="field">
            Location
            <input type="text" value={newCentreLoc} onChange={(e) => setNewCentreLoc(e.target.value)} required />
          </label>
          <button type="submit">Add centre</button>
        </form>
      </section>

      <h2>Centres ({centres.length})</h2>
      {centres.map((c) => {
        const det = details[c.id];
        const draft = editCentre[c.id] ?? { name: c.name, location: c.location };
        const offerDraft = addOffering[c.id] ?? { test_id: "", price: "" };
        return (
          <section key={c.id} className="card">
            <h3>#{c.id} — {c.name} <span className="muted">({c.location})</span></h3>
            <div className="toolbar">
              <label className="field">
                Name
                <input
                  type="text"
                  value={draft.name}
                  onChange={(e) => setEditCentre((p) => ({ ...p, [c.id]: { ...draft, name: e.target.value } }))}
                />
              </label>
              <label className="field">
                Location
                <input
                  type="text"
                  value={draft.location}
                  onChange={(e) => setEditCentre((p) => ({ ...p, [c.id]: { ...draft, location: e.target.value } }))}
                />
              </label>
              <button type="button" className="btn-ghost" onClick={() => void onSaveCentre(c.id)}>Save</button>
              <button type="button" className="btn-danger" onClick={() => void onDeleteCentre(c.id, c.name)}>Delete</button>
            </div>
            <h4>Tests &amp; prices</h4>
            {!det || det.tests.length === 0 ? (
              <p className="empty-state">No tests offered at this centre yet.</p>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>Test</th><th>Price</th><th>New price</th><th></th></tr>
                  </thead>
                  <tbody>
                    {det.tests.map((t) => {
                      const key = `${c.id}:${t.id}`;
                      return (
                        <tr key={t.id}>
                          <td>#{t.id} {t.name}</td>
                          <td>₹{Number(t.price).toFixed(2)}</td>
                          <td>
                            <input
                              type="text"
                              inputMode="decimal"
                              placeholder={String(t.price)}
                              value={priceEdits[key] ?? ""}
                              onChange={(e) => setPriceEdits((p) => ({ ...p, [key]: e.target.value }))}
                              aria-label={`New price for ${t.name} at centre ${c.id}`}
                            />
                          </td>
                          <td>
                            <button type="button" className="btn-ghost" onClick={() => void onSavePrice(c.id, t.id)}>Save price</button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            <div className="toolbar">
              <label className="field">
                Test
                <select
                  value={offerDraft.test_id}
                  onChange={(e) => setAddOffering((p) => ({ ...p, [c.id]: { ...offerDraft, test_id: e.target.value } }))}
                >
                  <option value="">Select test…</option>
                  {knownTests.map((t) => (
                    <option key={t.id} value={t.id}>#{t.id} {t.name}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                Price
                <input
                  type="text"
                  inputMode="decimal"
                  placeholder="e.g. 499.00"
                  value={offerDraft.price}
                  onChange={(e) => setAddOffering((p) => ({ ...p, [c.id]: { ...offerDraft, price: e.target.value } }))}
                />
              </label>
              <button type="button" className="btn-ghost" onClick={() => void onAddOffering(c.id)}>Add / update offering</button>
            </div>
          </section>
        );
      })}

      <section className="card">
        <h2>Tests</h2>
        <form className="toolbar" onSubmit={onCreateTest}>
          <label className="field">
            New test name
            <input type="text" value={newTestName} onChange={(e) => setNewTestName(e.target.value)} required />
          </label>
          <button type="submit">Add test</button>
        </form>
        {knownTests.length === 0 ? (
          <p className="empty-state">No tests yet.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>ID</th><th>Name</th><th>Rename to</th><th></th></tr>
              </thead>
              <tbody>
                {knownTests.map((t) => (
                  <tr key={t.id}>
                    <td>{t.id}</td>
                    <td>{t.name}</td>
                    <td>
                      <input
                        type="text"
                        placeholder={t.name}
                        value={renameTest[t.id] ?? ""}
                        onChange={(e) => setRenameTest((p) => ({ ...p, [t.id]: e.target.value }))}
                        aria-label={`Rename test ${t.id}`}
                      />
                    </td>
                    <td>
                      <div className="toolbar">
                        <button type="button" className="btn-ghost" onClick={() => void onRenameTest(t.id)}>Rename</button>
                        <button type="button" className="btn-danger" onClick={() => void onDeleteTest(t.id, t.name)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
