"""Обработчики системы отзывов."""
import logging
import asyncio
from datetime import datetime
from aiogram import Router, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Order, User, Review

logger = logging.getLogger(__name__)

router = Router()


class ReviewCallback(CallbackData, prefix="review"):
    """Callback данные для отзывов."""
    order_id: int
    rating: int


class ReviewStates(StatesGroup):
    """Состояния для сбора отзыва."""
    waiting_for_comment = State()


async def request_review(bot: Bot, order_id: int, user_telegram_id: int):
    """
    Запрос отзыва у пользователя через 1 час после отправки отчёта.

    Args:
        bot: Экземпляр бота
        order_id: ID заказа
        user_telegram_id: Telegram ID пользователя
    """
    try:
        # Ждём 1 час
        await asyncio.sleep(3600)  # 3600 секунд = 1 час

        # Формируем inline кнопки с оценками 1-5 звёзд
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{'⭐' * i}",
                        callback_data=ReviewCallback(order_id=order_id, rating=i).pack()
                    )
                    for i in range(1, 6)
                ]
            ]
        )

        await bot.send_message(
            chat_id=user_telegram_id,
            text=(
                "⭐ <b>Оцените ваш отчёт</b>\n\n"
                "Пожалуйста, поставьте оценку от 1 до 5 звёзд.\n"
                "Ваше мнение поможет нам улучшить сервис!"
            ),
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        logger.info(f"Запрос отзыва отправлен для заказа {order_id} пользователю {user_telegram_id}")

    except asyncio.CancelledError:
        logger.info(f"Запрос отзыва отменён для заказа {order_id}")
    except Exception as e:
        logger.error(f"Ошибка при запросе отзыва для заказа {order_id}: {e}")


@router.callback_query(ReviewCallback.filter())
async def process_review_rating(
    callback: CallbackQuery,
    callback_data: ReviewCallback,
    state: FSMContext,
    session: AsyncSession
):
    """Обработка оценки отзыва."""
    try:
        # Проверяем, что заказ принадлежит пользователю
        result = await session.execute(
            select(Order)
            .join(User)
            .where(
                Order.id == callback_data.order_id,
                User.telegram_id == callback.from_user.id
            )
        )
        order = result.scalar_one_or_none()

        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        # Проверяем, не оставлен ли уже отзыв
        result = await session.execute(
            select(Review).where(Review.order_id == order.id)
        )
        existing_review = result.scalar_one_or_none()

        if existing_review:
            await callback.answer("Вы уже оставили отзыв на этот заказ", show_alert=True)
            return

        # Сохраняем оценку в состояние
        await state.update_data(
            order_id=order.id,
            user_id=order.user_id,
            rating=callback_data.rating
        )

        # Спрашиваем комментарий
        await callback.message.edit_text(
            f"Спасибо за оценку {'⭐' * callback_data.rating}!\n\n"
            "Хотите оставить комментарий?\n\n"
            "Напишите ваш отзыв или нажмите /skip для пропуска.",
            parse_mode="HTML"
        )

        await state.set_state(ReviewStates.waiting_for_comment)
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при обработке оценки отзыва: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(ReviewStates.waiting_for_comment)
async def process_review_comment(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка комментария к отзыву."""
    try:
        # Получаем данные из состояния
        data = await state.get_data()

        # Проверка на команду /skip
        comment = None if message.text == "/skip" else message.text

        # Сохраняем отзыв в БД
        review = Review(
            order_id=data["order_id"],
            user_id=data["user_id"],
            rating=data["rating"],
            comment=comment,
            created_at=datetime.utcnow()
        )
        session.add(review)
        await session.commit()

        await message.answer(
            "✅ <b>Спасибо за отзыв!</b>\n\n"
            "Ваше мнение очень важно для нас и поможет улучшить сервис.",
            parse_mode="HTML"
        )

        logger.info(
            f"Отзыв сохранён: order_id={data['order_id']}, "
            f"rating={data['rating']}, comment={'Yes' if comment else 'No'}"
        )

        # Очищаем состояние
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при сохранении отзыва: {e}")
        await message.answer(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Попробуйте позже или обратитесь в поддержку: /support",
            parse_mode="HTML"
        )
        await state.clear()
