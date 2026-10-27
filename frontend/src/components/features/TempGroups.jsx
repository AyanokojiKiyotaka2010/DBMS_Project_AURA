import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API } from "../../lib/campus";
import { TactileCard, SectionHeading } from "../CampusUI";
import { UserCirclePlus, Timer } from "@phosphor-icons/react";

export function TempGroups({ user }) {
  const [groups, setGroups] = useState([]);
  const [name, setName] = useState("");
  const [hours, setHours] = useState(24);

  const load = () => axios.get(`${API}/temp-groups`).then((r) => setGroups(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    if (!name) return;
    try {
      await axios.post(`${API}/temp-groups`, { name, hours: Number(hours) });
      setName("");
      toast.success(`Group "${name}" will self-destruct in ${hours}h`);
      load();
    } catch { toast.error("Failed"); }
  };

  const join = async (id) => {
    try {
      await axios.post(`${API}/temp-groups/${id}/join`);
      toast.success("Joined — you'll be dropped when the timer ends");
      load();
    } catch { toast.error("Failed"); }
  };

  return (
    <div className="space-y-8 animate-fade-up" data-testid="temp-groups-view">
      <SectionHeading
        eyebrow="Short-lived"
        title="Temporary groups"
        description="Auto-expiring groups for hackathons, study sprints and one-off fest teams. Members drop off when the timer hits zero."
      />

      <TactileCard className="!p-5">
        <form onSubmit={create} className="flex flex-wrap gap-3 items-center">
          <input
            data-testid="temp-name-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Group name (e.g. Hackathon Team Nova)"
            className="flex-1 min-w-[220px] bg-paper-sidebar border border-edge-light rounded-lg px-3 py-2 text-sm"
          />
          <select
            data-testid="temp-hours-select"
            value={hours}
            onChange={(e) => setHours(e.target.value)}
            className="bg-paper-sidebar border border-edge-light rounded-lg px-3 py-2 text-sm"
          >
            {[6, 12, 24, 48, 72, 168].map((h) => (
              <option key={h} value={h}>{h < 168 ? `${h}h` : "1 week"}</option>
            ))}
          </select>
          <button
            data-testid="temp-create-btn"
            className="px-4 py-2 rounded-lg bg-brand text-paper text-sm font-semibold hover:bg-brand-hover flex items-center gap-2"
          >
            <UserCirclePlus size={14} weight="fill" /> Create
          </button>
        </form>
      </TactileCard>

      <div className="grid md:grid-cols-2 gap-5">
        {groups.map((g) => {
          const remaining = Math.max(0, new Date(g.expires_at) - new Date());
          const hrs = Math.floor(remaining / 3600000);
          const mins = Math.floor((remaining % 3600000) / 60000);
          const joined = (g.members || []).includes(user.user_id);
          return (
            <TactileCard key={g.id} className="!p-5" data-testid={`temp-group-${g.id}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-brand font-semibold flex items-center gap-1">
                    <Timer size={12} weight="fill" /> {hrs}h {mins}m left
                  </div>
                  <div className="font-serif text-xl font-semibold text-ink mt-1">{g.name}</div>
                  <div className="text-xs text-ink-3 mt-1">
                    {(g.members || []).length} members · created by {g.creator_name}
                  </div>
                </div>
                <button
                  data-testid={`temp-join-${g.id}`}
                  onClick={() => join(g.id)}
                  disabled={joined}
                  className={`px-3 py-2 rounded-lg text-xs font-semibold ${
                    joined ? "bg-brand-deep/10 text-brand-deep cursor-default" : "bg-brand-deep text-paper hover:bg-ink"
                  }`}
                >
                  {joined ? "Joined" : "Join"}
                </button>
              </div>
            </TactileCard>
          );
        })}
        {groups.length === 0 && <div className="text-ink-3 italic text-sm">No temporary groups yet.</div>}
      </div>
    </div>
  );
}
