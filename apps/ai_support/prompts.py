from textwrap import dedent


def format_course_chunks(chunks):
    formatted = []
    for index, chunk in enumerate(chunks, start=1):
        formatted.append(
            dedent(
                f"""
                [{index}] Источник: {chunk.source_label}
                Текст:
                {chunk.content}
                """
            ).strip()
        )
    return "\n\n".join(formatted)


def build_course_qna_messages(*, course, question, chunks, lesson=None):
    lesson_line = f"Текущий урок: {lesson.title}." if lesson else "Текущий урок не указан."
    has_chunks = bool(chunks)
    course_materials = format_course_chunks(chunks) if has_chunks else "Подходящих фрагментов из курса не найдено."

    system_message = dedent(
        f"""
        Ты помощник учебной платформы.
        Сначала используй предоставленные материалы курса «{course.title}» и, если возможно, ответь по ним.
        Если прямого ответа в материалах нет или их недостаточно, честно скажи об этом одной короткой фразой:
        «В материалах курса нет прямого ответа, поэтому ниже — общее пояснение».
        После этой фразы дай короткое, понятное и полезное общее объяснение по теме на русском языке.
        Не выдумывай ссылки на уроки и блоки, если опоры в материалах курса нет.
        Если используешь материалы курса, по возможности называй урок или блок, на который опираешься.
        {lesson_line}
        """
    ).strip()

    user_message = dedent(
        f"""
        Вопрос студента:
        {question}

        Материалы курса:
        {course_materials}

        Дай краткий, но содержательный ответ.
        Если ответ опирается на материалы курса, в конце добавь строку «Опора: ...» с упоминанием урока или блока.
        Если материалов курса недостаточно, не добавляй вымышленные источники и просто дай общее пояснение после честной пометки.
        """
    ).strip()

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]


def build_quiz_generation_messages(*, lesson, lesson_text):
    system_message = dedent(
        """
        Ты помогаешь автору курса составить учебный тест.
        Используй только предоставленный материал урока.
        Не придумывай темы, которых нет в тексте.
        Генерируй понятные, проверяемые вопросы для новичка.
        Возвращай строго JSON по указанной схеме.
        Язык ответа — русский.
        """
    ).strip()
    user_message = dedent(
        f"""
        Урок: {lesson.title}
        Краткое описание: {lesson.short_description}

        Содержание урока:
        {lesson_text}

        Сгенерируй проект теста по этому материалу. В тесте должно быть 3-5 вопросов.
        Используй только типы вопросов single_choice, multiple_choice и true_false.
        """
    ).strip()
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]
