from db.logs import is_logging_enabled, add_log


async def log_event(
    event: str,
    message: str,
    user_id: int | None = None,
    admin_id: int | None = None,
):
    """Записывает событие в лог, если логирование включено."""

    if not await is_logging_enabled():
        return

    await add_log(
        event=event,
        message=message,
        user_id=user_id,
        admin_id=admin_id,
    )