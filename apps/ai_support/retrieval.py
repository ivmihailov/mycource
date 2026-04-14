import re
from dataclasses import dataclass


TOKEN_RE = re.compile(r"[a-zA-Zа-яА-Я0-9_]+")


@dataclass
class CourseChunk:
    lesson_id: int
    lesson_title: str
    block_id: int | None
    block_title: str
    source_label: str
    content: str


def tokenize(value):
    return {token.lower() for token in TOKEN_RE.findall(value or "")}


class CourseContentRetriever:
    def collect_chunks(self, course):
        chunks = []
        lessons = course.lessons.filter(is_deleted=False).prefetch_related("blocks").order_by("position", "id")
        for lesson in lessons:
            for block in lesson.blocks.order_by("position", "id"):
                parts = []
                if block.title:
                    parts.append(block.title)
                if block.block_type in {"text", "quote"} and block.content_markdown:
                    parts.append(block.content_markdown)
                elif block.block_type == "code" and block.code_content:
                    parts.append(block.code_content)
                elif block.block_type == "file" and block.file:
                    parts.append(f"Файл: {block.file.name}")
                elif block.block_type == "quiz" and hasattr(block, "quiz") and block.quiz.description:
                    parts.append(block.quiz.description)
                content = "\n".join(part.strip() for part in parts if part and part.strip())
                if not content:
                    continue
                chunks.append(
                    CourseChunk(
                        lesson_id=lesson.pk,
                        lesson_title=lesson.title,
                        block_id=block.pk,
                        block_title=block.title or block.get_block_type_display(),
                        source_label=f"Урок «{lesson.title}», блок «{block.title or block.get_block_type_display()}»",
                        content=content[:2500],
                    )
                )
        return chunks

    def select_relevant_chunks(self, *, course, question, lesson=None, limit=5, max_chars=7000):
        chunks = self.collect_chunks(course)
        question_tokens = tokenize(question)
        ranked = []
        for chunk in chunks:
            chunk_tokens = tokenize(chunk.content)
            overlap = len(question_tokens & chunk_tokens)
            title_boost = len(question_tokens & tokenize(chunk.lesson_title + " " + chunk.block_title))
            current_lesson_boost = 2 if lesson and lesson.pk == chunk.lesson_id else 0
            score = overlap * 3 + title_boost * 4 + current_lesson_boost
            ranked.append((score, chunk))

        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = []
        current_size = 0
        for score, chunk in ranked:
            if score <= 0 and selected:
                continue
            if current_size >= max_chars:
                break
            selected.append(chunk)
            current_size += len(chunk.content)
            if len(selected) >= limit:
                break

        if not selected and chunks:
            fallback = [chunk for chunk in chunks if lesson and chunk.lesson_id == lesson.pk][:limit] or chunks[:limit]
            return fallback
        return selected

    def collect_lesson_text(self, lesson, *, max_chars=12000):
        parts = [f"Название урока: {lesson.title}"]
        if lesson.short_description:
            parts.append(f"Краткое описание: {lesson.short_description}")
        for block in lesson.blocks.select_related("quiz").order_by("position", "id"):
            block_parts = [f"Блок: {block.title or block.get_block_type_display()} ({block.get_block_type_display()})"]
            if block.block_type in {"text", "quote"} and block.content_markdown:
                block_parts.append(block.content_markdown)
            elif block.block_type == "code" and block.code_content:
                block_parts.append(block.code_content)
            elif block.block_type == "quiz" and hasattr(block, "quiz") and block.quiz.description:
                block_parts.append(block.quiz.description)
            elif block.block_type == "file" and block.file:
                block_parts.append(f"Файл: {block.file.name}")
            block_text = "\n".join(block_parts).strip()
            if len(block_text) > 40:
                parts.append(block_text)

        full_text = "\n\n".join(parts)
        return full_text[:max_chars]
