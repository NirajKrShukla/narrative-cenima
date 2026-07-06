import React, { useEffect, useState, useCallback } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  ArrowLeft, Film, Heart, IndianRupee, ShieldCheck, Loader2, Share2,
  Copy, Check, MessageCircle, Twitter, Facebook, Send, Linkedin, Play, Sparkles,
} from "lucide-react";
import { API, assetUrl } from "../lib/api";

const TIP_AMOUNTS = [49, 99, 199, 499];

const getUserId = () => {
  let uid = localStorage.getItem("aipillu_uid");
  if (!uid) {
    uid = "u_" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
    localStorage.setItem("aipillu_uid", uid);
  }
  return uid;
};

export default function GalleryItem() {
  const { projectId } = useParams();
  const [film, setFilm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tipAmount, setTipAmount] = useState(49);
  const [message, setMessage] = useState("");
  const [tipping, setTipping] = useState(false);
  const [polling, setPolling] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await API.get(`/gallery/${projectId}`);
      setFilm(data);
    } catch (e) {
      toast.error("Film not found or not public");
    } finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const sid = searchParams.get("tip_session_id");
    if (sid && searchParams.get("tipped") === "1") {
      pollTip(sid);
    }
  }, []);

  const pollTip = async (sid, attempts = 0) => {
    if (attempts >= 12) { setPolling(false); toast.warning("Tip status check timed out"); return; }
    setPolling(true);
    try {
      const { data } = await API.get(`/tip/status/${sid}`);
      if (data.payment_status === "paid") {
        toast.success("Thank you! Tip sent to the creator ❤");
        setPolling(false);
        setSearchParams({});
        await load();
        return;
      }
      if (data.status === "expired") { setPolling(false); toast.error("Tip session expired"); return; }
      setTimeout(() => pollTip(sid, attempts + 1), 2500);
    } catch {
      setPolling(false); toast.error("Status check failed");
    }
  };

  const sendTip = async () => {
    setTipping(true);
    try {
      const { data } = await API.post(`/gallery/${projectId}/tip`, {
        amount_inr: tipAmount,
        origin_url: window.location.origin,
        user_id: getUserId(),
        message,
      });
      if (data.url) window.location.href = data.url;
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Tip failed");
    } finally { setTipping(false); }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-gold" />
      </div>
    );
  }
  if (!film) return null;

  const filmUrl = `${process.env.REACT_APP_BACKEND_URL}/api/gallery/${projectId}/stream`;
  const pageUrl = window.location.origin + `/gallery/${projectId}`;
  const shareText = encodeURIComponent(`Watch "${film.title}" — an original AI short film on AiPillu Studio`);
  const shareUrl = encodeURIComponent(pageUrl);

  const targets = [
    { key: "whatsapp", label: "WhatsApp", icon: MessageCircle, url: `https://wa.me/?text=${shareText}%20${shareUrl}` },
    { key: "twitter", label: "Twitter", icon: Twitter, url: `https://twitter.com/intent/tweet?text=${shareText}&url=${shareUrl}` },
    { key: "facebook", label: "Facebook", icon: Facebook, url: `https://www.facebook.com/sharer/sharer.php?u=${shareUrl}` },
    { key: "telegram", label: "Telegram", icon: Send, url: `https://t.me/share/url?url=${shareUrl}&text=${shareText}` },
    { key: "linkedin", label: "LinkedIn", icon: Linkedin, url: `https://www.linkedin.com/sharing/share-offsite/?url=${shareUrl}` },
  ];

  const copyLink = async () => {
    await navigator.clipboard.writeText(pageUrl);
    setCopied(true); setTimeout(() => setCopied(false), 2000);
    toast.success("Link copied");
  };

  return (
    <div className="min-h-screen">
      <nav className="fixed top-0 left-0 right-0 z-40 glass">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/gallery" className="flex items-center gap-2 text-white/70 hover:text-white transition" data-testid="film-back">
            <ArrowLeft className="w-4 h-4" /><span className="text-sm">Gallery</span>
          </Link>
          <Link to="/studio" className="btn-ghost text-sm" data-testid="film-open-studio">
            <Film className="w-3.5 h-3.5" /> Make your own
          </Link>
        </div>
      </nav>

      <div className="pt-24 pb-20 max-w-6xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <div className="aspect-video bg-black rounded-md overflow-hidden border border-white/10">
            <video src={filmUrl} controls className="w-full h-full" data-testid="film-player" />
          </div>

          <div className="mt-6">
            <div className="overline">{film.genre || "Short film"} · {film.views} views</div>
            <h1 className="font-display text-3xl sm:text-4xl mt-2" data-testid="film-title">{film.title}</h1>
            <p className="text-white/60 mt-3 max-w-2xl italic">&ldquo;{film.logline}&rdquo;</p>
          </div>

          {/* Share row */}
          <div className="mt-8">
            <div className="overline mb-3 flex items-center gap-2"><Share2 className="w-3.5 h-3.5 text-gold" /> Share this film</div>
            <div className="flex flex-wrap gap-2">
              {targets.map((t) => (
                <a key={t.key} href={t.url} target="_blank" rel="noreferrer"
                   className="px-3 py-2 rounded-md border border-white/10 hover:border-gold/40 hover:bg-white/5 transition text-sm flex items-center gap-2"
                   data-testid={`film-share-${t.key}`}
                >
                  <t.icon className="w-3.5 h-3.5" /> {t.label}
                </a>
              ))}
              <button onClick={copyLink} className="px-3 py-2 rounded-md border border-white/10 hover:border-gold/40 hover:bg-white/5 transition text-sm flex items-center gap-2" data-testid="film-copy-link">
                {copied ? <Check className="w-3.5 h-3.5 text-gold" /> : <Copy className="w-3.5 h-3.5" />} {copied ? "Copied" : "Copy link"}
              </button>
            </div>
          </div>
        </div>

        {/* Tip creator */}
        <div className="lg:col-span-1">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card p-6 sticky top-24">
            <div className="flex items-center gap-2 mb-4">
              <Heart className="w-5 h-5 text-gold fill-gold/20" />
              <div className="font-display text-2xl">Tip the creator</div>
            </div>
            <p className="text-sm text-white/60 mb-5">
              Send a UPI/Card tip. The creator receives 100% of the tip — this is on top of any unlock fees.
              {film.tip_vpa && (
                <span className="block mt-2 font-mono text-[11px] text-gold">UPI: {film.tip_vpa}</span>
              )}
            </p>

            <div className="grid grid-cols-4 gap-2 mb-4">
              {TIP_AMOUNTS.map((a) => (
                <button
                  key={a}
                  onClick={() => setTipAmount(a)}
                  className={`p-2 rounded-md border text-sm ${tipAmount === a ? "border-gold/60 bg-gold/10 text-gold" : "border-white/10 hover:border-white/25"}`}
                  data-testid={`tip-amount-${a}`}
                >
                  ₹{a}
                </button>
              ))}
            </div>
            <div className="mb-4">
              <label className="overline">Custom amount (₹)</label>
              <input
                type="number" min={49} max={10000}
                className="input-field mt-2"
                value={tipAmount}
                onChange={(e) => setTipAmount(parseInt(e.target.value) || 49)}
                data-testid="tip-custom"
              />
            </div>
            <div className="mb-5">
              <label className="overline">Message (optional)</label>
              <input
                className="input-field mt-2"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Loved it!"
                data-testid="tip-message"
              />
            </div>

            <button className="btn-gold w-full justify-center" onClick={sendTip} disabled={tipping || polling} data-testid="tip-send">
              {(tipping || polling) ? <Loader2 className="w-4 h-4 animate-spin" /> : <IndianRupee className="w-4 h-4" />}
              {polling ? "Verifying tip…" : `Send ₹${tipAmount}`}
            </button>
            <div className="mt-3 text-[11px] text-white/40 text-center flex items-center justify-center gap-1">
              <ShieldCheck className="w-3 h-3 text-gold" /> Secure UPI &amp; Card · via Stripe
            </div>

            {film.tips_total_inr > 0 && (
              <div className="mt-5 p-3 rounded border border-gold/20 bg-gold/5 text-center">
                <div className="text-xs text-white/50">Total tipped so far</div>
                <div className="font-display text-2xl text-gold mt-1">₹{Math.round(film.tips_total_inr)}</div>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
