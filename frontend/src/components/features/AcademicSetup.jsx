import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API, useStructure } from "../../lib/campus";
import { TactileCard, SectionHeading } from "../CampusUI";
import { Trash } from "@phosphor-icons/react";
import { Field, Select, Btn, DataTable, inputCls, errMsg } from "./shared";

const TABS = [
  ["structure", "Departments, years & divisions"],
  ["courses", "Courses"],
  ["people", "Student placement"],
  ["enroll", "Enrolment"],
];

export function AcademicSetup() {
  const structure = useStructure();
  const [tab, setTab] = useState("structure");
  return (
    <div className="space-y-6 animate-fade-up" data-testid="academic-setup">
      <SectionHeading
        eyebrow="Administration"
        title="Academic setup"
        description="Everything the reports run on is entered here — nothing is preloaded."
      />
      <div className="flex flex-wrap gap-2">
        {TABS.map(([id, label]) => (
          <button key={id} data-testid={`setup-tab-${id}`} onClick={() => setTab(id)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${tab === id ? "bg-brand text-paper border-brand" : "bg-paper-card text-ink-2 border-edge-light"}`}>
            {label}
          </button>
        ))}
      </div>
      {tab === "structure" && <StructureTab structure={structure} />}
      {tab === "courses" && <CoursesTab structure={structure} />}
      {tab === "people" && <PeopleTab structure={structure} />}
      {tab === "enroll" && <EnrollTab structure={structure} />}
    </div>
  );
}

/* ------------------------------------------------------------------ structure */
function StructureTab({ structure }) {
  const [dept, setDept] = useState({ name: "", code: "" });
  const [year, setYear] = useState({ label: "", level_no: "" });
  const [div, setDiv] = useState({ department_id: "", year_id: "", name: "" });

  const act = async (fn, ok) => {
    try { structure.setStructure((await fn()).data); ok && toast.success(ok); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const del = (url) => window.confirm("Delete this entry?") && act(() => axios.delete(`${API}${url}`));

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <TactileCard>
        <h3 className="font-serif text-lg font-semibold mb-3">Departments</h3>
        <form className="flex gap-2 mb-3" onSubmit={(e) => { e.preventDefault(); act(() => axios.post(`${API}/admin/departments`, dept), "Department added").then(() => setDept({ name: "", code: "" })); }}>
          <input required data-testid="dept-name-input" className={inputCls} placeholder="Name" value={dept.name} onChange={(e) => setDept({ ...dept, name: e.target.value })} />
          <input className={inputCls + " !w-24"} placeholder="Code" value={dept.code} onChange={(e) => setDept({ ...dept, code: e.target.value })} />
          <Btn type="submit" data-testid="dept-add-btn">Add</Btn>
        </form>
        <ul className="space-y-1.5">
          {structure.departments.map((d) => (
            <li key={d.id} className="flex items-center justify-between text-sm">
              <span>{d.name} {d.code && <span className="text-ink-3">({d.code})</span>}</span>
              <button onClick={() => del(`/admin/departments/${d.id}`)} className="text-ink-3 hover:text-brand"><Trash size={14} /></button>
            </li>
          ))}
        </ul>
      </TactileCard>

      <TactileCard>
        <h3 className="font-serif text-lg font-semibold mb-3">Years</h3>
        <form className="flex gap-2 mb-3" onSubmit={(e) => { e.preventDefault(); act(() => axios.post(`${API}/admin/years`, { label: year.label, level_no: Number(year.level_no) }), "Year added").then(() => setYear({ label: "", level_no: "" })); }}>
          <input required data-testid="year-label-input" className={inputCls} placeholder="e.g. 2nd Year" value={year.label} onChange={(e) => setYear({ ...year, label: e.target.value })} />
          <input required type="number" min="1" max="10" className={inputCls + " !w-20"} placeholder="No." value={year.level_no} onChange={(e) => setYear({ ...year, level_no: e.target.value })} />
          <Btn type="submit" data-testid="year-add-btn">Add</Btn>
        </form>
        <ul className="space-y-1.5">
          {structure.years.map((y) => (
            <li key={y.id} className="flex items-center justify-between text-sm">
              <span>{y.label} <span className="text-ink-3">(level {y.level_no})</span></span>
              <button onClick={() => del(`/admin/years/${y.id}`)} className="text-ink-3 hover:text-brand"><Trash size={14} /></button>
            </li>
          ))}
        </ul>
      </TactileCard>

      <TactileCard>
        <h3 className="font-serif text-lg font-semibold mb-3">Divisions</h3>
        <form className="space-y-2 mb-3" onSubmit={(e) => { e.preventDefault(); act(() => axios.post(`${API}/admin/divisions`, { department_id: Number(div.department_id), year_id: Number(div.year_id), name: div.name }), "Division added").then(() => setDiv({ ...div, name: "" })); }}>
          <Select testid="div-dept-select" value={div.department_id} onChange={(v) => setDiv({ ...div, department_id: v })} placeholder="Department…" options={structure.departments.map((d) => ({ value: d.id, label: d.name }))} />
          <Select testid="div-year-select" value={div.year_id} onChange={(v) => setDiv({ ...div, year_id: v })} placeholder="Year…" options={structure.years.map((y) => ({ value: y.id, label: y.label }))} />
          <div className="flex gap-2">
            <input required data-testid="div-name-input" className={inputCls} placeholder="Division (A, B…)" value={div.name} onChange={(e) => setDiv({ ...div, name: e.target.value })} />
            <Btn type="submit" data-testid="div-add-btn" disabled={!div.department_id || !div.year_id}>Add</Btn>
          </div>
        </form>
        <ul className="space-y-1.5 max-h-56 overflow-y-auto">
          {structure.divisions.map((d) => (
            <li key={d.id} className="flex items-center justify-between text-sm">
              <span>{d.department} · {d.year} · <b>{d.name}</b></span>
              <button onClick={() => del(`/admin/divisions/${d.id}`)} className="text-ink-3 hover:text-brand"><Trash size={14} /></button>
            </li>
          ))}
        </ul>
      </TactileCard>
    </div>
  );
}

/* ------------------------------------------------------------------ courses */
function CoursesTab({ structure }) {
  const [courses, setCourses] = useState([]);
  const [profs, setProfs] = useState([]);
  const blank = { code: "", name: "", credits: 3, max_marks: 100, department_id: "", year_id: "", semester: "", professor_id: "" };
  const [f, setF] = useState(blank);

  const load = useCallback(() => {
    axios.get(`${API}/courses`).then((r) => setCourses(r.data)).catch(() => {});
    axios.get(`${API}/admin/users`).then((r) => setProfs(r.data.filter((u) => u.role === "Professor"))).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const create = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/admin/courses`, {
        ...f, credits: Number(f.credits), max_marks: Number(f.max_marks), department_id: Number(f.department_id),
        year_id: Number(f.year_id), semester: Number(f.semester), professor_id: f.professor_id ? Number(f.professor_id) : null,
      });
      toast.success("Course added"); setF(blank); load();
    } catch (err) { toast.error(errMsg(err)); }
  };
  const setProf = async (c, pid) => {
    try { await axios.put(`${API}/admin/courses/${c.id}`, { professor_id: pid ? Number(pid) : null }); load(); }
    catch (err) { toast.error(errMsg(err)); }
  };
  const del = async (c) => {
    if (!window.confirm(`Delete ${c.code}?`)) return;
    try { await axios.delete(`${API}/admin/courses/${c.id}`); load(); }
    catch (err) {
      if (err.response?.status === 409 && window.confirm(`${err.response.data.detail}\n\nDelete anyway?`)) {
        await axios.delete(`${API}/admin/courses/${c.id}?force=true`); load();
      } else toast.error(errMsg(err));
    }
  };
  return (
    <div className="space-y-6">
      <TactileCard>
        <form onSubmit={create} className="grid md:grid-cols-4 gap-3" data-testid="course-form">
          <Field label="Code"><input required data-testid="course-code-input" className={inputCls} value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} /></Field>
          <Field label="Name" className="md:col-span-2"><input required data-testid="course-name-input" className={inputCls} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
          <Field label="Credits"><input type="number" step="0.5" min="0.5" className={inputCls} value={f.credits} onChange={(e) => setF({ ...f, credits: e.target.value })} /></Field>
          <Field label="Department"><Select testid="course-dept-select" value={f.department_id} onChange={(v) => setF({ ...f, department_id: v })} placeholder="Select…" options={structure.departments.map((d) => ({ value: d.id, label: d.name }))} /></Field>
          <Field label="Year"><Select testid="course-year-select" value={f.year_id} onChange={(v) => setF({ ...f, year_id: v })} placeholder="Select…" options={structure.years.map((y) => ({ value: y.id, label: y.label }))} /></Field>
          <Field label="Semester (1-8)"><input required data-testid="course-sem-input" type="number" min="1" max="12" className={inputCls} value={f.semester} onChange={(e) => setF({ ...f, semester: e.target.value })} /></Field>
          <Field label="Max marks"><input type="number" min="1" className={inputCls} value={f.max_marks} onChange={(e) => setF({ ...f, max_marks: e.target.value })} /></Field>
          <Field label="Professor" className="md:col-span-2"><Select value={f.professor_id} onChange={(v) => setF({ ...f, professor_id: v })} placeholder="Assign later" options={profs.map((p) => ({ value: p.user_id, label: p.name }))} /></Field>
          <div className="md:col-span-2 flex items-end"><Btn type="submit" data-testid="course-add-btn" disabled={!f.department_id || !f.year_id}>Add course</Btn></div>
        </form>
      </TactileCard>
      <TactileCard>
        <DataTable testid="courses-table" empty="No courses yet." rows={courses} columns={[
          { key: "code", label: "Code" }, { key: "name", label: "Course" }, { key: "department", label: "Department" },
          { key: "year", label: "Year" }, { key: "semester", label: "Sem" }, { key: "credits", label: "Credits" },
          { key: "professor", label: "Professor", render: (c) => (
            <select className="bg-transparent text-sm outline-none" value={c.professor_id ?? ""} onChange={(e) => setProf(c, e.target.value)}>
              <option value="">— unassigned —</option>
              {profs.map((p) => <option key={p.user_id} value={p.user_id}>{p.name}</option>)}
            </select>) },
          { key: "x", label: "", render: (c) => <button onClick={() => del(c)} className="text-ink-3 hover:text-brand"><Trash size={14} /></button> },
        ]} />
      </TactileCard>
    </div>
  );
}

/* ------------------------------------------------------------------ people */
function PeopleTab({ structure }) {
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const load = useCallback(() => axios.get(`${API}/admin/users`).then((r) => setUsers(r.data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);

  const save = async (u, patch) => {
    try { await axios.put(`${API}/admin/users/${u.user_id}/assignment`, patch); load(); toast.success("Saved"); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const shown = users.filter((u) => `${u.name} ${u.email} ${u.roll_no}`.toLowerCase().includes(q.toLowerCase())).slice(0, 100);
  const sel = "bg-transparent text-xs outline-none max-w-[9rem]";
  const val = (v) => (v === null || v === undefined ? "" : v);
  return (
    <TactileCard>
      <input data-testid="people-search" className={inputCls + " mb-4"} placeholder="Search name, email or roll no." value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="overflow-x-auto">
        <table className="w-full text-sm" data-testid="people-table">
          <thead><tr className="text-left text-[11px] uppercase tracking-widest text-ink-3 border-b border-edge-light">
            {["Name", "Role", "Department", "Year", "Division", "Roll no."].map((h) => <th key={h} className="py-2 pr-3">{h}</th>)}
          </tr></thead>
          <tbody>
            {shown.map((u) => {
              const divs = structure.divisions.filter((d) => d.department_id === u.department_id && d.year_id === u.year_id);
              return (
                <tr key={u.user_id} className="border-b border-edge-light/60">
                  <td className="py-2 pr-3"><div className="font-medium">{u.name}</div><div className="text-[11px] text-ink-3">{u.email}</div></td>
                  <td className="pr-3 text-xs">{u.role}</td>
                  <td className="pr-3"><select className={sel} value={val(u.department_id)} onChange={(e) => save(u, { department_id: e.target.value ? Number(e.target.value) : null, division_id: null })}>
                    <option value="">—</option>{structure.departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></td>
                  <td className="pr-3"><select className={sel} value={val(u.year_id)} onChange={(e) => save(u, { year_id: e.target.value ? Number(e.target.value) : null, division_id: null })}>
                    <option value="">—</option>{structure.years.map((y) => <option key={y.id} value={y.id}>{y.label}</option>)}</select></td>
                  <td className="pr-3"><select data-testid={`people-div-${u.user_id}`} className={sel} value={val(u.division_id)} onChange={(e) => save(u, { division_id: e.target.value ? Number(e.target.value) : null })}>
                    <option value="">—</option>{divs.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></td>
                  <td className="pr-3"><input className={sel + " w-24 border-b border-edge-light"} defaultValue={u.roll_no} onBlur={(e) => e.target.value !== (u.roll_no || "") && save(u, { roll_no: e.target.value })} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-ink-3 mt-3">Changing department or year clears the division — pick it again. Make someone a Professor / CR / DCR in the Role Panel.</p>
    </TactileCard>
  );
}

/* ------------------------------------------------------------------ enrolment */
function EnrollTab({ structure }) {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [divisionId, setDivisionId] = useState("");
  useEffect(() => { axios.get(`${API}/courses`).then((r) => setCourses(r.data)).catch(() => {}); }, []);
  const course = useMemo(() => courses.find((c) => String(c.id) === courseId), [courses, courseId]);
  const [roster, setRoster] = useState([]);
  const loadRoster = useCallback(() => courseId
    ? axios.get(`${API}/courses/${courseId}/roster`).then((r) => setRoster(r.data.students)).catch(() => setRoster([]))
    : setRoster([]), [courseId]);
  useEffect(() => { loadRoster(); }, [loadRoster]);

  const enroll = async () => {
    try {
      const r = await axios.post(`${API}/admin/enrollments`, { course_id: Number(courseId), division_id: Number(divisionId) });
      toast.success(`${r.data.enrolled_now} student(s) enrolled (${r.data.total_enrolled} total)`);
      loadRoster();
    } catch (e) { toast.error(errMsg(e)); }
  };
  const remove = async (s) => {
    try { await axios.post(`${API}/admin/enrollments/remove`, { course_id: Number(courseId), student_id: s.student_id }); loadRoster(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <TactileCard>
      <div className="grid md:grid-cols-3 gap-3 mb-4">
        <Field label="Course"><Select testid="enroll-course-select" value={courseId} onChange={setCourseId} placeholder="Select…" options={courses.map((c) => ({ value: c.id, label: `${c.code} — ${c.name} (sem ${c.semester})` }))} /></Field>
        <Field label="Enrol a whole division"><Select testid="enroll-division-select" value={divisionId} onChange={setDivisionId} placeholder="Select…" options={structure.divisions.map((d) => ({ value: d.id, label: `${d.department} · ${d.year} · ${d.name}` }))} /></Field>
        <div className="flex items-end"><Btn data-testid="enroll-btn" onClick={enroll} disabled={!courseId || !divisionId}>Enrol division</Btn></div>
      </div>
      {course && <div className="text-xs text-ink-3 mb-2">{roster.length} student(s) enrolled in {course.code}</div>}
      <DataTable testid="enroll-roster" empty="Pick a course to see who is enrolled." rows={roster} columns={[
        { key: "roll_no", label: "Roll no." }, { key: "name", label: "Student" }, { key: "division", label: "Division" },
        { key: "x", label: "", render: (s) => <button onClick={() => remove(s)} className="text-ink-3 hover:text-brand"><Trash size={14} /></button> },
      ]} />
    </TactileCard>
  );
}
