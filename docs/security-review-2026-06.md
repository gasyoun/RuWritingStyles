_Created: 24-08-2026 · Last updated: 05-09-2026_

# Security Review — 2026-06

Scope: the public-facing surface and anything an outside caller could reach — the
FastAPI app (`src/ruwritingstyles/api.py`), subprocess use, outbound HTTP (SSRF),
secret handling, SQL, deserialization, and path handling. Companion to
[architecture-review-2026-06.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/architecture-review-2026-06.md) and
[data-schema-review-2026-06.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/data-schema-review-2026-06.md).

Method: three parallel read-only security sweeps (web surface / subprocess+SSRF+secrets
/ injection+deserialization+deps), then **direct verification of every CRITICAL claim**
against git state and the actual code. Two of the agents' top alarms did not survive
verification — see "Corrections" below. Do not act on the raw sweep output; act on this.

## Threat model — read this first

This is, today, a **single-user localhost developer tool**, and it is honest about that
in places (the Vite/API orchestration in `rws web`, the `.env`-driven keys). But
`src/ruwritingstyles/api.py` ends with `uvicorn.run(app, host="0.0.0.0", port=8000)` and
ships **no authentication**. So the operative question — exactly the one you asked — is:
*what happens the moment this binds a routable interface?* The answer is that several
by-design "it's just local" behaviours become real holes. Nothing here is a backdoor or a
committed secret; it is a local tool that must not be exposed as-is.

**Verdict: safe as a loopback single-user tool; NOT safe to bind publicly without the
P0/P1 fixes below.** The single highest-leverage change is one line: default the bind host
to `127.0.0.1`.

## Corrections to the raw sweep (verified)

- **"Live API keys committed to a public repo" — FALSE.** `git ls-files .env` is empty and
  `git log --all -- .env` is empty: `.env` is gitignored ([.gitignore:8](.gitignore)) and
  **was never committed**. The agent read the *local working-copy* `.env`, which correctly
  holds real keys for local use, and wrongly inferred public exposure. No public leak; no
  forced key rotation. (One real side effect: the subagent **printed the key values into
  this session transcript** — if you ever share this transcript, rotate them then, not now.)
- **"`GET /runs/{run_id}` path traversal" — already mitigated.** [`_run_dir`](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/api.py)
  resolves and rejects any id that escapes `runs/` (`400 Invalid run id`). Every run-id
  route goes through it. Not a hole.
- **SQL injection — none.** `db.py` and `corpus.py` are fully parameterized; the FTS5 search
  binds `MATCH ?`. Confirmed.
- **Deserialization — clean.** No `pickle`, `marshal`, `eval`, `exec`, or unsafe
  `yaml.load` anywhere; the custom YAML parser is non-eval and iterative; the regexes are
  anchored/bounded (no ReDoS). Confirmed.

## Findings (prioritized)

### P0 — fix before binding any non-loopback interface

**S1 · Arbitrary local file read in the static catch-all (LFI).** `HIGH`
[api.py:407-418](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/api.py). The SPA fallback route builds
`file_path = frontend_path / full_path` and returns `FileResponse(file_path)` with **no
`.resolve()` and no bounds check** — unlike `_run_dir`, which does exactly that guard 20
lines above. A request like `GET /..%2f..%2f.env` (or `../../rws.db`, `../../src/...py`)
resolves outside `web/dist/` and is served verbatim. Because the server binds `0.0.0.0`
with no auth, anyone who can reach the port reads `.env` (the real keys), `rws.db`, and all
source. Only active when `web/dist/` exists (frontend built), but that is the deployed
case. **This is the one to fix first.** Fix: resolve `file_path` and reject anything not
under `frontend_path` — reuse the `_run_dir` pattern.

**S2 · Default bind host is `0.0.0.0`.** `HIGH (as a multiplier)`
[api.py:423](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/api.py). Every other finding's severity is gated on
"if exposed." Defaulting to `127.0.0.1` and requiring an explicit opt-in env
(`RWS_BIND_HOST=0.0.0.0`) to go public turns the whole class from "exposed by default" to
"exposed on purpose." One line, the highest risk-reduction-per-character in the repo.

**S3 · `POST /runs/execute` reads any local file the process can.** `HIGH`
[api.py:189-196](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/api.py). `input_path` is taken from the request,
`expanduser().resolve()`'d, and read with **no directory allowlist** — an absolute path is
honoured. Unauthenticated callers can make the server read and process `/etc/passwd`,
sibling-repo source, `~/.ssh/...`, etc., and stream the result back over the run's
WebSocket. Fix: require `input_path` to resolve under an allowed root (repo root or a
configured documents dir); reject absolute/escaping paths. *(Behaviour tradeoff: today you
can run on a file anywhere on disk from the API; an allowlist removes that. Flagging for
your call — CLI is unaffected.)*

### P1 — needed for any multi-user / shared deployment

**S4 · No authentication on any route.** `HIGH (public) / N/A (loopback)`
All of `/runs`, `/runs/{id}`, `/runs/execute`, `/runs/{id}/resolve`, `/runs/{id}/finalize`,
`/api/audit/selection`, `/api/compare`, `/ws/{id}` are open. By design for localhost; a
hard blocker for any shared bind. If you ever expose it, gate it behind a single bearer
token (`RWS_API_TOKEN`) checked in middleware — cheap, and it neutralizes S3/S5/S6 at once.

**S5 · Unauthenticated provider-cost abuse.** `MEDIUM`
[api.py:247](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/api.py) `/api/audit/selection` and the `execute=true`
path both call **real providers with your keys** on attacker-supplied text. On an exposed
port this is an open wallet (and a prompt-exfiltration channel). Mitigated entirely by S2+S4.

### P2 — defense-in-depth / cheap hardening (worth doing regardless of exposure)

**S6 · Credential-redaction regex misses hyphenated keys.** `MEDIUM`
[hooks.py:17-22](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/hooks.py). `sk-[A-Za-z0-9]{20,}` stops at the first
hyphen, so OpenRouter (`sk-or-v1-…`) and Nous (`sk-nous-…`) keys are **not** redacted by
the pre-write artifact scrubber. The artifacts are gitignored, so this only bites on
export/sharing — but the fix is one character class: `sk-[A-Za-z0-9-]{20,}`. Do it.

**S7 · `shell=True` on the MCP subprocess.** `MEDIUM`
[mcp_client.py](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/mcp_client.py) launches the server via
`subprocess.Popen(self.server_path, shell=True, …)`. `server_path` is config/constructor-
controlled, **not** request-controlled, so this is not a remote RCE — but `shell=True` is
unnecessary (the path can be passed as an argv list) and is a latent injection sink if
`server_path` ever becomes configurable from a less-trusted source. Drop `shell=True`. The
`npm run dev` call in `cli.py` is a static argv and intentionally `shell=True` for Windows
(documented in CLAUDE.md) — leave it, or pass `shell=False` with the npm path resolved.

**S8 · SSRF via `RWS_LOCAL_LLM_URL` / `RWS_OLLAMA_URL`.** `LOW`
[providers.py](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/providers.py). Local/Ollama endpoints come from env and
are sent the prompt plus an `Authorization` header. Env is a trusted input (whoever sets it
owns the box), so this is low — but if those vars are ever sourced from request/config,
it becomes an exfiltration redirect. Note as a constraint: never wire these from user input.

**S9 · CORS allows `Authorization` it never checks; WebSocket `run_id` unauthenticated.** `LOW`
[api.py:72-77](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/api.py), [api.py:128](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/api.py).
Origins default to localhost (fine); the `Authorization` allow-header is cosmetic until S4
exists. `/ws/{run_id}` accepts any id and lets a client queue "human_injection" content
into another run and spam connections (memory). Both collapse into S4.

**S10 · Static-report XSS is self-inflicted only.** `LOW`
`html_summary.py`/`report.py` use `html.escape` on findings/excerpts and the React UI
auto-escapes; `summary.html` embeds your *own* document text and you open it yourself. No
cross-user vector. Keep escaping on any new HTML sink.

### P3 — hygiene (not security-critical)

- **npm ecosystem missing from Dependabot.** [.github/dependabot.yml](https://github.com/gasyoun/RuWritingStyles/blob/main/.github/dependabot.yml)
  covers `pip` + `github-actions` but not `web/`'s `npm`. Add it — cheap supply-chain win.
- **"Zero runtime dependencies" is now inaccurate.** The pipeline/CLI core stays light, but
  the API extra pulls `fastapi`/`uvicorn`/`pydantic`/`requests`/`websockets`/`jinja2`
  ([pyproject.toml](https://github.com/gasyoun/RuWritingStyles/blob/main/pyproject.toml)). This is a *doc* accuracy issue, not a vuln — phrase it
  as "zero deps for the core pipeline; the web surface adds FastAPI."
- **CodeQL lists PHP** ([.github/workflows/codeql.yml](https://github.com/gasyoun/RuWritingStyles/blob/main/.github/workflows/codeql.yml)) for a
  repo with no PHP — harmless waste; covers Python; add `javascript` for `web/`.

## Recommended fix order (all cheap, all low-risk except S3's tradeoff)

1. **S2** — bind `127.0.0.1` by default, `RWS_BIND_HOST` to opt into public. *(1 line)*
2. **S1** — bounds-check the static route (reuse the `_run_dir` resolve+parents guard).
3. **S6** — broaden the credential regex to hyphenated keys.
4. **S7** — drop `shell=True` on the MCP Popen.
5. **P3** — npm Dependabot + the doc/CodeQL touch-ups.
6. **S3 / S4** — input_path allowlist + optional `RWS_API_TOKEN` middleware. *(Your call —
   S3 changes behaviour; S4 is the real gate for ever exposing this.)*

Items 1–5 are safe, mechanical, and lock down the default posture without changing any
intended workflow. 6 is the "actually shippable as a public service" tier and is a product
decision, not a cleanup.

## Status (2026-07-19): all findings closed, including token-aware Web Studio

Items 1–5 shipped in v2.5.4. **S3 and S4 now implemented (v2.7.1)** — the public-bind tier:

- **S3 — input_path allowlist.** `POST /runs/execute` now confines `input_path` to an
  allowed root (`api._input_root`): the repo root by default, widenable with
  `RWS_INPUT_ROOT` for legitimate out-of-repo inputs. A path resolving outside returns
  **403** before any read, closing the arbitrary-file-read. The default UI path
  (`…/RuWritingStyles/article.md`) is under the repo, so the local flow is unaffected.
- **S4 — optional bearer-token auth, default-deny.** An HTTP middleware (`api._require_token`)
  requires `Authorization: Bearer <RWS_API_TOKEN>` when `RWS_API_TOKEN` is set. It is
  **default-deny**: every route is protected *except* an explicit static-frontend allowlist
  (`_PUBLIC_PATHS` = `/`, `/index.html`, `/favicon.ico`; `_PUBLIC_PREFIXES` = `/assets`), so a
  future data route is protected automatically rather than relying on a maintainer to add it
  to a protected-prefix list. The WebSocket checks the same token (header or `?token=`, closes
  1008). **Off by default** — the loopback dev tool keeps working with zero setup. CORS
  preflight (`OPTIONS`) is never blocked; comparison is constant-time (`secrets.compare_digest`).

A follow-up `/code-review` pass (2026-06-13) then (a) caught and fixed a **pre-existing crash** —
`/runs/execute` called `read_document`/`normalize_document`/`segment_markdown` which were never
imported in `api.py`, so the web-UI "New Run" path raised `NameError`; (b) hardened S4 from a
protected-prefix allowlist to the default-deny model above; (c) consolidated the three
path-containment checks (`_run_dir`, S3, S1) into one shared `_within(root, path)` primitive so a
later traversal-hardening tweak can't be applied to one guard and forgotten in another.

An adversarial verification pass (4 parallel skeptics) then drove raw ASGI scopes against the
auth layer and found **no unauthenticated bypass** (encoded traversal, case/slash variants,
`OPTIONS`, `/openapi.json`, WS — all denied), and confirmed the `_within` refactor is a
behaviour-preserving extraction. It also caught a **fourth same-class missing-import bug** the
first pass missed: `resolve_run`→`background_revision` called `provider_from_name` without it in
scope (`NameError` swallowed by `except Exception`, so `/runs/{id}/resolve` re-revision silently
failed on real providers). Fixed by hoisting `provider_from_name` to a module import; the
`/assets` exemption was also tightened to `/assets/` (so `/assets../x` stays protected).

`tests/test_api_security.py` (12) covers all of this via `TestClient` plus unit coverage of
`_within`/`_is_public_request`. **To bind publicly now:** set `RWS_BIND_HOST=0.0.0.0` (S2)
**and** `RWS_API_TOKEN=<secret>` (S4); optionally `RWS_INPUT_ROOT` (S3). Without a token, keep
it on loopback.

**Token-aware Web Studio (v2.15.2):** the bundled React SPA now routes every HTTP request through
one API client and sends `Authorization: Bearer <token>` when configured. The Settings dialog
stores the backend URL and token in browser `sessionStorage`; WebSocket connections convert
`http→ws` / `https→wss` and append only the URL-encoded token query parameter required by the
browser WebSocket API. Invalid URLs, 401 responses, and connection failures are visible in the
UI. The loopback default remains token-free and unchanged.

_Dr. Mārcis Gasūns_
