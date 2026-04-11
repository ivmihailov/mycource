# Мой Курс

«Мой Курс» — дипломный Django MVP-проект платформы для создания и прохождения интерактивных курсов. Проект реализован как серверно-рендеренный монолит с HTMX и ориентирован на учебный, но production-like подход: понятная архитектура, аккуратные доменные приложения, тесты, demo-data, Docker и готовность к дальнейшему развитию.

## Возможности MVP

- регистрация, вход, выход, подтверждение email и сброс пароля;
- профиль пользователя с аватаром и описанием;
- каталог курсов с поиском, фильтрацией и сортировкой;
- создание, редактирование, публикация, архивирование и soft delete курсов;
- конструктор уроков и блоков с inline-builder UX;
- drag-and-drop сортировка уроков и блоков;
- тесты внутри уроков, история попыток и автоматическая проверка;
- прогресс по урокам и курсам;
- комментарии, отзывы, рейтинг и избранное;
- mock-интеграция ИИ через отдельный сервисный слой;
- задел под практические задания и будущую песочницу;
- read-only API через DRF и Swagger/OpenAPI;
- Django admin, demo-data и тесты на ключевые сценарии;
- Docker-сборка и развёртывание через `docker compose`.

## Технологический стек

- Python 3.12+
- Django 5
- Django Templates
- HTMX
- Tailwind CSS через CDN
- SQLite
- Django REST Framework
- drf-spectacular / Swagger UI
- pytest + pytest-django + pytest-cov
- python-dotenv
- Pillow
- Markdown + bleach
- Docker + Docker Compose
- Gunicorn

## Архитектура проекта

```text
project/
  apps/
    core/          # базовые абстракции, валидаторы, layout, общие view
    users/         # кастомный пользователь, auth, профиль, email confirmation
    courses/       # категории, теги, курсы, каталог, авторские страницы
    lessons/       # уроки, блоки, практические задания, конструктор
    quizzes/       # тесты, вопросы, варианты, попытки, проверка
    learning/      # прогресс, старт/продолжение курса, lesson flow
    interactions/  # комментарии, отзывы, рейтинг, избранное
    ai_support/    # mock-ИИ и сервисный интерфейс для будущего LLM
    api/           # read-only API и OpenAPI
  config/
    settings/
      base.py
      dev.py
  docker/
  templates/
  static/
  tests/
  manage.py
  requirements.txt
  Dockerfile
  docker-compose.yml
  .env.example
```

## Важные инженерные решения

- Основной UX сделан на серверном рендеринге. SPA-фронтенд сознательно не используется.
- Tailwind подключен через CDN. Для MVP это уменьшает порог запуска и убирает обязательную Node-сборку. Для production стоит заменить на локальную сборку.
- Email confirmation построен на стандартном token generator Django.
- Soft delete включен для сущностей, где это важно для UX и истории: курсы, уроки, тесты, комментарии.
- SQLite используется как текущая БД MVP. Модели и связи спроектированы без sqlite-specific hack'ов и готовы к переходу на PostgreSQL.
- True/False в тестах поддерживается через общую модель вариантов ответов, чтобы не плодить отдельные сущности.
- Реальная интеграция ИИ и песочница кода не реализованы, но под них уже выделены app, сервисы, UI и TODO-точки расширения.
- Для локального и серверного развёртывания добавлена Docker-конфигурация с сохранением `db.sqlite3` и `media`.

## Локальный запуск без Docker

1. Создайте и активируйте виртуальное окружение:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Установите зависимости:

```powershell
pip install -r requirements.txt
```

3. Создайте `.env` на основе примера:

```powershell
Copy-Item .env.example .env
```

4. Примените миграции:

```powershell
python manage.py migrate
```

5. При необходимости загрузите demo-data:

```powershell
python manage.py seed_demo
```

6. Запустите сервер:

```powershell
python manage.py runserver
```

## Запуск через Docker

1. Создайте `.env`:

```powershell
Copy-Item .env.example .env
```

2. Соберите и запустите контейнер:

```powershell
docker compose up -d --build
```

3. Остановите контейнер:

```powershell
docker compose down
```

4. Посмотрите логи:

```powershell
docker compose logs -f web
```

Внутри контейнера автоматически выполняются:

- `python manage.py migrate --noinput`
- `python manage.py collectstatic --noinput`

## Основные URL

- главная: `http://127.0.0.1:8000/`
- каталог: `http://127.0.0.1:8000/courses/`
- Swagger: `http://127.0.0.1:8000/api/docs/`
- admin: `http://127.0.0.1:8000/admin/`

## Настройка `.env`

Минимально важные переменные:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
TIME_ZONE=Asia/Baku
SITE_PROTOCOL=http
SITE_DOMAIN=127.0.0.1:8000

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=no-reply@mycourse.local

AI_ENABLED=True
AI_PROVIDER=mock
```

Для локальной разработки можно оставить console email backend. Для реальной отправки писем замените backend на SMTP и заполните параметры почты.

## Полезные команды

Применить миграции:

```powershell
python manage.py migrate
```

Создать суперпользователя:

```powershell
python manage.py createsuperuser
```

Загрузить demo-data:

```powershell
python manage.py seed_demo
```

Запустить тесты:

```powershell
pytest
```

## Demo-data

Команда `seed_demo` создаёт:

- `admin / Admin12345!`
- `author_demo / Author12345!`
- `student_demo / Student12345!`
- 4 демо-курса, включая полноценный курс «Введение в устройство интернета»;
- уроки, блоки и тесты;
- комментарии, отзывы, избранное;
- пример прогресса прохождения.

## Email confirmation и password reset

- После регистрации пользователю отправляется письмо со ссылкой подтверждения email.
- Для сброса пароля используются встроенные view Django и отправка письма на email.
- В dev-режиме письма можно смотреть прямо в консоли, если используется console backend.

## Mock-ИИ

В проекте есть app `ai_support`, который показывает архитектурную готовность к реальной интеграции.

Что уже есть:

- интерфейс сервиса ИИ;
- mock-реализация;
- настройки `AI_ENABLED` и `AI_PROVIDER`;
- кнопки `Спросить ИИ` и `Получить совет ИИ`;
- HTMX endpoint для подгрузки mock-ответа.

Что отложено:

- подключение реального LLM;
- аудит запросов;
- лимиты и rate limiting;
- фильтрация небезопасного контента;
- управление стоимостью запросов.

## Практические задания и будущая песочница

В модели уроков уже есть `PracticeTask`. Сейчас это placeholder-функциональность:

- автор может добавить заготовку задания;
- ученик видит описание задания в уроке;
- запуск кода, хранение вывода и полноценная песочница пока не реализованы.

Это сознательное ограничение MVP.

## DRF и Swagger

DRF подключён не как основной frontend API, а как задел под будущее развитие.

Сейчас доступны read-only endpoint'ы:

- `/api/courses/`
- `/api/courses/<slug>/`
- `/api/categories/`
- `/api/tags/`

Swagger UI:

- `/api/docs/`

## Что входит в MVP

- auth и профиль;
- каталог и страницы курсов;
- конструктор курсов, уроков и блоков;
- тесты, попытки и проверка;
- прогресс обучения;
- комментарии, отзывы, избранное;
- mock-ИИ;
- демо-данные;
- admin;
- тесты;
- Docker-развёртывание;
- README.

## Что не входит в MVP

- платежи и подписки;
- чат между пользователями;
- сертификаты;
- видео-блоки;
- модерация публикации;
- реальная интеграция ИИ;
- полноценная песочница выполнения кода;
- асинхронные очереди, Celery, WebSocket.

## Тестирование

Базовые тесты покрывают:

- soft delete;
- генерацию slug;
- обновление рейтинга курса;
- прогресс уроков и курсов;
- проверку тестов;
- регистрацию и отправку email;
- подтверждение email;
- создание курса;
- ограничение доступа к чужим черновикам;
- комментарии, отзывы и избранное;
- последовательное прохождение уроков;
- builder-flow и ключевые UI smoke-сценарии.

## Серверное развёртывание

Проект уже успешно разворачивался на чистом Ubuntu-сервере через Docker:

- установка Docker Engine и Docker Compose plugin;
- перенос проекта, `db.sqlite3` и `media`;
- запуск через `docker compose`;
- публикация сайта на `80` порту;
- restart policy: `unless-stopped`.

Это можно использовать как базовый шаблон для дальнейшего production-деплоя.

## Что можно развивать дальше

- вынести Tailwind из CDN в локальную сборку;
- добавить richer Markdown preview;
- улучшить editor UX для тестов и блоков;
- подключить PostgreSQL;
- вынести reverse proxy в Nginx;
- добавить HTTPS и домен;
- реализовать аудит действий автора;
- добавить реальную интеграцию ИИ и безопасную песочницу.
