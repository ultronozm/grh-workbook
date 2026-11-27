const settingsPrefix = "grh-workbook:ai-settings:";
const providerKey = settingsPrefix + "provider";
const providers = {
  anthropic: {model: "claude-sonnet-5-5", url: "https://api.anthropic.com/v1/messages"},
  openai: {model: "gpt-6.2-sol", url: "https://api.openai.com/v1/chat/completions"},
};
const preamble = "GRH via exercises teaches the proof of the generalized Riemann hypothesis for Dirichlet L-functions following a Lean formalization. The reader is working through the exercises.";
const instruction = "Act as a careful referee for this solution. First say in one line whether the argument is correct and complete, correct with gaps, or wrong. Then identify the first real gap or error, quoting the step and saying exactly what is missing, and, if it helps, a hint toward fixing it, but do not write a full proof. Then list any minor points briefly. Do not restate the solution, do not praise, do not pad. If the solution is correct and complete, say so and stop. Use LaTeX with $...$ for mathematics.";
const settingsAnchor = "ai-feedback";

function settings() {
  const provider = localStorage.getItem(providerKey) === "openai" ? "openai" : "anthropic";
  const keyName = settingsPrefix + "key:" + provider;
  const modelName = settingsPrefix + "model:" + provider;
  const remembered = localStorage.getItem(keyName);
  return {
    provider, keyName, modelName, remember: remembered !== null,
    key: sessionStorage.getItem(keyName) || remembered || "",
    model: localStorage.getItem(modelName) || providers[provider].model,
  };
}

function setupSettings(panel) {
  const section = panel.querySelector("#" + settingsAnchor);
  const field = name => section.querySelector("[data-feedback-" + name + "]");
  const provider = field("provider");
  const key = field("key");
  const model = field("model");
  const remember = field("remember");
  const remove = field("remove");
  const status = field("key-status");

  function refresh() {
    const config = settings();
    provider.value = config.provider;
    key.value = config.key;
    model.value = config.model;
    remember.checked = config.remember;
    remove.disabled = !config.key;
  }

  function apply(action) {
    try {
      action();
      status.textContent = "";
    } catch {
      status.textContent = "Could not save settings in this browser.";
    }
  }

  function saveKey() {
    const {keyName} = settings();
    const value = key.value.trim();
    const target = remember.checked ? localStorage : sessionStorage;
    const other = remember.checked ? sessionStorage : localStorage;
    if (value) target.setItem(keyName, value);
    else target.removeItem(keyName);
    other.removeItem(keyName);
    remove.disabled = !value;
  }

  provider.addEventListener("change", () => apply(() => {
    localStorage.setItem(providerKey, provider.value);
    refresh();
  }));
  key.addEventListener("input", () => apply(saveKey));
  remember.addEventListener("change", () => apply(saveKey));
  remove.addEventListener("click", () => apply(() => {
    key.value = "";
    remember.checked = false;
    saveKey();
    key.focus();
  }));
  model.addEventListener("input", () => apply(() => {
    const {modelName} = settings();
    if (model.value.trim()) localStorage.setItem(modelName, model.value.trim());
    else localStorage.removeItem(modelName);
  }));
  model.addEventListener("blur", () => { model.value = settings().model; });

  function reveal() {
    if (location.hash !== "#" + settingsAnchor) return;
    panel.open = section.open = true;
    section.scrollIntoView({block: "start"});
    key.focus({preventScroll: true});
  }
  window.addEventListener("hashchange", reveal);
  window.addEventListener("pageshow", refresh);
  window.addEventListener("storage", event => {
    if (!event.key || event.key.startsWith(settingsPrefix)) refresh();
  });
  refresh();
  reveal();
}

async function solutionHash(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
}

let sheetSource;
async function makePrompt(id, links, solution) {
  const alternate = document.querySelector('link[rel="alternate"][type="text/plain"]');
  sheetSource ??= fetch(alternate.href, {mode: "same-origin"}).then(async response => {
    if (!response.ok) throw new Error();
    return "\n" + (await response.text()).replace(/\r\n/g, "\n");
  }).catch(() => {
    sheetSource = null;
    throw new Error("Could not load the sheet source.");
  });
  const source = await sheetSource;
  const marker = `\n% End problem: ${id}\n`;
  const end = source.indexOf(marker);
  if (end < 0) throw new Error("Could not find the exercise in the sheet source.");
  const shared = `${preamble}\n\nSheet source\n${source.slice(0, end + marker.length).trimStart()}`;
  // Block boundaries let Anthropic look back for a cached earlier exercise.
  const prefix = shared.split(/(?<=\n% End problem: [^\n]+\n)/).filter(Boolean);
  const references = links.length ? await window.workbookReferenceText(links) : [];
  const cited = references.length ? "Linked statements\n\n" + references.join("\n\n") + "\n\n" : "";
  const suffix = `\n\n${cited}Reader's solution\n\n${solution}\n\n${instruction}`;
  return {prefix, suffix};
}

class FeedbackError extends Error {}

async function getFeedback(config, {prefix, suffix}, signal, onText) {
  const {key, provider, model} = config;
  const anthropic = provider === "anthropic";
  const headers = anthropic ? {
    "x-api-key": key, "anthropic-version": "2023-06-01",
    "anthropic-dangerous-direct-browser-access": "true",
  } : {Authorization: "Bearer " + key};
  const body = anthropic ? {
    model, stream: true, max_tokens: 2048,
    messages: [{role: "user", content: [
      ...prefix.map((text, i) => i === prefix.length - 1
        ? {type: "text", text, cache_control: {type: "ephemeral"}}
        : {type: "text", text}),
      {type: "text", text: suffix},
    ]}],
  } : {
    model, stream: true, max_completion_tokens: 4096,
    messages: [{role: "user", content: prefix.join("") + suffix}],
  };
  let response;
  try {
    response = await fetch(providers[provider].url, {
      method: "POST", headers: {"Content-Type": "application/json", ...headers},
      body: JSON.stringify(body), signal, credentials: "omit", redirect: "error",
      cache: "no-store", referrerPolicy: "no-referrer",
    });
  } catch {
    signal.throwIfAborted();
    throw new FeedbackError("Could not reach the provider.");
  }
  if (response.status === 401 || response.status === 403) throw new FeedbackError("Check your API key and permissions.");
  if (response.status === 429) throw new FeedbackError("Provider rate limit reached. Try again later.");
  if (!response.ok) throw new FeedbackError("The provider could not complete the request. Check the model in settings.");
  if (!response.headers.get("Content-Type")?.includes("text/event-stream")) {
    const data = await response.json();
    return {
      model: data.model,
      text: anthropic ? data.content?.filter(block => block.type === "text").map(block => block.text).join("")
        : data.choices?.[0]?.message?.content,
    };
  }

  let text = "", responseModel, buffer = "", complete = false;
  const stream = response.body.pipeThrough(new TextDecoderStream());
  for await (const chunk of stream) {
    buffer += chunk;
    let newline;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newline).trimEnd();
      buffer = buffer.slice(newline + 1);
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (payload === "[DONE]") {
        complete = true;
        continue;
      }
      const data = JSON.parse(payload);
      if (data.type === "error" || data.error) {
        throw new FeedbackError("The provider stopped the response. Try again later.");
      }
      if (data.type === "message_stop") complete = true;
      responseModel = data.model || data.message?.model || responseModel;
      const delta = anthropic
        ? (data.delta?.type === "text_delta" ? data.delta.text : data.content_block?.text)
        : data.choices?.[0]?.delta?.content;
      if (typeof delta === "string" && delta) {
        text += delta;
        onText(text);
      }
    }
  }
  if (!complete) throw new FeedbackError("The response was interrupted. Try again.");
  return {text, model: responseModel};
}

export function startFeedback({
  panel, problems, make, solutionLink, renderMarkdown, typesetSolution,
  readSolution, readFeedback, saveFeedback,
}) {
  if (panel) setupSettings(panel);
  if (!problems.length) return;

  const header = document.querySelector("#title-block-header");
  const batchControls = make("div", "feedback-batch");
  const batchButton = solutionLink("");
  const cancel = solutionLink("Cancel");
  const batchStatus = make("span", "solution-status");
  batchStatus.setAttribute("role", "status");
  batchControls.append(batchButton, cancel, batchStatus);
  batchControls.hidden = true;
  header.append(batchControls);
  let batch;
  let individualRequests = 0;

  const items = problems.map(({problem, ids, area, viewer, revealSolution}) => {
    const links = [...problem.querySelectorAll("a[href]")].filter(link =>
      !link.closest(".used-in, .stable-tag, .problem-solution"));
    const toggle = solutionLink("Feedback");
    const menu = make("div", "feedback-menu");
    menu.id = "feedback-menu-" + problem.id;
    toggle.setAttribute("aria-controls", menu.id);
    toggle.setAttribute("aria-expanded", "false");
    menu.hidden = true;
    const request = solutionLink("Get feedback");
    const stored = solutionLink("Show feedback");
    const setup = make("a", "solution-link", "Add an API key…");
    setup.href = "index.html#" + settingsAnchor;
    const copy = solutionLink("Copy feedback prompt");
    const status = make("div", "solution-status");
    status.setAttribute("role", "status");
    const result = make("div", "feedback-result");
    const meta = make("div", "feedback-meta solution-status");
    const attribution = make("span", "");
    const stale = make("span", "", "Written for an earlier version");
    const renew = solutionLink("Refresh");
    const dismiss = solutionLink("Dismiss");
    const content = make("div", "solution-preview mathjax_ignore");
    meta.append(attribution, stale, renew, dismiss);
    result.append(meta, content);
    menu.append(request, setup, copy, stored);
    viewer.before(toggle, menu);
    area.append(status, result);
    toggle.hidden = result.hidden = true;

    let solution, hash, digest, record, recordKey, dismissed, rendering, inFlight;
    let streamText = "";
    function showMenu(open) {
      menu.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
    }

    function update() {
      const text = readSolution(ids);
      if (solution !== text) {
        solution = text;
        digest = null;
        const pending = text && crypto?.subtle ? solutionHash(text).catch(() => null) : null;
        hash = pending;
        pending?.then(value => {
          if (hash !== pending) return;
          digest = value;
          draw();
        });
        if (!text) {
          inFlight?.abort();
          showMenu(false);
          status.textContent = "";
        }
      }
      const nextRecord = text && readFeedback(ids);
      const nextKey = nextRecord ? JSON.stringify(nextRecord) : "";
      if (nextKey !== recordKey) {
        record = nextRecord;
        recordKey = nextKey;
      }
      draw();
    }

    function draw() {
      const hasKey = Boolean(settings().key);
      toggle.hidden = !solution;
      request.hidden = !hasKey || !crypto?.subtle;
      setup.hidden = hasKey;
      request.disabled = Boolean(inFlight || batch || individualRequests >= 4);
      renew.disabled = request.disabled;
      stored.hidden = !record || dismissed !== recordKey;
      result.hidden = !solution || (!streamText && (!record || dismissed === recordKey));
      if (result.hidden) return;
      if (streamText) {
        meta.hidden = true;
        if (rendering !== streamText) content.textContent = streamText;
        rendering = streamText;
        content.classList.add("feedback-stream");
        return;
      }
      meta.hidden = false;
      const outdated = Boolean(digest && digest !== record.hash);
      stale.hidden = !outdated;
      renew.hidden = !outdated || !hasKey;
      result.classList.toggle("feedback-stale", outdated);
      content.classList.remove("feedback-stream");
      if (rendering === recordKey) return;
      revealSolution();
      attribution.textContent = `Feedback from ${record.model}, ${new Date(record.date).toLocaleDateString()}`;
      const renderedKey = recordKey;
      rendering = renderedKey;
      const {fragment, math} = renderMarkdown(record.text);
      content.replaceChildren(fragment);
      if (math.length) typesetSolution(math, () => rendering === renderedKey).catch(() => {});
    }

    async function run(config, signal) {
      if (inFlight || !solution || signal.aborted) return false;
      const submitted = solution;
      const submittedHash = hash;
      inFlight = new AbortController();
      signal = AbortSignal.any([signal, inFlight.signal]);
      showMenu(false);
      status.textContent = "Getting feedback…";
      draw();
      try {
        const prompt = await makePrompt(ids[0], links, submitted);
        const digest = await submittedHash;
        if (!digest) throw new FeedbackError("Could not verify the saved solution.");
        signal.throwIfAborted();
        const reply = await getFeedback(config, prompt, signal, text => {
          if (signal.aborted || !solution) return;
          streamText = text;
          revealSolution();
          draw();
        });
        signal.throwIfAborted();
        if (!reply.text?.trim()) throw new FeedbackError("The provider returned no feedback.");
        if (readSolution(ids)) {
          saveFeedback(ids, {text: reply.text.trim(), hash: digest, model: reply.model || config.model,
            date: new Date().toISOString()});
          dismissed = null;
        }
        status.textContent = "";
        return true;
      } catch (error) {
        status.textContent = signal.reason?.name === "TimeoutError" ? "The request timed out. Try again."
          : signal.aborted ? "" : error instanceof FeedbackError ? error.message
          : "Could not get feedback. Try again.";
        return false;
      } finally {
        streamText = "";
        inFlight = null;
        refresh();
      }
    }

    async function requestOne() {
      const config = settings();
      if (!config.key || batch || inFlight || individualRequests >= 4) return;
      individualRequests++;
      const pending = run(config, AbortSignal.timeout(120000));
      refresh();
      try {
        await pending;
      } finally {
        individualRequests--;
        refresh();
      }
    }

    toggle.addEventListener("click", () => showMenu(menu.hidden));
    menu.addEventListener("keydown", event => {
      if (event.key !== "Escape") return;
      showMenu(false);
      toggle.focus();
    });
    request.addEventListener("click", requestOne);
    renew.addEventListener("click", requestOne);
    dismiss.addEventListener("click", () => {
      dismissed = recordKey;
      draw();
      toggle.focus();
    });
    stored.addEventListener("click", () => {
      dismissed = null;
      revealSolution();
      draw();
      showMenu(false);
      toggle.focus();
    });
    copy.addEventListener("click", async () => {
      const prompt = makePrompt(ids[0], links, solution);
      try {
        if (globalThis.ClipboardItem && navigator.clipboard?.write) {
          const text = prompt.then(({prefix, suffix}) => new Blob([prefix.join("") + suffix], {type: "text/plain"}));
          await navigator.clipboard.write([new ClipboardItem({"text/plain": text})]);
        } else {
          const {prefix, suffix} = await prompt;
          await navigator.clipboard.writeText(prefix.join("") + suffix);
        }
        status.textContent = "Copied";
        setTimeout(() => {
          if (status.textContent === "Copied") status.textContent = "";
        }, 2100);
      } catch {
        await prompt.catch(() => {});
        status.textContent = "Could not copy the feedback prompt.";
      }
    });
    return {
      update, run,
      async needsFeedback() {
        const current = hash;
        if (!solution || inFlight || !current) return false;
      const digest = await current;
      return Boolean(digest && hash === current && !inFlight && digest !== record?.hash);
      },
    };
  });

  let revision = 0;
  async function updateBatch() {
    const version = ++revision;
    const count = batch ? batch.remaining
      : settings().key ? (await Promise.all(items.map(item => item.needsFeedback()))).filter(Boolean).length : 0;
    if (version !== revision) return;
    batchControls.hidden = !count && !batchStatus.textContent;
    batchButton.hidden = !count;
    batchButton.disabled = Boolean(batch || individualRequests);
    cancel.hidden = !batch;
    batchButton.textContent = batch ? `Getting feedback · ${count} left`
      : `Get feedback on ${count} ${count === 1 ? "solution" : "solutions"}`;
  }

  function refresh() {
    items.forEach(item => item.update());
    updateBatch();
  }

  batchButton.addEventListener("click", async () => {
    const config = settings();
    if (batch || individualRequests || !config.key) return;
    const candidates = (await Promise.all(items.map(async item => await item.needsFeedback() && item))).filter(Boolean);
    if (batch || individualRequests || !candidates.length) return;
    const controller = new AbortController();
    batch = {controller, remaining: candidates.length};
    batchStatus.textContent = "";
    refresh();

    let next = 0, failed = 0;
    async function worker() {
      while (!controller.signal.aborted && next < candidates.length) {
        const item = candidates[next++];
        if (!await item.run(config, AbortSignal.any([controller.signal, AbortSignal.timeout(120000)]))) failed++;
        batch.remaining--;
        updateBatch();
      }
    }
    await Promise.all(Array.from({length: Math.min(4, candidates.length)}, worker));
    batch = null;
    batchStatus.textContent = controller.signal.aborted ? "Cancelled."
      : failed ? `Could not get feedback on ${failed} ${failed === 1 ? "solution" : "solutions"}.` : "";
    refresh();
  });
  cancel.addEventListener("click", () => batch?.controller.abort());
  refresh();
  return refresh;
}
