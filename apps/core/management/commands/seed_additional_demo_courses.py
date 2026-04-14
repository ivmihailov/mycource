from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.courses.models import Category, Course, Tag
from apps.lessons.models import Lesson, LessonBlock
from apps.quizzes.models import Quiz, QuizOption, QuizQuestion

User = get_user_model()


class Command(BaseCommand):
    help = "Добавляет два расширенных демонстрационных курса по IT и AI."

    @transaction.atomic
    def handle(self, *args, **options):
        author = User.objects.filter(username="author_demo").first() or User.objects.filter(is_staff=True).first()
        if author is None:
            self.stderr.write(self.style.ERROR("Не найден author_demo или staff-пользователь для создания демо-курсов."))
            return

        categories = {
            "ai": self._category("Искусственный интеллект"),
            "devops": self._category("DevOps"),
        }
        tags = {
            "ai": self._tag("ai"),
            "ml": self._tag("machine-learning"),
            "llm": self._tag("llm"),
            "mlops": self._tag("mlops"),
            "devops": self._tag("devops"),
            "apis": self._tag("api"),
            "monitoring": self._tag("monitoring"),
            "deployment": self._tag("deployment"),
        }

        self._create_machine_learning_course(author, categories["ai"], tags)
        self._create_ai_product_course(author, categories["devops"], tags)

        self.stdout.write(self.style.SUCCESS("Дополнительные демонстрационные курсы готовы."))

    def _category(self, name):
        category, _ = Category.objects.get_or_create(
            name=name,
            defaults={"description": f"Учебные материалы по теме: {name}.", "is_active": True},
        )
        if not category.is_active:
            category.is_active = True
            category.save(update_fields=["is_active", "updated_at"])
        return category

    def _tag(self, name):
        tag, _ = Tag.objects.get_or_create(name=name)
        return tag

    def _create_course(self, *, author, title, short_description, full_description, category, tags, level, duration, order_mode):
        course, created = Course.all_objects.get_or_create(
            author=author,
            title=title,
            defaults={
                "short_description": short_description,
                "full_description": full_description,
                "category": category,
                "level": level,
                "estimated_duration_minutes": duration,
                "order_mode": order_mode,
                "status": Course.Status.PUBLISHED,
                "published_at": timezone.now(),
                "view_count": 0,
            },
        )
        if course.is_deleted:
            course.restore()
        course.short_description = short_description
        course.full_description = full_description
        course.category = category
        course.level = level
        course.estimated_duration_minutes = duration
        course.order_mode = order_mode
        course.status = Course.Status.PUBLISHED
        course.published_at = course.published_at or timezone.now()
        course.save()
        course.tags.set(tags)
        if not created and course.lessons.exists():
            self.stdout.write(f"Курс '{title}' уже существует, уроки оставлены без изменений.")
        return course, created

    def _create_machine_learning_course(self, author, category, tags):
        course, created = self._create_course(
            author=author,
            title="Практическое введение в машинное обучение",
            short_description=(
                "Спокойный и прикладной курс о том, как устроено машинное обучение: от данных и признаков "
                "до обучения, оценки качества и внедрения модели в реальный продукт."
            ),
            full_description=(
                "## О курсе\n"
                "Курс показывает машинное обучение как инженерный процесс, а не как магию. "
                "Мы пройдем путь от постановки задачи до проверки качества модели и разберем, "
                "почему хорошие результаты зависят не только от алгоритма, но и от данных, "
                "метрик, инфраструктуры и продукта.\n\n"
                "### Внутри курса\n"
                "- 4 развернутых урока;\n"
                "- разбор терминов простым языком;\n"
                "- небольшие кодовые примеры на Python;\n"
                "- тесты для самопроверки после каждой темы."
            ),
            category=category,
            tags=[tags["ai"], tags["ml"], tags["apis"]],
            level=Course.Level.BEGINNER,
            duration=150,
            order_mode=Course.OrderMode.SEQUENTIAL,
        )
        if not created and course.lessons.exists():
            return

        lessons = [
            {
                "title": "Как выглядит задача машинного обучения",
                "short_description": "Разбираем, чем ML-задача отличается от обычной автоматизации и как формулировать цель модели.",
                "blocks": [
                    ("text", "От задачи к данным", "Машинное обучение начинается не с выбора модели, а с ясного ответа на вопрос: **что именно мы хотим предсказать или классифицировать**.\n\nЕсли цель расплывчата, команда часто строит красивую, но бесполезную модель. Поэтому сначала важно описать сценарий: кто будет пользоваться результатом, в какой момент, какие ошибки наиболее критичны и как будет выглядеть полезный выход системы."),
                    ("quote", "Практическое правило", "Хорошая постановка ML-задачи отвечает не только на вопрос *что предсказать*, но и на вопрос *как решение будет влиять на продукт и пользователя*.", "quote"),
                    ("text", "Основные типы задач", "На базовом уровне задачи ML удобно делить на несколько групп:\n\n- **классификация** — выбрать класс объекта;\n- **регрессия** — предсказать число;\n- **ранжирование** — упорядочить объекты по полезности;\n- **кластеризация** — найти похожие группы без готовых меток.\n\nВ реальном продукте одна задача часто превращается в комбинацию нескольких подходов."),
                    ("code", "Минимальная схема пайплайна", "python", "problem = 'predict_churn'\ndata = load_customer_events()\nfeatures = build_features(data)\ntrain, test = split_dataset(features)\nmodel = train_model(train)\nscore = evaluate(model, test)\nprint(score)"),
                ],
                "quiz": {
                    "title": "Проверка: постановка задачи",
                    "description": "Короткий тест по целям и типам задач ML.",
                    "passing_score": 3,
                    "questions": [
                        {"type": QuizQuestion.QuestionType.SINGLE, "text": "С чего начинается рабочая ML-задача?", "score": 1, "options": [("С выбора самой сложной модели", False), ("С понятной бизнес-цели и формулировки результата", True), ("С покупки GPU", False)]},
                        {"type": QuizQuestion.QuestionType.MULTIPLE, "text": "Какие типы задач относятся к базовым сценариям ML?", "score": 1, "options": [("Классификация", True), ("Регрессия", True), ("Сжатие ZIP-архивов", False), ("Кластеризация", True)]},
                        {"type": QuizQuestion.QuestionType.TRUE_FALSE, "text": "Если задача сформулирована расплывчато, модель может оказаться бесполезной для продукта.", "score": 1, "options": [("Верно", True), ("Неверно", False)]},
                    ],
                },
            },
            {
                "title": "Данные, признаки и подготовка датасета",
                "short_description": "Смотрим, как качество данных влияет на результат и почему признаки важнее экзотических моделей.",
                "blocks": [
                    ("text", "Почему данные важнее архитектуры", "Во многих прикладных проектах именно данные становятся главным ограничением. Если в датасете много шумных записей, пропусков или смещений, то даже сильная модель будет ошибаться системно.\n\nПоэтому команде важно уметь отвечать на вопросы: откуда пришли данные, насколько они репрезентативны, как часто обновляются и есть ли в них утечки будущей информации."),
                    ("text", "Что такое признаки", "Признак — это измеримая характеристика объекта, которую мы подаем модели. Например, для задачи прогнозирования оттока клиента признаками могут быть число входов в систему, длительность подписки, число обращений в поддержку и наличие просрочки по оплате.\n\nХорошие признаки отражают полезную структуру задачи и помогают модели различать важные закономерности."),
                    ("quote", "Инженерное наблюдение", "Если команда не понимает природу данных, она редко понимает и природу ошибок модели.", "note"),
                    ("code", "Пример подготовки признаков", "python", "df['is_active_week'] = df['sessions_last_7d'] > 0\ndf['support_load'] = df['tickets_last_30d'] / 30\nfeatures = df[['tenure_days', 'sessions_last_7d', 'support_load']]\nlabels = df['churned']"),
                ],
                "quiz": {
                    "title": "Проверка: данные и признаки",
                    "description": "Вопросы о качестве данных и признаках.",
                    "passing_score": 3,
                    "questions": [
                        {"type": QuizQuestion.QuestionType.SINGLE, "text": "Что чаще всего ограничивает качество прикладной ML-системы?", "score": 1, "options": [("Неудачное имя файла", False), ("Качество и структура данных", True), ("Размер favicon сайта", False)]},
                        {"type": QuizQuestion.QuestionType.MULTIPLE, "text": "Что важно проверить в данных перед обучением?", "score": 1, "options": [("Пропуски", True), ("Смещения и репрезентативность", True), ("Есть ли красивый градиент в дашборде", False), ("Утечку будущей информации", True)]},
                        {"type": QuizQuestion.QuestionType.TRUE_FALSE, "text": "Признак — это характеристика объекта, которую модель использует для вывода.", "score": 1, "options": [("Верно", True), ("Неверно", False)]},
                    ],
                },
            },
            {
                "title": "Обучение модели и оценка качества",
                "short_description": "Разбираем train/test split, метрики и смысл валидации без лишней математики.",
                "blocks": [
                    ("text", "Зачем делить данные", "Если обучать и проверять модель на одном и том же наборе записей, мы рискуем принять запоминание за обобщение. Поэтому данные обычно делят хотя бы на train и test.\n\nИдея проста: на train модель учится, а на test мы проверяем, как она работает на новых примерах, которых не видела раньше."),
                    ("text", "Почему одной точности мало", "Метрика должна соответствовать риску продукта. В задаче обнаружения мошенничества простая accuracy может быть обманчивой: если мошенничества мало, модель может часто угадывать класс большинства, но пропускать действительно важные случаи.\n\nПоэтому команды смотрят на precision, recall, F1, ROC-AUC или другие метрики в зависимости от сценария."),
                    ("code", "Минимальная оценка модели", "python", "from sklearn.model_selection import train_test_split\nfrom sklearn.metrics import f1_score\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\nmodel.fit(X_train, y_train)\npred = model.predict(X_test)\nprint(f1_score(y_test, pred))"),
                    ("quote", "Полезная мысль", "Хорошая метрика не просто измеряет модель, а помогает команде принимать продуктовые решения.", "quote"),
                ],
                "quiz": {
                    "title": "Проверка: оценка качества",
                    "description": "Проверяем понимание train/test и метрик.",
                    "passing_score": 3,
                    "questions": [
                        {"type": QuizQuestion.QuestionType.SINGLE, "text": "Зачем нужен test-набор?", "score": 1, "options": [("Чтобы модель дольше обучалась", False), ("Чтобы проверить обобщающую способность на новых данных", True), ("Чтобы скрыть данные от аналитиков", False)]},
                        {"type": QuizQuestion.QuestionType.MULTIPLE, "text": "Какие метрики часто используют в задачах классификации?", "score": 1, "options": [("Precision", True), ("Recall", True), ("F1", True), ("Температура процессора", False)]},
                        {"type": QuizQuestion.QuestionType.TRUE_FALSE, "text": "Высокая accuracy всегда означает, что модель подходит бизнесу.", "score": 1, "options": [("Верно", False), ("Неверно", True)]},
                    ],
                },
            },
            {
                "title": "Как довести модель до продукта",
                "short_description": "Смотрим на внедрение модели, мониторинг и типичные причины деградации после запуска.",
                "blocks": [
                    ("text", "После ноутбука начинается реальная работа", "Запуск модели в продукте требует больше, чем обученный файл весов. Нужно определить, где будет выполняться инференс, какие ограничения по задержке допустимы, как обновлять данные и как объяснять результат другим частям системы.\n\nОчень часто проект становится успешным не потому, что в нем самая умная модель, а потому, что у него надежный и понятный рабочий процесс после релиза."),
                    ("text", "Почему нужен мониторинг", "Даже хорошая модель со временем начинает ошибаться чаще, если меняется поведение пользователей, каналы данных или бизнес-процесс. Это называют data drift и concept drift.\n\nПоэтому после запуска важно следить за распределением признаков, качеством предсказаний и техническими метриками сервиса."),
                    ("code", "Идея production-проверок", "python", "prediction = model.predict(batch)\nlatency_ms = measure_latency()\nif latency_ms > 300:\n    alert('latency spike')\nif drift_detector.is_drifted(batch_features):\n    alert('feature drift detected')"),
                    ("quote", "Итог курса", "ML-проект становится зрелым тогда, когда команда умеет поддерживать модель после релиза, а не только обучать ее один раз.", "note"),
                ],
                "quiz": {
                    "title": "Проверка: запуск в продукт",
                    "description": "Короткий тест о deployment и мониторинге.",
                    "passing_score": 3,
                    "questions": [
                        {"type": QuizQuestion.QuestionType.SINGLE, "text": "Что нужно продумать после обучения модели?", "score": 1, "options": [("Только цвет карточки в презентации", False), ("Где и как выполнять инференс, мониторинг и обновление", True), ("Только название файла с моделью", False)]},
                        {"type": QuizQuestion.QuestionType.MULTIPLE, "text": "Что может сигнализировать о деградации модели после релиза?", "score": 1, "options": [("Drift данных", True), ("Рост задержки сервиса", True), ("Изменение пользовательского поведения", True), ("Наличие темной темы на сайте", False)]},
                        {"type": QuizQuestion.QuestionType.TRUE_FALSE, "text": "Production ML заканчивается в момент первого успешного обучения модели.", "score": 1, "options": [("Верно", False), ("Неверно", True)]},
                    ],
                },
            },
        ]
        self._build_lessons(course, lessons)

    def _create_ai_product_course(self, author, category, tags):
        course, created = self._create_course(
            author=author,
            title="Архитектура современных AI-приложений",
            short_description=(
                "Курс о том, как проектируют продукты вокруг LLM: от выбора модели и retrieval до "
                "проверки качества, безопасности и эксплуатации в production."
            ),
            full_description=(
                "## О курсе\n"
                "Этот курс помогает увидеть AI-приложение как систему из нескольких слоев: "
                "интерфейса, orchestration, retrieval, самой модели, guardrails и наблюдаемости. "
                "Подходит для разработчиков и авторов проектов, которые хотят понимать, "
                "из чего состоит современный AI-сервис и где появляются реальные инженерные риски.\n\n"
                "### После курса\n"
                "- станет понятнее, как выбирать модель под сценарий;\n"
                "- вы увидите, почему retrieval и prompt design не заменяют архитектуру;\n"
                "- разберетесь, как валидировать выход модели и что мониторить после релиза."
            ),
            category=category,
            tags=[tags["ai"], tags["llm"], tags["mlops"], tags["deployment"], tags["monitoring"]],
            level=Course.Level.INTERMEDIATE,
            duration=170,
            order_mode=Course.OrderMode.SEQUENTIAL,
        )
        if not created and course.lessons.exists():
            return

        lessons = [
            {
                "title": "Из чего состоит AI-приложение",
                "short_description": "Собираем картину: интерфейс, orchestration, модель, retrieval и guardrails.",
                "blocks": [
                    ("text", "AI-продукт — это не только модель", "Пользователь обычно видит чат-окно или кнопку генерации, но внутри AI-приложение состоит из нескольких уровней. Есть клиентский интерфейс, серверная логика, маршрутизация запросов, выбор модели, контекст из базы знаний и правила постобработки ответа.\n\nЕсли игнорировать эти слои, проект быстро начинает вести себя нестабильно: ответы становятся непредсказуемыми, стоимость растет, а поддержка превращается в ручную диагностику."),
                    ("text", "Базовая архитектурная схема", "Минимальный production-сценарий часто включает:\n\n- входной запрос пользователя;\n- нормализацию и проверку запроса;\n- сбор контекста;\n- вызов модели;\n- валидацию и форматирование результата;\n- логирование и метрики.\n\nТакой разбор помогает не переоценивать сам LLM-слой и видеть систему целиком."),
                    ("quote", "Архитектурный принцип", "Чем дороже ошибка модели, тем сильнее вокруг нее должны быть защитные слои.", "quote"),
                    ("code", "Схема вызова", "python", "request = receive_user_prompt()\ncontext = retrieval_service.fetch(request)\ncompletion = llm.generate(prompt=request, context=context)\nanswer = validator.clean(completion)\nreturn response_builder.render(answer)"),
                ],
                "quiz": {
                    "title": "Проверка: состав AI-приложения",
                    "description": "Проверяем понимание основных слоев.",
                    "passing_score": 3,
                    "questions": [
                        {"type": QuizQuestion.QuestionType.SINGLE, "text": "Что является только одной частью AI-приложения, но не всей системой?", "score": 1, "options": [("LLM-модель", True), ("Логирование", False), ("Валидация ответа", False)]},
                        {"type": QuizQuestion.QuestionType.MULTIPLE, "text": "Какие слои часто входят в AI-приложение?", "score": 1, "options": [("Интерфейс", True), ("Retrieval", True), ("Валидация вывода", True), ("Случайный набор CSS-классов", False)]},
                        {"type": QuizQuestion.QuestionType.TRUE_FALSE, "text": "Если не учитывать архитектурные слои вокруг LLM, продукт может стать нестабильным.", "score": 1, "options": [("Верно", True), ("Неверно", False)]},
                    ],
                },
            },
            {
                "title": "Как выбирать модель под сценарий",
                "short_description": "Разбираем компромиссы между скоростью, стоимостью, контекстом и качеством ответа.",
                "blocks": [
                    ("text", "Нет одной лучшей модели навсегда", "Модель подбирают под задачу. Для коротких справочных ответов важны скорость и цена, для генерации структурированного контента — устойчивость к формату, а для сложного reasoning — качество и размер контекста.\n\nПоэтому зрелые продукты редко завязываются на один-единственный режим работы. Обычно у системы есть несколько ролей моделей и логика выбора между ними."),
                    ("text", "На что смотрит команда", "При выборе модели удобно оценивать несколько параметров одновременно: стоимость запроса, задержку ответа, качество на вашем домене, максимальный контекст, поддержку JSON/structured output и стабильность провайдера.\n\nВажно сравнивать модели именно на реальных сценариях продукта, а не только по бенчмаркам."),
                    ("code", "Пример выбора профиля", "python", "if task_type == 'faq':\n    model = 'fast'\nelif task_type == 'quiz_generation':\n    model = 'balanced'\nelse:\n    model = 'strong'"),
                    ("quote", "Практическое замечание", "Дорогая модель не всегда выгоднее: если сценарий простой, быстрая модель может давать лучший итоговый UX.", "note"),
                ],
                "quiz": {
                    "title": "Проверка: выбор модели",
                    "description": "Вопросы о компромиссах при выборе модели.",
                    "passing_score": 3,
                    "questions": [
                        {"type": QuizQuestion.QuestionType.SINGLE, "text": "Что обычно важно для коротких справочных ответов?", "score": 1, "options": [("Только самый большой контекст", False), ("Скорость и стоимость", True), ("Максимально сложная цепочка промптов", False)]},
                        {"type": QuizQuestion.QuestionType.MULTIPLE, "text": "Какие критерии полезно сравнивать между моделями?", "score": 1, "options": [("Цена", True), ("Задержка", True), ("Поддержка структурированного вывода", True), ("Цвет логотипа провайдера", False)]},
                        {"type": QuizQuestion.QuestionType.TRUE_FALSE, "text": "Одна и та же модель всегда оптимальна для любого AI-сценария.", "score": 1, "options": [("Верно", False), ("Неверно", True)]},
                    ],
                },
            },
            {
                "title": "Retrieval, grounding и работа с контекстом",
                "short_description": "Понимаем, как связывать LLM с материалами курса, базы знаний или документации.",
                "blocks": [
                    ("text", "Зачем нужен retrieval", "Если модель отвечает только из общего предобучения, она не знает вашей внутренней документации, свежих правил и конкретного содержания курса. Retrieval позволяет сначала найти релевантные фрагменты, а затем подать их модели как контекст.\n\nЭто снижает риск галлюцинаций и делает ответ привязанным к реальному источнику."),
                    ("text", "Grounding важнее красивой формулировки", "Даже хороший промпт не заменит качественный контекст. Поэтому retrieval-система должна уметь разбивать источник на фрагменты, находить релевантные куски и передавать модели только то, что действительно связано с вопросом.\n\nИменно на этом уровне часто решается, будет ли ответ полезным или слишком общим."),
                    ("code", "Упрощенный retrieval flow", "python", "chunks = chunk_source_documents(documents)\nrelevant = ranker.top_k(chunks, query=user_question, k=4)\nanswer = llm.generate(question=user_question, context=relevant)"),
                    ("quote", "Ключевая мысль", "LLM без grounding может звучать уверенно, но grounded-ответ ценен тем, что его можно соотнести с конкретным источником.", "quote"),
                ],
                "quiz": {
                    "title": "Проверка: retrieval и grounding",
                    "description": "Короткий тест по работе с контекстом.",
                    "passing_score": 3,
                    "questions": [
                        {"type": QuizQuestion.QuestionType.SINGLE, "text": "Для чего AI-системе нужен retrieval?", "score": 1, "options": [("Чтобы случайно менять тему разговора", False), ("Чтобы находить релевантный контекст перед вызовом модели", True), ("Чтобы отключать логирование", False)]},
                        {"type": QuizQuestion.QuestionType.MULTIPLE, "text": "Что помогает сделать ответ grounded?", "score": 1, "options": [("Релевантные фрагменты источников", True), ("Привязка к документации или содержанию курса", True), ("Передача модели случайных нерелевантных кусочков", False), ("Ограничение ответа рамками найденного контекста", True)]},
                        {"type": QuizQuestion.QuestionType.TRUE_FALSE, "text": "Красивый промпт полностью заменяет качественный retrieval.", "score": 1, "options": [("Верно", False), ("Неверно", True)]},
                    ],
                },
            },
            {
                "title": "Надежность, валидация и эксплуатация",
                "short_description": "Разбираем ошибки модели, structured output, monitoring и безопасный запуск AI-фичей.",
                "blocks": [
                    ("text", "Почему нужен контроль выхода модели", "AI-функция кажется удобной только пока ответы соответствуют ожиданиям интерфейса и бизнес-правилам. Как только продукту нужен JSON, тест, письмо или карточка задачи, система должна проверять структуру вывода и уметь корректно обрабатывать ошибки.\n\nПоэтому production AI почти всегда включает schema validation, fallback-режимы и пользовательские сообщения без stack trace."),
                    ("text", "Что мониторить после релиза", "Помимо технических метрик вроде задержки и частоты ошибок, важно смотреть на продуктовые сигналы: долю успешных ответов, частоту ручных исправлений, отказов пользователей и стоимость по сценариям.\n\nЕсли это не измерять, команда быстро теряет понимание, где система реально помогает, а где просто выглядит эффектно."),
                    ("code", "Пример безопасного цикла", "python", "response = provider.generate(prompt)\nparsed = schema_parser.try_parse(response)\nif not parsed.ok:\n    logger.warning('ai_parse_failed')\n    return {'error': 'Не удалось подготовить корректный ответ'}\nreturn parsed.value"),
                    ("quote", "Финальный ориентир", "Надежный AI-продукт — это не тот, где модель отвечает всегда, а тот, где система умеет корректно переживать ошибки модели.", "note"),
                ],
                "quiz": {
                    "title": "Проверка: надежность AI-приложения",
                    "description": "Финальный тест по валидации и эксплуатации.",
                    "passing_score": 3,
                    "questions": [
                        {"type": QuizQuestion.QuestionType.SINGLE, "text": "Зачем нужен schema validation в AI-сценариях?", "score": 1, "options": [("Чтобы ответ совпадал с ожидаемой структурой", True), ("Чтобы сделать кнопку красивее", False), ("Чтобы не хранить логи", False)]},
                        {"type": QuizQuestion.QuestionType.MULTIPLE, "text": "Что полезно мониторить после релиза AI-функции?", "score": 1, "options": [("Задержку", True), ("Ошибки и parse failures", True), ("Стоимость сценариев", True), ("Только цвет toast-уведомлений", False)]},
                        {"type": QuizQuestion.QuestionType.TRUE_FALSE, "text": "Production AI должен уметь корректно обрабатывать ошибки модели и не показывать пользователю stack trace.", "score": 1, "options": [("Верно", True), ("Неверно", False)]},
                    ],
                },
            },
        ]
        self._build_lessons(course, lessons)

    def _build_lessons(self, course, lessons):
        for index, lesson_data in enumerate(lessons, start=1):
            lesson, created = Lesson.all_objects.get_or_create(
                course=course,
                title=lesson_data["title"],
                defaults={
                    "short_description": lesson_data["short_description"],
                    "position": index,
                    "estimated_duration_minutes": 35,
                },
            )
            if lesson.is_deleted:
                lesson.restore()
            lesson.short_description = lesson_data["short_description"]
            lesson.position = index
            lesson.estimated_duration_minutes = 35
            lesson.save()
            if not created and lesson.blocks.exists():
                continue

            for block_index, block_data in enumerate(lesson_data["blocks"], start=1):
                block_type, title, payload, *extra = block_data
                block = LessonBlock.objects.create(
                    lesson=lesson,
                    block_type=block_type,
                    title=title,
                    position=block_index,
                )
                if block_type == LessonBlock.BlockType.CODE:
                    block.code_language = extra[0]
                    block.code_content = payload
                else:
                    block.content_markdown = payload
                    if block_type == LessonBlock.BlockType.QUOTE and extra:
                        block.note_style = extra[0]
                block.save()

            self._attach_quiz(lesson, lesson_data["quiz"], len(lesson_data["blocks"]) + 1)

    def _attach_quiz(self, lesson, quiz_data, position):
        block = LessonBlock.objects.create(
            lesson=lesson,
            block_type=LessonBlock.BlockType.QUIZ,
            title=quiz_data["title"],
            position=position,
        )
        quiz = Quiz.objects.create(
            lesson_block=block,
            title=quiz_data["title"],
            description=quiz_data["description"],
            passing_score=quiz_data["passing_score"],
        )
        for question_index, question_data in enumerate(quiz_data["questions"], start=1):
            question = QuizQuestion.objects.create(
                quiz=quiz,
                question_type=question_data["type"],
                text=question_data["text"],
                score=question_data["score"],
                position=question_index,
            )
            for option_index, (option_text, is_correct) in enumerate(question_data["options"], start=1):
                QuizOption.objects.create(
                    question=question,
                    text=option_text,
                    is_correct=is_correct,
                    position=option_index,
                )
        quiz.update_max_score()
