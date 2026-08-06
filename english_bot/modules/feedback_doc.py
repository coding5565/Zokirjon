"""
Генерация .docx-файла с фидбеком по Writing/Speaking.

По просьбе заказчика фидбек теперь отправляется файлом, а не длинной стеной
текста в чате — аудитория (Gen-Z студенты) такие сообщения не дочитывает,
а файл воспринимается как «настоящий» разбор, который можно спокойно открыть
и прочитать. Сам текст фидбека (Burger-техника, ❌/✅-пары, лексика) не
меняется — meняется только канал доставки, см. handlers/teacher.py.
"""

import io

from docx import Document


def build_feedback_document(feedback_text: str, title: str) -> bytes:
    """
    Простой читаемый .docx: заголовок + текст фидбека, разбитый на абзацы по
    пустым строкам. Без попытки стилизовать ❌/✅-пары отдельно — обычных
    абзацев достаточно как апгрейд по сравнению с сырым текстом в чате;
    более сложная вёрстка сюда сознательно не добавлена (см. README).
    """
    document = Document()
    document.add_heading(title, level=1)
    for block in feedback_text.split("\n\n"):
        block = block.strip()
        if block:
            document.add_paragraph(block)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
