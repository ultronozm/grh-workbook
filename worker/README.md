# Deploy progress sync

1. Sign in to the Cloudflare dashboard and select your account. Open **Workers KV** under **Storage & databases**, choose **Create instance**, name it `grh-progress`, and choose **Create**. [Cloudflare KV setup](https://developers.cloudflare.com/kv/get-started/)
2. Open **Workers & Pages**, choose **Create application**, then **Start with Hello World! → Get started**. Name the Worker `grh-progress-sync` and choose **Deploy**. [Cloudflare Worker setup](https://developers.cloudflare.com/kv/get-started/)
3. Open the Worker. Under **Settings → Observability**, disable Workers Logs and any enabled tracing or log export before sending sync traffic. New Workers can have logging enabled by default, and invocation logs include the request URL. [Cloudflare Workers Logs](https://developers.cloudflare.com/workers/observability/logs/workers-logs/)
4. Choose **Edit code**, replace the entire starter script with [progress-sync.js](progress-sync.js) from this directory, and choose **Deploy**.
5. In the Worker's **Settings → Bindings**, choose **Add → KV Namespace**, enter `SYNC` for the variable name, select the `grh-progress` namespace, and choose **Deploy**. [Cloudflare dashboard binding steps](https://developers.cloudflare.com/kv/concepts/kv-namespaces/#bind-your-kv-namespace-via-the-dashboard)
6. In **Settings → Domains & Routes**, confirm that the `workers.dev` route is enabled and copy its URL. Use the full origin, such as `https://grh-progress-sync.YOUR-SUBDOMAIN.workers.dev`, as the value of `SYNC_ENDPOINT` in the repository's [progress.js](../progress.js). Publish the site through its normal GitHub Pages build. On the index, open **Your progress… → Sync across devices** and try creating, joining and deleting a test code. [Cloudflare workers.dev routes](https://developers.cloudflare.com/workers/configuration/routing/workers-dev/)

## Storage behavior

A successful GET or PUT refreshes the 365-day expiry. KV permits one write per key per second and propagates changes across regions asynchronously. Expect a delay across regions when joining a new code or after deletion. The browser merges timestamped records before uploading. Conditional requests reduce conflicting writes. KV's asynchronous replication and lack of atomic updates mean a concurrent expiry refresh can race with deletion. An already connected client that receives a missing record leaves its local copy intact and does not recreate the cloud copy.

The 256 KiB limit applies to the encrypted, base64-encoded snapshot. The site still saves locally if a snapshot grows beyond that limit. Sync codes use six independently sampled words from the [BIP-39 English word list](https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt). The workbook uses its own key derivation and ciphertext format.

## Tests

With Node 26 and the site built into `_site`, run:

```sh
node --test worker/tests/api.test.mjs
node --test worker/tests/browser.test.mjs
```

The browser test uses installed Chrome with two temporary profiles. It serves the site on IPv6 port 8000, runs the Worker with in-memory KV on a separate ephemeral port and supplies that endpoint only in the script response. Set `CHROME_BIN` if Chrome is installed elsewhere, `SYNC_SITE_DIR` for a different preview directory, or `SYNC_SCREEN_DIR` to retain PNG captures.
