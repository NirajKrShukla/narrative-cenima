import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Film, Mail, Phone, Check, Loader2, ShieldCheck, ArrowRight } from "lucide-react";
import { useAuth, formatApiError } from "../lib/auth";
import { useLicense } from "../lib/license";

/* Two-step OTP verification page (email + mobile). Ships in SANDBOX mode:
 * the backend returns the OTP in the /send response so we can auto-fill the
 * input during preview testing. In production this field is absent and the
 * user has to type the code they receive by SMS/email. */
export default function VerifyIdentity() {
  const nav = useNavigate();
  const { user, checkAuth } = useAuth();
  const { verifications, sendOtp, verifyOtp, refresh } = useLicense();

  const [emailInput, setEmailInput] = useState(user?.email || "");
  const [phoneInput, setPhoneInput] = useState(user?.phone || "");
  const [emailStage, setEmailStage] = useState("send"); // send | code | done
  const [phoneStage, setPhoneStage] = useState("send");
  const [emailCode, setEmailCode] = useState("");
  const [phoneCode, setPhoneCode] = useState("");
  const [sandboxEmail, setSandboxEmail] = useState("");
  const [sandboxPhone, setSandboxPhone] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    if (verifications.email_verified) setEmailStage("done");
    if (verifications.phone_verified) setPhoneStage("done");
    if (user?.phone) setPhoneInput(user.phone);
  }, [verifications, user]);

  useEffect(() => {
    if (verifications.email_verified && verifications.phone_verified) {
      // Redirect after both verified
      setTimeout(() => nav("/pricing", { replace: true }), 800);
    }
  }, [verifications, nav]);

  const sendEmailCode = async () => {
    setBusy("email-send");
    try {
      const r = await sendOtp("email", emailInput);
      if (r.sandbox_code) {
        setSandboxEmail(r.sandbox_code);
        setEmailCode(r.sandbox_code); // auto-fill for sandbox testing
      }
      setEmailStage("code");
      toast.success(r.sandbox_code ? `Sandbox OTP: ${r.sandbox_code}` : "Email OTP sent");
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(""); }
  };

  const verifyEmailCode = async () => {
    setBusy("email-verify");
    try {
      await verifyOtp("email", emailInput, emailCode);
      setEmailStage("done");
      toast.success("Email verified");
      await refresh();
      await checkAuth();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(""); }
  };

  const sendPhoneCode = async () => {
    setBusy("phone-send");
    try {
      const r = await sendOtp("phone", phoneInput);
      if (r.sandbox_code) {
        setSandboxPhone(r.sandbox_code);
        setPhoneCode(r.sandbox_code);
      }
      setPhoneStage("code");
      toast.success(r.sandbox_code ? `Sandbox OTP: ${r.sandbox_code}` : "SMS OTP sent");
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(""); }
  };

  const verifyPhoneCode = async () => {
    setBusy("phone-verify");
    try {
      await verifyOtp("phone", phoneInput, phoneCode);
      setPhoneStage("done");
      toast.success("Mobile verified");
      await refresh();
      await checkAuth();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(""); }
  };

  const bothDone = emailStage === "done" && phoneStage === "done";

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-lg"
      >
        <Link to="/" className="flex items-center gap-2 mb-8 group">
          <Film className="w-5 h-5 text-gold group-hover:rotate-12 transition-transform" />
          <span className="font-display text-lg tracking-tight">AiPillu <span className="text-gold">Studio</span></span>
        </Link>

        <div className="glass rounded-lg p-8 border border-white/10" data-testid="verify-card">
          <div className="overline mb-3 flex items-center gap-2 text-white/60">
            <ShieldCheck className="w-3.5 h-3.5 text-gold" /> Verify identity
          </div>
          <h1 className="font-display text-3xl leading-tight">
            Two quick checks. <span className="italic text-gold">Then you're in.</span>
          </h1>
          <p className="text-white/60 text-sm mt-3">
            One-time verification protects your free trial from abuse and secures your license.
          </p>

          {/* Email row */}
          <VerifyRow
            testid="verify-email"
            icon={<Mail className="w-4 h-4" />}
            label="Email address"
            input={emailInput}
            setInput={setEmailInput}
            stage={emailStage}
            code={emailCode}
            setCode={setEmailCode}
            sandbox={sandboxEmail}
            busySend={busy === "email-send"}
            busyVerify={busy === "email-verify"}
            onSend={sendEmailCode}
            onVerify={verifyEmailCode}
            placeholder="you@studio.com"
            inputType="email"
            disabled={!!user?.email}
          />

          {/* Phone row */}
          <VerifyRow
            testid="verify-phone"
            icon={<Phone className="w-4 h-4" />}
            label="Mobile number (with +country code)"
            input={phoneInput}
            setInput={setPhoneInput}
            stage={phoneStage}
            code={phoneCode}
            setCode={setPhoneCode}
            sandbox={sandboxPhone}
            busySend={busy === "phone-send"}
            busyVerify={busy === "phone-verify"}
            onSend={sendPhoneCode}
            onVerify={verifyPhoneCode}
            placeholder="+919876543210"
            inputType="tel"
          />

          {bothDone && (
            <div className="mt-8" data-testid="verify-both-done">
              <div className="text-emerald-300 text-sm mb-3 flex items-center gap-2">
                <Check className="w-4 h-4" /> Both channels verified.
              </div>
              <Link to="/pricing" className="btn-gold w-full justify-center" data-testid="verify-continue-btn">
                Continue to pricing <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

function VerifyRow({
  testid, icon, label, input, setInput, stage, code, setCode, sandbox,
  busySend, busyVerify, onSend, onVerify, placeholder, inputType, disabled,
}) {
  const done = stage === "done";
  return (
    <div className={`mt-6 rounded-md border p-4 ${done ? "border-emerald-500/40 bg-emerald-500/5" : "border-white/10 bg-black/30"}`} data-testid={testid}>
      <label className="text-xs text-white/50 flex items-center gap-2 mb-2">{icon} {label}</label>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={placeholder}
        type={inputType}
        disabled={disabled || stage !== "send"}
        className="w-full px-3 py-2.5 rounded-md bg-black/40 border border-white/10 focus:border-gold outline-none text-sm disabled:opacity-70"
        data-testid={`${testid}-input`}
      />

      {stage === "send" && (
        <button
          className="btn-ghost mt-3 text-sm"
          disabled={busySend || !input}
          onClick={onSend}
          data-testid={`${testid}-send-btn`}
        >
          {busySend && <Loader2 className="w-3 h-3 animate-spin" />}
          Send code
        </button>
      )}

      {stage === "code" && (
        <div className="mt-3 space-y-2">
          {sandbox && (
            <div className="text-xs text-gold/80 bg-gold/10 border border-gold/30 rounded px-2 py-1" data-testid={`${testid}-sandbox-code`}>
              Sandbox OTP: <strong>{sandbox}</strong>
            </div>
          )}
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="6-digit code"
            className="w-full px-3 py-2.5 rounded-md bg-black/40 border border-white/10 focus:border-gold outline-none text-sm tracking-widest text-center font-mono"
            data-testid={`${testid}-code-input`}
          />
          <button
            className="btn-gold text-sm"
            disabled={busyVerify || code.length < 4}
            onClick={onVerify}
            data-testid={`${testid}-verify-btn`}
          >
            {busyVerify && <Loader2 className="w-3 h-3 animate-spin" />}
            Verify
          </button>
        </div>
      )}

      {done && (
        <div className="mt-2 text-emerald-300 text-sm flex items-center gap-2" data-testid={`${testid}-done`}>
          <Check className="w-4 h-4" /> Verified · {input}
        </div>
      )}
    </div>
  );
}
