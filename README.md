# omsg-bridge

A lightweight async REST / WebSocket bridge for [imsg](https://github.com/openclaw/imsg), with OpenAPI and discovery-based MCP. Runs on your Messages Mac; other machines on your LAN can connect. Default: **127.0.0.1:8787, Basic Auth required**.

## Installation (interface being implemented)

macOS 14+, Messages signed in, Homebrew. From a checkout:

```sh
./scripts/install.sh                 # checks/installs brew install steipete/tap/imsg
./scripts/install.sh --login         # also installs a per-user launchd login service
```

The installer creates private settings only when absent, and never overwrites existing credentials or Messages data. Grant Full Disk Access to the actual executable/launching app in System Settings. Sending also needs Automation → Messages; UI tapbacks need Accessibility. A login service may need separate grants from your terminal.

## Configuration

`~/.config/omsg-bridge/settings.toml` (0600):

```toml
host = "127.0.0.1" # explicitly use "0.0.0.0" to serve your LAN
port = 8787       # PORT environment variable takes precedence
imsg = "imsg"
command_timeout = 60

[auth]
enabled = true
# Set username and password locally, never in this repository.
```

Authentication defaults to required; missing credentials prevent startup. Set `auth.enabled = false` only deliberately. Basic Auth over HTTP is not encrypted: use a trusted LAN or a TLS reverse proxy. Never expose this service to the Internet. Authenticated clients have the same message/file/mutation privileges as imsg running under your account.

## API contract

- `GET /health`: authenticated liveness and executable availability (not Messages permissions).
- `GET /v1/commands`: discover command metadata and options.
- `POST /v1/<command>`: finite CLI commands, body `{"args": [], "options": {"chat-id": 42}}`; option names match long CLI flags, without `--`. JSON is enabled automatically. Results are `{"data": [<upstream JSON records>], "stderr": "..."}`.
- `GET /v1/<read-command>`: query-string equivalents for read-only commands.
- `GET /v1/watch`: WebSocket, query options forwarded to `imsg watch --json`; one untouched upstream JSON record per frame.
- `POST /v1/rpc`: one JSON-RPC request/response. `GET /v1/rpc/ws`: persistent bidirectional JSON-RPC, including all subscriptions and notifications.
- `GET /docs/openapi.json`: OpenAPI specification. `GET /docs/ui`: interactive documentation.

Watch emits new messages, reaction events (with `reactions=true`), and `type: edited` / `type: unsent` updates. RPC also exposes bridge subscriptions where upstream supports them. Resume new rows with `since-rowid`; refresh history after disconnect to reconcile edits/unsends. No persistent event storage or automatic mutation retries.

## MCP

The optional stdio MCP adapter connects to this HTTP server. Only three tools are advertised: search actions, describe one action (including its schema), execute one action. Detailed actions are discovered on demand, not injected into every prompt.

## Development

Implementation and detailed install/API examples are being added in working, tested steps. Tests use a fake imsg executable; they never send messages or touch your Messages database.
