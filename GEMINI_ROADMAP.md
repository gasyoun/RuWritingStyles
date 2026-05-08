# Gemini Agent Roadmap: RuWritingStyles

*Персонализировано на основе https://github.com/codejunkie99/agent-roadmap-2026 и внутренних docs/ 2026-05-08.*

## Профиль проекта
- **Уровень**: Сложная многоагентная система (Council + Verifier).
- **Стек**: Python + JSON Schema + Markdown Styles.
- **Цель**: Создание "Gemini-Ready" филологической лаборатории с 17+ кластерами стилей.
- **Текущая Фаза**: Фаза 3 (Custom Harness) -> Фаза 4 (Evals).

## План внедрения (17 кластеров)

### Фаза A: Рефакторинг Манифеста (Шаги G-01, L-01, L-02)
- [x] Обновить `styles/manifest.yml`: добавить поля `cluster`, `level`, `extends`.
- [x] Создать 8 лингвистических паспортов (`mss`, `pfg`, `iesh`, `tsh`, `kmsh`, `nss`, `dss`, `mts`).
- [x] Создать 9 литературоведческих паспортов (`lit_opoyaz`, `lit_structural`, `lit_textology`, `lit_mythopoetics`, `lit_narratology`, `lit_bakhtin`, `lit_historico_cultural`, `lit_reception`, `lit_poststructural`).
- [x] Расширить `text_domain` в метаданных запуска (17 доменов в `run.schema.json`).

### Фаза B: Интеллектуальный Совет (Шаги G-04, L-03)
- [x] Реализовать `get_cluster_weights()` в `council.py`.
- [x] Внедрить матрицу парадигматических конфликтов (напр. ОПОЯЗ vs Бахтин).
- [x] Настроить "Веса доверия" для верификатора (доменно-ориентированная проверка).

### Фаза C: Автоматизация стилей (Шаг G-03, L-04)
- [x] Создать системный промпт `Style Architect`.
- [x] Сгенерировать паспорта для 17 кластеров.
- [x] Верифицировать паспорта на реальных текстах (через `eval-suite`).

### Фаза D: Филологические Эвалы (Шаги G-05, G-06, L-05)
- [x] Создать Golden Dataset (34/30+ кейсов готово).
- [x] Внедрить Adversarial Evals (защита "эпистемической осторожности").
- [x] Настроить CI gate на основе `rws eval-suite`.

## Следующее действие
1. Перейти к Фазе E: QA и финальная интеграция (см. [Phase_E_Plan.md](file:///C:/Users/user/.gemini/antigravity/brain/1ad57f16-8ee7-4260-819c-287d2b74fee0/Phase_E_Plan.md)).
2. Провести замеры качества на реальных API (Gemini 2.0 / Claude 3.5).

---
*Math: Total Steps (17) * 0.5 weeks/step = 8.5 weeks total project alignment.*
