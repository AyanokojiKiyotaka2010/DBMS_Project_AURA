import React, { useEffect, useState } from "react";
import axios from "axios";
import { API } from "../../lib/campus";
import { TactileCard, SectionHeading } from "../CampusUI";
import { Field, Select, DataTable, inputCls } from "./shared";

export function FacultyDirectory() {
  const [q, setQ] = useState("");
  const [dept, setDept] = useState("");
  const [data, setData] = useState({ departments: [], faculty: [] });
  useEffect(() => {
    const t = setTimeout(() => {
      axios.get(`${API}/faculty`, { params: { q, department: dept || undefined } }).then((r) => setData(r.data)).catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [q, dept]);
  return (
    <div className="space-y-6 animate-fade-up" data-testid="faculty-directory">
      <SectionHeading eyebrow="Campus" title="Faculty directory"
        description="Names and office extensions as published by SVNIT, department by department. Heads of department are marked." />
      <TactileCard>
        <div className="grid md:grid-cols-3 gap-3 mb-4">
          <Field label="Search" className="md:col-span-2"><input data-testid="faculty-search" className={inputCls} placeholder="Name or department" value={q} onChange={(e) => setQ(e.target.value)} /></Field>
          <Field label="Department"><Select testid="faculty-dept" value={dept} onChange={setDept} placeholder="All departments" options={data.departments.map((d) => ({ value: d, label: d }))} /></Field>
        </div>
        <DataTable testid="faculty-table" empty={data.departments.length ? "Nobody matches that search." : "The directory has not been imported yet."}
          rows={data.faculty} columns={[
            { key: "name", label: "Name", render: (f) => <span className="font-medium">{f.name}{f.is_hod && <span className="ml-2 text-[10px] font-semibold text-brand bg-brand/10 rounded-full px-1.5 py-0.5">HOD</span>}</span> },
            { key: "department", label: "Department" },
            { key: "extension", label: "Office ext.", render: (f) => f.extension || "—" },
            { key: "affiliation", label: "Also associated with", render: (f) => f.affiliation || "—" },
          ]} />
      </TactileCard>
    </div>
  );
}
