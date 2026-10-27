import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API, useStructure } from "../../lib/campus";
import { TactileCard, SectionHeading } from "../CampusUI";
import { Field, Select, Btn, DataTable, downloadCsv, inputCls, errMsg } from "./shared";

const REPORTS = {
  cgpa: { label: "CGPA / SGPA", path: "cgpa", blurb: "Credit-weighted grade average, per student or rolled up by year, department or division." },
  course: { label: "Course average", path: "course-average", blurb: "Average marks, pass rate and spread of a course (or every course) in a semester." },
  backlog: { label: "Backlogs", path: "backlogs", blurb: "Students with failed courses." },
  attendance: { label: "Attendance below x%", path: "attendance-below", blurb: "Students whose recorded class attendance is under a threshold you choose." },
};

const COLUMNS = {
  cgpa_student: [["roll_no", "Roll no."], ["name", "Student"], ["department", "Department"], ["year", "Year"], ["division", "Div"], ["cgpa", "GPA"], ["credits", "Credits"], ["backlogs", "Backlogs"]],
  cgpa_group: [["department", "Department"], ["year", "Year"], ["division", "Div"], ["students", "Students"], ["avg_cgpa", "Avg"], ["min_cgpa", "Min"], ["max_cgpa", "Max"], ["students_with_backlogs", "With backlogs"]],
  course: [["code", "Code"], ["course", "Course"], ["semester", "Sem"], ["professor", "Professor"], ["enrolled", "Enrolled"], ["graded", "Graded"], ["avg_marks", "Avg marks"], ["avg_percent", "Avg %"], ["min_marks", "Min"], ["highest_marks", "Max"], ["pass_rate", "Pass %"], ["failed", "Failed"]],
  backlog: [["roll_no", "Roll no."], ["name", "Student"], ["department", "Department"], ["year", "Year"], ["division", "Div"], ["backlogs", "Backlogs"], ["courses", "Courses"]],
  attendance: [["roll_no", "Roll no."], ["name", "Student"], ["division", "Div"], ["course_code", "Course"], ["attended", "Present"], ["total", "Sessions"], ["percent", "%"]],
};

export function Reports({ user }) {
  const structure = useStructure();
  const [kind, setKind] = useState("cgpa");
  const [locked, setLocked] = useState({});
  const [courses, setCourses] = useState([]);
  const [p, setP] = useState({ department_id: "", year_id: "", division_id: "", semester: "", course_id: "", group_by: "student", threshold: "75", mode: "overall", min_backlogs: "1", cgpa_below: "", cgpa_above: "", date_from: "", date_to: "" });
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (v) => setP((s) => ({ ...s, [k]: v }));

  useEffect(() => {
    axios.get(`${API}/reports/scope`).then((r) => {
      setLocked(r.data.locked);
      const fill = {};
      Object.entries(r.data.scope).forEach(([k, v]) => { if (v !== null) fill[k] = String(v); });
      setP((s) => ({ ...s, ...fill }));
    }).catch((e) => toast.error(errMsg(e)));
    axios.get(`${API}/courses`).then((r) => setCourses(r.data)).catch(() => {});
  }, []);

  const divisions = useMemo(
    () => structure.divisions.filter((d) => (!p.department_id || String(d.department_id) === p.department_id) && (!p.year_id || String(d.year_id) === p.year_id)),
    [structure.divisions, p.department_id, p.year_id]
  );
  const courseOpts = useMemo(
    () => courses.filter((c) => (!p.department_id || String(c.department_id) === p.department_id) && (!p.semester || String(c.semester) === p.semester)),
    [courses, p.department_id, p.semester]
  );

  const run = useCallback(async () => {
    const q = {};
    const common = ["department_id", "year_id", "division_id", "semester"];
    const per = {
      cgpa: [...common, "group_by", "cgpa_below", "cgpa_above"],
      course: [...common, "course_id"],
      backlog: [...common, "course_id", "min_backlogs"],
      attendance: [...common, "course_id", "threshold", "mode", "date_from", "date_to"],
    }[kind];
    per.forEach((k) => { if (p[k] !== "" && p[k] != null) q[k] = p[k]; });
    setBusy(true);
    try {
      const r = await axios.get(`${API}/reports/${REPORTS[kind].path}`, { params: q });
      setRes({ kind, ...r.data });
    } catch (e) { setRes(null); toast.error(errMsg(e, "Report failed")); }
    finally { setBusy(false); }
  }, [kind, p]);

  const cols = res && (res.kind === "cgpa" ? COLUMNS[res.group_by === "student" ? "cgpa_student" : "cgpa_group"]
    : res.kind === "attendance" ? COLUMNS.attendance.filter(([k]) => res.mode === "per_course" || k !== "course_code")
    : COLUMNS[res.kind]).map(([key, label]) => ({ key, label }));
  const cgpaGroupCols = res?.kind === "cgpa" && res.group_by !== "student"
    ? cols.filter((c) => !(c.key === "department" && res.group_by === "year") && !(c.key === "year" && res.group_by === "department") && !(c.key === "division" && res.group_by !== "division"))
    : cols;

  const summary = res && (res.kind === "cgpa"
    ? `${res.summary.students} student(s) · overall average ${res.summary.average ?? "—"} (${res.metric})`
    : res.kind === "course" ? `${res.summary.courses} course(s)`
    : res.kind === "backlog" ? `${res.summary.students} student(s) · ${res.summary.total_backlogs} backlog(s)`
    : `${res.summary.students} student(s) below ${res.threshold}%`);

  const lockedDept = locked.department_id, lockedYear = locked.year_id, lockedDiv = locked.division_id;
  return (
    <div className="space-y-6 animate-fade-up" data-testid="reports-view">
      <SectionHeading eyebrow={user.role === "Administrator" ? "H.O.D. console" : "Insights"} title="Academic reports"
        description="Pick a report, set its parameters, press Run. Results are limited to what your role may see." />
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {Object.entries(REPORTS).map(([id, r]) => (
          <button key={id} data-testid={`report-${id}`} onClick={() => { setKind(id); setRes(null); }}
            className={`text-left p-4 rounded-2xl border transition-all ${kind === id ? "bg-paper-card border-brand shadow-clay" : "bg-paper-card/60 border-edge-light hover:border-brand/50"}`}>
            <div className="font-serif text-lg font-semibold">{r.label}</div>
            <div className="text-xs text-ink-3 mt-1">{r.blurb}</div>
          </button>
        ))}
      </div>

      <TactileCard>
        <div className="grid md:grid-cols-4 gap-3">
          <Field label="Department"><Select testid="rp-dept" disabled={lockedDept} value={p.department_id} onChange={(v) => setP((s) => ({ ...s, department_id: v, division_id: "", course_id: "" }))} placeholder="All" options={structure.departments.map((d) => ({ value: d.id, label: d.name }))} /></Field>
          <Field label="Year"><Select testid="rp-year" disabled={lockedYear} value={p.year_id} onChange={(v) => setP((s) => ({ ...s, year_id: v, division_id: "" }))} placeholder="All" options={structure.years.map((y) => ({ value: y.id, label: y.label }))} /></Field>
          <Field label="Division"><Select testid="rp-div" disabled={lockedDiv} value={p.division_id} onChange={set("division_id")} placeholder="All" options={divisions.map((d) => ({ value: d.id, label: `${d.name}${!p.department_id ? ` (${d.department})` : ""}` }))} /></Field>
          <Field label={kind === "course" ? "Semester" : "Semester (optional)"}><Select testid="rp-sem" value={p.semester} onChange={(v) => setP((s) => ({ ...s, semester: v, course_id: "" }))} placeholder="Any" options={[1, 2, 3, 4, 5, 6, 7, 8].map((n) => ({ value: n, label: `Semester ${n}` }))} /></Field>

          {kind === "cgpa" && (<>
            <Field label="Group by"><Select testid="rp-groupby" value={p.group_by} onChange={set("group_by")} options={[
              { value: "student", label: "Student (ranking)" }, { value: "department", label: "Department" }, { value: "year", label: "Year" },
              { value: "department_year", label: "Department × Year" }, { value: "division", label: "Division" }]} /></Field>
            <Field label="GPA below (optional)"><input data-testid="rp-cgpa-below" type="number" step="0.1" min="0" max="10" className={inputCls} value={p.cgpa_below} onChange={(e) => set("cgpa_below")(e.target.value)} /></Field>
            <Field label="GPA above (optional)"><input type="number" step="0.1" min="0" max="10" className={inputCls} value={p.cgpa_above} onChange={(e) => set("cgpa_above")(e.target.value)} /></Field>
          </>)}

          {(kind === "course" || kind === "backlog" || kind === "attendance") && (
            <Field label="Course (optional)"><Select testid="rp-course" value={p.course_id} onChange={set("course_id")} placeholder="All courses" options={courseOpts.map((c) => ({ value: c.id, label: `${c.code} — ${c.name}` }))} /></Field>
          )}
          {kind === "backlog" && <Field label="At least N backlogs"><input data-testid="rp-minbl" type="number" min="1" className={inputCls} value={p.min_backlogs} onChange={(e) => set("min_backlogs")(e.target.value)} /></Field>}

          {kind === "attendance" && (<>
            <Field label="Attendance below (%)">
              <div className="flex gap-2 items-center">
                <input data-testid="rp-threshold" type="number" min="0" max="100" step="0.5" className={inputCls} value={p.threshold} onChange={(e) => set("threshold")(e.target.value)} />
                {[75, 60, 50].map((n) => <button key={n} type="button" data-testid={`rp-preset-${n}`} onClick={() => set("threshold")(String(n))} className="px-2 py-1 rounded-lg text-xs border border-edge-light bg-paper-sidebar hover:border-brand">{n}</button>)}
              </div>
            </Field>
            <Field label="Per"><Select testid="rp-mode" value={p.mode} onChange={set("mode")} options={[{ value: "overall", label: "Student overall" }, { value: "per_course", label: "Student × course" }]} /></Field>
            <Field label="From"><input type="date" className={inputCls} value={p.date_from} onChange={(e) => set("date_from")(e.target.value)} /></Field>
            <Field label="To"><input type="date" className={inputCls} value={p.date_to} onChange={(e) => set("date_to")(e.target.value)} /></Field>
          </>)}
        </div>
        <div className="mt-4 flex gap-2">
          <Btn data-testid="rp-run" onClick={run} disabled={busy || (kind === "course" && !p.semester && !p.course_id)}>{busy ? "Running…" : "Run report"}</Btn>
          {res && res.rows.length > 0 && <Btn variant="ghost" data-testid="rp-csv" onClick={() => downloadCsv(`aura-${res.kind}.csv`, cgpaGroupCols, res.rows)}>Download CSV</Btn>}
        </div>
        {kind === "course" && !p.semester && !p.course_id && <div className="text-xs text-ink-3 mt-2">Choose a semester (or a single course) to run this report.</div>}
      </TactileCard>

      {res && (
        <TactileCard>
          <div className="text-sm text-ink-2 mb-3" data-testid="rp-summary">{summary}</div>
          <DataTable testid="rp-table" columns={cgpaGroupCols} rows={res.rows} />
          {res.kind === "attendance" && <p className="text-[11px] text-ink-3 mt-3">Based on class attendance marked by professors / CRs. Students with no recorded sessions are not listed.</p>}
        </TactileCard>
      )}
    </div>
  );
}
