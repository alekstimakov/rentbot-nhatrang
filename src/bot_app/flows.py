import os

from aiogram.types import Message

from bot_app import db as bot_db
from bot_app import runtime as rt


async def on_text_flows(message: Message) -> None:
    if message.from_user:
        sos_state = rt.USER_SOS_FLOW.get(message.from_user.id)
        if sos_state and sos_state.get("stage") == "await_sos_location":
            if not message.location:
                await message.answer(
                    "Нужна текущая геолокация. Нажмите кнопку отправки геолокации."
                )
                return
            booking_id_raw = str(sos_state.get("booking_id", "")).strip()
            booking_id = int(booking_id_raw) if booking_id_raw.isdigit() else 0
            lat = message.location.latitude
            lon = message.location.longitude
            sos_state["location_link"] = f"https://maps.google.com/?q={lat},{lon}"
            sos_state["stage"] = "await_sos_text"
            await message.answer(
                "Кратко опишите проблему (1-2 предложения).",
                reply_markup=rt.main_reply_keyboard(message.from_user.id),
            )
            return

        if sos_state and sos_state.get("stage") == "await_sos_text":
            details = (message.text or "").strip()
            if not details or details.startswith("/"):
                await message.answer("Опишите проблему обычным текстом (кратко).")
                return
            booking_id_raw = str(sos_state.get("booking_id", "")).strip()
            booking_id = int(booking_id_raw) if booking_id_raw.isdigit() else 0
            alert = (
                "SOS от клиента\n"
                f"Номер брони: #{booking_id}\n"
                f"Имя: {message.from_user.full_name}\n"
                f"Telegram ID: {message.from_user.id}\n"
                f"Ссылка на Telegram: {sos_state.get('user_link', 'не указана')}\n"
                f"Причина: {sos_state.get('reason_title', '')}\n"
                f"Геолокация: {sos_state.get('location_link', '')}\n"
                f"Краткое описание: {details}"
            )
            sent = 0
            for admin_id in rt.get_admin_ids():
                try:
                    await message.bot.send_message(chat_id=admin_id, text=alert)
                    sent += 1
                except Exception:
                    continue
            rt.USER_SOS_FLOW.pop(message.from_user.id, None)
            if sent > 0:
                await message.answer("SOS отправлен менеджеру.")
            else:
                await message.answer("Не удалось отправить SOS менеджеру.")
            return

        manager_state = rt.USER_MANAGER_FLOW.get(message.from_user.id)
        if manager_state and manager_state.get("stage") == "await_manager_message":
            client_message = (message.text or "").strip()
            if not client_message or client_message.startswith("/"):
                await message.answer("Введите сообщение менеджеру обычным текстом.")
                return
            booking_id_raw = str(manager_state.get("booking_id", "")).strip()
            if not booking_id_raw.isdigit():
                rt.USER_MANAGER_FLOW.pop(message.from_user.id, None)
                await message.answer("Не удалось определить заявку. Нажмите кнопку еще раз.")
                return
            booking = bot_db.get_booking(int(booking_id_raw))
            if not booking:
                rt.USER_MANAGER_FLOW.pop(message.from_user.id, None)
                await message.answer("Заявка не найдена.")
                return

            manager_text = (
                f"{rt.admin_booking_text(booking)}\n\n"
                "Сообщение от клиента:\n"
                f"{client_message}"
            )
            delivered = 0
            for admin_id in rt.get_admin_ids():
                try:
                    await message.bot.send_message(chat_id=admin_id, text=manager_text)
                    delivered += 1
                except Exception:
                    continue
            rt.USER_MANAGER_FLOW.pop(message.from_user.id, None)
            if delivered > 0:
                await message.answer("Сообщение отправлено менеджеру.")
            else:
                await message.answer(
                    "Не удалось доставить сообщение менеджеру. Попробуйте позже."
                )
            return

        booking_state = rt.USER_BOOKING_FLOW.get(message.from_user.id)
        if booking_state and booking_state.get("stage") == "await_custom_dates":
            custom_dates = (message.text or "").strip()
            if not custom_dates or custom_dates.startswith("/"):
                await message.answer("Введите даты обычным текстом. Пример: с 12.03 по 18.03")
                return
            booking_state["stage"] = "await_delivery_choice"
            booking_state["custom_dates"] = custom_dates
            booking_state["rental_date"] = custom_dates
            await message.answer(
                f"Принято. Ваши даты: {custom_dates}.\n"
                "Нужна ли доставка?",
                reply_markup=rt.delivery_keyboard(),
            )
            return

        if booking_state and booking_state.get("stage") == "await_delivery_map":
            map_link = ""
            if message.location:
                lat = message.location.latitude
                lon = message.location.longitude
                map_link = f"https://maps.google.com/?q={lat},{lon}"
            else:
                map_link = (message.text or "").strip()
                if map_link.lower() == "отправлю ссылкой":
                    await message.answer("Хорошо, отправьте ссылку Google Maps.")
                    return
                if not map_link or map_link.startswith("/"):
                    await message.answer(
                        "Отправьте геолокацию или ссылку Google Maps обычным текстом."
                    )
                    return
            booking_state["delivery_map_link"] = map_link
            booking_state["stage"] = "await_delivery_time"
            await message.answer(
                "Укажите удобное время доставки байка.",
                reply_markup=rt.main_reply_keyboard(message.from_user.id),
            )
            return

        if booking_state and booking_state.get("stage") == "await_delivery_time":
            delivery_time = (message.text or "").strip()
            if not delivery_time or delivery_time.startswith("/"):
                await message.answer("Укажите время доставки обычным текстом.")
                return
            booking_state["delivery_time"] = delivery_time
            booking_state["stage"] = "await_confirm"
            scooter_id = int(booking_state.get("scooter_id", 0))
            scooter = bot_db.get_scooter_by_id(scooter_id) if scooter_id else None
            scooter_name = rt.make_scooter_title(scooter) if scooter else f"ID {scooter_id}"
            await message.answer(
                rt.booking_summary_text(message.from_user, booking_state, scooter_name),
                reply_markup=rt.booking_confirm_keyboard(),
            )
            return

        if booking_state and booking_state.get("stage") == "await_contact":
            user_contact = (message.text or "").strip()
            if not user_contact or user_contact.startswith("/"):
                await message.answer(
                    "Введите контакт обычным текстом: @username или номер телефона."
                )
                return

            scooter_id = int(booking_state.get("scooter_id", 0))
            scooter = bot_db.get_scooter_by_id(scooter_id) if scooter_id else None
            scooter_title = rt.make_scooter_title(scooter) if scooter else f"ID {scooter_id}"
            booking_data: dict[str, str | int] = {
                "user_id": message.from_user.id,
                "user_name": message.from_user.full_name,
                "user_link": rt.telegram_profile_link(message.from_user),
                "user_contact": user_contact,
                "scooter_title": scooter_title,
                "rental_date": str(
                    booking_state.get("rental_date") or booking_state.get("custom_dates") or ""
                ),
                "delivery_type": str(booking_state.get("delivery") or ""),
                "delivery_map_link": str(booking_state.get("delivery_map_link") or ""),
                "delivery_time": str(booking_state.get("delivery_time") or ""),
            }
            booking_id = bot_db.create_booking(booking_data)
            delivered = await rt.notify_admins_about_booking(message, booking_id)
            if delivered > 0:
                await message.answer(
                    "Отлично. Заявка подтверждена и принята в обработку.\n"
                    f"Номер брони: #{booking_id}\n"
                    "Менеджер скоро свяжется с вами.\n\n"
                    "После подтверждения брони менеджером появятся новые функции:\n"
                    "- кнопка SOS\n"
                    "- связь с менеджером",
                    reply_markup=rt.booking_success_keyboard(),
                )
            else:
                await message.answer(
                    "Заявка сохранена, но уведомление администратору не доставлено.\n"
                    f"Номер брони: #{booking_id}\n"
                    "Попросите администратора открыть чат с ботом и нажать /start.\n\n"
                    "Вам уже доступны новые функции в боте:\n"
                    "- кнопка SOS\n"
                    "- связь с менеджером",
                    reply_markup=rt.booking_success_keyboard(),
                )
            rt.USER_BOOKING_FLOW.pop(message.from_user.id, None)
            return

    if not message.from_user:
        return
    if not rt.is_admin(message.from_user.id):
        return
    if message.from_user.id not in rt.ADMIN_FLOW:
        return

    state = rt.ADMIN_FLOW[message.from_user.id]
    stage = state.get("stage")

    if stage == "await_db_wipe_password":
        password_input = (message.text or "").strip()
        expected_password = os.getenv("ADMIN_PASSWORD", "").strip()
        if not expected_password:
            rt.ADMIN_FLOW.pop(message.from_user.id, None)
            await message.answer(
                "ADMIN_PASSWORD не задан в .env. Очистка отменена.",
                reply_markup=rt.admin_main_keyboard(),
            )
            return
        if password_input != expected_password:
            rt.ADMIN_FLOW.pop(message.from_user.id, None)
            await message.answer(
                "Неверный пароль. Очистка отменена.",
                reply_markup=rt.admin_main_keyboard(),
            )
            return

        stats = bot_db.wipe_all_data()
        rt.ADMIN_FLOW.pop(message.from_user.id, None)
        await message.answer(
            "База данных полностью очищена.\n"
            f"- модели: {stats['scooters']}\n"
            f"- брони: {stats['bookings']}\n"
            f"- настройки: {stats['settings']}",
            reply_markup=rt.admin_main_keyboard(),
        )
        return

    if stage == "await_admin_message_text":
        admin_text = (message.text or "").strip()
        if not admin_text or admin_text.startswith("/"):
            await message.answer("Введите сообщение клиенту обычным текстом.")
            return
        booking_id_raw = str(state.get("booking_id", "")).strip()
        if not booking_id_raw.isdigit():
            rt.ADMIN_FLOW.pop(message.from_user.id, None)
            await message.answer("Не удалось определить заявку. Повторите действие.")
            return
        booking = bot_db.get_booking(int(booking_id_raw))
        if not booking:
            rt.ADMIN_FLOW.pop(message.from_user.id, None)
            await message.answer("Заявка не найдена.")
            return

        try:
            await message.bot.send_message(
                chat_id=int(booking["user_id"]),
                text=f"Сообщение от менеджера:\n{admin_text}",
            )
            await message.answer(
                "Сообщение отправлено клиенту.",
                reply_markup=rt.admin_main_keyboard(),
            )
        except Exception:
            await message.answer(
                "Не удалось отправить сообщение клиенту. "
                "Возможно, пользователь еще не запустил бота.",
                reply_markup=rt.admin_main_keyboard(),
            )
        rt.ADMIN_FLOW.pop(message.from_user.id, None)
        return

    if stage == "await_reject_reason_text":
        reason_text = (message.text or "").strip()
        if not reason_text or reason_text.startswith("/"):
            await message.answer("Введите причину обычным текстом.")
            return
        booking_id_raw = str(state.get("booking_id", "")).strip()
        if not booking_id_raw.isdigit():
            rt.ADMIN_FLOW.pop(message.from_user.id, None)
            await message.answer("Не удалось определить заявку. Повторите действие.")
            return
        booking_id = int(booking_id_raw)
        booking = bot_db.get_booking(booking_id)
        if not booking:
            rt.ADMIN_FLOW.pop(message.from_user.id, None)
            await message.answer("Заявка не найдена.")
            return
        if str(booking.get("status")) not in {"pending", "active"}:
            rt.ADMIN_FLOW.pop(message.from_user.id, None)
            await message.answer("Заявка уже обработана.")
            return

        bot_db.set_booking_status(booking_id, "rejected", reason_text)
        rt.ADMIN_FLOW.pop(message.from_user.id, None)
        await message.answer(
            f"Заявка #{booking_id} отклонена. Причина отправлена клиенту.",
            reply_markup=rt.admin_main_keyboard(),
        )
        try:
            await message.bot.send_message(
                chat_id=int(booking["user_id"]),
                text=f"Ваша заявка отклонена. Причина: {reason_text}",
            )
        except Exception:
            pass
        return

    if stage == "await_info_tips_text":
        tips_text = (message.text or "").strip()
        if not tips_text or tips_text.startswith("/"):
            await message.answer("Отправьте текст гайда обычным сообщением.")
            return
        bot_db.set_setting("info_tips_text", tips_text)
        state["stage"] = "await_info_tips_video"
        await message.answer("Теперь отправьте видео для гайда по вождению.")
        return

    if stage == "await_info_tips_video":
        if not message.video:
            await message.answer("Нужно именно видео. Отправьте видеофайл.")
            return
        bot_db.set_setting("info_tips_video_file_id", message.video.file_id)
        rt.ADMIN_FLOW.pop(message.from_user.id, None)
        await message.answer(
            "Гайд по вождению обновлен.",
            reply_markup=rt.admin_main_keyboard(),
        )
        return

    if stage == "await_info_guide_text":
        guide_text = (message.text or "").strip()
        if not guide_text or guide_text.startswith("/"):
            await message.answer("Отправьте путеводитель обычным текстом.")
            return
        bot_db.set_setting("info_guide_text", guide_text)
        state["stage"] = "await_info_guide_document"
        await message.answer("Теперь отправьте документ для путеводителя.")
        return

    if stage == "await_info_guide_document":
        if not message.document:
            await message.answer("Нужен именно документ. Отправьте файл документом.")
            return
        bot_db.set_setting("info_guide_document_file_id", message.document.file_id)
        rt.ADMIN_FLOW.pop(message.from_user.id, None)
        await message.answer(
            "Путеводитель обновлен.",
            reply_markup=rt.admin_main_keyboard(),
        )
        return

    if stage == "await_rules_text":
        rules_text = (message.text or "").strip()
        if not rules_text or rules_text.startswith("/"):
            await message.answer("Отправьте правила обычным текстом.")
            return
        bot_db.set_setting("booking_rules", rules_text)
        rt.ADMIN_FLOW.pop(message.from_user.id, None)
        await message.answer(
            "Правила бронирования обновлены.",
            reply_markup=rt.admin_main_keyboard(),
        )
        return

    if stage == "await_contract_file":
        if not message.document:
            await message.answer("Нужен именно документ. Перешлите файл с образцом договора.")
            return
        bot_db.set_setting("contract_file_id", message.document.file_id)
        contract_text = state.get("contract_text", "").strip()
        if contract_text:
            bot_db.set_setting("contract_caption", contract_text)
        rt.ADMIN_FLOW.pop(message.from_user.id, None)
        await message.answer(
            "Образец договора обновлен.",
            reply_markup=rt.admin_main_keyboard(),
        )
        return

    if stage == "await_contract_text":
        contract_text = (message.text or "").strip()
        if not contract_text or contract_text.startswith("/"):
            await message.answer("Отправьте текст обычным сообщением.")
            return
        state["contract_text"] = contract_text
        state["stage"] = "await_contract_file"
        await message.answer("Теперь отправьте файл образца договора (документом).")
        return

    if stage == "await_office_link":
        office_link = (message.text or "").strip()
        if not office_link or office_link.startswith("/"):
            await message.answer("Отправьте ссылку обычным текстом.")
            return
        bot_db.set_setting("office_link", office_link)
        rt.ADMIN_FLOW.pop(message.from_user.id, None)
        await message.answer(
            "Ссылка офиса обновлена.",
            reply_markup=rt.admin_main_keyboard(),
        )
        return

    if stage == "await_title":
        title = (message.text or "").strip()
        if not title or title.startswith("/"):
            await message.answer("Нужно текстовое название кнопки. Введите обычный текст.")
            return
        state["title"] = title[:60]
        state["stage"] = "await_forward"
        await message.answer(
            "Отлично. Теперь перешлите сообщение модели (текст или фото с подписью)."
        )
        return

    if stage != "await_forward":
        return

    if (message.text or "").startswith("/"):
        return

    category_code = state["category"]
    title = state.get("title", "").strip() or "Модель"

    model: dict[str, str | int] = {
        "category": category_code,
        "msg_type": "text",
        "text": "",
        "caption": "",
        "photo_file_id": "",
        "title": title,
    }

    if message.photo:
        biggest = message.photo[-1]
        model["msg_type"] = "photo"
        model["photo_file_id"] = biggest.file_id
        model["caption"] = message.caption or ""
    else:
        model["msg_type"] = "text"
        model["text"] = message.text or message.caption or ""
        if not str(model["text"]).strip():
            await message.answer("Не удалось извлечь контент. Перешли текст или фото с подписью.")
            return

    model_id = bot_db.add_scooter(model)
    rt.ADMIN_FLOW.pop(message.from_user.id, None)
    await message.answer(
        "Модель добавлена в каталог.\n"
        f"ID: {model_id}\n"
        f"Кнопка: {title}\n"
        f"Категория: {rt.CATEGORIES[category_code]}",
        reply_markup=rt.admin_main_keyboard(),
    )
