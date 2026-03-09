import asyncio

from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.types import CallbackQuery, Message

from bot_app import db as bot_db
from bot_app import runtime as rt


async def _safe_callback_answer(
    callback: CallbackQuery,
    text: str | None = None,
    *,
    show_alert: bool = False,
) -> None:
    try:
        await callback.answer(text, show_alert=show_alert)
    except TelegramBadRequest as exc:
        msg = str(exc).lower()
        if "query is too old" in msg or "query id is invalid" in msg:
            return
        raise

async def _safe_message_send(sender, *args, **kwargs) -> bool:
    for attempt in range(3):
        try:
            await sender(*args, **kwargs)
            return True
        except TelegramNetworkError:
            if attempt == 2:
                return False
            await asyncio.sleep(0.7 * (attempt + 1))
    return False


async def on_start(message: Message) -> None:
    await rt.show_main_menu(message)


async def on_menu_button(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    await message.answer("Главное меню", reply_markup=rt.main_reply_keyboard(user_id))
    if not (user_id and rt.is_admin(user_id)):
        await message.answer("Нажмите кнопку `🛵 Выбрать байк`, чтобы открыть категории.")


async def on_choose_bike_button(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    await message.answer(
        "Выберите категорию байка:",
        reply_markup=rt.categories_keyboard(user_id),
    )


async def on_rules_button(message: Message) -> None:
    await rt.send_rules_and_contract(message)


async def on_my_bookings_button(message: Message) -> None:
    if not message.from_user:
        return
    bookings = bot_db.list_user_bookings(message.from_user.id)
    if not bookings:
        await message.answer("У вас пока нет активных или одобренных заявок.")
        return
    await message.answer(rt.user_bookings_text(bookings))


async def on_contact_manager_button(message: Message) -> None:
    if not message.from_user:
        return
    active_booking = bot_db.get_latest_active_booking(message.from_user.id)
    if not active_booking:
        await message.answer("Активной заявки нет. Кнопка доступна только при активной заявке.")
        return
    rt.USER_MANAGER_FLOW[message.from_user.id] = {
        "stage": "await_manager_message",
        "booking_id": int(active_booking["id"]),
    }
    await message.answer("Напишите сообщение менеджеру по вашей заявке.")


async def on_sos_button(message: Message) -> None:
    if not message.from_user:
        return
    approved = bot_db.get_latest_sos_booking(message.from_user.id)
    if not approved:
        await message.answer(
            "Кнопка SOS доступна только при одобренной заявке.",
            reply_markup=rt.main_reply_keyboard(message.from_user.id),
        )
        return
    await message.answer("Выберите причину SOS:", reply_markup=rt.sos_keyboard())


async def on_useful_info_button(message: Message) -> None:
    if not message.from_user:
        return
    active_booking = bot_db.get_latest_active_booking(message.from_user.id)
    if not active_booking:
        await message.answer(
            "Раздел доступен после активации брони менеджером.",
            reply_markup=rt.main_reply_keyboard(message.from_user.id),
        )
        return
    await message.answer(
        "Полезная информация:",
        reply_markup=rt.useful_info_keyboard(),
    )


async def on_categories(message: Message) -> None:
    lines = ["Категории каталога:"]
    for code, title in rt.CATEGORIES.items():
        lines.append(f"- {code}: {title}")
    await message.answer("\n".join(lines))


async def on_show_rules(callback: CallbackQuery) -> None:
    await rt.send_rules_and_contract(callback.message)
    await _safe_callback_answer(callback)


async def on_info_selected(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    active_booking = bot_db.get_latest_active_booking(callback.from_user.id)
    if not active_booking:
        await _safe_callback_answer(callback, "Доступно только при активной брони.", show_alert=True)
        return

    assert callback.data is not None
    key = callback.data.split(":", 1)[1]
    if key == "tips":
        text = bot_db.get_setting("info_tips_text").strip()
        video_file_id = bot_db.get_setting("info_tips_video_file_id").strip()
        if not text and not video_file_id:
            await _safe_message_send(callback.message.answer, "Гайд по вождению пока не добавлен. Обратитесь к менеджеру.")
            await _safe_callback_answer(callback)
            return
        if text:
            await _safe_message_send(callback.message.answer, f"🛵 Гайд по вождению:\n{text}")
        if video_file_id:
            await _safe_message_send(callback.message.answer_video, video=video_file_id)
        await _safe_callback_answer(callback)
        return

    if key == "guide":
        text = bot_db.get_setting("info_guide_text").strip()
        document_file_id = bot_db.get_setting("info_guide_document_file_id").strip()
        if not text and not document_file_id:
            await _safe_message_send(callback.message.answer, "Путеводитель пока не добавлен. Обратитесь к менеджеру.")
            await _safe_callback_answer(callback)
            return
        if text:
            await _safe_message_send(callback.message.answer, f"🗺️ Путеводитель:\n{text}")
        if document_file_id:
            await _safe_message_send(callback.message.answer_document, document=document_file_id)
        await _safe_callback_answer(callback)
        return

    await _safe_callback_answer(callback, "Неизвестный раздел", show_alert=True)


async def on_sos_selected(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    approved = bot_db.get_latest_sos_booking(callback.from_user.id)
    if not approved:
        await _safe_callback_answer(callback, "Нет одобренной заявки для SOS.", show_alert=True)
        return

    assert callback.data is not None
    reason_code = callback.data.split(":", 1)[1]
    reason_map = {
        "breakdown": "Поломка байка",
        "accident": "ДТП",
        "other": "Другая причина",
    }
    reason = reason_map.get(reason_code)
    if not reason:
        await _safe_callback_answer(callback, "Неизвестная причина", show_alert=True)
        return

    user_link = rt.resolve_user_link(
        raw_user_link=str(approved.get("user_link", "")),
        raw_user_contact=str(approved.get("user_contact", "")),
    )
    link_display = user_link or "не указана"

    rt.USER_SOS_FLOW[callback.from_user.id] = {
        "stage": "await_sos_location",
        "booking_id": int(approved["id"]),
        "reason_code": reason_code,
        "reason_title": reason,
        "user_link": link_display,
    }
    await _safe_message_send(callback.message.answer, 
        "Отправьте вашу текущую геолокацию.",
        reply_markup=rt.sos_location_keyboard(callback.from_user.id),
    )
    await _safe_callback_answer(callback)


async def on_user_booking_list(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    bookings = bot_db.list_user_bookings(callback.from_user.id)
    if not bookings:
        await _safe_message_send(callback.message.answer, "У вас пока нет активных или одобренных заявок.")
        await _safe_callback_answer(callback)
        return
    await _safe_message_send(callback.message.answer, rt.user_bookings_text(bookings))
    await _safe_callback_answer(callback)


async def on_user_manager_contact(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    active_booking = bot_db.get_latest_active_booking(callback.from_user.id)
    if not active_booking:
        await _safe_message_send(callback.message.answer, "Активной заявки нет. Кнопка доступна только при активной заявке.")
        await _safe_callback_answer(callback)
        return
    rt.USER_MANAGER_FLOW[callback.from_user.id] = {
        "stage": "await_manager_message",
        "booking_id": int(active_booking["id"]),
    }
    await _safe_message_send(callback.message.answer, "Напишите сообщение менеджеру по вашей заявке.")
    await _safe_callback_answer(callback)


async def on_category_selected(callback: CallbackQuery) -> None:
    assert callback.data is not None
    category_code = callback.data.split(":", 1)[1]
    category_title = rt.CATEGORIES.get(category_code)
    if not category_title:
        await _safe_callback_answer(callback, "Unknown category", show_alert=True)
        return

    if not bot_db.list_scooters(category_code, only_available=True):
        await _safe_message_send(callback.message.edit_text, 
            f"Категория: {category_title}\nПока нет доступных моделей.",
            reply_markup=rt.scooters_keyboard(category_code),
        )
        await _safe_callback_answer(callback)
        return

    await _safe_message_send(callback.message.edit_text, 
        f"Категория: {category_title}\nВыберите модель:",
        reply_markup=rt.scooters_keyboard(category_code),
    )
    await _safe_callback_answer(callback)


async def on_back_to_categories(callback: CallbackQuery) -> None:
    await _safe_message_send(callback.message.edit_text, 
        "Выберите категорию скутера:",
        reply_markup=rt.categories_keyboard(callback.from_user.id if callback.from_user else None),
    )
    await _safe_callback_answer(callback)


async def on_scooter_selected(callback: CallbackQuery) -> None:
    assert callback.data is not None
    scooter_id = callback.data.split(":", 1)[1]
    if not scooter_id.isdigit():
        await _safe_callback_answer(callback, "Некорректный ID", show_alert=True)
        return
    scooter = bot_db.get_scooter_by_id(int(scooter_id))
    if not scooter:
        await _safe_callback_answer(callback, "Scooter not found", show_alert=True)
        return
    if not bool(int(scooter.get("is_available", 1))):
        await _safe_callback_answer(callback, "Эта модель сейчас недоступна.", show_alert=True)
        return

    msg_type = scooter.get("msg_type")
    text = str(scooter.get("text", ""))
    caption = str(scooter.get("caption", ""))
    photo_file_id = str(scooter.get("photo_file_id", ""))

    if msg_type == "photo" and photo_file_id:
        await _safe_message_send(callback.message.answer_photo, photo=photo_file_id, caption=caption or None)
    elif text:
        await _safe_message_send(callback.message.answer, text)
    elif caption:
        await _safe_message_send(callback.message.answer, caption)
    else:
        await _safe_message_send(callback.message.answer, "Карточка модели пуста.")

    await _safe_message_send(callback.message.answer, 
        "Что дальше?",
        reply_markup=rt.scooter_actions_keyboard(
            scooter_id=int(scooter["id"]),
            category_code=str(scooter["category"]),
        ),
    )
    await _safe_callback_answer(callback)


async def on_more_bikes(callback: CallbackQuery) -> None:
    assert callback.data is not None
    category_code = callback.data.split(":", 1)[1]
    category_title = rt.CATEGORIES.get(category_code, category_code)
    await _safe_message_send(callback.message.answer, 
        f"Категория: {category_title}\nВыберите модель:",
        reply_markup=rt.scooters_keyboard(category_code),
    )
    await _safe_callback_answer(callback)


async def on_book_clicked(callback: CallbackQuery) -> None:
    assert callback.data is not None
    scooter_id = callback.data.split(":", 1)[1]
    scooter = bot_db.get_scooter_by_id(int(scooter_id)) if scooter_id.isdigit() else None
    if not scooter:
        await _safe_callback_answer(callback, "Модель не найдена", show_alert=True)
        return
    if not bool(int(scooter.get("is_available", 1))):
        await _safe_callback_answer(callback, "Эта модель сейчас недоступна для брони.", show_alert=True)
        return

    if not callback.from_user:
        return
    rt.USER_BOOKING_FLOW[callback.from_user.id] = {
        "stage": "await_custom_dates",
        "scooter_id": int(scooter_id),
    }

    await _safe_message_send(callback.message.answer, 
        "Хорошо. Напишите свои даты аренды.\n"
        "Пример: с 12.03 по 18.03",
    )
    await _safe_callback_answer(callback)


async def on_delivery_selected(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    state = rt.USER_BOOKING_FLOW.get(callback.from_user.id)
    if not state or state.get("stage") not in {"await_delivery_choice"}:
        await _safe_callback_answer(callback, "Сначала выберите байк и срок аренды.", show_alert=True)
        return

    assert callback.data is not None
    choice = callback.data.split(":", 1)[1]
    if choice == "office":
        state["delivery"] = "office"
        state["stage"] = "await_confirm"
        scooter_id = int(state.get("scooter_id", 0))
        scooter = bot_db.get_scooter_by_id(scooter_id) if scooter_id else None
        scooter_name = rt.make_scooter_title(scooter) if scooter else f"ID {scooter_id}"
        office_link = bot_db.get_setting("office_link").strip()
        if office_link:
            state["office_link"] = office_link
        await _safe_message_send(callback.message.answer, 
            rt.booking_summary_text(callback.from_user, state, scooter_name),
            reply_markup=rt.booking_confirm_keyboard(),
        )
        if not office_link:
            await _safe_message_send(callback.message.answer, "Адрес офиса пока не настроен администратором.")
        await _safe_callback_answer(callback)
        return

    if choice == "yes":
        state["delivery"] = "yes"
        state["stage"] = "await_delivery_map"
        await _safe_message_send(callback.message.answer, 
            "Отправьте геолокацию кнопкой ниже или пришлите ссылку Google Maps.",
            reply_markup=rt.delivery_location_keyboard(callback.from_user.id if callback.from_user else None),
        )
        await _safe_callback_answer(callback)
        return

    await _safe_callback_answer(callback, "Неизвестный вариант", show_alert=True)


async def on_booking_confirm(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    state = rt.USER_BOOKING_FLOW.get(callback.from_user.id)
    if not state:
        await _safe_callback_answer(callback, "Заявка не найдена.", show_alert=True)
        return

    assert callback.data is not None
    action = callback.data.split(":", 1)[1]

    if action == "restart":
        rt.USER_BOOKING_FLOW.pop(callback.from_user.id, None)
        await _safe_message_send(callback.message.answer, 
            "Выберите категорию скутера:",
            reply_markup=rt.categories_keyboard(callback.from_user.id if callback.from_user else None),
        )
        await _safe_callback_answer(callback)
        return

    if action == "rules":
        await rt.send_rules_and_contract(callback.message)
        await _safe_message_send(callback.message.answer, 
            "Если все окей, нажмите кнопку ниже.",
            reply_markup=rt.booking_rules_ack_keyboard(),
        )
        await _safe_callback_answer(callback)
        return

    if action == "read":
        auto_user_link = rt.telegram_profile_link(callback.from_user).strip()
        if auto_user_link:
            scooter_id = int(state.get("scooter_id", 0))
            scooter = bot_db.get_scooter_by_id(scooter_id) if scooter_id else None
            scooter_title = rt.make_scooter_title(scooter) if scooter else f"ID {scooter_id}"
            booking_data: dict[str, str | int] = {
                "user_id": callback.from_user.id,
                "user_name": callback.from_user.full_name,
                "user_link": auto_user_link,
                "user_contact": auto_user_link,
                "scooter_title": scooter_title,
                "rental_date": str(state.get("rental_date") or state.get("custom_dates") or ""),
                "delivery_type": str(state.get("delivery") or ""),
                "delivery_map_link": str(state.get("delivery_map_link") or ""),
                "delivery_time": str(state.get("delivery_time") or ""),
            }
            booking_id = bot_db.create_booking(booking_data)
            delivered = await rt.notify_admins_about_booking(callback.message, booking_id)
            if delivered > 0:
                await _safe_message_send(callback.message.answer, 
                    "Отлично. Заявка подтверждена и принята в обработку.\n"
                    f"Номер брони: #{booking_id}\n"
                    "Менеджер скоро свяжется с вами.\n\n"
                    "После подтверждения брони менеджером появятся новые функции:\n"
                    "- кнопка SOS\n"
                    "- связь с менеджером",
                    reply_markup=rt.booking_success_keyboard(),
                )
            else:
                await _safe_message_send(callback.message.answer, 
                    "Заявка сохранена, но уведомление администратору не доставлено.\n"
                    f"Номер брони: #{booking_id}\n"
                    "Попросите администратора открыть чат с ботом и нажать /start.\n\n"
                    "Вам уже доступны новые функции в боте:\n"
                    "- кнопка SOS\n"
                    "- связь с менеджером",
                    reply_markup=rt.booking_success_keyboard(),
                )
            rt.USER_BOOKING_FLOW.pop(callback.from_user.id, None)
            await _safe_callback_answer(callback)
            return

        state["stage"] = "await_contact"
        await _safe_message_send(callback.message.answer, 
            "Отправьте, пожалуйста, ваш контакт для связи:\n"
            "- ссылку на Telegram (@username)\n"
            "или\n"
            "- номер телефона"
        )
        await _safe_callback_answer(callback)
        return

    await _safe_callback_answer(callback, "Неизвестная команда", show_alert=True)


async def on_user_nav_menu(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    user_id = callback.from_user.id
    await _safe_message_send(callback.message.answer, "Главное меню", reply_markup=rt.main_reply_keyboard(user_id))
    await _safe_message_send(callback.message.answer, "Нажмите кнопку `🛵 Выбрать байк`, чтобы открыть категории.")
    await _safe_callback_answer(callback)







