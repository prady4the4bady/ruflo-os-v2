import { describe, it, expect, vi, beforeEach } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { buildTaskGoal } from "../src/components/CommandBar/CommandBar";

// Cast to a spy so we can set resolved values in individual tests
const mockInvoke = invoke as ReturnType<typeof vi.fn>;

describe("buildTaskGoal()", () => {
  it("trims whitespace from the raw goal string", () => {
    expect(buildTaskGoal("  open firefox  ")).toBe("open firefox");
  });

  it("returns an empty string for blank input", () => {
    expect(buildTaskGoal("   ")).toBe("");
  });

  it("preserves inner whitespace", () => {
    expect(buildTaskGoal("go to github.com and star the repo")).toBe(
      "go to github.com and star the repo"
    );
  });
});

describe("invoke(submit_task_cmd) integration", () => {
  beforeEach(() => {
    mockInvoke.mockReset();
  });

  it("calls invoke with the correct command and goal argument", async () => {
    mockInvoke.mockResolvedValueOnce("task-abc-123");
    const goal = "Launch terminal and run ls -la";
    const result = await invoke<string>("submit_task_cmd", { goal });
    expect(mockInvoke).toHaveBeenCalledWith("submit_task_cmd", { goal });
    expect(result).toBe("task-abc-123");
  });

  it("propagates errors thrown by invoke", async () => {
    mockInvoke.mockRejectedValueOnce(new Error("workflow engine offline"));
    await expect(invoke("submit_task_cmd", { goal: "test" })).rejects.toThrow(
      "workflow engine offline"
    );
  });

  it("returns a non-empty task id on success", async () => {
    const fakeId = "d2f3e4a5-0000-4000-8000-000000000001";
    mockInvoke.mockResolvedValueOnce(fakeId);
    const id = await invoke<string>("submit_task_cmd", { goal: "do something" });
    expect(id).toMatch(/^[0-9a-f-]+$/i);
  });
});
