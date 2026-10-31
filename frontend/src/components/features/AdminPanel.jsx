import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API } from "../../lib/campus";
import { TactileCard, SectionHeading, RoleBadge } from "../CampusUI";

const ROLES = ["Student", "CR", "DCR", "Senior", "Alumni", "Professor", "Convener", "Administrator"];

export function AdminPanel({ setUser }) {
  const [users, setUsers] = useState([]);
  const load = () =>
    axios
      .get(`${API}/admin/users`)
      .then((r) => setUsers(r.data))
      .catch(() => toast.error("Not authorised"));
  useEffect(() => { load(); }, []);

  const changeRole = async (id, role) => {
    try {
      const r = await axios.post(`${API}/admin/users/${id}/role`, { role });
      toast.success(`Role updated → ${role}`);
      if (r.data.self_updated) setUser(r.data.user);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed");
    }
  };

  return (
    <div className="space-y-8 animate-fade-up" data-testid="admin-panel-view">
      <SectionHeading
        eyebrow="Governance"
        title="Role & CR/DCR management"
        description="Promote students to Class Representative, Deputy CR, or lift them to Senior/Alumni after graduation."
      />
      <TactileCard className="!p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-paper-sidebar text-[10px] uppercase tracking-widest text-ink-3 font-semibold">
            <tr>
              <th className="text-left py-3 px-4">Name</th>
              <th className="text-left py-3 px-4">Dept · Year</th>
              <th className="text-left py-3 px-4">Current role</th>
              <th className="text-left py-3 px-4">Change to</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id} className="border-t border-edge-light" data-testid={`admin-user-row-${u.email}`}>
                <td className="py-3 px-4">
                  <div className="font-semibold text-ink">{u.name}</div>
                  <div className="text-[11px] font-mono text-ink-3">{u.email}</div>
                </td>
                <td className="py-3 px-4 text-ink-2">
                  {u.department}{u.year ? " · " + u.year : ""}
                </td>
                <td className="py-3 px-4">
                  <RoleBadge role={u.role} />
                  {u.requested_role && (
                    <div className="mt-1.5 flex items-center gap-2" data-testid={`admin-request-${u.email}`}>
                      <span className="text-[10px] font-semibold text-brand-deep bg-brand/10 rounded-full px-2 py-0.5">
                        requests {u.requested_role}
                      </span>
                      <button
                        data-testid={`admin-approve-${u.email}`}
                        onClick={() => changeRole(u.user_id, u.requested_role)}
                        className="text-[11px] font-semibold text-brand hover:underline"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => changeRole(u.user_id, "Student")}
                        className="text-[11px] text-ink-3 hover:underline"
                      >
                        Decline
                      </button>
                    </div>
                  )}
                </td>
                <td className="py-3 px-4">
                  <select
                    data-testid={`admin-role-select-${u.email}`}
                    value={u.role}
                    onChange={(e) => changeRole(u.user_id, e.target.value)}
                    className="bg-paper-card border border-edge-light rounded-lg px-2 py-1.5 text-xs"
                  >
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr><td colSpan={4} className="py-6 text-center text-ink-3 italic">No users found</td></tr>
            )}
          </tbody>
        </table>
      </TactileCard>
    </div>
  );
}
