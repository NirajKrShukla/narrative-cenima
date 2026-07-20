/* License hook — surfaces the user's current license, verification state
 * and plan-purchase actions. Uses React Query-style lazy fetching. */
import { useCallback, useEffect, useState } from "react";
import { API } from "./api";
import { useAuth } from "./auth";

const empty = {
  license: null,
  trial_used: false,
  can_start_trial: false,
  verifications: { email_verified: false, phone_verified: false },
  can_create_films: false,
  plans: [],
};

export function useLicense() {
  const { isAuthenticated } = useAuth();
  const [data, setData] = useState(empty);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      if (isAuthenticated) {
        const { data: d } = await API.get("/licenses/status");
        setData(d);
      } else {
        // Guest: public pricing only — hydrate plans list from /plans endpoint
        const { data: d } = await API.get("/licenses/plans");
        setData({ ...empty, plans: d.plans || [] });
      }
    } catch {
      setData(empty);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => { refresh(); }, [refresh]);

  const startTrial = async () => {
    const { data: d } = await API.post("/licenses/start-trial");
    await refresh();
    return d;
  };

  const checkout = async (planId) => {
    const { data: d } = await API.post("/licenses/checkout", { plan_id: planId });
    return d;
  };

  const sandboxComplete = async (planId) => {
    const { data: d } = await API.post("/licenses/checkout/sandbox-complete", { plan_id: planId });
    await refresh();
    return d;
  };

  const verifyPayment = async (payload) => {
    const { data: d } = await API.post("/licenses/checkout/verify", payload);
    await refresh();
    return d;
  };

  const sendOtp = async (channel, identifier) => {
    const { data: d } = await API.post("/otp/send", { channel, identifier });
    return d;
  };

  const verifyOtp = async (channel, identifier, code) => {
    const { data: d } = await API.post("/otp/verify", { channel, identifier, code });
    await refresh();
    return d;
  };

  return {
    ...data,
    loading,
    refresh,
    startTrial,
    checkout,
    sandboxComplete,
    verifyPayment,
    sendOtp,
    verifyOtp,
  };
}
