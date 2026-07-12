# Venue checklist — «Совет филологов» (A29)

_Created: 03-07-2026 · Last updated: 12-07-2026_

> Чек-лист выбора площадки для методологической статьи
> [`methodology-paper-draft.ru.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/methodology-paper-draft.ru.md).

## Решение (04-07-2026)

**Площадка: «Вестник СПбГУ. Востоковедение и африканистика». Язык: RU (+ обязательная EN
аннотация).**

Обоснование: журнал уже смоделирован в проекте (`--journal vestnik-spbu`), целевая аудитория
(индология/востоковедение) — реальные читатели метода, кейс *guṇa* написан именно под этот
профиль. ВЯ отклонена — долгий цикл, ИИ/DH-темы проходят тяжело. DSH Oxford / open-DH
отложены как EN-вариант на случай отказа (методологический задел статьи это допускает —
перевод не требует новых данных).

## Кандидаты

| Площадка | Язык | Профиль | За | Против |
|---|---|---|---|---|
| **Вестник СПбГУ. Востоковедение и африканистика** | RU | индология / востоковедение | целевая аудитория проекта; журнал уже смоделирован в `--journal vestnik-spbu`; кейс *guṇa* именно под него | не DH/методы-профиль; метод-статья может читаться как «не по теме» |
| **Вопросы языкознания (ВЯ)** | RU | общее языкознание | престиж; методологический разворот уместен | ИИ/DH-темы проходят тяжело; долгий цикл |
| **Digital Scholarship in the Humanities (DSH, Oxford)** | EN | DH-методы | естественный дом для метода + воспроизводимости; международная видимость | нужен перевод на EN; санскритская специфика — нишевая для рецензентов |
| **Journal of Data Mining & Digital Humanities / аналог** | EN | DH-методы, open | open-access, дружествен к коду/датасетам | ниже престиж |

## Требования к рукописи («Вестник СПбГУ», RU)

- [x] Язык финального текста: **RU**.
- [x] Аннотация: RU + **EN** (EN Abstract добавлен 11-07-2026; лимит слов
      проверяется `--journal vestnik-spbu`).
- [x] Ключевые слова: RU + EN (EN Keywords добавлены 11-07-2026).
- [x] Библиография: ГОСТ Р 7.0.100-2018 — список «Литература» черновика отформатирован
      по ГОСТ 12-07-2026 (кириллический блок перед латинским, DOI/даты обращения); каждая
      inline-цитата (Author Year) имеет запись в
      [`knowledge/bibliography.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/knowledge/bibliography.json)
      (добавлены Feinstein & Cicchetti 1990, ARS, ГОСТ, CDSL), так что привязка цитат
      проверяет саму статью.
- [x] Байлайн: «М. Ю. Гасунс» · независимый исследователь · ORCID 0000-0003-4513-884X —
      в шапке черновика. Источник —
      [`Uprava/AUTHOR.md`](https://github.com/gasyoun/Uprava/blob/main/AUTHOR.md).
- [x] Декларация об ИИ — §7 черновика (включая роль ИИ-разметчика B из §4.6), формулы из
      [`AI_DISCLOSURE.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/AI_DISCLOSURE.md).
- [x] Двух-разметчиковая разметка золотого набора (блокер подачи) — выполнена 11-07-2026
      (§4.6 черновика): согласие 24/25, единственное расхождение — на адъюдикации человека
      ([`review-vedic-r02-adjudication.html`](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/annotation/review-vedic-r02-adjudication.html));
      оба варианта вердикта готовы к вставке в §4.6 —
      [`vedic-r02-adjudication-verdict-variants.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/paper-pack/vedic-r02-adjudication-verdict-variants.md).
- [ ] Data availability: ссылка на репозиторий + Zenodo-DOI (после минтинга — см. ниже).
- [ ] Cover letter под площадку —
      [`cover-letter.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/paper-pack/cover-letter.md).

## Зависимость: Zenodo-DOI

Data-availability и `CITATION.cff` статьи ссылаются на архивный DOI. Он минтится при
публикации GitHub-релиза v2.12.0 в Zenodo (кнопки автора — в
[`GTD_NEXT_ACTIONS.md`](https://github.com/gasyoun/Uprava/blob/main/GTD_NEXT_ACTIONS.md)).
До минтинга DOI в тексте статьи — плейсхолдер.

_Dr. Mārcis Gasūns_
