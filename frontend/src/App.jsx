import React, { useEffect, useMemo, useRef, useState } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";

// Polished single-file React UI for your FastAPI backend.
// Endpoints used:
// - POST /auth/login (username, password)
// - GET  /api/v1/documents?skip=0&limit=50
// - POST /api/v1/documents/upload (multipart field: file)
// - POST /api/v1/analyze/:doc_id (form field: query)
// - GET  /api/v1/documents/:doc_id
// Styling: TailwindCSS only (no extra libs).
// Works in Vite with Node 22 LTS.

/**
 * Safe env access + API base resolution with fallbacks.
 */
function safeImportMetaEnv() {
  try { return (import.meta && import.meta.env) ? import.meta.env : {}; } catch { return {}; }
}
export function resolveApiBase(env = {}, options = {}) {
  const candidates = [env?.VITE_API_BASE, typeof window !== "undefined" ? window.__API_BASE__ : undefined, options?.fallback, "/"]; // same-origin default
  let found = candidates.find((v) => typeof v === "string" && v.trim());
  if (!found) found = "/";
  return found.replace(/\/$/, "");
}
const API_BASE = resolveApiBase(safeImportMetaEnv(), { fallback: "/" });

// Map backend status → badge tone (module scope so all components can use it)
export function toneForStatus(s) {
  const k = String(s || "").toLowerCase();
  if (k === "completed") return "green";
  if (k === "failed") return "red";
  if (k === "processing") return "yellow";
  return "gray";
}

// Safe Markdown → sanitized HTML
function mdToHtml(md) {
  try {
    const raw = marked.parse(md || "");
    return { __html: DOMPurify.sanitize(raw) };
  } catch {
    return { __html: DOMPurify.sanitize(String(md || "")) };
  }
}

// ---------- Small UI primitives (no external libs) ----------
const Button = ({ children, onClick, kind = "primary", className = "", ...rest }) => {
  const base = "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition active:scale-[.98] focus:outline-none focus:ring-2 focus:ring-offset-2";
  const styles = {
    primary: "bg-gradient-to-r from-indigo-600 to-violet-600 text-white hover:opacity-95 focus:ring-indigo-400",
    secondary: "bg-white/70 border border-gray-200 hover:bg-white text-gray-800 focus:ring-gray-300",
    ghost: "bg-transparent hover:bg-gray-100 text-gray-700",
    danger: "bg-rose-600 text-white hover:opacity-95 focus:ring-rose-300",
  };
  return (
    <button onClick={onClick} className={`${base} ${styles[kind]} ${className}`} {...rest}>
      {children}
    </button>
  );
};

const Card = ({ title, right, children, className = "" }) => (
  <div className={`rounded-2xl bg-white shadow-sm ring-1 ring-black/5 ${className}`}>
    {(title || right) && (
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-800">{title}</h2>
        <div>{right}</div>
      </div>
    )}
    <div className="p-5">{children}</div>
  </div>
);

const Field = ({ label, children, help }) => (
  <label className="block text-sm">
    <span className="text-gray-600">{label}</span>
    <div className="mt-1">{children}</div>
    {help && <p className="mt-1 text-xs text-gray-500">{help}</p>}
  </label>
);

const Badge = ({ children, tone = "gray" }) => {
  const tones = {
    gray: "bg-gray-100 text-gray-700",
    yellow: "bg-amber-100 text-amber-800",
    green: "bg-emerald-100 text-emerald-800",
    red: "bg-rose-100 text-rose-800",
    blue: "bg-blue-100 text-blue-800",
  };
  return <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${tones[tone]}`}>{children}</span>;
};

const Spinner = ({ size = 4 }) => (
  <div className={`inline-block h-${size} w-${size} animate-spin rounded-full border-2 border-current border-t-transparent text-gray-500 align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]`} />
);

// ---------- App ----------
export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("token") || "");
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("user");
    return raw ? JSON.parse(raw) : null;
  });

  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  const [docsLoading, setDocsLoading] = useState(false);
  const [docsError, setDocsError] = useState("");
  const [documents, setDocuments] = useState([]);

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const [query, setQuery] = useState("Provide a comprehensive, succinct financial analysis focusing on key metrics, risks, and recommendations.");

  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState("");
  const [polling, setPolling] = useState(false);

  const isAuthed = useMemo(() => Boolean(token), [token]);
  const pollTimer = useRef(null);

  useEffect(() => { if (isAuthed) refreshDocuments(); return () => stopPolling(); }, [isAuthed]);

  function stopPolling() {
    if (pollTimer.current) { clearInterval(pollTimer.current); pollTimer.current = null; }
    setPolling(false);
  }

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const opts = { ...options, headers };
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    const err = new Error(text || res.statusText);
    err.status = res.status;
    // capture Retry-After (seconds) if server sent it
    const ra = res.headers.get("retry-after");
    if (ra && !Number.isNaN(Number(ra))) err.retryAfter = Number(ra);
    throw err;
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}


  // ---- Auth ----
  async function login(username, password) {
    try {
      setAuthLoading(true); setAuthError("");
      const form = new FormData(); form.set("username", username); form.set("password", password);
      const data = await apiFetch("/auth/login", { method: "POST", body: form });
      setToken(data.access_token); setUser(data.user);
      localStorage.setItem("token", data.access_token); localStorage.setItem("user", JSON.stringify(data.user));
    } catch (e) { setAuthError(renderError(e)); } finally { setAuthLoading(false); }
  }
  function logout() { setToken(""); setUser(null); localStorage.removeItem("token"); localStorage.removeItem("user"); setDocuments([]); stopPolling(); }


  // ---- Sign up ----
async function signup({ username, password, full_name, email }) {
  try {
    setAuthLoading(true);
    setAuthError("");
    if (!username || !password) throw new Error("Username and password are required");

    // Try JSON first
    try {
      await apiFetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, full_name, email }),
      });
    } catch (e) {
      // Fallback to form-data if your backend expects multipart/form
      if (e && (e.status === 415 || e.status === 422)) {
        const form = new FormData();
        form.set("username", username);
        form.set("password", password);
        if (full_name) form.set("full_name", full_name);
        if (email) form.set("email", email);
        await apiFetch("/auth/register", { method: "POST", body: form });
      } else {
        throw e;
      }
    }

    // Auto-login
    await login(username, password);
  } catch (e) {
    setAuthError(renderError(e));
  } finally {
    setAuthLoading(false);
  }
}


  // ---- Docs ----
  async function refreshDocuments() {
    try {
      setDocsLoading(true); setDocsError("");
      const data = await apiFetch(`/api/v1/documents?skip=0&limit=50`);
      const rows = Array.isArray(data) ? data : (data.documents || []);
      setDocuments(rows);
    } catch (e) { setDocsError(renderError(e)); } finally { setDocsLoading(false); }
  }

  async function uploadFile(file) {
    try {
      setUploadError(""); setUploading(true);
      const form = new FormData(); form.set("file", file);
      const resp = await apiFetch("/api/v1/documents/upload", { method: "POST", body: form });
      await refreshDocuments(); if (resp?.id) await openDetail(resp.id);
    } catch (e) { setUploadError(renderError(e)); } finally { setUploading(false); }
  }

  async function openDetail(id) {
    try { setDetailError(""); const d = await apiFetch(`/api/v1/documents/${id}`); setDetail(d); }
    catch (e) { setDetailError(renderError(e)); }
  }

  async function analyze(id) {
    try { const form = new FormData(); form.set("query", query); await apiFetch(`/api/v1/analyze/${id}`, { method: "POST", body: form }); startPollingDoc(id); }
    catch (e) { alert(renderError(e)); }
  }

  function startPollingDoc(id) {
    stopPolling(); setPolling(true); openDetail(id);
    pollTimer.current = setInterval(async () => {
      try {
        const d = await apiFetch(`/api/v1/documents/${id}`); setDetail(d);
        setDocuments((prev) => prev.map((x) => (x.id === id ? { ...x, status: d.status, processed_date: d.processed_date } : x)));
        if (d.status && ["completed", "failed", "COMPLETED", "FAILED"].includes(String(d.status))) stopPolling();
      } catch (e) { if (e.status !== 429) stopPolling(); }
    }, 1600);
  }

  // ---- UI helpers ----
  function toneForStatus(s) {
    const k = String(s || "").toLowerCase();
    if (k === "completed") return "green"; if (k === "failed") return "red"; if (k === "processing") return "yellow"; return "gray";
  }

return (
  <div className="min-h-screen overflow-x-hidden bg-gradient-to-br from-slate-50 via-indigo-50 to-violet-50 text-gray-900">
    <TopBar isAuthed={isAuthed} user={user} onLogout={logout} />

    <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
      {!isAuthed ? (
        <div className="mt-10">
          <AuthCard loading={authLoading} error={authError} onLogin={login} onSignup={signup} />
        </div>
      ) : (
        <>
          {/* Main 2-col grid */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mt-10">
            {/* Left: upload + list */}
            <div className="xl:col-span-2 space-y-6">
              <Card title="Upload a Document" right={<StatusLegend />}>
                <Uploader onUpload={uploadFile} uploading={uploading} error={uploadError} />
              </Card>

              <Card title="Your Documents" right={<Button kind="secondary" onClick={refreshDocuments}>Refresh</Button>}>
                <DocumentsTable
                  documents={documents}
                  loading={docsLoading}
                  error={docsError}
                  onOpen={openDetail}
                  onAnalyze={analyze}
                />
              </Card>
            </div>

            {/* Right: query + environment */}
            <div className="space-y-6">
              <Card title="Analysis Query">
                <Field label="Prompt">
                  <textarea
                    className="w-full rounded-xl border border-gray-200 bg-white/60 px-3 py-2 focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 min-h-[110px]"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </Field>
                <p className="mt-2 text-xs text-gray-500">
                  Sent as the <code>query</code> field to the analyze endpoint.
                </p>
              </Card>

              {/* <Card title="Environment">
                <p className="text-sm text-gray-600 mb-2">API Base resolved to:</p>
                <code className="text-xs bg-gray-900/90 text-indigo-100 rounded px-2 py-1">{API_BASE || "/"}</code>
              </Card> */}
            </div>
          </div>

          {/* Full-width detail below */}
          <div className="mt-6">
            <Card
              title="Document Detail"
              right={polling ? <Badge tone="yellow">Polling <span className="ml-1"><Spinner /></span></Badge> : null}
            >
              <DetailPanel detail={detail} error={detailError} onAnalyze={analyze} />
            </Card>
          </div>
        </>
      )}
    </main>
  </div>
);
}

// ---------- Sections ----------
function TopBar({ isAuthed, user, onLogout }) {
  return (
    <header className="sticky top-0 z-30 bg-white/70 backdrop-blur border-b border-gray-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-3 overflow-x-hidden">
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-9 w-9 shrink-0 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600" />
          <div className="min-w-0">
            <h1 className="text-base font-semibold text-gray-800 leading-tight truncate">
              Financial Document Analyzer
            </h1>
            <p className="text-xs text-gray-500 truncate">
              Analyze → Extract metrics → Risks → Recommendations
            </p>
          </div>
        </div>

        {isAuthed && (
          <div className="flex items-center gap-3 shrink-0">
            <span className="hidden sm:inline max-w-[40vw] truncate text-sm text-gray-600">
              {user?.full_name || user?.username}
            </span>
            <Button kind="secondary" onClick={onLogout}>Logout</Button>
          </div>
        )}
      </div>
    </header>
  );
}


function AuthCard({ loading, error, onLogin, onSignup }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [formError, setFormError] = useState("");

  async function submit() {
    try {
      setFormError("");
      if (mode === "login") {
        await onLogin(username, password);
      } else {
        if (!username || !password) throw new Error("Username and password are required");
        if (password !== confirm) throw new Error("Passwords do not match");
        await onSignup({ username, password, full_name: fullName, email });
      }
    } catch (e) {
      setFormError(renderError(e));
    }
  }

  return (
    <Card title={mode === "login" ? "Login" : "Sign Up"}>
      <div className="flex items-center gap-2 mb-4">
        <button
          className={`text-xs px-3 py-1.5 rounded-full border ${mode === "login" ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-700 border-gray-200"}`}
          onClick={() => setMode("login")}
        >Login</button>
        <button
          className={`text-xs px-3 py-1.5 rounded-full border ${mode === "signup" ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-700 border-gray-200"}`}
          onClick={() => setMode("signup")}
        >Sign Up</button>
      </div>

      {mode === "signup" && (
        <div className="grid gap-4 mb-2">
          <Field label="Full name (optional)">
            <input className="w-full rounded-xl border border-gray-200 bg-white/70 px-3 py-2 focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300"
                   value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Jane Doe" />
          </Field>
          <Field label="Email (optional)">
            <input type="email" className="w-full rounded-xl border border-gray-200 bg-white/70 px-3 py-2 focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300"
                   value={email} onChange={(e) => setEmail(e.target.value)} placeholder="jane@example.com" />
          </Field>
        </div>
      )}

      <div className="grid gap-4">
        <Field label="Username">
          <input className="w-full rounded-xl border border-gray-200 bg-white/70 px-3 py-2 focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300"
                 value={username} onChange={(e) => setUsername(e.target.value)} placeholder="jane.doe" />
        </Field>
        <Field label="Password">
          <input type="password" className="w-full rounded-xl border border-gray-200 bg-white/70 px-3 py-2 focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300"
                 value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        </Field>
        {mode === "signup" && (
          <Field label="Confirm password">
            <input type="password" className="w-full rounded-xl border border-gray-200 bg-white/70 px-3 py-2 focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300"
                   value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="••••••••" />
          </Field>
        )}
        {(formError || error) && <p className="text-sm text-rose-600">{formError || error}</p>}
        <div className="flex items-center gap-3">
          <Button onClick={submit} disabled={loading}>
            {loading ? <>Please wait… <span className="ml-1"><span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" /></span></> : (mode === "login" ? "Login" : "Create account")}
          </Button>
          {mode === "login" && (
            <button className="text-xs text-gray-600 hover:text-gray-800" onClick={() => setMode("signup")}>
              Need an account? Sign up
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}


function Uploader({ onUpload, uploading, error }) {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files?.[0]; if (f) setFile(f); }}
        className={`rounded-2xl border-2 border-dashed ${dragOver ? "border-indigo-400 bg-indigo-50/50" : "border-gray-300 bg-gray-50/60"} p-6 text-center`}
      >
        <p className="text-sm text-gray-700">Drag & drop your file here, or click to select</p>
        <input type="file" className="sr-only" id="hiddenFile" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <div className="mt-3 flex items-center justify-center gap-3">
          <Button kind="secondary" onClick={() => document.getElementById("hiddenFile").click()}>Choose File</Button>
          <span className="text-xs text-gray-500">PDF, DOCX, or TXT</span>
        </div>
        {file && <p className="mt-2 text-xs text-gray-600">Selected: <span className="font-medium">{file.name}</span></p>}
      </div>
      <div className="mt-4 flex items-center gap-3">
        <Button onClick={() => file && onUpload(file)} disabled={!file || uploading}>{uploading ? <>Uploading… <Spinner /></> : "Upload"}</Button>
        {error && <span className="text-sm text-rose-600">{error}</span>}
      </div>
    </div>
  );
}

function DocumentsTable({ documents, loading, error, onOpen, onAnalyze }) {
  if (loading) return <TableSkeleton />;
  if (error) return <p className="text-sm text-rose-600">{error}</p>;
  if (!documents?.length) return <EmptyState />;

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-600">
          <tr>
            <Th>File</Th>
            <Th>Status</Th>
            <Th>Processed</Th>
            <Th className="text-right pr-4">Actions</Th>
          </tr>
        </thead>
        <tbody>
          {documents.map((d) => (
            <tr key={d.id} className="border-t border-gray-100 hover:bg-indigo-50/30">
              <Td>{d.original_filename || d.filename || d.id}</Td>
              <Td><Badge tone={toneForStatus(d.status)}>{String(d.status || "").toLowerCase() || "—"}</Badge></Td>
              <Td>{d.processed_date ? new Date(d.processed_date).toLocaleString() : "—"}</Td>
              <Td className="text-right">
                <div className="flex justify-end gap-2 pr-2">
                  <Button kind="secondary" onClick={() => onOpen(d.id)}>View</Button>
                  <Button onClick={() => onAnalyze(d.id)}>Analyze</Button>
                </div>
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const Th = ({ children, className = "" }) => (
  <th className={`text-left py-2.5 pl-4 ${className}`}>{children}</th>
);
const Td = ({ children, className = "" }) => (
  <td className={`py-3 pl-4 align-middle ${className}`}>{children}</td>
);

function TableSkeleton() {
  return (
    <div className="animate-pulse space-y-2">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="h-12 rounded-lg bg-gray-100" />
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="h-14 w-14 rounded-2xl bg-gray-100 flex items-center justify-center">📄</div>
      <p className="mt-3 text-sm text-gray-700">No documents yet.</p>
      <p className="text-xs text-gray-500">Upload a file to get started.</p>
    </div>
  );
}

function DetailPanel({ detail, error, onAnalyze }) {
  if (error) return <p className="text-sm text-rose-600">{error}</p>;
  if (!detail) return <p className="text-sm text-gray-500">Select a document to inspect.</p>;

  // Normalize payload: some APIs put the analysis under detail.analysis (object),
  // others return strings at the top level. We unify to a single payload object.
  const payload = (detail && detail.analysis && typeof detail.analysis === "object" && !Array.isArray(detail.analysis))
    ? detail.analysis
    : detail;

  const statusTone = toneForStatus(detail.status);
  const metaSource = detail.source || payload.source;
  const metaQuery  = detail.query_used || payload.query_used;

  // Two shapes supported:
  // 1) Structured: { summary, key_metrics, risks, recommendations }
  // 2) Unstructured: { verification: string, analysis: string, risk: string, recommendation: string }
  const isStructured = !!(payload && typeof payload === "object" && (
    payload.summary || payload.key_metrics || payload.risks || payload.recommendations
  ));

  const verification   = payload.verification;
  const analysisStr    = payload.analysis; // when it's a markdown/string blob
  const risk           = payload.risk;
  const recommendation = payload.recommendation;

  return (
    <div className="space-y-5">
      {/* Meta */}
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={statusTone}>{String(detail.status || "").toLowerCase() || "—"}</Badge>
        {detail.processed_date && (
          <span className="text-xs text-gray-500">Processed {new Date(detail.processed_date).toLocaleString()}</span>
        )}
        {metaSource && <span className="text-xs text-gray-400">Source: {String(metaSource)}</span>}
        {metaQuery && (
          <span className="text-[11px] text-gray-500 bg-gray-100 rounded px-1.5 py-0.5">Query: {String(metaQuery)}</span>
        )}
      </div>

      {/* Render depending on shape */}
      {isStructured ? (
        <div className="space-y-4">
          {payload.summary && (
            <section>
              <h3 className="text-sm font-semibold text-gray-800 mb-1">Summary</h3>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{payload.summary}</p>
            </section>
          )}

          {payload.key_metrics && (
            <section>
              <h3 className="text-sm font-semibold text-gray-800 mb-2">Key Metrics</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {Object.entries(payload.key_metrics).map(([k, v]) => (
                  <div key={k} className="rounded-xl border border-gray-200 bg-gray-50/50 p-3">
                    <div className="text-xs uppercase tracking-wide text-gray-500">{k}</div>
                    <div className="text-sm font-medium text-gray-800">{String(v)}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {Array.isArray(payload.risks) && payload.risks.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-800 mb-2">Risks</h3>
              <ul className="list-disc pl-5 text-sm text-gray-700 space-y-1">
                {payload.risks.map((r, i) => <li key={i}>{String(r)}</li>)}
              </ul>
            </section>
          )}

          {Array.isArray(payload.recommendations) && payload.recommendations.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-800 mb-2">Recommendations</h3>
              <ul className="list-disc pl-5 text-sm text-gray-700 space-y-1">
                {payload.recommendations.map((r, i) => <li key={i}>{String(r)}</li>)}
              </ul>
            </section>
          )}
        </div>
      ) : (
        // Legacy/unstructured shape — render Markdown sections nicely
        <div className="space-y-4">
          {verification && (
            <section>
              <h3 className="text-sm font-semibold text-gray-800 mb-2">Verification</h3>
              <div className="text-sm text-gray-800 leading-relaxed [&>p]:mb-2 [&>ul]:list-disc [&>ul]:pl-5 [&>li]:mb-1" dangerouslySetInnerHTML={mdToHtml(verification)} />
            </section>
          )}
          {analysisStr && (
            <section>
              <h3 className="text-sm font-semibold text-gray-800 mb-2">Analysis</h3>
              <div className="text-sm text-gray-800 leading-relaxed [&>p]:mb-2 [&>ul]:list-disc [&>ul]:pl-5 [&>li]:mb-1" dangerouslySetInnerHTML={mdToHtml(analysisStr)} />
            </section>
          )}
          {risk && (
            <section>
              <h3 className="text-sm font-semibold text-gray-800 mb-2">Risk Assessment</h3>
              <div className="text-sm text-gray-800 leading-relaxed [&>p]:mb-2 [&>ul]:list-disc [&>ul]:pl-5 [&>li]:mb-1" dangerouslySetInnerHTML={mdToHtml(risk)} />
            </section>
          )}
          {recommendation && (
            <section>
              <h3 className="text-sm font-semibold text-gray-800 mb-2">Recommendation</h3>
              <div className="text-sm text-gray-800 leading-relaxed [&>p]:mb-2 [&>ul]:list-disc [&>ul]:pl-5 [&>li]:mb-1" dangerouslySetInnerHTML={mdToHtml(recommendation)} />
            </section>
          )}
          {!verification && !analysisStr && !risk && !recommendation && (
            <div className="text-sm text-gray-500">No analysis yet. Choose a document and click <span className="font-medium">Analyze</span>.</div>
          )}
        </div>
      )}

      {/* Raw JSON */}
      {/* <details className="group rounded-xl border border-gray-200 bg-white open:bg-gray-50/60">
        <summary className="cursor-pointer px-3 py-2 text-sm text-gray-700 group-open:rounded-b-none">View raw JSON</summary>
        <pre className="p-3 text-xs overflow-auto max-h-[320px]">{JSON.stringify(payload, null, 2)}</pre>
      </details> */}

      {detail.id && (
        <div className="pt-2">
          <Button onClick={() => onAnalyze(detail.id)}>Analyze this document</Button>
        </div>
      )}
    </div>
  );
}

function StatusLegend() {
  return (
    <div className="hidden md:flex items-center gap-2 text-xs text-gray-500">
      <span>Status:</span>
      <Badge tone="gray">uploaded</Badge>
      <Badge tone="yellow">processing</Badge>
      <Badge tone="green">completed</Badge>
      <Badge tone="red">failed</Badge>
    </div>
  );
}

function renderError(e) {
  if (!e) return ""; if (typeof e === "string") return e; try { const parsed = JSON.parse(e.message || ""); return parsed?.detail || e.message || "Request failed"; } catch { return e.message || "Request failed"; }
}

// ---------------------------
// Lightweight UI Helper Tests
// ---------------------------
export function runUiHelperTests() {
  const assert = (name, cond) => { if (!cond) throw new Error(name); };
  assert("toneForStatus completed", toneForStatus("completed") === "green");
  assert("toneForStatus failed", toneForStatus("failed") === "red");
  assert("toneForStatus processing", toneForStatus("processing") === "yellow");
  assert("toneForStatus other", toneForStatus("uploaded") === "gray");
}
if (typeof window !== "undefined" && window.__RUN_FRONTEND_TESTS__) {
  try { runUiHelperTests(); console.log("✓ UI helper tests passed"); } catch (e) { console.error("UI helper tests failed", e); }
}
