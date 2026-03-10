# RentBot Nha Trang

Telegram-бот для аренды байков в Нячанге: клиент выбирает модель и оставляет заявку, администратор подтверждает бронь и управляет каталогом.

## О проекте

Проект автоматизирует процесс аренды:

- клиент оформляет заявку без переписки “вручную”;
- администратор получает структурированные брони и обрабатывает их в несколько кликов;
- каталог, статусы заявок и настройки хранятся централизованно в SQLite.

Результат: быстрее обработка заявок, меньше ручной рутины и меньше потерь лидов.

## Возможности

### Клиент

- просмотр категорий и доступных моделей;
- оформление брони: даты, доставка/самовывоз, контакт;
- просмотр своих заявок;
- кнопка связи с менеджером;
- кнопка SOS (для активной брони);
- раздел “Полезная информация” (для активной брони):
  - рекомендации по вождению (текст + видео),
  - путеводитель (текст + документ).

### Администратор

- добавление/удаление моделей;
- управление доступностью моделей (чекбокс-кнопки в отдельном меню);
- работа с заявками по статусам: `pending`, `active`, `rejected`, `finished`;
- подтверждение/отклонение/завершение брони;
- отправка сообщения клиенту по конкретной заявке;
- редактирование контента из админ-панели:
  - правила бронирования,
  - адрес офиса,
  - образец договора,
  - рекомендации по вождению,
  - путеводитель;
- сервисные операции:
  - удаление всех броней,
  - полная очистка базы по паролю.

## Ключевые сценарии

1. Клиент нажимает “Выбрать байк”, выбирает модель и подтверждает правила.
2. Бот создает бронь со статусом `pending` и отправляет ее администратору.
3. Админ подтверждает (`active`) или отклоняет (`rejected`) заявку.
4. При `active` у клиента становятся доступны расширенные функции (SOS, полезная информация, связь с менеджером).

## Архитектура

- [main.py](main.py) — точка входа, запуск приложения.
- [src/bot_app/runtime.py](src/bot_app/runtime.py) — инициализация бота, роутинг, общие хелперы, запуск polling.
- [src/bot_app/user_handlers.py](src/bot_app/user_handlers.py) — пользовательские обработчики.
- [src/bot_app/admin_handlers.py](src/bot_app/admin_handlers.py) — административные обработчики.
- [src/bot_app/flows.py](src/bot_app/flows.py) — пошаговые сценарии (state-flow).
- [src/bot_app/db.py](src/bot_app/db.py) — слой работы с SQLite.
- [src/bot_app/keyboards.py](src/bot_app/keyboards.py) — все inline/reply клавиатуры.
- [src/bot_app/texts.py](src/bot_app/texts.py) — шаблоны текстов.

## Технологии

- Python 3.11+
- aiogram 3.x
- SQLite

## Быстрый старт

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

Установка зависимостей и запуск:

```bash
pip install -r requirements.txt
python main.py
```

## Переменные окружения

Пример: [.env.example](.env.example)

Обязательные:

- `BOT_TOKEN` — токен Telegram-бота;
- `ADMIN_IDS` — Telegram ID админов через запятую;
- `ADMIN_PASSWORD` — пароль для полной очистки базы.

Основные:

- `DB_PATH` — путь к SQLite базе (по умолчанию `data/bikes.db`);
- `START_PHOTO_PATH` или `START_PHOTO_URL` — медиа для стартового экрана.

Сетевые параметры (устойчивость polling):

- `BOT_HTTP_TIMEOUT` — timeout HTTP-запросов;
- `BOT_POLLING_TIMEOUT` — timeout long polling;
- `BOT_HTTP_LIMIT` — лимит одновременных HTTP-соединений;
- `BOT_BACKOFF_MIN`, `BOT_BACKOFF_MAX`, `BOT_BACKOFF_FACTOR`, `BOT_BACKOFF_JITTER` — стратегия повторов при сетевых ошибках.

## Деплой

Ниже рабочий сценарий деплоя на Ubuntu-сервер через `git clone` и `systemd`.

### 1. Подключиться к серверу и установить пакеты

```bash
ssh root@<SERVER_IP>
apt update
apt install -y git python3 python3-venv python3-pip
```

### 2. Клонировать проект

```bash
mkdir -p /opt/tg-bot-rent
git clone https://github.com/alekstimakov/rentbot-nhatrang.git /opt/tg-bot-rent
cd /opt/tg-bot-rent
```

### 3. Создать виртуальное окружение и установить зависимости

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Настроить `.env`

```bash
cp .env.example .env
nano .env
```

Минимально нужно заполнить:

```env
BOT_TOKEN=...
ADMIN_IDS=123456789
ADMIN_PASSWORD=...
DB_PATH=data/bikes.db
```

Проверка токена:

```bash
TOKEN=$(grep '^BOT_TOKEN=' .env | cut -d= -f2-)
curl -s "https://api.telegram.org/bot${TOKEN}/getMe"
```

Ожидается JSON с `"ok":true`. Если `"ok":false` и `401 Unauthorized`, токен неверный.

### 5. Подготовить папку базы

```bash
mkdir -p data
```

Если есть готовая локальная база `bikes.db`, перенесите ее с Windows на сервер:

```powershell
scp "C:\Users\sanii\OneDrive\Рабочий стол\tgbot\tg bot rent\project\data\bikes.db" root@<SERVER_IP>:/opt/tg-bot-rent/data/bikes.db
```

### 6. Первый запуск в foreground (проверка)

```bash
cd /opt/tg-bot-rent
source .venv/bin/activate
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/deleteWebhook?drop_pending_updates=true"
PYTHONUNBUFFERED=1 python -u main.py
```

После запуска отправьте боту `/start` в Telegram. Остановка процесса: `Ctrl+C`.

### 7. Запуск как systemd-сервис

Проверьте файл сервиса: [deploy/tg-bot-rent.service](deploy/tg-bot-rent.service).
Если запускаете не под `ubuntu`, поменяйте `User=` на нужного пользователя.

```bash
cp /opt/tg-bot-rent/deploy/tg-bot-rent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now tg-bot-rent
systemctl status tg-bot-rent
```

Логи:

```bash
journalctl -u tg-bot-rent -f
```

### 8. Обновление бота

```bash
cd /opt/tg-bot-rent
git pull
source .venv/bin/activate
pip install -r requirements.txt
systemctl restart tg-bot-rent
```

Подробная альтернативная инструкция: [DEPLOY.md](DEPLOY.md)

## Тестирование

Ручные тест-кейсы клиента: [docs/manual_test_cases_client.md](docs/manual_test_cases_client.md)

## Частые проблемы

- `query is too old` — callback подтвержден слишком поздно (обычно не критично).
- `message is not modified` — Telegram не изменяет сообщение, если разметка уже такая же.
- `WinError 121` при polling — сетевой сбой между хостом и Telegram; рекомендуется стабильный сервер/VPS.

## Лицензия

Если планируете open-source публикацию, добавьте файл `LICENSE` (например, MIT).
