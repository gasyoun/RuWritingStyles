# Инструкция по развертыванию RuWritingStyles

Этот документ описывает локальный запуск, Docker Compose и серверный режим для текущей версии проекта. Основная схема сейчас такая: FastAPI обслуживает API, а после сборки Web Studio также раздает готовый `web/dist` как статический SPA.

## 1. Предварительные условия

- Python 3.10+.
- Node.js 18+ для разработки Web Studio.
- Git.
- Docker и Docker Compose, если нужен контейнерный запуск.

## 2. Локальная разработка

```bash
git clone https://github.com/gasyoun/RuWritingStyles.git
cd RuWritingStyles
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
python -m pip install -e .
```

Для Web Studio:

```bash
cd web
npm install
cd ..
rws web
```

`rws web` запускает FastAPI на `http://localhost:8000` и Vite frontend на `http://localhost:5173`.

## 3. Настройка провайдеров

Скопируйте `.env.example` в `.env` и заполните только те ключи, которые реально будете использовать:

```env
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
OPENROUTER_API_KEY=...
```

Проверка готовности не печатает секреты:

```bash
rws provider-status --strict
rws provider-status --provider openai --strict
```

Для приватного локального режима можно использовать:

```env
RWS_OLLAMA_URL=http://localhost:11434/api/chat
RWS_LOCAL_LLM_URL=http://localhost:8000/v1/chat/completions
```

После этого запускайте аудит с `--provider ollama` или `--provider local`.

## 4. CLI smoke

Без внешних ключей:

```bash
rws run examples/input/pseudo-etymology.md --run-id deployment-smoke --execute --provider mock
rws validate-run runs/deployment-smoke
```

Eval suite:

```bash
rws eval-suite --provider mock --suite-id deployment-eval-smoke
rws validate-eval-suite runs/deployment-eval-smoke
```

Текущий manifest содержит 33 eval-кейса. `mock` provider проверяет инфраструктуру и схемы, но не является содержательной филологической оценкой.

## 5. Production через Docker Compose

Контейнер собирает React frontend, устанавливает Python-пакет из `pyproject.toml`, копирует проектные данные и запускает `python -m ruwritingstyles.api`.

```bash
docker compose up --build
```

Сервис доступен на `http://localhost:8000`. Этот же порт отдает API и собранный frontend.

`docker-compose.yml` монтирует:

- `./rws.db:/app/rws.db` - SQLite index запусков и метрик;
- `./runs:/app/runs` - переносимые run artifacts;
- `./examples:/app/examples` - демонстрационные входные документы.

Перед production-запуском проверьте, что `.env` не попадает в Git и что контейнер получает только нужные ключи провайдеров.

## 6. Production без Docker

Соберите frontend:

```bash
cd web
npm ci
npm run build
cd ..
```

Установите backend и запустите FastAPI:

```bash
python -m pip install .
python -m ruwritingstyles.api
```

Если `web/dist` существует, FastAPI автоматически раздает его вместе с API. Для публичного сервера можно поставить Nginx или другой reverse proxy перед портом `8000`; это опциональный внешний слой для TLS, домена и лимитов запросов, а не часть обязательного runtime проекта.

## 7. Release checks

Перед деплоем или PR:

```bash
python -m compileall -q src tools tests
python tools/validate_project.py
python -m unittest discover -s tests
```

Для frontend:

```bash
cd web
npm run lint
npm run build
```

GitHub Actions `CI` сейчас покрывает Python compile, `tools/validate_project.py` и unit tests. Manual workflow `Eval Smoke` запускает mock eval suite, сравнение, validation и export bundle.

## 8. Хранилище и приватность

- `runs/` остается источником переносимых артефактов: prompts, JSON, Markdown, HTML, diff, LaTeX/BibTeX и ZIP.
- `rws.db` ускоряет список запусков и хранит метрики, но не заменяет сами артефакты.
- `provider.log.jsonl` пишет duration/retry/status telemetry без API-ключей и без полного request body.
- Для конфиденциальных текстов используйте `mock`, `local` или `ollama`; внешние провайдеры всегда opt-in через явный `--provider`.
