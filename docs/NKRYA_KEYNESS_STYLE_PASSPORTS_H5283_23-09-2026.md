_Created: 23-09-2026 · Last updated: 23-09-2026_

# NKRYa keyness for the corpus-grounded style passports (H5283)

Executed by Claude Code, Opus 5.5 (`claude-opus-5-5`), 23-09-2026. The handoff is [H5283](https://github.com/gasyoun/Uprava/blob/main/handoffs/H5283-Opus_RuWritingStyles_nkrya-keyness-zaliznyak-first_23.09.26.md), and MG's rulings are in [GRILL_NKRYA_USES_ROUND2_DECISIONS_23-09-2026.md](https://github.com/gasyoun/SanskritLexicography/blob/master/RussianTranslation/docs/GRILL_NKRYA_USES_ROUND2_DECISIONS_23-09-2026.md). U7 ruled Zaliznyak first, then the four scholars. U6 made anachronism evidence advisory, and U9 keeps CI offline.

## What was measured

The procedure has five steps:

1. Each passport's source text in the private corpus (`RuWritingStyles-corpus/PDFtoTXT`) was tokenised.
2. The text was cleaned before counting. Pre-1918 spelling was modernised (ѣ→е, і→и, final ъ dropped). Stress marks were stripped. Sigla and abbreviations were skipped (`Чуд.`, `нов. 12`, «нов.»).
3. The text was lemmatised with pymorphy3. The top 30 content lemmas by in-text frequency were kept. The count excludes pronominal adjectives, names, light verbs and pronominal adverbs.
4. Each lemma's NKRYa frequency comes from the word portrait (`PORTRAIT_FREQUENCY`, main corpus), as ipm plus band 1–6. Here 1 means under 1 ipm and 6 means over 10 000 ipm.
5. Keyness is the log ratio, log₂(ipm in the text ÷ NKRYa ipm). The floor is 0.01 ipm when NKRYa has no portrait, which did not occur in this run. The rows are sorted by keyness.

A table «Лексическая подпись (НКРЯ)» was written into each passport. A Zaliznyak passport gets it after its «Лексика» section. A scholar passport gets it before «Примеры фраз». Each table sits between generated markers, so a re-run replaces it and never duplicates it. The reports are in [metadata/nkrya_keyness/](https://github.com/gasyoun/RuWritingStyles/tree/main/metadata/nkrya_keyness), and each one carries the source SHA-256 and its cache keys. The 185 API responses behind them are in [metadata/nkrya_cache/](https://github.com/gasyoun/RuWritingStyles/tree/main/metadata/nkrya_cache).

| Passport | Tokens | Top 5 by keyness (log₂) |
|---|---:|---|
| [zalizniak-imennoe](https://github.com/gasyoun/RuWritingStyles/blob/main/ClaudeStyles/zalizniak-imennoe-style.md) | 316 446 | словоформа +12.5, парадигма +9.5, ударение +8.9, склонение +8.9, падеж +8.8 |
| [zalizniak-novgorod](https://github.com/gasyoun/RuWritingStyles/blob/main/ClaudeStyles/zalizniak-novgorod-style.md) | 372 826 | словоформа +10.1, берестяной +9.4, морфология +9.1, грамота +7.9, графика +7.8 |
| [zalizniak-enklitiki](https://github.com/gasyoun/RuWritingStyles/blob/main/ClaudeStyles/zalizniak-enklitiki-style.md) | 98 344 | энклитика +17.5, постпозиция +16.3, препозиция +14.8, словоформа +11.1, сказуемое +9.6 |
| [zalizniak-udarenie](https://github.com/gasyoun/RuWritingStyles/blob/main/ClaudeStyles/zalizniak-udarenie-style.md) | 300 573 | акцентный +12.8, акцентуация +11.0, ударение +7.4, говор +6.3, древнерусский +6.0 |
| [bartold](https://github.com/gasyoun/RuWritingStyles/blob/main/ClaudeStyles/bartold-style.md) | 23 649 | уйгур +12.8, киргиз +11.3, упоминаться +9.9, киргизский +9.5, каган +9.4 |
| [turaev](https://github.com/gasyoun/RuWritingStyles/blob/main/ClaudeStyles/turaev-style.md) | 85 703 | папирус +10.4, египетский +7.3, гробница +7.3, жрец +6.7, надпись +6.2 |
| [krachkovskij](https://github.com/gasyoun/RuWritingStyles/blob/main/ClaudeStyles/krachkovskij-style.md) | 5 409 | автобиография +8.5, эмир +8.4, арабский +7.6, аллах +7.5, стоянка +7.3 |
| [golenishchev](https://github.com/gasyoun/RuWritingStyles/blob/main/ClaudeStyles/golenishchev-style.md) | 1 555 | папирус +11.3, шрифт +9.4, археологический +7.9, покойный +7.5, рай +6.8 |

The other five Zaliznyak passports (`method`, `ocherk`, `shkolnikov_1`, `slovo`, `zametki`) have no table. Their texts are not among the four named in the handoff, so they are left for a later pass.

## Scrutiny evidence

`rws scrutiny <run> --nkrya offline|live` lists archaic-looking words in the prompt with NKRYa evidence. Candidates are pre-reform spellings, a seed list of Church-Slavonic function words, and out-of-dictionary forms. For each one the prompt shows the ipm across all periods, the ipm in the 1800–1899 slice, and a hint. A word used at least twice as often in 1800–1899 as across the whole corpus is marked `19th-century-skewed`. The slice holds 82 049 244 words, taken from `subcorpStats` in the response. With `--execute`, every `anachronism` finding gets `nkrya_evidence` for its `term`, and severity and confidence are never changed. On the fixture ([tests/fixtures/scrutiny_nkrya/](https://github.com/gasyoun/RuWritingStyles/tree/main/tests/fixtures/scrutiny_nkrya)) only `сей` is skewed: 490 ipm across all periods against 1191 ipm in 1800–1899, so ×2.4. `дабы` (×1.4) and `оный` (×1.9) stay below the threshold, because the all-periods rate already includes the 19th century. A modern-only baseline would sharpen this, but it would cost one more request per word.

## Caveats (what would change a number)

1. **Reflexive verbs may be over-keyed.** NKRYa gives `упоминаться` only 1.57 ipm, which is probably folded into `упоминать` by its portraits. So Bartold's +9.9 for it is likely inflated.
2. **The two short texts are thin.** Golenishchev has 1 555 tokens, and its top 30 includes lemmas counted only 3 times. Krachkovskij has 5 409 tokens, with at least 9 counts per lemma. Treat those two tables as indicative.
3. **Ударение 2019 is an accent dictionary.** Its lemma list reflects the entries (город, земля, гора) as much as Zaliznyak's metalanguage. The extraction encodes stress as `\x01`/`\x02` bytes inside words, and these are stripped before tokenising.
4. **Lemmatisation is pymorphy3's first parse, without disambiguation.** The noise it leaves shows up as rare lemmas with implausibly high keyness. Such rows should be read against the source.

## How to reproduce

```bash
python scripts/nkrya_keyness.py --all --offline
```

```bash
python -m pytest -q tests/test_nkrya_evidence.py
```

Both commands need the `nkrya` extra (`pip install -e .[nkrya]`) and the private corpus beside the repo. The test also runs in CI without the corpus. It checks every committed ipm against the committed cache and every cache filename against its request hash.

_Гасунс_
