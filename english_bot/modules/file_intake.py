"""
Разбор материалов задания (Task/Question), присланных файлом — картинкой,
PDF или .docx — а не просто текстом. Нужно в первую очередь для IELTS
Academic Task 1: вопрос там почти всегда визуальный (график/диаграмма/
таблица), и модель должна реально «увидеть» его, а не текстовое описание.

Модуль не зависит от Telegram (как и modules/ai_feedback.py) — на вход
бинарные данные + mime/имя файла, на выход извлечённый текст и/или список
изображений, готовых передать в OpenAI vision (см. ai_feedback._append_image_parts).
Скачивание файла из Telegram остаётся в handlers/teacher.py.
"""

import io
from typing import NamedTuple, Optional

import fitz  # PyMuPDF
from docx import Document

# IELTS Academic Task 1 — обычно одна страница с графиком; 3 страницы с
# запасом покрывает составные/многочастные задания, не раздувая запрос.
MAX_PDF_PAGES = 3

_IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_PDF_MIME = "application/pdf"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class ExtractedQuestion(NamedTuple):
    text: str
    images: list[tuple[bytes, str]]  # (данные, mime)
    error_key: Optional[str]


def _guess_mime(mime_type: Optional[str], file_name: Optional[str]) -> str:
    """Telegram обычно присылает верный mime_type; имя файла — запасной вариант."""
    if mime_type and mime_type != "application/octet-stream":
        return mime_type
    name = (file_name or "").lower()
    if name.endswith(".pdf"):
        return _PDF_MIME
    if name.endswith(".docx"):
        return _DOCX_MIME
    if name.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if name.endswith(".png"):
        return "image/png"
    if name.endswith(".webp"):
        return "image/webp"
    return mime_type or "application/octet-stream"


def _pdf_to_images(data: bytes) -> list[tuple[bytes, str]]:
    images: list[tuple[bytes, str]] = []
    pdf = fitz.open(stream=data, filetype="pdf")
    try:
        for page in pdf[:MAX_PDF_PAGES]:
            pixmap = page.get_pixmap(dpi=150)
            images.append((pixmap.tobytes("png"), "image/png"))
    finally:
        pdf.close()
    return images


def _docx_to_text(data: bytes) -> str:
    document = Document(io.BytesIO(data))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def classify_and_extract(
    data: bytes, mime_type: Optional[str], file_name: Optional[str]
) -> ExtractedQuestion:
    """
    Определяет тип присланного файла-задания и извлекает текст и/или картинки.
    При неподдерживаемом формате (в т.ч. старый бинарный .doc — python-docx
    его не читает, а тянуть системный конвертер ради него на сервер не стали,
    см. README) возвращает error_key — handlers/teacher.py в этом случае
    показывает понятную ошибку и остаётся на том же шаге диалога.
    """
    resolved_mime = _guess_mime(mime_type, file_name)

    if resolved_mime in _IMAGE_MIMES:
        return ExtractedQuestion(text="", images=[(data, resolved_mime)], error_key=None)

    if resolved_mime == _PDF_MIME:
        try:
            images = _pdf_to_images(data)
        except Exception:  # noqa: BLE001 - повреждённый/нечитаемый PDF
            return ExtractedQuestion(text="", images=[], error_key="error_unsupported_question_format")
        if not images:
            return ExtractedQuestion(text="", images=[], error_key="error_unsupported_question_format")
        return ExtractedQuestion(text="", images=images, error_key=None)

    if resolved_mime == _DOCX_MIME:
        try:
            text = _docx_to_text(data)
        except Exception:  # noqa: BLE001 - повреждённый/нечитаемый .docx
            return ExtractedQuestion(text="", images=[], error_key="error_unsupported_question_format")
        return ExtractedQuestion(text=text, images=[], error_key=None)

    return ExtractedQuestion(text="", images=[], error_key="error_unsupported_question_format")
