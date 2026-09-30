from aiogram import Router

from . import (
    panel,
    rating,
    watermark,
    payment_details,
    replace_photo,
    products,
    moderation,
    product_number,
    orders,
    complaints,
    stats,
    user_search,
    logs,
)

router = Router()


for module in (
    panel,
    rating,
    watermark,
    payment_details,
    replace_photo,
    products,
    moderation,
    product_number,
    orders,
    complaints,
    stats,
    user_search,
    logs,
):
    router.include_router(module.router)