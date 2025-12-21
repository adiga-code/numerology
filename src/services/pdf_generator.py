"""Сервис для генерации PDF отчётов."""
import logging
import os
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

# Директория для сохранения PDF
PDF_DIR = Path("/app/pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)

# Директория с шаблонами
TEMPLATES_DIR = Path("/app/templates")


async def generate_pdf(order, participants, content: str) -> str:
    """
    Генерация PDF отчёта.

    Args:
        order: Модель заказа
        participants: Список участников
        content: Текст отчёта от AI

    Returns:
        str: Путь к сгенерированному PDF файлу
    """
    try:
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
            "content": content,
            "created_date": datetime.now().strftime("%d.%m.%Y"),
            "created_time": datetime.now().strftime("%H:%M")
        }

        # Рендерим HTML
        html_content = template.render(**context)

        # Генерируем PDF
        pdf_filename = f"report_{order.order_uuid}.pdf"
        pdf_path = PDF_DIR / pdf_filename

        # Конвертируем HTML в PDF с помощью xhtml2pdf
        with open(pdf_path, "w+b") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

        if pisa_status.err:
            raise Exception(f"Ошибка при создании PDF: {pisa_status.err}")

        logger.info(f"PDF сгенерирован: {pdf_path}")
        return str(pdf_path)

    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}")
        raise
