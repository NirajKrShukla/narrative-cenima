import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { Gift, Copy, Check, Share2 } from "lucide-react";
import { API } from "../lib/api";

/* Referral card — user's personal code + share buttons + counters.
 * Drop this in Studio's empty state / Pricing page footer. */
export default function ReferralCard() {
  const [data, setData] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    API.get("/referrals/me").then((r) => setData(r.data)).catch(() => {});
  }, []);

  if (!data?.code) return null;

  const shareUrl = `${window.location.origin}/login?ref=${data.code}`;
  const shareText = `I'm making AI films with AiPillu Studio — use my code ${data.code} and we both get +${data.bonus_days_per_referral} days free!`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${shareText}\n${shareUrl}`);
      setCopied(true);
      toast.success("Copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch { toast.error("Copy failed"); }
  };

  const share = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: "AiPillu Studio", text: shareText, url: shareUrl }); } catch {}
    } else { copy(); }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-md border border-fuchsia-500/30 p-5"
      data-testid="referral-card"
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-md bg-fuchsia-500/10 border border-fuchsia-500/30 flex items-center justify-center flex-shrink-0">
          <Gift className="w-5 h-5 text-fuchsia-300" />
        </div>
        <div className="flex-1">
          <div className="font-display text-lg">Invite a friend · earn free days</div>
          <p className="text-white/60 text-sm mt-1">
            Share your code. When they verify, you both get <span className="text-fuchsia-300 font-medium">+{data.bonus_days_per_referral} days</span> added to your license.
          </p>

          <div className="mt-4 flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-2 px-3 py-2 rounded-md border border-white/10 bg-black/40 font-mono text-sm tracking-widest text-fuchsia-200" data-testid="referral-code">
              {data.code}
            </div>
            <button onClick={copy} className="btn-ghost text-sm" data-testid="referral-copy-btn">
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? "Copied" : "Copy"}
            </button>
            <button onClick={share} className="btn-gold text-sm" data-testid="referral-share-btn">
              <Share2 className="w-3.5 h-3.5" /> Share
            </button>
          </div>

          <div className="mt-4 flex gap-4 text-xs text-white/60">
            <div>
              <span className="text-white text-lg font-display">{data.referred_count}</span>
              <span className="ml-1.5">rewarded</span>
            </div>
            <div>
              <span className="text-white/70 text-lg font-display">{data.pending_count}</span>
              <span className="ml-1.5">pending verify</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
