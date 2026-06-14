# Документация RuWritingStyles — карта

Указатель по документации. Начните сверху (для пользователя), ниже — материалы для
рецензентов кода и разработчиков.

## Начать (пользователю)

- [`QUICKSTART.ru.md`](QUICKSTART.ru.md) — установка → ключ DeepSeek → первый прогон за
  пять шагов.
- [`USE_CASES.ru.md`](USE_CASES.ru.md) — рабочие сценарии: этимология, подготовка к
  журналу, ведийский период, самаса, сверка словарей, транслитерация. Команда → что вернёт.
- [`cli.md`](cli.md) — полный справочник команд `rws`.
- [`STYLE_GALLERY.ru.md`](STYLE_GALLERY.ru.md) — галерея всех 39 стилей со ссылками на
  `.md` для использования как Claude Custom Style (открыть → скопировать → вставить).

## Доверие к результату (доказательная база)

- [`benchmark.md`](benchmark.md) — реальная точность на золотых санскритских кейсах
  (DeepSeek): детекция 5/5, где расходится с протоколом, оговорка о недетерминизме.
- [`case-study-p3-guna.md`](case-study-p3-guna.md) — разбор реальной статьи (≈22k знаков):
  Совет поймал все три заложенные ошибки; проверка под Вестник СПбГУ.
- [`p3-seed-key.md`](p3-seed-key.md) — ключ к заложенным проблемам этого кейса.
- [`case-study-phase1.md`](case-study-phase1.md) — детерминированный слой на реальной статье.
- [`../evals/GOLD_PROTOCOL.md`](../evals/GOLD_PROTOCOL.md) — протокол золотого стандарта
  (≥2 разметчика, согласие, метрики).

## Цитирование и использование ИИ

- [`../CITATION.cff`](../CITATION.cff) — как цитировать («Cite this repository»).
- [`AI_DISCLOSURE.md`](AI_DISCLOSURE.md) — готовые формулы декларации ИИ для статьи (рус./англ.).
- [`../metadata/dublin-core.xml`](../metadata/dublin-core.xml) — метаданные паспортов (DCMI).

## Как это устроено

- [`philological-feedback-loop.md`](philological-feedback-loop.md) — идея «Совета» и петли
  обратной связи.
- [`agent-protocol.md`](agent-protocol.md) — протокол: как стили проверяют документ,
  отвечают друг другу, синтезируют правку.
- [`style-contract.md`](style-contract.md) — контракт паспорта стиля.
- [`roadmap-sanskrit-dh.md`](roadmap-sanskrit-dh.md) — дорожная карта Sanskrit/DH (фазы 0–4).

## Рецензии (для рецензентов кода)

- [`security-review-2026-06.md`](security-review-2026-06.md) — обзор веб-поверхности
  (S1–S7 закрыты; default-deny авторизация; путь к публичному развёртыванию).
- [`prompt-fidelity-review-2026-06.md`](prompt-fidelity-review-2026-06.md) — верность
  паспортов и сохранение голоса стиля по конвейеру.
- [`data-schema-review-2026-06.md`](data-schema-review-2026-06.md) — слой данных и схем.
- [`architecture-review-2026-06.md`](architecture-review-2026-06.md) — архитектура конвейера.
- [`methodology-paper-outline.md`](methodology-paper-outline.md) — скелет методологической
  статьи о проекте (для публикации).

## Разработка и развёртывание

- [`obsidian-plugin-plan.md`](obsidian-plugin-plan.md) — план плагина для Obsidian:
  MVP с лёгкими детерминированными проверками (порт линтера на TypeScript), полный
  аудит «Совета» через локальный FastAPI как Tier 2.
- [`deployment.md`](deployment.md), [`onboarding.md`](onboarding.md),
  [`adr-001-reject-langgraph.md`](adr-001-reject-langgraph.md),
  [`provider-roadmaps.md`](provider-roadmaps.md) и прочие — внутренние материалы.

> Историческое: ранние `quickstart.md`, `scenarios.md`, `roadmap*.md`,
> `*-phase*.md`, `project-v2-vision.md` отражают прежние этапы; актуальны
> русскоязычные `QUICKSTART.ru.md` и `USE_CASES.ru.md` выше.
