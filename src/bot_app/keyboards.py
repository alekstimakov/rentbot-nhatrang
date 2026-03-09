from collections.abc import Mapping, Sequence

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def categories_keyboard(categories: Mapping[str, str]):
    builder = InlineKeyboardBuilder()
    for code, title in categories.items():
        builder.button(text=title, callback_data=f"cat:{code}")
    builder.adjust(1)
    return builder.as_markup()


def main_reply_keyboard(*, is_admin_user: bool, has_active_booking: bool) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = [[KeyboardButton(text="Меню")]]
    if is_admin_user:
        rows.append([KeyboardButton(text="Админ"), KeyboardButton(text="Управление бронями")])
        rows.append([KeyboardButton(text="Управление доступностью")])
    else:
        rows.append([KeyboardButton(text="🛵 Выбрать байк")])
        rows.append([KeyboardButton(text="📋 Правила бронирования")])
        rows.append([KeyboardButton(text="🧾 Мои заявки")])
        rows.append([KeyboardButton(text="💬 Связаться с менеджером")])
        if has_active_booking:
            rows.append([KeyboardButton(text="ℹ️ Полезная информация")])
        rows.append([KeyboardButton(text="🔴 SOS")])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
    )


def sos_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Поломка байка", callback_data="sos:breakdown")
    builder.button(text="ДТП", callback_data="sos:accident")
    builder.button(text="Другая причина", callback_data="sos:other")
    builder.button(text="🏠 Вернуться в главное меню", callback_data="user_nav:menu")
    builder.adjust(1)
    return builder.as_markup()


def delivery_location_keyboard(*, show_sos_button: bool) -> ReplyKeyboardMarkup:
    menu_row = [KeyboardButton(text="Меню")]
    if show_sos_button:
        menu_row.append(KeyboardButton(text="SOS"))
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="Отправлю ссылкой")],
            menu_row,
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
    )


def sos_location_keyboard(*, show_sos_button: bool) -> ReplyKeyboardMarkup:
    menu_row = [KeyboardButton(text="Меню")]
    if show_sos_button:
        menu_row.append(KeyboardButton(text="SOS"))
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить текущую геолокацию", request_location=True)],
            menu_row,
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
    )


def scooters_keyboard(scooters: Sequence[tuple[int, str]]):
    builder = InlineKeyboardBuilder()
    for scooter_id, title in scooters:
        builder.button(text=title, callback_data=f"scooter:{scooter_id}")
    builder.button(text="Back to categories", callback_data="back:categories")
    builder.adjust(1)
    return builder.as_markup()


def admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Городской скутер", callback_data="admin_add:city")
    builder.button(text="➕ Комфортный скутер", callback_data="admin_add:travel")
    builder.button(text="➕ Легкий мотоцикл", callback_data="admin_add:light")
    builder.button(text="➕ Без прав", callback_data="admin_add:no_license")
    builder.button(text="🗑 Удалить модель", callback_data="admin_del:list")
    builder.button(text="📦 Доступность байков", callback_data="admin_availability:open")
    builder.button(text="📍 Адрес офиса", callback_data="admin_office:set")
    builder.button(text="📋 Правила бронирования", callback_data="admin_rules:set")
    builder.button(text="🛵 Советы по вождению", callback_data="admin_info:set_tips")
    builder.button(text="🗺️ Путеводитель", callback_data="admin_info:set_guide")
    builder.button(text="📄 Образец договора", callback_data="admin_contract:set")
    builder.button(text="🗑 Удалить все брони", callback_data="admin_booking_wipe:request")
    builder.button(text="☠️ Полная очистка базы", callback_data="admin_db:wipe")
    builder.button(text="🏠 В обычный режим", callback_data="admin_nav:start")
    builder.adjust(1)
    return builder.as_markup()


def admin_booking_status_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🕒 Брони в ожидании", callback_data="admin_booking_state:pending")
    builder.button(text="🟢 Активные брони", callback_data="admin_booking_state:active")
    builder.button(text="🔴 Отклоненные", callback_data="admin_booking_state:rejected")
    builder.button(text="✅ Завершенные", callback_data="admin_booking_state:finished")
    builder.button(
        text="🧹 Очистить отклоненные и завершенные",
        callback_data="admin_booking_state:cleanup",
    )
    builder.button(text="⬅️ Назад", callback_data="admin_booking_state:back")
    builder.adjust(1)
    return builder.as_markup()


def admin_booking_view_mode_keyboard(status_code: str, total_count: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🕔 Последние 5", callback_data=f"admin_booking_view:{status_code}:last5")
    builder.button(
        text=f"📚 Показать все ({total_count})",
        callback_data=f"admin_booking_view:{status_code}:all",
    )
    builder.button(text="⬅️ К статусам", callback_data="admin_booking_state:menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_wipe_confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, очистить все", callback_data="admin_db_wipe:yes")
    builder.button(text="❌ Отмена", callback_data="admin_db_wipe:no")
    builder.adjust(1)
    return builder.as_markup()


def admin_booking_wipe_confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить все брони", callback_data="admin_booking_wipe:yes")
    builder.button(text="❌ Отмена", callback_data="admin_booking_wipe:no")
    builder.adjust(1)
    return builder.as_markup()


def admin_delete_keyboard(scooters: Sequence[tuple[int, str]]):
    builder = InlineKeyboardBuilder()
    for scooter_id, title in scooters:
        builder.button(text=f"🗑 {title}", callback_data=f"admin_del:{scooter_id}")
    builder.button(text="⬅️ Назад", callback_data="admin_del:back")
    builder.adjust(1)
    return builder.as_markup()


def scooter_actions_keyboard(scooter_id: int, category_code: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Забронировать", callback_data=f"book:{scooter_id}")
    builder.button(text="🔎 Посмотреть другие", callback_data=f"more:{category_code}")
    builder.adjust(1)
    return builder.as_markup()


def delivery_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏢 Заберу в офисе (центр)", callback_data="delivery:office")
    builder.button(text="🚚 Нужна доставка", callback_data="delivery:yes")
    builder.adjust(1)
    return builder.as_markup()


def booking_confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Правила бронирования", callback_data="booking_confirm:rules")
    builder.button(text="🔁 Выбрать модель заново", callback_data="booking_confirm:restart")
    builder.adjust(1)
    return builder.as_markup()


def booking_rules_ack_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Я прочитал", callback_data="booking_confirm:read")
    builder.button(text="🔁 Выбрать модель заново", callback_data="booking_confirm:restart")
    builder.adjust(1)
    return builder.as_markup()


def booking_success_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Вернуться в главное меню", callback_data="user_nav:menu")
    builder.adjust(1)
    return builder.as_markup()


def useful_info_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🛵 Рекомендации по вождению", callback_data="info:tips")
    builder.button(text="🗺️ Путеводитель", callback_data="info:guide")
    builder.button(text="🏠 В главное меню", callback_data="user_nav:menu")
    builder.adjust(1)
    return builder.as_markup()


def admin_booking_actions_keyboard(booking_id: int, user_link: str, status: str = "pending"):
    builder = InlineKeyboardBuilder()
    if status == "pending":
        builder.button(text="✅ Подтвердить бронь", callback_data=f"admin_booking:confirm:{booking_id}")
        builder.button(text="❌ Отклонить", callback_data=f"admin_booking:reject:{booking_id}")
    else:
        builder.button(text="🏁 Отметить завершенной", callback_data=f"admin_booking:finish:{booking_id}")
        builder.button(text="❌ Отклонить", callback_data=f"admin_booking:reject:{booking_id}")
    if user_link.startswith("https://t.me/"):
        builder.button(text="💬 Открыть чат с клиентом", url=user_link)
    else:
        builder.button(text="💬 Написать клиенту", callback_data=f"admin_booking:message:{booking_id}")
    builder.adjust(1)
    return builder.as_markup()


def admin_reject_reasons_keyboard(booking_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📦 Нет байка в наличии",
        callback_data=f"admin_booking_reject:{booking_id}:no_stock",
    )
    builder.button(
        text="⚠️ Неверные данные",
        callback_data=f"admin_booking_reject:{booking_id}:invalid_data",
    )
    builder.button(
        text="✍️ Другая причина",
        callback_data=f"admin_booking_reject:{booking_id}:other",
    )
    builder.adjust(1)
    return builder.as_markup()


def admin_availability_keyboard(scooters: Sequence[tuple[int, str, bool]]):
    builder = InlineKeyboardBuilder()
    for scooter_id, title, is_available in scooters:
        prefix = "✅" if is_available else "⬜"
        builder.button(
            text=f"{prefix} {title}",
            callback_data=f"admin_availability:toggle:{scooter_id}",
        )
    builder.button(text="🏠 В админ-панель", callback_data="admin_availability:done")
    builder.adjust(1)
    return builder.as_markup()
