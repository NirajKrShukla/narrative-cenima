import React from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Clock, AlertTriangle, Zap } from "lucide-react";
import { useLicense } from "../lib/license";

/* Nav badge showing days remaining on the current license.
 * Colour palette shifts as the deadline approaches:
 *   >7 days  → calm gold ring
 *   ≤7 days  → amber pulse
 *   ≤3 days  → rose pulse ("Renew")
 *   expired  → subdued red with a "Renew" CTA
 *
 * On hover a tiny popover reveals the plan + exact date. Click → /pricing.
 * Renders nothing if the user isn't signed in yet (loading or no license and
 * no verifications) — the sign-in / pricing CTAs elsewhere already cover
 * that state and we don't want to double-up.
 */
export default function LicenseBadge({ compact = false }) {
  const { license, loading, plans, verifications } = useLicense();
  if (loading) return null;

  const expired = !!license && !license.active;
  const active = !!license?.active;

  // Fully-anonymous states (no license record, no verification either) hide
  // the badge entirely — the "Sign in" CTA in nav is enough.
  if (!license && !verifications?.email_verified) return null;

  const days = license?.days_remaining || 0;
  let tone = "gold";
  if (expired) tone = "danger";
  else if (days <= 3) tone = "danger";
  else if (days <= 7) tone = "amber";

  const ring = {
    gold: "border-gold/40 text-gold bg-gold/5",
    amber: "border-amber-400/40 text-amber-300 bg-amber-500/5",
    danger: "border-rose-400/50 text-rose-300 bg-rose-500/10",
  }[tone];

  const Icon = expired ? AlertTriangle : (tone === "gold" ? Sparkles : Clock);
  const label = expired
    ? "License expired"
    : (days === 1 ? "1 day left" : `${days} days left`);

  const cheapest = (plans || []).find((p) => p.id === "m1");

  return (
    <div className="relative group" data-testid="license-badge">
      <Link
        to="/pricing"
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium transition ${ring} hover:brightness-125`}
        data-testid={`license-badge-${tone}`}
      >
        <AnimatePresence>
          {(tone !== "gold") && (
            <motion.span
              key="pulse"
              className={`absolute -left-0.5 -top-0.5 w-2 h-2 rounded-full ${
                tone === "danger" ? "bg-rose-400" : "bg-amber-400"
              }`}
              initial={{ opacity: 0.4, scale: 1 }}
              animate={{ opacity: [0.4, 1, 0.4], scale: [1, 1.6, 1] }}
              transition={{ duration: 1.6, repeat: Infinity }}
            />
          )}
        </AnimatePresence>
        <Icon className="w-3.5 h-3.5" />
        <span className={compact ? "hidden sm:inline" : ""}>{label}</span>
        {(expired || days <= 7) && (
          <span className="ml-1 inline-flex items-center gap-1 pl-2 border-l border-white/10 text-[10px] uppercase tracking-wider">
            <Zap className="w-3 h-3" /> Renew
          </span>
        )}
      </Link>

      {/* Hover popover with plan info */}
      <div className="absolute right-0 top-full mt-2 w-64 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition duration-200 z-40" data-testid="license-badge-popover">
        <div className="glass rounded-md border border-white/10 p-4 shadow-2xl">
          {active && (
            <>
              <div className="text-xs text-white/50">Current plan</div>
              <div className="text-sm font-medium mt-0.5">{license.plan_label}</div>
              <div className="text-xs text-white/50 mt-2">Expires</div>
              <div className="text-sm mt-0.5">
                {license.expires_at ? new Date(license.expires_at).toLocaleDateString(undefined, {
                  day: "numeric", month: "short", year: "numeric",
                }) : "—"}
              </div>
            </>
          )}
          {expired && (
            <>
              <div className="text-sm font-medium text-rose-300">Your license has ended</div>
              <div className="text-xs text-white/60 mt-1">
                Your existing films are still viewable & downloadable — renew to create new ones.
              </div>
            </>
          )}
          {cheapest && (
            <div className="mt-3 pt-3 border-t border-white/10 text-xs text-white/70">
              {expired ? "Reactivate " : "Extend "} from <span className="text-gold">₹{cheapest.amount_inr}</span> · {cheapest.days} days
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
