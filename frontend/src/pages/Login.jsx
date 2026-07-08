import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Film, Mail, Lock, User, Sparkles, ArrowRight } from "lucide-react";
import { useAuth, formatApiError } from "../lib/auth";

export default function Login() {
  const { login, register, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from || "/studio";

  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!email || !password) { setError("Email and password are required"); return; }
    setBusy(true);
    try {
      if (mode === "login") {
        await login({ email, password });
        toast.success("Welcome back!");
      } else {
        await register({ email, password, name });
        toast.success("Account created — you're in!");
      }
      navigate(from, { replace: true });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-16 px-6 relative overflow-hidden">
      {/* Ambient background — matches landing page aesthetic */}
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-black via-black to-[#0d0a05]" />
      <div className="absolute top-1/4 left-1/4 w-[520px] h-[520px] -z-10 rounded-full bg-gold/10 blur-[140px]" />
      <div className="absolute bottom-1/4 right-1/4 w-[420px] h-[420px] -z-10 rounded-full bg-rose-900/20 blur-[120px]" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md relative"
      >
        {/* Card */}
        <div className="glass rounded-lg p-8 border border-white/10 shadow-2xl">
          <Link to="/" className="flex items-center gap-2 mb-8 group" data-testid="login-logo">
            <Film className="w-5 h-5 text-gold group-hover:rotate-12 transition-transform" />
            <span className="font-display text-lg tracking-tight">
              AiPillu <span className="text-gold">Studio</span>
            </span>
          </Link>

          <div className="overline mb-3 flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-gold" />
            {mode === "login" ? "Welcome back" : "Create your account"}
          </div>
          <h1 className="font-display text-3xl tracking-tight leading-tight">
            {mode === "login" ? (
              <>Sign in to <span className="text-gold italic">continue</span>.</>
            ) : (
              <>Start telling your <span className="text-gold italic">stories</span>.</>
            )}
          </h1>
          <p className="text-white/50 text-sm mt-3">
            {mode === "login"
              ? "Guests can watch demos. Downloading or sharing your film requires an account."
              : "Free to create. Your first ≤20 MB film is free."}
          </p>

          {/* Google button (primary) */}
          <button
            type="button"
            onClick={loginWithGoogle}
            disabled={busy}
            className="mt-8 w-full flex items-center justify-center gap-3 py-3 px-4 rounded-md bg-white text-black font-medium hover:bg-white/90 transition disabled:opacity-60"
            data-testid="login-google-btn"
          >
            <svg width="18" height="18" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>

          <div className="my-6 flex items-center gap-4 text-xs text-white/40">
            <div className="flex-1 h-px bg-white/10" />
            or with email
            <div className="flex-1 h-px bg-white/10" />
          </div>

          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <div className="relative">
                <User className="w-4 h-4 text-white/40 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Your name (optional)"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 rounded-md bg-black/40 border border-white/10 focus:border-gold outline-none text-sm"
                  data-testid="login-name-input"
                />
              </div>
            )}
            <div className="relative">
              <Mail className="w-4 h-4 text-white/40 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                placeholder="you@studio.com"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-3 rounded-md bg-black/40 border border-white/10 focus:border-gold outline-none text-sm"
                data-testid="login-email-input"
              />
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-white/40 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                placeholder="Password (min 6 chars)"
                required
                minLength={6}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-3 rounded-md bg-black/40 border border-white/10 focus:border-gold outline-none text-sm"
                data-testid="login-password-input"
              />
            </div>

            {error && (
              <div className="text-sm text-rose-400 bg-rose-500/10 border border-rose-500/30 rounded-md px-3 py-2" data-testid="login-error">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={busy}
              className="btn-gold w-full justify-center"
              data-testid="login-submit-btn"
            >
              {busy ? "Please wait…" : (mode === "login" ? "Sign in" : "Create account")}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-white/60">
            {mode === "login" ? (
              <>
                New here?{" "}
                <button
                  type="button"
                  className="text-gold hover:underline"
                  onClick={() => { setMode("register"); setError(""); }}
                  data-testid="login-switch-register"
                >
                  Create an account
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  className="text-gold hover:underline"
                  onClick={() => { setMode("login"); setError(""); }}
                  data-testid="login-switch-login"
                >
                  Sign in
                </button>
              </>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-white/40 mt-6">
          <Link to="/" className="hover:text-white/70" data-testid="login-back-home">
            ← Back to homepage & demos
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
