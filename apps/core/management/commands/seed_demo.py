from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.courses.models import Category, Course, Tag
from apps.courses.services import normalize_categories
from apps.interactions.models import CourseComment, CourseReview, FavoriteCourse
from apps.interactions.services import refresh_course_rating
from apps.learning.services import mark_lesson_completed_manually, open_lesson, sync_progress_after_quiz_attempt
from apps.lessons.models import Lesson, LessonBlock, PracticeTask
from apps.quizzes.models import Quiz, QuizAnswer, QuizAttempt, QuizOption, QuizQuestion

User = get_user_model()


class Command(BaseCommand):
    help = "Заполняет проект демонстрационными данными для дипломной презентации."

    @transaction.atomic
    def handle(self, *args, **options):
        self._create_user(
            username="admin",
            email="admin@example.com",
            password="Admin12345!",
            is_staff=True,
            is_superuser=True,
            first_name="System",
            last_name="Admin",
        )
        author = self._create_user(
            username="author_demo",
            email="author@example.com",
            password="Author12345!",
            first_name="Анна",
            last_name="Авторова",
            bio="Автор демонстрационных курсов по вебу, интерфейсам и базовой инженерной грамотности.",
        )
        student = self._create_user(
            username="student_demo",
            email="student@example.com",
            password="Student12345!",
            first_name="Илья",
            last_name="Студентов",
            bio="Демо-аккаунт студента для показа обучения, прогресса и взаимодействий на платформе.",
        )

        categories = self._create_categories()
        normalize_categories()
        categories = {
            "networks": Category.objects.get(name="Сети"),
            "programming": Category.objects.get(name="Программирование"),
            "ux": Category.objects.get(name="UI/UX"),
            "databases": Category.objects.get(name="Базы данных"),
        }
        tags = self._create_tags()

        internet_course = self._create_course(
            author=author,
            title="Введение в устройство интернета",
            short_description=(
                "Понятное введение в то, как работает интернет: от сетей и IP-адресов до DNS, HTTP, "
                "браузера, серверов и передачи данных между устройствами."
            ),
            full_description=(
                "## О курсе\n"
                "Этот курс помогает без перегруза понять, что именно происходит, когда пользователь вводит адрес сайта "
                "в браузере и получает страницу на экране.\n\n"
                "### Что вы разберете\n"
                "- чем интернет отличается от веба;\n"
                "- как устройства находят друг друга по IP и MAC;\n"
                "- зачем нужен DNS и как браузер проходит путь от URL до сервера;\n"
                "- что такое HTTP, HTTPS, запросы, ответы и статус-коды;\n"
                "- почему современный сайт состоит не из одного файла, а из набора ресурсов.\n\n"
                "### Формат\n"
                "В курсе есть теоретические блоки, заметки, схемы, кодовые примеры, полезные файлы и тесты после "
                "каждого урока. Это демонстрационный курс для показа возможностей платформы, но его содержание "
                "написано как полноценное вводное объяснение для новичка."
            ),
            category=categories["networks"],
            tags=[
                tags["internet"],
                tags["networks"],
                tags["web"],
                tags["dns"],
                tags["http"],
                tags["browser"],
            ],
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            order_mode=Course.OrderMode.SEQUENTIAL,
            estimated_duration_minutes=105,
            view_count=84,
        )
        python_course = self._create_course(
            author=author,
            title="Основы Python для начинающих",
            short_description="Базовый курс по синтаксису, функциям и структурам данных для первого уверенного старта.",
            full_description=(
                "## О курсе\n"
                "Курс помогает сделать первые уверенные шаги в Python: разобраться с типами данных, условиями, "
                "циклами, функциями и базовой структурой небольших скриптов."
            ),
            category=categories["programming"],
            tags=[tags["python"], tags["web"]],
            level=Course.Level.BEGINNER,
            status=Course.Status.PUBLISHED,
            order_mode=Course.OrderMode.SEQUENTIAL,
            estimated_duration_minutes=80,
            view_count=61,
        )
        ux_course = self._create_course(
            author=author,
            title="Проектирование UX для учебных платформ",
            short_description=(
                "Как проектировать понятные учебные интерфейсы, снижать когнитивную нагрузку и поддерживать рабочий ритм обучения."
            ),
            full_description=(
                "## О курсе\n"
                "Небольшой курс о проектировании образовательных интерфейсов: от структуры экрана до роли текста, "
                "пустых состояний, обратной связи и сценариев автора и ученика."
            ),
            category=categories["ux"],
            tags=[tags["ux"], tags["web"]],
            level=Course.Level.INTERMEDIATE,
            status=Course.Status.PUBLISHED,
            order_mode=Course.OrderMode.FREE,
            estimated_duration_minutes=70,
            view_count=39,
        )
        sql_course = self._create_course(
            author=author,
            title="SQL для анализа данных",
            short_description="Черновик курса о базовых SQL-запросах, фильтрации данных и чтении табличных результатов.",
            full_description=(
                "## Черновик курса\n"
                "Этот курс остается в статусе черновика и нужен для демонстрации авторского сценария с приватными материалами."
            ),
            category=categories["databases"],
            tags=[tags["sql"], tags["analytics"]],
            level=Course.Level.BEGINNER,
            status=Course.Status.DRAFT,
            order_mode=Course.OrderMode.SEQUENTIAL,
            estimated_duration_minutes=60,
            view_count=0,
        )

        self._populate_internet_course(internet_course)
        self._populate_python_course(python_course)
        self._populate_ux_course(ux_course)
        self._populate_sql_draft(sql_course)

        self._create_interactions(student=student, author=author, courses=[internet_course, python_course, ux_course])
        self._simulate_learning(student=student, active_course=internet_course, completed_course=python_course)

        self.stdout.write(self.style.SUCCESS("Демо-данные успешно загружены."))
        self.stdout.write("admin / Admin12345!")
        self.stdout.write("author_demo / Author12345!")
        self.stdout.write("student_demo / Student12345!")

    def _create_user(self, username, email, password, **extra_fields):
        user, created = User.objects.get_or_create(username=username, defaults={"email": email, **extra_fields})
        if not created:
            for field, value in extra_fields.items():
                setattr(user, field, value)
        user.email = email
        user.is_email_verified = True
        user.set_password(password)
        user.save()
        return user

    def _create_categories(self):
        definitions = {
            "networks": {
                "name": "Сети и веб",
                "description": "Курсы о сетях, браузерах, протоколах и устройстве веба.",
            },
            "programming": {
                "name": "Программирование",
                "description": "Базовые и прикладные курсы по коду, языкам и инженерной практике.",
            },
            "ux": {
                "name": "UX и дизайн",
                "description": "Курсы о структуре интерфейсов, сценариях пользователя и учебном опыте.",
            },
            "analytics": {
                "name": "Аналитика",
                "description": "Курсы по работе с табличными данными, запросами и метриками.",
            },
        }
        categories = {}
        for key, data in definitions.items():
            category, _ = Category.objects.get_or_create(name=data["name"], defaults=data)
            category.description = data["description"]
            category.is_active = True
            category.save()
            categories[key] = category
        return categories

    def _create_tags(self):
        tag_names = {
            "internet": "интернет",
            "networks": "сети",
            "web": "веб",
            "dns": "dns",
            "http": "http",
            "browser": "браузер",
            "python": "python",
            "ux": "ux",
            "sql": "sql",
            "analytics": "аналитика",
        }
        return {key: Tag.objects.get_or_create(name=name)[0] for key, name in tag_names.items()}

    def _create_course(self, *, tags, **kwargs):
        course, _ = Course.all_objects.get_or_create(
            title=kwargs["title"],
            author=kwargs["author"],
            defaults=kwargs,
        )
        for field, value in kwargs.items():
            setattr(course, field, value)
        if course.status == Course.Status.PUBLISHED:
            course.published_at = course.published_at or timezone.now()
        else:
            course.published_at = None
        course.save()
        course.tags.set(tags)
        return course

    def _populate_internet_course(self, course):
        if course.lessons.filter(is_deleted=False).exists():
            return

        lesson_one = Lesson.objects.create(
            course=course,
            title="Что такое интернет и как устройства находят друг друга",
            short_description="Разбираемся, почему интернет — это сеть сетей и как пакет находит путь между устройствами.",
            position=1,
            estimated_duration_minutes=32,
        )
        self._add_markdown_block(
            lesson=lesson_one,
            title="Интернет и веб — не одно и то же",
            position=1,
            content_markdown=(
                "Интернет — это **глобальная инфраструктура связи**, то есть сеть сетей, в которой множество "
                "устройств и локальных сетей связаны между собой общими правилами передачи данных. "
                "Веб — лишь один из сервисов, который работает поверх интернета.\n\n"
                "Хорошая аналогия: интернет похож на систему дорог, развязок и транспортных правил, а веб — "
                "это один из видов транспорта, который по этим дорогам ездит. Кроме веба в интернете есть "
                "электронная почта, мессенджеры, VPN, онлайн-игры, синхронизация файлов и множество других сервисов.\n\n"
                "Когда вы открываете сайт, вы пользуетесь вебом. Но чтобы этот сайт вообще стал доступен, "
                "нужна инфраструктура интернета: провайдер, маршрутизаторы, адресация и передача пакетов."
            ),
        )
        self._add_markdown_block(
            lesson=lesson_one,
            title="Как выглядит путь пакета в упрощенной схеме",
            position=2,
            content_markdown=(
                "С точки зрения сети данные обычно передаются **не одним большим куском**, а наборами небольших пакетов. "
                "Каждый пакет получает адрес получателя и проходит через несколько узлов сети.\n\n"
                "<img src=\"/static/images/illustrations/course-internet.svg\" alt=\"Схема сети и серверов\">\n\n"
                "В упрощенном виде путь может выглядеть так:\n"
                "1. ваш ноутбук формирует пакет;\n"
                "2. домашний роутер понимает, что пакет нужно отправить наружу;\n"
                "3. пакет попадает к провайдеру;\n"
                "4. затем проходит через промежуточные маршрутизаторы;\n"
                "5. в конце приходит на сервер, который умеет ответить на запрос.\n\n"
                "Маршрут заранее не лежит целиком в одном месте. Каждый узел принимает локальное решение, "
                "куда передать пакет дальше, исходя из своих таблиц маршрутизации."
            ),
        )
        self._add_markdown_block(
            lesson=lesson_one,
            title="Ключевые термины урока",
            position=3,
            block_type=LessonBlock.BlockType.QUOTE,
            note_style=LessonBlock.NoteStyle.NOTE,
            content_markdown=(
                "- **Клиент** — устройство или программа, которая инициирует запрос.\n"
                "- **Сервер** — устройство или программа, которая принимает запросы и отвечает на них.\n"
                "- **Маршрутизатор** — сетевой узел, который пересылает пакеты дальше по маршруту.\n"
                "- **Провайдер** — организация, которая подключает пользователя к сети.\n"
                "- **IP-адрес** — логический адрес устройства в сети.\n"
                "- **MAC-адрес** — аппаратный адрес сетевого интерфейса в локальном сегменте сети."
            ),
        )
        self._add_markdown_block(
            lesson=lesson_one,
            title="IP и MAC: зачем нужны оба адреса",
            position=4,
            content_markdown=(
                "На локальном уровне сеть должна понимать, **какой именно сетевой карте** передать кадр внутри одного сегмента. "
                "Для этого используется MAC-адрес. Но если данные нужно отправить далеко, в другую сеть, нужен уже логический адрес — IP.\n\n"
                "Поэтому обычно говорят так: **MAC помогает доставить данные по локальной сети, а IP помогает понять, "
                "куда данные должны идти в масштабе интернета**.\n\n"
                "Это не два конкурирующих адреса, а два уровня одной системы. На практике устройство использует оба."
            ),
        )
        self._add_code_block(
            lesson=lesson_one,
            title="Упрощенный псевдокод пути пакета",
            position=5,
            code_language="text",
            code_content=(
                "packet.destination_ip = \"93.184.216.34\"\n"
                "packet.source_ip = \"192.168.0.25\"\n\n"
                "home_router.forward(packet)\n"
                "provider_router.forward(packet)\n"
                "backbone_router.forward(packet)\n"
                "server.receive(packet)\n"
            ),
        )
        quiz_one_block = LessonBlock.objects.create(
            lesson=lesson_one,
            block_type=LessonBlock.BlockType.QUIZ,
            title="Тест по основам сети и адресации",
            position=6,
        )
        self._create_quiz(
            lesson_block=quiz_one_block,
            title="Проверка по уроку 1",
            description="Проверьте, как вы различаете интернет, веб, адресацию и маршрут пакетов.",
            passing_score=4,
            questions=[
                {
                    "question_type": QuizQuestion.QuestionType.SINGLE,
                    "text": "Как точнее всего описать интернет на базовом уровне?",
                    "score": 1,
                    "options": [
                        ("Один большой сайт", False),
                        ("Сеть сетей, которая объединяет множество узлов и сервисов", True),
                        ("Только браузер и страницы", False),
                    ],
                },
                {
                    "question_type": QuizQuestion.QuestionType.MULTIPLE,
                    "text": "Что участвует в доставке пакета от клиента к серверу?",
                    "score": 2,
                    "options": [
                        ("Маршрутизаторы", True),
                        ("IP-адресация", True),
                        ("Провайдер или сеть провайдера", True),
                        ("Название вкладки в браузере", False),
                    ],
                },
                {
                    "question_type": QuizQuestion.QuestionType.TRUE_FALSE,
                    "text": "MAC-адрес в основном нужен для работы на локальном уровне сети.",
                    "score": 1,
                    "options": [("Верно", True), ("Неверно", False)],
                },
                {
                    "question_type": QuizQuestion.QuestionType.SINGLE,
                    "text": "Чем веб отличается от интернета?",
                    "score": 1,
                    "options": [
                        ("Веб — это один из сервисов, работающих поверх интернета", True),
                        ("Интернет — часть веба", False),
                        ("Между ними нет разницы", False),
                    ],
                },
            ],
        )

        lesson_two = Lesson.objects.create(
            course=course,
            title="DNS, доменные имена и путь запроса от браузера к серверу",
            short_description="Пошагово разбираем URL, DNS lookup, кэш, соединение и отправку запроса.",
            position=2,
            estimated_duration_minutes=35,
        )
        self._add_markdown_block(
            lesson=lesson_two,
            title="Почему доменные имена удобнее IP-адресов",
            position=1,
            content_markdown=(
                "Человеку неудобно запоминать наборы чисел вроде `142.250.74.206`. Нам гораздо проще работать с именами вроде "
                "`google.com` или `example.org`. Поэтому в вебе широко используются **доменные имена**.\n\n"
                "Доменное имя — это удобный для человека идентификатор, который затем через систему DNS связывается с нужным IP-адресом. "
                "Можно сказать, что DNS играет роль огромной распределенной телефонной книги для интернета."
            ),
        )
        self._add_markdown_block(
            lesson=lesson_two,
            title="Из каких частей состоит URL",
            position=2,
            block_type=LessonBlock.BlockType.QUOTE,
            note_style=LessonBlock.NoteStyle.NOTE,
            content_markdown=(
                "Пример URL: `https://example.com:8443/docs/networking?topic=dns#cache`\n\n"
                "- `https` — схема или протокол;\n"
                "- `example.com` — доменное имя;\n"
                "- `8443` — порт;\n"
                "- `/docs/networking` — путь к ресурсу;\n"
                "- `?topic=dns` — query string с параметрами;\n"
                "- `#cache` — якорь внутри страницы."
            ),
        )
        self._add_markdown_block(
            lesson=lesson_two,
            title="Что происходит после ввода адреса в браузере",
            position=3,
            content_markdown=(
                "Упрощенный путь запроса выглядит так:\n\n"
                "1. Пользователь вводит URL в адресную строку.\n"
                "2. Браузер проверяет локальные кэши: возможно, нужный адрес уже известен.\n"
                "3. Если адреса нет, начинается DNS lookup — поиск IP по доменному имени.\n"
                "4. Получив IP, браузер устанавливает соединение с нужным сервером.\n"
                "5. Затем браузер отправляет HTTP-запрос.\n"
                "6. Сервер возвращает ответ: HTML, JSON, редирект или сообщение об ошибке.\n\n"
                "Важно понимать, что браузер не просто “открывает сайт”, а проходит несколько технических шагов, "
                "каждый из которых может повлиять на скорость загрузки."
            ),
        )
        self._add_markdown_block(
            lesson=lesson_two,
            title="DNS-кэш и почему повторные запросы бывают быстрее",
            position=4,
            block_type=LessonBlock.BlockType.QUOTE,
            note_style=LessonBlock.NoteStyle.NOTE,
            content_markdown=(
                "DNS-кэш может находиться в браузере, операционной системе, роутере или у провайдера. "
                "Если нужное соответствие доменного имени и IP уже есть в кэше и еще не устарело, "
                "повторный запрос пройдет быстрее: системе не придется заново спрашивать DNS-сервер."
            ),
        )
        self._add_code_block(
            lesson=lesson_two,
            title="Псевдокод разрешения доменного имени",
            position=5,
            code_language="text",
            code_content=(
                "url = \"https://example.com/docs\"\n"
                "host = parse_host(url)          # example.com\n"
                "ip = dns_resolver.lookup(host)  # 93.184.216.34\n"
                "connection = open_connection(ip, port=443)\n"
                "connection.send_http_request(\"GET\", \"/docs\")\n"
            ),
        )
        self._add_file_block(
            lesson=lesson_two,
            title="Памятка по URL и DNS",
            position=6,
            filename="dns-url-reference.pdf",
            lines=[
                "Internet reference sheet",
                "1. URL = scheme + host + optional port + path + query + fragment",
                "2. DNS maps host names to IP addresses",
                "3. Useful reading: RFC 1034, RFC 1035, MDN: What is DNS?",
                "4. Practice: type example.com and explain each step before the first byte arrives",
            ],
        )
        quiz_two_block = LessonBlock.objects.create(
            lesson=lesson_two,
            block_type=LessonBlock.BlockType.QUIZ,
            title="Тест по DNS и пути запроса",
            position=7,
        )
        self._create_quiz(
            lesson_block=quiz_two_block,
            title="Проверка по уроку 2",
            description="Вопросы на понимание доменных имен, URL и порядка действий браузера.",
            passing_score=4,
            questions=[
                {
                    "question_type": QuizQuestion.QuestionType.SINGLE,
                    "text": "Почему люди обычно работают с доменными именами, а не напрямую с IP-адресами?",
                    "score": 1,
                    "options": [
                        ("Доменные имена проще читать и запоминать", True),
                        ("IP-адреса запрещены в интернете", False),
                        ("Браузер вообще не умеет работать с IP", False),
                    ],
                },
                {
                    "question_type": QuizQuestion.QuestionType.MULTIPLE,
                    "text": "Какие шаги обычно происходят после ввода URL в браузер?",
                    "score": 2,
                    "options": [
                        ("Проверка кэша и DNS lookup", True),
                        ("Установление соединения", True),
                        ("Отправка HTTP-запроса", True),
                        ("Компиляция приложения на C", False),
                    ],
                },
                {
                    "question_type": QuizQuestion.QuestionType.TRUE_FALSE,
                    "text": "DNS-кэш может ускорить повторное открытие знакомого ресурса.",
                    "score": 1,
                    "options": [("Верно", True), ("Неверно", False)],
                },
                {
                    "question_type": QuizQuestion.QuestionType.SINGLE,
                    "text": "Какая часть URL в `https://example.com/docs?id=7#top` является путем?",
                    "score": 1,
                    "options": [("`https`", False), ("`example.com`", False), ("`/docs`", True)],
                },
            ],
        )

        lesson_three = Lesson.objects.create(
            course=course,
            title="HTTP, HTTPS, страницы, ресурсы и что происходит при загрузке сайта",
            short_description="Разбираем запросы и ответы, статус-коды, ресурсы страницы и роль HTTPS.",
            position=3,
            estimated_duration_minutes=38,
        )
        self._add_markdown_block(
            lesson=lesson_three,
            title="HTTP и HTTPS на базовом уровне",
            position=1,
            content_markdown=(
                "HTTP — это протокол, по которому клиент и сервер обмениваются запросами и ответами. "
                "Клиент просит ресурс, сервер отвечает данными и статусом.\n\n"
                "HTTPS — это тот же HTTP, но поверх защищенного канала. Упрощенно можно сказать так: "
                "**HTTP описывает правила разговора, а TLS в HTTPS защищает этот разговор от подслушивания и подмены**.\n\n"
                "Важно не путать наличие HTTPS с общей надежностью сайта. HTTPS говорит о защищенном соединении, "
                "но не гарантирует качество контента или безопасность бизнес-логики."
            ),
        )
        self._add_code_block(
            lesson=lesson_three,
            title="Пример HTTP-запроса и ответа",
            position=2,
            code_language="http",
            code_content=(
                "GET /docs/networking HTTP/1.1\n"
                "Host: example.com\n"
                "Accept: text/html\n\n"
                "HTTP/1.1 200 OK\n"
                "Content-Type: text/html; charset=UTF-8\n"
                "Cache-Control: max-age=60\n\n"
                "<html>\n"
                "  <head><title>Networking Docs</title></head>\n"
                "  <body>...</body>\n"
                "</html>\n"
            ),
        )
        self._add_markdown_block(
            lesson=lesson_three,
            title="Статус-коды, которые важно узнавать с первого взгляда",
            position=3,
            block_type=LessonBlock.BlockType.QUOTE,
            note_style=LessonBlock.NoteStyle.NOTE,
            content_markdown=(
                "- **200 OK** — запрос обработан успешно.\n"
                "- **404 Not Found** — сервер не нашел указанный ресурс.\n"
                "- **500 Internal Server Error** — на стороне сервера возникла внутренняя ошибка.\n\n"
                "Статус-код — это краткий итог обработки запроса. Он не заменяет весь ответ, но очень быстро "
                "помогает понять, что произошло."
            ),
        )
        self._add_markdown_block(
            lesson=lesson_three,
            title="Почему сайт редко состоит из одного файла",
            position=4,
            content_markdown=(
                "HTML-страница обычно содержит ссылки на дополнительные ресурсы: таблицы стилей CSS, файлы JavaScript, "
                "шрифты, изображения, иконки и иногда отдельные API-запросы за данными.\n\n"
                "Поэтому после получения первого HTML браузер продолжает работу: анализирует документ, находит ссылки на "
                "ресурсы и выполняет новые запросы. Именно из-за этого в инструментах разработчика можно увидеть "
                "целую сетку запросов даже для относительно простой страницы."
            ),
        )
        self._add_markdown_block(
            lesson=lesson_three,
            title="Небольшая заметка про HTTPS и TLS",
            position=5,
            block_type=LessonBlock.BlockType.QUOTE,
            note_style=LessonBlock.NoteStyle.QUOTE,
            content_markdown=(
                "TLS не делает интернет “магически безопасным”. Он помогает шифровать соединение и проверять, "
                "что вы общаетесь именно с тем сервером, с которым собирались. Это снижает риск перехвата и подмены данных на пути."
            ),
        )
        self._add_file_block(
            lesson=lesson_three,
            title="Краткая шпаргалка по HTTP",
            position=6,
            filename="http-reference.pdf",
            lines=[
                "HTTP reference sheet",
                "GET retrieves a resource, POST sends data to the server",
                "Key status codes: 200 OK, 404 Not Found, 500 Internal Server Error",
                "Remember: HTML can trigger many extra requests for CSS, JS and images",
                "Useful reading: MDN HTTP overview and DevTools Network tab",
            ],
        )
        quiz_three_block = LessonBlock.objects.create(
            lesson=lesson_three,
            block_type=LessonBlock.BlockType.QUIZ,
            title="Тест по HTTP и загрузке страницы",
            position=7,
        )
        self._create_quiz(
            lesson_block=quiz_three_block,
            title="Проверка по уроку 3",
            description="Вопросы на понимание HTTP, HTTPS, статусов ответа и загрузки ресурсов.",
            passing_score=4,
            questions=[
                {
                    "question_type": QuizQuestion.QuestionType.SINGLE,
                    "text": "Что делает метод GET на базовом уровне?",
                    "score": 1,
                    "options": [
                        ("Запрашивает ресурс у сервера", True),
                        ("Создает шифрование TLS", False),
                        ("Обязательно удаляет ресурс", False),
                    ],
                },
                {
                    "question_type": QuizQuestion.QuestionType.MULTIPLE,
                    "text": "Какие статусы нужно уметь распознавать на базовом уровне?",
                    "score": 2,
                    "options": [
                        ("200 OK", True),
                        ("404 Not Found", True),
                        ("500 Internal Server Error", True),
                        ("000 Browser Magic", False),
                    ],
                },
                {
                    "question_type": QuizQuestion.QuestionType.TRUE_FALSE,
                    "text": "HTTPS означает, что соединение шифруется, но не гарантирует полезность или честность самого контента.",
                    "score": 1,
                    "options": [("Верно", True), ("Неверно", False)],
                },
                {
                    "question_type": QuizQuestion.QuestionType.SINGLE,
                    "text": "Почему после загрузки HTML браузер часто делает дополнительные запросы?",
                    "score": 1,
                    "options": [
                        ("Потому что страница может ссылаться на CSS, JS, изображения и другие ресурсы", True),
                        ("Потому что сервер всегда дублирует каждый ответ три раза", False),
                        ("Потому что HTML не может содержать текст без JavaScript", False),
                    ],
                },
            ],
        )
        PracticeTask.objects.get_or_create(
            lesson=lesson_three,
            title="Разберите загрузку знакомого сайта",
            defaults={
                "description_markdown": (
                    "Откройте любой знакомый сайт и представьте путь запроса своими словами: "
                    "доменное имя, DNS, соединение, HTTP-запрос, получение HTML и дополнительных ресурсов. "
                    "Это практическое задание пока служит архитектурной заготовкой под будущую песочницу."
                ),
                "language": "text",
                "starter_code": "",
                "expected_output_description": "Краткое текстовое объяснение шагов загрузки страницы.",
                "is_active": True,
                "is_placeholder": True,
            },
        )

    def _populate_python_course(self, course):
        if course.lessons.filter(is_deleted=False).exists():
            return

        lesson_one = Lesson.objects.create(
            course=course,
            title="Переменные, типы данных и первые выражения",
            short_description="Разбираем, как Python хранит данные и как читать простые выражения.",
            position=1,
            estimated_duration_minutes=20,
        )
        self._add_markdown_block(
            lesson=lesson_one,
            title="Что важно на старте",
            position=1,
            content_markdown=(
                "На первом шаге студенту важно понять: переменная — это имя, под которым программа хранит значение. "
                "В Python часто начинают с чисел, строк, булевых значений и простых выражений."
            ),
        )

        lesson_two = Lesson.objects.create(
            course=course,
            title="Условия, циклы и базовая управляющая логика",
            short_description="Собираем простые ветвления и повторяющиеся действия.",
            position=2,
            estimated_duration_minutes=28,
        )
        self._add_markdown_block(
            lesson=lesson_two,
            title="Когда код принимает решения",
            position=1,
            content_markdown=(
                "Условные конструкции помогают программе выбрать ветку выполнения, а циклы позволяют повторять действия "
                "без копирования одного и того же кода."
            ),
        )
        quiz_block = LessonBlock.objects.create(
            lesson=lesson_two,
            block_type=LessonBlock.BlockType.QUIZ,
            title="Мини-тест по управляющим конструкциям",
            position=2,
        )
        self._create_quiz(
            lesson_block=quiz_block,
            title="Проверка по Python",
            description="Короткий тест на понимание if и цикла for.",
            passing_score=2,
            questions=[
                {
                    "question_type": QuizQuestion.QuestionType.SINGLE,
                    "text": "Для чего чаще всего используют `if`?",
                    "score": 1,
                    "options": [
                        ("Чтобы выбрать ветку выполнения по условию", True),
                        ("Чтобы сохранить файл PDF", False),
                        ("Чтобы подключиться к базе автоматически", False),
                    ],
                },
                {
                    "question_type": QuizQuestion.QuestionType.TRUE_FALSE,
                    "text": "Цикл `for` позволяет повторять действие для элементов последовательности.",
                    "score": 1,
                    "options": [("Верно", True), ("Неверно", False)],
                },
            ],
        )

        lesson_three = Lesson.objects.create(
            course=course,
            title="Функции и декомпозиция небольших задач",
            short_description="Понимаем, зачем разбивать решение на отдельные функции.",
            position=3,
            estimated_duration_minutes=22,
        )
        self._add_markdown_block(
            lesson=lesson_three,
            title="Почему функции делают код понятнее",
            position=1,
            content_markdown=(
                "Функции помогают выделить повторяемую логику, дать ей имя и использовать снова. "
                "Для начинающего разработчика это первый шаг к более чистому и читаемому коду."
            ),
        )

    def _populate_ux_course(self, course):
        if course.lessons.filter(is_deleted=False).exists():
            return

        lesson_one = Lesson.objects.create(
            course=course,
            title="Как студент читает учебный экран",
            short_description="О роли визуальной иерархии, плотности и понятных действий.",
            position=1,
            estimated_duration_minutes=20,
        )
        self._add_markdown_block(
            lesson=lesson_one,
            title="Начинать нужно со структуры, а не с эффектов",
            position=1,
            content_markdown=(
                "В учебных интерфейсах пользователь должен быстро понимать, где он находится, что главное на экране "
                "и какой следующий шаг. Поэтому структура важнее декоративности."
            ),
        )

        lesson_two = Lesson.objects.create(
            course=course,
            title="Пустые состояния, ошибки и обратная связь",
            short_description="Разбираем, как система поддерживает пользователя в рабочих сценариях.",
            position=2,
            estimated_duration_minutes=24,
        )
        self._add_markdown_block(
            lesson=lesson_two,
            title="Хороший интерфейс объясняет ситуацию",
            position=1,
            content_markdown=(
                "Пустое состояние должно не просто сообщать об отсутствии данных, а подсказывать, что делать дальше. "
                "То же относится к ошибкам, подтверждениям и сохранению действий."
            ),
        )

    def _populate_sql_draft(self, course):
        if course.lessons.filter(is_deleted=False).exists():
            return

        lesson_one = Lesson.objects.create(
            course=course,
            title="Как читать таблицу и формулировать вопрос к данным",
            short_description="Первый черновой урок курса по SQL.",
            position=1,
            estimated_duration_minutes=18,
        )
        self._add_markdown_block(
            lesson=lesson_one,
            title="Черновая заготовка курса",
            position=1,
            content_markdown=(
                "Этот курс оставлен в статусе черновика специально, чтобы в системе была приватная авторская сущность "
                "для демонстрации сценариев редактирования и предпросмотра."
            ),
        )

    def _create_interactions(self, *, student, author, courses):
        internet_course, python_course, ux_course = courses

        CourseComment.objects.get_or_create(
            course=internet_course,
            author=student,
            body=(
                "Очень удачный вводный курс: понравилось, что DNS, HTTP и роль браузера объясняются как единый путь "
                "запроса, а не как разрозненные термины."
            ),
        )
        CourseComment.objects.get_or_create(
            course=internet_course,
            author=author,
            body="Этот курс задуман как связное введение в сетевую грамотность для студентов, которые только заходят в веб-разработку.",
        )
        CourseComment.objects.get_or_create(
            course=python_course,
            author=student,
            body="Хороший спокойный курс для первого знакомства с Python.",
        )

        CourseReview.objects.update_or_create(
            course=internet_course,
            author=student,
            defaults={
                "rating": 5,
                "body": "Сильный демонстрационный курс: материал последовательный, полезный и хорошо показывает сценарий прохождения уроков.",
            },
        )
        CourseReview.objects.update_or_create(
            course=python_course,
            author=student,
            defaults={
                "rating": 4,
                "body": "Подходит для старта и хорошо смотрится как пример короткого базового курса.",
            },
        )
        CourseReview.objects.update_or_create(
            course=ux_course,
            author=student,
            defaults={
                "rating": 4,
                "body": "Полезный материал по структуре учебных интерфейсов и обратной связи.",
            },
        )

        for course in courses:
            refresh_course_rating(course)
            FavoriteCourse.objects.get_or_create(user=student, course=course)

    def _simulate_learning(self, *, student, active_course, completed_course):
        active_lessons = list(active_course.lessons.filter(is_deleted=False).order_by("position", "id"))
        if active_lessons:
            first_lesson = active_lessons[0]
            first_quiz = first_lesson.blocks.filter(block_type=LessonBlock.BlockType.QUIZ).select_related("quiz").first()
            open_lesson(student, first_lesson)
            if first_quiz and hasattr(first_quiz, "quiz"):
                self._create_attempt(student, first_quiz.quiz, first_quiz.quiz.effective_passing_score - 1, passed=False)
                self._create_attempt(student, first_quiz.quiz, first_quiz.quiz.max_score, passed=True)
            if len(active_lessons) > 1:
                open_lesson(student, active_lessons[1])

        completed_lessons = list(completed_course.lessons.filter(is_deleted=False).order_by("position", "id"))
        for lesson in completed_lessons:
            open_lesson(student, lesson)
            quiz_block = lesson.blocks.filter(block_type=LessonBlock.BlockType.QUIZ).select_related("quiz").first()
            if quiz_block and hasattr(quiz_block, "quiz"):
                self._create_attempt(student, quiz_block.quiz, quiz_block.quiz.max_score, passed=True)
            else:
                mark_lesson_completed_manually(student, lesson)

    def _create_attempt(self, user, quiz, score, *, passed):
        attempt = QuizAttempt.objects.create(
            user=user,
            quiz=quiz,
            score=max(score, 0),
            passed=passed,
            submitted_at=timezone.now(),
        )
        for question in quiz.questions.all():
            is_correct = passed
            awarded_score = question.score if is_correct else 0
            answer = QuizAnswer.objects.create(
                attempt=attempt,
                question=question,
                is_correct=is_correct,
                awarded_score=awarded_score,
            )
            selected_options = question.options.filter(is_correct=is_correct)[:1]
            if question.question_type == QuizQuestion.QuestionType.MULTIPLE and is_correct:
                selected_options = question.options.filter(is_correct=True)
            if not is_correct:
                selected_options = question.options.filter(is_correct=False)[:1]
            answer.selected_options.set(selected_options)
        sync_progress_after_quiz_attempt(attempt)
        return attempt

    def _add_markdown_block(
        self,
        *,
        lesson,
        title,
        position,
        content_markdown,
        block_type=LessonBlock.BlockType.TEXT,
        note_style=LessonBlock.NoteStyle.NOTE,
    ):
        return LessonBlock.objects.create(
            lesson=lesson,
            block_type=block_type,
            title=title,
            position=position,
            content_markdown=content_markdown,
            note_style=note_style,
        )

    def _add_code_block(self, *, lesson, title, position, code_language, code_content):
        return LessonBlock.objects.create(
            lesson=lesson,
            block_type=LessonBlock.BlockType.CODE,
            title=title,
            position=position,
            code_language=code_language,
            code_content=code_content,
        )

    def _add_file_block(self, *, lesson, title, position, filename, lines):
        block = LessonBlock.objects.create(
            lesson=lesson,
            block_type=LessonBlock.BlockType.FILE,
            title=title,
            position=position,
        )
        block.file.save(filename, ContentFile(self._build_pdf(lines)), save=True)
        return block

    def _create_quiz(self, *, lesson_block, title, description, passing_score, questions):
        quiz = Quiz.objects.create(
            lesson_block=lesson_block,
            title=title,
            description=description,
            passing_score=passing_score,
        )
        for position, question_data in enumerate(questions, start=1):
            question = QuizQuestion.objects.create(
                quiz=quiz,
                question_type=question_data["question_type"],
                text=question_data["text"],
                position=position,
                score=question_data["score"],
            )
            for option_position, (text, is_correct) in enumerate(question_data["options"], start=1):
                QuizOption.objects.create(
                    question=question,
                    text=text,
                    is_correct=is_correct,
                    position=option_position,
                )
        quiz.update_max_score()
        return quiz

    def _build_pdf(self, lines):
        safe_lines = [self._pdf_escape(line) for line in lines]
        text_stream = ["BT", "/F1 12 Tf", "72 770 Td"]
        for index, line in enumerate(safe_lines):
            if index:
                text_stream.append("0 -18 Td")
            text_stream.append(f"({line}) Tj")
        text_stream.append("ET")
        stream = "\n".join(text_stream)

        objects = [
            "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
            "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
            (
                "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >> endobj"
            ),
            f"4 0 obj << /Length {len(stream.encode('latin-1'))} >> stream\n{stream}\nendstream endobj",
            "5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        ]

        result = "%PDF-1.4\n"
        offsets = [0]
        for obj in objects:
            offsets.append(len(result.encode("latin-1")))
            result += f"{obj}\n"
        startxref = len(result.encode("latin-1"))
        result += "xref\n0 6\n0000000000 65535 f \n"
        for offset in offsets[1:]:
            result += f"{offset:010d} 00000 n \n"
        result += "trailer << /Size 6 /Root 1 0 R >>\n"
        result += f"startxref\n{startxref}\n%%EOF"
        return result.encode("latin-1")

    def _pdf_escape(self, value):
        text = value.encode("ascii", "ignore").decode("ascii")
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
