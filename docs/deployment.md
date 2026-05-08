# Инструкция по развертыванию RuWritingStyles

Этот документ описывает, как запустить систему локально (для разработки и личного пользования) и на сервере (в режиме общего веб-сервиса).

## 1. Локальный запуск (Local Desktop)

### Предварительные условия
- Python 3.9+
- Node.js 18+ (для Web Studio)
- Git

### Установка
```bash
git clone https://github.com/gasyoun/RuWritingStyles.git
cd RuWritingStyles
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -e .
```

### Настройка ключей (.env)
Создайте файл `.env` в корне проекта:
```env
GOOGLE_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
RWS_OPENROUTER_MODEL=openai/gpt-oss-120b:free
```

### Запуск Web Studio
Самый удобный режим для филологов:
```bash
rws web
```
Система автоматически запустит Backend (порт 8000) и Frontend (порт 5173). Откройте `http://localhost:5173`.

### Запуск через CLI (примеры)
1. **Простой аудит**:
   ```bash
   rws run my_article.md --execute --provider openrouter
   ```
2. **Аудит с выбором школы (Архетипа)**:
   ```bash
   # Выбор "Ленинградской школы" для разрешения конфликтов
   rws run my_article.md --execute --provider google --archetype "Leningrad School"
   ```
3. **Проверка качества (Benchmark)**:
   ```bash
   # Запуск золотого набора тестов
   rws eval-suite --provider openrouter --tags GOLD_ZALIZNYAK
   ```

---

## 2. Развертывание на сервере (Production)

Для работы в режиме веб-сервиса (многопользовательский режим) рекомендуется следующая схема.

### Архитектура
- **Backend**: FastAPI под управлением `gunicorn` + `uvicorn`.
- **Frontend**: Скомпилированный статический билд Vite, раздаваемый через `nginx`.
- **Proxy**: Nginx как входная точка (SSL, порты).

### Шаг 1: Сборка фронтенда
```bash
cd web
npm install
npm run build
```
Результат будет в `web/dist/`. Эти файлы нужно скопировать в папку, которую обслуживает ваш веб-сервер (например, `/var/www/html`).

### Шаг 2: Запуск бэкенда
```bash
# Установка зависимостей без режима редактирования
pip install .
# Запуск через gunicorn (4 воркера для параллельной обработки)
gunicorn src.ruwritingstyles.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Шаг 3: Настройка Nginx
Пример конфигурации `/etc/nginx/sites-available/rws`:
```nginx
server {
    listen 80;
    server_name rws.yourdomain.com;

    # Frontend (Vite Build)
    location / {
        root /var/www/rws/web/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Особенности серверного режима (Фаза F)
1. **Очереди задач**: Для промышленного использования рекомендуется добавить Redis и Celery (см. `docs/project-v2-vision.md`), чтобы тяжелые аудиты выполнялись в фоновом режиме.
2. **SQLite**: База данных `rws_index.db` будет создана автоматически в корне проекта для быстрого поиска по выполненным запускам (`runs/`).
3. **Локальные модели**: Если сервер имеет GPU, вы можете запустить **Ollama** локально и указать её адрес в `.env`, чтобы не платить за внешние API и обеспечить полную приватность данных.

---

## 3. Примеры использования в разных ситуациях

### Сценарий: "Аудит сложной этимологической статьи"
Исследователь хочет получить максимально строгий результат, опираясь на питерскую школу.
```bash
rws run article.md --execute --provider google --archetype "Leningrad School" --style ling_iesh
```
*Результат*: Система будет использовать паспорт Тронского и отдавать приоритет его правкам при спорах.

### Сценарий: "Быстрая нормализация стиля"
Редактору нужно привести текст к московскому академическому стандарту.
```bash
rws run draft.md --execute --provider openrouter --archetype "Moscow School" --style ling_nss
```
*Результат*: Акцент на соблюдении литературной нормы и системности определений.

### Сценарий: "Приватный режим (No Cloud)"
Для конфиденциальных текстов.
1. Запустите Ollama с моделью `llama3:70b`.
2. В `.env` установите: `RWS_PROVIDER=ollama`, `OLLAMA_URL=http://localhost:11434`.
3. Запустите аудит: `rws run private.md --execute`.
