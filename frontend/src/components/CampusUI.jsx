import React from "react";
import { Lock } from "@phosphor-icons/react";

/* Role Badge — pill with role-specific tones */
export const ROLE_STYLES = {
  CR: "bg-role-cr-bg text-role-cr-text border-role-cr-border",
  DCR: "bg-role-dcr-bg text-role-dcr-text border-role-dcr-border",
  Professor: "bg-role-prof-bg text-role-prof-text border-role-prof-border",
  Alumni: "bg-role-alumni-bg text-role-alumni-text border-role-alumni-border",
  Senior: "bg-role-senior-bg text-role-senior-text border-role-senior-border",
  Student: "bg-role-student-bg text-role-student-text border-role-student-border",
  Administrator: "bg-brand/10 text-brand border-brand/30",
  Convener: "bg-brand-deep/10 text-brand-deep border-brand-deep/30",
};

export function RoleBadge({ role, className = "", testid }) {
  const style = ROLE_STYLES[role] || ROLE_STYLES.Student;
  return (
    <span
      data-testid={testid || `role-badge-${role?.toLowerCase()}`}
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-[11px] font-semibold tracking-wide ${style} ${className}`}
    >
      {role}
    </span>
  );
}

/* Encrypted ID chip — shimmering mono chip for anonymous authors */
export function EncryptedIDChip({ id, testid }) {
  return (
    <span
      data-testid={testid || "encrypted-id-chip"}
      className="encrypted-chip inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-edge-light text-[11px] font-mono text-ink-2"
    >
      <Lock size={12} weight="fill" className="text-brand-deep/70" />
      <span className="tracking-tight">{id}</span>
    </span>
  );
}

/* Tactile Card — warm paper card wrapper */
export function TactileCard({ children, className = "", as: Tag = "div", ...rest }) {
  return (
    <Tag className={`tactile-card p-6 ${className}`} {...rest}>
      {children}
    </Tag>
  );
}

/* Attendance Ring — SVG donut with % text */
export function AttendanceRing({ percent, size = 68, stroke = 8 }) {
  const clamped = Math.max(0, Math.min(100, percent));
  const radius = (size - stroke) / 2;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (clamped / 100) * circ;
  const color = clamped >= 75 ? "#2A4747" : clamped >= 60 ? "#E8B255" : "#D95D39";
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="#EAE5D9" strokeWidth={stroke} fill="transparent" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={stroke}
          fill="transparent"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.7s ease-out" }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <span className="font-serif text-lg font-semibold text-ink">{clamped}%</span>
      </div>
    </div>
  );
}

/* Escalation Timeline — visual stepper for query lifecycle */
export function EscalationTimeline({ stage }) {
  // stage: 'peers' | 'seniors' | 'alumni' | 'archived' | 'resolved'
  const steps = [
    { key: "peers", label: "Peers", hint: "0-48h" },
    { key: "seniors", label: "Seniors", hint: "48h+" },
    { key: "alumni", label: "Alumni", hint: "7d+" },
    { key: "archived", label: "Archive", hint: "after 7 days resolved" },
  ];
  const isResolved = stage === "resolved";
  return (
    <div data-testid="escalation-timeline" className="flex items-center gap-1 flex-wrap">
      {isResolved && (
        <span className="px-2 py-1 rounded-full bg-brand-deep text-paper text-[10px] font-semibold uppercase tracking-wider">
          Resolved
        </span>
      )}
      {!isResolved &&
        steps.map((s, i) => {
          const current = s.key === stage;
          return (
            <React.Fragment key={s.key}>
              <div
                className={`px-2 py-1 rounded-full border text-[10px] font-semibold uppercase tracking-wider transition-colors ${
                  current
                    ? "bg-brand text-paper border-brand"
                    : "bg-paper-card text-ink-3 border-edge-light"
                }`}
                title={s.hint}
              >
                {s.label}
              </div>
              {i < steps.length - 1 && (
                <div className="h-px w-3 bg-edge-light" />
              )}
            </React.Fragment>
          );
        })}
    </div>
  );
}

/* Section Heading — editorial style */
export function SectionHeading({ eyebrow, title, description, right }) {
  return (
    <div className="flex items-end justify-between gap-6 flex-wrap">
      <div>
        {eyebrow && (
          <div className="text-[11px] uppercase tracking-[0.22em] text-brand font-semibold mb-2">
            {eyebrow}
          </div>
        )}
        <h2 className="font-serif text-3xl md:text-4xl font-semibold text-ink tracking-tight leading-[1.05]">
          {title}
        </h2>
        {description && <p className="text-sm text-ink-2 mt-2 max-w-xl">{description}</p>}
      </div>
      {right}
    </div>
  );
}
