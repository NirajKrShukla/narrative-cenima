/* Auth context for AiPillu Studio.
 * Handles BOTH:
 *   1. Emergent-managed Google auth (session_id fragment → /api/auth/session)
 *   2. Email/password JWT (/api/auth/register + /api/auth/login → httpOnly cookies)
 *
 * Guests can view the landing page + demos. Everything else requires login.
 */
import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { API } from "./api";

const AuthCtx = createContext(null);

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

export function AuthProvider({ children }) {
  // null = still checking, false = anonymous, object = logged in
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    // Skip the /me probe if we're returning from Google auth — AuthCallback will handle it.
    if (typeof window !== "undefined" && window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    try {
      const { data } = await API.get("/auth/me");
      setUser(data);
    } catch {
      setUser(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { checkAuth(); }, [checkAuth]);

  const login = async ({ email, password }) => {
    const { data } = await API.post("/auth/login", { email, password });
    setUser(data);
    return data;
  };

  const register = async ({ email, password, name }) => {
    const { data } = await API.post("/auth/register", { email, password, name });
    setUser(data);
    return data;
  };

  const logout = async () => {
    try { await API.post("/auth/logout"); } catch { /* ignore */ }
    setUser(false);
  };

  const loginWithGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/auth/callback";
    window.location.href =
      "https://auth.emergentagent.com/?redirect=" + encodeURIComponent(redirectUrl);
  };

  // Called by AuthCallback once the session_id fragment is parsed
  const exchangeEmergentSession = async (sessionId) => {
    const { data } = await API.post("/auth/session", { session_id: sessionId });
    setUser(data);
    return data;
  };

  return (
    <AuthCtx.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        checkAuth,
        login,
        register,
        logout,
        loginWithGoogle,
        exchangeEmergentSession,
      }}
    >
      {children}
    </AuthCtx.Provider>
  );
}

// Best-effort helper: turn arbitrary FastAPI error payloads into a user string.
export function formatApiError(err) {
  const d = err?.response?.data?.detail;
  if (d == null) return err?.message || "Something went wrong. Please try again.";
  if (typeof d === "string") return d;
  if (Array.isArray(d))
    return d.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (d && typeof d.msg === "string") return d.msg;
  return String(d);
}
