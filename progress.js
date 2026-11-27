// Fold the Lean remarks: most readers do not need them, and a closed
// disclosure keeps them one click away.  Opened for printing and when a
// link points inside one.
(() => {
  "use strict";
  const folded = [];
  for (const remark of document.querySelectorAll("div.leanremark")) {
    const details = document.createElement("details");
    details.className = "leanremark";
    const summary = document.createElement("summary");
    summary.textContent = "In the Lean formalization";
    details.append(summary);
    const first = remark.querySelector(":scope > p:first-child > em:first-child");
    if (first && /^In the Lean formalization/.test(first.textContent)) {
      const rest = first.nextSibling;
      first.remove();
      if (rest && rest.nodeType === Node.TEXT_NODE) rest.textContent = rest.textContent.replace(/^\.\s*/, "");
    }
    while (remark.firstChild) details.append(remark.firstChild);
    remark.replaceWith(details);
    folded.push(details);
  }
  const openFor = () => {
    const target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    const details = target?.closest?.("details.leanremark");
    if (details) details.open = true;
  };
  openFor();
  window.addEventListener("hashchange", openFor);
  let printState = [];
  window.addEventListener("beforeprint", () => {
    printState = folded.map(d => d.open);
    folded.forEach(d => { d.open = true; });
  });
  window.addEventListener("afterprint", () => {
    folded.forEach((d, i) => { d.open = printState[i] ?? false; });
  });
})();

(() => {
  "use strict";

  const prefix = "grh-workbook:done:";
  const solutionPrefix = "grh-workbook:solution:";
  const requireSolutionKey = "grh-workbook:require-solution";
  let storage;
  try {
    storage = window.localStorage;
  } catch {
    return;
  }

  function readDone() {
    const done = new Set();
    for (let i = 0; i < storage.length; i++) {
      const key = storage.key(i);
      if (key?.startsWith(prefix)) done.add(key.slice(prefix.length));
    }
    return done;
  }

  function readSolutions() {
    const solutions = new Map();
    for (let i = 0; i < storage.length; i++) {
      const key = storage.key(i);
      if (!key?.startsWith(solutionPrefix)) continue;
      const text = storage.getItem(key);
      if (text?.trim()) solutions.set(key.slice(solutionPrefix.length), text);
    }
    return solutions;
  }

  function readSolution(ids) {
    for (const id of ids) {
      const text = storage.getItem(solutionPrefix + id);
      if (text?.trim()) return text;
    }
    return "";
  }

  function saveSolution([id, ...aliases], text) {
    if (text.trim()) storage.setItem(solutionPrefix + id, text);
    else storage.removeItem(solutionPrefix + id);
    aliases.forEach(alias => storage.removeItem(solutionPrefix + alias));
  }

  function make(tag, className, text = "") {
    const node = document.createElement(tag);
    node.className = className;
    node.textContent = text;
    return node;
  }

  function solutionLink(text) {
    const button = make("button", "solution-link", text);
    button.type = "button";
    return button;
  }

  function inlineMarkdown(parent, source, math) {
    const literals = [];
    // Protect math and code before interpreting Markdown punctuation.
    const text = source.replace(/\0/g, "�").replace(
      /`([^`\n]+)`|(\\\(([\s\S]+?)\\\)|\$((?:\\.|[^$\\\n])+)\$)|(\\\$)/g,
      (_, code, formula, parens, dollars) => {
        if (formula) {
          const span = make("span", "solution-math", formula);
          math.push([span, parens ?? dollars]);
          literals.push(span);
        } else {
          literals.push(code ? make("code", "", code) : document.createTextNode("$"));
        }
        return `\0${literals.length - 1}\0`;
      });

    function append(node, input) {
      const tokens = /\0(\d+)\0|\*\*(.+?)\*\*|__(.+?)__|\*([^*]+)\*|(?<!\w)_([^_]+)_(?!\w)/g;
      let end = 0;
      for (const match of input.matchAll(tokens)) {
        node.append(input.slice(end, match.index));
        const [, literal, boldStar, boldUnderscore, italicStar, italicUnderscore] = match;
        if (literal !== undefined) node.append(literals[Number(literal)]);
        else {
          const strong = boldStar ?? boldUnderscore;
          const emphasis = document.createElement(strong ? "strong" : "em");
          append(emphasis, strong ?? italicStar ?? italicUnderscore);
          node.append(emphasis);
        }
        end = match.index + match[0].length;
      }
      node.append(input.slice(end));
    }
    append(parent, text);
  }

  function renderMarkdown(source) {
    const fragment = document.createDocumentFragment();
    const math = [];
    let paragraph = [];
    let list;
    let code;

    function flushParagraph() {
      if (!paragraph.length) return;
      const node = document.createElement("p");
      inlineMarkdown(node, paragraph.join(" "), math);
      fragment.append(node);
      paragraph = [];
    }

    for (const line of source.split("\n")) {
      if (/^\s*```/.test(line)) {
        flushParagraph();
        list = null;
        if (code) code = null;
        else {
          code = document.createElement("code");
          const pre = document.createElement("pre");
          pre.append(code);
          fragment.append(pre);
        }
      } else if (code) {
        code.append(line + "\n");
      } else if (!line.trim()) {
        flushParagraph();
        list = null;
      } else {
        const item = /^\s*(?:[-*+]|(\d+)\.)\s+(.+)$/.exec(line);
        if (!item) {
          list = null;
          paragraph.push(line.trim());
          continue;
        }
        flushParagraph();
        const kind = item[1] ? "ol" : "ul";
        if (list?.localName !== kind) {
          list = document.createElement(kind);
          if (item[1] && item[1] !== "1") list.start = Number(item[1]);
          fragment.append(list);
        }
        const li = document.createElement("li");
        inlineMarkdown(li, item[2], math);
        list.append(li);
      }
    }
    flushParagraph();
    return {fragment, math};
  }

  let mathDocument;
  async function typesetSolution(math, current) {
    const mj = window.MathJax;
    await mj?.startup?.promise;
    if (!mj?.startup?.document || !current()) return;
    const main = mj.startup.document;
    const engine = mj._.mathjax.mathjax;
    // Keep draft macros and labels out of the sheet's TeX state. Use the
    // math packages without the HTML and dynamic package-loading commands.
    mathDocument ??= engine.document(document, {
      InputJax: new main.inputJax[0].constructor({
        macros: mj.config.tex?.macros,
        packages: ["base", "ams", "newcommand", "configmacros", "noundefined"],
      }),
      OutputJax: main.outputJax,
    });
    for (const [span, tex] of math) {
      if (!current()) return;
      try {
        const result = await engine.handleRetriesFor(() => mathDocument.convert(tex, {display: false}));
        if (!current()) return;
        result.removeAttribute("id");
        result.querySelectorAll("[id]").forEach(node => node.removeAttribute("id"));
        span.replaceChildren(result);
      } catch {
        // Leave the source visible if a formula cannot be rendered.
      }
    }
    // Characters not yet used on the page (e.g. an upright Delta or a
    // blackboard E) need their font rules added to the shared stylesheet.
    try {
      const sheet = main.outputJax.styleSheet(mathDocument);
      if (sheet && !sheet.isConnected) document.head.append(sheet);
    } catch {
      // The formulas stay in place even if the stylesheet cannot be refreshed.
    }
  }

  const solutionEditors = [];
  function addSolutionEditor(problem, ids, label) {
    const area = make("div", "problem-solution");
    const view = solutionLink("View solution");
    const toggle = solutionLink("Write solution");
    const viewer = make("div", "solution-preview solution-viewer mathjax_ignore");
    viewer.hidden = true;
    area.append(view, toggle, viewer);
    problem.append(area);
    let editor, input, note, preview, status, timer, revision = 0, viewRevision = 0;
    let saved = "";
    let dirty = false;

    function refreshLink() {
      saved = readSolution(ids);
      toggle.textContent = saved ? "Edit solution" : "Write solution";
      toggle.classList.toggle("solution-written", Boolean(saved));
      view.hidden = !saved || (editor && !editor.hidden);
      if (!saved) hideViewer();
    }

    function hideViewer() {
      viewRevision++;
      viewer.hidden = true;
      viewer.replaceChildren();
      view.textContent = "View solution";
    }

    function showViewer() {
      const version = ++viewRevision;
      const {fragment, math} = renderMarkdown(saved);
      viewer.replaceChildren(fragment);
      viewer.hidden = false;
      view.textContent = "Hide solution";
      if (math.length) typesetSolution(math, () => viewRevision === version).catch(() => {});
    }

    function grow() {
      if (CSS.supports("field-sizing", "content")) return;
      input.style.height = "auto";
      input.style.height = `${input.scrollHeight + input.offsetHeight - input.clientHeight}px`;
    }

    function updatePreview() {
      const version = ++revision;
      clearTimeout(timer);
      timer = setTimeout(() => {
        const {fragment, math} = renderMarkdown(input.value);
        preview.replaceChildren(fragment);
        if (math.length) {
          typesetSolution(math, () => revision === version).catch(() => {});
        }
      }, 250);
    }

    function showNote(required) {
      note.hidden = !required;
      if (required) input.setAttribute("aria-describedby", note.id);
      else input.removeAttribute("aria-describedby");
    }

    function save() {
      try {
        saveSolution(ids, input.value);
        dirty = false;
        status.textContent = input.value.trim() ? "Saved" : "";
        if (input.value.trim()) showNote(false);
        refreshLink();
      } catch {
        dirty = true;
        status.textContent = "Could not save in this browser.";
      }
    }

    function close() {
      if (dirty) {
        save();
        if (dirty) return;
      }
      clearTimeout(timer);
      revision++;
      editor.hidden = true;
      preview.replaceChildren();
      toggle.hidden = false;
      refreshLink();
      toggle.focus();
    }

    function open(required = false) {
      if (!editor) {
        editor = make("div", "solution-editor");
        editor.hidden = true;
        note = make("p", "solution-note", "Write a solution before marking this problem done.");
        note.id = `solution-note-${problem.id}`;
        input = document.createElement("textarea");
        input.rows = 3;
        input.setAttribute("aria-label", `Solution for ${label} (Markdown and TeX)`);
        input.placeholder = "Markdown and TeX";
        preview = make("div", "solution-preview mathjax_ignore");
        const actions = make("div", "solution-actions");
        const done = solutionLink("Done");
        status = make("span", "solution-status");
        status.setAttribute("role", "status");
        actions.append(done, status);
        editor.append(note, input, preview, actions);
        area.append(editor);
        input.addEventListener("input", () => {
          grow();
          save();
          updatePreview();
        });
        done.addEventListener("click", close);
        editor.addEventListener("keydown", event => {
          if (event.key !== "Escape" || event.isComposing) return;
          event.preventDefault();
          event.stopPropagation();
          close();
        });
      }
      if (editor.hidden) {
        refreshLink();
        input.value = saved;
        status.textContent = saved ? "Saved" : "";
        hideViewer();
        editor.hidden = false;
        toggle.hidden = true;
        view.hidden = true;
        grow();
        updatePreview();
      }
      showNote(required);
      input.focus();
    }

    toggle.addEventListener("click", () => open());
    view.addEventListener("click", () => (viewer.hidden ? showViewer() : hideViewer()));
    refreshLink();
    solutionEditors.push(() => {
      const previous = saved;
      refreshLink();
      if (!dirty && editor && !editor.hidden && previous !== saved) {
        input.value = saved;
        status.textContent = saved ? "Saved" : "";
        if (saved) showNote(false);
        grow();
        updatePreview();
      }
    });
    return open;
  }

  const renderers = [];
  function render() {
    const done = readDone();
    const isDone = ids => ids.some(id => done.has(id));
    renderers.forEach(update => update(isDone));
  }

  function addCount(container, problems, onIndex) {
    const count = document.createElement("span");
    count.className = "progress-count";
    count.hidden = true;
    if (onIndex) container.after(count);
    else container.append(count);

    renderers.push(isDone => {
      const total = problems.length;
      const done = problems.filter(isDone).length;
      count.hidden = done === 0;
      count.textContent = onIndex ? `${done}/${total}` : `${done} of ${total} done`;
      count.classList.toggle("progress-complete", onIndex && done === total);
    });
  }

  const problems = [];
  for (const problem of document.querySelectorAll("[data-progress-ids]")) {
    const ids = JSON.parse(problem.dataset.progressIds);
    const heading = problem.querySelector(":scope > p:first-of-type > strong:first-child");
    if (!heading) continue;
    problems.push(ids);
    const editSolution = addSolutionEditor(problem, ids, heading.textContent.trim());

    const button = document.createElement("button");
    button.type = "button";
    button.className = "progress-toggle";
    // Keep the accessible name steady when aria-pressed changes.
    button.setAttribute("aria-label", `Mark ${heading.textContent} as done`);
    heading.classList.add("progress-heading");
    heading.prepend(button);

    renderers.push(isDone => {
      const pressed = isDone(ids);
      button.setAttribute("aria-pressed", pressed);
      button.title = pressed ? "Mark as not done" : "Mark as done";
    });

    // The heading ("Problem 1.1.1") is a larger target for the same toggle,
    // which matters on phones.  Selecting text in it does not toggle.
    heading.addEventListener("click", event => {
      if (event.target.closest("button, a")) return;
      if (String(window.getSelection?.() || "")) return;
      button.click();
    });

    button.addEventListener("click", () => {
      try {
        if (ids.some(id => storage.getItem(prefix + id) !== null)) {
          ids.forEach(id => storage.removeItem(prefix + id));
        } else {
          if (storage.getItem(requireSolutionKey) === "1" && !readSolution(ids)) {
            editSolution(true);
            return;
          }
          storage.setItem(prefix + ids[0], "1");
        }
      } catch {
        // Leave the button showing the saved state if storage is full.
      }
      render();
    });
  }

  const headerLine = document.querySelector("#title-block-header .date") || document.querySelector("h1.title");
  if (problems.length && headerLine) addCount(headerLine, problems, false);

  for (const link of document.querySelectorAll("[data-sheet-progress]")) {
    addCount(link, JSON.parse(link.dataset.sheetProgress), true);
  }

  for (const node of document.querySelectorAll("[data-flowchart-progress]")) {
    const problems = JSON.parse(node.dataset.flowchartProgress);
    const title = node.querySelector("title");
    const label = title.textContent;
    renderers.push(isDone => {
      const done = problems.filter(isDone).length;
      const total = problems.length;
      if (done) node.dataset.completion = done === total ? "done" : "partial";
      else delete node.dataset.completion;
      title.textContent = done ? `${label} (${done} of ${total} done)` : label;
    });
  }

  const template = document.querySelector("#workbook-progress");
  const lastVisitKey = "grh-workbook:last-visit";
  if (template) {
    const continuation = document.createElement("p");
    continuation.className = "reading-continue";
    continuation.hidden = true;
    const link = document.createElement("a");
    continuation.append("Continue: ", link);
    const title = document.querySelector("#content > h1.title");
    title?.after(continuation);

    const update = () => {
      let visit;
      try {
        visit = JSON.parse(storage.getItem(lastVisitKey));
      } catch {
        visit = null;
      }
      const sheet = [...document.querySelectorAll("a[data-sheet-progress]")]
        .find(chapter => chapter.pathname === visit?.path);
      continuation.hidden = !sheet;
      if (!sheet) return;
      link.href = sheet.href;
      const chapter = sheet.textContent.trim().replace(/^(S?\d+)\.\s*/, "Chapter $1, ");
      link.textContent = chapter;
      if (visit.id && visit.label) {
        link.hash = encodeURIComponent(visit.id);
        link.textContent = `${chapter.split(",")[0]}, ${visit.label}`;
      }
    };
    update();
    window.addEventListener("pageshow", update);
    window.addEventListener("storage", event => {
      if (event.storageArea === storage && (!event.key || event.key === lastVisitKey)) update();
    });
  }
  if (template) {
    const panel = template.content.firstElementChild.cloneNode(true);
    const file = panel.querySelector('input[type="file"]');
    const status = panel.querySelector('[role="status"]');
    const required = panel.querySelector("[data-require-solution]");
    document.body.append(panel);

    const destinations = [];
    for (const sheet of document.querySelectorAll("a[data-sheet-problems]")) {
      const ids = JSON.parse(sheet.dataset.sheetProgress);
      const chapter = sheet.textContent.trim().match(/^S?\d+/)?.[0];
      JSON.parse(sheet.dataset.sheetProblems).forEach(([anchor, label], i) => {
        const url = new URL(sheet.href);
        url.hash = encodeURIComponent(anchor);
        destinations.push({ids: ids[i], heading: `Chapter ${chapter}, ${label}`, url: url.href});
      });
    }
    const knownIds = new Set(destinations.flatMap(({ids}) => ids));

    function download(name, type, contents) {
      const url = URL.createObjectURL(new Blob([contents + "\n"], {type}));
      const link = document.createElement("a");
      link.href = url;
      link.download = name;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    function updateSetting() {
      required.checked = storage.getItem(requireSolutionKey) === "1";
    }
    updateSetting();
    window.addEventListener("pageshow", updateSetting);
    window.addEventListener("storage", event => {
      if (event.storageArea === storage && (!event.key || event.key === requireSolutionKey)) updateSetting();
    });
    required.addEventListener("change", () => {
      try {
        if (required.checked) storage.setItem(requireSolutionKey, "1");
        else storage.removeItem(requireSolutionKey);
        status.textContent = "";
      } catch {
        updateSetting();
        status.textContent = "Could not save the setting in this browser.";
      }
    });

    panel.querySelector("[data-export]").addEventListener("click", () => {
      const backup = {
        version: 1,
        done: [...readDone()].sort(),
        solutions: Object.fromEntries([...readSolutions()].sort(([a], [b]) => a.localeCompare(b))),
      };
      download("grh-workbook-progress.json", "application/json", JSON.stringify(backup, null, 2));
    });

    panel.querySelector("[data-export-solutions]").addEventListener("click", () => {
      const sections = [];
      for (const {ids, heading, url} of destinations) {
        const text = readSolution(ids);
        if (text) sections.push(`## [${heading}](<${url}>)\n\n${text}`);
      }
      const other = [...readSolutions()].filter(([id]) => !knownIds.has(id));
      if (other.length) {
        sections.push("## Other saved solutions",
          ...other.map(([id, text]) => `### ${id}\n\n${text}`));
      }
      if (sections.length) {
        status.textContent = "";
        download("grh-workbook-solutions.md", "text/markdown", sections.join("\n\n"));
      } else {
        status.textContent = "No saved solutions.";
      }
    });

    panel.querySelector("[data-import]").addEventListener("click", () => file.click());
    file.addEventListener("change", async () => {
      const selected = file.files[0];
      if (!selected) return;
      file.value = "";
      let backup;
      try {
        backup = JSON.parse(await selected.text());
        const solutions = backup?.solutions;
        if (backup?.version !== 1 || !Array.isArray(backup.done) ||
            !backup.done.every(id => typeof id === "string" && id.length > 0) ||
            (solutions !== undefined && (!solutions || typeof solutions !== "object" ||
              Array.isArray(solutions) || !Object.entries(solutions).every(([id, text]) =>
                id && typeof text === "string" && text.trim())))) {
          throw new Error("Invalid progress backup");
        }
      } catch {
        status.textContent = "Could not read this progress file.";
        return;
      }
      try {
        backup.done.forEach(id => storage.setItem(prefix + id, "1"));
        const solutions = new Map(Object.entries(backup.solutions ?? {}));
        for (const {ids} of destinations) {
          const id = ids.find(id => solutions.has(id));
          if (id) saveSolution(ids, solutions.get(id));
        }
        for (const [id, text] of solutions) {
          if (!knownIds.has(id)) saveSolution([id], text);
        }
        status.textContent = "Progress imported.";
      } catch {
        status.textContent = "Browser storage is full. Some progress or solutions may not have been imported.";
      }
      render();
    });

    panel.querySelector("[data-clear]").addEventListener("click", () => {
      if (!window.confirm("Clear all saved progress for GRH via exercises?")) return;
      const solutions = readSolutions();
      const clearSolutions = solutions.size && window.confirm("Also clear all saved solutions?");
      readDone().forEach(id => storage.removeItem(prefix + id));
      if (clearSolutions) {
        for (const id of solutions.keys()) storage.removeItem(solutionPrefix + id);
      }
      status.textContent = clearSolutions ? "Progress and solutions cleared." : "Progress cleared.";
      render();
    });
  }

  window.addEventListener("storage", event => {
    if (event.storageArea !== storage) return;
    if (!event.key || event.key.startsWith(prefix)) render();
    if (!event.key || event.key.startsWith(solutionPrefix)) solutionEditors.forEach(update => update());
  });
  window.addEventListener("pageshow", render);
  window.addEventListener("pageshow", () => solutionEditors.forEach(update => update()));
  render();
})();

// The converter emits problems and section headings as siblings of the title.
(() => {
  "use strict";

  const header = document.querySelector("#title-block-header");
  if (!header || !document.querySelector('meta[name="workbook-chapter"]')) return;

  const modeKey = "grh-workbook:reading-mode";
  const cardKey = "grh-workbook:reading-card:" + location.pathname;
  const positionKey = "grh-workbook:reading-position:" + location.pathname;
  function read(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }
  function save(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      // The reading mode also works without browser storage.
    }
  }

  function recordVisit(problem) {
    const heading = problem?.querySelector(":scope > p:first-of-type > strong:first-child");
    save("grh-workbook:last-visit", JSON.stringify({
      path: location.pathname, id: problem?.id, label: heading?.textContent,
    }));
  }

  if (!document.querySelector("body > div.problem")) {
    recordVisit();
    window.addEventListener("pageshow", () => recordVisit());
    return;
  }

  function make(tag, className, text) {
    const element = document.createElement(tag);
    element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function button(className, text, label) {
    const control = make("button", className, text);
    control.type = "button";
    if (label) control.setAttribute("aria-label", label);
    return control;
  }

  const toggle = button("reading-toggle", "One at a time");
  const position = make("span", "reading-position");
  position.hidden = true;
  const previous = button("reading-step", "‹", "Previous card");
  const next = button("reading-step", "›", "Next card");
  const counter = button("reading-counter");
  counter.setAttribute("aria-expanded", "false");
  const back = button("reading-back");
  back.hidden = true;
  const list = make("ul", "reading-card-list");
  list.id = "reading-card-list";
  list.hidden = true;
  list.setAttribute("aria-label", "Choose a card");
  counter.setAttribute("aria-controls", list.id);
  position.append(previous, counter, next, back);
  (header.querySelector(".date") || header.querySelector(".title")).append(toggle, position);
  header.append(list);

  let deck, cards, hiddenHints, restoreNodes, restoreHints;
  let current = -1;
  let pageTop = 0;
  let savedCard = read(cardKey);
  let returnLabel = null;
  let entryId;
  let entrySequence = 0;
  let saveTimer;
  const positions = new Map();

  function setReturn(label) {
    returnLabel = label;
    back.hidden = !label;
    back.textContent = label ? `← ${label}` : "";
  }

  function closeList(restoreFocus = false) {
    if (list.hidden) return;
    list.hidden = true;
    counter.setAttribute("aria-expanded", "false");
    if (restoreFocus) counter.focus({preventScroll: true});
  }

  function snapshot() {
    const {key, slide} = cards[current];
    return {
      id: entryId, key, top: slide.scrollTop, back: returnLabel,
      open: [...slide.querySelectorAll("details")].map(details => details.open),
    };
  }

  function newEntry() {
    entryId = `${performance.timeOrigin}:${++entrySequence}`;
  }

  function remember(url = location.href, push = false) {
    clearTimeout(saveTimer);
    const state = snapshot();
    positions.set(entryId, state);
    if (push) history.pushState({readingCard: state}, "", url);
    else if (location.href !== new URL(url, location.href).href ||
             JSON.stringify(history.state?.readingCard) !== JSON.stringify(state)) {
      history.replaceState({...history.state, readingCard: state}, "", url);
    }
  }

  function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => remember(), 350);
  }

  function targetFor(hash) {
    if (!hash) return null;
    try {
      return document.getElementById(decodeURIComponent(hash.slice(1)));
    } catch {
      return null;
    }
  }

  function disclosure(label) {
    const details = make("details", "reading-disclosure");
    details.append(make("summary", "reading-summary", label));
    return details;
  }

  function collectHints(elements) {
    // This sheet's older description markup loses the item labels in Pandoc.
    // The Bernoulli list omits pr:simplest, so use the TeX hint order.
    const legacy = location.pathname.endsWith("--the-minus-part-by-gauss-sums__workbook.html") ? {
      "sec:signs": ["split", "parts", "parity", "degree"],
      "sec:bernoulli": ["integral", "hurwitz", "size", "matrix", "eigen", "adjugate", "zcong", "witness"],
      "sec:euler": ["theta", "derivative", "hilbert", "exponent-rank", "sum-e"],
      "sec:examples": ["37", "psi-one", "compare"],
    } : {};
    const hints = new Map();
    for (const element of elements) {
      if (element.matches("dl")) {
        for (const term of element.querySelectorAll(":scope > dt")) {
          const problem = targetFor(term.querySelector('a[href^="#"]')?.hash);
          if (!problem?.matches("div.problem")) continue;
          for (let entry = term.nextElementSibling; entry?.matches("dd"); entry = entry.nextElementSibling) {
            if (!hints.has(problem)) hints.set(problem, []);
            hints.get(problem).push(entry);
          }
        }
      }
      if (element.matches("div.description")) {
        const section = targetFor(element.previousElementSibling?.querySelector('a[href^="#"]')?.hash);
        const problems = legacy[section?.id]?.map(label => document.getElementById("pr:" + label));
        const entries = [...element.children];
        if (problems?.length === entries.length && problems.every(problem => problem?.matches("div.problem"))) {
          problems.forEach((problem, index) => hints.set(problem, [entries[index]]));
        }
      }
    }
    return hints;
  }

  function addHint(content, entries) {
    const hint = disclosure("Hint");
    const body = make("div", "reading-hint");
    hint.append(body);
    content.append(hint);
    for (const entry of entries) {
      if (entry.matches("dd")) {
        const part = document.createElement("div");
        part.append(...entry.childNodes);
        body.append(part);
        restoreHints.push(() => entry.append(...part.childNodes));
      } else {
        const place = document.createComment("");
        entry.replaceWith(place);
        body.append(entry);
        restoreHints.push(() => place.replaceWith(entry));
      }
    }
  }

  function activate(index) {
    if (index === current) return;
    const oldSlide = cards[current]?.slide;
    const focused = oldSlide?.contains(document.activeElement);
    if (oldSlide) oldSlide.inert = true;
    current = index;
    const {slide, key, problem} = cards[current];
    slide.inert = false;
    if (focused) slide.focus({preventScroll: true});
    counter.textContent = `${current + 1} / ${cards.length}`;
    counter.setAttribute("aria-label", `Card ${current + 1} of ${cards.length}. Choose a card`);
    previous.disabled = current === 0;
    next.disabled = current === cards.length - 1;
    savedCard = key;
    save(cardKey, key);
    recordVisit(problem);
  }

  function show(index, target, focus = false) {
    const {slide} = cards[index];
    deck.scrollLeft = index * deck.clientWidth;
    activate(index);
    if (target) {
      for (let node = target; node && node !== slide; node = node.parentElement) {
        if (node.matches("details")) node.open = true;
      }
      slide.scrollTop += target.getBoundingClientRect().top - slide.getBoundingClientRect().top - 16;
    }
    if (focus) slide.focus({preventScroll: true});
  }

  function cardFor(target) {
    return cards.findIndex(({slide}) => slide.contains(target));
  }

  function restorePosition(state, revealHash = true) {
    const index = cards.findIndex(({key}) => key === state?.key);
    setReturn(state?.back ?? null);
    if (index >= 0) {
      entryId = state.id;
      show(index);
      const {slide} = cards[index];
      slide.querySelectorAll("details").forEach((details, i) => { details.open = !!state.open[i]; });
      slide.scrollTop = state.top;
      return;
    }
    newEntry();
    const target = revealHash && targetFor(location.hash);
    const linked = target ? cardFor(target) : -1;
    const remembered = cards.findIndex(({key}) => key === savedCard);
    show(linked >= 0 ? linked : Math.max(0, remembered), linked >= 0 ? target : null);
  }

  function pageTo(index, moveDeck = true) {
    if (!cards[index] || index === current) return;
    closeList();
    setReturn(null);
    if (moveDeck) show(index);
    else activate(index);
    // The current card replaces any fragment left by a link.
    remember(location.pathname + location.search);
  }

  counter.addEventListener("click", () => {
    if (!list.hidden) {
      closeList(true);
      return;
    }
    let lastSection;
    const items = cards.map(({problem, label, section}, index) => {
      const item = document.createElement("li");
      if (section && section !== lastSection) item.append(make("div", "reading-list-section", section));
      lastSection = section;
      const row = button("reading-list-card", label);
      if (problem?.querySelector('.progress-toggle[aria-pressed="true"]')) {
        const check = make("span", "reading-list-done", "✓");
        check.setAttribute("aria-hidden", "true");
        row.append(check);
        row.setAttribute("aria-label", `${label}, done`);
      }
      if (index === current) row.setAttribute("aria-current", "true");
      row.addEventListener("click", () => {
        closeList(true);
        pageTo(index);
      });
      item.append(row);
      return item;
    });
    list.replaceChildren(...items);
    list.hidden = false;
    counter.setAttribute("aria-expanded", "true");
    const active = list.querySelector('[aria-current="true"]');
    active.focus({preventScroll: true});
    active.scrollIntoView({block: "nearest"});
  });

  previous.addEventListener("click", () => pageTo(current - 1));
  next.addEventListener("click", () => pageTo(current + 1));
  back.addEventListener("click", () => {
    remember();
    history.back();
  });
  document.addEventListener("pointerdown", event => {
    if (!position.contains(event.target) && !list.contains(event.target)) closeList();
  });

  function enter(state, revealHash = true) {
    const groups = [];
    const hintNodes = [];
    const nodes = [];
    let group = [], inHints = false;
    // Keep the original sibling order, including whitespace, for the full page.
    for (let node = header.nextSibling; node && !node.matches?.("script"); node = node.nextSibling) {
      nodes.push(node);
      if (node.id === "hints") inHints = true;
      else if (node.matches?.("h1, .footnotes, [role='doc-endnotes']")) inHints = false;

      if (inHints) {
        hintNodes.push(node);
        continue;
      }
      group.push(node);
      if (node.matches?.("div.problem")) {
        groups.push({nodes: group, problem: node});
        group = [];
      }
    }
    if (group.some(node => node.nodeType === Node.ELEMENT_NODE ||
                          (node.nodeType === Node.TEXT_NODE && node.textContent.trim()))) {
      groups.push({nodes: group});
    }

    const hints = collectHints(hintNodes.filter(node => node.nodeType === Node.ELEMENT_NODE));
    restoreNodes = nodes;
    restoreHints = [];
    pageTop = window.scrollY;
    deck = make("main", "reading-deck");
    deck.setAttribute("aria-label", "Sheet cards");
    hiddenHints = document.createElement("div");
    hiddenHints.hidden = true;
    nodes[0].before(deck, hiddenHints);
    hiddenHints.append(...hintNodes);

    let section = "";
    cards = groups.map(({nodes, problem}, index) => {
      const slide = make("div", "reading-card");
      slide.setAttribute("role", "group");
      slide.setAttribute("aria-label", `Card ${index + 1} of ${groups.length}`);
      slide.tabIndex = 0;
      slide.inert = true;
      const content = make("div", "reading-card-content");
      for (const node of nodes) {
        if (node.matches?.("h1, h2, h3, h4, h5, h6")) {
          const heading = node.cloneNode(true);
          heading.querySelector(".stable-tag")?.remove();
          section = heading.textContent.replace(/\\[()]/g, "").trim();
        }
        if (node.id === "TOC") {
          const contents = disclosure("Contents");
          contents.append(node);
          content.append(contents);
        } else {
          content.append(node);
        }
      }
      if (hints.has(problem)) addHint(content, hints.get(problem));
      slide.append(content);
      deck.append(slide);
      const label = problem?.querySelector(":scope > p:first-of-type > strong:first-child")?.textContent.trim();
      return {slide, problem, key: problem ? problem.id || String(index) : "trailing",
        label: label || "End of sheet", section};
    });

    document.body.setAttribute("data-reading-cards", "");
    toggle.textContent = "Full page";
    position.hidden = false;
    deck.addEventListener("scroll", ({currentTarget}) => {
      if (currentTarget !== deck) return;
      const index = Math.round(deck.scrollLeft / deck.clientWidth);
      pageTo(index, false);
    }, {passive: true});
    deck.addEventListener("scroll", event => {
      if (event.currentTarget === deck && event.target === cards[current]?.slide) scheduleSave();
    }, {capture: true, passive: true});
    deck.addEventListener("toggle", event => {
      if (event.currentTarget === deck && cards[current]?.slide.contains(event.target)) scheduleSave();
    }, true);
    restorePosition(state, revealHash);
  }

  function leave() {
    clearTimeout(saveTimer);
    closeList();
    restoreHints.forEach(restore => restore());
    for (const node of restoreNodes) deck.before(node);
    deck.remove();
    hiddenHints.remove();
    deck = cards = hiddenHints = restoreNodes = restoreHints = null;
    current = -1;
    document.body.removeAttribute("data-reading-cards");
    toggle.textContent = "One at a time";
    position.hidden = true;
  }

  toggle.addEventListener("click", () => {
    if (deck) {
      setReturn(null);
      remember();
      leave();
      history.scrollRestoration = "auto";
      save(modeKey, "page");
      recordCurrentVisit();
      const target = targetFor(location.hash);
      if (target) target.scrollIntoView();
      else window.scrollTo(0, pageTop);
    } else {
      save(modeKey, "cards");
      startCards();
    }
  });

  document.addEventListener("click", event => {
    if (!deck || event.defaultPrevented || event.button !== 0 ||
        event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const link = event.target.closest?.("a[href]");
    if (!link?.hash || (link.target && link.target !== "_self") || link.hasAttribute("download") ||
        link.origin !== location.origin || link.pathname !== location.pathname || link.search !== location.search) return;
    const target = targetFor(link.hash);
    const index = target ? cardFor(target) : -1;
    if (index < 0) return;
    event.preventDefault();
    remember();
    closeList();
    setReturn(cards[current].problem ? `Back to ${cards[current].label}` : "Back");
    newEntry();
    show(index, target, true);
    remember(link.hash, true);
  });
  window.addEventListener("popstate", event => {
    if (!deck) return;
    // The outgoing card is still visible here, even if scrolling had not settled.
    positions.set(entryId, snapshot());
    const state = event.state?.readingCard;
    restorePosition(positions.get(state?.id) ?? state);
    history.scrollRestoration = "manual";
    remember();
  });
  window.addEventListener("hashchange", () => {
    if (!deck) recordCurrentVisit();
  });

  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !list.hidden) {
      event.preventDefault();
      closeList(true);
      return;
    }
    if (!deck || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey ||
        event.target.matches?.("input, textarea, select") || event.target.isContentEditable) return;
    const index = {ArrowLeft: current - 1, ArrowRight: current + 1, Home: 0, End: cards.length - 1}[event.key];
    if (index === undefined) return;
    event.preventDefault();
    pageTo(index);
    if (cards[index]) cards[index].slide.focus({preventScroll: true});
  });

  let printState;
  window.addEventListener("beforeprint", () => {
    if (!deck) return;
    printState = {
      position: snapshot(),
      open: [...deck.querySelectorAll("details")].map(details => details.open),
    };
    leave();
  });
  window.addEventListener("afterprint", () => {
    if (!printState) return;
    enter(printState.position, false);
    deck.querySelectorAll("details").forEach((details, index) => { details.open = printState.open[index]; });
    cards[current].slide.scrollTop = printState.position.top;
    printState = null;
  });

  function recordCurrentVisit() {
    const problem = deck ? cards[current]?.problem : targetFor(location.hash)?.closest("div.problem");
    recordVisit(problem);
  }

  function startCards(state = history.state?.readingCard) {
    history.scrollRestoration = "manual";
    enter(state);
    remember();
  }

  if (read(modeKey) === "cards") {
    const state = history.state?.readingCard;
    let lastPosition;
    try {
      lastPosition = JSON.parse(sessionStorage.getItem(positionKey));
      sessionStorage.removeItem(positionKey);
    } catch {
      // History still holds the last saved position.
    }
    startCards(lastPosition?.id && lastPosition.id === state?.id ? lastPosition : state);
  }
  window.addEventListener("pagehide", () => {
    if (!deck) return;
    // A reload can copy history.state before pagehide runs.
    try {
      sessionStorage.setItem(positionKey, JSON.stringify(snapshot()));
    } catch {
      // History still holds the last saved position.
    }
    remember();
  });
  recordCurrentVisit();
  window.addEventListener("pageshow", recordCurrentVisit);
})();
