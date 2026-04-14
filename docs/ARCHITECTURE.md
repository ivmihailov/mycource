# Архитектура проекта «Мой Курс»

Этот документ описывает архитектуру проекта в форме, удобной для:

- построения UML- и C4-диаграмм;
- подготовки технической документации;
- генерации схем с помощью GPT или других LLM;
- быстрого онбординга нового разработчика.

Документ отражает текущее состояние проекта как серверно-рендеренного Django-монолита с HTMX и AI-слоем через OpenRouter.

## 1. Архитектурный стиль

Проект реализован как `Django monolith` с четким разделением по доменным приложениям.

Основные принципы:

- основной UX построен на `Django Templates`;
- точечная интерактивность реализована через `HTMX`;
- клиентская логика легкая и вспомогательная, без SPA-архитектуры;
- данные и бизнес-правила живут на стороне сервера;
- AI-интеграция вынесена в отдельный слой сервисов и провайдера;
- проект готов к переходу с `SQLite` на `PostgreSQL` без смены прикладной модели.

## 2. Технологический стек

- Backend: `Python`, `Django`, `Django ORM`
- UI: `Django Templates`, `HTMX`, `Tailwind CSS`, небольшой `vanilla JS`
- API: `Django REST Framework`, `drf-spectacular`, `Swagger UI`
- База данных: `SQLite` в текущем MVP
- AI: `OpenRouter API`
- Тесты: `pytest`, `pytest-django`, `pytest-cov`
- Деплой: `Docker`, `Docker Compose`, `Gunicorn`

## 3. Верхнеуровневая схема системы

### 3.1 Системные узлы

Система состоит из следующих крупных блоков:

1. Пользовательский браузер
2. Django web application
3. SQLite database
4. Media storage на файловой системе
5. OpenRouter API

### 3.2 Поток взаимодействия

1. Пользователь открывает страницу в браузере.
2. Запрос попадает в Django view.
3. View использует формы, сервисы и ORM.
4. Django рендерит HTML или HTMX partial.
5. Для AI-сценариев Django вызывает отдельный AI service layer.
6. AI layer обращается к OpenRouter provider.
7. Ответ модели валидируется и возвращается в UI.

### 3.3 Текстовая схема для диаграммы

```text
Browser
  -> Django URLs
  -> Django Views
  -> Forms / Permissions / Services
  -> ORM / Models
  -> SQLite

Django Views
  -> Template Rendering
  -> HTMX Partial Rendering

AI Views
  -> AI Services
  -> Prompt Builders
  -> Retrieval Layer
  -> OpenRouter Provider
  -> OpenRouter API
```

## 4. Структура приложений

Проект организован по доменным приложениям внутри каталога `apps/`.

### 4.1 `apps/core`

Назначение:

- базовые абстрактные модели;
- общие утилиты;
- валидаторы файлов;
- middleware;
- общие view и context processors;
- management commands;

Ключевые элементы:

- `TimeStampedModel`
- `SoftDeleteModel`
- `SoftDeleteQuerySet`
- `HtmxToastMessagesMiddleware`

### 4.2 `apps/users`

Назначение:

- кастомная модель пользователя;
- регистрация, логин, логаут;
- email confirmation;
- password reset;
- профиль пользователя;

Ключевая сущность:

- `User` на базе `AbstractUser`

### 4.3 `apps/courses`

Назначение:

- категории;
- теги;
- курсы;
- каталог;
- авторские страницы курсов;

Ключевые сущности:

- `Category`
- `Tag`
- `Course`

### 4.4 `apps/lessons`

Назначение:

- уроки;
- блоки уроков;
- inline lesson builder;
- сортировка уроков и блоков;
- задел под практические задания;

Ключевые сущности:

- `Lesson`
- `LessonBlock`
- `PracticeTask`

### 4.5 `apps/quizzes`

Назначение:

- тесты внутри уроков;
- вопросы и варианты ответов;
- попытки прохождения;
- AI-черновики тестов;

Ключевые сущности:

- `Quiz`
- `QuizQuestion`
- `QuizOption`
- `QuizAttempt`
- `QuizAnswer`

### 4.6 `apps/learning`

Назначение:

- прохождение курсов;
- прогресс по урокам и курсам;
- логика завершения урока;
- проверка последовательного доступа;

Ключевые сущности:

- `CourseProgress`
- `LessonProgress`

### 4.7 `apps/interactions`

Назначение:

- комментарии;
- отзывы;
- рейтинг;
- избранное;

Ключевые сущности:

- `CourseComment`
- `CourseReview`
- `FavoriteCourse`

### 4.8 `apps/ai_support`

Назначение:

- интеграция с OpenRouter;
- выбор модели;
- grounded Q&A по курсу;
- генерация тестов по содержанию урока;
- AI-настройки пользователя;
- минимальный лог AI-взаимодействий;

Ключевые сущности и слои:

- `AIModelOption`
- `AIUserPreference`
- `AIInteractionLog`
- `OpenRouterProvider`
- `ModelCatalogService`
- `CourseQnAService`
- `QuizGenerationService`
- `prompt builders`
- `schema validation`
- `retrieval layer`

### 4.9 `apps/api`

Назначение:

- read-only API;
- сериализация опубликованных сущностей;
- OpenAPI / Swagger;

## 5. Основные доменные сущности и связи

Ниже описаны ключевые связи, которые удобно переносить в ER-диаграмму.

### 5.1 Пользователи и курсы

- `User 1 -> N Course`
- один пользователь может быть автором многих курсов;
- один и тот же пользователь может быть и учеником, и автором;

### 5.2 Категории и теги

- `Category 1 -> N Course`
- `Course N <-> M Tag`

### 5.3 Курс и уроки

- `Course 1 -> N Lesson`
- уроки внутри курса имеют ручной `position`
- уникальность slug урока обеспечивается в рамках курса

### 5.4 Урок и блоки

- `Lesson 1 -> N LessonBlock`
- блоки тоже упорядочены через `position`
- тип блока определяет, какие поля у него используются

Поддерживаемые типы блока:

- `text`
- `image`
- `code`
- `file`
- `quote`
- `quiz`

### 5.5 Тесты

- `LessonBlock (quiz) 1 -> 1 Quiz`
- `Quiz 1 -> N QuizQuestion`
- `QuizQuestion 1 -> N QuizOption`
- `Quiz 1 -> N QuizAttempt`
- `QuizAttempt 1 -> N QuizAnswer`

### 5.6 Прогресс

- `User 1 -> N CourseProgress`
- `User 1 -> N LessonProgress`
- `CourseProgress` агрегирует состояние прохождения курса
- `LessonProgress` хранит статус конкретного урока и лучший результат теста

### 5.7 Взаимодействия

- `Course 1 -> N CourseComment`
- `Course 1 -> N CourseReview`
- `User 1 -> N FavoriteCourse`

### 5.8 AI-настройки

- `AIUserPreference 1 -> 1 User`
- `AIUserPreference -> AIModelOption`
- `AIInteractionLog -> User`
- `AIInteractionLog -> Course (nullable)`
- `AIInteractionLog -> Lesson (nullable)`

## 6. Схема предметной модели в текстовом виде

```text
User
  1 -> N Course
  1 -> N CourseProgress
  1 -> N LessonProgress
  1 -> N QuizAttempt
  1 -> N CourseComment
  1 -> N CourseReview
  1 -> N FavoriteCourse
  1 -> 1 AIUserPreference

Category
  1 -> N Course

Tag
  N <-> M Course

Course
  1 -> N Lesson
  1 -> N CourseComment
  1 -> N CourseReview
  1 -> N FavoriteCourse
  1 -> N AIInteractionLog

Lesson
  1 -> N LessonBlock
  1 -> N PracticeTask
  1 -> N LessonProgress
  1 -> N AIInteractionLog

LessonBlock
  (quiz type) 1 -> 1 Quiz

Quiz
  1 -> N QuizQuestion
  1 -> N QuizAttempt

QuizQuestion
  1 -> N QuizOption
  1 -> N QuizAnswer

QuizAttempt
  1 -> N QuizAnswer
```

## 7. Ключевые бизнес-сценарии

### 7.1 Каталог и просмотр курса

1. Пользователь открывает каталог.
2. Система показывает только опубликованные и не удаленные курсы.
3. Доступны поиск, фильтры и сортировка.
4. При переходе в курс пользователь видит описание, программу, отзывы, комментарии и CTA.

### 7.2 Создание курса автором

1. Автор создает курс.
2. Автор добавляет уроки.
3. Автор открывает lesson builder.
4. Автор добавляет блоки inline без перехода на отдельные страницы для каждого блока.
5. Автор публикует курс.

### 7.3 Прохождение курса студентом

1. Студент открывает курс.
2. Запускает прохождение.
3. Открывает урок.
4. Если урок без теста, завершает вручную.
5. Если урок с тестом, должен пройти его по порогу.
6. Прогресс обновляется на уровне урока и курса.

### 7.4 Комментарии, отзывы и избранное

1. Авторизованный пользователь может комментировать курс.
2. Пользователь может оставить один отзыв на курс.
3. Пользователь может добавить курс в избранное.
4. Средний рейтинг курса пересчитывается сервисом.

## 8. Lesson Builder

Lesson Builder — один из центральных UX-модулей проекта.

### 8.1 Назначение

- редактирование урока в одном экране;
- управление блоками inline;
- сортировка блоков;
- работа с quiz block без постоянной навигации между страницами;

### 8.2 Основные части builder

1. Верхняя панель урока
2. Outline со списком блоков
3. Центральная зона с карточками блоков
4. HTMX-слоты для добавления блоков между существующими

### 8.3 Техническая реализация

- shell builder рендерится сервером;
- редактирование блоков выполняется через HTMX partial update;
- reorder работает через `SortableJS` + POST endpoint;
- новые пустые блоки не создаются автоматически;
- блок появляется только после явного действия пользователя;

## 9. AI-архитектура

AI-функции изолированы в `apps/ai_support`.

### 9.1 Почему отдельный AI-слой

Это сделано, чтобы:

- не размазывать вызовы LLM по views;
- упростить замену провайдера;
- отделить prompt engineering от UI;
- централизовать выбор модели, ошибки и валидацию;

### 9.2 Слои AI-модуля

#### Provider layer

Отвечает за внешний вызов OpenRouter API.

Главный класс:

- `OpenRouterProvider`

Ответственность:

- вызов списка моделей;
- chat/completion запросы;
- обработка timeout и provider errors;

#### Model catalog layer

Главный сервис:

- `ModelCatalogService`

Ответственность:

- получить список моделей OpenRouter;
- отфильтровать текстовые модели;
- выбрать 3 роли:
  - `fast`
  - `balanced`
  - `strong`
- сохранить доступные модели;
- дать fallback через env override;

#### Preference layer

Хранит выбор модели пользователя.

Главные сущности:

- `AIModelOption`
- `AIUserPreference`

#### Retrieval layer

Главная задача:

- собрать материал курса;
- разбить содержимое на фрагменты;
- выбрать релевантные куски под вопрос;

Текущая реализация:

- text-based retrieval

Расширение в будущем:

- можно заменить на embeddings / pgvector, не ломая внешний интерфейс сервиса

#### Prompt layer

Формирует промпты для:

- student Q&A
- quiz generation

#### Schema / parsing layer

Используется для генерации тестов:

- ожидает структурированный JSON;
- валидирует вопрос, тип, варианты и баллы;

#### Service layer

Основные сервисы:

- `CourseQnAService`
- `QuizGenerationService`

### 9.3 AI-сценарий: grounded Q&A

Поток:

1. Пользователь задает вопрос на странице курса или урока.
2. View проверяет доступ.
3. Retrieval layer собирает релевантный контекст.
4. Prompt builder формирует grounded prompt.
5. Provider вызывает OpenRouter.
6. Ответ возвращается в AI drawer.
7. Если точного ответа в курсе нет, система честно сообщает это и может дать общее пояснение по теме.

### 9.4 AI-сценарий: генерация теста

Поток:

1. Автор нажимает кнопку генерации теста в lesson builder.
2. Сервис собирает текстовые блоки урока.
3. Если контента мало, генерация останавливается с понятным сообщением.
4. Если контента достаточно, prompt builder формирует запрос.
5. Provider вызывает модель.
6. Ответ валидируется как JSON-схема теста.
7. В БД создается quiz draft.
8. Автор получает черновик и редактирует его вручную.

## 10. UI-архитектура

### 10.1 Общие принципы

- страницы рендерятся на сервере;
- HTMX используется для локальных действий;
- глобальные UI-механизмы вынесены в layout-компоненты;
- интерфейс поддерживает `light/dark theme`;

### 10.2 Глобальные UI-компоненты

- `toast notifications`
- `AI drawer`
- `model switcher in navbar`
- `reusable cards / panels / empty states / headers`

### 10.3 Toast pipeline

1. Django messages формируются на сервере.
2. Для обычных page reload они попадают в `toast-container` при серверном рендере.
3. Для HTMX-запросов middleware переводит их в `HX-Trigger`.
4. Клиентский JS отображает toast и следит за дедупликацией.

### 10.4 AI drawer

- глобально присутствует в base layout;
- открывается справа;
- контент подгружается partial’ом;
- не ломает layout урока и не внедряется в основной поток текста;

## 11. Слой доступа и безопасности

### 11.1 Общие правила

- чувствительные действия доступны только авторизованным пользователям;
- редактирование курса, уроков и блоков доступно только владельцу курса или staff;
- черновики чужих курсов недоступны;
- AI endpoints тоже проверяют права доступа;

### 11.2 Проверки по AI

- student Q&A доступен только в контексте доступного курса;
- quiz generation доступна автору курса и staff;
- нельзя через AI endpoint получить чужой черновой контент;
- OpenRouter API key хранится только в env;

## 12. Слой данных и расширяемость

### 12.1 Что уже подготовлено под развитие

- soft delete;
- кастомный user model;
- service layer для AI;
- отдельный app для API;
- practice task как задел под песочницу;

### 12.2 Что можно расширять дальше

- PostgreSQL + full text search / pgvector;
- object storage для media;
- Celery / background jobs;
- версионирование курсов;
- moderation workflow;
- аналитика AI usage;

## 13. Deploy-архитектура

### 13.1 Текущий production-like deploy

Используется Docker Compose.

Контейнер:

- собирает приложение;
- применяет миграции;
- выполняет `collectstatic`;
- запускает `gunicorn`;

### 13.2 Persisted data

- `db.sqlite3` монтируется как volume/bind mount;
- `media` монтируется отдельно;

### 13.3 Restart policy

- контейнер запускается с `restart: unless-stopped`

## 14. Подсказки для построения диаграмм

Если GPT или другой инструмент должен построить диаграммы, удобно просить его сделать:

1. `C4 Context Diagram`
   - Browser
   - Django Monolith
   - SQLite
   - OpenRouter
   - File Storage

2. `C4 Container Diagram`
   - Web UI layer
   - Domain apps
   - AI services
   - API layer

3. `ER Diagram`
   - User
   - Course
   - Lesson
   - LessonBlock
   - Quiz
   - QuizQuestion
   - QuizOption
   - Progress
   - Review / Comment / Favorite
   - AIModelOption / AIUserPreference / AIInteractionLog

4. `Sequence Diagram`
   - student asks AI question
   - author generates quiz
   - author edits lesson inline

## 15. Краткое резюме

Проект — это аккуратно разделенный Django-монолит для учебной платформы, где:

- учебный контент и прохождение находятся в доменных app’ах;
- интерактивность построена на HTMX;
- AI вынесен в отдельную сервисную архитектуру;
- текущая реализация подходит для MVP, но уже имеет понятные точки роста до production.
