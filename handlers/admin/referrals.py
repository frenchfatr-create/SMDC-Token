from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_IDS
from db.users import get_all_referrals

router = Router()


@router.message(Command("referrals"))
async def referrals(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    rows = await get_all_referrals()

    if not rows:
        await message.answer("👥 Рефералов пока нет.")
        return

    out = ["👥 <b>Кто кого пригласил</b>"]

    for row in rows:
        referrer = (
            f"@{row['referrer_username']}"
            if row["referrer_username"]
            else str(row["referrer_id"])
        )
        invited = (
            f"@{row['referred_username']}"
            if row["referred_username"]
            else str(row["referred_id"])
        )

        out.append(
            f"\n👤 {referrer} (<code>{row['referrer_id']}</code>)"
            f" → {invited} (<code>{row['referred_id']}</code>)"
        )

    await message.answer("\n".join(out)[:3900])
