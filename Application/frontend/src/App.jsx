import { useState, useEffect, useCallback } from "react";

// ─── API base URL ────────────────────────────────────────────────────────────
// Falls back to the browser hostname so it works automatically when accessed
// over the EC2 public IP (e.g. http://54.x.x.x:8000).
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  `http://${window.location.hostname}:8000`;

// ─── Helpers ─────────────────────────────────────────────────────────────────
const EMPTY_FORM = {
  customer_id: "",
  product_id: "",
  store_id: "",
  quantity: "",
  price: "",
};

function StatusBadge({ ok }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${
        ok
          ? "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20"
          : "bg-red-500/10 text-red-400 ring-1 ring-red-500/20"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          ok ? "bg-emerald-400 animate-pulse-soft" : "bg-red-400"
        }`}
      />
      {ok ? "Connected" : "Offline"}
    </span>
  );
}

// ─── Main Application ────────────────────────────────────────────────────────
export default function App() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [transactions, setTransactions] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState(null); // { type: 'success' | 'error', msg }
  const [backendAlive, setBackendAlive] = useState(false);

  // ── Health check ─────────────────────────────────────
  useEffect(() => {
    let mounted = true;
    const ping = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/health`);
        if (mounted) setBackendAlive(res.ok);
      } catch {
        if (mounted) setBackendAlive(false);
      }
    };
    ping();
    const id = setInterval(ping, 15000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  // ── Auto-refresh feed every 8 s ─────────────────────
  const fetchTransactions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/transactions`);
      if (res.ok) {
        const data = await res.json();
        setTransactions(data);
      }
    } catch {
      /* network blip — keep stale data */
    }
  }, []);

  useEffect(() => {
    fetchTransactions();
    const id = setInterval(fetchTransactions, 8000);
    return () => clearInterval(id);
  }, [fetchTransactions]);

  // ── Toast auto-dismiss ──────────────────────────────
  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(id);
  }, [toast]);

  // ── Form handlers ───────────────────────────────────
  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    const payload = {
      customer_id: form.customer_id.trim(),
      product_id: form.product_id.trim(),
      store_id: form.store_id.trim(),
      quantity: parseInt(form.quantity, 10),
      price: parseFloat(form.price),
    };

    // Client-side guard
    if (
      !payload.customer_id ||
      !payload.product_id ||
      !payload.store_id ||
      isNaN(payload.quantity) ||
      payload.quantity <= 0 ||
      isNaN(payload.price) ||
      payload.price <= 0
    ) {
      setToast({ type: "error", msg: "All fields are required and numeric values must be > 0." });
      setSubmitting(false);
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/transactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.status === 201) {
        setToast({ type: "success", msg: "Transaction committed successfully." });
        setForm(EMPTY_FORM);
        await fetchTransactions();
      } else {
        const err = await res.json().catch(() => ({}));
        setToast({
          type: "error",
          msg: err.detail || `Server responded with ${res.status}.`,
        });
      }
    } catch (err) {
      setToast({ type: "error", msg: `Network error: ${err.message}` });
    } finally {
      setSubmitting(false);
    }
  };

  // ── Render ──────────────────────────────────────────
  return (
    <div className="min-h-screen px-4 py-8 md:px-8 lg:px-16 animate-fade-in">
      {/* ─ Header ─ */}
      <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-10">
        <div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-brand-300 via-brand-400 to-brand-500 bg-clip-text text-transparent">
            Retail Analytics
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Enterprise Transaction Console &middot; AWS Cloud
          </p>
        </div>
        <StatusBadge ok={backendAlive} />
      </header>

      {/* ─ Toast ─ */}
      {toast && (
        <div
          className={`mb-6 animate-slide-up rounded-xl px-5 py-3 text-sm font-medium shadow-lg ${
            toast.type === "success"
              ? "bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/30"
              : "bg-red-500/10 text-red-300 ring-1 ring-red-500/30"
          }`}
        >
          {toast.type === "success" ? "✓ " : "✗ "}
          {toast.msg}
        </div>
      )}

      <div className="grid gap-8 lg:grid-cols-[minmax(0,420px)_1fr]">
        {/* ─ Form Card ─ */}
        <section className="glass-card p-6 md:p-8 self-start">
          <h2 className="text-lg font-semibold text-slate-200 mb-6 flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600/20 text-brand-400">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
            </span>
            New Transaction
          </h2>

          <form onSubmit={handleSubmit} className="space-y-5" id="transaction-form">
            {[
              { name: "customer_id", label: "Customer ID", type: "text", placeholder: "CUST-001" },
              { name: "product_id", label: "Product ID", type: "text", placeholder: "PROD-2048" },
              { name: "store_id", label: "Store ID", type: "text", placeholder: "STORE-NYC-12" },
              { name: "quantity", label: "Quantity", type: "number", placeholder: "1" },
              { name: "price", label: "Unit Price ($)", type: "number", placeholder: "29.99" },
            ].map((f) => (
              <div key={f.name}>
                <label
                  htmlFor={f.name}
                  className="block text-xs font-medium uppercase tracking-wider text-slate-400 mb-1.5"
                >
                  {f.label}
                </label>
                <input
                  id={f.name}
                  name={f.name}
                  type={f.type}
                  step={f.type === "number" ? "any" : undefined}
                  min={f.type === "number" ? "0" : undefined}
                  placeholder={f.placeholder}
                  value={form[f.name]}
                  onChange={handleChange}
                  required
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30"
                />
              </div>
            ))}

            <button
              type="submit"
              disabled={submitting}
              id="submit-transaction"
              className="w-full rounded-lg bg-gradient-to-r from-brand-600 to-brand-500 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-brand-600/25 transition-all hover:shadow-brand-500/40 hover:brightness-110 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
                <span className="inline-flex items-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" /></svg>
                  Committing…
                </span>
              ) : (
                "Commit Transaction"
              )}
            </button>
          </form>
        </section>

        {/* ─ Feed Table ─ */}
        <section className="glass-card p-6 md:p-8 overflow-hidden">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600/20 text-emerald-400">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              </span>
              Live Transaction Feed
            </h2>
            <span className="text-xs text-slate-500">
              Auto-refresh 8 s &middot; Latest 50
            </span>
          </div>

          {transactions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-500">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}><path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" /></svg>
              <p className="text-sm">No transactions recorded yet.</p>
              <p className="text-xs mt-1 text-slate-600">Submit one using the form →</p>
            </div>
          ) : (
            <div className="overflow-x-auto -mx-6 md:-mx-8">
              <table className="w-full min-w-[720px] text-left text-sm" id="transaction-table">
                <thead>
                  <tr className="border-b border-white/5 text-xs uppercase tracking-wider text-slate-500">
                    <th className="px-6 md:px-8 pb-3 font-medium">Transaction ID</th>
                    <th className="px-4 pb-3 font-medium">Customer</th>
                    <th className="px-4 pb-3 font-medium">Product</th>
                    <th className="px-4 pb-3 font-medium">Store</th>
                    <th className="px-4 pb-3 font-medium text-right">Qty</th>
                    <th className="px-4 pb-3 font-medium text-right">Price</th>
                    <th className="px-4 pb-3 font-medium text-right pr-6 md:pr-8">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx, i) => (
                    <tr
                      key={tx.transaction_id}
                      className={`border-b border-white/[0.03] transition hover:bg-white/[0.03] ${
                        i === 0 ? "animate-slide-up" : ""
                      }`}
                    >
                      <td className="px-6 md:px-8 py-3 font-mono text-xs text-brand-300 truncate max-w-[160px]">
                        {tx.transaction_id}
                      </td>
                      <td className="px-4 py-3 text-slate-300">{tx.customer_id}</td>
                      <td className="px-4 py-3 text-slate-300">{tx.product_id}</td>
                      <td className="px-4 py-3 text-slate-300">{tx.store_id}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-300">
                        {tx.quantity}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-emerald-400 font-medium">
                        ${Number(tx.price).toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-slate-500 pr-6 md:pr-8 whitespace-nowrap">
                        {new Date(tx.date).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {/* ─ Footer ─ */}
      <footer className="mt-16 text-center text-xs text-slate-600">
        Retail Analytics Platform &copy; {new Date().getFullYear()} &middot;
        Powered by FastAPI + React on AWS
      </footer>
    </div>
  );
}
