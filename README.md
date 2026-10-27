# omsg-bridge

A small, asynchronous REST / WebSocket bridge for [imsg](https://github.com/openclaw/imsg), with local Swagger UI and a discovery-based MCP adapter. Run it on your Messages Mac and connect from other machines on your LAN.

**Defaults: `127.0.0.1:8787`, Basic Auth required.** No database of its own, background polling, message cache, event backlog, or automatic delivery retries. Python 3.11+ and aiohttp; MCP dependencies are optional on the server.

## Install

Prerequisites: macOS 14+, signed into Messages, and [Homebrew](https://brew.sh). From a checkout of this repository:

```sh
./scripts/install.sh          # install, configure credentials; do not start a service
# OR
./scripts/install.sh --login  # also start now and automatically restart at login / after crashes
```

The installer:

1. Checks for `imsg`; if missing, runs **`brew install steipete/tap/imsg`**. Existing installations are not upgraded automatically.
2. Uses Python 3.11+ (installs Homebrew Python 3.13 if needed), creates `~/.local/share/omsg-bridge/venv`, and installs the bridge.
3. Creates `~/.config/omsg-bridge/settings.toml` with username `bridge` and a randomly generated password, mode **0600**, only if the file is absent. **Existing settings/credentials are preserved.** The password is not printed.
4. Links `~/.local/bin/omsg-bridge`, refusing to overwrite an unrelated file. `--login` installs the per-user `local.omsg-bridge` LaunchAgent, not a root daemon.

No Messages data is altered during installation. No messages, reactions, read receipts, or typing indicators are sent. No private IMCore helper is enabled.

Run manually (or add `~/.local/bin` to `PATH`):

```sh
~/.local/bin/omsg-bridge
# Alternative settings file:
~/.local/bin/omsg-bridge --config /path/outside/repo/settings.toml
```

### macOS permissions

Grant **Full Disk Access** to the actual executable/launcher in System Settings → Privacy & Security. A login service does not necessarily inherit your terminal's permissions; grant the venv Python executable/launcher as appropriate and restart it. Sending also needs **Automation → Messages**; UI `react` needs **Accessibility**. SMS requires Text Message Forwarding on your paired iPhone.

`/health` does not probe the database. After granting permissions, use `GET /v1/chats?limit=1&no-contacts=true` or RPC `status` to check actual readiness. See [upstream permissions](https://github.com/openclaw/imsg/blob/v0.19.1/docs/permissions.md).

### Login service control

```sh
launchctl print "gui/$(id -u)/local.omsg-bridge"
launchctl kickstart -k "gui/$(id -u)/local.omsg-bridge" # restart after changing settings
launchctl bootout "gui/$(id -u)/local.omsg-bridge"     # stop until loaded again/login
```

To disable login startup permanently, stop the job and move `~/Library/LaunchAgents/local.omsg-bridge.plist` outside `LaunchAgents`. Keep your settings and Messages data. Re-running `install.sh --login` updates/restarts only this service. Logs are in `~/Library/Logs/omsg-bridge/`; HTTP access/body/query logging is disabled. A `PORT` variable exported in a terminal is **not inherited by launchd**: use the settings file for the login service.

## Settings and authentication

Edit `~/.config/omsg-bridge/settings.toml` locally:

```toml
host = "127.0.0.1" # use "0.0.0.0" or a LAN address explicitly for other machines
port = 8787       # PORT environment variable overrides this
imsg = "imsg"    # installer writes the absolute executable path
command_timeout = 60 # seconds, finite commands/RPC only; max 3600

[auth]
enabled = true
username = "bridge"
# Keep the installer-generated password here, or set your own strong password.
```

**Startup refuses missing/empty credentials.** `OMSG_USERNAME` and `OMSG_PASSWORD` can override TOML credentials. Explicitly setting `auth.enabled = false` disables authentication, including on a LAN bind; that is deliberately unsafe and never the default. HTTP, health, docs, and WebSocket handshakes use the same authentication. Browser cross-origin requests are rejected; there is no wildcard CORS.

Basic Auth over plain HTTP is **not encrypted**. Use a trusted LAN, or a TLS reverse proxy that preserves the original Host/scheme correctly; do not expose this service to the Internet. Authenticated clients have the same message, file, and mutation privileges as your `imsg` account. Paths such as `file`, `db`, `format-file`, `parts-file`, and `dylib` refer to the **server's filesystem**, not uploads. Do not give credentials to untrusted clients.

Never put credentials or real message fixtures in Git. `.env.local` is ignored but **not auto-loaded**; export variables explicitly if using it. Keep all actual settings outside the checkout. Restart the service after changes.

## REST API

- **OpenAPI:** `/docs/openapi.json` (OpenAPI 3.0.3).
- **Interactive Swagger UI:** `/docs/ui`. All UI assets are served locally; no CDN or external validator receives your data. Authenticate with the browser prompt / Swagger Authorize.
- **Health:** `GET /health` → `{"status":"ok","version":"0.1.0","imsg_available":true}`. Liveness/executable availability only, not a delivery or permission guarantee.
- **Discovery:** `GET /v1/commands` → versioned upstream command inventory, descriptions, canonical options, positional arguments, read-only hints, and transport modes.

Every finite CLI command has **`POST /v1/<command>`** with this body:

```json
{"args": [], "options": {"chat-id": 42, "limit": 20}}
```

Keys match canonical long CLI names **without `--`**. Flags are JSON booleans; value options accept strings/numbers. Arrays repeat an option, e.g. `"option": ["Tea", "Coffee"]` for polls. `args` carries positional subcommands such as `["list"]`, `["status"]`, or `["vote"]`. Options containing JSON (e.g. `parts`, `format`) are passed as **JSON-encoded strings**, just like CLI values. The bridge controls `--json`; aliases, help/version flags, unknown keys, and shell commands are not accepted as options. `typing.stop` is a **value option**, so use `"stop":"true"`, not a boolean.

Successful finite calls return:

```json
{"data": [{"id": 42, "name": "Example chat"}], "stderr": ""}
```

`data` is always an array of unmodified upstream JSON records. Empty stdout becomes `[]`; a single JSON object becomes one record. A top-level upstream array stays one record rather than being silently flattened. `completions` is the text exception: `data` contains one string, with no `--json` passed. RPC has its own response format below.

Read-only commands also accept **GET** with query options (`?chat-id=42&limit=20&attachments=true`). Repeat query keys for repeated options; `arg=list` supplies a positional argument. Mutations are POST only. The bridge does not invent missing CLI operations (e.g. scheduled-message creation).

### Complete command / endpoint inventory (imsg v0.19.1)

Every name in this table is prefixed with `/v1/`:

| Commands | HTTP / purpose |
|---|---|
| `chats`, `group`, `history`, `stats`, `search` | GET or POST: conversations, identity/participants, messages, aggregates, search |
| `scheduled` (`args:["list"]`), `chat-background` (`args:["status"]`) | GET or POST: read-only scheduled messages/background state |
| `status`, `completions` (`args:["llm"]`, `bash`, `zsh`, or `fish`) | GET or POST: upstream diagnostics / CLI reference |
| `send`, `react` | POST: text/files and standard UI tapbacks |
| `read`, `typing` | POST: read receipts and typing start/stop |
| `send-rich`, `send-multipart`, `send-attachment`, `send-sticker` | POST: richer sends, replies, effects, formatting, audio/stickers |
| `poll` (`send`, `vote`, `unvote`) | POST: native polls; poll sends may also send a caption |
| `tapback`, `edit`, `unsend`, `delete-message`, `notify-anyways` | POST: GUID-targeted reactions and message mutations |
| `chat-create`, `chat-name`, `chat-photo`, `chat-add-member`, `chat-remove-member`, `chat-leave`, `chat-delete`, `chat-mark` | POST: chat creation, metadata, membership, deletion and read state |
| `account`, `whois`, `nickname` | POST: account/handle/contact inspection; `local:true` flag avoids helper where supported |
| `name-photo` (`status`, `share`) | POST: contact sharing state / action |
| `launch` | POST: explicit upstream helper/agent lifecycle; **never invoked automatically** |
| `watch` | WebSocket GET, not a finite POST |
| `rpc` | POST one RPC call; WebSocket GET at `/v1/rpc/ws` for a session |

Descriptions and every option are included in the discovery endpoint and OpenAPI; see also [upstream JSON fields](https://github.com/openclaw/imsg/blob/v0.19.1/docs/json.md) and [provenance](THIRD_PARTY.md). Unknown upstream JSON fields are preserved. New CLI commands require a catalog update; new RPC methods pass through immediately.

**Important upstream limitations:** `react` acts on the selected/last message in a chat, not a guaranteed GUID. Use `tapback` for GUID targeting. Most advanced operations require the private IMCore helper and upstream's SIP-disabled setup. We expose these operations but **do not recommend or automatically disable SIP, inject into Messages, or kill/relaunch Messages**. Capabilities vary by macOS/imsg version. CLI `launch` and destructive commands run only when explicitly requested by an authenticated client.

### Examples

These are examples, **not installation or test actions**. Curl prompts for the password instead of putting it in shell history:

```sh
curl -u bridge 'http://127.0.0.1:8787/v1/chats?limit=10&no-contacts=true'
curl -u bridge 'http://127.0.0.1:8787/v1/history?chat-id=42&limit=20'
curl -u bridge 'http://127.0.0.1:8787/v1/scheduled?arg=list'

# ONLY when you intend to send; replace RECIPIENT first:
curl -u bridge -H 'Content-Type: application/json' \
  -d '{"options":{"to":"RECIPIENT","text":"Hello","service":"imessage"}}' \
  http://127.0.0.1:8787/v1/send

# A reaction is also a real mutation:
curl -u bridge -H 'Content-Type: application/json' \
  -d '{"options":{"chat-id":42,"reaction":"like"}}' \
  http://127.0.0.1:8787/v1/react
```

### Errors and delivery uncertainty

Errors use `{"error":{"code":"...","message":"...", ...}}`. Invalid input → 400, missing auth → 401, cross-origin → 403, slow request body → 408, oversized request → 413, wrong content type → 415, CLI/output failure → 502, missing executable/busy/shutdown → 503, command timeout → 504. CLI failures include `exit_code`, parsed stdout `data`, and bounded `stderr`, including permission guidance.

**Never automatically retry a send, reaction, or other mutation after timeout/disconnect/failure.** The operation may already have happened; `retry_safe:false` is intentional. A `send` success is upstream's acknowledgement, not proof of delivery. RPC errors remain upstream JSON-RPC error objects, returned with HTTP 200; inspect `error`, not just the HTTP status.

## WebSockets and JSON-RPC

Authenticate the handshake using the same `Authorization: Basic …` header. Credentials in query strings are not supported. Browser clients must use the same authenticated origin (native browser WebSocket cannot set arbitrary headers); non-browser clients can supply the header directly.

### `/v1/watch`

One `imsg watch --json` child per connected socket, started on demand. Query options match the CLI:

```text
ws://mini.local:8787/v1/watch?reactions=true&attachments=true&since-rowid=123
```

One upstream JSON record per text frame, without an added wrapper:

| Event | Recognition |
|---|---|
| New message | Message record with `id`, `chat_id`, `guid`, `text`, etc.; normally no `type` |
| Reaction | `is_reaction:true`, `is_reaction_add`, `reaction_type`, `reacted_to_guid`; enable `reactions=true` |
| Edit / unsend | `type:"edited"` / `type:"unsent"`; reconcile the existing message, don't append |
| Native poll | Message's `poll` extension includes `event` and decoded poll/vote data |
| Optional helper event | With `bb-events=true`: `kind:"bridge-event"`, `event`, `data`, optional `ts`; current names include `started-typing`, `stopped-typing`, `aliases-removed` |
| Bridge transport failure | `{"type":"bridge.error","error":{...}}`, then close |

**Helper events are not scoped by chat/date/participant filters** in upstream. A healthy DB watch does not prove the helper event stream is available. Unknown event names/fields pass through.

No replay queue is stored by the bridge. Resume new rows with `since-rowid`; after any disconnect or overflow, refresh history to reconcile missed edits/unsends. Reset cursors after replacing/restoring the Messages database. An idle stream does not time out merely because no messages arrive; heartbeat and bounded write waits detect dead/slow peers.

### `/v1/rpc` and `/v1/rpc/ws`

REST accepts a **complete JSON-RPC object**, not the CLI options envelope:

```sh
curl -u bridge -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"status","params":{}}' \
  http://127.0.0.1:8787/v1/rpc
```

RPC `status` discovers compiled/currently usable methods. Methods include `chats.list/get`, `messages.history/search/stats/after/scheduled`, `send`, `send.tracked`, `message.send_status`, advanced sends/mutations, group/contact/poll/handle operations and their upstream aliases. See the [exact RPC methods/parameters](https://github.com/openclaw/imsg/blob/v0.19.1/docs/rpc.md). Optional `?db=...` and RPC runtime query options configure the child.

For a persistent session, connect to `/v1/rpc/ws` and send the same JSON objects as frames. Responses can arrive out of order; correlate by `id`. Notifications omit `id`. No batch arrays. `watch.subscribe`, `bridge.events.subscribe`, and `watch.unsubscribe` require this WebSocket transport, and subscriptions belong to that socket. It forwards `message`, `error`, `watch.overflow`, `bridge.event`, `bridge.events.overflow`, and `bridge.events.error` notifications unchanged. Wrapper failures use JSON-RPC notification `omsg.error`, then close.

Each RPC WebSocket has its own upstream process and mutation lane. REST RPC uses a short-lived process; finite CLI calls also use separate processes. Neither shares upstream's process-local uncertain-delivery state across clients. Do not issue overlapping UI mutations from multiple clients or use new connections to retry uncertain sends.

## MCP for agents

The optional **stdio MCP adapter** can run on another machine; it uses HTTP, not local imsg. Install from a checkout with [uv](https://docs.astral.sh/uv/):

```sh
uv tool install '.[mcp]'
omsg-bridge-mcp --url http://mini.local:8787 --config /path/outside/repo/client.toml
```

The client settings file uses the same `[auth]` section and credentials as the server; `OMSG_USERNAME`, `OMSG_PASSWORD`, and `OMSG_URL` may be set in the launching environment instead. Never commit client credentials or embed passwords in URLs. Stdio stdout is protocol-only.

An MCP client configuration (replace the executable/config paths):

```json
{
  "mcpServers": {
    "omsg": {
      "command": "/absolute/path/to/omsg-bridge-mcp",
      "args": ["--url", "http://mini.local:8787", "--config", "/private/path/client.toml"]
    }
  }
}
```

Only **three tools** are advertised:

1. `search_actions(query, limit=10)` — small matching action summaries.
2. `describe_action(name)` — fetch one action's input schema, options and safety notes.
3. `execute_action(name, payload)` — call that action via REST. Mutations are marked potentially destructive/non-idempotent. Authentication and upstream errors are surfaced as tool errors.

Schemas come from the connected server, not a giant hard-coded tool list. `describe_action("rpc")` explains live RPC capability discovery. MCP tool calls are finite; persistent subscriptions use the WebSocket APIs, not an endlessly running tool call.

## Resource limits and tests

- **At most 8 active non-health HTTP requests/WebSockets, including response transmission**, and at most 8 imsg children. Excess work gets 503 immediately; no waiting queue. Health remains available.
- No application event queues, persistent child when idle, or per-message caches. One child per connected stream, cleaned up when it disconnects.
- Request/frame/stream record: **1 MiB**. Finite stdout: **16 MiB**. Retained stderr: **64 KiB** (the rest is drained/discarded). Use upstream limits/filters for large history reads.
- Request-body and response/stream-write deadlines: **10 seconds**. Finite command deadline is configurable (default 60s). Failed writes close the connection; there is no replay buffer.
- Shutdown stops admission, closes streams, terminates child process groups, escalates to kill when needed, and awaits cleanup even during cancellation. No automatic mutation retries.
- Third-party imsg/Apple processes are outside our memory guarantees. The bridge cannot safely impose a memory cap on Messages.app. The automated soak checks bridge RSS/idle CPU; it is regression evidence, not a claim of infinite-uptime proof.

Development (no imsg or Messages permissions required):

```sh
uv sync --extra dev --extra mcp
uv run pytest
uv run ruff check .
uv run ruff format --check .
# Focused 720-operation real-process resource soak, prints RSS/idle CPU:
uv run pytest tests/test_e2e.py -q -s
```

Tests launch a **synthetic executable** through real subprocesses, exercise every finite endpoint, HTTP auth, local OpenAPI/UI, WS events/concurrent REST, RPC, MCP over real stdio, subprocess reaping, failed/oversized/slow output, cancellation, shutdown, and slow-reader backpressure. No real messages, reactions, read receipts, or typing indicators are sent. Actual Apple permission/delivery behavior must be verified separately by the operator; advanced private-framework features are not enabled by tests.

MIT licensed. Not affiliated with Apple or imsg.
