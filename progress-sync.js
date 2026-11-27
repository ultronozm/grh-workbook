const codeKey = "grh-workbook:sync-code";
const syncedKey = "grh-workbook:synced-at";
const maxBytes = 256 * 1024;
const encoder = new TextEncoder();
const waitForKV = () => new Promise(resolve => setTimeout(resolve, 1100));

function normalize(code) {
  return code.trim().toLowerCase().split(/[\s-]+/).join(" ");
}

async function generateCode() {
  const response = await fetch(new URL("worker/wordlist.txt", import.meta.url));
  if (!response.ok) throw new Error();
  const words = (await response.text()).trim().split(/\s+/);
  if (words.length !== 2048 || new Set(words).size !== 2048) throw new Error();
  const random = crypto.getRandomValues(new Uint16Array(6));
  return Array.from(random, n => words[n & 2047]).join(" ");
}

async function derive(code) {
  const id = await crypto.subtle.digest("SHA-256", encoder.encode("grh-sync-id:" + code));
  const password = await crypto.subtle.importKey("raw", encoder.encode(code), "PBKDF2", false, ["deriveKey"]);
  const key = await crypto.subtle.deriveKey(
    {name: "PBKDF2", salt: encoder.encode("grh-sync-key"), iterations: 200000, hash: "SHA-256"},
    password, {name: "AES-GCM", length: 256}, false, ["encrypt", "decrypt"],
  );
  return {key, id: Array.from(new Uint8Array(id), n => n.toString(16).padStart(2, "0")).join("")};
}

async function seal(key, entries) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const plaintext = encoder.encode(JSON.stringify({version: 1, entries: Object.fromEntries(entries)}));
  const data = new Uint8Array(await crypto.subtle.encrypt({name: "AES-GCM", iv}, key, plaintext));
  let binary = String.fromCharCode(...iv);
  for (let i = 0; i < data.length; i += 8192) {
    binary += String.fromCharCode(...data.subarray(i, i + 8192));
  }
  return btoa(binary);
}

async function unseal(key, ciphertext, isProgressKey) {
  const data = Uint8Array.from(atob(ciphertext), character => character.charCodeAt(0));
  const plaintext = await crypto.subtle.decrypt({name: "AES-GCM", iv: data.subarray(0, 12)}, key, data.subarray(12));
  const {version, entries} = JSON.parse(new TextDecoder().decode(plaintext));
  if (version !== 1 || !entries || typeof entries !== "object" || Array.isArray(entries)) throw new Error();
  const records = Object.entries(entries);
  for (const [name, entry] of records) {
    if (!isProgressKey(name) || !Array.isArray(entry) || entry.length !== 2 ||
        !Number.isSafeInteger(entry[0]) || entry[0] < 0 ||
        (entry[1] !== null && typeof entry[1] !== "string")) throw new Error();
  }
  return new Map(records);
}

// When two devices edit in the same millisecond, prefer a deletion, then
// compare text so that both devices choose the same result.
function newer(entry, previous) {
  if (!previous || entry[0] !== previous[0]) return !previous || entry[0] > previous[0];
  return previous[1] !== null && (entry[1] === null || entry[1] > previous[1]);
}

function savedAgo(time) {
  const minutes = Math.floor(Math.max(0, Date.now() - time) / 60000);
  if (minutes === 0) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  return `${days} ${days === 1 ? "day" : "days"} ago`;
}

export function startSync({endpoint, storage, isProgressKey, stampPrefix, refresh, panel}) {
  const getCode = () => storage.getItem(codeKey);
  const request = (id, options) => fetch(endpoint.replace(/\/$/, "") + "/v1/" + id, {
    cache: "no-store", credentials: "omit", redirect: "error", referrerPolicy: "no-referrer",
    signal: AbortSignal.timeout(12000), ...options,
  });
  const lock = action => navigator.locks ? navigator.locks.request(codeKey, action) : action();

  function snapshot() {
    const entries = new Map();
    for (let i = 0; i < storage.length; i++) {
      const name = storage.key(i);
      const key = name?.startsWith(stampPrefix) ? name.slice(stampPrefix.length) : name;
      if (key && isProgressKey(key) && !entries.has(key)) {
        entries.set(key, [Number(storage.getItem(stampPrefix + key)), storage.getItem(key)]);
      }
    }
    return entries;
  }

  function merge(remote) {
    const local = snapshot();
    let changed = false;
    try {
      for (const [key, entry] of remote) {
        if (!newer(entry, local.get(key))) continue;
        const [stamp, value] = entry;
        if (storage.getItem(key) !== value) {
          if (value === null) storage.removeItem(key);
          else storage.setItem(key, value);
          changed = true;
        }
        storage.setItem(stampPrefix + key, String(stamp));
        local.set(key, entry);
      }
    } finally {
      if (changed) refresh();
    }
    return local;
  }

  async function put(id, key, entries, headers) {
    const body = await seal(key, entries);
    if (body.length > maxBytes) throw new SyncError("Synced progress exceeds 256 KB.");
    return request(id, {method: "PUT", body, headers});
  }

  function hasChanges(local, remote) {
    return [...local].some(([name, entry]) => newer(entry, remote.get(name)));
  }

  class SyncError extends Error {}

  async function download(id, key) {
    let response = await request(id);
    if (response.status === 503) {
      await waitForKV();
      response = await request(id);
    }
    if (response.status === 404) return null;
    if (!response.ok) throw new Error();
    const etag = response.headers.get("ETag");
    if (!etag) throw new Error();
    try {
      const {ciphertext} = await response.json();
      return {etag, entries: await unseal(key, ciphertext, isProgressKey)};
    } catch {
      throw new SyncError("Could not read the synced data.");
    }
  }

  const ui = panel?.querySelector(".progress-sync");
  const find = selector => ui?.querySelector(selector);
  const setup = find("[data-sync-setup]");
  const create = find("[data-sync-create]");
  const form = find("[data-sync-form]");
  const input = form?.elements.code;
  const connected = find("[data-sync-connected]");
  const shownCode = find("[data-sync-code]");
  const copy = find("[data-sync-copy]");
  const stop = find("[data-sync-stop]");
  const remove = find("[data-sync-delete]");
  const status = find("[data-sync-status]");
  let visibleCode = "";
  let notice = "";
  let working = false;
  let timer;
  let retries = 0;
  let rerun = false;

  function show() {
    if (!ui) return;
    const code = getCode();
    const syncedAt = Number(storage.getItem(syncedKey));
    setup.hidden = Boolean(code);
    connected.hidden = !code;
    shownCode.hidden = !code || visibleCode !== code;
    status.textContent = notice || (code && (syncedAt ? `Synced · ${savedAgo(syncedAt)}` : "Waiting to sync")) || "";
    for (const control of [create, input, form.elements.submitCode, stop, remove]) control.disabled = working;
  }

  function schedule(delay = 0) {
    if (!getCode() || timer !== undefined) return;
    timer = setTimeout(() => {
      timer = undefined;
      if (working) rerun = true;
      else sync();
    }, delay);
  }

  function changed() {
    retries = 0;
    clearTimeout(timer);
    timer = undefined;
    rerun = false;
    schedule(3000);
  }

  async function run(action, onError) {
    working = true;
    show();
    try {
      await lock(action);
    } catch (error) {
      onError(error);
    } finally {
      working = false;
      show();
      if (rerun) {
        rerun = false;
        schedule();
      }
    }
  }

  function saved() {
    storage.setItem(syncedKey, String(Date.now()));
    notice = "";
    retries = 0;
  }

  function sync() {
    const code = getCode();
    if (!code) return;
    run(async () => {
      if (getCode() !== code) return;
      const {id, key} = await derive(code);
      const remote = await download(id, key);
      if (getCode() !== code) return;
      if (!remote) {
        notice = "Synced data is unavailable.";
        return;
      }
      const local = merge(remote.entries);
      if (hasChanges(local, remote.entries)) {
        // GET refreshes the KV TTL with a write. KV allows one write per
        // key per second. Keep the comparison tag from this GET for PUT.
        await waitForKV();
        if (getCode() !== code) return;
        const response = await put(id, key, local, {"If-Match": remote.etag});
        if (response.status === 413) throw new SyncError("Synced progress exceeds 256 KB.");
        if (!response.ok) throw new Error();
      }
      saved();
    }, error => {
      if (error instanceof SyncError) notice = error.message;
      else if (navigator.onLine && retries < 3) {
        retries++;
        schedule(3000 * retries + Math.random() * 1500);
      }
    });
  }

  function connect(code) {
    storage.removeItem(syncedKey);
    storage.setItem(codeKey, code);
  }

  function disconnect() {
    clearTimeout(timer);
    timer = undefined;
    retries = 0;
    rerun = false;
    storage.removeItem(codeKey);
    storage.removeItem(syncedKey);
    visibleCode = "";
    notice = "";
  }

  if (ui) {
    ui.hidden = false;
    create.addEventListener("click", () => {
      notice = "";
      run(async () => {
        if (getCode()) return;
        const code = await generateCode();
        const {id, key} = await derive(code);
        const local = snapshot();
        const response = await put(id, key, local, {"If-None-Match": "*"});
        if (!response.ok) throw new Error();
        connect(code);
        visibleCode = code;
        shownCode.querySelector("code").textContent = code;
        copy.textContent = "Copy";
        saved();
        if (hasChanges(snapshot(), local)) changed();
      }, error => { notice = error instanceof SyncError ? error.message : "Could not create a sync code. Try again."; })
        .then(() => { if (!shownCode.hidden) copy.focus(); });
    });
    form.addEventListener("submit", event => {
      event.preventDefault();
      const code = normalize(input.value);
      if (!/^[a-z]{3,8}( [a-z]{3,8}){5}$/.test(code)) {
        notice = "Enter all six words.";
        show();
        return;
      }
      notice = "";
      run(async () => {
        if (getCode()) return;
        const {id, key} = await derive(code);
        const remote = await download(id, key);
        if (!remote) {
          notice = "No synced data found for that code.";
          return;
        }
        const local = merge(remote.entries);
        connect(code);
        input.value = "";
        if (hasChanges(local, remote.entries)) schedule(3000);
        else saved();
      }, error => { notice = error instanceof SyncError ? error.message : "Could not connect. Try again."; })
        .then(() => { if (getCode()) stop.focus(); else input.focus(); });
    });
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(visibleCode);
        copy.textContent = "Copied";
      } catch {
        const selection = window.getSelection();
        selection.selectAllChildren(shownCode.querySelector("code"));
      }
    });
    stop.addEventListener("click", () => {
      disconnect();
      show();
      create.focus();
    });
    remove.addEventListener("click", () => {
      if (!window.confirm("Delete synced data? Your progress will stay in this browser.")) return;
      const code = getCode();
      notice = "";
      run(async () => {
        if (!code || getCode() !== code) return;
        const {id} = await derive(code);
        const response = await request(id, {method: "DELETE"});
        if (!response.ok) throw new Error();
        disconnect();
        notice = "Synced data deleted.";
      }, () => { notice = "Could not delete synced data. Try again."; })
        .then(() => { if (!getCode()) create.focus(); });
    });
    setInterval(() => { if (ui.open) show(); }, 30000);
    ui.addEventListener("toggle", show);
  }

  window.addEventListener("storage", event => {
    if (event.storageArea !== storage) return;
    if (!event.key || event.key === codeKey) {
      notice = "";
      if (!getCode()) visibleCode = "";
      schedule();
    }
    if (!event.key || event.key === codeKey || event.key === syncedKey) show();
  });
  window.addEventListener("pageshow", event => { if (event.persisted) schedule(); });
  window.addEventListener("online", () => schedule());
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") schedule();
  });

  show();
  schedule();
  return changed;
}
