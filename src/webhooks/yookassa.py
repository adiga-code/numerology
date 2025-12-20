"""Webhook handler для ЮKassa."""
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class YooKassaWebhookPayload(BaseModel):
    """Модель данных webhook от ЮKassa."""
    type: str
    event: str
    object: dict


@router.post("/")
async def yookassa_webhook(request: Request, payload: YooKassaWebhookPayload):
    """
    Обработка webhook от ЮKassa.

    Args:
        request: FastAPI request
        payload: Данные от ЮKassa

    Returns:
        dict: Статус обработки
    """
    logger.info(f"Получен webhook от ЮKassa: type={payload.type}, event={payload.event}")

    try:
        db_manager = request.app.state.db

        # TODO: Проверить подпись webhook
        # TODO: Обновить статус платежа в БД
        # TODO: Если payment.succeeded - отправить заказ на генерацию
        # TODO: Если payment.canceled - отменить заказ

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Ошибка обработки ЮKassa webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
