# Быстрый старт

От установки до первой рецензии статьи за пять шагов. Конвейер запускает «Совет»
филологических стилей (Зализняк, Тронский, Елизаренкова, Топоров, Панини-традиция и
др.) над вашим текстом в Markdown и возвращает находки, исправления, список литературы
по ГОСТ и проверку соответствия журналу.

> Нужен только Python ≥ 3.10 и (для реальных прогонов) ключ **DeepSeek**. Без ключа
> всё работает на детерминированном провайдере `mock` — см. шаг 5.

## 1. Установка

```bash
git clone https://github.com/gasyoun/RuWritingStyles
cd RuWritingStyles
python -m pip install -e .
```

После этого команда `rws` доступна в терминале. Если её не видно (бывает на Windows,
когда каталог `Scripts` не в `PATH`), везде ниже вместо `rws` используйте
`python -m ruwritingstyles.cli`.

## 2. Ключ DeepSeek

Получите ключ на <https://platform.deepseek.com>, скопируйте шаблон и впишите ключ:

```bash
cp .env.example .env
# откройте .env и подставьте: DEEPSEEK_API_KEY=sk-...
```

Проверьте готовность (ключи никогда не печатаются):

```bash
rws provider-status --provider deepseek
# ready: yes  — всё готово
```

## 3. Первый прогон (на готовом примере)

Возьмите маленький встроенный пример, чтобы убедиться, что всё работает:

```bash
rws run examples/input/poststructural-term-check.md \
  --provider deepseek --execute --council sanskrit
```

Результат появится в `runs/<id>/` — главное смотреть `report.md`.

## 4. Свой текст

Подайте свою статью (Markdown) и выберите профиль журнала:

```bash
rws run моя-статья.md \
  --provider deepseek --execute \
  --council sanskrit \
  --journal vestnik-spbu
```

- `--council sanskrit` — индологическая панель (веда, этимология, Панини, комментарий).
  Список панелей: `rws councils`. Можно задать свои стили: `--styles toporov-etym,panini-traditional`.
- `--journal vestnik-spbu` — проверка под журнал (объём, ГОСТ, IAST, аннотация/ключевые
  слова на ru+en). Список журналов: `rws journals`.

## 5. Что смотреть в отчёте (`runs/<id>/report.md`)

- **Находки по стилям** — что каждый «рецензент» отметил (со ссылкой на `span_id`).
- **Соответствие журналу** — объём против лимита, формат ссылок, схема транслитерации,
  наличие аннотации и ключевых слов на нужных языках.
- **Транслитерация санскрита** — детерминированный линтер: где не хватает IAST при
  первом упоминании, где смешаны схемы.
- **`references-gost.md`** — список литературы по ГОСТ Р 7.0.100-2018.
- **`revised.md` / `revision.diff`** — предложенная (точечная) правка текста.

## Без ключа и офлайн

Прогон на детерминированном провайдере (бесплатно, без сети) — удобно посмотреть
структуру конвейера:

```bash
rws run examples/input/poststructural-term-check.md --provider mock --execute
```

`RWS_OFFLINE=1` дополнительно отключает обращения к OpenAlex.

## Полезные команды

```bash
rws list-styles            # все стили; --mvp — только базовый набор
rws councils               # именованные панели (general / sanskrit / indology)
rws journals               # профили журналов
rws lint-translit файл.md  # только проверка транслитерации, без Совета
rws findings <run> --span p016   # находки по конкретному фрагменту
rws validate-run <run>     # проверить целостность артефактов прогона
```

## Дальше

- Как цитировать проект и как декларировать использование ИИ в статье —
  [`AI_DISCLOSURE.md`](AI_DISCLOSURE.md) и [`../CITATION.cff`](../CITATION.cff).
- Что модель ловит на реальной статье — [`case-study-p3-guna.md`](case-study-p3-guna.md).
- Честная оценка качества по золотым кейсам — [`benchmark.md`](benchmark.md).
- Полный список команд — [`cli.md`](cli.md).
