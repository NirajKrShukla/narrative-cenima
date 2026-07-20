import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Film, Check, ShieldCheck, Sparkles, ArrowRight, Loader2, IndianRupee, Zap } from "lucide-react";
import { useAuth, formatApiError } from "../lib/auth";
import { useLicense } from "../lib/license";

/* Loads Razorpay checkout script once. */
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

export default function Pricing() {
  const nav = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const {
    license, trial_used, can_start_trial, verifications, plans, loading,
    startTrial, checkout, sandboxComplete, verifyPayment, refresh,
  } = useLicense();
  const [busyPlan, setBusyPlan] = useState(null);

  useEffect(() => {
    if (isAuthenticated) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  const promoActive = license?.source === "promo";
  const needsVerify = isAuthenticated && !promoActive && (!verifications.email_verified || !verifications.phone_verified);

  const handleStartTrial = async () => {
    if (!isAuthenticated) { nav("/login", { state: { from: "/pricing" } }); return; }
    if (needsVerify) { nav("/verify"); return; }
    setBusyPlan("trial");
    try {
      await startTrial();
      toast.success("Your 7-day free trial is active!");
      nav("/studio", { replace: true });
    } catch (err) {
      toast.error(formatApiError(err));
    } finally { setBusyPlan(null); }
  };

  const handlePaidPlan = async (plan) => {
    if (!isAuthenticated) { nav("/login", { state: { from: "/pricing" } }); return; }
    if (needsVerify) { nav("/verify"); return; }
    setBusyPlan(plan.id);
    try {
      const order = await checkout(plan.id);
      if (order.sandbox) {
        // Sandbox mode: instantly complete
        const res = await sandboxComplete(plan.id);
        toast.success(`Sandbox: activated ${res.license.plan_label} · ${res.license.days_remaining} days`);
        nav("/studio", { replace: true });
        return;
      }
      // Live Razorpay flow
      const ok = await loadRazorpayScript();
      if (!ok) { toast.error("Failed to load Razorpay checkout"); return; }
      const options = {
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        name: "AiPillu Studio",
        description: `License · ${plan.label}`,
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
              plan_id: plan.id,
            });
            toast.success(`License activated — ${plan.label}!`);
            nav("/studio", { replace: true });
          } catch (err) {
            toast.error(formatApiError(err));
          }
        },
        modal: { ondismiss: () => setBusyPlan(null) },
      };
      const rzp = new window.Razorpay(options);
      rzp.on("payment.failed", (err) => {
        toast.error(err?.error?.description || "Payment failed");
        setBusyPlan(null);
      });
      rzp.open();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally { setBusyPlan(null); }
  };

  const activeLic = license?.active ? license : null;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="max-w-7xl mx-auto px-6 pt-24 pb-8" data-testid="pricing-page">
        <Link to="/" className="text-white/50 hover:text-white text-sm inline-flex items-center gap-2" data-testid="pricing-back">
          <Film className="w-4 h-4 text-gold" /> AiPillu Studio
        </Link>
      </div>

      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="max-w-7xl mx-auto px-6 text-center pb-12"
      >
        <div className="overline mb-3 justify-center flex items-center gap-2 text-white/60">
          <Sparkles className="w-3.5 h-3.5 text-gold" /> Simple, honest pricing
        </div>
        <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl tracking-tight leading-[1.05]">
          One license. <span className="italic text-gold">Unlimited films.</span>
        </h1>
        <p className="text-white/60 mt-5 max-w-2xl mx-auto">
          Sign in once and get <span className="text-fuchsia-300">20 days on the house</span> — no card, no OTP.
          When the launch promo ends, choose any plan below:
          <span className="text-gold"> no auto-renew</span>, no surprise charges.
        </p>

        {activeLic && (
          <div className="mt-8 inline-flex items-center gap-3 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm" data-testid="pricing-active-badge">
            <ShieldCheck className="w-4 h-4" /> Active: {activeLic.plan_label} · {activeLic.days_remaining} days remaining
          </div>
        )}
        {!activeLic && !isAuthenticated && (
          <div className="mt-8 inline-flex items-center gap-3 px-4 py-2 rounded-full bg-fuchsia-500/10 border border-fuchsia-500/30 text-fuchsia-200 text-sm" data-testid="pricing-launch-promo-banner">
            <Sparkles className="w-4 h-4" /> Launch promo — first login unlocks 20 days free
          </div>
        )}
        {needsVerify && (
          <div className="mt-8" data-testid="pricing-verify-cta">
            <Link to="/verify" className="btn-gold" data-testid="pricing-verify-link">
              Verify email + mobile to unlock <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        )}
      </motion.div>

      {/* Free trial banner — only shown when the launch promo is NOT active
       * (i.e. after the promo ends we fall back to the manual 7-day flow). */}
      {!promoActive && (
        <div className="max-w-7xl mx-auto px-6 pb-6">
          <div
            className="glass rounded-lg p-6 sm:p-8 border border-gold/30 flex flex-col md:flex-row md:items-center gap-6 justify-between"
            data-testid="pricing-trial-card"
          >
            <div>
              <div className="overline mb-1 text-gold">Zero commitment</div>
              <div className="font-display text-2xl">7-day free trial</div>
              <p className="text-white/60 text-sm mt-2 max-w-xl">
                Create unlimited films for a week. No card, no charge — just verify your identity once so
                trial isn't abused.
              </p>
            </div>
            <button
              onClick={handleStartTrial}
              disabled={busyPlan === "trial" || (isAuthenticated && trial_used)}
              className="btn-gold whitespace-nowrap"
              data-testid="pricing-start-trial-btn"
            >
              {busyPlan === "trial" && <Loader2 className="w-4 h-4 animate-spin" />}
              {trial_used ? "Trial used" : "Start free trial"}
              {!trial_used && <ArrowRight className="w-4 h-4" />}
            </button>
          </div>
        </div>
      )}

      {promoActive && (
        <div className="max-w-7xl mx-auto px-6 pb-6">
          <div
            className="glass rounded-lg p-6 sm:p-8 border border-fuchsia-500/40 flex flex-col md:flex-row md:items-center gap-6 justify-between"
            data-testid="pricing-promo-active-card"
          >
            <div>
              <div className="overline mb-1 text-fuchsia-300">Launch promotion — currently active</div>
              <div className="font-display text-2xl">You have {activeLic?.days_remaining} days on the house.</div>
              <p className="text-white/60 text-sm mt-2 max-w-xl">
                No card, no OTP needed during the launch promo — just make films. When it ends, pick any plan below to continue.
              </p>
            </div>
            <div className="text-fuchsia-300/70 text-sm whitespace-nowrap font-mono">
              Ends {activeLic?.expires_at ? new Date(activeLic.expires_at).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : "—"}
            </div>
          </div>
        </div>
      )}

      {/* Paid plan grid */}
      <div className="max-w-7xl mx-auto px-6 pb-24">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mt-8" data-testid="pricing-grid">
          {(plans || []).filter((p) => p.source === "paid").map((p) => (
            <PlanCard
              key={p.id}
              plan={p}
              highlight={p.id === "m1"}
              busy={busyPlan === p.id}
              onBuy={() => handlePaidPlan(p)}
            />
          ))}
        </div>

        <div className="mt-10 text-center text-xs text-white/40 max-w-2xl mx-auto">
          Prices in INR · Powered by Razorpay UPI · Cards · Netbanking · Wallets ·
          Each purchase extends your license from its current expiry — you never lose days by renewing early. ·
          Max validity 365 days.
        </div>
      </div>
    </div>
  );
}

function PlanCard({ plan, highlight, busy, onBuy }) {
  const perDay = (plan.amount_inr / plan.days).toFixed(2);
  return (
    <motion.div
      whileHover={{ y: -4 }}
      className={`glass rounded-lg p-6 border ${highlight ? "border-gold/60" : "border-white/10"} relative`}
      data-testid={`plan-card-${plan.id}`}
    >
      {highlight && (
        <div className="absolute -top-3 right-4 text-xs px-2 py-1 rounded-full bg-gold text-black font-medium tracking-wide" data-testid="plan-badge-popular">
          POPULAR
        </div>
      )}
      <div className="overline text-white/50">{plan.label}</div>
      <div className="mt-3 flex items-baseline gap-1">
        <IndianRupee className="w-5 h-5 text-gold" />
        <span className="font-display text-4xl">{plan.amount_inr}</span>
        <span className="text-white/40 text-sm ml-1">/ {plan.days} days</span>
      </div>
      <div className="text-xs text-white/40 mt-1">≈ ₹{perDay} / day</div>
      <ul className="mt-5 space-y-2 text-sm text-white/70">
        <li className="flex items-start gap-2"><Check className="w-4 h-4 text-gold mt-0.5" />Unlimited films</li>
        <li className="flex items-start gap-2"><Check className="w-4 h-4 text-gold mt-0.5" />Unlimited downloads</li>
        <li className="flex items-start gap-2"><Check className="w-4 h-4 text-gold mt-0.5" />Multilingual auto-dubs</li>
        <li className="flex items-start gap-2"><Check className="w-4 h-4 text-gold mt-0.5" />Per-character voices</li>
      </ul>
      <button
        onClick={onBuy}
        disabled={busy}
        className={`w-full mt-6 flex items-center justify-center gap-2 py-3 rounded-md transition ${
          highlight ? "btn-gold" : "btn-ghost"
        }`}
        data-testid={`plan-buy-${plan.id}`}
      >
        {busy && <Loader2 className="w-4 h-4 animate-spin" />}
        {highlight ? <Zap className="w-4 h-4" /> : null}
        Buy {plan.label}
      </button>
    </motion.div>
  );
}
