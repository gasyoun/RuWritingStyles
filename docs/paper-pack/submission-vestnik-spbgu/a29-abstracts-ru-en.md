«Совет филологов»: агентное рецензирование научной прозы по санскритологии с детерминированным контролем качества

Council of Philologists: Agentic Peer Review of Sanskritological Scholarly Prose with Deterministic Quality Control

М. Ю. Гасунс (Mārcis Gasūns), независимый исследователь / independent researcher, ORCID 0000-0003-4513-884X, gasyoun@ya.ru

## Аннотация

Предлагается воспроизводимый метод ИИ-ассистированного рецензирования научной прозы по
санскритской лингвистике на русском языке. Метод соединяет (1) каталог стилей-паспортов,
моделирующих прозаический метод конкретных филологов (Зализняк, Тронский, Мельчук,
Елизаренкова, Топоров, Лидова и др.), (2) многоагентный «Совет», прогоняющий рукопись
через цепочку `сегментация → независимые рецензии стилей → дебаты Совета → синтез правки →
верификация`, и (3) детерминированный слой качества (сверка IAST/кириллической
транслитерации, оформление библиографии по ГОСТ Р 7.0.100-2018, привязка цитат). Ключевой
методологический вклад — честная оценка: показано, что одиночный прогон бесполезен как
метрика (зачет золотых кейсов колебался 0/5…3/5 на неизменном коде из-за недетерминизма
провайдера), и введен N-усредненный бенчмарк. На нем измерено, что **детекция филологических
ошибок сильна и стабильна (24/25 = 0.96)**, а узким местом был **синтез правки**: ревизия
над-переписывала короткие фрагменты (pass-rate 12/25 = 0.48). Узкое место снято
архитектурно — движок реконструирует исправленный текст из пер-спановых правок и
ограничивает рост документа бюджетом, — что подняло pass-rate до **23/25 = 0.92** при нуле
diff-провалов. Проект — открытый (Apache-2.0), с `CITATION.cff`, Zenodo-DOI и метаданными
Dublin Core.

**Ключевые слова:** санскрит, лексикография, цифровые гуманитарные науки, большие языковые
модели, агентное рецензирование, IAST, ГОСТ Р 7.0.100-2018, воспроизводимость.

## Abstract

We present a reproducible method for AI-assisted peer review of Russian-language scholarly
prose in Sanskrit linguistics. The method combines (1) a catalogue of style passports
modelling the written method of individual philologists (Zalizniak, Tronsky, Elizarenkova,
Toporov and others), (2) a multi-agent "Council" that runs a manuscript through
segmentation, independent style reviews, council debate, revision synthesis and
verification, and (3) a deterministic quality layer (IAST/Cyrillic transliteration linting,
GOST R 7.0.100-2018 bibliography checks, citation grounding). The key methodological
contribution is honest measurement: single-run accuracy is meaningless under provider
non-determinism (gold-case scores oscillated 0/5–3/5 on unchanged code), so an N-averaged
benchmark is introduced. Detection of philological errors proves strong and stable
(24/25 = 0.96), while revision synthesis was the bottleneck (pass rate 12/25 = 0.48); it is
removed architecturally by engine-side span-patch reconstruction with a document-growth
budget, raising the pass rate to 23/25 = 0.92 with zero diff failures. A two-rater gold-set
annotation (mechanical scorer vs an independent frontier model, disclosed) reaches 0.96
agreement. The project is open source (Apache-2.0) with full citation and archival
metadata.

**Keywords:** Sanskrit, lexicography, digital humanities, large language models, agentic
peer review, IAST, GOST R 7.0.100-2018, reproducibility.
