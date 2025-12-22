"""Сервис для генерации PDF отчётов с использованием WeasyPrint."""
import logging
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import markdown

logger = logging.getLogger(__name__)

# Директория для сохранения PDF
PDF_DIR = Path("/app/pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)

# Директория с шаблонами
TEMPLATES_DIR = Path("/app/templates")


async def generate_pdf(order, participants, content: str) -> str:
    """
    Генерация PDF отчёта с использованием WeasyPrint.

    Args:
        order: Модель заказа
        participants: Список участников
        content: Текст отчёта от AI

    Returns:
        str: Путь к сгенерированному PDF файлу
    """
    try:
        # Конвертируем markdown в HTML
        md = markdown.Markdown(
            extensions=[
                'extra',           # Таблицы, атрибуты и др.
                'nl2br',           # Переводы строк в <br>
                'sane_lists',      # Улучшенная обработка списков
                'codehilite',      # Подсветка кода
                'fenced_code',     # Блоки кода с ```
                'tables',          # Таблицы
            ],
            output_format='html5'
        )

        # Конвертируем content из markdown в HTML
        html_content_body = md.convert(content)

        logger.debug(f"Markdown конвертирован в HTML (длина: {len(html_content_body)} символов)")

        # Настройка Jinja2
        env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
        template = env.get_template("report.html")

        # Данные для шаблона
        context = {
            "order_uuid": order.order_uuid,
            "tariff": order.tariff.value,
            "style": order.style.value,
            "participants": [
                {
                    "full_name": p.full_name,
                    "birth_date": p.birth_date.strftime("%d.%m.%Y"),
                    "birth_time": p.birth_time.strftime("%H:%M") if p.birth_time else "не указано",
                    "birth_place": p.birth_place or "не указано"
                }
                for p in participants
            ],
            "content": html_content_body,  # HTML вместо markdown
            "created_date": datetime.now().strftime("%d.%m.%Y"),
            "created_time": datetime.now().strftime("%H:%M")
        }

        # Рендерим HTML с явной кодировкой UTF-8
        html_content = template.render(**context)

        # Генерируем PDF с помощью WeasyPrint
        pdf_filename = f"report_{order.order_uuid}.pdf"
        pdf_path = PDF_DIR / pdf_filename

        # Конфигурация шрифтов для WeasyPrint
        font_config = FontConfiguration()

        # Создаем HTML объект с правильной кодировкой
        html = HTML(string=html_content, encoding='utf-8')

        # Генерируем PDF с конфигурацией шрифтов
        html.write_pdf(
            str(pdf_path),
            font_config=font_config
        )

        logger.info(f"PDF сгенерирован: {pdf_path}")
        return str(pdf_path)

    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}", exc_info=True)
        raise
