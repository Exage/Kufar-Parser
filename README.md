# Kufar Parser

Парсер объявлений Kufar с фильтрацией по правилам, сохранением новых объявлений в БД и отправкой уведомлений в Telegram.

## Что делает

- Читает правила из `config/categories.json`
- Парсит объявления с пагинацией
- Фильтрует по цене, `keywords`, `excludeKeywords`
- Сохраняет только новые объявления в таблицу `products`
- Отправляет уведомления в Telegram
- Запоминает отправленные уведомления в `notifications`

## Требования

- Python 3.9+
- PostgreSQL/MySQL/SQLite

## Установка

```bash
cd /Users/n.gorkavchuk/Desktop/Kufar-Parser
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Формат `.env`

```env
DATABASE_URL=postgresql://user:password@localhost:5432/kufar_parser
TELEGRAM_BOT_TOKEN=123456789:AA...token...
TELEGRAM_CHAT_ID=-1001234567890
POLL_INTERVAL_MINUTES=5
```

Примечания:
- `DATABASE_URL` обязателен и должен начинаться с `postgresql://`, `mysql://` или `sqlite:///`.
- Для SQLite можно использовать: `DATABASE_URL=sqlite:///kufar_parser.db`.
- `TELEGRAM_CHAT_ID` должен быть числом (для каналов/групп обычно отрицательный).

## Правила парсинга

Правила лежат в `config/categories.json`.

Поля:
- `name`: имя категории для логов и уведомлений
- `minPrice`, `maxPrice`: фильтр цены (`-1` отключает границу)
- `keywords`: список включаемых слов (пустой список отключает фильтр)
- `excludeKeywords`: список исключаемых слов
- `categoryUrl`: URL категории Kufar

## Запуск

Один прогон:

```bash
.venv/bin/python main.py
```

Непрерывный запуск по расписанию (APScheduler):

```bash
.venv/bin/python main.py --schedule
```

Интервал задаётся в `.env` через `POLL_INTERVAL_MINUTES`.

## Полезные скрипты

Тест отправки в Telegram:

```bash
.venv/bin/python scripts/test_telegram.py
```

Просмотр последних товаров из БД:

```bash
.venv/bin/python scripts/list_products.py
```

## Логи и их смысл

Формат логов:

```text
YYYY-MM-DD HH:MM:SS,ms | LEVEL | message
```

Основные события:
- `Loaded rules: N` — загружено `N` правил
- `[RULE] parsing: URL` — начат парсинг правила
- `[RULE] parsed=X | passed_filters=Y | saved_new=Z | notified=W`:
  - `parsed` — найдено объявлений
  - `passed_filters` — прошло фильтры
  - `saved_new` — новых записано в БД
  - `notified` — реально отправлено уведомлений
- `[RULE] failed, moving to next rule` — ошибка в одном правиле; цикл продолжает работу

## Автозапуск через systemd (Linux, опционально)

Создай сервис `/etc/systemd/system/kufar-parser.service`:

```ini
[Unit]
Description=Kufar Parser
After=network.target

[Service]
Type=simple
WorkingDirectory=/Users/n.gorkavchuk/Desktop/Kufar-Parser
ExecStart=/Users/n.gorkavchuk/Desktop/Kufar-Parser/.venv/bin/python main.py --schedule
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Команды:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now kufar-parser
sudo systemctl status kufar-parser
```

## Автозапуск через cron (альтернатива)

Если нужен запуск раз в N минут без постоянного процесса:

```cron
*/5 * * * * cd /Users/n.gorkavchuk/Desktop/Kufar-Parser && /Users/n.gorkavchuk/Desktop/Kufar-Parser/.venv/bin/python main.py
```
