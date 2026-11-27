const origins = new Set([
  "https://ultronozm.github.io",
  "http://localhost:8000",
  "http://[::1]:8000",
]);
const methods = "GET, PUT, DELETE, OPTIONS";
const maxBytes = 256 * 1024;
const expirationTtl = 365 * 24 * 60 * 60;

async function readBody(request) {
  if (Number(request.headers.get("Content-Length")) > maxBytes) return null;
  if (!request.body) return "";
  const reader = request.body.getReader();
  const decoder = new TextDecoder("utf-8", {fatal: true, ignoreBOM: true});
  let size = 0;
  let body = "";
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) return body + decoder.decode();
      size += value.byteLength;
      if (size > maxBytes) {
        await reader.cancel();
        return null;
      }
      body += decoder.decode(value, {stream: true});
    }
  } finally {
    reader.releaseLock();
  }
}

async function tag(body) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(body));
  return '"' + Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("") + '"';
}

async function fetch(request, {SYNC}) {
  const origin = request.headers.get("Origin");
  const headers = new Headers({"Cache-Control": "no-store", "Vary": "Origin"});
  const json = (body, status = 200) => Response.json(body, {status, headers});
  if (origin !== null && !origins.has(origin)) return json({error: "Origin not allowed"}, 403);
  if (origin) headers.set("Access-Control-Allow-Origin", origin);
  headers.set("Access-Control-Expose-Headers", "ETag");

  const path = new URL(request.url).pathname;
  const id = /^\/v1\/([A-Fa-f0-9]{64})$/.exec(path)?.[1]?.toLowerCase();
  if (!id) return json({error: "Not found"}, 404);

  const method = request.method;
  if (method === "OPTIONS") {
    headers.set("Access-Control-Allow-Methods", methods);
    headers.set("Access-Control-Allow-Headers", "Content-Type, If-Match, If-None-Match");
    return new Response(null, {status: 204, headers});
  }
  if (!["GET", "PUT", "DELETE"].includes(method)) {
    headers.set("Allow", methods);
    return json({error: "Method not allowed"}, 405);
  }

  let body;
  if (method === "PUT") {
    try {
      body = await readBody(request);
    } catch {
      return json({error: "Invalid body"}, 400);
    }
    if (body === null) return json({error: "Body too large"}, 413);
    if (!body) return json({error: "Empty body"}, 400);
  }

  try {
    if (method === "DELETE") {
      await SYNC.delete(id);
      return json({ok: true});
    }
    if (method === "GET") {
      const ciphertext = await SYNC.get(id);
      if (ciphertext === null) return json({error: "Not found"}, 404);
      headers.set("ETag", await tag(ciphertext));
      await SYNC.put(id, ciphertext, {expirationTtl});
      return json({ciphertext});
    }

    const match = request.headers.get("If-Match");
    const create = request.headers.get("If-None-Match") === "*";
    if (match || create) {
      const current = await SYNC.get(id);
      if ((create && current !== null) ||
          (match && (current === null || match !== await tag(current)))) {
        return json({error: "Synced data changed"}, 412);
      }
    }
    await SYNC.put(id, body, {expirationTtl});
    return json({ok: true});
  } catch {
    return json({error: "Sync temporarily unavailable"}, 503);
  }
}

export default {fetch};
