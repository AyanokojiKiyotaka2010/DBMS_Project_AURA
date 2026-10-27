import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { useAuth } from "./context/AuthContext";
import AuthPage from "./components/AuthPage";
import { RoleBadge } from "./components/CampusUI";
import { API, IS_ADMIN, CAN_VIEW_DIGEST, CAN_RUN_REPORTS, CAN_CLASS_TOOLS } from "./lib/campus";

import { Dashboard } from "./components/features/Dashboard";
import { Announcements } from "./components/features/Announcements";
import { Attendance } from "./components/features/Attendance";
import { Queries } from "./components/features/Queries";
import { ProfessorAnalytics } from "./components/features/ProfessorAnalytics";
import { Clubs } from "./components/features/Clubs";
import { TempGroups } from "./components/features/TempGroups";
import { Complaints } from "./components/features/Complaints";
import { AdminPanel } from "./components/features/AdminPanel";
import { WeeklyDigest } from "./components/features/WeeklyDigest";
import { Reports } from "./components/features/Reports";
import { ClassTools } from "./components/features/ClassTools";
import { AcademicSetup } from "./components/features/AcademicSetup";

import {
  House,
  Megaphone,
  Question,
  UsersThree,
  ClockCountdown,
  ShieldWarning,
  SignOut,
  CalendarBlank,
  Sparkle,
  UserGear,
  ChartBar,
  ClipboardText,
  GearSix,
  ChartLineUp,
  Newspaper,
  Warning,
  X,
} from "@phosphor-icons/react";

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: House },
  { id: "announcements", label: "Announcements", icon: Megaphone, group: "Department" },
  { id: "attendance", label: "Attendance", icon: CalendarBlank },
  { id: "digest", label: "Weekly Digest", icon: Newspaper, digestOnly: true },
  { id: "queries", label: "Anonymous Q&A", icon: Question, group: "Learn" },
  { id: "analytics", label: "Professor Analytics", icon: ChartLineUp },
  { id: "clubs", label: "Clubs & Archives", icon: UsersThree, group: "Community" },
  { id: "temp", label: "Temporary Groups", icon: ClockCountdown },
  { id: "complaints", label: "Complaints", icon: ShieldWarning, group: "Admin" },
  { id: "admin", label: "Role Panel", icon: UserGear, adminOnly: true },
  { id: "setup", label: "Academic Setup", icon: GearSix, adminOnly: true },
  { id: "reports", label: "Reports", icon: ChartBar, group: "Academics", reportsOnly: true },
  { id: "classtools", label: "Attendance & Marks", icon: ClipboardText, classOnly: true },
];

function visibleNav(role) {
  return NAV.filter(
    (n) =>
      (!n.adminOnly || IS_ADMIN(role)) &&
      (!n.digestOnly || CAN_VIEW_DIGEST(role)) &&
      (!n.reportsOnly || CAN_RUN_REPORTS(role)) &&
      (!n.classOnly || CAN_CLASS_TOOLS(role))
  );
}

export default function App() {
  const { user, logout, loading, setUser } = useAuth();
  const [active, setActive] = useState("dashboard");
  const [escalations, setEscalations] = useState({ count: 0, items: [], tier: null });
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const prevCountRef = React.useRef(0);
  const firstFetchRef = React.useRef(true);

  useEffect(() => {
    if (!user) return;

    const fetchEscalations = async ({ silent } = {}) => {
      try {
        const r = await axios.get(`${API}/notifications/escalations`);
        const data = r.data;
        const prev = prevCountRef.current;
        prevCountRef.current = data.count;
        setEscalations(data);

        const isEscalationRole = ["Senior", "Alumni", "Professor", "Administrator"].includes(user.role);
        if (!isEscalationRole) return;

        if (firstFetchRef.current) {
          firstFetchRef.current = false;
          if (data.count > 0 && !silent) {
            toast.error(
              `${data.count} escalated ${data.count === 1 ? "query needs" : "queries need"} your attention`,
              { duration: 5000 }
            );
          }
          return;
        }

        // Subsequent polls — only alert when new escalations arrive
        if (data.count > prev) {
          const delta = data.count - prev;
          setBannerDismissed(false);
          toast.error(
            `${delta} new escalated ${delta === 1 ? "query" : "queries"} just landed in your tier`,
            { duration: 6000, id: "esc-poll" }
          );
        }
      } catch {
        /* ignore transient errors */
      }
    };

    fetchEscalations();
    const interval = setInterval(fetchEscalations, 60_000);
    const onFocus = () => fetchEscalations({ silent: true });
    window.addEventListener("focus", onFocus);
    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", onFocus);
    };
  }, [user]);

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center bg-paper text-ink-2">
        <div className="flex items-center gap-3 animate-pulse">
          <Sparkle size={20} className="text-brand" />
          <span className="font-serif text-xl">Preparing your commons…</span>
        </div>
      </div>
    );
  }
  if (!user) return <AuthPage />;

  const nav = visibleNav(user.role);

  return (
    <div data-testid="campus-shell" className="min-h-screen flex bg-paper text-ink">
      <aside
        data-testid="sidebar"
        className="hidden md:flex w-64 shrink-0 flex-col border-r border-edge-light bg-paper-sidebar sticky top-0 h-screen"
      >
        <div className="p-6 border-b border-edge-light">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand text-paper grid place-items-center font-serif text-xl font-bold shadow-clay">A</div>
            <div>
              <div className="font-serif text-xl font-semibold leading-none">AURA</div>
              <div className="text-[10px] uppercase tracking-[0.22em] text-ink-3 mt-1">Campus Commons</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {nav.map((item, i) => {
            const prev = nav[i - 1];
            const showGroup = item.group && item.group !== prev?.group;
            const Icon = item.icon;
            const isActive = active === item.id;
            return (
              <React.Fragment key={item.id}>
                {showGroup && (
                  <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-ink-3 px-3 pt-4 pb-1.5">
                    {item.group}
                  </div>
                )}
                <button
                  data-testid={`nav-${item.id}`}
                  onClick={() => setActive(item.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? "bg-paper-card text-ink shadow-clay border border-edge-light"
                      : "text-ink-2 hover:text-ink hover:bg-paper-card/60"
                  }`}
                >
                  <Icon size={17} weight={isActive ? "duotone" : "regular"} className={isActive ? "text-brand" : ""} />
                  <span>{item.label}</span>
                </button>
              </React.Fragment>
            );
          })}
        </nav>

        <div className="p-4 border-t border-edge-light">
          <div className="tactile-card !p-3 flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-brand/10 text-brand grid place-items-center font-serif font-semibold">
              {user.name?.[0] || "?"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold truncate">{user.name}</div>
              <div className="text-[11px] text-ink-3 truncate">
                {user.department}{user.year ? ` · ${user.year}` : ""}
              </div>
            </div>
            <button
              data-testid="logout-btn"
              onClick={logout}
              title="Sign out"
              className="p-2 rounded-lg text-ink-3 hover:text-brand hover:bg-brand/10 transition-colors"
            >
              <SignOut size={16} />
            </button>
          </div>
          <div className="mt-2 flex justify-center">
            <RoleBadge role={user.role} testid="sidebar-role-badge" />
          </div>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <div className="md:hidden sticky top-0 z-30 bg-paper/85 backdrop-blur border-b border-edge-light">
          <div className="flex items-center gap-2 overflow-x-auto p-3">
            {nav.map((n) => (
              <button
                key={n.id}
                data-testid={`mobile-nav-${n.id}`}
                onClick={() => setActive(n.id)}
                className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold border ${
                  active === n.id
                    ? "bg-brand text-paper border-brand"
                    : "bg-paper-card text-ink-2 border-edge-light"
                }`}
              >
                {n.label}
              </button>
            ))}
          </div>
        </div>

        <div className="p-6 md:p-10 max-w-6xl mx-auto">
          {escalations.count > 0 && !bannerDismissed && (
            <div
              data-testid="escalation-banner"
              className="mb-6 flex items-start gap-3 px-5 py-4 rounded-2xl border border-brand/30 relative overflow-hidden"
              style={{ backgroundColor: "rgba(217, 93, 57, 0.08)" }}
            >
              <div className="mt-0.5 rounded-full bg-brand text-paper p-1.5">
                <Warning size={16} weight="fill" />
              </div>
              <div className="flex-1">
                <div className="text-[11px] uppercase tracking-widest text-brand font-semibold">
                  Escalation ping
                </div>
                <div className="text-sm text-ink font-medium mt-0.5">
                  {escalations.count} {escalations.count === 1 ? "query has" : "queries have"} escalated to{" "}
                  <b>{escalations.tier === "any" ? "the senior / alumni tier" : escalations.tier}</b>. Your input would help.
                </div>
                <button
                  data-testid="banner-goto-queries"
                  onClick={() => setActive("queries")}
                  className="text-xs font-semibold text-brand-deep underline underline-offset-4 mt-1"
                >
                  Open Q&A →
                </button>
              </div>
              <button
                data-testid="banner-dismiss"
                onClick={() => setBannerDismissed(true)}
                className="p-1.5 rounded-lg text-ink-3 hover:text-ink hover:bg-paper-card"
              >
                <X size={14} />
              </button>
            </div>
          )}

          {active === "dashboard" && <Dashboard user={user} setActive={setActive} />}
          {active === "announcements" && <Announcements user={user} />}
          {active === "attendance" && <Attendance user={user} />}
          {active === "digest" && CAN_VIEW_DIGEST(user.role) && <WeeklyDigest user={user} />}
          {active === "queries" && <Queries user={user} />}
          {active === "analytics" && <ProfessorAnalytics />}
          {active === "clubs" && <Clubs user={user} />}
          {active === "temp" && <TempGroups user={user} />}
          {active === "complaints" && <Complaints user={user} />}
          {active === "admin" && IS_ADMIN(user.role) && <AdminPanel setUser={setUser} />}
          {active === "setup" && IS_ADMIN(user.role) && <AcademicSetup />}
          {active === "reports" && CAN_RUN_REPORTS(user.role) && <Reports user={user} />}
          {active === "classtools" && CAN_CLASS_TOOLS(user.role) && <ClassTools user={user} />}
        </div>
      </main>
    </div>
  );
}
