import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";

const field = "w-full bg-paper-card border border-edge-light rounded-xl px-4 py-3 text-sm text-ink outline-none focus:border-brand transition-colors";
const label = "text-[11px] font-semibold text-ink-2 uppercase tracking-widest block mb-1.5";
const msg = (e, fallback) => {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg).join(", ") : fallback;
};

/** stage: "verify" (enter the sign-up code) | "forgot" (ask for a reset code) | "reset" (code + new password) */
export default function VerifyPanel({ stage, setStage, email, setEmail, emailSent = true }) {
  const { verifyEmail, resendCode, forgotPassword, resetPassword } = useAuth();
  const [code, setCode] = useState("");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const run = async (fn) => {
    setBusy(true);
    try { await fn(); } catch (e) { toast.error(msg(e, "Something went wrong")); } finally { setBusy(false); }
  };

  const verify = (e) => { e.preventDefault(); run(async () => { await verifyEmail(email, code.trim()); toast.success("Email verified — welcome to AURA"); }); };
  const resend = () => run(async () => { await resendCode(email); setCooldown(60); toast.success("If that address is registered, a new code is on its way"); });
  const ask = (e) => { e.preventDefault(); run(async () => { await forgotPassword(email); setCooldown(60); setStage("reset"); toast.success("If that address has an account, a code is on its way"); }); };
  const reset = (e) => {
    e.preventDefault();
    run(async () => { await resetPassword(email, code.trim(), pw); toast.success("Password updated — sign in with it"); setCode(""); setPw(""); setStage(null); });
  };

  return (
    <div data-testid="verify-panel" className="space-y-5">
      <div>
        <div className="text-[11px] uppercase tracking-[0.22em] text-brand font-semibold">
          {stage === "verify" ? "One more step" : "Account recovery"}
        </div>
        <h2 className="font-serif text-4xl font-semibold text-ink mt-1 tracking-tight">
          {stage === "verify" ? "Verify your email" : stage === "forgot" ? "Forgot password?" : "Set a new password"}
        </h2>
        <p className="text-sm text-ink-2 mt-2">
          {stage === "verify" && (emailSent
            ? <>We sent a 6-digit code to <b>{email}</b>. It expires in 15 minutes.</>
            : <>We could not send the email just now. Press “Send a new code” to try again.</>)}
          {stage === "forgot" && "Enter your account email and we will send you a 6-digit code."}
          {stage === "reset" && <>Enter the code we sent to <b>{email}</b> and choose a new password.</>}
        </p>
      </div>

      {stage === "forgot" && (
        <form onSubmit={ask} className="space-y-4">
          <div>
            <label className={label}>Account email</label>
            <input data-testid="forgot-email-input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={field} />
          </div>
          <button data-testid="forgot-submit" disabled={busy} className="w-full py-3.5 rounded-xl bg-brand hover:bg-brand-hover text-paper font-semibold text-sm shadow-clay disabled:opacity-60">
            {busy ? "Sending…" : "Send code"}
          </button>
        </form>
      )}

      {(stage === "verify" || stage === "reset") && (
        <form onSubmit={stage === "verify" ? verify : reset} className="space-y-4">
          <div>
            <label className={label}>6-digit code</label>
            <input data-testid="code-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6} required value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} placeholder="123456"
              className={field + " tracking-[0.5em] text-center font-mono text-lg"} />
          </div>
          {stage === "reset" && (
            <div>
              <label className={label}>New password (min 8 characters)</label>
              <input data-testid="reset-password-input" type="password" required minLength={8} value={pw} onChange={(e) => setPw(e.target.value)} className={field} />
            </div>
          )}
          <button data-testid="code-submit" disabled={busy || code.length !== 6} className="w-full py-3.5 rounded-xl bg-brand hover:bg-brand-hover text-paper font-semibold text-sm shadow-clay disabled:opacity-60">
            {busy ? "Checking…" : stage === "verify" ? "Verify and continue" : "Update password"}
          </button>
          <button type="button" data-testid="code-resend" disabled={busy || cooldown > 0}
            onClick={stage === "verify" ? resend : () => run(async () => { await forgotPassword(email); setCooldown(60); toast.success("A new code is on its way"); })}
            className="w-full text-xs font-semibold text-brand-deep hover:text-brand disabled:opacity-50">
            {cooldown > 0 ? `Send a new code (${cooldown}s)` : "Send a new code"}
          </button>
        </form>
      )}

      <button type="button" onClick={() => { setStage(null); setCode(""); setPw(""); }}
        className="text-xs text-ink-3 hover:text-ink underline underline-offset-4">← Back to sign in</button>
    </div>
  );
}
