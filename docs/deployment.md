# Инструкция по развертыванию RuWritingStyles

Этот документ различает четыре режима: checkout для разработки, установленный wheel с редактируемым workspace, production Web Studio из wheel и контейнер с одним writable volume.

## 1. Предварительные условия

- Python 3.10+.
- Node.js 24 только для разработки/сборки Web Studio.
- Git только для checkout-разработки.
- Docker и Docker Compose, если нужен контейнерный запуск.

## 2. Установленный workspace (обычный режим)

```bash
python -m pip install ruwritingstyles-2.15.3-py3-none-any.whl
mkdir rws-workspace && cd rws-workspace
rws init .
rws web
```

`rws init` копирует только управляемые runtime assets и создает `.rws-workspace.json`; runs, exports, `rws.db`, `.env` и посторонние файлы не затрагиваются. `rws init --upgrade` заменяет только неизмененные файлы, а новые версии локально правленных файлов кладет в `.rws-new/`.

## 3. Checkout-разработка

```bash
git clone https://github.com/gasyoun/RuWritingStyles.git
cd RuWritingStyles
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
python -m pip install -e .
```

Для Vite-разработки Web Studio:

```bash
cd web
npm ci
cd ..
rws web --dev
```

Production-команда `rws web` всегда отдает встроенный SPA и API на `http://localhost:8000`; `--dev` сохраняет Vite на `http://localhost:5173`.

## 4. Настройка провайдеров

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

## 5. CLI smoke

Без внешних ключей:

```bash
rws run examples/input/pseudo-etymology.md --run-id deployment-smoke --execute --provider mock --budget-mode smoke
rws validate-run runs/deployment-smoke
```

Eval suite:

```bash
rws eval-suite --provider mock --suite-id deployment-eval-smoke
rws validate-eval-suite runs/deployment-eval-smoke
```

Текущий manifest содержит 52 eval-кейса: шесть детерминированно проходят на `mock`, остальные 46 требуют содержательного провайдера. `mock` проверяет инфраструктуру, схемы и сохранность защищенных проходов, но не является содержательной филологической оценкой.

## 6. Production через Docker Compose

Контейнер собирает frontend на Node 24 через `npm ci`, собирает и устанавливает wheel, затем при первом старте инициализирует `/data`. Образ не использует исходный checkout во время исполнения.

```bash
docker compose up --build
```

Сервис доступен на `http://localhost:8000`. Этот же порт отдает API и собранный frontend.

`docker-compose.yml` монтирует один writable каталог `./rws-data:/data`; в нем совместно живут marker, редактируемые assets, `runs/`, exports и rebuildable `rws.db`.

Перед production-запуском проверьте, что `.env` не попадает в Git и что контейнер получает только нужные ключи провайдеров.

## 7. Production без Docker (Bare Metal)

Для развертывания на обычном Linux-сервере (Ubuntu/Debian) без контейнеров:

1. **Подготовьте окружение и workspace**:
   ```bash
    python -m venv venv
    source venv/bin/activate
    pip install ruwritingstyles-2.15.3-py3-none-any.whl
    mkdir -p /srv/ruwritingstyles-data
    rws init /srv/ruwritingstyles-data
    export RWS_WORKSPACE=/srv/ruwritingstyles-data
   ```

2. **Запустите через Process Manager (PM2)**:
   Рекомендуется использовать PM2 для автоматического перезапуска при сбоях:
   ```bash
   pm2 start "python -m ruwritingstyles.api" --name rws-api
   ```

3. **Или через Systemd (Рекомендуется для Linux)**:
   Создайте файл `/etc/systemd/system/rws.service`:
   ```ini
   [Unit]
   Description=RuWritingStyles API Service
   After=network.target

   [Service]
   User=youruser
   WorkingDirectory=/srv/ruwritingstyles-data
   Environment="PATH=/opt/ruwritingstyles/venv/bin"
   Environment="RWS_WORKSPACE=/srv/ruwritingstyles-data"
   ExecStart=/opt/ruwritingstyles/venv/bin/uvicorn ruwritingstyles.api:app --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Затем: `systemctl enable rws && systemctl start rws`.

4. **Reverse Proxy (Nginx)**:
   Поставьте Nginx перед портом 8000 для поддержки SSL (HTTPS) и доменного имени. FastAPI будет отдавать и API, и статику фронтенда на одном порту.

## 8. Release checks

Перед деплоем или PR:

```bash
python -m compileall -q src tools tests
python tools/validate_project.py
python -m pytest -q
python scripts/ci-eval-gate.py
python -m build --wheel --sdist
python scripts/verify-runtime-assets.py dist/*.whl dist/*.tar.gz
```

Для frontend:

```bash
cd web
npm ci
npm test
npm run lint
npm run build
```

Для Obsidian plugin: `cd obsidian-plugin && npm ci && npm run build && npm test`. GitHub Actions также проверяет wheel в чистых Windows/Ubuntu consumer-средах (Python 3.10/3.14) и запускает Docker smoke; стабильный `CI / Required gate` требует все применимые jobs.

## 9. Хранилище и приватность

- `runs/` остается источником переносимых артефактов: prompts, JSON, Markdown, HTML, diff, LaTeX/BibTeX и ZIP.
- `run.json` — durable source of truth; `rws.db` является rebuildable index.
- `provider.log.jsonl` пишет duration/retry/status и budget consumption без API-ключей и полного request body.
- Для конфиденциальных текстов используйте `mock`, `local` или `ollama`; внешние провайдеры всегда opt-in через явный `--provider`.
