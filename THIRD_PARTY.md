# Upstream reference and notices

`omsg_bridge/commands.json` contains descriptions and option metadata derived from
`imsg v0.19.1`'s `imsg completions llm`. imsg is MIT licensed, copyright (c) 2025
Peter Steinberger. The MIT license grant and disclaimer in `LICENSE` also apply
to this derived material; upstream: https://github.com/openclaw/imsg/blob/v0.19.1/LICENSE.

Reference binary: https://github.com/openclaw/imsg/releases/download/v0.19.1/imsg-macos.zip
SHA-256: `adb176c1b00aa1e8abe3b5fe640fc0d84586282c5eac1b91aa328ef3a08acf31`
Release tag: `aea7c22c2570d0fef883b34f077cc44e1bf2a508`.
Source inspection also covered `31171997d03da82ef825777d351235ee21b357c9`.
The release contains **38** commands. The downloaded reference was used only for
`--version`, help and completions; no personal database access or mutations.

Swagger UI assets are served locally from `swagger-ui-bundle` (Apache-2.0;
license included in that dependency). No CDN receives API credentials or message data.

To refresh metadata after reviewing a new upstream release:

```sh
imsg completions llm > /tmp/imsg-cli-reference.md
python3 scripts/import_catalog.py /tmp/imsg-cli-reference.md omsg_bridge/commands.json
```

Review the inventory count, descriptions, flags versus value options, positional
arguments and JSON behavior. Update provenance here and in the importer. Runtime
aliases such as `--json-output` are normalized: the HTTP API accepts canonical
long names and always controls JSON output itself.
