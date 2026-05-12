import { useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Skill {
  skill_id: string;
  name: string;
  description: string;
  status: "active" | "deprecated" | "deleted";
  elite: boolean;
  use_count: number;
  success_rate: number;
  avg_latency_ms: number;
  last_used_at: number | null;
}

interface SoulFields {
  name?: string;
  personality?: string;
  communication_style?: string;
  preferred_model?: string;
  memory_summary?: unknown[];
}

type Tab = "skills" | "acquire" | "soul";

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const SWARM_BASE = import.meta.env.VITE_SWARM_URL ?? "http://localhost:8000";
const SOUL_USER = "default";

function toErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === "string") return err;
  return "Unexpected error";
}

function skillStatusClass(status: Skill["status"]): string {
  if (status === "active") return "text-emerald-400";
  if (status === "deprecated") return "text-yellow-400";
  return "text-red-400";
}

async function fetchSkills(): Promise<Skill[]> {
  const res = await fetch(`${SWARM_BASE}/lumyn/skills`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.skills as Skill[];
}

async function acquireSkill(task: string): Promise<Skill> {
  const res = await fetch(`${SWARM_BASE}/lumyn/skill/acquire`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_description: task, user_id: SOUL_USER }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.skill as Skill;
}

async function deleteSkill(skillId: string): Promise<void> {
  const res = await fetch(`${SWARM_BASE}/lumyn/skills/${skillId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

async function fetchSoul(): Promise<SoulFields> {
  const res = await fetch(`${SWARM_BASE}/soul/${SOUL_USER}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.fields as SoulFields;
}

async function updateSoul(fields: Partial<SoulFields>): Promise<SoulFields> {
  const res = await fetch(`${SWARM_BASE}/soul/${SOUL_USER}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.fields as SoulFields;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SkillsTab() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    fetchSkills()
      .then(setSkills)
      .catch((e: unknown) => setError(toErrorMessage(e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleDelete = async (id: string) => {
    try {
      await deleteSkill(id);
      load();
    } catch (e: unknown) {
      alert(`Delete failed: ${toErrorMessage(e)}`);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm">Skill Registry</h3>
        <button
          onClick={load}
          className="text-xs px-2 py-1 rounded bg-white/20 hover:bg-white/40 transition"
        >
          Refresh
        </button>
      </div>

      {loading && <p className="text-xs opacity-60">Loading skills…</p>}
      {error && <p className="text-xs text-red-400">{error}</p>}

      {!loading && skills.length === 0 && (
        <p className="text-xs opacity-60">No skills in registry. Use the Acquire tab to create some.</p>
      )}

      <div className="overflow-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="text-left opacity-60 border-b border-white/20">
              <th className="pb-1 pr-3">Name</th>
              <th className="pb-1 pr-3">Status</th>
              <th className="pb-1 pr-3">Uses</th>
              <th className="pb-1 pr-3">Success%</th>
              <th className="pb-1 pr-3">Avg ms</th>
              <th className="pb-1">Actions</th>
            </tr>
          </thead>
          <tbody>
            {skills.map((s) => (
              <tr key={s.skill_id} className="border-b border-white/10 hover:bg-white/5">
                <td className="py-1 pr-3 font-mono">
                  {s.elite && <span title="Elite" className="mr-1">⭐</span>}
                  {s.name}
                </td>
                <td className="py-1 pr-3">
                  <span className={skillStatusClass(s.status)}>
                    {s.status}
                  </span>
                </td>
                <td className="py-1 pr-3">{s.use_count}</td>
                <td className="py-1 pr-3">{(s.success_rate * 100).toFixed(0)}%</td>
                <td className="py-1 pr-3">{s.avg_latency_ms.toFixed(0)}</td>
                <td className="py-1">
                  <button
                    onClick={() => void handleDelete(s.skill_id)}
                    className="text-red-400 hover:text-red-300 transition"
                    title="Delete skill"
                  >
                    🗑
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AcquireTab() {
  const [task, setTask] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Skill | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAcquire = async () => {
    if (!task.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const skill = await acquireSkill(task.trim());
      setResult(skill);
    } catch (e: unknown) {
      setError(toErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <h3 className="font-semibold text-sm">Acquire New Skill</h3>
      <textarea
        className="w-full rounded-lg bg-white/10 border border-white/20 p-2 text-xs resize-none h-20 focus:outline-none focus:ring-1 focus:ring-blue-400"
        placeholder="Describe the task the skill should perform…"
        value={task}
        onChange={(e) => setTask(e.target.value)}
      />
      <button
        disabled={loading || !task.trim()}
        onClick={() => void handleAcquire()}
        className="self-start text-xs px-4 py-1.5 rounded-lg bg-blue-500 hover:bg-blue-400 disabled:opacity-40 text-white transition"
      >
        {loading ? "Acquiring…" : "Acquire Skill"}
      </button>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {result && (
        <div className="rounded-lg bg-emerald-500/10 border border-emerald-400/30 p-3 text-xs space-y-1">
          <div className="font-semibold text-emerald-400">Skill acquired!</div>
          <div><span className="opacity-60">ID:</span> <span className="font-mono">{result.skill_id}</span></div>
          <div><span className="opacity-60">Name:</span> {result.name}</div>
          <div><span className="opacity-60">Status:</span> {result.status}</div>
          <div><span className="opacity-60">Description:</span> {result.description}</div>
        </div>
      )}
    </div>
  );
}

function SoulTab() {
  const [soul, setSoul] = useState<SoulFields | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [form, setForm] = useState<Partial<SoulFields>>({});

  useEffect(() => {
    setLoading(true);
    fetchSoul()
      .then((fields) => {
        setSoul(fields);
        setForm({
          name: fields.name ?? "",
          personality: fields.personality ?? "",
          communication_style: fields.communication_style ?? "",
          preferred_model: fields.preferred_model ?? "",
        });
      })
        .catch((e: unknown) => setError(toErrorMessage(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleChange = (key: keyof SoulFields, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateSoul(form);
      setSoul(updated);
      setDirty(false);
    } catch (e: unknown) {
      setError(toErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="text-xs opacity-60">Loading soul…</p>;

  return (
    <div className="flex flex-col gap-3">
      <h3 className="font-semibold text-sm">SOUL.md — Personality Profile</h3>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <div className="grid grid-cols-2 gap-3">
        {(["name", "personality", "communication_style", "preferred_model"] as const).map((key) => (
          <label key={key} className="flex flex-col gap-1">
            <span className="text-xs opacity-60 capitalize">{key.replaceAll("_", " ")}</span>
            <input
              type="text"
              className="rounded bg-white/10 border border-white/20 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
              value={String(form[key] ?? "")}
              onChange={(e) => handleChange(key, e.target.value)}
            />
          </label>
        ))}
      </div>

      {Array.isArray(soul?.memory_summary) && soul.memory_summary.length > 0 && (
        <div className="mt-2">
          <div className="text-xs font-semibold opacity-60 mb-1">Recent Memory</div>
          <ul className="text-xs space-y-1 max-h-24 overflow-auto">
            {soul.memory_summary.slice(-5).map((m) => (
              <li key={JSON.stringify(m)} className="opacity-70">
                {JSON.stringify(m)}
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        disabled={!dirty || saving}
        onClick={() => void handleSave()}
        className="self-start text-xs px-4 py-1.5 rounded-lg bg-purple-500 hover:bg-purple-400 disabled:opacity-40 text-white transition"
      >
        {saving ? "Saving…" : "Save SOUL"}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function LumynConsole() {
  const [tab, setTab] = useState<Tab>("skills");

  const tabs: { id: Tab; label: string }[] = [
    { id: "skills", label: "⚡ Skills" },
    { id: "acquire", label: "✨ Acquire" },
    { id: "soul", label: "🧬 SOUL" },
  ];

  return (
    <div className="flex flex-col h-full text-sm bg-black/5">
      {/* Tab bar */}
      <div className="flex gap-1 px-3 pt-3 pb-0">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 rounded-t-lg text-xs font-medium transition ${
              tab === t.id
                ? "bg-white/20 text-white"
                : "text-white/50 hover:text-white/80 hover:bg-white/10"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 bg-white/5 rounded-b-lg rounded-tr-lg">
        {tab === "skills" && <SkillsTab />}
        {tab === "acquire" && <AcquireTab />}
        {tab === "soul" && <SoulTab />}
      </div>
    </div>
  );
}
