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
    <ol></ol>`;
  heading.after(search);

  const input = search.querySelector("input");
  const status = search.querySelector("[role=status]");
  const results = search.querySelector("ol");
  const normalize = text => text.toLowerCase().normalize("NFC");
  let index;

  function load() {
    index ??= fetch("workbook-search.json")
      .then(response => {
        if (!response.ok) throw new Error("Search index unavailable");
        return response.json();
      })
      .then(rows => rows.map(([chapter, url, label, body]) => ({
        chapter, url, label, body, title: normalize(`chapter ${chapter} ${label}`),
        text: normalize(body),
      })))
      .catch(error => {
        index = undefined;
        throw error;
      });
    return index;
  }

  function snippet(row, tokens) {
    if (!row.body) return "";
    const hit = row.text.indexOf(tokens.find(token => row.text.includes(token)) || "");
    const start = Math.max(0, hit - 38);
    const end = start + 150;
    return (start ? "…" : "") + row.body.slice(start, end).trim() + (end < row.body.length ? "…" : "");
  }

  async function update() {
    const query = normalize(input.value.trim());
    results.replaceChildren();
    status.textContent = "";
    if (!query) return;
    let rows;
    try {
      rows = await load();
    } catch {
      if (normalize(input.value.trim()) === query) status.textContent = "Search is unavailable.";
      return;
    }
    if (normalize(input.value.trim()) !== query) return;

    const tokens = query.split(/\s+/);
    const matches = [];
    for (const row of rows) {
      const scores = tokens.map(token => row.title.includes(token) ? 4 : Number(row.text.includes(token)));
      if (scores.some(score => score === 0)) continue;
      const phrase = row.title.includes(query) ? 12 : row.text.includes(query) ? 3 : 0;
      matches.push({row, score: phrase + scores.reduce((sum, score) => sum + score, 0)});
    }
    matches.sort((a, b) => b.score - a.score);
    status.textContent = matches.length
      ? `Showing ${Math.min(matches.length, 7)} of ${matches.length} results`
      : "No results.";
    const items = matches.slice(0, 7).map(({row}) => {
      const item = document.createElement("li");
      const link = document.createElement("a");
      const excerpt = document.createElement("span");
      link.href = row.url;
      link.textContent = `Chapter ${row.chapter} · ${row.label}`;
      excerpt.textContent = snippet(row, tokens);
      item.append(link, excerpt);
      return item;
    });
    results.replaceChildren(...items);
  }

  input.addEventListener("input", update);
  search.addEventListener("keydown", event => {
    const links = [...results.querySelectorAll("a")];
    const selected = links.indexOf(document.activeElement);
    if (event.key === "Escape") {
      event.preventDefault();
      input.value = "";
      update();
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
