# imsg CLI Reference

macOS Messages.app CLI to send, read, and stream iMessage/SMS.

## Commands

### chats

List recent conversations

Usage: `imsg chats [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--limit <value>`: Number of chats to list
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--no-contacts`: Skip Contacts lookups and return raw handles
- `--unread-only`: Return only chats with unread inbound messages
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg chats --limit 5`
- `imsg chats --limit 5 --json`
- `imsg chats --unread-only --json`

### stats

Show aggregate message and media statistics

Usage: `imsg stats [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat-id <value>`: Limit stats to a chat rowid
- `--time-zone <value>`: IANA time zone for date buckets (defaults to local)
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--media`: include attachment statistics
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg stats`
- `imsg stats --chat-id 42 --time-zone Europe/Vienna --media --json`

### group

Show chat identity and participants for a chat id

Prints chat identifier, guid, display name, service, group flag, and participants for a given chat rowid. Works for direct chats too.

Usage: `imsg group [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat-id <value>`: chat rowid from 'imsg chats'
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg group --chat-id 1`
- `imsg group --chat-id 1 --json`

### history

Show recent messages for a chat

Usage: `imsg history [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat-id <value>`: chat rowid from 'imsg chats'
- `--limit <value>`: Number of messages to show
- `--participants <value>`: filter by participant handles
- `--start <value>`: ISO8601 start (inclusive)
- `--end <value>`: ISO8601 end (exclusive)
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--no-contacts`: Skip Contacts lookups and return raw handles
- `--attachments`: include attachment metadata
- `--convert-attachments`: convert CAF/GIF attachments to model-compatible cached files
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg history --chat-id 1 --limit 10 --attachments`
- `imsg history --chat-id 1 --start 2025-01-01T00:00:00Z --json`

### watch

Stream messages, edits, and unsends

Usage: `imsg watch [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat-id <value>`: limit to chat rowid
- `--debounce <value>`: debounce interval for filesystem events (e.g. 250ms)
- `--since-rowid <value>`: start watching after this rowid
- `--participants <value>`: filter by participant handles
- `--start <value>`: ISO8601 start (inclusive)
- `--end <value>`: ISO8601 end (exclusive)
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--attachments`: include attachment metadata
- `--convert-attachments`: convert CAF/GIF attachments to model-compatible cached files
- `--reactions`: include reaction events (tapback add/remove) in the stream
- `--bb-events`: include dylib-pushed events (typing, alias-removed) when injection is active
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg watch --chat-id 1 --attachments --debounce 250ms`
- `imsg watch --chat-id 1 --participants +15551234567`

### send

Send a message (text and/or attachment)

Usage: `imsg send [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--to <value>`: phone number or email
- `--chat-id <value>`: chat rowid
- `--chat-identifier <value>`: chat identifier (e.g. iMessage;+;chat...)
- `--chat-guid <value>`: chat guid
- `--text <value>`: message body
- `--file <value>`: path to attachment
- `--service <value>`: service to use: imessage|sms|auto
- `--region <value>`: default region for phone normalization
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--no-sms-fallback`: disable automatic iMessage->SMS fallback for text-only auto phone sends
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg send --to +14155551212 --text "hi"`
- `imsg send --to +14155551212 --text "hi" --file ~/Desktop/pic.jpg --service imessage`
- `imsg send --chat-id 1 --text "hi"`

### react

Send a standard tapback through Messages UI automation

Sends a standard tapback using Messages' last-or-selected-message shortcut.

IMPORTANT LIMITATIONS:
- Cannot reliably select a specific message; use bridge tapback for GUID targeting
- Requires Messages.app to be running
- The chat must exist in Messages' live AppleScript chats collection
- Uses UI automation (System Events) which requires accessibility permissions
- Opens the conversation directly and requires a visible, enabled Tapback button
- Reports success only after a new outgoing reaction is recorded in the requested chat
- If confirmation fails, inspect Messages before retrying; a retry may toggle a reaction

Reaction types:
  love (❤️), like (👍), dislike (👎), laugh (😂), emphasis (‼️), question (❓)

Custom emoji tapbacks can be read from history/watch output, but cannot be
sent reliably through Messages.app AppleScript automation.

Usage: `imsg react [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat-id <value>`: chat rowid to react in
- `--reaction, -r <value>`: reaction type: love, like, dislike, laugh, emphasis, question
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg react --chat-id 1 --reaction like`
- `imsg react --chat-id 1 -r love`

### read

Mark messages as read for a chat

Marks messages as read via IMCore advanced features.
Requires SIP disabled and Messages launched with `imsg launch`.

Usage: `imsg read [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--to, --handle <value>`: phone number or email
- `--chat-id <value>`: chat rowid
- `--chat-identifier <value>`: chat identifier (e.g. iMessage;-;+14155551212)
- `--chat-guid <value>`: chat guid
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg read --to +14155551212`
- `imsg read --handle steipete@gmail.com`
- `imsg read --chat-id 1`
- `imsg read --chat-identifier "iMessage;-;+14155551212"`

### typing

Send typing indicator to a chat

Sends typing indicators via IMCore advanced features.
Requires SIP disabled and Messages launched with `imsg launch`.

Usage: `imsg typing [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--to <value>`: phone number or email
- `--chat-id <value>`: chat rowid
- `--chat-identifier <value>`: chat identifier (e.g. iMessage;-;+14155551212)
- `--chat-guid <value>`: chat guid
- `--duration <value>`: how long to show typing (e.g. 5s, 3000ms); omit for start-only
- `--stop <value>`: stop typing indicator instead of starting
- `--service <value>`: service to use: imessage|sms|auto
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg typing --to +14155551212`
- `imsg typing --to +14155551212 --duration 5s`
- `imsg typing --to +14155551212 --stop true`
- `imsg typing --chat-identifier "iMessage;-;+14155551212"`

### launch

Launch Messages.app with dylib injection

Ensures Messages.app is running with DYLD_INSERT_LIBRARIES set to
inject the imsg bridge helper dylib. Reuses a healthy current helper.
This enables advanced features like typing indicators and read receipts
that require IMCore framework access.

If Messages.app is already running with a dylib injected by a different
imsg version, it is killed and relaunched with the current dylib under
the launch lock. Pass --force to relaunch even when the running dylib
matches.

--install-agent installs and loads an opt-in login LaunchAgent that runs
this check at login and every 300 seconds (minimum 60 via --agent-interval).
--uninstall-agent unloads and removes it. Neither flag can be combined
with --force or --kill-only. Headless Macs need automatic login.
Non-interactive successful launches are quiet; JSON output is unchanged.

Requires SIP (System Integrity Protection) to be disabled.

Usage: `imsg launch [options]`

Options:
- `--dylib <value>`: Custom path to imsg-bridge-helper.dylib
- `--agent-interval <value>`: Agent interval in seconds (default 300, minimum 60; requires --install-agent)
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--install-agent`: Install and load the opt-in bridge login agent
- `--uninstall-agent`: Unload and remove the bridge login agent
- `--kill-only`: Only kill Messages.app, don't relaunch
- `--force`: Relaunch even when Messages already runs the current dylib
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg launch`
- `imsg launch --force`
- `imsg launch --kill-only`
- `imsg launch --dylib /path/to/dylib`
- `imsg launch --json`
- `imsg launch --install-agent`
- `imsg launch --install-agent --agent-interval 600 --json`
- `imsg launch --uninstall-agent`

### status

Check availability of imsg advanced features

Display the current status of imsg features and permissions.
Shows which advanced features (typing indicators, read receipts) are
available and provides setup instructions if needed.

Usage: `imsg status [options]`

Options:
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg status`
- `imsg status --json`

### rpc

Run JSON-RPC over stdin/stdout

Usage: `imsg rpc [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg rpc`
- `imsg rpc --db ~/Library/Messages/chat.db`

### completions

Generate shell completions or LLM context

Outputs completion scripts for bash, zsh, fish, or a Markdown CLI reference.

Usage: `imsg completions [shell]`

Arguments:
- `shell` optional: bash, zsh, fish, or llm

Examples:
- `imsg completions bash > ~/.bash_completion.d/imsg`
- `imsg completions zsh > ~/.zsh/completions/_imsg`
- `imsg completions fish > ~/.config/fish/completions/imsg.fish`
- `imsg completions llm`

### scheduled

List scheduled messages

Lists future scheduled rows read-only from chat.db.

Usage: `imsg scheduled <action> [options]`

Arguments:
- `action`: list

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--limit <value>`: max rows for list
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg scheduled list --json`

### chat-background

Inspect a Messages chat background

Reads background metadata and cache state from the local Messages database. No bridge or SIP change is required.

Usage: `imsg chat-background <action> [options]`

Arguments:
- `action`: status

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat-id <value>`: local chat ROWID
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg chat-background status --chat-id 42 --json`

### send-rich

Send a message via the IMCore bridge (effects, replies, subjects)

Requires `imsg launch` (SIP-disabled, dylib injected). Unlike `imsg send`
which uses AppleScript, this routes through Messages' private API for
richer features: expressive-send effects, reply targets, subject lines.

Usage: `imsg send-rich [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid (e.g. iMessage;-;+15551234567)
- `--text <value>`: message body
- `--file <value>`: path to attachment
- `--url <value>`: URL to send as a rich link preview
- `--effect <value>`: expressive send id (impact, loud, gentle, invisibleink, confetti, …)
- `--subject <value>`: subject line
- `--reply-to <value>`: guid of message to reply to
- `--part <value>`: part index (default 0)
- `--format <value>`: JSON array of {start,length,styles:[...]} ranges (macOS 15+)
- `--format-file <value>`: path to JSON file containing the format ranges array
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--no-dd-scan`: disable data-detector scan deferral
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg send-rich --chat 'iMessage;-;+15551234567' --text 'hi'`
- `imsg send-rich --chat 'iMessage;-;+15551234567' --reply-to ABCD --file ~/Desktop/pic.jpg`
- `imsg send-rich --chat 'iMessage;-;+15551234567' --text 'BOOM' --effect impact`
- `imsg send-rich --chat 'iMessage;-;+15551234567' --text 'pew pew' --effect lasers`
- `imsg send-rich --chat 'iMessage;-;+15551234567' --url https://imsg.sh`
- `imsg send-rich --chat ... --text 'hello world' --format '[{"start":0,"length":5,"styles":["bold"]}]'`

### send-multipart

Send a multi-part message

Pass --parts as a JSON array (e.g., '[{"text":"hi"},{"text":"there"}]')
or via --parts-file pointing at a .json file. v1 supports text-only
parts; mention/file parts are a future enhancement.

Usage: `imsg send-multipart [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--parts <value>`: JSON array of parts
- `--parts-file <value>`: path to JSON file containing parts array
- `--effect <value>`: expressive send id
- `--subject <value>`: subject line
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg send-multipart --chat 'iMessage;+;chat0000' --parts '[{"text":"hi"},{"text":"world"}]'`

### send-attachment

Send a file attachment via the IMCore bridge

Usage: `imsg send-attachment [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--file <value>`: absolute path to file
- `--reply-to <value>`: guid of message to reply to
- `--transport <value>`: transport to use: auto|dylib|applescript
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--audio`: send as audio message
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg send-attachment --chat 'iMessage;-;+15551234567' --file ~/Pictures/me.jpg`

### send-sticker

Send an image as an iMessage sticker via the IMCore bridge

Requires `imsg launch` (SIP-disabled, dylib injected). Sends the file as a
sticker-attributed IMCore transfer. `--attach-to` associates the sticker
with an existing message bubble. Accepts PNG/APNG, GIF, or JPEG images up
to 500 KiB, 618x618 pixels, 100 frames, and 25 million total decoded
pixels. Stickers are iMessage-only.

Usage: `imsg send-sticker [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--file <value>`: path to sticker image
- `--attach-to <value>`: guid of message bubble to attach the sticker to
- `--target-part <value>`: target bubble part index (default 0)
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg send-sticker --chat 'iMessage;-;+15551234567' --file ~/Pictures/sticker.png`
- `imsg send-sticker --chat 'iMessage;-;+15551234567' --file ~/Pictures/sticker.png --attach-to MSG_GUID --target-part 0`

### poll

Send a native Apple Messages poll

Requires `imsg launch` (SIP-disabled, dylib injected). Use the `send`
action to create a native Messages Polls extension balloon, `vote`/`unvote`
to select or remove a selection.

Messages renders only the options on a poll balloon — the poll title is
never shown to recipients. So `send` automatically sends `--question` as a
plain caption message right after the poll (matching how the native
"comment or Send" field renders — a message with no thread metadata, not a
threaded reply). Callers pass only `--question` and the visible caption
appears for free; `--comment` overrides the caption text when it should
differ from the title. Use `--no-comment` when the caller renders its own
visible context before the poll.

The caption is best-effort but not silent: the result reports it under
`comment` (`requested`, `sent`, `verified`, plus
`error`/`disposition`/`retry_safe` when it fails or remains unresolved). A bridge
acknowledgement is not proof of delivery, so the caption's row is looked
up in the target chat before `sent` is reported true. `sent: null` means
delivery is unknown and must not be retried automatically. Re-send the
caption text alone only when `retry_safe` is true; never re-send the poll,
which would duplicate the balloon.

Usage: `imsg poll <action> [options]`

Arguments:
- `action`: send|vote|unvote

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid or rowid
- `--chat-id <value>`: chat rowid
- `--question <value>`: poll question. Messages does not render the poll title on the balloon, so imsg sends this as a plain caption message right after the poll (the visible text) and also stores it as the payload title for agent readback
- `--comment <value>`: optional override for the caption text; defaults to --question. Sent as a plain message right after the poll, matching Messages' native 'comment or Send' field
- `--reply-to <value>`: guid of message to reply to
- `--option <value>`: poll option text; pass at least twice
- `--poll <value>`: vote/unvote: guid of the poll message to update
- `--option-id <value>`: vote/unvote: UUID of the option to select
- `--option-index <value>`: vote/unvote: 1-based option number to select
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--no-comment`: do not echo the question as a caption after the poll
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg poll send --chat 'iMessage;-;+15551234567' --question 'Dinner?' --option 'Pizza' --option 'Sushi'`
- `imsg poll send --chat 'iMessage;-;+15551234567' --question 'Dinner?' --comment 'Vote by 5pm 🍽️' --option 'Pizza' --option 'Sushi'`
- `imsg poll send --chat 'iMessage;-;+15551234567' --reply-to ABCD --question 'Approve?' --option 'Yes' --option 'No'`
- `imsg poll vote --chat 'iMessage;-;+15551234567' --poll ABCD --option-id 1B2C-...`
- `imsg poll unvote --chat 'iMessage;-;+15551234567' --poll ABCD --option-index 1`

### tapback

Send a tapback reaction via the IMCore bridge

`imsg tapback` uses the bridge for reliability across macOS versions.
`imsg react` (AppleScript) remains for SIP-on machines.

Usage: `imsg tapback [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--message <value>`: target message guid
- `--kind <value>`: love|like|dislike|laugh|emphasize|question, or an emoji
- `--part <value>`: part index
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--remove`: remove this reaction instead of adding
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg tapback --chat 'iMessage;-;+15551234567' --message ABCD-EFGH --kind love`

### edit

Edit a sent message

Requires macOS 13+ (selector-probed at startup).

Usage: `imsg edit [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--message <value>`: target message guid
- `--new-text <value>`: replacement text
- `--bc-text <value>`: backwards-compat text shown to older clients (default: same as new-text)
- `--part <value>`: part index
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg edit --chat ... --message <guid> --new-text 'updated'`

### unsend

Retract a sent message

Requires macOS 13+ (selector-probed at startup).

Usage: `imsg unsend [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--message <value>`: target message guid
- `--part <value>`: part index
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg unsend --chat ... --message <guid>`

### delete-message

Delete a single message from a chat

Usage: `imsg delete-message [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--message <value>`: target message guid
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg delete-message --chat ... --message <guid>`

### notify-anyways

Force a notification for a message that was filtered/suppressed

Usage: `imsg notify-anyways [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--message <value>`: target message guid
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg notify-anyways --chat ... --message <guid>`

### chat-create

Create a new chat (1:1 or group)

Requires `imsg launch` (SIP-disabled, dylib injected). Vends handles for
each address, including previously uncontacted recipients, through the
active iMessage account. Every recipient must pass an IDS availability
check before the chat is created. Optionally sets a display name and sends an
initial message. Chat creation is currently iMessage-only; use
`imsg send --service sms` for SMS sends.

Usage: `imsg chat-create [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--addresses <value>`: comma-separated handles (phone or email)
- `--name <value>`: group display name
- `--text <value>`: initial message body
- `--service <value>`: iMessage (default)
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg chat-create --addresses '+15551234567,+15559876543' --name 'Crew' --text 'gm'`

### chat-name

Set a chat's display name

Usage: `imsg chat-name [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--name <value>`: new display name
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg chat-name --chat 'iMessage;+;chat0000' --name 'New Name'`

### chat-photo

Set or clear a group chat photo

Omit --file to clear the existing photo.

Usage: `imsg chat-photo [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--file <value>`: path to image (omit to clear)
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg chat-photo --chat 'iMessage;+;chat0000' --file ~/Downloads/g.jpg`

### chat-add-member

Add a participant to a group chat

Usage: `imsg chat-add-member [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--address <value>`: phone or email to add
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg chat-add-member --chat 'iMessage;+;chat0000' --address +15551234567`

### chat-remove-member

Remove a participant from a group chat

Usage: `imsg chat-remove-member [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--address <value>`: phone or email to remove
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg chat-remove-member --chat 'iMessage;+;chat0000' --address +15551234567`

### chat-leave

Leave a group chat

Usage: `imsg chat-leave [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg chat-leave --chat 'iMessage;+;chat0000'`

### chat-delete

Delete a chat from Messages.app

Usage: `imsg chat-delete [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg chat-delete --chat 'iMessage;-;+15551234567'`

### chat-mark

Mark a chat as read or unread

Usage: `imsg chat-mark [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--read`: mark as read
- `--unread`: mark as unread
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg chat-mark --chat ... --read`
- `imsg chat-mark --chat ... --unread`

### search

Search local Messages history

Searches the local chat.db, not the injected bridge. Use --match exact
for case-insensitive exact text matches; the default is contains.

Usage: `imsg search [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--query <value>`: search query (required)
- `--match <value>`: exact|contains (default contains)
- `--limit <value>`: maximum results (default 50)
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg search --query 'pizza tonight' --match contains`

### account

Show the active iMessage account, login, and aliases

The default mode reads the live account via the IMCore bridge (requires
`imsg launch`, SIP disabled). Use --local for a SIP-free listing of the
account login(s) recorded in local chat.db history. Local mode reflects
accounts observed in history rather than the live signed-in account; for
a single-account Mac these are equivalent.

Usage: `imsg account [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--local`: list accounts from local chat.db history (no SIP / bridge required)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg account`
- `imsg account --local`

### whois

Check whether a handle is reachable on iMessage

The default mode performs a live reachability check via the IMCore bridge
(requires `imsg launch`, SIP disabled). Use --local for a SIP-free check
that infers the preferred service from local chat.db history. Local mode
only resolves handles you already have message history with; unknown
handles report service "unknown".

Usage: `imsg whois [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--address <value>`: phone or email to check
- `--type <value>`: phone|email
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--local`: infer service from local chat.db history (no SIP / bridge required)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg whois --address +15551234567 --type phone`
- `imsg whois --address foo@bar.com --type email`
- `imsg whois --address foo@bar.com --local`

### nickname

Show contact-card / nickname info for a handle

The default mode reads the contact-card nickname the correspondent shared
over iMessage via the IMCore bridge (requires `imsg launch`, SIP disabled).

--local is a SIP-free alternative that returns YOUR local AddressBook
contact name for the handle. NOTE: this is a different datum — it is your
own contact label, not the iMessage-shared nickname/photo, which is only
available through the bridge.

Usage: `imsg nickname [options]`

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--address <value>`: phone or email
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `--local`: return local AddressBook contact name (no SIP; NOT the shared nickname)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg nickname --address +15551234567`
- `imsg nickname --address +15551234567 --local`

### name-photo

Inspect or share your Messages Name & Photo

Requires `imsg launch` (SIP disabled, dylib injected). `status` reads
whether Messages would offer Name & Photo sharing for the chat. `share`
explicitly sends your personal Name & Photo to every chat participant.

Usage: `imsg name-photo <action> [options]`

Arguments:
- `action`: status|share

Options:
- `--db <value>`: Path to chat.db (defaults to ~/Library/Messages/chat.db)
- `--chat <value>`: chat guid
- `--log-level, --logLevel <value>`: Set log level (trace|verbose|debug|info|warning|error|critical)
- `-v, --verbose`: Enable verbose logging
- `--json, -j, --json-output, --jsonOutput`: Emit machine-readable JSON output

Examples:
- `imsg name-photo status --chat 'iMessage;-;+15551234567'`
- `imsg name-photo share --chat 'iMessage;-;+15551234567'`
