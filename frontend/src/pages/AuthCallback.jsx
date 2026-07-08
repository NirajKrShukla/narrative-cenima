import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { useAuth, formatApiError } from "../lib/auth";

/* Handles the Emergent Google-auth return URL:
 *   /auth/callback#session_id=xxx
 * Exchanges the one-time session_id for a persistent session cookie,
 * then redirects to /studio.
 */
export default function AuthCallback() {
  const navigate = useNavigate();
  const { exchangeEmergentSession } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const hash = window.location.hash || "";
    const m = hash.match(/session_id=([^&]+)/);
    if (!m) {
      toast.error("Missing session id in redirect URL");
      navigate("/login", { replace: true });
      return;
    }
    const sessionId = decodeURIComponent(m[1]);

    (async () => {
      try {
        const user = await exchangeEmergentSession(sessionId);
        toast.success(`Welcome, ${user?.name || user?.email || ""}!`);
        // Strip the hash so a refresh doesn't try to re-exchange
        window.history.replaceState({}, document.title, "/studio");
        navigate("/studio", { replace: true });
      } catch (err) {
        toast.error(formatApiError(err));
        navigate("/login", { replace: true });
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center gap-4" data-testid="auth-callback-loader">
        <Loader2 className="w-8 h-8 text-gold animate-spin" />
        <div className="text-white/60 text-sm">Signing you in…</div>
      </div>
    </div>
  );
}
