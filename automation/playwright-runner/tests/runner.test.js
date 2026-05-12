import test from "node:test";
import assert from "node:assert/strict";

import { runAction, runTask } from "../src/runner.js";

function createFakePage() {
  return {
    url: null,
    clicked: [],
    filled: [],
    goto: async function (url) {
      this.url = url;
    },
    click: async function (selector) {
      this.clicked.push(selector);
    },
    fill: async function (selector, text) {
      this.filled.push({ selector, text });
    },
    screenshot: async function () {
      return Buffer.from("image-bytes", "utf-8");
    },
    textContent: async function (selector) {
      return `text:${selector}`;
    },
  };
}

test("runAction handles navigate", async () => {
  const page = createFakePage();
  const result = await runAction(page, { type: "navigate", url: "https://example.com" });

  assert.equal(result.ok, true);
  assert.equal(page.url, "https://example.com");
});

test("runAction handles click/type/extract_text/screenshot", async () => {
  const page = createFakePage();

  const clickResult = await runAction(page, { type: "click_selector", selector: "#btn" });
  const typeResult = await runAction(page, { type: "type_selector", selector: "#q", text: "hello" });
  const textResult = await runAction(page, { type: "extract_text", selector: "h1" });
  const screenshotResult = await runAction(page, { type: "screenshot" });

  assert.equal(clickResult.ok, true);
  assert.equal(typeResult.ok, true);
  assert.equal(textResult.data.text, "text:h1");
  assert.ok(typeof screenshotResult.data.screenshot_base64 === "string");
});

test("runTask returns structured results and closes resources", async () => {
  const page = createFakePage();
  let contextClosed = false;
  let browserClosed = false;

  const fakeBrowser = {
    newContext: async () => ({
      newPage: async () => page,
      close: async () => {
        contextClosed = true;
      },
    }),
    close: async () => {
      browserClosed = true;
    },
  };

  const result = await runTask(
    {
      url: "https://example.com",
      actions: [
        { type: "click_selector", selector: "#btn" },
        { type: "type_selector", selector: "#name", text: "kryos" },
        { type: "extract_text", selector: "h1" },
      ],
    },
    async () => fakeBrowser,
  );

  assert.equal(result.success, true);
  assert.equal(result.results.length, 4);
  assert.equal(contextClosed, true);
  assert.equal(browserClosed, true);
});

test("runTask marks unsupported action as failure in results", async () => {
  const page = createFakePage();

  const fakeBrowser = {
    newContext: async () => ({
      newPage: async () => page,
      close: async () => {},
    }),
    close: async () => {},
  };

  const result = await runTask(
    {
      actions: [{ type: "unknown_action" }],
    },
    async () => fakeBrowser,
  );

  assert.equal(result.success, false);
  assert.equal(result.results[0].ok, false);
  assert.equal(result.results[0].type, "unknown_action");
});
