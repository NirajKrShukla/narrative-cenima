import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Film, ArrowLeft, Globe, Heart, Play, ShieldCheck, Sparkles } from "lucide-react";
import { API, assetUrl } from "../lib/api";

export default function Gallery() {
  const [films, setFilms] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await API.get("/gallery");
        setFilms(data);
      } catch (e) { /* ignore */ }
      setLoading(false);
    })();
  }, []);

  return (
    <div className="min-h-screen">
      <nav className="fixed top-0 left-0 right-0 z-40 glass">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-white/70 hover:text-white transition" data-testid="gallery-back">
            <ArrowLeft className="w-4 h-4" /><span className="text-sm">Home</span>
          </Link>
          <div className="flex items-center gap-2">
            <Film className="w-5 h-5 text-gold" />
            <span className="font-display text-lg">AiPillu <span className="text-gold">Gallery</span></span>
          </div>
          <Link to="/studio" className="btn-gold text-sm" data-testid="gallery-studio">
            Open Studio
          </Link>
        </div>
      </nav>

      <div className="pt-32 pb-20 max-w-7xl mx-auto px-6">
        <div className="overline mb-3 flex items-center gap-2">
          <Globe className="w-3.5 h-3.5 text-gold" /> Public gallery
        </div>
        <h1 className="font-display text-4xl sm:text-5xl tracking-tighter" data-testid="gallery-title">
          Films the community made.
        </h1>
        <p className="text-white/60 mt-4 max-w-2xl">
          Every film here was crafted by an AiPillu creator — from a scrap of a story to a full short.
          Watch them, tip the creator over UPI, and try your own.
        </p>

        <div className="mt-12">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1,2,3].map((i) => (
                <div key={i} className="shimmer aspect-video rounded-md" />
              ))}
            </div>
          ) : films.length === 0 ? (
            <EmptyGallery />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="gallery-grid">
              {films.map((f) => <FilmCard key={f.id} film={f} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const EmptyGallery = () => (
  <div className="card p-16 text-center" data-testid="gallery-empty">
    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full border border-gold/30 bg-gold/5 mb-6">
      <Sparkles className="w-7 h-7 text-gold" />
    </div>
    <h2 className="font-display text-3xl">The stage is empty.</h2>
    <p className="text-white/60 mt-3 max-w-md mx-auto text-sm">
      Be the first creator to publish a film here. Every film gets its own page,
      tip button, and shareable URL.
    </p>
    <Link to="/studio" className="btn-gold mt-8 inline-flex" data-testid="gallery-empty-cta">
      <Film className="w-4 h-4" /> Make your first film
    </Link>
  </div>
);

const FilmCard = ({ film }) => {
  const poster = film.poster_scene_image ? assetUrl(film.poster_scene_image) : null;
  return (
    <Link to={`/gallery/${film.id}`} className="group block" data-testid={`gallery-card-${film.id}`}>
      <motion.div
        whileHover={{ y: -4 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className="card overflow-hidden"
      >
        <div className="aspect-video bg-black overflow-hidden relative">
          {poster ? (
            <img src={poster} alt={film.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-white/30">
              <Play className="w-8 h-8" />
            </div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent" />
          <div className="absolute bottom-3 left-3 right-3">
            <div className="overline">{film.genre || "Short film"} · {film.scene_count} scenes</div>
          </div>
        </div>
        <div className="p-5">
          <div className="font-display text-xl">{film.title}</div>
          <p className="text-sm text-white/60 mt-1.5 line-clamp-2">{film.logline}</p>
          <div className="flex items-center justify-between mt-4 text-[11px] text-white/40">
            <span>{film.views} views</span>
            {film.tips_total_inr > 0 && (
              <span className="flex items-center gap-1 text-gold">
                <Heart className="w-3 h-3 fill-current" /> ₹{Math.round(film.tips_total_inr)} tipped
              </span>
            )}
          </div>
        </div>
      </motion.div>
    </Link>
  );
};
