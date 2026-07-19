# Аудит применения решений: адъюдикация vedic-classical-anachronism-r02

_Created: 19-07-2026 · Last updated: 19-07-2026_

Лист: `review-vedic-r02-adjudication` (сгенерирован 11-07-2026, Claude Fable 5
(`claude-fable-5`), H588) · прогон `20260703-h073gov-vedic-classical-anachronism-r02` ·
решение автора зафиксировано 19-07-2026 в
[`evals/annotation/decisions.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/annotation/decisions.json).
Применение: Claude Opus 4.8 (`claude-opus-4-8`), 19-07-2026.

## Счёт по вердиктам

| Вердикт | Кол-во | Позиции |
|---|---:|---|
| Принято (`substantive_detection`) | 1 | единственный вопрос листа |
| Отклонено | 2 | `scorer_stands`, `add_alias` (невыбранные альтернативы) |
| Отложено | 0 | — |

Лист был одновопросным (адъюдикация одного расхождения разметки), а не поитемным
approve/reject/defer — поэтому сверка ID с манифестом неприменима; идентификация листа
выполнена по полям `sheet` + `run` в `decisions.json`.

## Что именно постановлено

Зачесть **содержательную** детекцию и репортировать **два слоя раздельно**, не выбирая
между ними:

| Слой | Что измеряет | Итог по 25 прогонам |
|---|---|---:|
| Слой 1 — механический скорер | детекция при совпадении канонического типа/псевдонима | 24/25 = 0.96 |
| Слой 2 — золотая разметка + адъюдикация | детекция по существу, независимо от метки | 25/25 = 1.00 |

`accepted_finding_aliases` под конкретный прогон **не расширены** — вариант `add_alias`
отклонён как прямо не рекомендованный протоколом.

## Куда применено

| Файл | Что изменено |
|---|---|
| [`docs/methodology-paper-draft.ru.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/methodology-paper-draft.ru.md) | §4.6 — блок «Адъюдикация (19-07-2026)» + двухслойная таблица; §7 (раскрытие ИИ) и «Открытые задачи» — расхождение больше не «ждёт решения» |
| [`docs/benchmark.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/benchmark.md) | «Слой 2 (2026-07-11)» — заголовок и абзац расхождения несут вердикт и оба числа |
| [`docs/paper-pack/cover-letter.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/paper-pack/cover-letter.md) | 0.96 переформулировано как «при строгом совпадении типа; 25/25 по существу» |
| [`docs/paper-pack/venue-checklist.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/paper-pack/venue-checklist.md) | пункт двух-разметчиковой разметки — адъюдикация закрыта, ссылка на этот аудит |
| [`evals/GOLD_PROTOCOL.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/GOLD_PROTOCOL.md) | новое правило «Двухслойный репортинг» + схема блока `adjudication` |
| [`evals/annotation/gold-annotation-vedic-classical-anachronism.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/annotation/gold-annotation-vedic-classical-anachronism.json) | добавлен блок `adjudication` (разметчик C — человек, дата, вердикт, эффект) |
| [`docs/roadmap-2026-q3.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/roadmap-2026-q3.md) | O1 «Адъюдикация vedic-r02» → ✅ |

Сам лист `review-vedic-r02-adjudication.html` удалён после применения (закрытый лист рядом
с живыми провоцирует повторное голосование); `decisions.json` сохранён как аудит-след.

## Остаток — то, что вердиктом не закрывается

Заметка автора при голосовании содержит три вещи за пределами самого вопроса:

1. **Претензия к формату гейтинга.** «Голосование с одним вопросом должно быть в чате, а
   не отдельной HTML-страницей», и листу не хватало примеров и явного описания последствий
   каждого варианта. Отражено в правиле генерации листов (см. память
   `feedback_single_question_vote_in_chat`): одновопросный выбор задаётся в чате;
   HTML-лист — для батчей от ~5 позиций, и каждая опция обязана нести «к чему это
   приведёт».
2. **Ārṣa как узаконенное отклонение (научный вопрос).** Язык риши/эпоса (*ārṣa prayoga*)
   традиционно легитимирует отклонения от Панини — например, в «Рамаяне». Это ставит под
   вопрос сам золотой кейс `vedic-classical-anachronism`: часть «анахронизмов» может быть
   не ошибкой, а признанной эпической нормой. Кандидат в ограничения §5 статьи и в правку
   рубрики кейса.
3. **Возможен ли парсинг комментариев к МБх/Рамаяне** ради базы всех подобных случаев,
   уже описанных традиционными комментаторами. Прямо смыкается с
   [CommentaryStrategies](https://github.com/gasyoun/CommentaryStrategies) и с
   `commentary-layer-mix`; вопрос заведён в
   [`Uprava/QUESTIONS_LOG.md`](https://github.com/gasyoun/Uprava/blob/main/QUESTIONS_LOG.md).

Пункты 2 и 3 — новая работа, а не применение вердикта; они не смешаны с этим коммитом.

_Dr. Mārcis Gasūns_
