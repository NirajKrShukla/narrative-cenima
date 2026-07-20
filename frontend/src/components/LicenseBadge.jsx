import React, { useState, useRef } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { Sparkles, Clock, AlertTriangle, Zap, Loader2 } from "lucide-react";
import { useLicense } from "../lib/license";
import { useAuth, formatApiError } from "../lib/auth";

/* Ensure the Razorpay SDK is loaded (idempotent) */
function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve(true);
    s.onerror = () => resolve(false);
    document.body.appendChild(s);
  });
}

/* Nav badge showing days remaining on the current license.
 * Colour palette shifts as the deadline approaches:
 *   >7 days  → calm gold ring
 *   ≤7 days  → amber pulse
 *   ≤3 days  → rose pulse ("Renew")
 *   expired  → subdued red with a "Renew" CTA
 *
 * Hover popover reveals plan + expiry + a **1-click "Renew ₹99" button** that
 * opens Razorpay checkout inline — no page navigation. Falls back to sandbox
 * instant-unlock while SANDBOX_MODE=true.
 */
export default function LicenseBadge({ compact = false }) {
  const { license, loading, plans, verifications, checkout, sandboxComplete, verifyPayment, refresh } = useLicense();
  const { user } = useAuth();
  const [renewing, setRenewing] = useState(false);
  const clickedRef = useRef(false);

  if (loading) return null;
  const expired = !!license && !license.active;
  const active = !!license?.active;
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

  const oneClickRenew = async (planId = "m1") => {
    // Prevent accidental double-clicks
    if (clickedRef.current) return;
    clickedRef.current = true;
    setRenewing(true);
    try {
      const order = await checkout(planId);
      if (order.sandbox) {
        const res = await sandboxComplete(planId);
        toast.success(`Sandbox: activated · ${res.license.days_remaining} days`);
        setRenewing(false);
        clickedRef.current = false;
        return;
      }
      const ok = await loadRazorpayScript();
      if (!ok) {
        toast.error("Failed to load Razorpay");
        setRenewing(false);
        clickedRef.current = false;
        return;
      }
      const options = {
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        name: "AiPillu Studio",
        description: `License · ${order.plan?.label || planId}`,
        order_id: order.order_id,
        prefill: {
          name: user?.name || "",
          email: user?.email || "",
          contact: user?.phone || "",
        },
        theme: { color: "#e6c874" },
        handler: async (r) => {
          try {
            await verifyPayment({
              razorpay_order_id: r.razorpay_order_id,
              razorpay_payment_id: r.razorpay_payment_id,
              razorpay_signature: r.razorpay_signature,
              plan_id: planId,
            });
            toast.success("License extended — thank you!");
            await refresh();
          } catch (err) {
            toast.error(formatApiError(err));
          } finally {
            setRenewing(false);
            clickedRef.current = false;
          }
        },
        modal: {
          ondismiss: () => {
            setRenewing(false);
            clickedRef.current = false;
          },
        },
      };
      const rzp = new window.Razorpay(options);
      rzp.on("payment.failed", (err) => {
        toast.error(err?.error?.description || "Payment failed");
        setRenewing(false);
        clickedRef.current = false;
      });
      rzp.open();
    } catch (err) {
      toast.error(formatApiError(err));
      setRenewing(false);
      clickedRef.current = false;
    }
  };

  return (
    <div className="relative group" data-testid="license-badge">
      <Link
        to="/pricing"
        className={`relative inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium transition ${ring} hover:brightness-125`}
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

      {/* Hover popover with plan info + 1-click renew */}
      <div className="absolute right-0 top-full mt-2 w-72 opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto transition duration-200 z-40" data-testid="license-badge-popover">
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
            <div className="mt-3 pt-3 border-t border-white/10 space-y-2">
              <button
                type="button"
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); oneClickRenew("m1"); }}
                disabled={renewing}
                className="btn-gold w-full justify-center py-2 text-xs disabled:opacity-70"
                data-testid="license-badge-renew-btn"
              >
                {renewing ? (
                  <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Opening…</>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5" />
                    {expired ? "Reactivate" : "Extend"} · ₹{cheapest.amount_inr} · {cheapest.days} days
                  </>
                )}
              </button>
              <Link
                to="/pricing"
                className="block text-center text-[11px] text-white/50 hover:text-white/80 transition"
                data-testid="license-badge-see-plans"
              >
                Or see all plans →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
