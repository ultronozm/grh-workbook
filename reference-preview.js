(() => {
  "use strict";

  const hover = matchMedia("(hover: hover) and (pointer: fine)");
  const blocks = "div:is(.definition,.theorem,.proposition,.lemma,.problem,.remark)";
  const headings = "h1,h2,h3,h4,h5,h6";
  const entries = ".thebibliography > p, .csl-entry, [role='doc-biblioentry']";
  const footnotes = ".footnotes > ol > li, [role='doc-endnote'], [role='doc-footnote']";
  const pages = new Map();
  const previews = new Map();
  let active;
  let closeTimer;
  let rendering = Promise.resolve();

  function destination(link) {
    if (!link || link.closest(".reference-preview") ||
        (!link.hash && !link.closest(".used-in")) ||
        link.origin !== location.origin || link.hasAttribute("download")) return null;
    const page = new URL(link.href);
    const local = page.pathname === location.pathname && page.search === location.search;
    if (!local && (!/^https?:$/.test(page.protocol) || !/\.html$/i.test(page.pathname))) return null;
    let id;
    try {
      id = decodeURIComponent(page.hash.slice(1));
    } catch {
      return null;
    }
    page.hash = "";
    return {page: page.href, id, local};
  }

  function fetchPage(url) {
    if (!pages.has(url)) {
      pages.set(url, (async () => {
        const key = "grh-workbook:reference-page:" + url;
        let html;
        try {
          html = sessionStorage.getItem(key);
        } catch {
          // The in-memory cache also works when storage is unavailable.
        }
        if (html == null) {
          const response = await fetch(url, {mode: "same-origin"});
          if (!response.ok) return null;
          html = await response.text();
          try {
            sessionStorage.setItem(key, html);
          } catch {
            // Keep the parsed page in memory if the tab's storage is full.
          }
        }
        return new DOMParser().parseFromString(html, "text/html");
      })().catch(() => null));
    }
    return pages.get(url);
  }

  function makeCard() {
    const card = document.createElement("div");
    card.className = "reference-preview";
    return card;
  }

  function stripIds(root) {
    root.removeAttribute("id");
    root.querySelectorAll("[id]").forEach(node => node.removeAttribute("id"));
  }

  function copyTarget(source, ref) {
    const chapterLink = !ref.id && source.querySelector('meta[name="workbook-chapter"]');
    let target = chapterLink ? source.querySelector("#title-block-header") : source.getElementById(ref.id);
    const entry = target?.closest(entries + ", " + footnotes);
    if (entry) target = entry;
    // A display with several labels has empty anchors immediately before it.
    while (target?.matches("span[id]:empty:not([data-label])")) {
      target = target.nextElementSibling;
    }
    if (!target) return null;
    const section = target.matches(headings) && /^§\s*\w/.test(target.textContent);
    const block = target.matches(blocks);
    const equation = target.matches(".math.display");
    if (!chapterLink && !section && !block && !equation && !entry) return null;

    const content = document.createElement("div");
    content.className = "reference-preview-content";
    if (equation) content.classList.add("reference-preview-equation");
    if (!chapterLink) {
      const copy = target.cloneNode(true);
      if (block) copy.classList.add("reference-preview-block");
      if (section) copy.classList.add("reference-preview-heading");
      if (entry) {
        copy.classList.add("reference-preview-entry");
        copy.querySelectorAll(".footnote-back, [role='doc-backlink']").forEach(node => node.remove());
      }
      content.append(copy);
    }
    if (section || chapterLink) {
      for (let node = target.nextElementSibling; node && !node.matches(headings);
           node = node.nextElementSibling) {
        if (node.matches("p")) {
          content.append(node.cloneNode(true));
          break;
        }
      }
    }
    stripIds(content);
    content.querySelectorAll(".progress-toggle, .problem-solution, .stable-tag, .used-in")
      .forEach(node => node.remove());
    content.querySelectorAll("a[href]").forEach(link => {
      link.href = new URL(link.getAttribute("href"), ref.page).href;
    });
    content.querySelectorAll("img[src]").forEach(image => {
      image.src = new URL(image.getAttribute("src"), ref.page).href;
    });
    if (!ref.local || chapterLink) {
      const chapter = source.querySelector('meta[name="workbook-chapter"]')?.content;
      const context = document.createElement("div");
      context.className = "reference-preview-context";
      context.textContent = chapter ? `Chapter ${chapter}, ${source.title}` : source.title;
      content.prepend(context);
    }
    return content;
  }

  function sheetMacros(source) {
    // The converter writes a JSON object inside this assignment.
    for (const script of source.head.querySelectorAll("script:not([src])")) {
      const match = /^window\.MathJax = \{tex: \{macros: (\{.*\})\}\};$/s.exec(script.textContent.trim());
      if (match) return JSON.parse(match[1]);
    }
    return {};
  }

  async function typeset(content, source) {
    if (![...content.querySelectorAll(".math")].some(node => !node.querySelector("mjx-container"))) return;
    const mj = window.MathJax;
    if (!mj?.typesetPromise) throw new Error("MathJax is unavailable");
    const staging = makeCard();
    staging.classList.add("reference-preview-staging");
    staging.append(content);
    document.body.append(staging);
    try {
      if (source === document) {
        await mj.typesetPromise([content]);
        mj.typesetClear([content]);
        stripIds(content);
      } else {
        // Share the site's CommonHTML output and fonts, with this sheet's TeX macros
        // and its own equation labels. The main page's TeX state stays intact.
        const main = mj.startup.document;
        const input = new main.inputJax[0].constructor({...mj.config.tex, macros: sheetMacros(source)});
        const math = mj._.mathjax.mathjax;
        const preview = math.document(document, {
          InputJax: input,
          OutputJax: main.outputJax,
          elements: [content],
        });
        await math.handleRetriesFor(() => {
          preview.render();
          stripIds(content);
        });
      }
    } finally {
      staging.remove();
    }
  }

  async function previewFor(ref) {
    await window.MathJax?.startup?.promise;
    if (ref.local) {
      const content = copyTarget(document, ref);
      if (content) await queueTypeset(content, document);
      return content;
    }
    const key = JSON.stringify([ref.page, ref.id]);
    if (!previews.has(key)) {
      previews.set(key, (async () => {
        const source = await fetchPage(ref.page);
        const content = source && copyTarget(source, ref);
        if (content) await queueTypeset(content, source);
        return content;
      })());
    }
    return (await previews.get(key))?.cloneNode(true);
  }

  function queueTypeset(content, source) {
    const next = rendering.then(() => typeset(content, source));
    rendering = next.catch(() => {});
    return next;
  }

  function dismiss() {
    clearTimeout(closeTimer);
    if (!active) return;
    clearTimeout(active.openTimer);
    active.card?.remove();
    active = null;
  }

  function place() {
    if (!active?.card) return;
    const {link, card} = active;
    const anchor = link.getBoundingClientRect();
    const {clientWidth: width, clientHeight: height} = document.documentElement;
    if (!anchor.width || anchor.bottom <= 0 || anchor.top >= height ||
        anchor.right <= 0 || anchor.left >= width) {
      dismiss();
      return;
    }
    const inset = 8;
    const gap = 6;
    const below = height - anchor.bottom - inset - gap;
    const above = anchor.top - inset - gap;
    const desiredHeight = Math.min(card.scrollHeight + 2, height * 0.6);
    const flip = below < desiredHeight && above > below;
    card.style.maxHeight = `${Math.min(height * 0.6, flip ? above : below)}px`;
    const preferredLeft = anchor.left + (anchor.width - card.offsetWidth) / 2;
    const left = Math.min(Math.max(inset, preferredLeft), width - card.offsetWidth - inset);
    card.style.left = `${left}px`;
    card.style.top = `${flip ? anchor.top - gap - card.offsetHeight : anchor.bottom + gap}px`;
  }

  function activate(link, keyboard) {
    if (active && active.link === link) {
      clearTimeout(closeTimer);
      active.keyboard ||= keyboard;
      return;
    }
    const ref = destination(link);
    if (!ref) return;
    dismiss();
    const opening = {link, keyboard};
    active = opening;
    opening.openTimer = setTimeout(async () => {
      try {
        const content = await previewFor(ref);
        if (!content || active !== opening) return;
        const card = makeCard();
        card.append(content);
        document.body.append(card);
        opening.card = card;
        place();
      } catch {
        if (active === opening) dismiss();
      }
    }, 300);
  }

  function inside(node) {
    return active && (active.link.contains(node) || active.card?.contains(node));
  }

  document.addEventListener("pointerover", event => {
    if (!hover.matches || event.pointerType === "touch") return;
    if (inside(event.target)) clearTimeout(closeTimer);
    else activate(event.target.closest?.("a[href]"), false);
  });
  document.addEventListener("pointerout", event => {
    if (event.pointerType === "touch" || !inside(event.target) || inside(event.relatedTarget) ||
        active.keyboard) return;
    clearTimeout(closeTimer);
    closeTimer = setTimeout(dismiss, active.card ? 180 : 0);
  });
  document.addEventListener("focusin", event => {
    if (hover.matches && event.target.matches?.("a[href]:focus-visible")) {
      activate(event.target, true);
    }
  });
  document.addEventListener("focusout", event => {
    if (active?.keyboard && inside(event.target) && !inside(event.relatedTarget)) dismiss();
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && active) dismiss();
  });
  document.addEventListener("click", event => {
    if (!active?.card?.contains(event.target) || event.target.closest?.("a[href]")) dismiss();
  });
  window.addEventListener("scroll", event => {
    if (event.target === window || !active?.card?.contains(event.target)) place();
  }, {capture: true, passive: true});
  window.addEventListener("resize", place);
  window.addEventListener("popstate", dismiss);
  window.addEventListener("pagehide", dismiss);
  window.addEventListener("beforeprint", dismiss);
  hover.addEventListener("change", dismiss);
})();
