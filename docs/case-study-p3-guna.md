# P3 — real full-article run on DeepSeek (case study)

First end-to-end run of a **full-length** article through the agentic pipeline on a real
provider. Draft: [`examples/input/lexicography-guna.md`](../examples/input/lexicography-guna.md)
(~12.1k chars / ~22k with markup, Russian, Sanskrit lexicography of *guṇa*, for *Вестник
СПбГУ. Востоковедение*). Council: **`--council sanskrit`** (the F1 panel) on
`deepseek-chat`. Grading key: [`p3-seed-key.md`](p3-seed-key.md).

## Headline: all 3 seeded problems caught, revision stayed proportionate

| Seed | Caught? | By | Finding type |
|---|---|---|---|
| 1 — fabricated IE etymology (§2, p016) | ✅ | toporov-etym (major), + zaliznyak-method | `unsupported_sanskrit_etymology` + `missing_source` |
| 2 — missing IAST on *vṛddhi*/*sandhi* (§4) | ✅✅ | deterministic `translit_lint` (named both planted terms) + toporov-etym | `missing_iast_on_first_mention` |
| 3 — PW←Apte anachronism (§3, p019) | ✅ | tronsky-readings + zaliznyak-method | `unsupported_reading` + `logical_inconsistency` |

**3 / 3 detected**, each at the correct span, with on-target finding types and genuine
explanations.

### Seed 1 — the etymology refutation is real expertise, not pattern-matching

toporov-etym (DeepSeek) didn't just flag the etymology as "unsupported" — it produced a
correct comparative-linguistic counter-argument:

> «Утверждение о восхождении слова *guṇa* к ИЕ корню *gʷenǝ-* «вить, скручивать» с
> соответствиями лат. *funis* и греч. *χορδή* ненадёжно. Во-первых, лат. *funis* обычно
> возводят к ИЕ *bʰendʰ-/*bʰondʰ-* (связывать), а не к *gʷenǝ-*; соответствие *gʷenǝ- > лат.
> *f[unis]*…»

The model **knew the actual etymology of *funis*** (← *bʰendʰ-*) and used it to dismantle
the planted false correspondence. This is the single most encouraging signal in the run:
on the project's core subject, the council's judgement holds up.

### Seed 3 — caught as "illogical/unsupported," not literally "anachronism"

The PW(1855–1875)←Apte(1890) impossibility was flagged at the right paragraph by
zaliznyak-method as `logical_inconsistency` and tronsky-readings as `unsupported_reading`,
rather than a literal `anachronistic_sanskrit_period`. The *judgement* is correct (the
claim contradicts the dates in the bibliography); only the label differs. Acceptable.

## Two honest findings beyond the seeds

1. **The draft wasn't as clean as intended.** The deterministic linter caught the two
   planted terms (*vṛddhi*, *sandhi*) **plus** two I left un-IAST'd by accident (*sūtra*,
   *vyākaraṇa*) and a *guṇa*/*гуна* inconsistency. The tool surfaced real omissions the
   author missed — exactly its job.
2. **Revision is proportionate on real-length text — the benchmark's "over-rewrite"
   alarm was a small-doc artifact.** On this full article the revision applied 16 targeted
   changes: **char-delta 0.18, changed-line 0.22** — well inside the gold caps (0.50 / 0.75)
   that the tiny ~500-char benchmark docs blew through. The over-rewriting in
   [`benchmark.md`](benchmark.md) is now understood as ratio-sensitivity on short inputs,
   not a general defect. (Still worth tightening for short notes.)

## Other observations

- **No false-positive storm.** elizarenkova-veda returned 0 findings (correct — this is not
  a Vedic text); the others returned 3–5 each on a 22k-char article. Several non-seed
  findings are legitimate (the draft is deliberately light on inline citations, which
  tronsky-readings/zaliznyak-method flag as `missing_source`/`missing_apparatus`).
- **Findings are well-explained.** Each carries `finding` (prose), `suggestion`, `severity`,
  `confidence` — DeepSeek populated them substantively, in Russian.
- **Verification verdict:** `needs_human_review` (12 warnings) — an appropriate status for a
  draft with real issues; within the gold protocol's allowed set.
- **Cost/latency:** full 6-style council + all stages on a 22k-char doc, `deepseek-chat`,
  completed in ~10–12 min, well under $1.

## Verdict

On a real full-length article in the project's core domain, the DeepSeek-powered `sanskrit`
council **caught every planted problem with correct, well-argued findings**, surfaced extra
real omissions, kept revision proportionate, and did not flood the draft with noise. This is
the first concrete evidence that the pipeline produces philologically credible reviews on
real material — the strongest result of the "measure quality" workstream so far.

## Addendum — vestnik-spbu journal-compliance pass

The P3 run targeted *Вестник СПбГУ* but skipped its journal profile. Re-running with
`--journal vestnik-spbu` (a new flag — no project dir needed) produces the compliance
section, which now **checks** (not just echoes) the journal's requirements:

```
## Соответствие журналу: Вестник СПбГУ. Востоковедение и африканистика
- Объем: 12114 / 40000 знаков — OK
- Список литературы: GOST-R-7.0.100-2018
- Транслитерация: IAST
- Аннотация (ru, en): ru ✓, en ⚠ нет
- Ключевые слова (ru, en): ru ✓, en ⚠ нет
```

It correctly flags that the draft has a Russian abstract and keywords but is **missing the
English abstract and keywords** the journal requires — a real, actionable submission gap,
caught deterministically (no provider call).
