import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  Film, Plus, Trash2, FileText, Link2, Mic, Wand2, Sparkles, Users,
  Image as ImageIcon, Video, Volume2, Layers, Download, Loader2, ChevronRight,
  ArrowLeft, Play, ShieldCheck, RefreshCw, Zap, Lock, Share2, IndianRupee,
  Copy, Check, MessageCircle, Twitter, Facebook, Send, Linkedin, Youtube, Instagram,
} from "lucide-react";
import { API, assetUrl } from "../lib/api";

// --------- Anonymous user id (localStorage) ----------
const getUserId = () => {
  let uid = localStorage.getItem("aipillu_uid");
  if (!uid) {
    uid = "u_" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
    localStorage.setItem("aipillu_uid", uid);
  }
  return uid;
};

// -------- Small UI helpers --------
const Spinner = ({ className = "w-4 h-4" }) => <Loader2 className={`animate-spin ${className}`} />;

const Pill = ({ tone = "neutral", children }) => (
  <span className={`pill pill-${tone}`}>{children}</span>
);

const Section = ({ title, icon: Icon, right, children, testid }) => (
  <div className="card p-6" data-testid={testid}>
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="w-4 h-4 text-gold" />}
        <div className="font-display text-lg tracking-tight">{title}</div>
      </div>
      {right}
    </div>
    {children}
  </div>
);

// -------- Studio Page --------
export default function Studio() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("ingest"); // ingest, analyze, characters, scenes, assemble

  const refreshProjects = useCallback(async () => {
    try {
      const { data } = await API.get("/projects");
      setProjects(data);
    } catch (e) {
      console.error(e);
    }
  }, []);

  const loadProject = useCallback(async (pid) => {
    if (!pid) { setProject(null); return; }
    setLoading(true);
    try {
      const { data } = await API.get(`/projects/${pid}`);
      setProject(data);
      // Auto move to next relevant tab based on state
      if (data.blueprint && activeTab === "ingest") setActiveTab("characters");
    } catch (e) {
      toast.error("Could not load project");
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => { refreshProjects(); }, [refreshProjects]);
  useEffect(() => { loadProject(projectId); }, [projectId, loadProject]);

  const createProject = async () => {
    try {
      const { data } = await API.post("/projects", { title: "Untitled Film" });
      await refreshProjects();
      navigate(`/studio/${data.id}`);
      setActiveTab("ingest");
      toast.success("New project created");
    } catch (e) {
      toast.error("Failed to create project");
    }
  };

  const deleteProject = async (pid) => {
    if (!window.confirm("Delete this project?")) return;
    try {
      await API.delete(`/projects/${pid}`);
      toast.success("Deleted");
      await refreshProjects();
      if (projectId === pid) navigate("/studio");
    } catch { toast.error("Delete failed"); }
  };

  return (
    <div className="min-h-screen">
      {/* Top bar */}
      <div className="glass sticky top-0 z-30" data-testid="studio-topbar">
        <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-2 text-white/70 hover:text-white transition" data-testid="back-home">
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Home</span>
            </Link>
            <div className="h-6 w-px bg-white/10 mx-2" />
            <div className="flex items-center gap-2">
              <Film className="w-5 h-5 text-gold" />
              <span className="font-display text-lg tracking-tight">
                AiPillu <span className="text-gold">Studio</span>
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-1 text-xs text-white/50">
              <ShieldCheck className="w-3.5 h-3.5 text-gold" /> Copyright-safe pipeline
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-[1600px] mx-auto px-6 py-8 grid grid-cols-12 gap-6">
        {/* Sidebar */}
        <aside className="col-span-12 lg:col-span-3 xl:col-span-2">
          <div className="card p-4">
            <button className="btn-gold w-full justify-center" onClick={createProject} data-testid="new-project-btn">
              <Plus className="w-4 h-4" /> New project
            </button>
          </div>
          <div className="mt-4 card p-3" data-testid="project-list">
            <div className="overline px-2 py-1">Projects</div>
            {projects.length === 0 && (
              <div className="text-xs text-white/40 px-2 py-4">No projects yet.</div>
            )}
            <div className="space-y-1 max-h-[70vh] overflow-y-auto">
              {projects.map((p) => (
                <div
                  key={p.id}
                  className={`group flex items-center justify-between gap-2 px-2 py-2 rounded-md cursor-pointer transition ${
                    projectId === p.id ? "bg-white/5 border border-gold/30" : "hover:bg-white/5 border border-transparent"
                  }`}
                  onClick={() => navigate(`/studio/${p.id}`)}
                  data-testid={`project-item-${p.id}`}
                >
                  <div className="min-w-0">
                    <div className="text-sm truncate">{p.title}</div>
                    <div className="text-[10px] uppercase tracking-widest text-white/40 mt-0.5 flex items-center gap-2">
                      <span>{p.status}</span>
                      {p.scene_count > 0 && <span>· {p.scene_count} sc</span>}
                    </div>
                  </div>
                  <button
                    className="opacity-0 group-hover:opacity-100 text-white/40 hover:text-red-400 transition"
                    onClick={(e) => { e.stopPropagation(); deleteProject(p.id); }}
                    data-testid={`delete-project-${p.id}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* Main workspace */}
        <main className="col-span-12 lg:col-span-9 xl:col-span-10">
          {!project ? (
            <EmptyState onCreate={createProject} />
          ) : (
            <>
              <ProjectHeader project={project} activeTab={activeTab} setActiveTab={setActiveTab} loading={loading} onReload={() => loadProject(project.id)} />
              <div className="mt-6">
                {activeTab === "ingest" && (
                  <IngestPanel project={project} onDone={() => loadProject(project.id)} />
                )}
                {activeTab === "characters" && (
                  <CharactersPanel project={project} onReload={() => loadProject(project.id)} />
                )}
                {activeTab === "scenes" && (
                  <ScenesPanel project={project} onReload={() => loadProject(project.id)} />
                )}
                {activeTab === "assemble" && (
                  <AssemblePanel project={project} onReload={() => loadProject(project.id)} />
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

// ---- Empty state ----
const EmptyState = ({ onCreate }) => (
  <div className="card p-16 text-center" data-testid="empty-state">
    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full border border-gold/30 bg-gold/5 mb-6">
      <Film className="w-7 h-7 text-gold" />
    </div>
    <h2 className="font-display text-3xl tracking-tight">Start a new film</h2>
    <p className="text-white/60 mt-3 max-w-md mx-auto text-sm">
      Ingest a story via file, URL, script or voice — AiPillu will do the rest.
    </p>
    <button className="btn-gold mt-8" onClick={onCreate} data-testid="empty-create-btn">
      <Plus className="w-4 h-4" /> Create project
    </button>
  </div>
);

// ---- Project header with tabs ----
const TABS = [
  { key: "ingest", label: "Ingest", icon: FileText },
  { key: "characters", label: "Characters", icon: Users },
  { key: "scenes", label: "Scenes", icon: Layers },
  { key: "assemble", label: "Assemble", icon: Film },
];

const ProjectHeader = ({ project, activeTab, setActiveTab, loading, onReload }) => {
  const analyzed = !!project.blueprint;
  return (
    <div>
      <div className="flex items-start justify-between gap-6 flex-wrap">
        <div>
          <div className="overline flex items-center gap-2">
            <span>Project · {project.id.slice(0, 6)}</span>
            <span>·</span>
            <span className="text-gold">{project.status}</span>
            {loading && <Spinner className="w-3 h-3 ml-1" />}
          </div>
          <h1 className="font-display text-3xl sm:text-4xl tracking-tight mt-2" data-testid="project-title">
            {project.title}
          </h1>
          {project.blueprint?.logline && (
            <p className="text-white/60 mt-2 max-w-2xl italic" data-testid="project-logline">
              &ldquo;{project.blueprint.logline}&rdquo;
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-ghost text-sm" onClick={onReload} data-testid="reload-btn">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </div>

      <div className="mt-6 flex items-center gap-2 border-b border-white/5">
        {TABS.map((t) => {
          const disabled = (t.key !== "ingest" && !analyzed);
          return (
            <button
              key={t.key}
              disabled={disabled}
              onClick={() => setActiveTab(t.key)}
              className={`px-4 py-2.5 text-sm flex items-center gap-2 border-b-2 transition ${
                activeTab === t.key
                  ? "border-gold text-white"
                  : disabled
                    ? "border-transparent text-white/25 cursor-not-allowed"
                    : "border-transparent text-white/60 hover:text-white"
              }`}
              data-testid={`tab-${t.key}`}
            >
              <t.icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>
    </div>
  );
};

// ---- Ingest Panel ----
const IngestPanel = ({ project, onDone }) => {
  const [mode, setMode] = useState("script");
  const [busy, setBusy] = useState(false);
  const [scriptText, setScriptText] = useState("");
  const [url, setUrl] = useState("");
  const fileRef = useRef(null);
  const voiceRef = useRef(null);
  const [analyzing, setAnalyzing] = useState(false);

  const doAction = async (fn) => {
    setBusy(true);
    try {
      await fn();
      toast.success("Source ingested");
      await onDone();
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message || "Failed");
    } finally {
      setBusy(false);
    }
  };

  const submitScript = () => doAction(async () => {
    if (scriptText.trim().length < 30) throw new Error("Please provide at least a few sentences.");
    await API.post(`/projects/${project.id}/ingest/text`, { text: scriptText });
  });

  const submitUrl = () => doAction(async () => {
    if (!url.match(/^https?:\/\//)) throw new Error("Enter a full http(s) URL");
    await API.post(`/projects/${project.id}/ingest/url`, { url });
  });

  const submitFile = () => doAction(async () => {
    const f = fileRef.current?.files?.[0];
    if (!f) throw new Error("Choose a file first");
    const form = new FormData();
    form.append("file", f);
    await API.post(`/projects/${project.id}/ingest/file`, form);
  });

  const submitVoice = () => doAction(async () => {
    const f = voiceRef.current?.files?.[0];
    if (!f) throw new Error("Choose an audio file");
    const form = new FormData();
    form.append("file", f);
    await API.post(`/projects/${project.id}/ingest/voice`, form);
  });

  const runAnalyze = async () => {
    setAnalyzing(true);
    try {
      await API.post(`/projects/${project.id}/analyze`);
      toast.success("Analysis started — this can take 1–3 minutes");
      // Poll project until status becomes 'analyzed' or 'error'
      let attempts = 0;
      const poll = async () => {
        attempts += 1;
        try {
          const { data } = await API.get(`/projects/${project.id}`);
          if (data.status === "analyzed") {
            toast.success("Story analyzed — characters and scenes ready");
            setAnalyzing(false);
            await onDone();
            return;
          }
          if (data.status === "error") {
            toast.error(data.last_error || "Analysis failed");
            setAnalyzing(false);
            return;
          }
          if (attempts > 90) {
            toast.error("Analysis timed out. Please try again.");
            setAnalyzing(false);
            return;
          }
          setTimeout(poll, 3000);
        } catch (err) {
          setAnalyzing(false);
          toast.error("Status poll failed");
        }
      };
      setTimeout(poll, 3000);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Analysis failed");
      setAnalyzing(false);
    }
  };

  const modes = [
    { key: "script", icon: Wand2, label: "Paste script" },
    { key: "file", icon: FileText, label: "Upload file" },
    { key: "url", icon: Link2, label: "From URL" },
    { key: "voice", icon: Mic, label: "Voice / audio" },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <Section title="Ingest source" icon={FileText} testid="ingest-section">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-6">
            {modes.map((m) => (
              <button
                key={m.key}
                onClick={() => setMode(m.key)}
                className={`p-3 rounded-md border text-sm flex items-center gap-2 transition ${
                  mode === m.key ? "border-gold/50 bg-gold/5 text-white" : "border-white/10 text-white/60 hover:text-white hover:border-white/25"
                }`}
                data-testid={`ingest-mode-${m.key}`}
              >
                <m.icon className="w-4 h-4" />
                {m.label}
              </button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            {mode === "script" && (
              <motion.div key="script" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <label className="overline">Your story or script</label>
                <textarea
                  className="textarea-field mt-2 min-h-[200px]"
                  value={scriptText}
                  onChange={(e) => setScriptText(e.target.value)}
                  placeholder="Paste your story here. Ramayan, Mahabharat, a short tale, your original screenplay — anything works."
                  data-testid="script-textarea"
                />
                <div className="flex justify-end mt-4">
                  <button className="btn-gold" onClick={submitScript} disabled={busy} data-testid="submit-script">
                    {busy ? <Spinner /> : <ChevronRight className="w-4 h-4" />} Submit script
                  </button>
                </div>
              </motion.div>
            )}

            {mode === "file" && (
              <motion.div key="file" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <label className="dashed-drop p-10 flex flex-col items-center justify-center cursor-pointer">
                  <FileText className="w-8 h-8 text-gold" />
                  <div className="mt-3 text-sm text-white/70">Click to choose a PDF, DOCX or TXT</div>
                  <div className="mt-1 text-xs text-white/40">Max 15 MB</div>
                  <input ref={fileRef} type="file" className="hidden" accept=".pdf,.docx,.doc,.txt,.md" data-testid="file-input" />
                </label>
                <div className="flex justify-end mt-4">
                  <button className="btn-gold" onClick={submitFile} disabled={busy} data-testid="submit-file">
                    {busy ? <Spinner /> : <ChevronRight className="w-4 h-4" />} Upload
                  </button>
                </div>
              </motion.div>
            )}

            {mode === "url" && (
              <motion.div key="url" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <label className="overline">Article or web URL</label>
                <input
                  className="input-field mt-2"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/story"
                  data-testid="url-input"
                />
                <div className="flex justify-end mt-4">
                  <button className="btn-gold" onClick={submitUrl} disabled={busy} data-testid="submit-url">
                    {busy ? <Spinner /> : <ChevronRight className="w-4 h-4" />} Fetch
                  </button>
                </div>
              </motion.div>
            )}

            {mode === "voice" && (
              <motion.div key="voice" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <label className="dashed-drop p-10 flex flex-col items-center justify-center cursor-pointer">
                  <Mic className="w-8 h-8 text-gold" />
                  <div className="mt-3 text-sm text-white/70">Click to choose an audio file (mp3, wav, m4a, webm...)</div>
                  <div className="mt-1 text-xs text-white/40">Max 25 MB · Transcribed with Whisper</div>
                  <input ref={voiceRef} type="file" className="hidden" accept="audio/*" data-testid="voice-input" />
                </label>
                <div className="flex justify-end mt-4">
                  <button className="btn-gold" onClick={submitVoice} disabled={busy} data-testid="submit-voice">
                    {busy ? <Spinner /> : <ChevronRight className="w-4 h-4" />} Transcribe
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Section>
      </div>

      <div>
        <Section title="Source" icon={Sparkles} testid="source-section">
          {project.source_text ? (
            <>
              <Pill tone="ok">{project.source_type || "text"} · {project.source_text.length} chars</Pill>
              <div className="mt-4 max-h-[220px] overflow-y-auto text-sm text-white/70 leading-relaxed whitespace-pre-wrap font-mono text-xs bg-black/40 rounded p-3 border border-white/5">
                {project.source_text.slice(0, 3000)}{project.source_text.length > 3000 ? "…" : ""}
              </div>
              <div className="mt-5">
                <button
                  className="btn-gold w-full justify-center"
                  onClick={runAnalyze}
                  disabled={analyzing}
                  data-testid="analyze-btn"
                >
                  {analyzing ? <><Spinner /> Analyzing…</> : <><Zap className="w-4 h-4" /> Analyze story</>}
                </button>
                <p className="text-xs text-white/40 mt-3">
                  Uses Claude Sonnet 4.6 to draft an original film blueprint —
                  characters, scenes, camera language.
                </p>
              </div>
            </>
          ) : (
            <div className="text-sm text-white/50">No source ingested yet.</div>
          )}
        </Section>
      </div>
    </div>
  );
};

// ---- Characters Panel ----
const CharactersPanel = ({ project, onReload }) => {
  const [busyId, setBusyId] = useState(null);
  const characters = project.characters || [];

  const gen = async (cid) => {
    setBusyId(cid);
    try {
      await API.post(`/projects/${project.id}/characters/${cid}/image`);
      toast.success("Character portrait generated");
      await onReload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Image failed");
    } finally { setBusyId(null); }
  };

  return (
    <Section title="Character studio" icon={Users} testid="characters-section"
      right={<Pill tone="gold">{characters.length} characters</Pill>}
    >
      {characters.length === 0 && (
        <div className="text-sm text-white/50">Run analysis first to conjure the cast.</div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {characters.map((c) => (
          <div key={c.id} className="rounded-md border border-white/5 bg-black/30 overflow-hidden group" data-testid={`char-card-${c.id}`}>
            <div className="aspect-[4/5] bg-black/40 overflow-hidden relative">
              {c.image_file ? (
                <img src={assetUrl(c.image_file)} alt={c.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center text-white/40 gap-2">
                  <Users className="w-8 h-8" />
                  <div className="text-xs">No portrait yet</div>
                </div>
              )}
              <button
                className="absolute bottom-3 right-3 btn-gold text-xs !py-1.5 !px-3"
                disabled={busyId === c.id}
                onClick={() => gen(c.id)}
                data-testid={`gen-char-${c.id}`}
              >
                {busyId === c.id ? <Spinner /> : <ImageIcon className="w-3.5 h-3.5" />}
                {c.image_file ? "Regenerate" : "Generate"}
              </button>
            </div>
            <div className="p-4">
              <div className="font-display text-lg tracking-tight">{c.name}</div>
              <div className="overline mt-1">{c.archetype}</div>
              {c.traditional_alias && (
                <div className="text-[11px] text-white/40 mt-1">alias · {c.traditional_alias}</div>
              )}
              <p className="text-xs text-white/60 mt-3 leading-relaxed line-clamp-4">{c.description}</p>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
};

// ---- Scenes Panel ----
const ScenesPanel = ({ project, onReload }) => {
  const [busy, setBusy] = useState({});
  const scenes = project.scenes || [];

  const setB = (id, key, val) => setBusy((s) => ({ ...s, [`${id}_${key}`]: val }));

  const action = async (id, key, url, opts = {}) => {
    setB(id, key, true);
    try {
      await API.post(url, opts.body || {});
      toast.success(opts.msg || "Done");
      await onReload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    } finally { setB(id, key, false); }
  };

  return (
    <Section title="Scene storyboard" icon={Layers} testid="scenes-section"
      right={<Pill tone="gold">{scenes.length} scenes</Pill>}
    >
      {scenes.length === 0 && <div className="text-sm text-white/50">No scenes yet — analyze the story first.</div>}
      <div className="space-y-6">
        {scenes.map((s, idx) => (
          <div key={s.id} className="rounded-md border border-white/5 bg-black/30 p-5" data-testid={`scene-card-${s.id}`}>
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="text-gold font-mono text-xs">SCENE {String(idx + 1).padStart(2, "0")}</div>
                <div className="font-display text-xl mt-1">{s.title}</div>
                <div className="text-[11px] text-white/40 uppercase tracking-widest mt-1">
                  {s.location} · {s.time_of_day} · {s.mood}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {s.image_file && <Pill tone="ok">image ✓</Pill>}
                {s.video_file && <Pill tone="ok">video ✓</Pill>}
                {s.audio_file && <Pill tone="ok">narration ✓</Pill>}
                {s.final_file && <Pill tone="gold">final ✓</Pill>}
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 lg:grid-cols-5 gap-4">
              <div className="lg:col-span-2">
                <div className="aspect-video rounded-md border border-white/5 bg-black overflow-hidden">
                  {s.final_file ? (
                    <video src={assetUrl(s.final_file)} controls className="w-full h-full object-cover" />
                  ) : s.video_file ? (
                    <video src={assetUrl(s.video_file)} controls className="w-full h-full object-cover" />
                  ) : s.image_file ? (
                    <img src={assetUrl(s.image_file)} alt={s.title} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-white/30 text-xs">
                      <ImageIcon className="w-8 h-8" />
                    </div>
                  )}
                </div>
                {s.audio_file && (
                  <audio src={assetUrl(s.audio_file)} controls className="w-full mt-2" />
                )}
              </div>
              <div className="lg:col-span-3">
                <p className="text-sm text-white/70 leading-relaxed">{s.description}</p>
                {s.narration && (
                  <div className="mt-3 p-3 rounded border border-white/5 bg-black/40">
                    <div className="overline mb-1">Narration</div>
                    <p className="text-sm italic text-white/80">&ldquo;{s.narration}&rdquo;</p>
                  </div>
                )}
                {s.camera && <div className="mt-2 text-xs text-white/50">Camera · {s.camera}</div>}

                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    className="btn-ghost text-xs"
                    onClick={() => action(s.id, "img", `/projects/${project.id}/scenes/${s.id}/image`, { msg: "Image generated" })}
                    disabled={busy[`${s.id}_img`]}
                    data-testid={`scene-image-${s.id}`}
                  >
                    {busy[`${s.id}_img`] ? <Spinner /> : <ImageIcon className="w-3.5 h-3.5" />} Storyboard image
                  </button>
                  <button
                    className="btn-ghost text-xs"
                    onClick={() => action(s.id, "vid", `/projects/${project.id}/scenes/${s.id}/video`, { body: { duration: 4, size: "1280x720", model: "sora-2" }, msg: "Sora 2 clip generated" })}
                    disabled={busy[`${s.id}_vid`]}
                    data-testid={`scene-video-${s.id}`}
                  >
                    {busy[`${s.id}_vid`] ? <Spinner /> : <Video className="w-3.5 h-3.5" />} Sora 2 clip (4s)
                  </button>
                  <button
                    className="btn-ghost text-xs"
                    onClick={() => action(s.id, "kb", `/projects/${project.id}/scenes/${s.id}/kenburns`, { msg: "Motion applied" })}
                    disabled={busy[`${s.id}_kb`] || !s.image_file}
                    title={!s.image_file ? "Generate image first" : ""}
                    data-testid={`scene-kenburns-${s.id}`}
                  >
                    {busy[`${s.id}_kb`] ? <Spinner /> : <Wand2 className="w-3.5 h-3.5" />} Ken-Burns motion
                  </button>
                  <button
                    className="btn-ghost text-xs"
                    onClick={() => action(s.id, "nar", `/projects/${project.id}/scenes/${s.id}/narration`, { body: { voice: "onyx", model: "tts-1" }, msg: "Narration generated" })}
                    disabled={busy[`${s.id}_nar`]}
                    data-testid={`scene-narration-${s.id}`}
                  >
                    {busy[`${s.id}_nar`] ? <Spinner /> : <Volume2 className="w-3.5 h-3.5" />} Narration
                  </button>
                  <button
                    className="btn-gold text-xs"
                    onClick={() => action(s.id, "mux", `/projects/${project.id}/scenes/${s.id}/mux`, { msg: "Scene finalized" })}
                    disabled={busy[`${s.id}_mux`] || !s.video_file}
                    title={!s.video_file ? "Generate video first" : ""}
                    data-testid={`scene-mux-${s.id}`}
                  >
                    {busy[`${s.id}_mux`] ? <Spinner /> : <Sparkles className="w-3.5 h-3.5" />} Finalize scene
                  </button>
                </div>
                <div className="mt-3 text-[11px] text-white/40">
                  Tip · Sora 2 clips take 2–5 minutes each. Ken-Burns is instant and works offline.
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
};

// ---- Assemble Panel ----
const AssemblePanel = ({ project, onReload }) => {
  const [busy, setBusy] = useState(false);
  const [unlock, setUnlock] = useState(null);
  const [loading, setLoading] = useState(false);
  const [payBusy, setPayBusy] = useState(false);
  const [polling, setPolling] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const userId = getUserId();
  const readyScenes = (project.scenes || []).filter((s) => s.video_file || s.final_file);

  const refreshUnlock = useCallback(async () => {
    if (!project.final_film) { setUnlock(null); return; }
    setLoading(true);
    try {
      const { data } = await API.get(`/projects/${project.id}/unlock-status`, { params: { user_id: userId } });
      setUnlock(data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [project.id, project.final_film, userId]);

  useEffect(() => { refreshUnlock(); }, [refreshUnlock]);

  // Handle return from Stripe with ?session_id=...
  useEffect(() => {
    const sid = searchParams.get("session_id");
    const paid = searchParams.get("paid");
    if (sid && paid === "1") {
      pollStatus(sid);
    }
  }, []);

  const pollStatus = async (sid, attempts = 0) => {
    if (attempts >= 12) {
      setPolling(false);
      toast.warning("Payment status check timed out — please refresh in a minute");
      return;
    }
    setPolling(true);
    try {
      const { data } = await API.get(`/checkout/status/${sid}`);
      if (data.payment_status === "paid") {
        toast.success("Payment received — film unlocked!");
        setPolling(false);
        setSearchParams({});
        await onReload();
        await refreshUnlock();
        return;
      }
      if (data.status === "expired") {
        toast.error("Checkout expired");
        setPolling(false);
        return;
      }
      setTimeout(() => pollStatus(sid, attempts + 1), 2500);
    } catch (e) {
      setPolling(false);
      toast.error("Status check failed");
    }
  };

  const assemble = async () => {
    setBusy(true);
    try {
      await API.post(`/projects/${project.id}/assemble`);
      toast.success("Final film assembled!");
      await onReload();
      await refreshUnlock();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Assembly failed");
    } finally { setBusy(false); }
  };

  const claimFree = async () => {
    setPayBusy(true);
    try {
      await API.post(`/projects/${project.id}/claim-free`, {
        origin_url: window.location.origin, user_id: userId,
      });
      toast.success("Free tier unlocked — download & share away!");
      await onReload();
      await refreshUnlock();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Free unlock failed");
    } finally { setPayBusy(false); }
  };

  const payNow = async () => {
    setPayBusy(true);
    try {
      const { data } = await API.post(`/projects/${project.id}/checkout`, {
        origin_url: window.location.origin, user_id: userId,
      });
      if (data.already_unlocked) {
        await refreshUnlock();
        return;
      }
      if (data.url) window.location.href = data.url;
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Payment init failed");
    } finally { setPayBusy(false); }
  };

  const unlocked = !!(project.paid || project.free_granted) || unlock?.already_unlocked;
  const filmDownloadUrl = `${process.env.REACT_APP_BACKEND_URL}/api/projects/${project.id}/film?user_id=${userId}`;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <Section title="Final film" icon={Film} testid="assemble-section">
          <div className="aspect-video bg-black rounded-md overflow-hidden border border-white/5 relative">
            {project.final_film && unlocked ? (
              <video src={filmDownloadUrl} controls className="w-full h-full" data-testid="final-film-video" />
            ) : project.final_film ? (
              <div className="w-full h-full flex flex-col items-center justify-center text-white/50 gap-4 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-tr from-black via-black/60 to-gold/10" />
                <Lock className="w-12 h-12 text-gold relative" />
                <div className="text-sm relative">Film ready — unlock to preview, download & share.</div>
              </div>
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center text-white/30 gap-3">
                <Play className="w-10 h-10" />
                <div className="text-xs uppercase tracking-widest">Nothing to play yet</div>
              </div>
            )}
          </div>
          <div className="mt-4 flex flex-wrap gap-2 justify-between">
            <div className="text-xs text-white/50">
              {readyScenes.length} of {(project.scenes || []).length} scenes have video clips.
            </div>
            <div className="flex gap-2">
              <button className="btn-gold text-sm" onClick={assemble} disabled={busy || readyScenes.length === 0} data-testid="assemble-btn">
                {busy ? <Spinner /> : <Film className="w-3.5 h-3.5" />} {project.final_film ? "Re-assemble" : "Assemble film"}
              </button>
            </div>
          </div>
        </Section>

        {project.final_film && (
          <UnlockAndShare
            project={project}
            unlock={unlock}
            unlocked={unlocked}
            loading={loading}
            payBusy={payBusy}
            polling={polling}
            onClaimFree={claimFree}
            onPayNow={payNow}
            filmDownloadUrl={filmDownloadUrl}
            onRefresh={refreshUnlock}
            userId={userId}
          />
        )}
      </div>

      <Section title="Checklist" icon={Layers} testid="assemble-checklist">
        <div className="space-y-3">
          {(project.scenes || []).map((s, idx) => (
            <div key={s.id} className="flex items-center justify-between gap-3 text-sm border-b border-white/5 pb-2">
              <div className="min-w-0">
                <div className="truncate">{String(idx + 1).padStart(2, "0")} · {s.title}</div>
                <div className="text-[10px] text-white/40 uppercase tracking-widest">
                  {s.image_file ? "img" : "—"} · {s.video_file ? "vid" : "—"} · {s.audio_file ? "aud" : "—"}
                </div>
              </div>
              {s.final_file ? <Pill tone="gold">final</Pill> : s.video_file ? <Pill tone="ok">video</Pill> : <Pill>pending</Pill>}
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
};

// ---- Unlock + Share Panel ----
const UnlockAndShare = ({ project, unlock, unlocked, loading, payBusy, polling, onClaimFree, onPayNow, filmDownloadUrl, onRefresh, userId }) => {
  const [copied, setCopied] = useState(false);
  const [shareUrl, setShareUrl] = useState("");

  useEffect(() => {
    if (!unlocked) { setShareUrl(""); return; }
    (async () => {
      try {
        const { data } = await API.get(`/projects/${project.id}/share-info`, { params: { origin_url: window.location.origin } });
        setShareUrl(data.share_url);
      } catch { /* ignore */ }
    })();
  }, [unlocked, project.id]);

  const copyLink = async () => {
    if (!shareUrl) return;
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    toast.success("Link copied");
    setTimeout(() => setCopied(false), 2000);
  };

  const shareText = `Watch "${project.title}" — an original AI-crafted short film made with AiPillu Studio`;
  const enc = encodeURIComponent;
  const encUrl = enc(shareUrl || "");
  const encText = enc(shareText);

  const shareTargets = [
    { key: "whatsapp", label: "WhatsApp", icon: MessageCircle, url: `https://wa.me/?text=${encText}%20${encUrl}` },
    { key: "twitter", label: "Twitter / X", icon: Twitter, url: `https://twitter.com/intent/tweet?text=${encText}&url=${encUrl}` },
    { key: "facebook", label: "Facebook", icon: Facebook, url: `https://www.facebook.com/sharer/sharer.php?u=${encUrl}` },
    { key: "telegram", label: "Telegram", icon: Send, url: `https://t.me/share/url?url=${encUrl}&text=${encText}` },
    { key: "linkedin", label: "LinkedIn", icon: Linkedin, url: `https://www.linkedin.com/sharing/share-offsite/?url=${encUrl}` },
  ];

  if (loading && !unlock) {
    return (
      <Section title="Unlock & share" icon={Sparkles} testid="unlock-section">
        <div className="flex items-center gap-2 text-white/60 text-sm"><Spinner /> Checking film status…</div>
      </Section>
    );
  }

  if (polling) {
    return (
      <Section title="Payment" icon={IndianRupee} testid="unlock-section">
        <div className="flex flex-col items-center gap-3 py-8">
          <Spinner className="w-6 h-6" />
          <div className="text-sm text-white/70">Verifying your UPI / card payment securely…</div>
          <div className="text-xs text-white/40">This usually takes a few seconds.</div>
        </div>
      </Section>
    );
  }

  return (
    <Section title={unlocked ? "Share your film" : "Unlock your film"} icon={unlocked ? Share2 : Lock} testid="unlock-section"
      right={<button className="btn-ghost text-xs" onClick={onRefresh}><RefreshCw className="w-3 h-3" /> Refresh</button>}
    >
      {!unlocked && unlock && (
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-5">
            <MetricBox label="Size" value={`${unlock.size_mb} MB`} />
            <MetricBox label="Free limit" value="20 MB" />
            <MetricBox label="Sora 2 scenes" value={String(unlock.price?.sora_scenes || 0)} />
          </div>

          {unlock.free_eligible ? (
            <div className="rounded-md border border-gold/30 bg-gold/5 p-5">
              <div className="flex items-center gap-2 text-gold text-sm font-medium">
                <Sparkles className="w-4 h-4" /> First film is on the house
              </div>
              <p className="text-sm text-white/70 mt-2">
                Your film is under 20 MB and this is your first project — download and share it for free.
              </p>
              <button className="btn-gold mt-4" onClick={onClaimFree} disabled={payBusy} data-testid="claim-free-btn">
                {payBusy ? <Spinner /> : <Zap className="w-3.5 h-3.5" />} Claim free unlock
              </button>
            </div>
          ) : (
            <div className="rounded-md border border-white/10 bg-black/40 p-5">
              <div className="flex items-baseline gap-2">
                <IndianRupee className="w-5 h-5 text-gold" />
                <span className="text-4xl font-display font-light" data-testid="price-display">{unlock.price.total_inr}</span>
                <span className="text-xs text-white/40 uppercase tracking-widest">one-time</span>
              </div>
              <div className="mt-3 text-xs text-white/50 space-y-1 font-mono">
                <div>Base fee · ₹{unlock.price.base_inr}</div>
                {unlock.price.size_fee_inr > 0 && <div>Size fee (over {20} MB) · ₹{unlock.price.size_fee_inr}</div>}
                {unlock.price.quality_fee_inr > 0 && <div>Sora 2 quality · ₹{unlock.price.quality_fee_inr}</div>}
                <div>Creator margin · {unlock.price.creator_margin_percent}%</div>
              </div>
              <div className="mt-4 flex items-center gap-3 text-xs text-white/50">
                <ShieldCheck className="w-3.5 h-3.5 text-gold" />
                Secure UPI &amp; Card checkout · HMAC-verified webhook · No card details touch this server.
              </div>
              <button className="btn-gold mt-5 w-full justify-center" onClick={onPayNow} disabled={payBusy} data-testid="pay-btn">
                {payBusy ? <Spinner /> : <IndianRupee className="w-4 h-4" />} Pay ₹{unlock.price.total_inr} securely
              </button>
              <div className="mt-2 text-[11px] text-white/40 text-center">
                Powered by Stripe · UPI, Card, and more
              </div>
            </div>
          )}
          <div className="mt-4 text-[11px] text-white/40">
            Note: <span className="text-white/60">{unlock.reason}</span>
          </div>
        </div>
      )}

      {unlocked && (
        <div>
          <div className="rounded-md border border-gold/30 bg-gold/5 p-4 mb-5 flex items-center gap-3">
            <ShieldCheck className="w-5 h-5 text-gold" />
            <div>
              <div className="text-sm">Film unlocked{project.paid ? " · payment received" : " · free tier"}</div>
              <div className="text-[11px] text-white/50">Download, share, or embed anywhere.</div>
            </div>
          </div>

          {/* Primary actions */}
          <div className="grid grid-cols-2 gap-3 mb-5">
            <a className="btn-gold justify-center" href={filmDownloadUrl} download data-testid="download-film">
              <Download className="w-4 h-4" /> Download MP4
            </a>
            <button className="btn-ghost justify-center" onClick={copyLink} data-testid="copy-link">
              {copied ? <Check className="w-4 h-4 text-gold" /> : <Copy className="w-4 h-4" />} {copied ? "Copied" : "Copy link"}
            </button>
          </div>

          {/* Share targets */}
          <div className="overline mb-3">One-click share</div>
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 mb-5">
            {shareTargets.map((s) => (
              <a
                key={s.key}
                href={s.url}
                target="_blank"
                rel="noreferrer"
                className="p-3 rounded-md border border-white/10 hover:border-gold/40 hover:bg-white/5 transition text-center group"
                data-testid={`share-${s.key}`}
              >
                <s.icon className="w-4 h-4 mx-auto text-white/70 group-hover:text-gold" />
                <div className="text-[11px] mt-1.5 text-white/60">{s.label}</div>
              </a>
            ))}
          </div>

          <div className="overline mb-3">Native apps</div>
          <div className="grid grid-cols-2 gap-2 mb-2">
            <a href={filmDownloadUrl} download className="p-3 rounded-md border border-white/10 hover:border-gold/40 hover:bg-white/5 transition text-center flex items-center justify-center gap-2" data-testid="share-youtube">
              <Youtube className="w-4 h-4 text-white/70" />
              <span className="text-xs">Download for YouTube</span>
            </a>
            <a href={filmDownloadUrl} download className="p-3 rounded-md border border-white/10 hover:border-gold/40 hover:bg-white/5 transition text-center flex items-center justify-center gap-2" data-testid="share-instagram">
              <Instagram className="w-4 h-4 text-white/70" />
              <span className="text-xs">Download for Instagram</span>
            </a>
          </div>
          <div className="text-[11px] text-white/40 mt-2">
            YouTube &amp; Instagram require using their native apps — download first, then upload from the app.
          </div>
        </div>
      )}
    </Section>
  );
};

const MetricBox = ({ label, value }) => (
  <div className="rounded-md border border-white/5 bg-black/40 p-3">
    <div className="overline">{label}</div>
    <div className="font-display text-xl mt-1">{value}</div>
  </div>
);
