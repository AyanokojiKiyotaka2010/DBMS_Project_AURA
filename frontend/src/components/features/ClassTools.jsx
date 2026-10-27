import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API } from "../../lib/campus";
import { TactileCard, SectionHeading } from "../CampusUI";
import { Field, Select, Btn, inputCls, errMsg } from "./shared";

const today = () => new Date().toISOString().slice(0, 10);

export function ClassTools({ user }) {
  const canMarks = user.role === "Professor" || user.role === "Administrator";
  const [tab, setTab] = useState("attendance");
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  useEffect(() => {
    axios.get(`${API}/courses`, { params: user.role === "Professor" ? { mine: true } : {} })
      .then((r) => setCourses(r.data)).catch((e) => toast.error(errMsg(e)));
  }, [user.role]);
  const course = useMemo(() => courses.find((c) => String(c.id) === courseId), [courses, courseId]);

  return (
    <div className="space-y-6 animate-fade-up" data-testid="class-tools">
      <SectionHeading eyebrow="Classroom" title="Attendance & marks"
        description="Mark who attended each lecture and record exam marks — the reports are built from these records." />
      <TactileCard>
        <div className="grid md:grid-cols-3 gap-3">
          <Field label="Course" className="md:col-span-2">
            <Select testid="ct-course" value={courseId} onChange={setCourseId} placeholder={courses.length ? "Select…" : "No courses available"}
              options={courses.map((c) => ({ value: c.id, label: `${c.code} — ${c.name} (sem ${c.semester})` }))} />
          </Field>
          <div className="flex items-end gap-2">
            <Btn variant={tab === "attendance" ? "primary" : "ghost"} data-testid="ct-tab-attendance" onClick={() => setTab("attendance")}>Attendance</Btn>
            {canMarks && <Btn variant={tab === "marks" ? "primary" : "ghost"} data-testid="ct-tab-marks" onClick={() => setTab("marks")}>Marks</Btn>}
          </div>
        </div>
      </TactileCard>
      {course && tab === "attendance" && <AttendanceSheet user={user} course={course} />}
      {course && tab === "marks" && canMarks && <MarksSheet course={course} />}
    </div>
  );
}

function AttendanceSheet({ user, course }) {
  const [divisions, setDivisions] = useState([]);
  const [divisionId, setDivisionId] = useState(user.division_id && ["CR", "DCR"].includes(user.role) ? String(user.division_id) : "");
  const [date, setDate] = useState(today());
  const [slot, setSlot] = useState(1);
  const [rows, setRows] = useState([]);
  const [info, setInfo] = useState(null);

  useEffect(() => {
    axios.get(`${API}/courses/${course.id}/divisions`).then((r) => {
      setDivisions(r.data.divisions);
      if (r.data.divisions.length === 1) setDivisionId(String(r.data.divisions[0].division_id));
    }).catch((e) => toast.error(errMsg(e)));
  }, [course.id]);

  const load = useCallback(() => {
    if (!divisionId) return setRows([]);
    axios.get(`${API}/courses/${course.id}/attendance-sheet`, { params: { division_id: divisionId, date, slot } })
      .then((r) => { setInfo(r.data); setRows(r.data.students.map((s) => ({ ...s, present: s.present ?? true }))); })
      .catch((e) => { setRows([]); toast.error(errMsg(e)); });
  }, [course.id, divisionId, date, slot]);
  useEffect(() => { load(); }, [load]);

  const toggle = (id) => setRows((rs) => rs.map((r) => (r.student_id === id ? { ...r, present: !r.present } : r)));
  const all = (v) => setRows((rs) => rs.map((r) => ({ ...r, present: v })));
  const save = async () => {
    try {
      const r = await axios.post(`${API}/courses/${course.id}/attendance`, {
        division_id: Number(divisionId), date, slot: Number(slot),
        present_student_ids: rows.filter((x) => x.present).map((x) => x.student_id),
      });
      toast.success(`Saved: ${r.data.present} present, ${r.data.absent} absent`);
      load();
    } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <TactileCard>
      <div className="grid md:grid-cols-4 gap-3 mb-4">
        <Field label="Division"><Select testid="ct-division" disabled={["CR", "DCR"].includes(user.role)} value={divisionId} onChange={setDivisionId} placeholder="Select…"
          options={divisions.map((d) => ({ value: d.division_id, label: `${d.year} · ${d.division} (${d.students})` }))} /></Field>
        <Field label="Date"><input data-testid="ct-date" type="date" max={today()} className={inputCls} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        <Field label="Lecture slot"><input type="number" min="1" max="12" className={inputCls} value={slot} onChange={(e) => setSlot(e.target.value)} /></Field>
        <div className="flex items-end gap-2"><Btn variant="ghost" onClick={() => all(true)}>All present</Btn><Btn variant="ghost" onClick={() => all(false)}>All absent</Btn></div>
      </div>
      {info?.already_marked && <div className="text-xs text-brand-deep bg-brand/10 rounded-lg px-3 py-2 mb-3">This lecture was already marked — saving will overwrite it.</div>}
      {rows.length === 0 && <div className="text-sm text-ink-3 py-4 text-center">{divisionId ? "No students enrolled from this division." : "Pick a division to load the class list."}</div>}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2" data-testid="ct-roster">
        {rows.map((r) => (
          <label key={r.student_id} className={`flex items-center gap-3 px-3 py-2 rounded-xl border cursor-pointer ${r.present ? "border-edge-light bg-paper-card" : "border-brand/40 bg-brand/5"}`}>
            <input type="checkbox" data-testid={`ct-present-${r.student_id}`} checked={r.present} onChange={() => toggle(r.student_id)} />
            <span className="text-sm flex-1">{r.name}<span className="block text-[11px] text-ink-3">{r.roll_no}</span></span>
            <span className={`text-[10px] font-semibold ${r.present ? "text-ink-3" : "text-brand"}`}>{r.present ? "P" : "A"}</span>
          </label>
        ))}
      </div>
      {rows.length > 0 && <div className="mt-4"><Btn data-testid="ct-save-attendance" onClick={save}>Save attendance</Btn></div>}
    </TactileCard>
  );
}

function MarksSheet({ course }) {
  const [rows, setRows] = useState([]);
  const load = useCallback(() => axios.get(`${API}/courses/${course.id}/roster`)
    .then((r) => setRows(r.data.students.map((s) => ({ ...s, input: s.marks_obtained ?? "" }))))
    .catch((e) => toast.error(errMsg(e))), [course.id]);
  useEffect(() => { load(); }, [load]);
  const save = async () => {
    try {
      const entries = rows.map((r) => ({ student_id: r.student_id, marks_obtained: r.input === "" ? null : Number(r.input) }));
      const r = await axios.post(`${API}/courses/${course.id}/results`, { entries });
      toast.success(`${r.data.saved} saved, ${r.data.cleared} cleared`);
      load();
    } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <TactileCard>
      <div className="text-xs text-ink-3 mb-3">Marks out of {course.max_marks}. Pass mark is 40%; failed courses count as backlogs. Leave blank to clear.</div>
      {rows.length === 0 && <div className="text-sm text-ink-3 py-4 text-center">No students are enrolled in this course yet — the administrator enrols divisions under Academic setup.</div>}
      <table className="w-full text-sm" data-testid="ct-marks-table">
        <tbody>
          {rows.map((r) => (
            <tr key={r.student_id} className="border-b border-edge-light/60">
              <td className="py-2 pr-3 text-ink-3 text-xs">{r.roll_no}</td>
              <td className="pr-3">{r.name} <span className="text-[11px] text-ink-3">{r.division}</span></td>
              <td className="pr-3 w-28"><input data-testid={`ct-marks-${r.student_id}`} type="number" min="0" max={course.max_marks} step="0.5" className={inputCls}
                value={r.input} onChange={(e) => setRows((rs) => rs.map((x) => (x.student_id === r.student_id ? { ...x, input: e.target.value } : x)))} /></td>
              <td className="text-xs w-24">{r.grade_letter ? <span className={r.status === "FAIL" ? "text-brand font-semibold" : "text-ink-2"}>{r.grade_letter} · {r.grade_point}{r.status === "FAIL" ? " (backlog)" : ""}</span> : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 0 && <div className="mt-4"><Btn data-testid="ct-save-marks" onClick={save}>Save marks</Btn></div>}
    </TactileCard>
  );
}
