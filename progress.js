(() => {
  "use strict";

  const prefix = "grh-workbook:done:";
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
      count.textContent = onIndex ? `${done}/${total}` : `${done} of ${total}`;
      count.classList.toggle("progress-complete", onIndex && done === total);
    });
  }

  const problems = [];
  for (const problem of document.querySelectorAll("[data-progress-ids]")) {
    const ids = JSON.parse(problem.dataset.progressIds);
    const heading = problem.querySelector(":scope > p:first-of-type > strong:first-child");
    if (!heading) continue;
    problems.push(ids);

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
    document.body.append(panel);

    panel.querySelector("[data-export]").addEventListener("click", () => {
      const contents = JSON.stringify({version: 1, done: [...readDone()].sort()}, null, 2);
      const url = URL.createObjectURL(new Blob([contents + "\n"], {type: "application/json"}));
      const link = document.createElement("a");
      link.href = url;
      link.download = "grh-workbook-progress.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });

    panel.querySelector("[data-import]").addEventListener("click", () => file.click());
    file.addEventListener("change", async () => {
      const selected = file.files[0];
      if (!selected) return;
      file.value = "";
      let backup;
      try {
        backup = JSON.parse(await selected.text());
        if (backup?.version !== 1 || !Array.isArray(backup.done) ||
            !backup.done.every(id => typeof id === "string" && id.length > 0)) {
          throw new Error("Invalid progress backup");
        }
      } catch {
        status.textContent = "Could not read this progress file.";
        return;
      }
      try {
        backup.done.forEach(id => storage.setItem(prefix + id, "1"));
        status.textContent = "Progress imported.";
      } catch {
        status.textContent = "Browser storage is full. Some marks may not have been imported.";
      }
      render();
    });

    panel.querySelector("[data-clear]").addEventListener("click", () => {
      if (!window.confirm("Clear all saved progress for GRH via exercises?")) return;
      readDone().forEach(id => storage.removeItem(prefix + id));
      status.textContent = "Progress cleared.";
      render();
    });
  }

  window.addEventListener("storage", event => {
    if (event.storageArea === storage && (!event.key || event.key.startsWith(prefix))) render();
  });
  window.addEventListener("pageshow", render);
  render();
})();

// The converter emits problems and section headings as siblings of the title.
(() => {
  "use strict";

  const header = document.querySelector("#title-block-header");
  if (!header || !document.querySelector('meta[name="workbook-chapter"]')) return;

  const modeKey = "grh-workbook:reading-mode";
  const cardKey = "grh-workbook:reading-card:" + location.pathname;
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

  const toggle = make("button", "reading-toggle", "One at a time");
  toggle.type = "button";
  const position = make("span", "reading-position");
  position.setAttribute("role", "status");
  position.hidden = true;
  (header.querySelector(".date") || header.querySelector(".title")).append(toggle, position);

  let deck, cards, hiddenHints, restoreNodes, restoreHints;
  let current = -1;
  let pageTop = 0;
  let savedCard = read(cardKey);

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
    const previous = cards[current]?.slide;
    const focused = previous?.contains(document.activeElement);
    if (previous) previous.inert = true;
    current = index;
    const {slide, key, problem} = cards[current];
    slide.inert = false;
    if (focused) slide.focus({preventScroll: true});
    position.textContent = `${current + 1} / ${cards.length}`;
    savedCard = key;
    save(cardKey, key);
    recordVisit(problem);

    // A fragment takes precedence on reload until the reader pages away.
    const hashCard = targetFor(location.hash)?.closest(".reading-card");
    if (hashCard && hashCard !== slide) history.replaceState(history.state, "", location.pathname + location.search);
  }

  function show(index, target, focus = false) {
    const {slide} = cards[index];
    deck.scrollLeft = index * deck.clientWidth;
    activate(index);
    if (target) {
      const details = target.closest("details");
      if (details) details.open = true;
      slide.scrollTop += target.getBoundingClientRect().top - slide.getBoundingClientRect().top - 16;
    }
    if (focus) slide.focus({preventScroll: true});
  }

  function reveal(target, focus = false) {
    const index = cards.findIndex(({slide}) => slide.contains(target));
    if (index < 0) return;
    show(index, target, focus);
  }

  function enter(revealHash = true) {
    const groups = [];
    const hintNodes = [];
    const nodes = [];
    let group = [], inHints = false;
    // Keep the original sibling order, including whitespace, for the full page.
    for (let node = header.nextSibling; node && !node.matches?.("script"); node = node.nextSibling) {
      nodes.push(node);
      if (node.id === "hints") inHints = true;
      else if (node.matches?.("h1")) inHints = false;

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

    cards = groups.map(({nodes, problem}, index) => {
      const slide = make("div", "reading-card");
      slide.setAttribute("role", "group");
      slide.setAttribute("aria-label", `Card ${index + 1} of ${groups.length}`);
      slide.tabIndex = 0;
      slide.inert = true;
      const content = make("div", "reading-card-content");
      for (const node of nodes) {
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
      return {slide, problem, key: problem ? problem.id || String(index) : "trailing"};
    });

    document.body.setAttribute("data-reading-cards", "");
    toggle.textContent = "Full page";
    position.hidden = false;
    deck.addEventListener("scroll", ({currentTarget}) => {
      if (currentTarget !== deck) return;
      const index = Math.round(deck.scrollLeft / deck.clientWidth);
      if (cards[index]) activate(index);
    }, {passive: true});
    const target = revealHash && targetFor(location.hash);
    const linked = target ? cards.findIndex(({slide}) => slide.contains(target)) : -1;
    const remembered = cards.findIndex(({key}) => key === savedCard);
    show(linked >= 0 ? linked : Math.max(0, remembered), linked >= 0 ? target : null);
  }

  function leave() {
    restoreHints.forEach(restore => restore());
    for (const node of restoreNodes) deck.before(node);
    deck.remove();
    hiddenHints.remove();
    deck = cards = hiddenHints = restoreNodes = restoreHints = null;
    current = -1;
    document.body.removeAttribute("data-reading-cards");
    toggle.textContent = "One at a time";
    position.hidden = true;
    position.textContent = "";
  }

  toggle.addEventListener("click", () => {
    if (deck) {
      leave();
      save(modeKey, "page");
      recordCurrentVisit();
      const target = targetFor(location.hash);
      if (target) target.scrollIntoView();
      else window.scrollTo(0, pageTop);
    } else {
      save(modeKey, "cards");
      enter();
    }
  });

  document.addEventListener("click", event => {
    if (!deck || event.defaultPrevented || event.button !== 0 ||
        event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const link = event.target.closest?.("a[href]");
    if (!link?.hash || (link.target && link.target !== "_self") || link.hasAttribute("download") ||
        link.origin !== location.origin || link.pathname !== location.pathname || link.search !== location.search) return;
    const target = targetFor(link.hash);
    if (!target?.closest(".reading-card")) return;
    event.preventDefault();
    if (link.hash !== location.hash) history.pushState(null, "", link.hash);
    reveal(target, true);
  });
  window.addEventListener("hashchange", () => {
    if (deck) reveal(targetFor(location.hash));
    else recordCurrentVisit();
  });

  document.addEventListener("keydown", event => {
    if (!deck || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey ||
        event.target.matches?.("input, textarea, select") || event.target.isContentEditable) return;
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const next = current + (event.key === "ArrowRight" ? 1 : -1);
    if (cards[next]) show(next, null, true);
  });

  let printState;
  window.addEventListener("beforeprint", () => {
    if (!deck) return;
    printState = {
      top: cards[current].slide.scrollTop,
      open: [...deck.querySelectorAll("details")].map(details => details.open),
    };
    leave();
  });
  window.addEventListener("afterprint", () => {
    if (!printState) return;
    enter(false);
    deck.querySelectorAll("details").forEach((details, index) => { details.open = printState.open[index]; });
    cards[current].slide.scrollTop = printState.top;
    printState = null;
  });

  function recordCurrentVisit() {
    const problem = deck ? cards[current]?.problem : targetFor(location.hash)?.closest("div.problem");
    recordVisit(problem);
  }

  if (read(modeKey) === "cards") enter();
  recordCurrentVisit();
  window.addEventListener("pageshow", recordCurrentVisit);
})();
