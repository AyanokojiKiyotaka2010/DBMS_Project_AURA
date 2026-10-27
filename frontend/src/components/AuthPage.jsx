import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useStructure } from "../lib/campus";
import { toast } from "sonner";
import { Lock, EnvelopeSimple, User, GraduationCap, IdentificationCard, Sparkle } from "@phosphor-icons/react";

const ROLES = ["Student", "Senior", "Alumni"]; // Professor / CR / DCR are granted by an administrator

const HERO_IMG =
  "https://images.unsplash.com/photo-1758270704763-22072a90d3b6?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1MDV8MHwxfHNlYXJjaHwxfHxkaXZlcnNlJTIwY29sbGVnZSUyMHN0dWRlbnRzJTIwc3R1ZHlpbmclMjBjYW1wdXMlMjB3YXJtJTIwbGlnaHR8ZW58MHx8fHwxNzg2MDUyMzU2fDA&ixlib=rb-4.1.0&q=85";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const structure = useStructure();
  const [departmentId, setDepartmentId] = useState("");
  const [yearId, setYearId] = useState("");
  const [divisionId, setDivisionId] = useState("");
  const [rollNo, setRollNo] = useState("");
  const [role, setRole] = useState("Student");
  const [loading, setLoading] = useState(false);

  const { login, register } = useAuth();

  const fillDemo = (demoEmail, demoPass) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setIsLogin(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isLogin) {
        await login(email, password);
        toast.success("Welcome back to AURA");
      } else {
        const num = (v) => (v === "" ? null : Number(v));
        await register(name, email, password, num(departmentId), role, num(yearId), num(divisionId), rollNo.trim() || null);
        toast.success(`Account created — welcome, ${name}`);
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg).join(", ")
            : "Authentication failed. Check your credentials.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="auth-page" className="min-h-screen flex bg-paper">
      {/* Left panel — editorial hero */}
      <div className="hidden lg:flex lg:w-[52%] relative overflow-hidden">
        <img
          src={HERO_IMG}
          alt="Students studying in warm campus light"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-brand-deep/85 via-brand-deep/40 to-transparent" />
        <div className="relative z-10 flex flex-col justify-between p-12 text-paper w-full">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-2xl bg-paper text-brand grid place-items-center font-serif text-2xl font-bold">
              A
            </div>
            <div>
              <div className="font-serif text-2xl font-semibold leading-none">AURA</div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-paper/70 mt-1">
                Academic & Club Commons
              </div>
            </div>
          </div>

          <div className="max-w-md">
            <div className="text-[11px] uppercase tracking-[0.22em] text-brand-gold font-semibold mb-4">
              Campus, Rewired
            </div>
            <h1 className="font-serif text-5xl xl:text-6xl font-semibold leading-[1.02] tracking-tight text-paper">
              Announce. Ask. <span className="italic text-brand-gold">Belong.</span>
            </h1>
            <p className="text-sm text-paper/80 mt-5 leading-relaxed">
              A daylight home for department feeds, anonymous doubts, club
              archives and everything you'd otherwise scatter across five WhatsApp groups.
            </p>

            <div className="mt-8 grid grid-cols-3 gap-3">
              <div className="tactile-card !p-4 !bg-paper/10 border-paper/20 text-paper">
                <div className="font-serif text-3xl font-semibold">6</div>
                <div className="text-[11px] uppercase tracking-widest text-paper/70">Departments</div>
              </div>
              <div className="tactile-card !p-4 !bg-paper/10 border-paper/20 text-paper">
                <div className="font-serif text-3xl font-semibold">48h</div>
                <div className="text-[11px] uppercase tracking-widest text-paper/70">Escalation</div>
              </div>
              <div className="tactile-card !p-4 !bg-paper/10 border-paper/20 text-paper">
                <div className="font-serif text-3xl font-semibold">5y</div>
                <div className="text-[11px] uppercase tracking-widest text-paper/70">Archive</div>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-paper/60 font-mono">
            Secured · JWT + Bcrypt · Encrypted anonymous IDs
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md">
          <div className="flex items-center justify-between mb-8">
            <div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-brand font-semibold">
                {isLogin ? "Welcome back" : "Join the campus"}
              </div>
              <h2 className="font-serif text-4xl font-semibold text-ink mt-1 tracking-tight">
                {isLogin ? "Sign in to AURA" : "Create your AURA"}
              </h2>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="text-[11px] font-semibold text-ink-2 uppercase tracking-widest block mb-1.5">
                  Full name
                </label>
                <div className="flex items-center gap-2 bg-paper-card border border-edge-light rounded-xl px-4 py-3 focus-within:border-brand transition-colors">
                  <User size={16} className="text-ink-3" />
                  <input
                    data-testid="auth-name-input"
                    type="text"
                    required
                    value={name}
                    placeholder="e.g. Kavya Menon"
                    onChange={(e) => setName(e.target.value)}
                    className="bg-transparent outline-none w-full text-sm text-ink"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="text-[11px] font-semibold text-ink-2 uppercase tracking-widest block mb-1.5">
                Campus email
              </label>
              <div className="flex items-center gap-2 bg-paper-card border border-edge-light rounded-xl px-4 py-3 focus-within:border-brand transition-colors">
                <EnvelopeSimple size={16} className="text-ink-3" />
                <input
                  data-testid="auth-email-input"
                  type="email"
                  required
                  value={email}
                  placeholder="you@campus.edu"
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-transparent outline-none w-full text-sm text-ink"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-ink-2 uppercase tracking-widest block mb-1.5">
                Password
              </label>
              <div className="flex items-center gap-2 bg-paper-card border border-edge-light rounded-xl px-4 py-3 focus-within:border-brand transition-colors">
                <Lock size={16} className="text-ink-3" />
                <input
                  data-testid="auth-password-input"
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  placeholder="••••••••"
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-transparent outline-none w-full text-sm text-ink"
                />
              </div>
            </div>

            {!isLogin && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-semibold text-ink-2 uppercase tracking-widest block mb-1.5">
                    Department
                  </label>
                  <div className="flex items-center gap-2 bg-paper-card border border-edge-light rounded-xl px-3 py-3">
                    <GraduationCap size={16} className="text-ink-3" />
                    <select
                      data-testid="auth-department-select"
                      value={departmentId}
                      onChange={(e) => { setDepartmentId(e.target.value); setDivisionId(""); }}
                      className="bg-transparent outline-none w-full text-sm text-ink"
                    >
                      <option value="">Select…</option>
                      {structure.departments.map((d) => (
                        <option key={d.id} value={d.id}>{d.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-ink-2 uppercase tracking-widest block mb-1.5">
                    Year
                  </label>
                  <select
                    data-testid="auth-year-select"
                    value={yearId}
                    onChange={(e) => { setYearId(e.target.value); setDivisionId(""); }}
                    className="w-full bg-paper-card border border-edge-light rounded-xl px-3 py-3 text-sm text-ink outline-none"
                  >
                    <option value="">Select…</option>
                    {structure.years.map((y) => (
                      <option key={y.id} value={y.id}>{y.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-ink-2 uppercase tracking-widest block mb-1.5">Division</label>
                  <select
                    data-testid="auth-division-select"
                    value={divisionId}
                    onChange={(e) => setDivisionId(e.target.value)}
                    className="w-full bg-paper-card border border-edge-light rounded-xl px-3 py-3 text-sm text-ink outline-none"
                  >
                    <option value="">None / not sure</option>
                    {structure.divisions
                      .filter((d) => String(d.department_id) === departmentId && String(d.year_id) === yearId)
                      .map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-ink-2 uppercase tracking-widest block mb-1.5">Roll no.</label>
                  <input
                    data-testid="auth-rollno-input"
                    value={rollNo}
                    onChange={(e) => setRollNo(e.target.value)}
                    placeholder="optional"
                    className="w-full bg-paper-card border border-edge-light rounded-xl px-3 py-3 text-sm text-ink outline-none"
                  />
                </div>
                {structure.loaded && structure.departments.length === 0 && (
                  <div className="col-span-2 text-xs text-brand-deep bg-brand/10 rounded-lg px-3 py-2" data-testid="auth-no-structure">
                    No departments have been set up yet. Ask the administrator to add them (Academic Setup).
                  </div>
                )}
                <div className="col-span-2">
                  <label className="text-[11px] font-semibold text-ink-2 uppercase tracking-widest block mb-1.5">
                    Role
                  </label>
                  <div className="flex items-center gap-2 bg-paper-card border border-edge-light rounded-xl px-3 py-3">
                    <IdentificationCard size={16} className="text-ink-3" />
                    <select
                      data-testid="auth-role-select"
                      value={role}
                      onChange={(e) => setRole(e.target.value)}
                      className="bg-transparent outline-none w-full text-sm text-ink"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            <button
              data-testid="auth-submit-btn"
              type="submit"
              disabled={loading}
              className="w-full py-3.5 rounded-xl bg-brand hover:bg-brand-hover text-paper font-semibold text-sm shadow-clay transition-all active:scale-[0.98] flex items-center justify-center gap-2 disabled:opacity-60"
            >
              <Sparkle size={16} weight="fill" />
              {loading ? "Processing…" : isLogin ? "Sign in" : "Create account"}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              data-testid="auth-toggle-mode-btn"
              onClick={() => setIsLogin(!isLogin)}
              className="text-xs text-brand-deep hover:text-brand font-semibold underline underline-offset-4"
            >
              {isLogin ? "New here? Create an account →" : "Already a member? Sign in"}
            </button>
          </div>

          {isLogin && (
            <div className="mt-8 pt-6 border-t border-edge-light">
              <div className="text-[11px] uppercase tracking-widest text-ink-3 font-semibold mb-3">
                Try a demo persona
              </div>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { l: "Admin", e: "admin@campus.edu", p: "admin123" },
                  { l: "CR", e: "cr@campus.edu", p: "cr12345" },
                  { l: "DCR", e: "dcr@campus.edu", p: "dcr12345" },
                  { l: "Professor", e: "prof@campus.edu", p: "prof12345" },
                  { l: "Senior", e: "senior@campus.edu", p: "senior12345" },
                  { l: "Alumni", e: "alumni@campus.edu", p: "alumni12345" },
                ].map((d) => (
                  <button
                    key={d.l}
                    type="button"
                    data-testid={`demo-fill-${d.l.toLowerCase()}`}
                    onClick={() => fillDemo(d.e, d.p)}
                    className="px-3 py-2 text-xs font-medium rounded-lg border border-edge-light bg-paper-card hover:bg-paper-sidebar text-ink-2 hover:text-ink transition-colors text-left"
                  >
                    <div className="font-semibold text-ink">{d.l}</div>
                    <div className="text-[10px] font-mono text-ink-3 truncate">{d.e}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
