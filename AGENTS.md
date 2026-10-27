# omsg-bridge contributor instructions

## Purpose and scope
A small, asynchronous macOS LAN bridge over `imsg`: REST, WebSockets, OpenAPI and a discovery-based MCP client. Preserve upstream JSON; do not reimplement Messages storage or delivery. Python 3.11+, asyncio and aiohttp. Prefer the smallest complete change; no queues/databases/frameworks without a demonstrated need.

## Safety (mandatory)
- This repository is public. Never commit credentials, personal message data, real chat databases, logs or private configuration, even temporarily. Secrets belong in `~/.config/omsg-bridge/settings.toml` (mode 0600) or ignored `.env.local`; the latter is not auto-loaded.
- Never delete or modify existing user data during development or installation. Preserve existing settings. Never enable private-framework injection or change SIP automatically.
- Never send real messages, reactions, read receipts, typing indicators, or mutate chats in tests. Use the fake CLI. Live mutation testing requires explicit contemporaneous operator permission; the initial operator's only allowable test recipient is recorded outside this public repo, not here.
- Bind to 127.0.0.1 by default. Require Basic Auth unless explicitly disabled. Protect HTTP, docs and WebSocket handshakes. Do not log credentials, bodies, message data or query strings.
- No shell interpolation of client input. Use async subprocess argument arrays. Never automatically retry a mutation: timeout/disconnect may leave delivery uncertain.

## Workflow
- Read callers, tests, documentation and upstream sources before changing behavior.
- TDD: add a failing test, implement the minimum, run tests and end-to-end checks using a fake executable over real TCP/stdio.
- Keep command metadata, routes, OpenAPI, MCP discovery and README consistent. Document supported upstream revision and limitations.
- Use async I/O for subprocesses, network and streams. Watchers must not block reads or writes. Clean up subprocesses on disconnect/shutdown; bound output and report failures usefully.
- Long uptime with bounded memory/CPU is a release requirement. Keep admission through response transmission, reject excess work rather than queue it, use bounded output/backpressure, and await cancellation-resistant child cleanup. Add lifecycle/churn/RSS/idle-CPU regressions for resource-sensitive changes; never claim third-party/infinite-uptime guarantees from a finite soak.
- Ask independent subagents to verify assumptions and completed work when authorized by the operator (authorized for the initial build). Review findings yourself.
- Make small working commits. Inspect staged files for secrets before each commit. Never commit runtime `.pi` artifacts.

## Checks
`uv sync --extra dev --extra mcp`
`uv run pytest`
`uv run ruff check .`
`uv run ruff format --check .`

Tests must run without installed imsg, macOS permissions, or access to a Messages database. Live read-only checks are opt-in, never part of CI.
