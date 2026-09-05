_Created: 02-09-2026 · Last updated: 05-09-2026_

# Run Report: phase1-council-example

## Input

- Source: `examples/input/article-snippet.md`
- Segment count: 5

## Segment Types

- heading: 3
- paragraph: 2

## Pipeline Status

| Step | Status | Artifact |
| --- | --- | --- |
| review | completed | 4 review file(s) |
| council | completed | council.json |
| revision | completed | revision.json |
| verification | needs_human_review | verification.json |

## Reviews

| Style | Status | Findings | Summary |
| --- | --- | --- | --- |
| kazanskiy-korpus | completed | 1 | Mock review completed for kazanskiy-korpus. |
| lidova-commentary | completed | 1 | Mock review completed for lidova-commentary. |
| tronsky-readings | completed | 1 | Mock review completed for tronsky-readings. |
| zalizniak-ocherk | completed | 1 | Mock review completed for zalizniak-ocherk. |

## Findings

| Style | Severity | Span | Finding | Suggestion | Confidence |
| --- | --- | --- | --- | --- | --- |
| kazanskiy-korpus | note | p003 | Mock provider placeholder finding for pipeline validation. | Replace the mock provider with a real provider to get substantive review findings. | 0.1 |
| lidova-commentary | note | p003 | Mock provider placeholder finding for pipeline validation. | Replace the mock provider with a real provider to get substantive review findings. | 0.1 |
| tronsky-readings | note | p003 | Mock provider placeholder finding for pipeline validation. | Replace the mock provider with a real provider to get substantive review findings. | 0.1 |
| zalizniak-ocherk | note | p003 | Mock provider placeholder finding for pipeline validation. | Replace the mock provider with a real provider to get substantive review findings. | 0.1 |

## Provider Log

| Task | Provider | Model | Status | Duration ms | Retries | Retry delay s |
| --- | --- | --- | --- | --- | --- | --- |
| review | mock | gpt-5.5 | completed | 45 | 0 | 0.0 |
| review | mock | gpt-5.5 | completed | 55 | 0 | 0.0 |
| review | mock | gpt-5.5 | completed | 53 | 0 | 0.0 |
| review | mock | gpt-5.5 | completed | 59 | 0 | 0.0 |
| council | mock | gpt-5.5 | completed | 49 | 0 | 0.0 |
| revision | mock | gpt-5.5 | completed | 42 | 0 | 0.0 |
| verification | mock | gpt-5.5 | completed | 2661 | 0 | 0.0 |
| syntax_assessment | mock | gpt-5.5 | completed | 48 | 0 | 0.0 |

## Council

Status: `completed`

| Finding | Decision | Reason |
| --- | --- | --- |
| finding-001 | informational | Mock council keeps placeholder findings informational. |
| finding-001 | informational | Mock council keeps placeholder findings informational. |
| finding-001 | informational | Mock council keeps placeholder findings informational. |
| finding-001 | informational | Mock council keeps placeholder findings informational. |

## Methodological Bias Audit
- **Bias Score**: 1/10
- **Primary Bias**: NONE

**Critique**: Mock critique.

| Severity | Issue | Recommendation |
| --- | --- | --- |
| note | Mock bias audit: council is impartial. | Maintain methodological diversity. |

## Revision

- Status: `completed`
- Revised document: `runs/phase1-council-example/revised.md`
- Diff: `revision.diff`
- Applied changes: 0
- Unresolved items: 1

## Verification

- Status: `needs_human_review`
- Passed checks: 1
- Warnings: 1

| Span | Message |
| --- | --- |
|  | Mock provider cannot verify factual fidelity; run a real provider for substantive verification. |

## Scholarly Grounding (Citations)
- **Status**: `completed`
- **Verified Citations**: 4
- **Not in Bibliography**: 0

### Verified Sources
| Citation | Source Collection |
| --- | --- |
| Erman 2009 |  |
| Kazansky 2025 |  |
| Paribok 2011 |  |
| Zaliznyak 2004 |  |


## Соответствие журналу: Вопросы языкознания

- Объем: 1250 / 60000 знаков — OK
- Список литературы: author-year-brackets
- Транслитерация: IAST
- Аннотация (ru, en): ru ✓ (55/250 слов — OK), en ⚠ нет
- Ключевые слова (ru, en): ru ⚠ нет, en ⚠ нет

## Транслитерация санскрита (детерминированный линтер)

Схемы в тексте: iast

Замечаний нет.

_Dr. Mārcis Gasūns_
