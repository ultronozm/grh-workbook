(() => {
  "use strict";

  const script = document.currentScript;
  const discussion = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Discussion";
  discussion.append(summary);
  script.after(discussion);

  const origin = "https://giscus.app";
  const sessionKey = "giscus-session";
  const page = new URL(location.href);
  const returnedSession = page.searchParams.get("giscus");
  page.searchParams.delete("giscus");
  page.hash = "";
  let session = "";
  try {
    if (returnedSession) localStorage.setItem(sessionKey, JSON.stringify(returnedSession));
    session = JSON.parse(localStorage.getItem(sessionKey)) || "";
  } catch {
    session = returnedSession || "";
  }
  if (returnedSession) history.replaceState(history.state, "", page);

  let frame;
  function load() {
    const {repo, repoId, category, categoryId, theme, reactionsEnabled, inputPosition, strict, lang} = script.dataset;
    const term = page.pathname.slice(1).replace(/\.\w+$/, "") || "index";
    const params = new URLSearchParams({
      repo, repoId, category, categoryId, theme, reactionsEnabled, inputPosition, strict,
      term, session, origin: page.href, backLink: page.href,
    });
    frame.src = `${origin}/${lang}/widget?${params}`;
  }

  discussion.addEventListener("toggle", () => {
    if (!discussion.open || frame) return;
    frame = document.createElement("iframe");
    frame.title = "Comments";
    frame.allow = "clipboard-write";
    frame.style.cssText = "display:block;width:100%;border:0";
    discussion.append(frame);
    load();
  });
  window.addEventListener("message", event => {
    if (event.origin !== origin || !frame || event.source !== frame.contentWindow) return;
    const message = event.data?.giscus;
    const height = Number(message?.resizeHeight);
    if (height > 0 && Number.isFinite(height)) frame.style.height = `${height}px`;
    if (message?.signOut || (session && /Bad credentials|Invalid state value|State has expired/.test(message?.error))) {
      session = "";
      try { localStorage.removeItem(sessionKey); } catch {}
      load();
    }
  });
  discussion.open = Boolean(returnedSession);
})();
