from aiogram.types import CallbackQuery, Message

from bot_app import db as bot_db
from bot_app import runtime as rt


def _status_title(status_code: str) -> str | None:
    return {
        "pending": "в ожидании",
        "active": "активна",
        "rejected": "отклонена",
        "finished": "отъездила",
    }.get(status_code)


def _availability_stats_text() -> str:
    scooters = bot_db.list_scooters()
    total = len(scooters)
    available = sum(1 for scooter in scooters if bool(int(scooter.get("is_available", 1))))
    return f"Доступно {available} из {total}"


def _booking_actions_markup(booking: dict[str, str | int], status_code: str):
    if status_code not in {"pending", "active"}:
        return None
    user_link = rt.resolve_user_link(
        raw_user_link=str(booking.get("user_link", "")),
        raw_user_contact=str(booking.get("user_contact", "")),
    )
    return rt.admin_booking_actions_keyboard(
        int(booking["id"]),
        user_link,
        status=str(booking.get("status", status_code)),
    )


async def _send_booking_list(callback: CallbackQuery, bookings: list[dict[str, str | int]], status_code: str) -> None:
    for booking in bookings:
        await callback.message.answer(
            rt.admin_booking_text(booking),
            reply_markup=_booking_actions_markup(booking, status_code),
        )


async def on_admin_button(message: Message) -> None:
    if not message.from_user or not rt.is_admin(message.from_user.id):
        await message.answer("Команда доступна только администратору.")
        return
    await message.answer(
        "Панель администратора. Выберите действие:",
        reply_markup=rt.admin_main_keyboard(),
    )


async def on_bookings_button(message: Message) -> None:
    if not message.from_user or not rt.is_admin(message.from_user.id):
        await message.answer("Команда доступна только администратору.")
        return
    await message.answer(
        "Меню управления бронями:",
        reply_markup=rt.admin_booking_status_menu_keyboard(),
    )


async def on_availability_button(message: Message) -> None:
    if not message.from_user or not rt.is_admin(message.from_user.id):
        await message.answer("Команда доступна только администратору.")
        return
    await message.answer(
        "Управление доступностью байков:\n"
        "Нажимайте на модели, чтобы включать/выключать их для клиентов.\n"
        f"{_availability_stats_text()}",
        reply_markup=rt.admin_availability_keyboard(),
    )


async def on_admin(message: Message) -> None:
    await on_admin_button(message)


async def on_admin_add_clicked(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return

    assert callback.data is not None
    action = callback.data.split(":", 1)[1]
    if action not in rt.CATEGORIES:
        await callback.answer("Неизвестная категория", show_alert=True)
        return

    rt.ADMIN_FLOW[callback.from_user.id] = {"stage": "await_title", "category": action}
    await callback.message.answer(
        "Введите название для кнопки этой модели.\n"
        "Пример: Honda PCX 160 - 350k/день"
    )
    await callback.answer()


async def on_admin_delete_clicked(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return

    assert callback.data is not None
    action = callback.data.split(":", 1)[1]

    if action == "back":
        await callback.message.answer(
            "Панель администратора. Выберите действие:",
            reply_markup=rt.admin_main_keyboard(),
        )
        await callback.answer()
        return

    if action == "list":
        all_scooters = bot_db.list_scooters()
        if not all_scooters:
            await callback.message.answer("Список пуст. Удалять нечего.")
            await callback.answer()
            return
        await callback.message.answer(
            "Выбери модель для удаления:",
            reply_markup=rt.admin_delete_keyboard(),
        )
        await callback.answer()
        return

    if not action.isdigit():
        await callback.answer("Неверный ID", show_alert=True)
        return
    scooter_id = int(action)
    scooter = bot_db.get_scooter_by_id(scooter_id)
    if not scooter:
        await callback.answer("Модель не найдена", show_alert=True)
        return

    bot_db.delete_scooter(scooter_id)
    await callback.message.answer(
        f"Удалено: {rt.make_scooter_title(scooter)}",
        reply_markup=rt.admin_main_keyboard(),
    )
    await callback.answer()


async def on_admin_office_set(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    rt.ADMIN_FLOW[callback.from_user.id] = {"stage": "await_office_link"}
    current_link = bot_db.get_setting("office_link")
    if current_link:
        await callback.message.answer(
            "Отправьте новую ссылку на офис в Google Maps.\n"
            f"Текущая ссылка: {current_link}"
        )
    else:
        await callback.message.answer("Отправьте ссылку на офис в Google Maps.")
    await callback.answer()


async def on_admin_rules_set(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    rt.ADMIN_FLOW[callback.from_user.id] = {"stage": "await_rules_text"}
    current_rules = bot_db.get_setting("booking_rules").strip()
    if current_rules:
        await callback.message.answer(
            "Отправьте новый текст правил бронирования.\n"
            f"Текущие правила:\n{current_rules}"
        )
    else:
        await callback.message.answer("Отправьте текст правил бронирования.")
    await callback.answer()


async def on_admin_info_set(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    assert callback.data is not None
    action = callback.data.split(":", 1)[1]
    if action == "set_tips":
        rt.ADMIN_FLOW[callback.from_user.id] = {"stage": "await_info_tips_text"}
        current_text = bot_db.get_setting("info_tips_text").strip()
        current_video = bot_db.get_setting("info_tips_video_file_id").strip()
        if current_text:
            await callback.message.answer(
                "Отправьте новый текст гайда по вождению.\n"
                f"Текущий текст:\n{current_text}\n\n"
                f"Видео: {'добавлено' if current_video else 'не добавлено'}"
            )
        else:
            await callback.message.answer("Отправьте текст гайда по вождению.")
        await callback.answer()
        return
    if action == "set_guide":
        rt.ADMIN_FLOW[callback.from_user.id] = {"stage": "await_info_guide_text"}
        current_text = bot_db.get_setting("info_guide_text").strip()
        current_document = bot_db.get_setting("info_guide_document_file_id").strip()
        if current_text:
            await callback.message.answer(
                "Отправьте новый текст путеводителя.\n"
                f"Текущий текст:\n{current_text}\n\n"
                f"Документ: {'добавлен' if current_document else 'не добавлен'}"
            )
        else:
            await callback.message.answer("Отправьте текст путеводителя.")
        await callback.answer()
        return
    await callback.answer("Неизвестная команда", show_alert=True)


async def on_admin_contract_set(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    rt.ADMIN_FLOW[callback.from_user.id] = {"stage": "await_contract_text"}
    await callback.message.answer(
        "Сначала отправьте текст к образцу договора."
    )
    await callback.answer()


async def on_admin_db_wipe_request(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    await callback.message.answer(
        "Внимание: это удалит ВСЕ данные (модели, брони, настройки).\n"
        "Подтвердите действие:",
        reply_markup=rt.admin_wipe_confirm_keyboard(),
    )
    await callback.answer()


async def on_admin_availability(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    assert callback.data is not None
    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.answer("Некорректная команда", show_alert=True)
        return
    action = parts[1]

    if action == "open":
        await callback.message.answer(
            "Управление доступностью байков:\n"
            "Нажимайте на модели, чтобы включать/выключать их для клиентов.\n"
            f"{_availability_stats_text()}",
            reply_markup=rt.admin_availability_keyboard(),
        )
        await callback.answer()
        return

    if action == "done":
        await callback.message.answer(
            "Панель администратора. Выберите действие:",
            reply_markup=rt.admin_main_keyboard(),
        )
        await callback.answer()
        return

    if action == "toggle":
        if len(parts) != 3 or not parts[2].isdigit():
            await callback.answer("Некорректный ID", show_alert=True)
            return
        scooter_id = int(parts[2])
        new_state = bot_db.toggle_scooter_availability(scooter_id)
        if new_state is None:
            await callback.answer("Модель не найдена", show_alert=True)
            return
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=rt.admin_availability_keyboard())
        await callback.answer(f"Доступность обновлена. {_availability_stats_text()}")
        return

    await callback.answer("Неизвестная команда", show_alert=True)


async def on_admin_booking_wipe(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    assert callback.data is not None
    action = callback.data.split(":", 1)[1]
    if action == "request":
        await callback.message.answer(
            "Удалить вообще все брони?\n"
            "Это действие удалит все записи из таблицы бронирований.",
            reply_markup=rt.admin_booking_wipe_confirm_keyboard(),
        )
        await callback.answer()
        return
    if action == "no":
        await callback.message.answer("Удаление всех броней отменено.")
        await callback.answer()
        return
    if action != "yes":
        await callback.answer("Неизвестная команда", show_alert=True)
        return

    deleted = bot_db.delete_all_bookings()
    await callback.message.answer(
        f"Все брони удалены. Удалено записей: {deleted}",
        reply_markup=rt.admin_main_keyboard(),
    )
    await callback.answer()


async def on_admin_db_wipe_confirm(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    assert callback.data is not None
    action = callback.data.split(":", 1)[1]
    if action == "no":
        await callback.message.answer("Очистка базы отменена.")
        await callback.answer()
        return
    if action != "yes":
        await callback.answer("Неизвестная команда", show_alert=True)
        return

    rt.ADMIN_FLOW[callback.from_user.id] = {"stage": "await_db_wipe_password"}
    await callback.message.answer("Введите пароль администратора для очистки базы:")
    await callback.answer()


async def on_admin_back_to_start(callback: CallbackQuery) -> None:
    await rt.show_main_menu(callback.message)
    await callback.answer()


async def on_admin_booking_action(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    assert callback.data is not None
    parts = callback.data.split(":")
    if len(parts) == 2 and parts[1] == "menu":
        await callback.message.answer(
            "Меню управления бронями:",
            reply_markup=rt.admin_booking_status_menu_keyboard(),
        )
        await callback.answer()
        return

    if len(parts) != 3 or not parts[2].isdigit():
        await callback.answer("Некорректная команда", show_alert=True)
        return
    action = parts[1]
    booking_id = int(parts[2])

    booking = bot_db.get_booking(booking_id)
    if not booking:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if action == "confirm":
        if str(booking.get("status")) != "pending":
            await callback.answer("Заявка уже обработана", show_alert=True)
            return
        bot_db.set_booking_status(booking_id, "active")
        await callback.message.answer(f"Заявка #{booking_id} подтверждена. Статус: активна.")
        try:
            await callback.message.bot.send_message(
                chat_id=int(booking["user_id"]),
                text=(
                    f"Бронь #{booking_id} подтверждена. Статус: активна.\n"
                    "Нажмите кнопку 'Меню' — там появится дополнительная кнопка SOS."
                ),
                reply_markup=rt.main_reply_keyboard(int(booking["user_id"])),
            )
        except Exception:
            pass
        await callback.answer()
        return

    if action == "finish":
        if str(booking.get("status")) != "active":
            await callback.answer("Заявка уже обработана", show_alert=True)
            return
        bot_db.set_booking_status(booking_id, "finished")
        await callback.message.answer(f"Заявка #{booking_id} отмечена как отъездила.")
        try:
            await callback.message.bot.send_message(
                chat_id=int(booking["user_id"]),
                text=f"Бронь #{booking_id} завершена. Спасибо, что выбрали нас.",
            )
        except Exception:
            pass
        await callback.answer()
        return

    if action == "message":
        rt.ADMIN_FLOW[callback.from_user.id] = {
            "stage": "await_admin_message_text",
            "booking_id": str(booking_id),
        }
        await callback.message.answer(
            f"Напишите сообщение клиенту по заявке #{booking_id}. "
            "Бот отправит его клиенту от имени менеджера."
        )
        await callback.answer()
        return

    if action == "reject":
        if str(booking.get("status")) not in {"pending", "active"}:
            await callback.answer("Заявка уже обработана", show_alert=True)
            return
        await callback.message.answer(
            f"Выберите причину отклонения заявки #{booking_id}:",
            reply_markup=rt.admin_reject_reasons_keyboard(booking_id),
        )
        await callback.answer()
        return

    await callback.answer("Неизвестное действие", show_alert=True)


async def on_admin_booking_reject_reason(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    assert callback.data is not None
    parts = callback.data.split(":")
    if len(parts) != 3 or not parts[1].isdigit():
        await callback.answer("Некорректная команда", show_alert=True)
        return
    booking_id = int(parts[1])
    reason_code = parts[2]
    booking = bot_db.get_booking(booking_id)
    if not booking:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    if str(booking.get("status")) not in {"pending", "active"}:
        await callback.answer("Заявка уже обработана", show_alert=True)
        return

    reasons = {
        "no_stock": "Нет такого байка в наличии",
        "invalid_data": "Неверные данные",
        "other": "Другая причина",
    }
    reason = reasons.get(reason_code)
    if not reason:
        await callback.answer("Неизвестная причина", show_alert=True)
        return

    if reason_code == "other":
        rt.ADMIN_FLOW[callback.from_user.id] = {
            "stage": "await_reject_reason_text",
            "booking_id": str(booking_id),
        }
        await callback.message.answer(
            f"Напишите причину отклонения для заявки #{booking_id}. "
            "Этот текст будет отправлен клиенту."
        )
        await callback.answer()
        return

    bot_db.set_booking_status(booking_id, "rejected", reason)
    await callback.message.answer(f"Заявка #{booking_id} отклонена. Причина: {reason}")
    try:
        await callback.message.bot.send_message(
            chat_id=int(booking["user_id"]),
            text=f"Ваша заявка отклонена. Причина: {reason}",
        )
    except Exception:
        pass
    await callback.answer()


async def on_admin_booking_state(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    assert callback.data is not None
    state_code = callback.data.split(":", 1)[1]
    if state_code == "menu":
        await callback.message.answer(
            "Меню управления бронями:",
            reply_markup=rt.admin_booking_status_menu_keyboard(),
        )
        await callback.answer()
        return
    if state_code == "back":
        await callback.message.answer(
            "Панель администратора. Выберите действие:",
            reply_markup=rt.admin_main_keyboard(),
        )
        await callback.answer()
        return
    if state_code == "cleanup":
        deleted = bot_db.delete_bookings_by_statuses(["rejected", "finished"])
        await callback.message.answer(
            f"Удалено броней: {deleted}\n"
            "Очищены статусы: отклонена и отъездила."
        )
        await callback.answer()
        return
    if state_code in {"pending", "active", "finished"}:
        bookings = bot_db.list_bookings_by_status(state_code)
        status_title = _status_title(state_code) or state_code
        total_count = len(bookings)
        if total_count == 0:
            await callback.message.answer(f"Броней со статусом '{status_title}' нет.")
            await callback.answer()
            return
        if total_count > 5:
            await callback.message.answer(
                "Выберите режим отображения:",
                reply_markup=rt.admin_booking_view_mode_keyboard(state_code, total_count),
            )
            await callback.answer()
            return

        await callback.message.answer(
            f"Статус '{status_title}', все ({total_count}):"
        )
        await _send_booking_list(callback, bookings, state_code)
        await callback.answer()
        return

    status_title = _status_title(state_code)
    if not status_title:
        await callback.answer("Неизвестный статус", show_alert=True)
        return

    bookings = bot_db.list_bookings_by_status(state_code)
    if not bookings:
        await callback.message.answer(f"Броней со статусом '{status_title}' нет.")
        await callback.answer()
        return

    await callback.message.answer(f"Брони со статусом '{status_title}': {len(bookings)}")
    await _send_booking_list(callback, bookings, state_code)
    await callback.answer()


async def on_admin_booking_view(callback: CallbackQuery) -> None:
    if not callback.from_user or not rt.is_admin(callback.from_user.id):
        await callback.answer("Только для администратора", show_alert=True)
        return
    assert callback.data is not None
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректная команда", show_alert=True)
        return
    status_code, view_mode = parts[1], parts[2]
    if status_code not in {"pending", "active", "finished"}:
        await callback.answer("Неизвестный статус", show_alert=True)
        return
    limit = 5 if view_mode == "last5" else None
    if view_mode not in {"last5", "all"}:
        await callback.answer("Неизвестный режим", show_alert=True)
        return

    status_title = _status_title(status_code) or status_code
    bookings = bot_db.list_bookings_by_status(status_code, limit=limit)
    if not bookings:
        await callback.message.answer(f"Броней со статусом '{status_title}' нет.")
        await callback.answer()
        return

    prefix = "последние 5" if limit == 5 else "все"
    await callback.message.answer(
        f"Статус '{status_title}', {prefix}: {len(bookings)}"
    )
    await _send_booking_list(callback, bookings, status_code)
    await callback.answer()
