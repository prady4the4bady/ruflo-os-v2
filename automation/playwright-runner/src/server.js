import express from "express";
import { runTask } from "./runner.js";

const app = express();
app.use(express.json({ limit: "5mb" }));

app.get("/healthz", (_req, res) => {
  res.json({ status: "ok" });
});

app.post("/run", async (req, res) => {
  try {
    const task = req.body;
    const result = await runTask(task);
    res.json(result);
  } catch (error) {
    res.status(400).json({
      success: false,
      error: error instanceof Error ? error.message : String(error),
    });
  }
});

const port = Number(process.env.PORT || "3000");
app.listen(port, () => {
  console.log(`playwright-runner listening on ${port}`);
});
