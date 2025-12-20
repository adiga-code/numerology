"""Webhook handler для Manus API."""
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ManusWebhookPayload(BaseModel):
    """Модель данных webhook от Manus."""
    task_id: str
    status: str
    result: str | None = None
    error: str | None = None


@router.post("/")
async def manus_webhook(request: Request, payload: ManusWebhookPayload):
    """
    Обработка webhook от Manus API.

    Args:
        request: FastAPI request
        payload: Данные от Manus

    Returns:
        dict: Статус обработки
    """
    logger.info(f"Получен webhook от Manus: task_id={payload.task_id}, status={payload.status}")

    try:
        db_manager = request.app.state.db

        # TODO: Обновить статус заказа в БД
        # TODO: Если success - сгенерировать PDF и отправить пользователю
        # TODO: Если failed - попробовать fallback на GPT-4/Gemini

        return {"status": "ok", "task_id": payload.task_id}

    except Exception as e:
        logger.error(f"Ошибка обработки Manus webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
