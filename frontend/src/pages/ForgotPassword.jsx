import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Mail, Lock, KeyRound, ArrowRight, Film } from "lucide-react";
import { API } from "../lib/api";
import { formatApiError } from "../lib/auth";

/* Two-step "forgot password" page — send OTP → set new password. */
export default function ForgotPassword() {
  const nav = useNavigate();
  const [step, setStep] = useState("send"); // send | reset
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sandbox, setSandbox] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const sendCode = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await API.post("/auth/forgot-password", { email });
      if (data.sandbox_code) setSandbox(data.sandbox_code);
      setStep("reset");
      toast.success("If the email exists, we've sent a reset code.");
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const resetPassword = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await API.post("/auth/reset-password", { email, code, new_password: newPassword });
      toast.success("Password reset — please sign in.");
      nav("/login", { replace: true });
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        <Link to="/" className="flex items-center gap-2 mb-8 group">
          <Film className="w-5 h-5 text-gold group-hover:rotate-12 transition-transform" />
          <span className="font-display text-lg tracking-tight">AiPillu <span className="text-gold">Studio</span></span>
        </Link>

        <div className="glass rounded-lg p-8 border border-white/10" data-testid="forgot-card">
          <div className="overline mb-3 text-white/60"><KeyRound className="w-3.5 h-3.5 inline text-gold mr-1" /> Reset password</div>
          <h1 className="font-display text-3xl leading-tight">
            {step === "send"
              ? <>Forgot your <span className="italic text-gold">password</span>?</>
              : <>Set a <span className="italic text-gold">new one</span>.</>}
          </h1>
          <p className="text-white/60 text-sm mt-3">
            {step === "send"
              ? "We'll send a 6-digit code to your email. Use it to set a fresh password."
              : "Enter the code we sent to " + email + "."}
          </p>

          {step === "send" && (
            <form onSubmit={sendCode} className="mt-8 space-y-4">
              <div className="relative">
                <Mail className="w-4 h-4 text-white/40 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full pl-10 pr-4 py-3 rounded-md bg-black/40 border border-white/10 focus:border-gold outline-none text-sm"
                  data-testid="forgot-email-input"
                />
              </div>
              <button className="btn-gold w-full justify-center" disabled={busy} data-testid="forgot-send-btn">
                {busy ? "Sending…" : "Send reset code"} <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          )}

          {step === "reset" && (
            <form onSubmit={resetPassword} className="mt-8 space-y-4">
              {sandbox && (
                <div className="text-xs text-gold/80 bg-gold/10 border border-gold/30 rounded px-2 py-1" data-testid="forgot-sandbox-code">
                  Sandbox OTP: <strong>{sandbox}</strong>
                </div>
              )}
              <input
                type="text"
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="6-digit code"
                className="w-full px-3 py-3 rounded-md bg-black/40 border border-white/10 focus:border-gold outline-none text-sm text-center tracking-widest font-mono"
                data-testid="forgot-code-input"
              />
              <div className="relative">
                <Lock className="w-4 h-4 text-white/40 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  minLength={6}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="New password"
                  className="w-full pl-10 pr-4 py-3 rounded-md bg-black/40 border border-white/10 focus:border-gold outline-none text-sm"
                  data-testid="forgot-newpass-input"
                />
              </div>
              <button className="btn-gold w-full justify-center" disabled={busy} data-testid="forgot-reset-btn">
                {busy ? "Resetting…" : "Set new password"} <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-white/40 mt-6">
          <Link to="/login" className="hover:text-white/70">← Back to sign in</Link>
        </p>
      </motion.div>
    </div>
  );
}
