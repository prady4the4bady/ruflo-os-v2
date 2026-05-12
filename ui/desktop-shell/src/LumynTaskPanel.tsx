import { useEffect, useMemo, useState } from "react";

type LumynModel = { id: string; source: string; status: string };
type LumynStatus = {
  tasks: Array<{ task_id: string; status: string; task: string; model_id: string }>;
};

const LUMYN_URL = "http://localhost:8102";
const AUTOMATION_URL = "http://localhost:8101";

export function LumynTaskPanel() {
  const [task, setTask] = useState("");
  const [models, setModels] = useState<LumynModel[]>([]);
  const [selectedModel, setSelectedModel] = useState("lumyn-default");
  const [status, setStatus] = useState<LumynStatus | null>(null);
  const [visionVerify, setVisionVerify] = useState(false);
  const [overlay, setOverlay] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<string>("");

  async function loadModels() {
    const res = await fetch(`${LUMYN_URL}/lumyn/models`);
    if (!res.ok) return;
    const payload = (await res.json()) as { models: LumynModel[]; default_model: string };
    setModels(payload.models ?? []);
    if (payload.default_model) {
      setSelectedModel(payload.default_model);
    }
  }

  async function loadStatus() {
    const res = await fetch(`${LUMYN_URL}/lumyn/status`);
    if (!res.ok) return;
    const payload = (await res.json()) as LumynStatus;
    setStatus(payload);
  }

  useEffect(() => {
    void loadModels();
    void loadStatus();
    const poll = globalThis.setInterval(() => {
      void loadStatus();
    }, 2000);
    return () => globalThis.clearInterval(poll);
  }, []);

  async function submitTask() {
    if (!task.trim()) return;

    const res = await fetch(`${LUMYN_URL}/lumyn/task`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task,
        model_id: selectedModel,
        context: { task_type: "automation" },
      }),
    });

    if (!res.ok) {
      const body = (await res.json()) as { detail?: string };
      const errorMsg = body.detail ?? `HTTP ${res.status}`;
      setLastResult(`Error: ${errorMsg}`);
      return;
    }

    const body = (await res.json()) as { backend: string; result: unknown };
    setLastResult(`${body.backend}: ${JSON.stringify(body.result).slice(0, 400)}`);

    if (visionVerify) {
      try {
        const verify = await fetch(`${AUTOMATION_URL}/automation/vision-verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            screenshot_b64: "base64mock==",
            expected_state_description: task,
          }),
        });
        const verifyBody = (await verify.json()) as { verified?: boolean };
        setOverlay(verifyBody.verified ? "✅ Verified" : "❌ Not verified");
      } catch {
        setOverlay("❌ Verification unavailable");
      }
    }

    setTask("");
    await loadStatus();
  }

  const recentTasks = useMemo(() => status?.tasks?.slice(-5).reverse() ?? [], [status]);

  return (
    <aside className="fixed bottom-4 right-4 z-50 w-[360px] glass rounded-2xl p-3 text-xs shadow-2xl">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold">Lumyn Task Panel</h3>
        <label className="flex items-center gap-1 text-[11px]">
          <input type="checkbox" checked={visionVerify} onChange={(e) => setVisionVerify(e.target.checked)} />
          {" "}
          Vision verify
        </label>
      </div>

      {overlay ? <div className="mb-2 rounded-lg bg-black/20 px-2 py-1 text-center font-medium">{overlay}</div> : null}

      <div className="space-y-2">
        <textarea
          rows={3}
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="Describe a Lumyn task..."
          className="w-full rounded-xl border border-white/20 bg-white/50 dark:bg-black/25 px-3 py-2 text-xs outline-none"
        />
        <div className="flex gap-2">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="flex-1 rounded-lg border border-white/20 bg-white/50 dark:bg-black/25 px-2 py-1"
          >
            <option value="lumyn-default">lumyn-default</option>
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.id}
              </option>
            ))}
          </select>
          <button onClick={() => void submitTask()} className="rounded-lg px-3 py-1 bg-emerald-500/80 text-white">
            Run
          </button>
        </div>
      </div>

      <div className="mt-3 space-y-2">
        <div className="font-medium opacity-70">Live status feed</div>
        <div className="max-h-28 overflow-y-auto space-y-1">
          {recentTasks.length === 0 ? (
            <div className="opacity-60">No tasks yet.</div>
          ) : (
            recentTasks.map((item) => (
              <div key={item.task_id} className="rounded-lg bg-white/40 dark:bg-black/20 p-2">
                <div className="font-medium">{item.status}</div>
                <div className="opacity-70 truncate">{item.task}</div>
                <div className="opacity-60">{item.model_id}</div>
              </div>
            ))
          )}
        </div>
      </div>

      {lastResult ? (
        <div className="mt-2 rounded-lg bg-black/20 p-2 text-[11px] whitespace-pre-wrap max-h-24 overflow-y-auto">
          {lastResult}
        </div>
      ) : null}
    </aside>
  );
}
