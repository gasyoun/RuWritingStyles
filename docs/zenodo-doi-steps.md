# Zenodo DOI — author steps + ready-to-apply patch

_Created: 03-07-2026 · Last updated: 12-07-2026_

> **12-07-2026:** финальное описание депозита уже вписано в
> [`.zenodo.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/.zenodo.json)
> (включая измеренные числа бенчмарка 0.48 → 0.92 и двух-разметчиковую разметку) — при
> включении репозитория Zenodo возьмет его автоматически, руками ничего вписывать не
> нужно. Свежий релиз для п. 3 уже есть — используйте последний релиз H770 (v2.14.x), а
> не патч-тег v2.12.1. Клик заморожен до 15-07 (org-wide freeze).

> Релиз **v2.12.0 уже опубликован на GitHub**
> ([releases](https://github.com/gasyoun/RuWritingStyles/releases)). Метаданные архива
> готовы: [`.zenodo.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/.zenodo.json)
> и [`CITATION.cff`](https://github.com/gasyoun/RuWritingStyles/blob/main/CITATION.cff)
> несут канонический байлайн (Gasūns, Mārcis · ORCID 0000-0003-4513-884X · Independent
> scholar). Ниже — только то, что **должен нажать автор**, и готовый патч под минтинг DOI.

## Кнопки автора (в порядке)

1. **Включить репозиторий в Zenodo.** Зайти на <https://zenodo.org> под GitHub-аккаунтом →
   *Account → GitHub* → переключить `gasyoun/RuWritingStyles` в **ON**. (Zenodo архивирует
   только релизы, созданные **после** включения — см. п. 3.)
2. **Проверить**, что Zenodo видит репозиторий (появляется в списке с тумблером ON).
3. **Создать новый релиз, чтобы Zenodo его поймал.** Zenodo не архивирует уже
   существующие релизы задним числом. Проще всего выпустить патч-тег:
   - либо в GitHub UI: *Releases → Draft a new release* → тег `v2.12.1` (или следующий) →
     Publish;
   - либо CLI: `git tag v2.12.1 && git push origin v2.12.1` и затем `gh release create v2.12.1`.
   Zenodo автоматически создаст депозит и **выдаст DOI** (concept-DOI для всех версий +
   version-DOI для конкретного релиза).
4. **Скопировать concept-DOI** (тот, что «all versions») из бейджа/страницы депозита.

## Готовый патч (применить ПОСЛЕ получения DOI)

Заменить `10.5281/zenodo.XXXXXXX` на реальный concept-DOI.

**`CITATION.cff`** — раскомментировать/заменить хвост, добавив блок `identifiers` перед
`references:`:

```yaml
identifiers:
  - type: doi
    value: 10.5281/zenodo.XXXXXXX
    description: "Concept DOI (all versions)"
```

**`README.md`** — в разделе «Цитирование и декларация об использовании ИИ» заменить фразу
«Архивирование с DOI готовится на Zenodo … после первого релиза DOI добавляется в
`CITATION.cff`» на:

```markdown
- **Архив с DOI.** Каждый релиз заархивирован на Zenodo: concept-DOI
  [10.5281/zenodo.XXXXXXX](https://doi.org/10.5281/zenodo.XXXXXXX) (все версии).
```

**Статья** — в data-availability методологической статьи
([`methodology-paper-draft.ru.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/methodology-paper-draft.ru.md))
заменить плейсхолдер «релиз с DOI на Zenodo» на реальный DOI.

_Dr. Mārcis Gasūns_
