import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Users, ShieldCheck, IndianRupee, Film, Search, ArrowLeft, TrendingUp, Calendar, Sparkles } from "lucide-react";
import { API } from "../lib/api";
import { useAuth } from "../lib/auth";

/* Admin-only KYC + revenue dashboard. Guarded server-side (role=admin).
 * Guests / non-admin users hitting this page get a friendly "not authorised"
 * card instead of a raw 403. */
export default function Admin() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("users"); // users | licenses
  const [licenses, setLicenses] = useState([]);

  const isAdmin = user?.role === "admin";

  useEffect(() => {
    if (!isAdmin) { setLoading(false); return; }
    (async () => {
      try {
        const [s, u, l] = await Promise.all([
          API.get("/admin/summary"),
          API.get("/admin/users?limit=50"),
          API.get("/admin/licenses?limit=50"),
        ]);
        setSummary(s.data);
        setUsers(u.data.users);
        setLicenses(l.data.licenses);
      } catch (err) {
        toast.error("Failed to load admin data");
      } finally {
        setLoading(false);
      }
    })();
  }, [isAdmin]);

  const searchUsers = async () => {
    try {
      const { data } = await API.get(`/admin/users?q=${encodeURIComponent(q)}&limit=100`);
      setUsers(data.users);
    } catch { toast.error("Search failed"); }
  };

  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="glass rounded-lg p-8 border border-white/10 max-w-md text-center" data-testid="admin-forbidden">
          <ShieldCheck className="w-8 h-8 text-rose-400 mx-auto mb-4" />
          <h1 className="font-display text-2xl">Admin only</h1>
          <p className="text-white/60 text-sm mt-2">This dashboard is reserved for staff accounts.</p>
          <Link to="/" className="btn-ghost mt-6 inline-flex" data-testid="admin-home-btn"><ArrowLeft className="w-4 h-4" /> Back home</Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-white/50">Loading admin data…</div>;
  }

  return (
    <div className="min-h-screen">
      <div className="glass sticky top-0 z-30" data-testid="admin-topbar">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-white/70 hover:text-white transition" data-testid="admin-back-home">
            <ArrowLeft className="w-4 h-4" /> <span className="text-sm">Home</span>
          </Link>
          <div className="font-display text-lg">Admin <span className="text-gold">Dashboard</span></div>
          <div className="text-xs text-white/50">Signed in as {user.email}</div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8" data-testid="admin-page">
        {/* Summary cards */}
        {summary && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-2 lg:grid-cols-4 gap-4"
            data-testid="admin-summary-grid"
          >
            <Card icon={Users} label="Users" value={summary.users.total} sub={`${summary.users.verified} fully verified`} tone="gold" />
            <Card icon={ShieldCheck} label="Active licenses" value={summary.licenses.active} sub="right now" tone="emerald" />
            <Card icon={Film} label="Films made" value={summary.projects.with_final_film} sub={`from ${summary.projects.total} projects`} tone="rose" />
            <Card
              icon={IndianRupee}
              label="Revenue"
              value={`₹${summary.revenue.total_inr.toLocaleString()}`}
              sub={`₹${summary.revenue.this_month_inr.toLocaleString()} this month · ${summary.revenue.total_transactions} paid`}
              tone="gold"
            />
          </motion.div>
        )}

        {/* Revenue by plan */}
        {summary?.revenue?.by_plan?.length > 0 && (
          <div className="card p-6" data-testid="admin-by-plan">
            <div className="font-display text-lg mb-4 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-gold" /> Revenue by plan
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {summary.revenue.by_plan.map((p) => (
                <div key={p.plan_id} className="rounded-md border border-white/10 bg-black/30 p-4">
                  <div className="text-xs text-white/50 uppercase">{p.plan_id}</div>
                  <div className="font-display text-2xl mt-1">₹{p.total_inr.toLocaleString()}</div>
                  <div className="text-xs text-white/50 mt-1">{p.count} × transactions</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex items-center gap-3 border-b border-white/10">
          {[
            { k: "users", l: "Users" },
            { k: "licenses", l: "Licenses" },
          ].map((t) => (
            <button
              key={t.k}
              onClick={() => setTab(t.k)}
              className={`px-4 py-3 text-sm border-b-2 -mb-px transition ${
                tab === t.k ? "border-gold text-gold" : "border-transparent text-white/60 hover:text-white/90"
              }`}
              data-testid={`admin-tab-${t.k}`}
            >
              {t.l}
            </button>
          ))}
        </div>

        {tab === "users" && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="relative flex-1 max-w-md">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && searchUsers()}
                  placeholder="Search by email, name, or phone…"
                  className="w-full pl-10 pr-4 py-2 rounded-md bg-black/40 border border-white/10 text-sm focus:border-gold outline-none"
                  data-testid="admin-search-input"
                />
              </div>
              <button onClick={searchUsers} className="btn-ghost text-sm" data-testid="admin-search-btn">Search</button>
            </div>
            <div className="card overflow-x-auto" data-testid="admin-users-table">
              <table className="w-full text-sm">
                <thead className="text-xs text-white/50 uppercase">
                  <tr>
                    <th className="text-left p-3">User</th>
                    <th className="text-left p-3">Verifications</th>
                    <th className="text-left p-3">Phone</th>
                    <th className="text-left p-3">License</th>
                    <th className="text-left p-3">Ref code</th>
                    <th className="text-left p-3">Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.user_id} className="border-t border-white/5 hover:bg-white/5" data-testid={`admin-user-row-${u.user_id}`}>
                      <td className="p-3">
                        <div className="font-medium">{u.name || "—"}</div>
                        <div className="text-xs text-white/50">{u.email}</div>
                        {u.role === "admin" && <span className="text-[10px] px-1.5 py-0.5 mt-1 inline-block rounded bg-gold/10 text-gold border border-gold/30">ADMIN</span>}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-1">
                          <VerifyChip label="Email" ok={u.email_verified} />
                          <VerifyChip label="Phone" ok={u.phone_verified} />
                        </div>
                      </td>
                      <td className="p-3 text-white/70 text-xs">{u.phone || "—"}</td>
                      <td className="p-3">
                        {u.license_active ? (
                          <div>
                            <div className="text-emerald-300 text-xs font-medium">{u.current_plan}</div>
                            <div className="text-[10px] text-white/50">{u.days_remaining}d left</div>
                          </div>
                        ) : (
                          <span className="text-white/40 text-xs">None</span>
                        )}
                      </td>
                      <td className="p-3 text-xs font-mono text-gold/70">{u.referral_code || "—"}</td>
                      <td className="p-3 text-xs text-white/50">{u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tab === "licenses" && (
          <div className="card overflow-x-auto" data-testid="admin-licenses-table">
            <table className="w-full text-sm">
              <thead className="text-xs text-white/50 uppercase">
                <tr>
                  <th className="text-left p-3">User</th>
                  <th className="text-left p-3">Plan</th>
                  <th className="text-left p-3">Source</th>
                  <th className="text-left p-3">Amount</th>
                  <th className="text-left p-3">Starts</th>
                  <th className="text-left p-3">Expires</th>
                  <th className="text-left p-3">Payment ID</th>
                </tr>
              </thead>
              <tbody>
                {licenses.map((lic) => (
                  <tr key={lic.id} className="border-t border-white/5 hover:bg-white/5">
                    <td className="p-3 text-xs">{lic.email || lic.user_id}</td>
                    <td className="p-3 text-xs">{lic.plan_label}</td>
                    <td className="p-3"><SourceChip s={lic.source} /></td>
                    <td className="p-3 text-xs">₹{lic.amount_inr}</td>
                    <td className="p-3 text-xs text-white/50">{lic.starts_at ? new Date(lic.starts_at).toLocaleDateString() : "—"}</td>
                    <td className="p-3 text-xs text-white/50">{lic.expires_at ? new Date(lic.expires_at).toLocaleDateString() : "—"}</td>
                    <td className="p-3 text-xs font-mono text-white/50">{lic.payment_id ? lic.payment_id.slice(-12) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const toneMap = {
  gold: "border-gold/40 bg-gold/5",
  emerald: "border-emerald-500/40 bg-emerald-500/5",
  rose: "border-rose-500/40 bg-rose-500/5",
};

function Card({ icon: Icon, label, value, sub, tone = "gold" }) {
  return (
    <div className={`rounded-md p-5 border ${toneMap[tone]}`}>
      <div className="flex items-center gap-2 text-xs text-white/60"><Icon className="w-4 h-4 text-gold" />{label}</div>
      <div className="font-display text-3xl mt-2">{value}</div>
      <div className="text-xs text-white/50 mt-1">{sub}</div>
    </div>
  );
}

function VerifyChip({ label, ok }) {
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
      ok ? "border-emerald-500/40 text-emerald-300 bg-emerald-500/10" : "border-white/10 text-white/40"
    }`}>
      {ok ? "✓" : "✗"} {label}
    </span>
  );
}

function SourceChip({ s }) {
  const map = {
    trial: "border-gold/40 text-gold bg-gold/10",
    paid: "border-emerald-500/40 text-emerald-300 bg-emerald-500/10",
    referral: "border-fuchsia-500/40 text-fuchsia-300 bg-fuchsia-500/10",
  };
  return <span className={`text-[10px] px-2 py-0.5 rounded border ${map[s] || "border-white/10 text-white/40"}`}>{s}</span>;
}
