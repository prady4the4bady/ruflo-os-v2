import { chromium } from "playwright";

function required(value, message) {
  if (!value) {
    throw new Error(message);
  }
}

export async function runAction(page, action) {
  switch (action.type) {
    case "navigate": {
      required(action.url, "navigate requires url");
      await page.goto(action.url, { waitUntil: "domcontentloaded" });
      return { ok: true, type: action.type, data: { url: action.url } };
    }
    case "click_selector": {
      required(action.selector, "click_selector requires selector");
      await page.click(action.selector);
      return { ok: true, type: action.type, data: { selector: action.selector } };
    }
    case "type_selector": {
      required(action.selector, "type_selector requires selector");
      required(action.text !== undefined, "type_selector requires text");
      await page.fill(action.selector, action.text);
      return { ok: true, type: action.type, data: { selector: action.selector } };
    }
    case "screenshot": {
      const buffer = await page.screenshot({ fullPage: Boolean(action.fullPage) });
      return {
        ok: true,
        type: action.type,
        data: { screenshot_base64: Buffer.from(buffer).toString("base64") },
      };
    }
    case "extract_text": {
      const selector = action.selector || "body";
      const text = await page.textContent(selector);
      return { ok: true, type: action.type, data: { selector, text: text || "" } };
    }
    default:
      throw new Error(`unsupported action type: ${action.type}`);
  }
}

export async function runTask(task, createBrowser = () => chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-setuid-sandbox"] })) {
  if (!task || !Array.isArray(task.actions)) {
    throw new Error("task.actions must be an array");
  }

  const browser = await createBrowser();
  const context = await browser.newContext();
  const page = await context.newPage();

  const results = [];
  try {
    if (task.url) {
      await page.goto(task.url, { waitUntil: "domcontentloaded" });
      results.push({ ok: true, type: "navigate", data: { url: task.url } });
    }

    for (const action of task.actions) {
      try {
        const result = await runAction(page, action);
        results.push(result);
      } catch (error) {
        results.push({
          ok: false,
          type: action?.type || "unknown",
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }

    return {
      success: results.every((item) => item.ok),
      results,
    };
  } finally {
    await context.close();
    await browser.close();
  }
}
