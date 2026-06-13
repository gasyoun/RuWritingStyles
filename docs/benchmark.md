# Бенчмарк провайдеров по санскритским eval-кейсам

Сводная точность реальных провайдеров (Anthropic / OpenAI / Google) на
экспертных санскритских кейсах (`tags: ["GOLD_SANSKRIT"]` без `deterministic`).
Заполняется **после** платного прогона и экспертной разметки по протоколу
[../evals/GOLD_PROTOCOL.md](../evals/GOLD_PROTOCOL.md).

## Статус

⏳ **Ожидает платного прогона и экспертной разметки.** Числа без двойной
экспертной разметки не являются золотым стандартом, поэтому таблица пока пуста.

Детерминированные кейсы (линтер транслитерации, проверка цитирований) не зависят
от провайдера и проверяются бесплатно в `Eval Smoke` CI на `--provider mock`;
их сюда не включают.

## Как заполнить

```bash
rws eval-suite --provider anthropic --suite-id gold-anthropic
rws eval-suite --provider google    --suite-id gold-google
rws eval-suite --provider openai     --suite-id gold-openai
rws eval-compare runs/gold-anthropic runs/gold-google
```

Затем по каждому кейсу провести экспертную разметку (≥2 разметчика) и внести
`gold-annotation.json`; итоги свести в таблицу ниже.

## Таблица точности (по типам находок)

| Кейс | Тип находки | Anthropic | OpenAI | Google |
|---|---|---|---|---|
| sanskrit-pseudo-etymology | `unsupported_sanskrit_etymology` | — | — | — |
| karaka-not-padezh | `mistranslated_native_term` | — | — | — |
| vedic-classical-anachronism | `anachronistic_sanskrit_period` | — | — | — |
| samasa-misclassification | `wrong_samasa_type` | — | — | — |
| commentary-layer-mix | `missing_commentary_layer` | — | — | — |

(«—» = прогон ещё не выполнен.)
