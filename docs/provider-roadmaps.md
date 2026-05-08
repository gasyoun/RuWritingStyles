# Провайдерные версии roadmap

Этот документ описывает, как тот же агентный план RuWritingStyles раскладывается на OpenAI GPT-5.5, Google Gemini 3.1 Pro и Anthropic Claude Sonnet 4.6. Основной проектный контракт остается одинаковым: стили выдают структурированные замечания, совет стилей обсуждает конкретные `span_id`, синтезатор применяет согласованные правки, проверяющий защищает исходный смысл.

## Общее правило

Провайдер не должен менять протокол проекта. Меняться могут только:

- ID модели;
- параметры reasoning/thinking;
- способ tool calling;
- поддержка structured outputs;
- лимиты контекста и вывода;
- стоимость и latency;
- fallback-модель для дешевых массовых задач.

Все провайдерные различия должны быть спрятаны в provider adapter. Файлы стилей, JSON-схемы замечаний и `council.json` должны оставаться переносимыми.

Общий execution layer уже учитывает rate-limit поведение провайдеров: сначала используется стандартный `Retry-After`, затем OpenAI `x-ratelimit-reset-*` и Anthropic `anthropic-ratelimit-*-reset` для исчерпанных лимитов. Для Gemini фиксируется тот же общий механизм `Retry-After`, если сервис возвращает этот заголовок. Каждый запуск также пишет retry telemetry в `provider.log.jsonl`: `retry_count`, `retry_delay_seconds` и `retry_statuses`.

## OpenAI GPT-5.5

Основной маршрут проекта.

| Часть системы | Модель | Режим |
|---|---|---|
| Архитектура, схемы, протоколы | `gpt-5.5` | reasoning `xhigh` |
| Реализация сложного кода | `gpt-5.5` | reasoning `high` |
| Одиночный style review | `gpt-5.5` | reasoning `medium` |
| Council round | `gpt-5.5` | reasoning `high` |
| Синтезатор | `gpt-5.5` | reasoning `high` или `xhigh` |
| Verifier | `gpt-5.5` | reasoning `xhigh` |
| Роутинг и smoke tests | `gpt-5.4-mini` | reasoning `low` |

Причина выбора: официальная документация OpenAI рекомендует `gpt-5.5` как стартовую модель для complex reasoning и coding, а также Responses API для reasoning, tool-calling и multi-turn сценариев.

## Google Gemini 3.1 Pro

Альтернативный маршрут для Google-стека.

По официальным Google docs актуальный API ID: `gemini-3.1-pro-preview`. Для workflow с bash и custom tools есть отдельный endpoint `gemini-3.1-pro-preview-customtools`. Модель находится в preview, поэтому перед production-запуском нужно повторно проверить ID и лимиты.

| Часть системы | Модель | Режим |
|---|---|---|
| Архитектура, схемы, протоколы | `gemini-3.1-pro-preview` | Thinking High |
| Реализация с custom tools/bash | `gemini-3.1-pro-preview-customtools` | Thinking High |
| Одиночный style review | `gemini-3.1-pro-preview` | Thinking Medium |
| Council round | `gemini-3.1-pro-preview` | Thinking High |
| Синтезатор | `gemini-3.1-pro-preview` | Thinking High |
| Verifier | `gemini-3.1-pro-preview` | Thinking High |

Сильные стороны для RuWritingStyles:

- длинный контекст до 1,048,576 input tokens;
- text, image, video, audio и PDF input;
- structured outputs;
- function calling;
- code execution;
- search grounding;
- URL context;
- отдельный customtools endpoint для агентной разработки.

Риски:

- preview-статус;
- возможные изменения ID и поведения;
- нужно отдельно проверить совместимость structured outputs с внутренними JSON-схемами проекта;
- provider adapter не должен протаскивать Google-специфичные параметры в общий протокол.

Порядок внедрения Gemini-ветки:

1. Добавить `google` provider adapter. Стартовый HTTP-адаптер уже подключен к CLI как `--provider google`.
2. Поддержать `gemini-3.1-pro-preview` и `gemini-3.1-pro-preview-customtools`.
3. Прогнать один и тот же eval-набор на OpenAI и Gemini.
4. Сравнить JSON-валидность, полноту замечаний, сохранность `span_id`.
5. Разрешить Gemini как альтернативный backend только после прохождения verifier eval.

## Anthropic Claude Sonnet 4.6

Альтернативный маршрут для Anthropic-стека.

По официальным Anthropic docs API alias: `claude-sonnet-4-6`. Модель описывается как лучшее сочетание скорости и интеллекта, поддерживает text/image input, text output, extended thinking, adaptive thinking, 1M context window и 64K max output.

| Часть системы | Модель | Режим |
|---|---|---|
| Архитектура, схемы, протоколы | `claude-sonnet-4-6` | adaptive thinking |
| Реализация сложного кода | `claude-sonnet-4-6` | extended thinking |
| Одиночный style review | `claude-sonnet-4-6` | adaptive thinking |
| Council round | `claude-sonnet-4-6` | extended thinking |
| Синтезатор | `claude-sonnet-4-6` | extended thinking |
| Verifier | `claude-sonnet-4-6` | extended thinking |

Сильные стороны для RuWritingStyles:

- хорошее сочетание скорости и качества;
- длинный контекст 1M tokens;
- сильные документные и knowledge-work сценарии;
- пригодность для параллельных reviewer agents;
- полезен как независимый verifier для OpenAI/Gemini outputs.

Риски:

- для самых тяжелых задач Anthropic рекомендует Opus 4.7, поэтому Sonnet 4.6 лучше рассматривать как balanced-ветку, а не максимальный ceiling;
- нужно отдельно нормализовать thinking-параметры;
- нужно проверить, насколько строго модель соблюдает JSON-схемы без дополнительного repair-шагa;
- provider adapter не должен смешивать Claude-specific thinking с общим `reasoning` полем.

Порядок внедрения Claude-ветки:

1. Добавить `anthropic` provider adapter. Стартовый HTTP-адаптер уже подключен к CLI как `--provider anthropic`.
2. Поддержать `claude-sonnet-4-6` как balanced backend.
3. Прогнать style review и council eval на текущем MVP-наборе из `styles/manifest.yml`.
4. Использовать Claude как cross-provider verifier для документов, сгенерированных OpenAI или Gemini.
5. Сравнить стоимость, latency и долю JSON repair.

## Cross-provider eval

Каждый провайдер должен пройти один и тот же набор. Базовый manifest сейчас содержит 33 eval-кейса; для дорогих real-provider проверок можно запускать меньший tagged subset, но promoted baseline должен быть сопоставим с полным набором.

| Eval | Что проверяет |
|---|---|
| `schema_validity` | Все ответы проходят JSON Schema. |
| `span_grounding` | Замечания привязаны к существующим `span_id`. |
| `finding_relevance` | Замечания относятся к компетенции выбранного стиля. |
| `council_stability` | Ответы стилей не превращаются в свободный диалог. |
| `revision_fidelity` | Синтезатор сохраняет исходный смысл. |
| `verifier_strictness` | Проверяющий ловит неподтвержденные добавления. |

До прохождения этих eval-ов провайдерная ветка считается экспериментальной.

## Официальные источники

- OpenAI: https://developers.openai.com/api/docs/models
- OpenAI GPT-5.5: https://developers.openai.com/api/docs/guides/latest-model
- OpenAI Agents SDK: https://developers.openai.com/api/docs/guides/agents
- OpenAI API rate limits: https://platform.openai.com/docs/guides/rate-limits
- Google Gemini 3.1 Pro Preview: https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview
- Google Gemini API rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Google DeepMind Gemini 3.1 Pro model card: https://deepmind.google/models/model-cards/gemini-3-1-pro/
- Anthropic Claude models overview: https://platform.claude.com/docs/en/about-claude/models/overview
- Anthropic Claude Sonnet: https://www.anthropic.com/claude/sonnet
- Anthropic API rate limits: https://docs.anthropic.com/en/api/rate-limits
