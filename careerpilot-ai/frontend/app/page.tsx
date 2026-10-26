"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowUpRight, BriefcaseBusiness, BrainCircuit, CheckCircle2, ChevronDown,
  CircleHelp, FileSearch, FileText, GraduationCap, LayoutDashboard, ListChecks,
  Lock, LogIn, LogOut, Menu, Mic2, Search, Settings2, ShieldCheck, Sparkles, Target,
  TrendingUp, UploadCloud, User as UserIcon, X, Zap
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// Use relative API path to leverage Next.js proxy rewrites for same-origin cookies,
// falling back to NEXT_PUBLIC_API_URL if explicitly specified.
const API = process.env.NEXT_PUBLIC_API_URL || "";

// ── Domain types ──────────────────────────────────────────────────────────────
type AuthUser = { id: number; email: string; full_name?: string | null; created_at?: string | null };
type Job = { id: string; title: string; company: string; location: string; description: string; is_demo: boolean };
type Gap = { target_role: string; known_role_template: boolean; coverage_score: number; matched_skills: {skill:string;importance:number}[]; missing_skills: {skill:string;importance:number}[]; message?: string };
type Application = { id: number; company: string; role: string; status: string; source_url?: string; notes?: string; user_id?: number };
type MatchResult = { similarity_score: number; matched_skills: string[]; missing_skills: string[]; resume_skills: string[]; job_skills: string[]; interpretation: string; role_gap?: Gap };
type ResumeResult = { id?: number; filename: string; skill_count: number; skills: string[]; suggestions: string[]; notice: string; extracted_text_preview: string };
type EvaluationResult = { practice_score: number; rubric: Record<string, number>; suggestions: string[]; disclaimer: string };
type InterviewQuestion = { question: string; focus: string[]; role_context: string; category: string; source: string };

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : "Could not connect to API.";
}

const trend = [
  { week: "W1", readiness: 34, practice: 22 }, { week: "W2", readiness: 39, practice: 31 },
  { week: "W3", readiness: 43, practice: 36 }, { week: "W4", readiness: 48, practice: 42 },
  { week: "W5", readiness: 54, practice: 49 }, { week: "W6", readiness: 61, practice: 57 },
];

const nav = [
  { label: "Overview", icon: LayoutDashboard }, { label: "Resume Intelligence", icon: FileSearch },
  { label: "Job Matching", icon: Target }, { label: "Skill Roadmap", icon: GraduationCap },
  { label: "Mock Interview", icon: Mic2 }, { label: "Applications", icon: BriefcaseBusiness },
];

export default function Home() {
  const [active, setActive] = useState("Overview");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [apiStatus, setApiStatus] = useState<"checking"|"online"|"offline">("checking");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [applicationsLoading, setApplicationsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [targetRole, setTargetRole] = useState("Data Scientist");
  const [skillsInput, setSkillsInput] = useState("python, sql");
  const [matchResult, setMatchResult] = useState<MatchResult|null>(null);
  const [gapResult, setGapResult] = useState<Gap|null>(null);
  const [resumeResult, setResumeResult] = useState<ResumeResult|null>(null);
  const [loading, setLoading] = useState(false);
  const [newCompany, setNewCompany] = useState("");
  const [newRole, setNewRole] = useState("");
  const [newStatus, setNewStatus] = useState("Applied");
  const [interviewCategory, setInterviewCategory] = useState("technical");
  const [interviewQuestions, setInterviewQuestions] = useState<InterviewQuestion[]>([]);
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState<EvaluationResult|null>(null);
  const [currentQuestion, setCurrentQuestion] = useState("");

  // ── Authentication state ──────────────────────────────────────────────────
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authFullName, setAuthFullName] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  // ── Initial Mount & Session Hydration ─────────────────────────────────────
  useEffect(() => {
    fetch(`${API}/health`).then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(() => setApiStatus("online")).catch(() => setApiStatus("offline"));
    loadJobs();
    checkAuth();
  }, []);

  async function checkAuth() {
    try {
      const res = await fetch(`${API}/api/auth/me`, { credentials: "include" });
      if (res.ok) {
        const u = await res.json();
        setUser(u);
        loadApplications();
        loadLatestResume();
        loadLatestRoadmap();
        loadLatestInterview();
      } else {
        setUser(null);
        setApplications([]);
        loadLatestResume();
        loadLatestRoadmap();
        loadLatestInterview();
      }
    } catch {
      setUser(null);
    }
  }

  async function loadJobs() {
    try { const r = await fetch(`${API}/api/jobs`); const d = await r.json(); setJobs(d.items || []); }
    catch { setJobs([]); }
  }

  // ── Persisted Applications ────────────────────────────────────────────────
  async function loadApplications(authToken?: string | null) {
    setApplicationsLoading(true);
    const curToken = authToken !== undefined ? authToken : token;
    const headers: Record<string, string> = {};
    if (curToken) headers["Authorization"] = `Bearer ${curToken}`;
    try {
      const r = await fetch(`${API}/api/applications`, {
        credentials: "include",
        headers,
      });
      if (r.status === 401) {
        setApplications([]);
        return;
      }
      const d = await r.json();
      setApplications(d.items || []);
    } catch {
      setApplications([]);
    } finally {
      setApplicationsLoading(false);
    }
  }

  async function addApplication() {
    if (!user) {
      setAuthMode("login");
      setAuthModalOpen(true);
      setMessage("Please sign in to save and manage job applications.");
      return;
    }
    if (!newCompany.trim() || !newRole.trim()) { setMessage("Enter both company and role."); return; }
    setLoading(true);
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
      const r = await fetch(`${API}/api/applications`, {
        method: "POST",
        headers,
        credentials: "include",
        body: JSON.stringify({ company: newCompany, role: newRole, status: newStatus }),
      });
      const d = await r.json();
      if (r.status === 401) {
        setUser(null);
        setAuthModalOpen(true);
        throw new Error("Session expired. Please sign in again.");
      }
      if (!r.ok) throw new Error(d.detail || "Could not add application");
      setNewCompany(""); setNewRole(""); setMessage("Application saved to database.");
      await loadApplications();
    } catch(e) { setMessage(errMsg(e)); }
    finally { setLoading(false); }
  }

  async function changeStatus(item: Application, status: string) {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
      const r = await fetch(`${API}/api/applications/${item.id}`, {
        method: "PATCH",
        headers,
        credentials: "include",
        body: JSON.stringify({ status }),
      });
      if (r.status === 401) {
        setUser(null);
        setAuthModalOpen(true);
        setMessage("Session expired. Please sign in again.");
        return;
      }
      await loadApplications();
    } catch {
      setMessage("Could not update application.");
    }
  }

  async function deleteApp(id: number) {
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
      const r = await fetch(`${API}/api/applications/${id}`, {
        method: "DELETE",
        headers,
        credentials: "include",
      });
      if (r.status === 401) {
        setUser(null);
        setAuthModalOpen(true);
        setMessage("Session expired. Please sign in again.");
        return;
      }
      setMessage("Application deleted from database.");
      await loadApplications();
    } catch {
      setMessage("Could not delete application.");
    }
  }

  // ── Persisted Resume Analysis ─────────────────────────────────────────────
  async function loadLatestResume(authToken?: string | null) {
    const curToken = authToken !== undefined ? authToken : token;
    const headers: Record<string, string> = {};
    if (curToken) headers["Authorization"] = `Bearer ${curToken}`;
    try {
      const r = await fetch(`${API}/api/analyze/resume/latest`, {
        credentials: "include",
        headers,
      });
      if (!r.ok) return;
      const d = await r.json();
      if (d.item) {
        setResumeResult(d.item);
        setResumeText(d.item.extracted_text_preview || "");
      }
    } catch {
      // Ignored if none exists
    }
  }

  async function analyzeFile(file?: File) {
    if (!file) return;
    setLoading(true); setMessage("");
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
      const fd = new FormData(); fd.append("file", file);
      const r = await fetch(`${API}/api/analyze/resume`, {
        method: "POST",
        headers,
        credentials: "include",
        body: fd,
      });
      const d = await r.json(); if (!r.ok) throw new Error(d.detail || "Resume analysis failed");
      setResumeResult(d); setResumeText(d.extracted_text_preview || "");
      setMessage("Resume analyzed and saved to your account. Review extracted skills below.");
      setActive("Resume Intelligence");
    } catch (e) { setMessage(errMsg(e)); }
    finally { setLoading(false); }
  }

  // ── Persisted Skill Roadmap ───────────────────────────────────────────────
  async function loadLatestRoadmap(authToken?: string | null) {
    const curToken = authToken !== undefined ? authToken : token;
    const headers: Record<string, string> = {};
    if (curToken) headers["Authorization"] = `Bearer ${curToken}`;
    try {
      const r = await fetch(`${API}/api/roadmap/latest`, {
        credentials: "include",
        headers,
      });
      if (!r.ok) return;
      const d = await r.json();
      if (d.item) {
        if (d.item.target_role) setTargetRole(d.item.target_role);
        if (d.item.current_skills) setSkillsInput(d.item.current_skills);
        if (d.item.result_json?.gap_analysis) setGapResult(d.item.result_json.gap_analysis);
      }
    } catch {
      // Ignored
    }
  }

  async function buildRoadmap() {
    setLoading(true); setMessage("");
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
      const skills = skillsInput.split(",").map(s => s.trim()).filter(Boolean);
      const r = await fetch(`${API}/api/roadmap`, {
        method: "POST",
        headers,
        credentials: "include",
        body: JSON.stringify({ target_role: targetRole, current_skills: skills, weeks: 8 }),
      });
      const d = await r.json(); if (!r.ok) throw new Error(d.detail || "Roadmap generation failed");
      setGapResult(d.gap_analysis); setMessage(`${d.tasks.length} roadmap tasks generated and saved.`); setActive("Skill Roadmap");
    } catch (e) { setMessage(errMsg(e)); }
    finally { setLoading(false); }
  }

  // ── Persisted Mock Interview ──────────────────────────────────────────────
  async function loadLatestInterview(authToken?: string | null) {
    const curToken = authToken !== undefined ? authToken : token;
    const headers: Record<string, string> = {};
    if (curToken) headers["Authorization"] = `Bearer ${curToken}`;
    try {
      const r = await fetch(`${API}/api/interviews/latest`, {
        credentials: "include",
        headers,
      });
      if (!r.ok) return;
      const d = await r.json();
      if (d.item) {
        if (d.item.question) setCurrentQuestion(d.item.question);
        if (d.item.answer) setAnswer(d.item.answer);
        if (d.item.role) setTargetRole(d.item.role);
        setEvaluation({
          practice_score: d.item.practice_score,
          rubric: d.item.rubric_json || {},
          suggestions: d.item.suggestions_json || [],
          disclaimer: "Transparent rubric-based practice feedback loaded from your saved session.",
        });
      }
    } catch {
      // Ignored
    }
  }

  async function getQuestions() {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/interviews/questions?role=${encodeURIComponent(targetRole)}&category=${interviewCategory}`);
      const d = await r.json(); if (!r.ok) throw new Error(d.detail || "Could not load questions");
      setInterviewQuestions(d.items || []); setCurrentQuestion(d.items?.[0]?.question || ""); setEvaluation(null); setActive("Mock Interview");
    } catch(e) { setMessage(errMsg(e)); }
    finally { setLoading(false); }
  }

  async function evaluate() {
    if (!currentQuestion || !answer.trim()) { setMessage("Choose a question and write your answer first."); return; }
    setLoading(true);
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    try {
      const r = await fetch(`${API}/api/interviews/evaluate`, {
        method: "POST",
        headers,
        credentials: "include",
        body: JSON.stringify({ question: currentQuestion, answer, role: targetRole }),
      });
      const d = await r.json(); if (!r.ok) throw new Error(d.detail || "Evaluation failed");
      setEvaluation(d);
      setMessage("Interview answer evaluated and saved to your history.");
    } catch(e) { setMessage(errMsg(e)); }
    finally { setLoading(false); }
  }

  // ── Matching ──────────────────────────────────────────────────────────────
  async function matchJob() {
    setLoading(true); setMessage("");
    try {
      const r = await fetch(`${API}/api/match`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({resume_text: resumeText, job_description: jobDescription, role: targetRole}) });
      const d = await r.json(); if (!r.ok) throw new Error(d.detail || "Matching failed");
      setMatchResult(d); setActive("Job Matching");
    } catch (e) { setMessage(errMsg(e)); }
    finally { setLoading(false); }
  }

  // ── Auth Handlers ─────────────────────────────────────────────────────────
  async function handleLogin(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!authEmail.trim() || !authPassword) {
      setAuthError("Email and password are required.");
      return;
    }
    setAuthLoading(true);
    setAuthError("");
    try {
      const res = await fetch(`${API}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Sign in failed. Check your credentials.");
      }
      setUser(data.user);
      setToken(data.access_token);
      setAuthModalOpen(false);
      setAuthPassword("");
      setMessage(`Welcome back, ${data.user.full_name || data.user.email}!`);
      await Promise.all([
        loadApplications(data.access_token),
        loadLatestResume(data.access_token),
        loadLatestRoadmap(data.access_token),
        loadLatestInterview(data.access_token),
      ]);
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "Sign in failed.");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleRegister(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!authEmail.trim() || !authPassword) {
      setAuthError("Email and password are required.");
      return;
    }
    if (authPassword.length < 8) {
      setAuthError("Password must be at least 8 characters.");
      return;
    }
    setAuthLoading(true);
    setAuthError("");
    try {
      const res = await fetch(`${API}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          email: authEmail,
          password: authPassword,
          full_name: authFullName.trim() || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        let msg = data.detail;
        if (Array.isArray(msg)) msg = msg.map((m: { msg: string }) => m.msg).join(", ");
        throw new Error(msg || "Registration failed.");
      }
      setUser(data.user);
      setToken(data.access_token);
      setAuthModalOpen(false);
      setAuthPassword("");
      setMessage(`Account created! Welcome, ${data.user.full_name || data.user.email}.`);
      await Promise.all([
        loadApplications(data.access_token),
        loadLatestResume(data.access_token),
        loadLatestRoadmap(data.access_token),
        loadLatestInterview(data.access_token),
      ]);
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleLogout() {
    try {
      await fetch(`${API}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Ignore network errors
    }
    setUser(null);
    setToken(null);
    setApplications([]);
    setResumeResult(null);
    setResumeText("");
    setGapResult(null);
    setEvaluation(null);
    setMessage("You have been signed out.");
  }

  const appliedCount = applications.filter(a => ["Applied","Assessment","Interview"].includes(a.status)).length;

  const content = useMemo(() => {
    switch (active) {
      case "Resume Intelligence": return <section className="space-y-5">
        <PageTitle eyebrow="NLP WORKSPACE" title="Resume Intelligence" subtitle="Extract skills from a resume. Extracted data is securely saved to your account and reloaded across sessions."/>
        <div className="panel p-6"><label className="mb-3 block text-sm font-semibold">Upload resume (PDF or TXT)</label><div className="rounded-xl border-2 border-dashed border-indigo-200 bg-indigo-50/40 p-8 text-center"><UploadCloud className="mx-auto mb-3 text-indigo-600" size={32}/><p className="font-semibold">Choose a resume file</p><p className="mt-1 text-sm text-slate-500">Text-based PDF or TXT, maximum 5 MB</p><input aria-label="Upload resume" type="file" accept=".pdf,.txt" className="mx-auto mt-4 block max-w-full text-sm" onChange={e=>analyzeFile(e.target.files?.[0])}/></div>
          {resumeResult && <div className="mt-5"><div className="flex items-center justify-between"><h3 className="font-semibold">Detected skills ({resumeResult.skill_count})</h3><span className="text-xs text-slate-400">File: {resumeResult.filename}</span></div><div className="mt-3 flex flex-wrap gap-2">{resumeResult.skills.map((s:string)=><span key={s} className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700">{s}</span>)}</div><ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-slate-600">{resumeResult.suggestions.map((s:string)=><li key={s}>{s}</li>)}</ul></div>}
        </div>
        <div className="panel p-6"><h3 className="font-semibold">Extracted text (editable)</h3><p className="mt-1 text-sm text-slate-500">Review the text and correct extraction issues before matching.</p><textarea className="field mt-4 min-h-48" value={resumeText} onChange={e=>setResumeText(e.target.value)} placeholder="Upload a resume or paste resume text here..."/></div>
      </section>;
      case "Job Matching": return <section className="space-y-5">
        <PageTitle eyebrow="SEMANTIC ALIGNMENT" title="Job Matching" subtitle="Compare a resume with a target job description. Scores are heuristics, not hiring probabilities."/>
        <div className="panel grid gap-5 p-6 md:grid-cols-2"><div><label className="mb-2 block text-sm font-semibold">Resume text</label><textarea className="field min-h-52" value={resumeText} onChange={e=>setResumeText(e.target.value)} placeholder="Paste resume text or analyze a file first."/></div><div><label className="mb-2 block text-sm font-semibold">Job description</label><textarea className="field min-h-52" value={jobDescription} onChange={e=>setJobDescription(e.target.value)} placeholder="Paste the job description here."/></div><div><label className="mb-2 block text-sm font-semibold">Target role (optional)</label><input className="field" value={targetRole} onChange={e=>setTargetRole(e.target.value)}/></div><div className="flex items-end"><button className="btn w-full" disabled={loading} onClick={matchJob}>{loading?"Analyzing...":"Analyze match"}</button></div></div>
        {matchResult && <div className="panel p-6"><div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm text-slate-500">Text similarity</p><p className="mt-1 text-4xl font-bold">{matchResult.similarity_score}%</p></div><p className="max-w-xl text-sm text-slate-500">{matchResult.interpretation}</p></div><div className="mt-6 grid gap-5 md:grid-cols-2"><SkillList title="Matched skills" items={matchResult.matched_skills}/><SkillList title="Skills to review" items={matchResult.missing_skills}/></div></div>}
        <div className="panel p-6"><h3 className="font-semibold">Demo job descriptions</h3><p className="mb-4 mt-1 text-sm text-slate-500">Sample listings only; not live vacancies.</p><div className="space-y-3">{jobs.map(j=><button key={j.id} className="w-full rounded-xl border border-slate-100 p-4 text-left hover:border-indigo-200 hover:bg-indigo-50/30" onClick={()=>{setJobDescription(j.description);setTargetRole(j.title.replace(" (Sample)",""));}}><div className="flex items-center justify-between gap-3"><div><p className="font-semibold">{j.title}</p><p className="mt-1 text-sm text-slate-500">{j.company} · {j.location}</p></div><ArrowUpRight size={18} className="text-indigo-600"/></div></button>)}</div></div>
      </section>;
      case "Skill Roadmap": return <section className="space-y-5"><PageTitle eyebrow="PERSONALIZED DEVELOPMENT" title="Skill-gap roadmap" subtitle="See missing skills and a priority-ordered learning plan for a supported demo role. Saved automatically to your profile."/>
        <div className="panel grid gap-4 p-6 md:grid-cols-3"><div className="md:col-span-1"><label className="mb-2 block text-sm font-semibold">Target role</label><select className="field" value={targetRole} onChange={e=>setTargetRole(e.target.value)}><option>Data Scientist</option><option>Machine Learning Engineer</option><option>Frontend Developer</option><option>Backend Developer</option><option>Cybersecurity Analyst</option></select></div><div className="md:col-span-2"><label className="mb-2 block text-sm font-semibold">Current skills (comma-separated)</label><input className="field" value={skillsInput} onChange={e=>setSkillsInput(e.target.value)}/></div><div className="md:col-span-3"><button className="btn" disabled={loading} onClick={buildRoadmap}>{loading?"Building...":"Generate roadmap"}</button></div></div>
        {gapResult && <div className="panel p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm text-slate-500">Skill coverage (heuristic)</p><p className="text-4xl font-bold">{gapResult.coverage_score}%</p></div><span className="rounded-full bg-emerald-50 px-3 py-1 text-sm text-emerald-700">{gapResult.matched_skills.length} skills matched</span></div><div className="mt-5 h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-indigo-600" style={{width:`${gapResult.coverage_score}%`}}/></div><div className="mt-5 grid gap-5 md:grid-cols-2"><SkillList title="Skills already listed" items={gapResult.matched_skills.map(x=>x.skill)}/><SkillList title="Priority gaps" items={gapResult.missing_skills.map(x=>x.skill)}/></div><p className="mt-4 text-sm text-slate-500">{gapResult.message}</p></div>}
      </section>;
      case "Mock Interview": return <section className="space-y-5"><PageTitle eyebrow="PRACTICE LAB" title="Mock Interview" subtitle="Practice questions and get transparent feedback. Your answers and evaluations persist to your account."/>
        <div className="panel grid gap-4 p-6 md:grid-cols-3"><div><label className="mb-2 block text-sm font-semibold">Target role</label><input className="field" value={targetRole} onChange={e=>setTargetRole(e.target.value)}/></div><div><label className="mb-2 block text-sm font-semibold">Category</label><select className="field" value={interviewCategory} onChange={e=>setInterviewCategory(e.target.value)}><option value="technical">Technical</option><option value="hr">HR</option><option value="behavioral">Behavioral</option></select></div><div className="flex items-end"><button className="btn w-full" disabled={loading} onClick={getQuestions}>Load questions</button></div></div>
        {interviewQuestions.length>0 && <div className="panel p-6"><label className="mb-2 block text-sm font-semibold">Select a question</label><select className="field" value={currentQuestion} onChange={e=>{setCurrentQuestion(e.target.value);setEvaluation(null)}}>{interviewQuestions.map((q)=><option key={q.question} value={q.question}>{q.question}</option>)}</select><label className="mb-2 mt-5 block text-sm font-semibold">Your answer</label><textarea className="field min-h-40" value={answer} onChange={e=>setAnswer(e.target.value)} placeholder="Structure your answer and include a concrete example..."/><button className="btn mt-4" disabled={loading} onClick={evaluate}>Review my answer</button></div>}
        {evaluation && <div className="panel p-6"><p className="text-sm text-slate-500">Practice score (heuristic)</p><p className="mt-1 text-4xl font-bold">{evaluation.practice_score}/100</p><div className="mt-4 grid gap-3 sm:grid-cols-3">{Object.entries(evaluation.rubric).map(([k,v])=><div className="rounded-xl bg-slate-50 p-3" key={k}><p className="text-xs capitalize text-slate-500">{k.replaceAll("_"," ")}</p><p className="mt-1 text-xl font-semibold">{v}/40</p></div>)}</div><ul className="mt-4 list-disc space-y-2 pl-5 text-sm">{evaluation.suggestions.map((s:string)=><li key={s}>{s}</li>)}</ul><p className="mt-4 text-xs text-slate-500">{evaluation.disclaimer}</p></div>}
      </section>;
      case "Applications": return <section className="space-y-5">
        <PageTitle eyebrow="JOB SEARCH WORKSPACE" title="Application tracker" subtitle="Track applications you add. These records are securely stored and isolated in your database account."/>
        {!user ? (
          <div className="panel p-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
              <Lock size={28}/>
            </div>
            <h3 className="text-lg font-bold text-slate-900">Sign in to track applications</h3>
            <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
              Applications are private and tied to your verified account. Sign in or register in seconds to store and manage your opportunities across sessions.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <button className="btn" onClick={() => { setAuthMode("login"); setAuthError(""); setAuthModalOpen(true); }}>
                Sign In
              </button>
              <button className="btn-secondary" onClick={() => { setAuthMode("register"); setAuthError(""); setAuthModalOpen(true); }}>
                Create Account
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="panel grid gap-3 p-5 md:grid-cols-4">
              <input className="field" placeholder="Company" value={newCompany} onChange={e=>setNewCompany(e.target.value)}/>
              <input className="field" placeholder="Role" value={newRole} onChange={e=>setNewRole(e.target.value)}/>
              <select className="field" value={newStatus} onChange={e=>setNewStatus(e.target.value)}>
                {["Saved","Applied","Assessment","Interview","Offer","Rejected","Withdrawn"].map(s=><option key={s}>{s}</option>)}
              </select>
              <button className="btn" disabled={loading} onClick={addApplication}>Add application</button>
            </div>
            <div className="panel overflow-hidden">
              <div className="flex items-center justify-between border-b border-slate-100 p-5 font-semibold">
                <div>Your applications <span className="ml-2 rounded-full bg-slate-100 px-2 py-1 text-xs">{applications.length}</span></div>
                <span className="text-xs font-normal text-slate-400">Scoped to {user.email}</span>
              </div>
              {applicationsLoading ? (
                <p className="p-8 text-center text-sm text-slate-500">Loading your saved applications...</p>
              ) : applications.length === 0 ? (
                <p className="p-8 text-center text-sm text-slate-500">No applications yet. Add your first record above.</p>
              ) : (
                <div className="divide-y divide-slate-100">
                  {applications.map(a=>(
                    <div key={a.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                      <div>
                        <p className="font-semibold">{a.role}</p>
                        <p className="mt-1 text-sm text-slate-500">{a.company}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <select className="field max-w-40" value={a.status} onChange={e=>changeStatus(a,e.target.value)}>
                          {["Saved","Applied","Assessment","Interview","Offer","Rejected","Withdrawn"].map(s=><option key={s}>{s}</option>)}
                        </select>
                        <button
                          className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 transition"
                          onClick={()=>deleteApp(a.id)}
                          aria-label="Delete application"
                          title="Delete application"
                        >
                          <X size={16}/>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </section>;
      default: return <section className="space-y-5">
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#171C4B] via-[#3730A3] to-[#6366F1] p-7 text-white shadow-soft md:p-9"><div className="relative z-10 max-w-2xl"><div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold"><Sparkles size={14}/> YOUR PERSONAL CAREER INTELLIGENCE</div><h2 className="text-3xl font-bold leading-tight md:text-4xl">Build skills with a plan.<br/>Move forward with clarity.</h2><p className="mt-3 max-w-xl text-sm leading-6 text-indigo-100 md:text-base">Connect resume insights, job matching and focused practice into one career development workflow.</p><button className="mt-6 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-indigo-800 hover:bg-indigo-50" onClick={()=>setActive("Resume Intelligence")}>Analyze your resume <ArrowUpRight size={16}/></button></div><div className="absolute -right-8 -top-16 h-64 w-64 rounded-full border border-white/15"/><div className="absolute -right-2 -top-6 h-52 w-52 rounded-full border border-white/15"/></div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric icon={<Target size={18}/>} label="Career readiness" value="—" detail="Build profile to calculate" color="indigo"/><Metric icon={<BriefcaseBusiness size={18}/>} label="Active applications" value={String(appliedCount)} detail="Applied, assessment, interview" color="blue"/><Metric icon={<BrainCircuit size={18}/>} label="ML services" value="4" detail="Resume, match, gap, rubric" color="violet"/><Metric icon={<Activity size={18}/>} label="API status" value={apiStatus==="online"?"Online":apiStatus==="offline"?"Offline":"Checking"} detail={apiStatus==="online"?"Backend responding":apiStatus==="offline"?"Start FastAPI backend":"Checking health endpoint"} color={apiStatus==="online"?"green":"amber"}/></div>
        <div className="grid gap-5 xl:grid-cols-[1.55fr_1fr]"><div className="panel p-5 md:p-6"><div className="flex items-start justify-between"><div><h3 className="font-semibold">Progress snapshot</h3><p className="mt-1 text-sm text-slate-500">Illustrative design preview — not personal measured data</p></div><button className="btn-secondary text-sm" onClick={()=>setActive("Skill Roadmap")}>Build roadmap</button></div><div className="mt-5 h-64"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend}><defs><linearGradient id="readinessFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#6366F1" stopOpacity={0.22}/><stop offset="95%" stopColor="#6366F1" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#EEF0F6"/><XAxis dataKey="week" axisLine={false} tickLine={false} tick={{fontSize:12,fill:"#94A3B8"}}/><YAxis axisLine={false} tickLine={false} tick={{fontSize:12,fill:"#94A3B8"}}/><Tooltip/><Area type="monotone" dataKey="readiness" stroke="#4F46E5" fill="url(#readinessFill)" strokeWidth={2.5}/><Area type="monotone" dataKey="practice" stroke="#0EA5E9" fill="transparent" strokeWidth={2}/></AreaChart></ResponsiveContainer></div><div className="flex flex-wrap gap-4 text-xs text-slate-500"><span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-indigo-600"/>Readiness demo trend</span><span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-sky-500"/>Practice demo trend</span></div></div>
        <div className="panel p-5 md:p-6"><h3 className="font-semibold">Recommended next actions</h3><p className="mt-1 text-sm text-slate-500">Start with an action to personalize the workspace.</p><div className="mt-5 space-y-3"><Action icon={<FileText size={18}/>} title="Analyze your resume" desc="Extract skills and review suggestions" onClick={()=>setActive("Resume Intelligence")}/><Action icon={<Target size={18}/>} title="Compare a job description" desc="Find matching and missing skills" onClick={()=>setActive("Job Matching")}/><Action icon={<ListChecks size={18}/>} title="Create a skill roadmap" desc="Prioritize gaps for your target role" onClick={()=>setActive("Skill Roadmap")}/><Action icon={<Mic2 size={18}/>} title="Practice an interview" desc="Get structured answer feedback" onClick={()=>setActive("Mock Interview")}/></div></div></div>
        <div className="panel p-5"><div className="flex items-center justify-between gap-3"><div><h3 className="font-semibold">Demo job catalogue</h3><p className="mt-1 text-sm text-slate-500">Synthetic listings to test matching flows.</p></div><button className="btn-secondary text-sm" onClick={()=>setActive("Job Matching")}>Explore jobs</button></div><div className="mt-4 grid gap-3 md:grid-cols-2">{jobs.slice(0,4).map(j=><div key={j.id} className="rounded-xl border border-slate-100 p-4"><div className="flex items-start justify-between gap-2"><div><p className="font-semibold">{j.title}</p><p className="mt-1 text-sm text-slate-500">{j.company}</p></div><span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-bold uppercase text-amber-700">Demo</span></div><p className="mt-3 line-clamp-2 text-sm text-slate-600">{j.description}</p></div>)}</div></div>
      </section>;
    }
  }, [active, resumeText, resumeResult, jobDescription, targetRole, matchResult, gapResult, skillsInput, loading, jobs, apiStatus, applications, applicationsLoading, appliedCount, newCompany, newRole, newStatus, interviewCategory, interviewQuestions, currentQuestion, answer, evaluation, user]);

  return <div className="min-h-screen">
    {mobileOpen && <button aria-label="Close navigation overlay" className="fixed inset-0 z-40 bg-slate-950/30 lg:hidden" onClick={()=>setMobileOpen(false)}/>}
    <aside className={`fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col border-r border-slate-200 bg-white transition-transform lg:translate-x-0 ${mobileOpen?"translate-x-0":"-translate-x-full"}`}>
      <div className="flex h-20 items-center gap-3 border-b border-slate-100 px-6"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white"><BrainCircuit size={22}/></div><div><p className="font-bold tracking-tight">CareerPilot <span className="text-indigo-600">AI</span></p><p className="text-[11px] text-slate-500">CAREER INTELLIGENCE</p></div><button className="ml-auto lg:hidden" onClick={()=>setMobileOpen(false)} aria-label="Close menu"><X size={18}/></button></div>
      <div className="px-4 pt-6"><p className="px-3 text-[10px] font-bold uppercase tracking-[.16em] text-slate-400">Workspace</p><nav className="mt-3 space-y-1">{nav.map(item=><button key={item.label} onClick={()=>{setActive(item.label);setMobileOpen(false)}} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition ${active===item.label?"bg-indigo-50 text-indigo-700":"text-slate-600 hover:bg-slate-50 hover:text-slate-900"}`}><item.icon size={18}/>{item.label}{active===item.label&&<span className="ml-auto h-1.5 w-1.5 rounded-full bg-indigo-600"/>}</button>)}</nav></div>
      <div className="mt-auto p-4">
        <div className="rounded-xl bg-slate-50 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck size={17} className="text-emerald-600"/>
            {user ? "Persistent & Isolated" : "Private & Secure"}
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            {user
              ? `Signed in as ${user.email}. Applications, resumes, roadmaps, and interview sessions persist across browser refreshes.`
              : "Sign in or register to securely save applications, resumes, and personalized roadmaps."}
          </p>
        </div>
        <button onClick={()=>setMessage("Profile settings and preferences are saved to your active account.")} className="mt-3 flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm text-slate-500 hover:bg-slate-50"><Settings2 size={17}/> Settings <ChevronDown size={14} className="ml-auto"/></button>
      </div>
    </aside>

    <main className="min-h-screen lg:pl-[260px]">
      <header className="sticky top-0 z-30 flex h-[72px] items-center justify-between border-b border-slate-200/80 bg-[#F7F8FC]/90 px-4 backdrop-blur md:px-8">
        <div className="flex items-center gap-3">
          <button className="rounded-lg border border-slate-200 bg-white p-2 lg:hidden" onClick={()=>setMobileOpen(true)} aria-label="Open navigation"><Menu size={18}/></button>
          <div><p className="text-sm font-semibold">{active}</p><p className="hidden text-xs text-slate-500 sm:block">Your career development workspace</p></div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500 md:flex">
            <Search size={14}/>Career workspace
          </div>
          <button className="relative rounded-xl border border-slate-200 bg-white p-2.5" aria-label="Help" onClick={()=>setMessage("Tip: start with Resume Intelligence, then paste a job description to see ML matching.")}>
            <CircleHelp size={17}/>
          </button>

          {/* User profile / auth actions */}
          {user ? (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white">
                  {(user.full_name || user.email).slice(0, 2).toUpperCase()}
                </div>
                <span className="hidden sm:inline max-w-[140px] truncate">{user.full_name || user.email}</span>
              </div>
              <button
                className="rounded-xl border border-slate-200 bg-white p-2 text-slate-600 hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition"
                onClick={handleLogout}
                title="Sign out"
                aria-label="Sign out"
              >
                <LogOut size={16}/>
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                onClick={() => { setAuthMode("login"); setAuthError(""); setAuthModalOpen(true); }}
              >
                Sign In
              </button>
              <button
                className="rounded-xl bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-indigo-700 shadow-sm transition"
                onClick={() => { setAuthMode("register"); setAuthError(""); setAuthModalOpen(true); }}
              >
                Sign Up
              </button>
            </div>
          )}
        </div>
      </header>

      <div className="mx-auto max-w-[1500px] p-4 md:p-8">
        {message && (
          <div role="status" className="mb-5 flex items-start justify-between gap-3 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
            <span>{message}</span>
            <button onClick={()=>setMessage("")} aria-label="Dismiss message"><X size={16}/></button>
          </div>
        )}
        {content}
        <footer className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 py-5 text-xs text-slate-400">
          <span>CareerPilot AI · Advanced career intelligence platform</span>
          <span>Database persistence enabled · Sessions and records securely stored across reloads.</span>
        </footer>
      </div>
    </main>

    {/* ── Auth Modal ──────────────────────────────────────────────────────── */}
    {authModalOpen && (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/40 backdrop-blur-sm">
        <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl border border-slate-100">
          <button
            onClick={() => setAuthModalOpen(false)}
            className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition"
            aria-label="Close"
          >
            <X size={18}/>
          </button>

          <div className="flex items-center gap-3 mb-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white">
              <BrainCircuit size={20}/>
            </div>
            <div>
              <h3 className="font-bold text-slate-900">CareerPilot <span className="text-indigo-600">AI</span></h3>
              <p className="text-xs text-slate-500">
                {authMode === "login" ? "Sign in to access your workspace" : "Create your career intelligence account"}
              </p>
            </div>
          </div>

          <div className="flex rounded-xl bg-slate-100 p-1 mb-5">
            <button
              type="button"
              className={`flex-1 rounded-lg py-1.5 text-xs font-semibold transition ${authMode === "login" ? "bg-white text-indigo-700 shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
              onClick={() => { setAuthMode("login"); setAuthError(""); }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`flex-1 rounded-lg py-1.5 text-xs font-semibold transition ${authMode === "register" ? "bg-white text-indigo-700 shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
              onClick={() => { setAuthMode("register"); setAuthError(""); }}
            >
              Create Account
            </button>
          </div>

          {authError && (
            <div role="alert" className="mb-4 rounded-xl border border-red-100 bg-red-50 p-3 text-xs font-medium text-red-700">
              {authError}
            </div>
          )}

          <form onSubmit={authMode === "login" ? handleLogin : handleRegister} className="space-y-3.5">
            {authMode === "register" && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name (optional)</label>
                <input
                  type="text"
                  className="field text-sm"
                  placeholder="e.g. Alex Johnson"
                  value={authFullName}
                  onChange={e => setAuthFullName(e.target.value)}
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Email address</label>
              <input
                type="email"
                required
                className="field text-sm"
                placeholder="you@example.com"
                value={authEmail}
                onChange={e => setAuthEmail(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
              <input
                type="password"
                required
                className="field text-sm"
                placeholder="••••••••"
                value={authPassword}
                onChange={e => setAuthPassword(e.target.value)}
              />
              {authMode === "register" && (
                <p className="mt-1 text-[11px] text-slate-400">Must be at least 8 characters.</p>
              )}
            </div>

            <button
              type="submit"
              disabled={authLoading}
              className="btn w-full mt-2"
            >
              {authLoading
                ? (authMode === "login" ? "Signing in..." : "Creating account...")
                : (authMode === "login" ? "Sign In" : "Create Account")}
            </button>
          </form>

          <p className="mt-4 text-center text-xs text-slate-400">
            {authMode === "login" ? (
              <>
                Don&apos;t have an account?{" "}
                <button
                  type="button"
                  onClick={() => { setAuthMode("register"); setAuthError(""); }}
                  className="font-semibold text-indigo-600 hover:underline"
                >
                  Create one now
                </button>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => { setAuthMode("login"); setAuthError(""); }}
                  className="font-semibold text-indigo-600 hover:underline"
                >
                  Sign in instead
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    )}
  </div>;
}

function PageTitle({eyebrow,title,subtitle}:{eyebrow:string;title:string;subtitle:string}) {
  return <div><p className="text-[10px] font-bold tracking-[.18em] text-indigo-600">{eyebrow}</p><h2 className="mt-2 text-2xl font-bold tracking-tight md:text-3xl">{title}</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">{subtitle}</p></div>;
}
function Metric({icon,label,value,detail,color}:{icon:React.ReactNode;label:string;value:string;detail:string;color:string}) {
  const bg:Record<string,string>={indigo:"bg-indigo-50 text-indigo-700",blue:"bg-sky-50 text-sky-700",violet:"bg-violet-50 text-violet-700",green:"bg-emerald-50 text-emerald-700",amber:"bg-amber-50 text-amber-700"};
  return <div className="panel p-4"><div className="flex items-center justify-between"><span className="text-sm text-slate-500">{label}</span><span className={`rounded-lg p-2 ${bg[color]||bg.indigo}`}>{icon}</span></div><p className="mt-4 text-2xl font-bold">{value}</p><p className="mt-1 text-xs text-slate-500">{detail}</p></div>;
}
function Action({icon,title,desc,onClick}:{icon:React.ReactNode;title:string;desc:string;onClick:()=>void}) {
  return <button onClick={onClick} className="flex w-full items-center gap-3 rounded-xl border border-slate-100 p-3 text-left hover:border-indigo-200 hover:bg-indigo-50/30"><span className="rounded-lg bg-indigo-50 p-2 text-indigo-700">{icon}</span><span className="min-w-0 flex-1"><span className="block text-sm font-semibold">{title}</span><span className="mt-1 block text-xs text-slate-500">{desc}</span></span><ArrowUpRight size={16} className="text-slate-400"/></button>;
}
function SkillList({title,items}:{title:string;items:string[]}) {
  return <div><h4 className="mb-3 text-sm font-semibold">{title}</h4>{items.length===0?<p className="text-sm text-slate-400">No items to show.</p>:<div className="flex flex-wrap gap-2">{items.map(s=><span key={s} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700">{s}</span>)}</div>}</div>;
}
