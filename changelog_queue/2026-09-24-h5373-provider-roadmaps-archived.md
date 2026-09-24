# 2026-09-24 — H5373: docs/provider-roadmaps.md archived (roadmap verdict pass, E015 wave 1)

Verdict pass over the historical provider-roadmaps generation (GPT-5.5 /
Gemini 3.1 Pro / Claude Sonnet 4.6; banner-archived R2 since 2026-07-03):
file moved verbatim to `archive/provider-roadmaps.md`, old path carries a
one-line tombstone. Unminted-prose table = zero rows: the `google` and
`anthropic` adapters and CLI wiring are shipped (`src/ruwritingstyles/providers.py`,
H5097 PR #228, H5071 PR #227), and the cross-provider eval agenda (Gemini/
Claude rollout steps 2–5, 52-case eval set) is owned by the live
`docs/roadmap-2026-q3.md`, which already declares this file historical.
Uprava ROADMAP_INDEX.md row struck with the dated verdict (separate commit).
