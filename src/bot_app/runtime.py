import asyncio
import contextlib
import importlib
import os
import re
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    Message,
    ReplyKeyboardRemove,
    User,
)

from bot_app import db as bot_db
from bot_app import keyboards
from bot_app import texts


def load_dotenv(env_path: str = ".env") -> None:
    path = Path(env_path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    get_admin_ids.cache_clear()


router = Router()

CATEGORIES: dict[str, str] = {
    "city": "🏙 Городской скутер",
    "travel": "🛵 Комфортный для города и поездок",
    "light": "🏍 Легкий мотоцикл",
    "no_license": "🪪 Без прав",
}

START_TEXT = (
    "Привет это бот для быстрой аренды байков в городе нячанг. "
    "здесь можно посмотреть доступные байки на сегодня"
)

ADMIN_FLOW: dict[int, dict[str, str]] = {}
USER_BOOKING_FLOW: dict[int, dict[str, str | int]] = {}
USER_MANAGER_FLOW: dict[int, dict[str, str | int]] = {}
USER_SOS_FLOW: dict[int, dict[str, str | int]] = {}


@lru_cache(maxsize=1)
def _user_handlers():
    return importlib.import_module("bot_app.user_handlers")


@lru_cache(maxsize=1)
def _admin_handlers():
    return importlib.import_module("bot_app.admin_handlers")


@lru_cache(maxsize=1)
def _flows():
    return importlib.import_module("bot_app.flows")


@lru_cache(maxsize=1)
def get_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "")
    result: set[int] = set()
    for part in raw.split(","):
        value = part.strip()
        if value.isdigit():
            result.add(int(value))
    return result


def is_admin(user_id: int) -> bool:
    return user_id in get_admin_ids()


def make_scooter_title(model: dict[str, str | int]) -> str:
    title = str(model.get("title", "")).strip()
    if title:
        return title[:60]
    return f"Модель #{model['id']}"


def categories_keyboard(user_id: int | None = None):
    _ = user_id
    return keyboards.categories_keyboard(CATEGORIES)


def sos_keyboard():
    return keyboards.sos_keyboard()


def main_reply_keyboard(user_id: int | None = None):
    is_admin_user = bool(user_id and is_admin(user_id))
    has_active_booking = bool(
        user_id and (not is_admin_user) and bot_db.get_latest_active_booking(user_id)
    )
    return keyboards.main_reply_keyboard(
        is_admin_user=is_admin_user,
        has_active_booking=has_active_booking,
    )


def delivery_location_keyboard(user_id: int | None = None):
    show_sos_button = bool(user_id and (not is_admin(user_id)) and bot_db.get_latest_sos_booking(user_id))
    return keyboards.delivery_location_keyboard(show_sos_button=show_sos_button)


def sos_location_keyboard(user_id: int | None = None):
    show_sos_button = bool(user_id and (not is_admin(user_id)) and bot_db.get_latest_sos_booking(user_id))
    return keyboards.sos_location_keyboard(show_sos_button=show_sos_button)


def parse_start_date(rental_date_raw: str) -> datetime | None:
    # Supports free text like "с 12.03 по 18.03" or "12.03.2026".
    match = re.search(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?", rental_date_raw or "")
    if not match:
        return None
    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3)) if match.group(3) else datetime.now().year
    try:
        return datetime(year, month, day, 10, 0, 0)
    except ValueError:
        return None


def scooters_keyboard(category_code: str):
    category_scooters = bot_db.list_scooters(category_code, only_available=True)
    scooter_items = [(int(scooter["id"]), make_scooter_title(scooter)) for scooter in category_scooters]
    return keyboards.scooters_keyboard(scooter_items)


def admin_main_keyboard():
    return keyboards.admin_main_keyboard()


def admin_booking_status_menu_keyboard():
    return keyboards.admin_booking_status_menu_keyboard()


def admin_booking_view_mode_keyboard(status_code: str, total_count: int):
    return keyboards.admin_booking_view_mode_keyboard(status_code, total_count)


def admin_wipe_confirm_keyboard():
    return keyboards.admin_wipe_confirm_keyboard()


def admin_booking_wipe_confirm_keyboard():
    return keyboards.admin_booking_wipe_confirm_keyboard()


def admin_delete_keyboard():
    scooters = [(int(scooter["id"]), make_scooter_title(scooter)) for scooter in bot_db.list_scooters()]
    return keyboards.admin_delete_keyboard(scooters)


def admin_availability_keyboard():
    scooters = [
        (
            int(scooter["id"]),
            make_scooter_title(scooter),
            bool(int(scooter.get("is_available", 1))),
        )
        for scooter in bot_db.list_scooters()
    ]
    return keyboards.admin_availability_keyboard(scooters)


def scooter_actions_keyboard(scooter_id: int, category_code: str):
    return keyboards.scooter_actions_keyboard(scooter_id, category_code)


def delivery_keyboard():
    return keyboards.delivery_keyboard()


def booking_confirm_keyboard():
    return keyboards.booking_confirm_keyboard()


def booking_rules_ack_keyboard():
    return keyboards.booking_rules_ack_keyboard()


def booking_success_keyboard():
    return keyboards.booking_success_keyboard()


def useful_info_keyboard():
    return keyboards.useful_info_keyboard()


def admin_booking_actions_keyboard(booking_id: int, user_link: str, status: str = "pending"):
    return keyboards.admin_booking_actions_keyboard(booking_id, user_link, status)


def admin_reject_reasons_keyboard(booking_id: int):
    return keyboards.admin_reject_reasons_keyboard(booking_id)


def telegram_profile_link(user: User) -> str:
    if user.username:
        return f"https://t.me/{user.username}"
    return ""


def resolve_user_link(raw_user_link: str, raw_user_contact: str = "") -> str:
    user_link = (raw_user_link or "").strip()
    user_contact = (raw_user_contact or "").strip()
    if user_link.startswith("https://t.me/"):
        return user_link
    if user_contact.startswith("https://t.me/"):
        return user_contact
    if user_contact.startswith("@") and len(user_contact) > 1:
        return f"https://t.me/{user_contact[1:]}"
    return ""


def booking_summary_text(user: User, state: dict[str, str | int], scooter_title: str) -> str:
    return texts.booking_summary_text(
        user_full_name=user.full_name,
        user_link=telegram_profile_link(user),
        state=state,
        scooter_title=scooter_title,
    )


def admin_booking_text(booking: dict[str, str | int]) -> str:
    resolved_user_link = resolve_user_link(
        raw_user_link=str(booking.get("user_link", "")),
        raw_user_contact=str(booking.get("user_contact", "")).strip(),
    )
    return texts.admin_booking_text(booking, resolved_user_link)


def user_bookings_text(bookings: list[dict[str, str | int]]) -> str:
    return texts.user_bookings_text(bookings)


async def notify_admins_about_booking(message: Message, booking_id: int) -> int:
    booking = bot_db.get_booking(booking_id)
    if not booking:
        return 0
    delivered = 0
    for admin_id in get_admin_ids():
        try:
            user_link = resolve_user_link(
                raw_user_link=str(booking.get("user_link", "")),
                raw_user_contact=str(booking.get("user_contact", "")),
            )
            await message.bot.send_message(
                chat_id=admin_id,
                text=admin_booking_text(booking),
                reply_markup=admin_booking_actions_keyboard(
                    booking_id=booking_id,
                    user_link=user_link,
                    status=str(booking.get("status", "pending")),
                ),
            )
            delivered += 1
        except Exception:
            # Admin may block bot or never started chat.
            continue
    return delivered


async def reminder_loop(bot: Bot) -> None:
    while True:
        try:
            now = datetime.now()
            for booking in bot_db.list_active_bookings_for_reminders():
                booking_id = int(booking.get("id", 0))
                start_dt = parse_start_date(str(booking.get("rental_date", "")))
                if not start_dt:
                    continue
                delta = start_dt - now
                if not (timedelta(hours=0) < delta <= timedelta(hours=24)):
                    continue

                user_sent = bool(int(booking.get("reminder_user_sent", 0)))
                admin_sent = bool(int(booking.get("reminder_admin_sent", 0)))

                if not user_sent:
                    try:
                        await bot.send_message(
                            chat_id=int(booking["user_id"]),
                            text=(
                                f"Напоминание по брони #{booking_id}:\n"
                                "До начала аренды осталось меньше 24 часов."
                            ),
                        )
                        user_sent = True
                    except Exception:
                        pass

                if not admin_sent:
                    admin_delivered = 0
                    for admin_id in get_admin_ids():
                        try:
                            await bot.send_message(
                                chat_id=admin_id,
                                text=(
                                    f"Напоминание менеджеру по брони #{booking_id}:\n"
                                    f"Клиент: {booking.get('user_name', '')}\n"
                                    f"Дата аренды: {booking.get('rental_date', '')}\n"
                                    "Старт менее чем через 24 часа."
                                ),
                            )
                            admin_delivered += 1
                        except Exception:
                            continue
                    admin_sent = admin_delivered > 0

                bot_db.mark_booking_reminders_sent(
                    booking_id,
                    user_sent=user_sent,
                    admin_sent=admin_sent,
                )
        except Exception:
            # Keep reminder loop alive even on transient errors.
            pass

        await asyncio.sleep(300)


async def send_rules_and_contract(message: Message) -> None:
    rules_text = bot_db.get_setting("booking_rules").strip()
    contract_file_id = bot_db.get_setting("contract_file_id").strip()
    contract_caption = bot_db.get_setting("contract_caption").strip() or "Образец договора"

    if rules_text:
        await message.answer(f"Правила бронирования:\n{rules_text}")

    if contract_file_id:
        await message.answer(contract_caption)
        await message.answer_document(document=contract_file_id)
    else:
        await message.answer("Образец договора пока не добавлен.")


async def show_main_menu(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    is_admin_user = bool(user_id and is_admin(user_id))
    start_photo_path = os.getenv("START_PHOTO_PATH", "").strip()
    start_photo_url = os.getenv("START_PHOTO_URL", "").strip()

    if start_photo_path and Path(start_photo_path).is_file():
        await message.answer_photo(
            photo=FSInputFile(start_photo_path),
            caption=START_TEXT,
            reply_markup=main_reply_keyboard(user_id),
        )
    elif start_photo_url:
        await message.answer_photo(
            photo=start_photo_url,
            caption=START_TEXT,
            reply_markup=main_reply_keyboard(user_id),
        )
    else:
        await message.answer(START_TEXT, reply_markup=main_reply_keyboard(user_id))
    if not is_admin_user:
        await message.answer("Нажмите кнопку `🛵 Выбрать байк`, чтобы открыть категории.")


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    await _user_handlers().on_start(message)


@router.message(lambda m: (m.text or "").strip().lower() == "меню")
async def on_menu_button(message: Message) -> None:
    await _user_handlers().on_menu_button(message)


@router.message(lambda m: (m.text or "").strip().lower() == "🛵 выбрать байк")
async def on_choose_bike_button(message: Message) -> None:
    await _user_handlers().on_choose_bike_button(message)


@router.message(lambda m: (m.text or "").strip().lower() == "📋 правила бронирования")
async def on_rules_button(message: Message) -> None:
    await _user_handlers().on_rules_button(message)


@router.message(lambda m: (m.text or "").strip().lower() == "🧾 мои заявки")
async def on_my_bookings_button(message: Message) -> None:
    await _user_handlers().on_my_bookings_button(message)


@router.message(lambda m: (m.text or "").strip().lower() == "💬 связаться с менеджером")
async def on_contact_manager_button(message: Message) -> None:
    await _user_handlers().on_contact_manager_button(message)


@router.message(lambda m: (m.text or "").strip().lower() == "админ")
async def on_admin_button(message: Message) -> None:
    await _admin_handlers().on_admin_button(message)


@router.message(
    lambda m: (m.text or "").strip().lower() in {"брони", "управление бронями"}
)
async def on_bookings_button(message: Message) -> None:
    await _admin_handlers().on_bookings_button(message)


@router.message(
    lambda m: (m.text or "").strip().lower() in {"управление доступностью", "доступность"}
)
async def on_availability_button(message: Message) -> None:
    await _admin_handlers().on_availability_button(message)


@router.message(lambda m: (m.text or "").strip().lower() in {"sos", "🔴 sos"})
async def on_sos_button(message: Message) -> None:
    await _user_handlers().on_sos_button(message)


@router.message(lambda m: (m.text or "").strip().lower() == "ℹ️ полезная информация")
async def on_useful_info_button(message: Message) -> None:
    await _user_handlers().on_useful_info_button(message)


@router.message(Command("categories"))
async def on_categories(message: Message) -> None:
    await _user_handlers().on_categories(message)


@router.message(Command("admin"))
async def on_admin(message: Message) -> None:
    await _admin_handlers().on_admin(message)


@router.callback_query(lambda c: c.data and c.data.startswith("admin_add:"))
async def on_admin_add_clicked(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_add_clicked(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("admin_del:"))
async def on_admin_delete_clicked(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_delete_clicked(callback)


@router.callback_query(lambda c: c.data == "admin_office:set")
async def on_admin_office_set(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_office_set(callback)


@router.callback_query(lambda c: c.data == "admin_rules:set")
async def on_admin_rules_set(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_rules_set(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("admin_info:"))
async def on_admin_info_set(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_info_set(callback)


@router.callback_query(lambda c: c.data == "admin_contract:set")
async def on_admin_contract_set(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_contract_set(callback)


@router.callback_query(lambda c: c.data == "admin_db:wipe")
async def on_admin_db_wipe_request(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_db_wipe_request(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("admin_availability:"))
async def on_admin_availability(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_availability(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("admin_booking_wipe:"))
async def on_admin_booking_wipe(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_booking_wipe(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("admin_db_wipe:"))
async def on_admin_db_wipe_confirm(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_db_wipe_confirm(callback)


@router.callback_query(lambda c: c.data == "admin_nav:start")
async def on_admin_back_to_start(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_back_to_start(callback)


@router.callback_query(lambda c: c.data == "rules:show")
async def on_show_rules(callback: CallbackQuery) -> None:
    await _user_handlers().on_show_rules(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("info:"))
async def on_info_selected(callback: CallbackQuery) -> None:
    await _user_handlers().on_info_selected(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("sos:"))
async def on_sos_selected(callback: CallbackQuery) -> None:
    await _user_handlers().on_sos_selected(callback)


@router.callback_query(lambda c: c.data == "user_booking:list")
async def on_user_booking_list(callback: CallbackQuery) -> None:
    await _user_handlers().on_user_booking_list(callback)


@router.callback_query(lambda c: c.data == "user_manager:contact")
async def on_user_manager_contact(callback: CallbackQuery) -> None:
    await _user_handlers().on_user_manager_contact(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("admin_booking:"))
async def on_admin_booking_action(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_booking_action(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("admin_booking_reject:"))
async def on_admin_booking_reject_reason(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_booking_reject_reason(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("admin_booking_state:"))
async def on_admin_booking_state(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_booking_state(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("admin_booking_view:"))
async def on_admin_booking_view(callback: CallbackQuery) -> None:
    await _admin_handlers().on_admin_booking_view(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("cat:"))
async def on_category_selected(callback: CallbackQuery) -> None:
    await _user_handlers().on_category_selected(callback)


@router.callback_query(lambda c: c.data == "back:categories")
async def on_back_to_categories(callback: CallbackQuery) -> None:
    await _user_handlers().on_back_to_categories(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("scooter:"))
async def on_scooter_selected(callback: CallbackQuery) -> None:
    await _user_handlers().on_scooter_selected(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("more:"))
async def on_more_bikes(callback: CallbackQuery) -> None:
    await _user_handlers().on_more_bikes(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("book:"))
async def on_book_clicked(callback: CallbackQuery) -> None:
    await _user_handlers().on_book_clicked(callback)


@router.message()
async def on_text_flows(message: Message) -> None:
    await _flows().on_text_flows(message)


@router.callback_query(lambda c: c.data and c.data.startswith("delivery:"))
async def on_delivery_selected(callback: CallbackQuery) -> None:
    await _user_handlers().on_delivery_selected(callback)


@router.callback_query(lambda c: c.data and c.data.startswith("booking_confirm:"))
async def on_booking_confirm(callback: CallbackQuery) -> None:
    await _user_handlers().on_booking_confirm(callback)


@router.callback_query(lambda c: c.data == "user_nav:menu")
async def on_user_nav_menu(callback: CallbackQuery) -> None:
    await _user_handlers().on_user_nav_menu(callback)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp


async def run() -> None:
    load_dotenv()
    bot_db.init_db()
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Add it to .env as BOT_TOKEN=...")

    bot = Bot(token=bot_token)
    dp = build_dispatcher()
    reminder_task = asyncio.create_task(reminder_loop(bot))
    try:
        while True:
            try:
                await dp.start_polling(bot)
                break
            except asyncio.CancelledError:
                raise
            except Exception:
                # Auto-restart bot polling on transient network/Telegram errors.
                await asyncio.sleep(5)
    finally:
        reminder_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reminder_task


class BikeRentalBotApplication:
    async def run(self) -> None:
        await run()
