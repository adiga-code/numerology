"""Сервис для генерации PDF отчётов."""
import logging
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

logger = logging.getLogger(__name__)

# Директория для сохранения PDF
PDF_DIR = Path("/app/pdfs")
PDF_DIR.mkdir(parents=True, exist_ok=True)

# Регистрация шрифтов DejaVu для поддержки кириллицы
try:
    pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
except Exception as e:
    logger.warning(f"Не удалось зарегистрировать шрифты DejaVu: {e}")


async def generate_pdf(order, participants, content: str) -> str:
    """
    Генерация PDF отчёта с использованием reportlab.

    Args:
        order: Модель заказа
        participants: Список участников
        content: Текст отчёта от AI

    Returns:
        str: Путь к сгенерированному PDF файлу
    """
    try:
        pdf_filename = f"report_{order.order_uuid}.pdf"
        pdf_path = PDF_DIR / pdf_filename

        # Создаём PDF документ
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )

        # Стили
        styles = getSampleStyleSheet()

        # Заголовки с поддержкой кириллицы
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='DejaVu-Bold',
            fontSize=24,
            textColor='#2c3e50',
            spaceAfter=12,
            alignment=TA_CENTER
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontName='DejaVu',
            fontSize=14,
            textColor='#7f8c8d',
            spaceAfter=20,
            alignment=TA_CENTER
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName='DejaVu',
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=10
        )

        # Собираем контент
        story = []

        # Титульная страница
        story.append(Spacer(1, 40*mm))
        story.append(Paragraph("Нумерологический отчёт", title_style))
        story.append(Paragraph(f"{order.tariff.value}", subtitle_style))
        story.append(Spacer(1, 10*mm))

        # Участники
        story.append(Paragraph("<b>Участники анализа:</b>", normal_style))
        for p in participants:
            birth_time = p.birth_time.strftime("%H:%M") if p.birth_time else "не указано"
            birth_place = p.birth_place or "не указано"
            participant_text = f"""
            <b>{p.full_name}</b><br/>
            Дата рождения: {p.birth_date.strftime("%d.%m.%Y")}<br/>
            Время рождения: {birth_time}<br/>
            Место рождения: {birth_place}
            """
            story.append(Paragraph(participant_text, normal_style))
            story.append(Spacer(1, 5*mm))

        # Информация о заказе
        info_text = f"""
        Стиль: {order.style.value}<br/>
        Дата создания: {datetime.now().strftime("%d.%m.%Y %H:%M")}<br/>
        Номер заказа: {order.order_uuid}
        """
        story.append(Paragraph(info_text, normal_style))
        story.append(PageBreak())

        # Содержание отчёта
        # Разбиваем текст на параграфы
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.strip(), normal_style))
                story.append(Spacer(1, 5*mm))

        # Футер
        story.append(Spacer(1, 20*mm))
        footer_text = f"""
        <i>Этот отчёт создан специально для вас на основе нумерологического анализа.</i><br/>
        © {datetime.now().strftime("%d.%m.%Y")} Numerology Bot
        """
        footer_style = ParagraphStyle(
            'Footer',
            parent=normal_style,
            fontSize=9,
            textColor='#7f8c8d',
            alignment=TA_CENTER
        )
        story.append(Paragraph(footer_text, footer_style))

        # Генерируем PDF
        doc.build(story)

        logger.info(f"PDF сгенерирован: {pdf_path}")
        return str(pdf_path)

    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}")
        raise
