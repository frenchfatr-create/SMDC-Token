from db.logs import write_log


async def log_event(
    bot,
    user_id: int,
    event: str,
    details: str = "",
):
    """
    Универсальная запись события в лог.

    Логирование включается/выключается через db.logs.
    Если логи выключены — ничего не происходит.
    """

    await write_log(
        bot=bot,
        user_id=user_id,
        event=event,
        details=details,
    )