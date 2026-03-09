def booking_summary_text(
    *,
    user_full_name: str,
    user_link: str,
    state: dict[str, str | int],
    scooter_title: str,
) -> str:
    rental_date = str(state.get("rental_date") or state.get("custom_dates") or "не указана")
    delivery = str(state.get("delivery") or "не указано")

    lines = [
        "Проверьте данные бронирования:",
        f"Имя: {user_full_name}",
        f"Ссылка на Telegram: {user_link}",
        f"Байк: {scooter_title}",
        f"Дата аренды: {rental_date}",
    ]

    if delivery == "yes":
        lines.append("Доставка: да")
        lines.append(f"Куда доставлять: {state.get('delivery_map_link', '')}")
        lines.append(f"Время доставки: {state.get('delivery_time', '')}")
    elif delivery == "office":
        lines.append("Доставка: заберу сам в офисе (центр города)")
        office_link = str(state.get("office_link", "")).strip()
        if office_link:
            lines.append(f"Наш офис находится здесь: {office_link}")
    else:
        lines.append("Доставка: не указано")

    return "\n".join(lines)


def admin_booking_text(booking: dict[str, str | int], resolved_user_link: str) -> str:
    user_contact = str(booking.get("user_contact", "")).strip()
    user_link_display = "не указана"
    if resolved_user_link.startswith("https://t.me/"):
        username = resolved_user_link.rsplit("/", 1)[-1].strip()
        if username:
            user_link_display = f"{resolved_user_link} или @{username}"
        else:
            user_link_display = resolved_user_link

    lines = [
        "Новая заявка",
        f"Номер брони: #{booking.get('id', '')}",
        "",
        f"Имя: {booking.get('user_name', '')}",
        f"Telegram ID: {booking.get('user_id', '')}",
        f"Ссылка на Telegram: {user_link_display}",
        f"Контакт клиента: {user_contact or 'не указан'}",
        f"Байк: {booking.get('scooter_title', '')}",
        f"Дата аренды: {booking.get('rental_date', '')}",
    ]
    delivery_type = str(booking.get("delivery_type", ""))
    if delivery_type == "office":
        lines.append("Доставка: заберу сам в офисе (центр города)")
    else:
        lines.append("Доставка: да, нужна")
        lines.append(f"Куда доставить: {booking.get('delivery_map_link', '')}")
        lines.append(f"К какому времени: {booking.get('delivery_time', '')}")
    return "\n".join(lines)


def user_bookings_text(bookings: list[dict[str, str | int]]) -> str:
    status_map = {
        "pending": "ожидает подтверждения",
        "active": "активна",
        "rejected": "отклонена",
        "finished": "отъездила",
    }
    lines = ["Ваши заявки:"]
    for booking in bookings:
        status = status_map.get(str(booking.get("status", "")), str(booking.get("status", "")))
        lines.append(
            f"- #{booking.get('id')} | {status} | {booking.get('scooter_title')} | {booking.get('rental_date')}"
        )
    return "\n".join(lines)
