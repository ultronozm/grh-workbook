import assert from "node:assert/strict";
import {test} from "node:test";
import worker from "../progress-sync.js";

const id = "ab".repeat(32);
const path = "/v1/" + id;
const origin = "https://ultronozm.github.io";
const ttl = 365 * 86400;
const maxBytes = 256 * 1024;

function api() {
  const records = new Map();
  const writes = [];
  const SYNC = {
    async get(key) { return records.get(key) ?? null; },
    async put(key, value, options) {
      writes.push([key, options]);
      records.set(key, value);
    },
    async delete(key) { records.delete(key); },
  };
  const send = (method, {url = path, body, headers = {Origin: origin}} = {}) =>
    worker.fetch(new Request("https://worker.test" + url, {method, headers, body, duplex: "half"}), {SYNC});
  return {send, writes, records};
}

test("PUT and GET refresh expiration; DELETE removes the record", async () => {
  const {send, writes, records} = api();
  assert.equal((await send("GET")).status, 404);
  assert.deepEqual(writes, []);
  assert.equal((await send("PUT", {body: "ciphertext"})).status, 200);
  const response = await send("GET", {url: "/v1/" + id.toUpperCase()});
  assert.deepEqual(await response.json(), {ciphertext: "ciphertext"});
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.deepEqual(writes, [[id, {expirationTtl: ttl}], [id, {expirationTtl: ttl}]]);
  assert.equal((await send("DELETE")).status, 200);
  assert.equal(records.has(id), false);
  assert.equal((await send("GET")).status, 404);
});

test("CORS and preflight accept only the three site origins", async () => {
  const {send} = api();
  for (const allowed of [origin, "http://localhost:8000", "http://[::1]:8000"]) {
    const headers = {Origin: allowed};
    const response = await send("OPTIONS", {headers: {
      ...headers, "Access-Control-Request-Method": "PUT", "Access-Control-Request-Headers": "If-Match",
    }});
    assert.equal(response.status, 204);
    assert.equal(response.headers.get("Access-Control-Allow-Origin"), allowed);
    assert.match(response.headers.get("Access-Control-Allow-Methods"), /GET, PUT, DELETE/);
    assert.match(response.headers.get("Access-Control-Allow-Headers"), /If-Match/);
    assert.equal(response.headers.get("Access-Control-Allow-Credentials"), null);
    const missing = await send("GET", {headers});
    assert.equal(missing.headers.get("Access-Control-Allow-Origin"), allowed);
    assert.equal(missing.headers.get("Vary"), "Origin");
  }
  for (const method of ["OPTIONS", "GET", "PUT", "DELETE"]) {
    const blocked = await send(method, {headers: {Origin: "https://ultronozm.github.io.example"}});
    assert.equal(blocked.status, 403);
    assert.equal(blocked.headers.get("Access-Control-Allow-Origin"), null);
  }
});

test("rejects other paths, methods and bodies above the byte limit", async () => {
  const {send, writes} = api();
  for (const url of ["/", "/v2/" + id, "/V1/" + id, path + "/", path + "a", "/v1/" + "x".repeat(64)]) {
    assert.equal((await send("GET", {url})).status, 404);
  }
  for (const method of ["POST", "PATCH", "HEAD"]) {
    assert.equal((await send(method)).status, 405);
  }
  assert.equal((await send("PUT", {body: "x", headers: {"Content-Length": maxBytes + 1}})).status, 413);
  assert.equal((await send("PUT", {body: ""})).status, 400);
  assert.equal((await send("PUT", {body: new Uint8Array([255])})).status, 400);
  const bytes = new TextEncoder().encode("é".repeat(maxBytes / 2 + 1));
  for (const size of [maxBytes + 1, maxBytes]) {
    const body = new ReadableStream({start(controller) {
      controller.enqueue(bytes.subarray(0, 3));
      controller.enqueue(bytes.subarray(3, size));
      controller.close();
    }});
    assert.equal((await send("PUT", {body})).status, size > maxBytes ? 413 : 200);
  }
  assert.equal(writes.length, 1);
});

test("conditional writes avoid overwriting a changed or deleted record", async () => {
  const {send} = api();
  const create = {body: "ciphertext", headers: {Origin: origin, "If-None-Match": "*"}};
  assert.equal((await send("PUT", create)).status, 200);
  assert.equal((await send("PUT", create)).status, 412);
  const previous = (await send("GET")).headers.get("ETag");
  assert.ok(previous);
  const update = {body: "new ciphertext", headers: {Origin: origin, "If-Match": previous}};
  assert.equal((await send("PUT", update)).status, 200);
  assert.equal((await send("PUT", update)).status, 412);
  await send("DELETE");
  assert.equal((await send("PUT", update)).status, 412);
  assert.equal((await send("GET")).status, 404);
});
