import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Loader2, Lock, ShieldCheck, Sparkles, ArrowRight, Clock, Zap } from "lucide-react";
import { useLicense } from "../lib/license";

/* Wraps any protected content. Guests are already blocked by ProtectedRoute
 * (they hit /login). This gate handles the AUTHENTICATED user who doesn't
 * have an active license yet — showing a friendly upgrade card instead of
 * hiding the app. Read-only endpoints remain available so old films still
 * load in Studio; we only block the "Create new film" CTA at the UI level. */
export default function LicenseGate({ children }) {
  const {
    license, verifications, can_create_films, trial_used, loading,
  } = useLicense();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-gold animate-spin" />
      </div>
    );
  }

  if (can_create_films) return children;

  const needsVerify = !verifications.email_verified || !verifications.phone_verified;

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-xl"
      >
        <div className="glass rounded-lg p-8 sm:p-10 border border-gold/30 relative overflow-hidden" data-testid="license-gate">
          <div className="absolute -top-24 -right-24 w-64 h-64 rounded-full bg-gold/10 blur-3xl" />
          <div className="relative">
            <div className="overline mb-3 flex items-center gap-2 text-gold">
              <Lock className="w-3.5 h-3.5" /> License required
            </div>
            <h1 className="font-display text-3xl leading-tight" data-testid="license-gate-title">
              {license?.expires_at ? (
                <>Your license has <span className="italic text-gold">expired</span>.</>
              ) : (
                <>Activate a license to <span className="italic text-gold">start creating</span>.</>
              )}
            </h1>
            <p className="text-white/60 text-sm mt-3">
              {license?.expires_at ? (
                <>Your <strong>{license.plan_label}</strong> plan ended. Your existing films are still viewable and downloadable — you just need a new plan to create more.</>
              ) : (
                <>Verify your identity once, then start with the free trial or pick any paid plan. Every plan gives you unlimited films.</>
              )}
            </p>

            {needsVerify ? (
              <div className="mt-8 space-y-3">
                <div className="rounded-md border border-white/10 bg-black/30 p-4 flex items-center gap-3" data-testid="license-gate-verify-required">
                  <ShieldCheck className="w-5 h-5 text-gold" />
                  <div className="flex-1">
                    <div className="text-sm">Verify your email & mobile first</div>
                    <div className="text-xs text-white/50 mt-1">One-time · under a minute</div>
                  </div>
                  <Link to="/verify" className="btn-gold text-sm" data-testid="license-gate-verify-btn">
                    Verify now <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ) : (
              <div className="mt-8 space-y-3">
                {!trial_used && (
                  <div className="rounded-md border border-gold/40 bg-gold/5 p-4 flex items-center gap-3" data-testid="license-gate-trial-available">
                    <Sparkles className="w-5 h-5 text-gold" />
                    <div className="flex-1">
                      <div className="text-sm">7-day free trial available</div>
                      <div className="text-xs text-white/50 mt-1">No card required · one-time offer</div>
                    </div>
                    <Link to="/pricing" className="btn-gold text-sm" data-testid="license-gate-trial-btn">
                      Start trial <Zap className="w-4 h-4" />
                    </Link>
                  </div>
                )}
                <div className="rounded-md border border-white/10 bg-black/30 p-4 flex items-center gap-3">
                  <Clock className="w-5 h-5 text-white/50" />
                  <div className="flex-1">
                    <div className="text-sm">Paid plans from ₹99</div>
                    <div className="text-xs text-white/50 mt-1">30 · 60 · 90 · 365 days · UPI · Cards · Netbanking</div>
                  </div>
                  <Link to="/pricing" className="btn-ghost text-sm" data-testid="license-gate-plans-btn">
                    See plans <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            )}

            <div className="mt-8 text-xs text-white/40">
              Already have an active license? <button onClick={() => window.location.reload()} className="underline hover:text-white/70">Refresh</button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
