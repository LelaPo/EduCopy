# Telegram-бот для просмотра домашних заданий

Бот для просмотра домашних заданий из электронного дневника [authedu.mosreg.ru](https://authedu.mosreg.ru).

## Требования

- Python 3.11+
- Docker (опционально)

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd EduCopy
```

### 2. Настройка переменных окружения

Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Заполните файл `.env`:

```env
# Telegram Bot
TG_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ALLOWED_USER_ID=123456789

# Authedu API
AUTHEDU_BEARER=eyJhbGciOiJSUzI1NiIs...
STUDENT_ID=12345678
PROFILE_ID=12345678
PROFILE_TYPE=student
X_MES_SUBSYSTEM=familyweb
AUTHEDU_COOKIE=

# Прочее
TIMEZONE=Europe/Moscow
```

**Получение токенов:**

1. `TG_BOT_TOKEN` — создайте бота через [@BotFather](https://t.me/BotFather)
2. `ALLOWED_USER_ID` — ваш Telegram ID (можно узнать через [@userinfobot](https://t.me/userinfobot))
3. `AUTHEDU_BEARER`, `STUDENT_ID`, `PROFILE_ID` — получите из личного кабинета authedu.mosreg.ru (через инструменты разработчика в браузере)

### 3. Запуск

#### Через Docker (рекомендуется)

```bash
docker-compose up -d --build
```

#### Без Docker

Установите зависимости:

```bash
pip install -r requirements.txt
```

Запустите бота:

```bash
python main.py
```

## Использование

### Команды

- `/start` — начать работу с ботом
- `/admin` — управление ключами доступа (только для создателя)

### Просмотр домашних заданий

**Через кнопки:**
- «Сегодня» — ДЗ на сегодня
- «Завтра» — ДЗ на завтра
- «Неделя» — ДЗ на 7 дней вперёд
- «Выбрать дату» — ввод даты вручную

**Через ввод даты в чат:**

| Формат | Пример | Описание |
|--------|--------|----------|
| `ДД.ММ.ГГГГ` | `25.12.2025` | ДЗ на конкретную дату |
| `ГГГГ-ММ-ДД` | `2025-12-25` | ДЗ на конкретную дату (ISO) |
| `ДД.ММ-ДД.ММ` | `25.02-28.02` | ДЗ с 25 по 28 февраля |
| `ДД-ДД` | `25-28` | ДЗ с 25 по 28 число текущего месяца |
| Перечисление | `25,26,27,28` | ДЗ за перечисленные дни |

### Система доступа

Бот работает по ключам доступа. Создатель может генерировать ключи через команду `/admin` и выдавать их другим пользователям.

## Структура проекта

```
EduCopy/
├── main.py                 # Точка входа
├── app/
│   ├── config.py           # Конфигурация
│   ├── handlers/
│   │   ├── homework.py     # Обработчики команд
│   │   └── admin.py        # Админ-панель
│   ├── keyboards/
│   │   └── inline.py       # Inline-клавиатуры
│   ├── services/
│   │   ├── authedu_client.py  # API клиент
│   │   └── storage.py      # Хранение данных
│   └── utils/
│       └── formatting.py   # Форматирование вывода
├── data.json               # База данных ключей и пользователей
├── .env                    # Переменные окружения
├── docker-compose.yml      # Docker Compose
└── requirements.txt        # Зависимости Python
```

## Лицензия

Проект находится в стадии бета-тестирования.
