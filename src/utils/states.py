"""FSM состояния для бота."""
from aiogram.fsm.state import State, StatesGroup


class OrderFlow(StatesGroup):
    """Состояния процесса создания заказа."""

    # Выбор тарифа
    choosing_tariff = State()

    # Сбор данных для участников
    entering_full_name = State()
    entering_birth_date = State()
    entering_birth_time = State()
    entering_birth_place = State()

    # Для парного и семейного тарифа
    asking_partner_data = State()
    asking_family_count = State()

    # Выбор стиля
    choosing_style = State()

    # Оплата
    choosing_payment_method = State()
    waiting_payment = State()

    # Подтверждение
    confirming_order = State()
