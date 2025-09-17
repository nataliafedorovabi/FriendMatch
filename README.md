## Бот-игра "Подружки: Знакомства" (Telegram)

Игра для подруг: одна заполняет анкету, другая пытается угадать её ответы. В конце — очки совпадений и милые комментарии.

### Стек
- Python 3.11
- FastAPI (webhook)
- aiogram v3 (Telegram bot)
- PostgreSQL (Railway), async SQLAlchemy + asyncpg
- Docker (деплой на Railway)

### Быстрый старт (локально)
1. Создайте бота у `@BotFather`, получите `BOT_TOKEN` и узнайте `BOT_USERNAME`.
2. Скопируйте `env.example` → `.env` и заполните переменные.
3. Установите зависимости:
```bash
pip install -r requirements.txt
```
4. Запуск (локально):
```bash
uvicorn app.webhook:app --host 0.0.0.0 --port 8000
```
Для теста вебхука локально используйте `ngrok` и задайте `WEBHOOK_BASE_URL`.

### Деплой на Railway
1. Подключите проект к Railway.
2. Добавьте PostgreSQL (переменная `DATABASE_URL` появится автоматически).
3. В Variables задайте: `BOT_TOKEN`, `BOT_USERNAME`, `WEBHOOK_SECRET_TOKEN`, `WEBHOOK_BASE_URL`.
4. Deploy. Приложение само выставит webhook.

### Что уже есть
- Анкета, угадывание через deep-link `/start guess_<tg_id>`
- Подсчёт совпадений и процент
- FastAPI + webhook для Telegram

### Docker
```bash
docker build -t girls-quiz-bot .
docker run --env-file .env -p 8000:8000 girls-quiz-bot
```
