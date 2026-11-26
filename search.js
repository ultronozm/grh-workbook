(() => {
  "use strict";

  const heading = document.querySelector("#content > h1.title");
  if (!heading) return;

  const search = document.createElement("div");
  search.className = "workbook-search";
  search.setAttribute("role", "search");
  search.innerHTML = `
    <input type="search" aria-label="Search the workbook" placeholder="Search the workbook…" autocomplete="off">
    <p role="status"></p>
    <ol class="tex2jax_ignore"></ol>`;
  (document.querySelector(".reading-continue") || heading).after(search);

  const input = search.querySelector("input");
  const status = search.querySelector("[role=status]");
  const results = search.querySelector("ol");
  const normalize = text => text.toLowerCase().normalize("NFC");
  const searchable = text => normalize(text.replace(/\\(?:\\|[a-zA-Z]+|[()[\]])/g,
    match => " ".repeat(match.length)));
  const phraseText = text => text.replace(/\s+/g, " ");
  let index;
  let timer;
  let revision = 0;

  function load() {
    index ??= fetch("workbook-search.json")
      .then(response => {
        if (!response.ok) throw new Error("Search index unavailable");
        return response.json();
      })
      .then(data => {
        const {rows = data, macros = {}} = data;
        return rows.map(([chapter, url, label, body]) => {
          const sheet = url.split("#", 1)[0];
          const text = searchable(body);
          return {chapter, url, label, body, sheet, macros: macros[sheet], text,
            title: phraseText(searchable(`chapter ${chapter} ${label}`)),
            phrase: phraseText(text)};
        });
      })
      .catch(error => {
        index = undefined;
        throw error;
      });
    return index;
  }

  function snippet(row, tokens) {
    if (!row.body) return "";
    const hit = row.text.indexOf(tokens.find(token => row.text.includes(token)) || "");
    let start = Math.max(0, hit - 38);
    let end = Math.min(row.body.length, start + 150);
    let opening;
    let close;
    for (const delimiter of row.body.matchAll(/\\(?:\\|[()[\]])/g)) {
      const [mark] = delimiter;
      if (mark === "\\\\") continue;
      const offset = delimiter.index;
      const after = offset + mark.length;
      if (opening === undefined && (mark === "\\(" || mark === "\\[")) {
        opening = offset;
        close = mark === "\\(" ? "\\)" : "\\]";
      } else if (mark === close) {
        if (opening < start && start < after) start = after;
        if (opening < end && end < after) end = opening;
        opening = close = undefined;
      } else if (opening === undefined && offset < end) {
        // Discard the prefix of a span whose opening delimiter is missing.
        start = Math.max(start, after);
      }
    }
    if (opening !== undefined) end = Math.min(end, opening);
    const excerpt = row.body.slice(start, end).trim();
    if (!excerpt) return "";
    return (start ? "…" : "") + excerpt + (end < row.body.length ? "…" : "");
  }

  async function typeset(groups, current) {
    const mj = window.MathJax;
    try {
      await mj?.startup?.promise;
      if (current !== revision || !mj?.startup?.document) return;
      const main = mj.startup.document;
      const math = mj._.mathjax.mathjax;
      // A separate TeX input per sheet keeps its macros and labels local.
      for (const {macros, elements} of groups.values()) {
        if (current !== revision) return;
        const input = new main.inputJax[0].constructor({
          ...mj.config.tex, tags: "none", macros: {...mj.config.tex?.macros, ...macros},
        });
        const page = math.document(document, {InputJax: input, OutputJax: main.outputJax});
        await math.handleRetriesFor(() => {
          if (current === revision) page.findMath({elements}).render();
        });
      }
    } catch (error) {
      console.warn("Could not typeset search results", error);
    }
  }

  async function update(current) {
    const query = normalize(input.value.trim());
    let rows;
    try {
      rows = await load();
    } catch {
      if (current === revision) status.textContent = "Search is unavailable.";
      return;
    }
    if (current !== revision) return;

    const tokens = query.split(/\s+/);
    const phraseQuery = phraseText(query);
    const matches = [];
    for (const row of rows) {
      const scores = tokens.map(token => row.title.includes(token) ? 4 : Number(row.text.includes(token)));
      if (scores.some(score => score === 0)) continue;
      const phrase = row.title.includes(phraseQuery) ? 12 : row.phrase.includes(phraseQuery) ? 3 : 0;
      matches.push({row, score: phrase + scores.reduce((sum, score) => sum + score, 0)});
    }
    matches.sort((a, b) => b.score - a.score);
    status.textContent = matches.length
      ? `Showing ${Math.min(matches.length, 7)} of ${matches.length} results`
      : "No results.";
    const groups = new Map();
    const items = matches.slice(0, 7).map(({row}) => {
      const item = document.createElement("li");
      const link = document.createElement("a");
      const excerpt = document.createElement("span");
      link.href = row.url;
      link.textContent = `Chapter ${row.chapter} · ${row.label}`;
      excerpt.textContent = snippet(row, tokens);
      item.append(link, excerpt);
      if (/\\[([]/.test(item.textContent)) {
        if (!groups.has(row.sheet)) groups.set(row.sheet, {macros: row.macros, elements: []});
        groups.get(row.sheet).elements.push(item);
      }
      return item;
    });
    results.replaceChildren(...items);
    if (groups.size) await typeset(groups, current);
  }

  function scheduleUpdate() {
    const current = ++revision;
    clearTimeout(timer);
    results.replaceChildren();
    status.textContent = "";
    if (input.value.trim()) timer = setTimeout(() => update(current), 150);
  }

  input.addEventListener("input", scheduleUpdate);
  search.addEventListener("keydown", event => {
    const links = [...results.querySelectorAll("a")];
    const selected = links.indexOf(document.activeElement);
    if (event.key === "Escape") {
      event.preventDefault();
      input.value = "";
      scheduleUpdate();
      input.focus();
    } else if (links.length && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      event.preventDefault();
      const next = selected + (event.key === "ArrowDown" ? 1 : -1);
      (links[next] || input).focus();
    } else if (event.key === "Enter" && event.target === input && links.length) {
      event.preventDefault();
      links[0].click();
    }
  });
})();
