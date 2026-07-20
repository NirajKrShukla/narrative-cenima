import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  Film, Plus, Trash2, FileText, Link2, Mic, Wand2, Sparkles, Users,
  Image as ImageIcon, Video, Volume2, Layers, Download, Loader2, ChevronRight,
  ArrowLeft, Play, ShieldCheck, RefreshCw, Zap, Lock, Share2, IndianRupee,
  Copy, Check, MessageCircle, Twitter, Facebook, Send, Linkedin, Youtube, Instagram,
  Settings, Globe, Heart, Rocket, AlertCircle, Languages, Type, Subtitles, X,
} from "lucide-react";
import { API, assetUrl } from "../lib/api";
import LicenseBadge from "../components/LicenseBadge";

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
            <LicenseBadge compact />
            <Link to="/gallery" className="text-sm text-white/70 hover:text-white transition flex items-center gap-1.5" data-testid="nav-gallery">
              <Globe className="w-4 h-4 text-gold" /> Gallery
            </Link>
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
                {activeTab === "batch" && (
                  <BatchPanel project={project} onReload={() => loadProject(project.id)} />
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
  { key: "batch", label: "Auto-Pilot", icon: Rocket },
  { key: "assemble", label: "Assemble", icon: Film },
];

const ProjectHeader = ({ project, activeTab, setActiveTab, loading, onReload }) => {
  const analyzed = !!project.blueprint;
  const [settingsOpen, setSettingsOpen] = useState(false);
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
          <button className="btn-ghost text-sm" onClick={() => setSettingsOpen((v) => !v)} data-testid="settings-toggle">
            <Settings className="w-3.5 h-3.5" /> Voice &amp; language
          </button>
          <button className="btn-ghost text-sm" onClick={onReload} data-testid="reload-btn">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </div>

      <AnimatePresence>
        {settingsOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <VoiceLanguageSettings project={project} onReload={onReload} onClose={() => setSettingsOpen(false)} />
          </motion.div>
        )}
      </AnimatePresence>

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
  const [ingestLang, setIngestLang] = useState(project.language_hint || "auto");
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
    await API.post(`/projects/${project.id}/ingest/text`, { text: scriptText, language: ingestLang });
  });

  const submitUrl = () => doAction(async () => {
    if (!url.match(/^https?:\/\//)) throw new Error("Enter a full http(s) URL");
    await API.post(`/projects/${project.id}/ingest/url`, { url, language: ingestLang });
  });

  const submitFile = () => doAction(async () => {
    const f = fileRef.current?.files?.[0];
    if (!f) throw new Error("Choose a file first");
    const form = new FormData();
    form.append("file", f);
    if (ingestLang) form.append("language", ingestLang);
    await API.post(`/projects/${project.id}/ingest/file`, form);
  });

  const submitVoice = () => doAction(async () => {
    const f = voiceRef.current?.files?.[0];
    if (!f) throw new Error("Choose an audio file");
    const form = new FormData();
    form.append("file", f);
    if (ingestLang) form.append("language", ingestLang);
    await API.post(`/projects/${project.id}/ingest/voice`, form);
  });

  const [targetLength, setTargetLength] = useState("auto");   // auto | short | medium | long | custom
  const [customSeconds, setCustomSeconds] = useState(90);

  const runAnalyze = async () => {
    setAnalyzing(true);
    try {
      const payload = {};
      if (targetLength === "short") payload.target_seconds = 30;
      else if (targetLength === "medium") payload.target_seconds = 90;
      else if (targetLength === "long") payload.target_seconds = 180;
      else if (targetLength === "custom") payload.target_seconds = Math.max(15, Math.min(600, Number(customSeconds) || 60));
      // "auto" → no override, backend scales from word count
      await API.post(`/projects/${project.id}/analyze`, payload);
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
          {/* Universal language picker — applies to any input method */}
          <div className="mb-6 p-4 rounded-md border border-gold/20 bg-gold/5">
            <div className="flex items-center gap-2 mb-2">
              <Globe className="w-3.5 h-3.5 text-gold" />
              <label className="overline">Narration language · works with ANY input method</label>
            </div>
            <select
              className="input-field"
              value={ingestLang}
              onChange={(e) => setIngestLang(e.target.value)}
              data-testid="ingest-language"
            >
              {(() => {
                const groups = {};
                LANGUAGES.forEach((l) => {
                  const g = l.region || "General";
                  (groups[g] = groups[g] || []).push(l);
                });
                const order = ["", "General", "South Asia", "Europe & Global", "Europe", "East Asia", "SE Asia", "Middle East", "Caucasus", "Central Asia", "Asia", "Africa", "Americas", "Pacific"];
                const keys = Object.keys(groups).sort(
                  (a, b) => (order.indexOf(a) + 100) - (order.indexOf(b) + 100)
                );
                return keys.map((k) => (
                  <optgroup key={k} label={k || "General"}>
                    {groups[k].map((l) => (
                      <option key={l.id} value={l.id}>{l.label}</option>
                    ))}
                  </optgroup>
                ));
              })()}
            </select>
            <div className="text-[11px] text-white/50 mt-2">
              {LANGUAGES.length - 1}+ world languages supported · translated automatically from any source
            </div>
          </div>

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
                {/* Film length selector — respects the source text, never pads */}
                <div className="mb-4" data-testid="length-selector">
                  <div className="text-xs text-white/50 mb-2 flex items-center justify-between">
                    <span>Target film length</span>
                    <span className="text-white/40">
                      ~{Math.max(3, Math.min(15, Math.round((project.source_text?.split(/\s+/).length || 0) / 120)))} scenes if Auto
                    </span>
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-xs">
                    {[
                      { key: "auto", label: "Auto", hint: "Scales with source" },
                      { key: "short", label: "Short", hint: "~30 s · 3 scenes" },
                      { key: "medium", label: "Medium", hint: "~90 s · 10 scenes" },
                      { key: "long", label: "Long", hint: "~3 min · 20 scenes" },
                    ].map((opt) => (
                      <button
                        key={opt.key}
                        type="button"
                        onClick={() => setTargetLength(opt.key)}
                        className={`px-2 py-2 rounded border transition text-left ${
                          targetLength === opt.key
                            ? "border-gold bg-gold/10 text-gold"
                            : "border-white/10 hover:border-white/25 text-white/60"
                        }`}
                        data-testid={`length-${opt.key}`}
                      >
                        <div className="font-medium">{opt.label}</div>
                        <div className="text-[10px] text-white/40 mt-0.5">{opt.hint}</div>
                      </button>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={() => setTargetLength("custom")}
                    className={`mt-2 w-full text-xs text-left px-2 py-2 rounded border transition ${
                      targetLength === "custom"
                        ? "border-gold bg-gold/10 text-gold"
                        : "border-white/10 hover:border-white/25 text-white/60"
                    }`}
                    data-testid="length-custom-toggle"
                  >
                    Custom
                    {targetLength === "custom" && (
                      <span className="ml-2 inline-flex items-center gap-1">
                        <input
                          type="number"
                          min={15}
                          max={600}
                          value={customSeconds}
                          onChange={(e) => setCustomSeconds(e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          className="w-14 bg-black/40 border border-white/10 rounded px-1 py-0.5 text-center"
                          data-testid="length-custom-input"
                        /> sec
                      </span>
                    )}
                  </button>
                  <p className="text-[10px] text-white/40 mt-2 leading-relaxed">
                    We adapt only what's in your source — the film will never invent characters or events that aren't in your text.
                  </p>
                </div>

                <button
                  className="btn-gold w-full justify-center"
                  onClick={runAnalyze}
                  disabled={analyzing}
                  data-testid="analyze-btn"
                >
                  {analyzing ? <><Spinner /> Analyzing…</> : <><Zap className="w-4 h-4" /> Analyze story</>}
                </button>
                <p className="text-xs text-white/40 mt-3">
                  Uses Claude Sonnet 4.6 to draft a faithful, original film blueprint —
                  characters, scenes, camera language. No hallucination — every scene traces back to your text.
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

                <SceneNarrationEditor scene={s} projectId={project.id} onReload={onReload} />

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
                    onClick={() => action(s.id, "nar", `/projects/${project.id}/scenes/${s.id}/narration`, { msg: "Narration generated" })}
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
          <div className="grid grid-cols-3 gap-3 mb-5">
            <a className="btn-gold justify-center" href={filmDownloadUrl} download data-testid="download-film">
              <Download className="w-4 h-4" /> Download MP4
            </a>
            <a
              className="btn-ghost justify-center"
              href={`${process.env.REACT_APP_BACKEND_URL}/api/projects/${project.id}/subtitles`}
              download
              data-testid="download-srt"
              title="Download SRT subtitle file"
            >
              <Subtitles className="w-4 h-4" /> SRT
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

          <PublishSection project={project} onRefresh={onRefresh} />

          <DubPanel project={project} onReload={onRefresh} />
        </div>
      )}
    </Section>
  );
};

// ---------- Publish to Gallery ----------
const PublishSection = ({ project, onRefresh }) => {
  const [isPublic, setIsPublic] = useState(!!project.is_public);
  const [tipVpa, setTipVpa] = useState(project.tip_vpa || "");
  const [busy, setBusy] = useState(false);

  const publish = async (val) => {
    setBusy(true);
    try {
      await API.post(`/projects/${project.id}/publish`, { is_public: val, tip_vpa: tipVpa });
      setIsPublic(val);
      toast.success(val ? "Published to public gallery" : "Removed from gallery");
      await onRefresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Publish failed");
    } finally { setBusy(false); }
  };

  const galleryUrl = `${window.location.origin}/gallery/${project.id}`;

  return (
    <div className="mt-6 rounded-md border border-white/10 bg-black/30 p-5" data-testid="publish-section">
      <div className="flex items-center gap-2 mb-2">
        <Globe className="w-4 h-4 text-gold" />
        <div className="font-display text-lg">Publish to public gallery</div>
      </div>
      <p className="text-xs text-white/50 mb-4">
        Let anyone watch your film on the AiPillu gallery. Viewers can send you tips over UPI — 100% goes to the creator margin.
      </p>
      <div className="space-y-3">
        <div>
          <label className="overline">Display UPI ID (optional)</label>
          <input
            className="input-field mt-2"
            value={tipVpa}
            onChange={(e) => setTipVpa(e.target.value)}
            placeholder="e.g. yourname@okhdfcbank"
            data-testid="publish-vpa"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isPublic ? (
            <>
              <Pill tone="ok">public</Pill>
              <a href={galleryUrl} target="_blank" rel="noreferrer" className="btn-ghost text-xs" data-testid="publish-view">
                <Globe className="w-3.5 h-3.5" /> View public page
              </a>
              <button className="btn-ghost text-xs" onClick={() => publish(false)} disabled={busy} data-testid="publish-unpublish">
                {busy ? <Spinner /> : <Lock className="w-3.5 h-3.5" />} Make private
              </button>
              <button className="btn-gold text-xs" onClick={() => publish(true)} disabled={busy} data-testid="publish-update">
                {busy ? <Spinner /> : <Check className="w-3.5 h-3.5" />} Update
              </button>
            </>
          ) : (
            <button className="btn-gold" onClick={() => publish(true)} disabled={busy} data-testid="publish-btn">
              {busy ? <Spinner /> : <Rocket className="w-4 h-4" />} Publish to gallery
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const MetricBox = ({ label, value }) => (
  <div className="rounded-md border border-white/5 bg-black/40 p-3">
    <div className="overline">{label}</div>
    <div className="font-display text-xl mt-1">{value}</div>
  </div>
);


// ---------- Voice & Language Settings ----------
const VOICES = [
  { id: "alloy", desc: "Neutral, balanced" },
  { id: "ash", desc: "Clear, articulate" },
  { id: "coral", desc: "Warm, friendly" },
  { id: "echo", desc: "Smooth, calm" },
  { id: "fable", desc: "Expressive, storytelling" },
  { id: "nova", desc: "Energetic, upbeat" },
  { id: "onyx", desc: "Deep, authoritative" },
  { id: "sage", desc: "Wise, measured" },
  { id: "shimmer", desc: "Bright, cheerful" },
];

// All spoken languages on Earth (ISO 639-1/2 codes). Covers 100+ languages.
// TTS (OpenAI) and Claude both accept these; Whisper accepts the 2-letter codes.
const LANGUAGES = [
  { id: "auto", label: "Auto-detect (from story)", region: "" },
  // Indian subcontinent
  { id: "hi", label: "Hindi (हिन्दी)", region: "South Asia" },
  { id: "bn", label: "Bengali (বাংলা)", region: "South Asia" },
  { id: "ta", label: "Tamil (தமிழ்)", region: "South Asia" },
  { id: "te", label: "Telugu (తెలుగు)", region: "South Asia" },
  { id: "mr", label: "Marathi (मराठी)", region: "South Asia" },
  { id: "gu", label: "Gujarati (ગુજરાતી)", region: "South Asia" },
  { id: "kn", label: "Kannada (ಕನ್ನಡ)", region: "South Asia" },
  { id: "ml", label: "Malayalam (മലയാളം)", region: "South Asia" },
  { id: "pa", label: "Punjabi (ਪੰਜਾਬੀ)", region: "South Asia" },
  { id: "ur", label: "Urdu (اردو)", region: "South Asia" },
  { id: "or", label: "Odia (ଓଡ଼ିଆ)", region: "South Asia" },
  { id: "as", label: "Assamese (অসমীয়া)", region: "South Asia" },
  { id: "sa", label: "Sanskrit (संस्कृतम्)", region: "South Asia" },
  { id: "ne", label: "Nepali (नेपाली)", region: "South Asia" },
  { id: "si", label: "Sinhala (සිංහල)", region: "South Asia" },
  { id: "sd", label: "Sindhi (سنڌي)", region: "South Asia" },
  // European
  { id: "en", label: "English", region: "Europe & Global" },
  { id: "es", label: "Spanish (Español)", region: "Europe & Global" },
  { id: "fr", label: "French (Français)", region: "Europe & Global" },
  { id: "de", label: "German (Deutsch)", region: "Europe" },
  { id: "it", label: "Italian (Italiano)", region: "Europe" },
  { id: "pt", label: "Portuguese (Português)", region: "Europe & Global" },
  { id: "nl", label: "Dutch (Nederlands)", region: "Europe" },
  { id: "pl", label: "Polish (Polski)", region: "Europe" },
  { id: "ru", label: "Russian (Русский)", region: "Europe" },
  { id: "uk", label: "Ukrainian (Українська)", region: "Europe" },
  { id: "el", label: "Greek (Ελληνικά)", region: "Europe" },
  { id: "sv", label: "Swedish (Svenska)", region: "Europe" },
  { id: "no", label: "Norwegian (Norsk)", region: "Europe" },
  { id: "da", label: "Danish (Dansk)", region: "Europe" },
  { id: "fi", label: "Finnish (Suomi)", region: "Europe" },
  { id: "is", label: "Icelandic (Íslenska)", region: "Europe" },
  { id: "cs", label: "Czech (Čeština)", region: "Europe" },
  { id: "sk", label: "Slovak (Slovenčina)", region: "Europe" },
  { id: "sl", label: "Slovenian (Slovenščina)", region: "Europe" },
  { id: "hr", label: "Croatian (Hrvatski)", region: "Europe" },
  { id: "sr", label: "Serbian (Српски)", region: "Europe" },
  { id: "bs", label: "Bosnian (Bosanski)", region: "Europe" },
  { id: "mk", label: "Macedonian (Македонски)", region: "Europe" },
  { id: "bg", label: "Bulgarian (Български)", region: "Europe" },
  { id: "ro", label: "Romanian (Română)", region: "Europe" },
  { id: "hu", label: "Hungarian (Magyar)", region: "Europe" },
  { id: "lt", label: "Lithuanian (Lietuvių)", region: "Europe" },
  { id: "lv", label: "Latvian (Latviešu)", region: "Europe" },
  { id: "et", label: "Estonian (Eesti)", region: "Europe" },
  { id: "sq", label: "Albanian (Shqip)", region: "Europe" },
  { id: "be", label: "Belarusian (Беларуская)", region: "Europe" },
  { id: "ca", label: "Catalan (Català)", region: "Europe" },
  { id: "gl", label: "Galician (Galego)", region: "Europe" },
  { id: "eu", label: "Basque (Euskara)", region: "Europe" },
  { id: "cy", label: "Welsh (Cymraeg)", region: "Europe" },
  { id: "ga", label: "Irish (Gaeilge)", region: "Europe" },
  { id: "mt", label: "Maltese (Malti)", region: "Europe" },
  { id: "yi", label: "Yiddish (ייִדיש)", region: "Europe" },
  { id: "la", label: "Latin (Latinum)", region: "Europe" },
  // Middle East & Africa
  { id: "ar", label: "Arabic (العربية)", region: "Middle East" },
  { id: "he", label: "Hebrew (עברית)", region: "Middle East" },
  { id: "fa", label: "Persian / Farsi (فارسی)", region: "Middle East" },
  { id: "tr", label: "Turkish (Türkçe)", region: "Middle East" },
  { id: "az", label: "Azerbaijani (Azərbaycan)", region: "Caucasus" },
  { id: "hy", label: "Armenian (Հայերեն)", region: "Caucasus" },
  { id: "ka", label: "Georgian (ქართული)", region: "Caucasus" },
  { id: "kk", label: "Kazakh (Қазақ)", region: "Central Asia" },
  { id: "uz", label: "Uzbek (Oʻzbek)", region: "Central Asia" },
  { id: "tg", label: "Tajik (Тоҷикӣ)", region: "Central Asia" },
  { id: "tk", label: "Turkmen (Türkmen)", region: "Central Asia" },
  { id: "mn", label: "Mongolian (Монгол)", region: "Asia" },
  { id: "sw", label: "Swahili (Kiswahili)", region: "Africa" },
  { id: "am", label: "Amharic (አማርኛ)", region: "Africa" },
  { id: "ha", label: "Hausa", region: "Africa" },
  { id: "yo", label: "Yoruba", region: "Africa" },
  { id: "zu", label: "Zulu", region: "Africa" },
  { id: "af", label: "Afrikaans", region: "Africa" },
  { id: "so", label: "Somali", region: "Africa" },
  { id: "sn", label: "Shona (chiShona)", region: "Africa" },
  { id: "mg", label: "Malagasy", region: "Africa" },
  { id: "ln", label: "Lingala", region: "Africa" },
  { id: "ps", label: "Pashto (پښتو)", region: "Central Asia" },
  { id: "ug", label: "Uyghur (ئۇيغۇرچە)", region: "Central Asia" },
  // East / South-East Asia
  { id: "zh", label: "Chinese Mandarin (中文)", region: "East Asia" },
  { id: "yue", label: "Cantonese (粵語)", region: "East Asia" },
  { id: "ja", label: "Japanese (日本語)", region: "East Asia" },
  { id: "ko", label: "Korean (한국어)", region: "East Asia" },
  { id: "vi", label: "Vietnamese (Tiếng Việt)", region: "SE Asia" },
  { id: "th", label: "Thai (ไทย)", region: "SE Asia" },
  { id: "lo", label: "Lao (ລາວ)", region: "SE Asia" },
  { id: "km", label: "Khmer (ខ្មែរ)", region: "SE Asia" },
  { id: "my", label: "Burmese (မြန်မာ)", region: "SE Asia" },
  { id: "id", label: "Indonesian (Bahasa Indonesia)", region: "SE Asia" },
  { id: "ms", label: "Malay (Bahasa Melayu)", region: "SE Asia" },
  { id: "tl", label: "Filipino / Tagalog", region: "SE Asia" },
  { id: "jv", label: "Javanese (Basa Jawa)", region: "SE Asia" },
  { id: "su", label: "Sundanese (Basa Sunda)", region: "SE Asia" },
  { id: "bo", label: "Tibetan (བོད་ཡིག)", region: "Asia" },
  // Americas & Pacific
  { id: "ht", label: "Haitian Creole (Kreyòl)", region: "Americas" },
  { id: "haw", label: "Hawaiian (ʻŌlelo Hawaiʻi)", region: "Pacific" },
  { id: "mi", label: "Māori (Te Reo)", region: "Pacific" },
];

const VoiceLanguageSettings = ({ project, onReload }) => {
  const [voice, setVoice] = useState(project.voice || "onyx");
  const [voiceModel, setVoiceModel] = useState(project.voice_model || "tts-1");
  const [language, setLanguage] = useState(project.language_hint || "auto");
  const [title, setTitle] = useState(project.title || "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await API.patch(`/projects/${project.id}/settings`, {
        voice, voice_model: voiceModel, language_hint: language, title,
      });
      toast.success("Settings saved");
      await onReload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  return (
    <div className="card p-6 mt-4" data-testid="voice-settings-panel">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="lg:col-span-2">
          <label className="overline">Project title</label>
          <input
            className="input-field mt-2"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            data-testid="settings-title"
          />
        </div>
        <div>
          <label className="overline">Voice</label>
          <div className="flex gap-2 mt-2">
            <select
              className="input-field flex-1"
              value={voice}
              onChange={(e) => setVoice(e.target.value)}
              data-testid="settings-voice"
            >
              {VOICES.map((v) => (
                <option key={v.id} value={v.id}>{v.id} — {v.desc}</option>
              ))}
            </select>
            <VoicePreview voice={voice} model={voiceModel} language={language} testid="settings-voice-preview" />
          </div>
        </div>
        <div>
          <label className="overline">Quality</label>
          <select
            className="input-field mt-2"
            value={voiceModel}
            onChange={(e) => setVoiceModel(e.target.value)}
            data-testid="settings-voice-model"
          >
            <option value="tts-1">tts-1 (fast)</option>
            <option value="tts-1-hd">tts-1-hd (studio-grade)</option>
          </select>
        </div>
        <div className="lg:col-span-2">
          <label className="overline">Narration language</label>
          <select
            className="input-field mt-2"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            data-testid="settings-language"
          >
            {/* Grouped by region for easier scanning */}
            {(() => {
              const groups = {};
              LANGUAGES.forEach((l) => {
                const g = l.region || "General";
                (groups[g] = groups[g] || []).push(l);
              });
              const order = ["", "General", "South Asia", "Europe & Global", "Europe", "East Asia", "SE Asia", "Middle East", "Caucasus", "Central Asia", "Asia", "Africa", "Americas", "Pacific"];
              const keys = Object.keys(groups).sort(
                (a, b) => (order.indexOf(a) + 100) - (order.indexOf(b) + 100)
              );
              return keys.map((k) => (
                <optgroup key={k} label={k || "General"}>
                  {groups[k].map((l) => (
                    <option key={l.id} value={l.id}>{l.label}</option>
                  ))}
                </optgroup>
              ));
            })()}
          </select>
          <div className="mt-1 text-[11px] text-white/40">
            {LANGUAGES.length - 1}+ languages supported. Applied to future narrations you generate.
          </div>
        </div>
        <div className="lg:col-span-2 flex items-end justify-end">
          <button className="btn-gold" onClick={save} disabled={saving} data-testid="settings-save">
            {saving ? <Spinner /> : <Check className="w-4 h-4" />} Save settings
          </button>
        </div>
      </div>
    </div>
  );
};

// ---------- Auto-Pilot Batch Panel ----------
const BATCH_MODES = [
  { id: "all", label: "Full film", desc: "Images → Narration → Video (Ken-Burns) → Mux → Assemble" },
  { id: "images", label: "All scene images", desc: "Nano Banana across every scene" },
  { id: "narration", label: "All narrations", desc: "Uses project voice & language" },
  { id: "kenburns", label: "Ken-Burns motion", desc: "Instant motion from existing images" },
  { id: "sora", label: "Sora 2 clips (slow, premium)", desc: "~3 min per scene, higher cost" },
];

const BatchPanel = ({ project, onReload }) => {
  const [mode, setMode] = useState("all");
  const [videoType, setVideoType] = useState("kenburns");
  const [batch, setBatch] = useState(project.batch || null);
  const [starting, setStarting] = useState(false);
  const esRef = useRef(null);

  const fetchBatch = useCallback(async () => {
    try {
      const { data } = await API.get(`/projects/${project.id}/batch`);
      setBatch(data);
    } catch (e) { /* ignore */ }
  }, [project.id]);

  useEffect(() => { fetchBatch(); }, [fetchBatch]);

  // Server-Sent Events for realtime batch progress
  useEffect(() => {
    if (!batch?.running) return;
    const url = `${process.env.REACT_APP_BACKEND_URL}/api/projects/${project.id}/batch/stream`;
    const es = new EventSource(url);
    esRef.current = es;
    es.addEventListener("progress", (ev) => {
      try {
        const payload = JSON.parse(ev.data);
        if (payload.batch) setBatch(payload.batch);
      } catch (e) { /* ignore */ }
    });
    es.addEventListener("done", async (ev) => {
      try {
        const payload = JSON.parse(ev.data);
        if (payload.batch) setBatch(payload.batch);
      } catch (e) { /* ignore */ }
      es.close();
      esRef.current = null;
      await onReload();
      toast.success("Auto-Pilot finished");
    });
    es.onerror = () => {
      es.close();
      esRef.current = null;
      // Fallback to polling if SSE dies
      fetchBatch();
    };
    return () => { es.close(); esRef.current = null; };
  }, [batch?.running, project.id, fetchBatch, onReload]);

  const start = async () => {
    setStarting(true);
    try {
      await API.post(`/projects/${project.id}/batch`, { mode, video_type: videoType });
      toast.success("Auto-Pilot started");
      await fetchBatch();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Start failed");
    } finally { setStarting(false); }
  };

  const percent = batch?.total ? Math.min(100, Math.round((batch.completed / batch.total) * 100)) : 0;
  const scenes = project.scenes || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <Section title="Auto-Pilot" icon={Rocket} testid="batch-section"
          right={batch?.running ? <Pill tone="warn">running</Pill> : batch?.finished_at ? <Pill tone="ok">last run · done</Pill> : <Pill>idle</Pill>}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
            {BATCH_MODES.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                disabled={batch?.running}
                className={`text-left p-4 rounded-md border transition ${
                  mode === m.id ? "border-gold/50 bg-gold/5" : "border-white/10 hover:border-white/25"
                }`}
                data-testid={`batch-mode-${m.id}`}
              >
                <div className="font-medium text-sm">{m.label}</div>
                <div className="text-xs text-white/50 mt-1">{m.desc}</div>
              </button>
            ))}
          </div>

          {mode === "all" && (
            <div className="mb-5">
              <label className="overline">Video engine for &ldquo;full film&rdquo; mode</label>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <button
                  className={`p-3 rounded-md border text-sm ${videoType === "kenburns" ? "border-gold/50 bg-gold/5" : "border-white/10"}`}
                  onClick={() => setVideoType("kenburns")}
                  data-testid="batch-video-kb"
                >
                  Ken-Burns · instant, free
                </button>
                <button
                  className={`p-3 rounded-md border text-sm ${videoType === "sora" ? "border-gold/50 bg-gold/5" : "border-white/10"}`}
                  onClick={() => setVideoType("sora")}
                  data-testid="batch-video-sora"
                >
                  Sora 2 · slow, premium
                </button>
              </div>
            </div>
          )}

          <button className="btn-gold w-full justify-center" onClick={start} disabled={starting || batch?.running || scenes.length === 0} data-testid="batch-start">
            {starting || batch?.running ? <Spinner /> : <Rocket className="w-4 h-4" />}
            {batch?.running ? "Auto-Pilot running…" : "Start Auto-Pilot"}
          </button>

          {batch && (batch.running || batch.total > 0) && (
            <div className="mt-6" data-testid="batch-progress">
              <BatchProgressCard batch={batch} project={project} percent={percent} />
              {batch.errors && batch.errors.length > 0 && (
                <div className="mt-4 rounded border border-red-500/20 bg-red-500/5 p-3">
                  <div className="flex items-center gap-2 text-red-300 text-xs mb-2">
                    <AlertCircle className="w-3.5 h-3.5" /> {batch.errors.length} scene issue{batch.errors.length > 1 ? "s" : ""}
                  </div>
                  <div className="space-y-1 text-[11px] font-mono text-white/60 max-h-32 overflow-y-auto">
                    {batch.errors.map((e, i) => <div key={i}>{e}</div>)}
                  </div>
                </div>
              )}
            </div>
          )}
        </Section>
      </div>

      <Section title="What Auto-Pilot does" icon={Sparkles} testid="batch-info">
        <ul className="space-y-3 text-sm text-white/70">
          <li className="flex gap-3"><span className="text-gold font-mono text-xs mt-1">01</span> Reads the analyzed blueprint from your project.</li>
          <li className="flex gap-3"><span className="text-gold font-mono text-xs mt-1">02</span> Generates a storyboard image per scene (Nano Banana).</li>
          <li className="flex gap-3"><span className="text-gold font-mono text-xs mt-1">03</span> Voices the narration using your chosen voice &amp; language.</li>
          <li className="flex gap-3"><span className="text-gold font-mono text-xs mt-1">04</span> Animates each scene with Ken-Burns motion (or Sora 2 if premium).</li>
          <li className="flex gap-3"><span className="text-gold font-mono text-xs mt-1">05</span> Muxes audio + subtitles into each clip.</li>
          <li className="flex gap-3"><span className="text-gold font-mono text-xs mt-1">06</span> Assembles the final MP4 automatically.</li>
        </ul>
        <div className="mt-5 p-3 rounded border border-white/5 bg-black/40 text-xs text-white/50">
          Progress is polled every 2.5s. Errors on individual scenes don&apos;t stop the pipeline — you can retry them from the Scenes tab afterwards.
        </div>
      </Section>
    </div>
  );
};


// ---------- Voice preview player ----------
const VoicePreview = ({ voice, model = "tts-1", language = "auto", testid = "voice-preview" }) => {
  const [busy, setBusy] = useState(false);
  const audioRef = useRef(null);

  const play = async () => {
    setBusy(true);
    try {
      const url = `${process.env.REACT_APP_BACKEND_URL}/api/voice-preview?voice=${voice}&model=${model}&language=${encodeURIComponent(language || "auto")}`;
      if (!audioRef.current) audioRef.current = new Audio();
      audioRef.current.src = url;
      audioRef.current.play().catch(() => toast.error("Playback blocked"));
    } catch (e) {
      toast.error("Preview failed");
    } finally { setBusy(false); }
  };

  return (
    <button
      type="button"
      className="p-2 rounded-md border border-white/10 hover:border-gold/50 hover:bg-gold/5 transition inline-flex items-center gap-1.5 text-xs"
      onClick={play}
      disabled={busy}
      title={`Preview ${voice} in ${language}`}
      data-testid={testid}
    >
      {busy ? <Spinner className="w-3 h-3" /> : <Play className="w-3 h-3 text-gold" />}
      Preview
    </button>
  );
};

// ---------- Per-scene narration editor with language override ----------
const SceneNarrationEditor = ({ scene, projectId, onReload }) => {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(scene.narration || "");
  const [lang, setLang] = useState(scene.language || "auto");
  const [voice, setVoice] = useState(scene.voice || "");
  const [voiceModel, setVoiceModel] = useState(scene.voice_model || "");
  const [saving, setSaving] = useState(false);
  const [translating, setTranslating] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        narration: text,
        language: lang !== "auto" ? lang : undefined,
      };
      if (voice !== "") payload.voice = voice;
      if (voiceModel !== "") payload.voice_model = voiceModel;
      await API.patch(`/projects/${projectId}/scenes/${scene.id}/narration`, payload);
      toast.success("Narration updated");
      setOpen(false);
      await onReload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally { setSaving(false); }
  };

  const translate = async () => {
    if (!lang || lang === "auto") { toast.error("Pick a target language first"); return; }
    setTranslating(true);
    try {
      const { data } = await API.patch(`/projects/${projectId}/scenes/${scene.id}/narration`, {
        language: lang,
      });
      setText(data.narration || "");
      toast.success(`Translated to ${lang}`);
      await onReload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Translation failed");
    } finally { setTranslating(false); }
  };

  const currentLangLabel = LANGUAGES.find((l) => l.id === (scene.language || "auto"))?.label || (scene.language || "Auto");
  // Effective voice for preview
  const effectiveVoice = (voice || scene.voice) || "onyx";
  const effectiveModel = (voiceModel || scene.voice_model) || "tts-1";

  return (
    <div className="mt-3 p-3 rounded border border-white/5 bg-black/40">
      <div className="flex items-center justify-between mb-2 gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="overline">Narration</span>
          {scene.language && scene.language !== "auto" && (
            <Pill tone="gold">{currentLangLabel.split(" ")[0]}</Pill>
          )}
          {scene.voice && (
            <Pill tone="neutral">voice · {scene.voice}</Pill>
          )}
        </div>
        <button
          className="text-[11px] text-white/50 hover:text-gold transition"
          onClick={() => setOpen((v) => !v)}
          data-testid={`narration-edit-${scene.id}`}
        >
          {open ? "Cancel" : "Edit / translate"}
        </button>
      </div>

      {!open ? (
        <p className="text-sm italic text-white/80" data-testid={`narration-text-${scene.id}`}>
          &ldquo;{scene.narration}&rdquo;
        </p>
      ) : (
        <div className="space-y-3">
          <textarea
            className="textarea-field text-sm min-h-[100px]"
            value={text}
            onChange={(e) => setText(e.target.value)}
            data-testid={`narration-textarea-${scene.id}`}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="overline">Language (overrides project default)</label>
              <select
                className="input-field mt-1"
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                data-testid={`narration-lang-${scene.id}`}
              >
                {(() => {
                  const groups = {};
                  LANGUAGES.forEach((l) => {
                    const g = l.region || "General";
                    (groups[g] = groups[g] || []).push(l);
                  });
                  const order = ["", "General", "South Asia", "Europe & Global", "Europe", "East Asia", "SE Asia", "Middle East", "Caucasus", "Central Asia", "Asia", "Africa", "Americas", "Pacific"];
                  const keys = Object.keys(groups).sort(
                    (a, b) => (order.indexOf(a) + 100) - (order.indexOf(b) + 100)
                  );
                  return keys.map((k) => (
                    <optgroup key={k} label={k || "General"}>
                      {groups[k].map((l) => (
                        <option key={l.id} value={l.id}>{l.label}</option>
                      ))}
                    </optgroup>
                  ));
                })()}
              </select>
            </div>
            <div>
              <label className="overline">Voice (per-scene override)</label>
              <div className="flex gap-2 mt-1">
                <select
                  className="input-field flex-1"
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                  data-testid={`narration-voice-${scene.id}`}
                >
                  <option value="">Use project default</option>
                  {VOICES.map((v) => (
                    <option key={v.id} value={v.id}>{v.id} — {v.desc}</option>
                  ))}
                </select>
                <VoicePreview
                  voice={effectiveVoice}
                  model={effectiveModel}
                  language={lang}
                  testid={`narration-preview-${scene.id}`}
                />
              </div>
            </div>
            <div>
              <label className="overline">Voice quality</label>
              <select
                className="input-field mt-1"
                value={voiceModel}
                onChange={(e) => setVoiceModel(e.target.value)}
                data-testid={`narration-model-${scene.id}`}
              >
                <option value="">Use project default</option>
                <option value="tts-1">tts-1 (fast)</option>
                <option value="tts-1-hd">tts-1-hd (studio)</option>
              </select>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 justify-end">
            <button className="btn-ghost text-xs" onClick={translate} disabled={translating} data-testid={`narration-translate-${scene.id}`}>
              {translating ? <Spinner /> : <Globe className="w-3.5 h-3.5" />} Translate to selected
            </button>
            <button className="btn-gold text-xs" onClick={save} disabled={saving} data-testid={`narration-save-${scene.id}`}>
              {saving ? <Spinner /> : <Check className="w-3.5 h-3.5" />} Save
            </button>
          </div>
          <p className="text-[11px] text-white/40">
            After saving or translating, regenerate the narration audio (Narration button below) to hear the change.
          </p>
        </div>
      )}
    </div>
  );
};

// ---------- Improved Batch Progress Card ----------
const STEP_ICONS = {
  image: ImageIcon,
  narration: Volume2,
  video: Video,
  mux: Sparkles,
  assembling: Film,
  starting: Loader2,
  queued: Loader2,
  done: Check,
};

const STEP_LABEL = {
  image: "Painting storyboard",
  narration: "Voicing narration",
  video: "Animating scene",
  mux: "Adding audio + subtitles",
  assembling: "Assembling final film",
  starting: "Warming up",
  queued: "Queued",
  done: "Finished",
};

const formatElapsed = (startedAt) => {
  if (!startedAt) return "";
  const s = Math.max(0, Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
};

const BatchProgressCard = ({ batch, project, percent }) => {
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!batch?.running) return;
    const t = setInterval(() => setTick((v) => v + 1), 1000);
    return () => clearInterval(t);
  }, [batch?.running]);

  const scenes = project.scenes || [];
  // Parse batch.current like "scene_1:image" -> { sid, step }
  const parseCurrent = (cur) => {
    if (!cur || cur.indexOf(":") < 0) return { sid: null, step: cur };
    const [sid, step] = cur.split(":");
    return { sid, step };
  };
  const { sid: curSid, step: curStep } = parseCurrent(batch.current);
  const curScene = scenes.find((s) => s.id === curSid);
  const StepIcon = STEP_ICONS[curStep] || Sparkles;
  const stepLabel = STEP_LABEL[curStep] || curStep || "Processing";

  const elapsed = formatElapsed(batch.started_at);

  return (
    <div>
      {/* Top status */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="overline flex items-center gap-2">
            {batch.running ? <span className="w-2 h-2 rounded-full bg-gold animate-pulse" /> : <Check className="w-3 h-3 text-gold" />}
            {batch.running ? "Auto-Pilot running" : "Auto-Pilot finished"}
          </div>
          <div className="mt-2 flex items-center gap-3">
            <StepIcon className={`w-5 h-5 text-gold ${batch.running ? "animate-pulse" : ""}`} />
            <div>
              <div className="font-display text-lg">{stepLabel}</div>
              {curScene && (
                <div className="text-xs text-white/50 mt-0.5">
                  Scene {scenes.findIndex((s) => s.id === curSid) + 1} · {curScene.title}
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono text-2xl text-gold">{percent}%</div>
          <div className="text-[11px] text-white/40 uppercase tracking-widest">
            {batch.completed} / {batch.total} steps · {elapsed}
          </div>
        </div>
      </div>

      {/* Bar */}
      <div className="h-2 rounded-full bg-white/5 overflow-hidden mt-4">
        <motion.div
          className="h-full bg-gradient-to-r from-gold to-yellow-300"
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>

      {/* Per-scene grid */}
      <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2" data-testid="batch-scene-grid">
        {scenes.map((s, idx) => {
          const isCurrent = s.id === curSid;
          const done = {
            image: !!s.image_file,
            video: !!s.video_file,
            audio: !!s.audio_file,
            final: !!s.final_file,
          };
          const allDone = done.image && done.video && done.audio;
          return (
            <div
              key={s.id}
              className={`p-2 rounded-md border text-[10px] font-mono transition ${
                isCurrent && batch.running
                  ? "border-gold/60 bg-gold/10 shadow-goldGlow"
                  : allDone
                    ? "border-white/10 bg-black/40"
                    : "border-white/5 bg-black/30"
              }`}
              title={s.title}
              data-testid={`batch-scene-${s.id}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-gold">{String(idx + 1).padStart(2, "0")}</span>
                {isCurrent && batch.running && <Loader2 className="w-3 h-3 animate-spin text-gold" />}
                {!isCurrent && allDone && <Check className="w-3 h-3 text-gold" />}
              </div>
              <div className="mt-1 text-white/70 truncate">{s.title}</div>
              <div className="mt-1.5 flex gap-1">
                <span className={`w-1.5 h-1.5 rounded-full ${done.image ? "bg-gold" : "bg-white/15"}`} title="image" />
                <span className={`w-1.5 h-1.5 rounded-full ${done.audio ? "bg-gold" : "bg-white/15"}`} title="audio" />
                <span className={`w-1.5 h-1.5 rounded-full ${done.video ? "bg-gold" : "bg-white/15"}`} title="video" />
                <span className={`w-1.5 h-1.5 rounded-full ${done.final ? "bg-gold" : "bg-white/15"}`} title="final" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};


// ---------- Multilingual Auto-Dub Panel ----------
const POPULAR_DUB_LANGS = [
  { id: "hi", label: "Hindi", native: "हिन्दी" },
  { id: "en", label: "English", native: "English" },
  { id: "es", label: "Spanish", native: "Español" },
  { id: "fr", label: "French", native: "Français" },
  { id: "de", label: "German", native: "Deutsch" },
  { id: "pt", label: "Portuguese", native: "Português" },
  { id: "ar", label: "Arabic", native: "العربية" },
  { id: "zh", label: "Mandarin", native: "中文" },
  { id: "ja", label: "Japanese", native: "日本語" },
  { id: "ko", label: "Korean", native: "한국어" },
  { id: "ru", label: "Russian", native: "Русский" },
  { id: "id", label: "Indonesian", native: "Bahasa" },
  { id: "sw", label: "Swahili", native: "Kiswahili" },
  { id: "bn", label: "Bengali", native: "বাংলা" },
  { id: "ta", label: "Tamil", native: "தமிழ்" },
  { id: "te", label: "Telugu", native: "తెలుగు" },
];

const DubPanel = ({ project, onReload }) => {
  const [selected, setSelected] = useState([]);
  const [customLang, setCustomLang] = useState("");
  const [starting, setStarting] = useState(false);
  const [dubs, setDubs] = useState(project.dubs || []);
  const [dubJob, setDubJob] = useState(project.dub_job || null);
  const esRef = useRef(null);
  const userId = getUserId();

  const fetchDubs = useCallback(async () => {
    try {
      const { data } = await API.get(`/projects/${project.id}/dubs`);
      setDubs(data.dubs || []);
      setDubJob(data.dub_job || null);
    } catch (e) { /* ignore */ }
  }, [project.id]);

  useEffect(() => { fetchDubs(); }, [fetchDubs]);

  // SSE stream for dub progress
  useEffect(() => {
    if (!dubJob?.running) return;
    const url = `${process.env.REACT_APP_BACKEND_URL}/api/projects/${project.id}/batch/stream`;
    const es = new EventSource(url);
    esRef.current = es;
    const handle = (ev) => {
      try {
        const payload = JSON.parse(ev.data);
        if (payload.dub_job) setDubJob(payload.dub_job);
      } catch (e) { /* ignore */ }
    };
    es.addEventListener("progress", handle);
    es.addEventListener("done", async (ev) => {
      handle(ev);
      es.close();
      esRef.current = null;
      await fetchDubs();
      await onReload();
      toast.success("Multilingual dub finished");
    });
    es.onerror = () => { es.close(); esRef.current = null; };
    return () => { es.close(); esRef.current = null; };
  }, [dubJob?.running, project.id, fetchDubs, onReload]);

  const toggleLang = (id) => {
    setSelected((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  };

  const addCustom = () => {
    const l = customLang.trim();
    if (!l) return;
    if (selected.length >= 10) { toast.error("Max 10 languages per job"); return; }
    if (!selected.includes(l)) setSelected([...selected, l]);
    setCustomLang("");
  };

  const startDub = async () => {
    if (selected.length === 0) { toast.error("Pick at least one language"); return; }
    setStarting(true);
    try {
      await API.post(`/projects/${project.id}/dub`, { languages: selected });
      toast.success("Dub job started");
      setDubJob({ running: true, total: 0, completed: 0, current: "starting", languages: selected });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Dub start failed");
    } finally { setStarting(false); }
  };

  const dubPercent = dubJob?.total ? Math.min(100, Math.round((dubJob.completed / dubJob.total) * 100)) : 0;
  const canDub = !!project.final_film;

  return (
    <div className="mt-6 rounded-md border border-white/10 bg-black/30 p-5" data-testid="dub-panel">
      <div className="flex items-center gap-2 mb-2">
        <Languages className="w-4 h-4 text-gold" />
        <div className="font-display text-lg">Multilingual auto-dub</div>
      </div>
      <p className="text-xs text-white/50 mb-4">
        Render your film into any number of languages in one click. Each dub gets translated narration,
        native-language TTS, embedded soft subtitles, and its own downloadable MP4.
      </p>

      {!canDub && (
        <div className="text-sm text-white/60 italic">Assemble the primary film first, then multilingual dubs unlock.</div>
      )}

      {canDub && (
        <>
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 mb-4">
            {POPULAR_DUB_LANGS.map((l) => {
              const on = selected.includes(l.id);
              return (
                <button
                  key={l.id}
                  onClick={() => toggleLang(l.id)}
                  disabled={dubJob?.running}
                  className={`p-2 rounded-md border text-left text-xs transition ${
                    on ? "border-gold/60 bg-gold/10 text-gold" : "border-white/10 hover:border-white/25"
                  }`}
                  data-testid={`dub-lang-${l.id}`}
                >
                  <div className="font-medium">{l.label}</div>
                  <div className="text-[10px] opacity-70">{l.native}</div>
                </button>
              );
            })}
          </div>

          <div className="flex gap-2 mb-4">
            <input
              className="input-field text-sm"
              value={customLang}
              onChange={(e) => setCustomLang(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addCustom()}
              placeholder="Add any language (e.g. Yoruba, Māori, Sanskrit)…"
              data-testid="dub-custom-input"
            />
            <button className="btn-ghost text-xs" onClick={addCustom} data-testid="dub-add-custom">
              Add
            </button>
          </div>

          {selected.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-4">
              {selected.map((l) => (
                <span key={l} className="pill pill-gold flex items-center gap-1">
                  {l}
                  <button
                    onClick={() => setSelected(selected.filter((x) => x !== l))}
                    className="hover:text-red-300"
                    data-testid={`dub-remove-${l}`}
                    disabled={dubJob?.running}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          <button
            className="btn-gold w-full justify-center"
            onClick={startDub}
            disabled={starting || dubJob?.running || selected.length === 0}
            data-testid="dub-start-btn"
          >
            {(starting || dubJob?.running) ? <Spinner /> : <Rocket className="w-4 h-4" />}
            {dubJob?.running ? `Dubbing… ${dubPercent}%` : `Render ${selected.length || "N"} language${selected.length === 1 ? "" : "s"}`}
          </button>

          {dubJob && (dubJob.running || dubJob.total > 0) && (
            <div className="mt-4" data-testid="dub-progress">
              <div className="flex items-center justify-between text-xs mb-2">
                <span className="text-white/60 font-mono">{dubJob.current || "—"}</span>
                <span className="text-white/50 font-mono">{dubJob.completed}/{dubJob.total}</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-gold to-yellow-300 transition-all duration-500" style={{ width: `${dubPercent}%` }} />
              </div>
              {dubJob.errors && dubJob.errors.length > 0 && (
                <div className="mt-3 text-[11px] font-mono text-red-300/70 max-h-24 overflow-y-auto">
                  {dubJob.errors.slice(0, 5).map((e, i) => <div key={i}>{e}</div>)}
                </div>
              )}
            </div>
          )}

          {dubs.length > 0 && (
            <div className="mt-6" data-testid="dub-results">
              <div className="overline mb-3">Your dubs</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {dubs.map((d) => (
                  <div key={d.language} className="rounded-md border border-white/10 bg-black/40 p-3" data-testid={`dub-item-${d.language}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-display text-lg">{d.language}</div>
                        <div className="text-[10px] text-white/40 uppercase tracking-widest">
                          {d.size_mb} MB · {new Date(d.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <Pill tone="gold">MP4 + SRT</Pill>
                    </div>
                    <video
                      src={`${process.env.REACT_APP_BACKEND_URL}/api/projects/${project.id}/dubs/${encodeURIComponent(d.language)}/film?user_id=${userId}`}
                      controls
                      className="w-full mt-3 rounded"
                    />
                    <div className="grid grid-cols-2 gap-2 mt-3">
                      <a
                        className="btn-ghost text-xs justify-center"
                        href={`${process.env.REACT_APP_BACKEND_URL}/api/projects/${project.id}/dubs/${encodeURIComponent(d.language)}/film?user_id=${userId}`}
                        download
                        data-testid={`dub-download-${d.language}`}
                      >
                        <Download className="w-3 h-3" /> MP4
                      </a>
                      <a
                        className="btn-ghost text-xs justify-center"
                        href={`${process.env.REACT_APP_BACKEND_URL}/api/projects/${project.id}/subtitles?language=${encodeURIComponent(d.language)}`}
                        download
                        data-testid={`dub-srt-${d.language}`}
                      >
                        <Subtitles className="w-3 h-3" /> SRT
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

