# Releasing the RuWritingStyles Obsidian plugin

The plugin lives in this subdirectory of the RuWritingStyles monorepo. The three
files Obsidian actually loads are **`main.js`**, **`manifest.json`**, and
**`styles.css`** (`main.js` is the esbuild bundle; it is git-ignored and produced
by `npm run build`).

## Versioning

Keep these three in sync (all currently `0.1.0`):

- `manifest.json` → `version`
- `versions.json` → maps the plugin version to the minimum Obsidian version
- `package.json` → `version`

## Cutting a release (automated)

A GitHub Actions workflow
([`.github/workflows/release-obsidian-plugin.yml`](https://github.com/gasyoun/RuWritingStyles/blob/main/.github/workflows/release-obsidian-plugin.yml))
builds + tests the plugin and attaches `main.js`, `manifest.json`, `styles.css`,
and a zip to a GitHub release.

```sh
# 1. bump the version in manifest.json, versions.json, package.json, commit it
# 2. tag with the `obsidian-v` prefix (suffix MUST equal the manifest version)
git tag obsidian-v0.1.0
git push origin obsidian-v0.1.0
```

The `obsidian-v` prefix keeps plugin releases distinct from any engine versioning
in this monorepo; the workflow fails if the tag suffix ≠ `manifest.json` version.
`workflow_dispatch` runs a build+test smoke without releasing.

## Installing

### Manual (works today)

Copy `main.js`, `manifest.json`, `styles.css` from a release (or a local
`npm run build`) into `<vault>/.obsidian/plugins/ruwritingstyles/`, then enable
**RuWritingStyles** under Settings → Community plugins.

### BRAT (beta)

[BRAT](https://github.com/TfTHacker/obsidian42-brat) installs a plugin from a repo's
latest GitHub release assets. Once an `obsidian-v*` release exists, add the repo in
BRAT. **Caveat:** BRAT reads the repo's *latest* release; in a monorepo that also
publishes engine releases this is fragile, and BRAT/official tooling expect the
release tag to equal the bare manifest version. For a reliable beta channel, prefer
the dedicated-repo path below.

## Official community submission (needs a decision)

Submitting to the Obsidian **community plugins** directory (a PR to
[`obsidianmd/obsidian-releases`](https://github.com/obsidianmd/obsidian-releases))
requires the plugin repo to have **`manifest.json` at its root** and releases tagged
with the **bare version** (`0.1.0`, no prefix), one plugin per repo. That is not
possible from this monorepo subdirectory.

**Recommended:** publish from a **dedicated repo**, e.g. `gasyoun/ruwritingstyles-obsidian`:

1. Create the repo; mirror this folder's contents to its root (`manifest.json`,
   `versions.json`, `main.js` via its own build, `styles.css`, `README.md`, source).
2. Keep this monorepo folder as the dev source; sync to the dedicated repo on release
   (a small `git subtree`/rsync step, or copy-on-release).
3. In the dedicated repo, tag bare `0.1.0` and let its release workflow attach the
   three files.
4. Open the submission PR per the
   [plugin guidelines](https://docs.obsidian.md/Plugins/Releasing/Submit+your+plugin).

These steps need your GitHub identity and a structural decision, so they are left as
deliberate manual actions — they are **not** automated here.

## Pre-submission checklist

- [ ] `npm run build` is green and `main.js` is produced
- [ ] `npm test` is green (36 tests)
- [ ] versions aligned across `manifest.json` / `versions.json` / `package.json`
- [ ] `manifest.json` `description` ≤ ~250 chars, no "Obsidian"/"plugin" in the name
- [ ] `isDesktopOnly` correct (this plugin is `false` — pure TS, mobile-capable)
- [ ] tested in a real vault (load, lint a note, quick-fix, journal dropdown)
- [ ] (official) dedicated repo with root `manifest.json` + bare-version tag
