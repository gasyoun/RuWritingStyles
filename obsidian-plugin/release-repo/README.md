_Created: 24-08-2026 · Last updated: 05-09-2026_

# RuWritingStyles for Obsidian

Inline philological checks for Russian Sanskrit-studies notes: IAST transliteration
linting and journal-compliance hints, ported from the
[RuWritingStyles](https://github.com/gasyoun/RuWritingStyles) engine. Runs fully
locally — no server, no API key.

> This repository is the **publish mirror** for the Obsidian community-plugin
> directory and [BRAT](https://github.com/TfTHacker/obsidian42-brat). Development
> happens in the monorepo at
> [gasyoun/RuWritingStyles/obsidian-plugin](https://github.com/gasyoun/RuWritingStyles/tree/main/obsidian-plugin);
> this repo is regenerated on each release by
> [tools/sync_plugin_release_repo.py](https://github.com/gasyoun/RuWritingStyles/blob/main/tools/sync_plugin_release_repo.py).
> File issues and PRs against the monorepo, not here.

## Install

### BRAT (beta)

1. Install the [BRAT](https://github.com/TfTHacker/obsidian42-brat) community plugin.
2. BRAT → *Add a beta plugin* → enter this repository's URL.
3. Enable **RuWritingStyles** under Settings → Community plugins.

BRAT reads this repo's **latest release** (bare `x.y.z` tag), which is exactly what
this dedicated repo publishes — unlike the monorepo, whose releases are prefixed
`obsidian-v*` and interleaved with engine releases.

### Manual

Download `main.js`, `manifest.json`, and `styles.css` from the
[latest release](../../releases/latest) into
`<vault>/.obsidian/plugins/ruwritingstyles/`, then enable the plugin.

## What it does

- Flags Latin/Cyrillic transliteration that is not valid IAST and offers a quick-fix.
- Surfaces journal-compliance hints (per configurable journal profile).
- Uses the same term dictionary and journal profiles as the Python engine, so a note
  that lints clean here lints clean in the pipeline.

## Roadmap & source

Everything upstream — engine, tests, roadmap — lives in the monorepo:
[gasyoun/RuWritingStyles](https://github.com/gasyoun/RuWritingStyles)
(plugin roadmap:
[docs/roadmap-2026-q3.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/roadmap-2026-q3.md)).

## License

Apache-2.0.

_Dr. Mārcis Gasūns_
