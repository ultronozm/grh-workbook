import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {once} from "node:events";
import {mkdir, mkdtemp, readFile, rm, writeFile} from "node:fs/promises";
import {createServer} from "node:http";
import {join, extname, resolve} from "node:path";
import {Readable} from "node:stream";
import {test} from "node:test";
import {setTimeout as wait} from "node:timers/promises";
import worker from "../progress-sync.js";

const chrome = process.env.CHROME_BIN || (process.platform === "darwin"
  ? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" : "google-chrome");
const site = "http://[::1]:8000";
const siteDirectory = process.env.SYNC_SITE_DIR || "_site";
const screenshots = process.env.SYNC_SCREEN_DIR;
const codeKey = "grh-workbook:sync-code";
const requireKey = "grh-workbook:require-solution";

async function until(check, message, timeout = 15000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const result = await check();
    if (result) return result;
    await wait(80);
  }
  assert.fail(message);
}

async function listen(t, handler, port = 0, host = "127.0.0.1") {
  const server = createServer(handler).listen(port, host);
  t.after(() => {
    server.closeAllConnections();
    server.close();
  });
  await once(server, "listening");
  return server.address().port;
}

async function device(t, width, height) {
  const profile = await mkdtemp(resolve(".sync-chrome-"));
  const child = spawn(chrome, [
    "--headless", "--no-first-run", "--no-default-browser-check", "--no-proxy-server",
    "--disable-background-networking", "--disable-gpu", "--remote-debugging-port=0",
    "--user-data-dir=" + profile, "about:blank",
  ], {stdio: "ignore"});
  let launchError;
  child.on("error", error => { launchError = error; });
  let ws;
  t.after(async () => {
    ws?.close();
    if (child.pid && child.exitCode === null && child.signalCode === null) {
      const stopped = once(child, "exit");
      child.kill();
      await stopped;
    }
    await rm(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  });
  const port = await until(async () => {
    if (launchError) throw launchError;
    try {
      return (await readFile(join(profile, "DevToolsActivePort"), "utf8")).split("\n")[0];
    } catch {
      return null;
    }
  }, "Chrome did not start");
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  ws = new WebSocket(targets.find(target => target.type === "page").webSocketDebuggerUrl);
  await once(ws, "open");
  const pending = new Map();
  let sequence = 0;
  ws.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    const callback = pending.get(message.id);
    if (!callback) return;
    pending.delete(message.id);
    callback(message);
  });
  const cdp = async (method, params = {}) => {
    const id = ++sequence;
    const response = new Promise(resolve => pending.set(id, resolve));
    ws.send(JSON.stringify({id, method, params}));
    const {result, error} = await response;
    if (error) throw new Error(`${method}: ${error.message}`);
    return result;
  };
  async function evaluate(expression) {
    const result = await cdp("Runtime.evaluate", {expression, returnByValue: true, awaitPromise: true});
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || expression);
    return result.result.value;
  }
  const element = selector => `document.querySelector(${JSON.stringify(selector)})`;
  await cdp("Page.enable");
  await cdp("Network.enable");
  await cdp("Network.setBlockedURLs", {urls: ["https://*"]});
  await cdp("Emulation.setDeviceMetricsOverride", {width, height, deviceScaleFactor: 1, mobile: width < 500});
  if (width < 500) await cdp("Emulation.setTouchEmulationEnabled", {enabled: true});
  return {
    evaluate,
    click: selector => evaluate(element(selector) + ".click()"),
    text: selector => evaluate(element(selector) + "?.textContent.trim()"),
    stored: key => evaluate(`localStorage.getItem(${JSON.stringify(key)})`),
    fill: (selector, text) => evaluate(`{
      const input = ${element(selector)};
      input.value = ${JSON.stringify(text)};
      input.dispatchEvent(new Event("input", {bubbles: true}));
    }`),
    async go(path, ready) {
      await cdp("Page.navigate", {url: site + path});
      await until(() => evaluate(`location.pathname === ${JSON.stringify(path)} && Boolean(${element(ready)})`),
        "Page did not render: " + path);
    },
    visible: () => evaluate('document.dispatchEvent(new Event("visibilitychange"))'),
    offline: offline => cdp("Network.emulateNetworkConditions", {
      offline, latency: 0, downloadThroughput: -1, uploadThroughput: -1,
    }),
    async capture(name) {
      if (!screenshots) return;
      await mkdir(screenshots, {recursive: true});
      const bottom = await evaluate('document.querySelector(".progress-sync a").getBoundingClientRect().bottom + scrollY');
      const clip = {x: 0, y: Math.max(0, Math.ceil(bottom) + 14 - height), width, height, scale: 1};
      const {data} = await cdp("Page.captureScreenshot", {format: "png", captureBeyondViewport: true, clip});
      await writeFile(join(screenshots, name + ".png"), Buffer.from(data, "base64"));
    },
  };
}

test("two Chrome profiles sync marks, solutions and settings through the Worker", {timeout: 120000}, async t => {
  const records = new Map();
  const recentWrites = new Map();
  const traffic = [];
  const SYNC = {
    async get(id) { return records.get(id) ?? null; },
    async put(id, body, {expirationTtl}) {
      assert.equal(expirationTtl, 365 * 86400);
      const now = Date.now();
      if (now - (recentWrites.get(id) ?? 0) < 1000) throw new Error("KV write limit");
      recentWrites.set(id, now);
      records.set(id, body);
    },
    async delete(id) { records.delete(id); },
  };
  const port = await listen(t, async (req, res) => {
    const options = {method: req.method, headers: req.headers};
    if (req.method === "PUT") Object.assign(options, {body: Readable.toWeb(req), duplex: "half"});
    const result = await worker.fetch(new Request("http://" + req.headers.host + req.url, options), {SYNC});
    traffic.push([req.method, result.status, Date.now()]);
    res.writeHead(result.status, Object.fromEntries(result.headers));
    res.end(Buffer.from(await result.arrayBuffer()));
  });
  const script = await readFile("progress.js", "utf8");
  assert.match(script, /const SYNC_ENDPOINT = "";/);
  const endpoint = `http://127.0.0.1:${port}`;
  const enabled = script.replace('const SYNC_ENDPOINT = "";', `const SYNC_ENDPOINT = "${endpoint}";`);
  const assetTypes = {".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".txt": "text/plain"};
  let configured = false;
  await listen(t, async (req, res) => {
    try {
      const path = new URL(req.url, site).pathname.slice(1);
      const contents = path === "progress.js" ? (configured ? enabled : script)
        : await readFile(join(siteDirectory, path));
      res.writeHead(200, {"Content-Type": assetTypes[extname(path)] || "application/octet-stream",
        "Cache-Control": "no-store"});
      res.end(contents);
    } catch {
      res.writeHead(404).end();
    }
  }, 8000, "::1");

  const [a, b] = await Promise.all([device(t, 1280, 900), device(t, 390, 844)]);
  const index = "/index.html";
  const panel = ".progress-panel";
  const syncPanel = ".progress-sync";
  const status = "[data-sync-status]";
  const revealed = `document.querySelector('${syncPanel}').hidden === false`;
  const openPanel = async browser => {
    await until(() => browser.evaluate(revealed), "Sync controls not initialized");
    await browser.evaluate(`document.querySelector('${panel}').open = true;
      document.querySelector('${syncPanel}').open = true`);
  };

  await a.go(index, panel);
  assert.equal(await a.evaluate(`document.querySelector('${syncPanel}').hidden`), true);
  assert.deepEqual(traffic, []);
  const sheet = await a.evaluate("document.querySelector('a[data-sheet-progress]').pathname");
  const mark = ".progress-toggle";
  const solution = "A writes a private solution.";
  const solutionInput = ".problem-solution textarea";
  const solutionLink = ".problem-solution > .solution-link";
  const valueOfMark = browser => browser.evaluate('document.querySelector(".progress-toggle").getAttribute("aria-pressed")');
  const waitForMark = (browser, value) => until(async () => await valueOfMark(browser) === value,
    "Mark did not sync: " + value);

  await a.go(sheet, mark);
  assert.equal(await a.evaluate(`document.querySelector('${syncPanel}') === null`), true);
  await a.click(mark);
  await a.click(solutionLink);
  await a.fill(solutionInput, solution);
  await a.click(".solution-actions button");
  const problem = await a.evaluate('JSON.parse(document.querySelector("[data-progress-ids]").dataset.progressIds)[0]');
  await a.click(".reading-toggle");
  assert.equal(await a.stored("grh-workbook:reading-mode"), "cards");
  const doneKey = "grh-workbook:done:" + problem;
  const solutionKey = "grh-workbook:solution:" + problem;

  configured = true;
  await a.go(index, panel);
  await openPanel(a);
  assert.equal(await a.evaluate('document.querySelector(".progress-sync a").hash === "#privacy" && Boolean(document.getElementById("privacy"))'), true);
  await a.capture("desktop-setup");
  await a.click("[data-sync-create]");
  const code = await until(() => a.text("[data-sync-code] code"), "Code was not created");
  const wordlist = new Set((await readFile("worker/wordlist.txt", "utf8")).trim().split("\n"));
  assert.equal(wordlist.size, 2048);
  assert.equal(code.split(" ").length, 6);
  assert.ok(code.split(" ").every(word => wordlist.has(word)));
  await a.capture("desktop-code");
  await a.evaluate('Object.defineProperty(navigator.clipboard, "writeText", {value: async text => { window.copiedCode = text; }})');
  await a.click("[data-sync-copy]");
  assert.equal(await a.evaluate("window.copiedCode"), code);
  const id = new Uint8Array(await crypto.subtle.digest("SHA-256", Buffer.from("grh-sync-id:" + code))).toHex();
  assert.deepEqual([...records.keys()], [id]);

  const password = await crypto.subtle.importKey("raw", Buffer.from(code), "PBKDF2", false, ["deriveKey"]);
  const key = await crypto.subtle.deriveKey({
    name: "PBKDF2", salt: Buffer.from("grh-sync-key"), iterations: 200000, hash: "SHA-256",
  }, password, {name: "AES-GCM", length: 256}, false, ["decrypt"]);
  async function cloudEntries() {
    const ciphertext = Buffer.from(records.get(id), "base64");
    assert.equal(ciphertext.includes(solution), false);
    const plaintext = await crypto.subtle.decrypt({
      name: "AES-GCM", iv: ciphertext.subarray(0, 12),
    }, key, ciphertext.subarray(12));
    return JSON.parse(Buffer.from(plaintext)).entries;
  }
  assert.deepEqual((await cloudEntries())[solutionKey], [0, solution]);
  assert.deepEqual(Object.keys(await cloudEntries()).sort(), [doneKey, solutionKey].sort());

  await b.go(index, panel);
  await openPanel(b);
  await b.capture("mobile-setup");
  const connect = async code => {
    await b.fill("#workbook-sync-code", code);
    await b.click('[name="submitCode"]');
  };
  await connect("wrong wrong wrong wrong wrong wrong");
  await until(async () => /No synced data/.test(await b.text(status)), "Wrong code was not rejected");
  assert.equal(await b.stored(codeKey), null);
  assert.equal(records.size, 1);
  await b.capture("mobile-wrong-code");

  await connect("  " + code.toUpperCase().replaceAll(" ", "  ") + "  ");
  await until(async () => /Synced/.test(await b.text(status)), "Device B failed to join");
  await b.capture("mobile-synced");
  assert.equal(await b.stored(solutionKey), solution);
  assert.equal(await b.stored("grh-workbook:last-visit"), null);
  assert.equal(await b.stored("grh-workbook:reading-mode"), null);
  assert.equal(await b.stored(doneKey), "1");

  await b.go(sheet, mark);
  await waitForMark(b, "true");
  await b.click(solutionLink);
  await b.offline(true);
  const lastPut = () => traffic.filter(([method, status]) => method === "PUT" && status === 200).length;
  const putsBeforeOffline = lastPut();
  await b.click(mark);
  await b.fill(solutionInput, "Device B kept writing offline.");
  await wait(3350);
  assert.equal(lastPut(), putsBeforeOffline);
  assert.equal(await b.stored(solutionKey), "Device B kept writing offline.");
  await b.offline(false);
  await until(async () => (await cloudEntries())[doneKey]?.[1] === null, "Offline unmark did not sync");
  assert.equal((await cloudEntries())[solutionKey][1], "Device B kept writing offline.");

  await a.go(sheet, mark);
  await waitForMark(a, "false");
  await until(async () => await a.stored(solutionKey) === "Device B kept writing offline.", "B's solution did not reach A");
  await a.click(solutionLink);
  const priorPuts = lastPut();
  const editedAt = Date.now();
  await a.fill(solutionInput, "");
  await a.click(mark);
  await until(() => lastPut() > priorPuts, "A's solution deletion and re-mark did not upload");
  assert.ok(traffic.findLast(([method, status]) => method === "PUT" && status === 200)[2] - editedAt >= 3000);
  assert.equal((await cloudEntries())[solutionKey][1], null);
  await b.visible();
  await waitForMark(b, "true");
  await until(async () => await b.evaluate('document.querySelector(".problem-solution textarea").value') === "",
    "Solution tombstone did not clear the open editor");

  await a.go(index, panel);
  await openPanel(a);
  await a.click("[data-require-solution]");
  await until(async () => (await cloudEntries())[requireKey]?.[1] === "1", "Setting was not uploaded");
  await b.go(index, panel);
  await openPanel(b);
  await until(() => b.evaluate('document.querySelector("[data-require-solution]").checked'), "Setting did not sync");

  await until(() => b.evaluate('!document.querySelector("[data-sync-stop]").disabled'), "Sync did not settle");
  await b.click("[data-sync-stop]");
  assert.equal(await b.stored(codeKey), null);
  assert.equal(await b.stored(doneKey), "1");
  assert.equal(records.size, 1);
  await connect(code);
  await until(async () => /Synced/.test(await b.text(status)), "Device B failed to reconnect");
  await until(() => a.evaluate('!document.querySelector("[data-sync-delete]").disabled'), "Delete still disabled");
  await a.evaluate("window.confirm = () => false");
  await a.click("[data-sync-delete]");
  assert.equal(records.size, 1);
  await a.evaluate("window.confirm = () => true");
  await a.click("[data-sync-delete]");
  await until(async () => /Synced data deleted/.test(await a.text(status)), "Delete did not complete");
  await a.capture("desktop-deleted");
  assert.equal(records.size, 0);
  assert.equal(await a.stored(codeKey), null);
  assert.equal(await a.stored(doneKey), "1");
  await b.visible();
  await until(async () => /unavailable/.test(await b.text(status)), "Device B did not detect deletion");
  assert.equal(await b.stored(doneKey), "1");
  assert.equal(records.size, 0);
});
