import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Film, Sparkles, FileText, Mic, Link2, PlayCircle, ShieldCheck, Wand2, Play } from "lucide-react";

const HERO_BG =
  "https://images.pexels.com/photos/18415806/pexels-photo-18415806.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";
const PROJECTOR_IMG =
  "https://images.unsplash.com/photo-1763748998933-7e09e6504529?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1ODh8MHwxfHNlYXJjaHwzfHxjaW5lbWF0aWMlMjBmaWxtJTIwcHJvamVjdG9yfGVufDB8fHx8MTc4MzM1NTUwMXww&ixlib=rb-4.1.0&q=85";
const WARRIOR_IMG =
  "https://images.pexels.com/photos/10068860/pexels-photo-10068860.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

const stagger = { animate: { transition: { staggerChildren: 0.08 } } };
const item = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } },
};

const inputs = [
  { icon: FileText, label: "PDF, DOCX, TXT", note: "Screenplays, manuscripts" },
  { icon: Link2, label: "Any Web URL", note: "Blog posts, articles" },
  { icon: Mic, label: "Voice Recording", note: "Narrate your idea" },
  { icon: Wand2, label: "Pasted Script", note: "Type or paste directly" },
];

// A single demo-video tile with hover autoplay and click-to-fullscreen
function DemoTile({ src, title, caption, testid }) {
  const ref = React.useRef(null);
  const [playing, setPlaying] = React.useState(false);

  const onEnter = () => {
    const v = ref.current;
    if (!v) return;
    v.play().then(() => setPlaying(true)).catch(() => {});
  };
  const onLeave = () => {
    const v = ref.current;
    if (!v) return;
    v.pause();
    setPlaying(false);
  };
  const onClick = () => {
    const v = ref.current;
    if (!v) return;
    if (v.requestFullscreen) v.requestFullscreen();
    v.muted = false;
    v.currentTime = 0;
    v.play().catch(() => {});
  };

  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
      className="group relative rounded-lg overflow-hidden border border-white/10 bg-black cursor-pointer"
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      onClick={onClick}
      data-testid={testid}
    >
      <div className="aspect-video bg-black relative">
        <video
          ref={ref}
          src={src}
          muted
          loop
          playsInline
          preload="auto"
          className="w-full h-full object-cover"
          data-testid={`${testid}-video`}
        />
        {!playing && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-16 h-16 rounded-full bg-gold/90 flex items-center justify-center shadow-goldGlow transition-transform group-hover:scale-110">
              <Play className="w-6 h-6 text-black fill-current ml-1" />
            </div>
          </div>
        )}
        <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black to-transparent pointer-events-none" />
      </div>
      <div className="p-5 border-t border-white/5">
        <div className="font-display text-xl">{title}</div>
        <p className="text-sm text-white/60 mt-1.5">{caption}</p>
      </div>
    </motion.div>
  );
}

export default function Landing() {  return (
    <div className="relative overflow-x-hidden">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-40 glass" data-testid="nav-header">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group" data-testid="nav-logo">
            <Film className="w-5 h-5 text-gold group-hover:rotate-12 transition-transform" />
            <span className="font-display text-lg tracking-tight">
              AiPillu <span className="text-gold">Studio</span>
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm text-white/70">
            <a href="#demo" className="hover:text-white transition" data-testid="nav-demo">Watch demo</a>
            <a href="#how" className="hover:text-white transition" data-testid="nav-how">How it works</a>
            <a href="#inputs" className="hover:text-white transition" data-testid="nav-inputs">Inputs</a>
            <a href="#safety" className="hover:text-white transition" data-testid="nav-safety">Safety</a>
            <Link to="/gallery" className="hover:text-white transition" data-testid="nav-gallery">Gallery</Link>
          </div>
          <Link to="/studio" className="btn-gold text-sm" data-testid="nav-open-studio">
            Open Studio <PlayCircle className="w-4 h-4" />
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-40 pb-24 min-h-[92vh] flex items-center">
        <div
          className="absolute inset-0 -z-10 bg-cover bg-center"
          style={{ backgroundImage: `url(${HERO_BG})` }}
        />
        <div className="absolute inset-0 -z-10 bg-black/70" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-transparent via-black/40 to-black" />

        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-10 items-center relative">
          <motion.div initial="initial" animate="animate" variants={stagger} className="lg:col-span-8">
            <motion.div variants={item} className="overline mb-6 flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-gold" />
              An original short film — from any story, any language
            </motion.div>
            <motion.h1
              variants={item}
              className="font-display font-light tracking-tighter text-5xl sm:text-6xl lg:text-7xl leading-[1.05]"
              data-testid="hero-title"
            >
              Every story
              <br />
              deserves a <span className="text-gold italic font-normal">screen</span>.
            </motion.h1>
            <motion.p variants={item} className="mt-8 max-w-2xl text-lg text-white/70 leading-relaxed">
              Drop a PDF, paste a script, share a URL, or narrate aloud —
              AiPillu turns it into a cinematic short with original characters,
              scene-by-scene direction, voice narration and a downloadable film.
            </motion.p>
            <motion.div variants={item} className="mt-10 flex flex-wrap gap-4">
              <Link to="/studio" className="btn-gold" data-testid="hero-start">
                <Film className="w-4 h-4" /> Start creating
              </Link>
              <a href="#how" className="btn-ghost" data-testid="hero-learn">
                See how it works
              </a>
            </motion.div>
            <motion.div variants={item} className="mt-12 grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-2xl">
              {inputs.map((it) => (
                <div key={it.label} className="glass rounded-md p-4">
                  <it.icon className="w-4 h-4 text-gold mb-2" />
                  <div className="text-sm font-medium">{it.label}</div>
                  <div className="text-xs text-white/50 mt-1">{it.note}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0, transition: { duration: 0.8, delay: 0.3 } }}
            className="lg:col-span-4 hidden lg:block"
          >
            <div className="relative">
              <div className="absolute -inset-3 rounded-lg bg-gradient-to-tr from-gold/30 to-transparent blur-2xl -z-10" />
              <img
                src={WARRIOR_IMG}
                alt="Ancient warrior"
                className="w-full h-[520px] object-cover rounded-md border border-white/10"
              />
              <div className="absolute bottom-4 left-4 right-4 glass rounded p-3">
                <div className="overline">Original design</div>
                <div className="text-sm mt-1">All characters are AI-generated — never derivative.</div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="overline mb-4">The pipeline</div>
          <h2 className="font-display text-4xl sm:text-5xl tracking-tight max-w-3xl leading-tight">
            From your idea to the final cut — <span className="text-gold">in six steps</span>.
          </h2>

          <div className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { n: "01", t: "Ingest", d: "Upload PDF/DOCX, paste a script, share a URL, or record your voice — we extract the story." },
              { n: "02", t: "Analyze", d: "A director-grade LLM breaks the story into 4-8 cinematic scenes with mood, camera and blocking." },
              { n: "03", t: "Cast", d: "Original characters are conceived — never copied from any film or franchise." },
              { n: "04", t: "Storyboard", d: "Cinematic stills are painted for each scene with a consistent visual grammar." },
              { n: "05", t: "Animate", d: "Sora 2 or Ken-Burns motion brings the frames to life with camera moves." },
              { n: "06", t: "Assemble", d: "Narration, subtitles and scene clips are stitched into your downloadable film." },
            ].map((s) => (
              <div key={s.n} className="card p-6 hover:border-white/20 transition group">
                <div className="text-gold font-mono text-xs">{s.n}</div>
                <div className="font-display text-2xl mt-2">{s.t}</div>
                <p className="text-sm text-white/60 mt-3 leading-relaxed">{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Demo videos */}
      <section id="demo" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="overline mb-4 flex items-center gap-2">
            <Play className="w-3.5 h-3.5 text-gold" /> See it in action
          </div>
          <h2 className="font-display text-4xl sm:text-5xl tracking-tight max-w-3xl leading-tight">
            Two short demos — <span className="text-gold">one for the mood</span>, one for the process.
          </h2>
          <p className="text-white/60 mt-4 max-w-2xl">
            Both are less than 20 seconds. Autoplays on hover, loops silently, and works on every phone.
          </p>

          <div className="mt-14 grid grid-cols-1 lg:grid-cols-2 gap-8">
            <DemoTile
              testid="demo-showcase"
              title="The Showreel"
              caption="A cinematic teaser for the studio's soul — every story, every language, one screen."
              src={`${process.env.REACT_APP_BACKEND_URL}/api/storage/demo_showcase.mp4`}
            />
            <DemoTile
              testid="demo-workflow"
              title="Six Steps to a Film"
              caption="Ingest → analyze → cast → animate → narrate → share. All auto-piloted."
              src={`${process.env.REACT_APP_BACKEND_URL}/api/storage/demo_workflow.mp4`}
            />
          </div>

          <div className="mt-10 text-center">
            <Link to="/studio" className="btn-gold" data-testid="demo-cta">
              <Film className="w-4 h-4" /> Make your own — start free
            </Link>
          </div>
        </div>
      </section>

      {/* Inputs strip */}
      <section id="inputs" className="py-24 bg-black/40 border-y border-white/5 relative">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-5">
            <img src={PROJECTOR_IMG} alt="Projector" className="w-full h-80 object-cover rounded-md border border-white/10" />
          </div>
          <div className="lg:col-span-7">
            <div className="overline">Any source</div>
            <h3 className="font-display text-3xl sm:text-4xl mt-3 leading-tight">
              Ramayan, Mahabharat, your grandmother&apos;s tale, or a
              <span className="text-gold"> half-written idea</span> — AiPillu reads them all.
            </h3>
            <p className="mt-5 text-white/60 max-w-xl">
              Give it the raw material; get back a scene-by-scene short film with narration in <span className="text-gold">100+ world languages</span>.
              Hindi, Sanskrit, Tamil, Arabic, Mandarin, Swahili, Spanish, English — the narrator speaks any of them.
            </p>
          </div>
        </div>
      </section>

      {/* Safety */}
      <section id="safety" className="py-24">
        <div className="max-w-5xl mx-auto px-6">
          <div className="glass rounded-md p-10">
            <div className="flex items-start gap-6">
              <div className="p-3 rounded-md border border-gold/30 bg-gold/5">
                <ShieldCheck className="w-6 h-6 text-gold" />
              </div>
              <div>
                <div className="overline mb-2">Copyright-safe by design</div>
                <h4 className="font-display text-3xl leading-tight">
                  Original characters, original visuals, always.
                </h4>
                <p className="text-white/60 mt-4 max-w-2xl leading-relaxed">
                  AiPillu&apos;s director model rewrites well-known figures into inspired-but-original creations —
                  new names, new attire, new silhouettes — so nothing you generate steps on protected IP.
                  No living celebrities. No franchise designs. No hidden logos.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24">
        <div className="max-w-4xl mx-auto text-center px-6">
          <h2 className="font-display text-4xl sm:text-6xl tracking-tighter leading-[1.05]">
            Roll the <span className="text-gold italic">first cut</span>.
          </h2>
          <p className="text-white/60 mt-6 max-w-xl mx-auto">
            Your idea → a director-approved short film, in minutes.
          </p>
          <div className="mt-10">
            <Link to="/studio" className="btn-gold" data-testid="cta-open-studio">
              <Film className="w-4 h-4" /> Enter the studio
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/5 py-8 text-center text-xs text-white/40">
        AiPillu Studio · Story-to-Film AI Agent
      </footer>
    </div>
  );
}
