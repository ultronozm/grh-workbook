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

  const template = document.querySelector("#workbook-progress");
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
