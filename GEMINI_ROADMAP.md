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
- [ ] Внедрить матрицу парадигматических конфликтов (напр. ОПОЯЗ vs Бахтин).
- [ ] Настроить "Веса доверия" для верификатора.

### Фаза C: Автоматизация стилей (Шаг G-03, L-04)
- [x] Создать системный промпт `Style Architect`.
- [x] Сгенерировать паспорта для Аверинцева, Зализняка, Гаспарова, Мельчука.
- [ ] Верифицировать паспорта на реальных текстах.

### Фаза D: Филологические Эвалы (Шаги G-05, G-06, L-05)
- [/] Создать Golden Dataset (8/30+ кейсов готово).
- [ ] Внедрить Adversarial Evals (защита "эпистемической осторожности").
- [ ] Настроить CI gate на основе `rws eval-suite`.

## Следующее действие
1. Довести Golden Dataset до 30+ кейсов (Фаза D).
2. Внедрить Adversarial Evals для защиты эпистемической осторожности.

---
*Math: Total Steps (17) * 0.5 weeks/step = 8.5 weeks total project alignment.*
