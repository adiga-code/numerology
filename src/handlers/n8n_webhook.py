"""Webhook endpoints для приёма результатов от N8N."""
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from services.n8n_result_handler import handle_n8n_result, handle_n8n_error
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook/n8n", tags=["n8n"])
config = Config()


class N8nResultRequest(BaseModel):
    """Модель запроса от N8N с результатом генерации."""
    order_id: int
    status: str  # "success" или "failed"
    text: Optional[str] = None  # Текст отчёта (если успех)
    error: Optional[str] = None  # Сообщение об ошибке (если провал)


def verify_n8n_token(x_n8n_token: Optional[str] = Header(None)) -> None:
    """
    Проверка секретного токена от N8N.

    Args:
        x_n8n_token: Токен из заголовка X-N8N-Token

    Raises:
        HTTPException: Если токен неверный или отсутствует
    """
    if not config.N8N_SECRET_TOKEN:
        logger.warning("N8N_SECRET_TOKEN не настроен - пропускаем проверку токена")
        return

    if not x_n8n_token:
        logger.error("N8N запрос без токена")
        raise HTTPException(status_code=401, detail="Missing N8N token")

    if x_n8n_token != config.N8N_SECRET_TOKEN:
        logger.error(f"N8N запрос с неверным токеном: {x_n8n_token}")
        raise HTTPException(status_code=403, detail="Invalid N8N token")


@router.post("/result")
async def receive_n8n_result(
    request: Request,
    request_data: N8nResultRequest,
    x_n8n_token: Optional[str] = Header(None)
):
    """
    Endpoint для приёма результатов генерации от N8N.

    N8N должен отправить POST запрос с JSON:
    {
        "order_id": 123,
        "status": "success",
        "text": "сгенерированный отчёт"
    }

    Или при ошибке:
    {
        "order_id": 123,
        "status": "failed",
        "error": "описание ошибки"
    }

    Заголовок: X-N8N-Token: your_secret_token

    Args:
        request: FastAPI request
        request_data: Данные от N8N
        x_n8n_token: Токен из заголовка для проверки

    Returns:
        dict: Статус обработки
    """
    # Проверка токена
    verify_n8n_token(x_n8n_token)

    # Получаем зависимости из app state
    bot = request.app.state.bot
    db_manager = request.app.state.db

    logger.info(
        f"Получен результат от N8N для заказа {request_data.order_id}, "
        f"статус: {request_data.status}"
    )

    # Получаем сессию БД
    async with db_manager.get_session() as session:
        try:
            if request_data.status == "success":
                if not request_data.text:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing 'text' field for success status"
                    )

                # Обрабатываем успешный результат
                await handle_n8n_result(
                    order_id=request_data.order_id,
                    text=request_data.text,
                    session=session,
                    bot=bot
                )

                return {
                    "status": "ok",
                    "message": f"Report processed for order {request_data.order_id}"
                }

            elif request_data.status == "failed":
                error_msg = request_data.error or "Unknown error from N8N"

                # Обрабатываем ошибку
                await handle_n8n_error(
                    order_id=request_data.order_id,
                    error_message=error_msg,
                    session=session,
                    bot=bot
                )

                return {
                    "status": "ok",
                    "message": f"Error processed for order {request_data.order_id}"
                }

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown status: {request_data.status}"
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке результата N8N: {e}")
            raise HTTPException(status_code=500, detail=str(e))
