from aiogram import Router
from . import panel,rating,watermark,payment_details,replace_photo,products,moderation,product_number,orders
router=Router()
for r in (panel,rating,watermark,payment_details,replace_photo,products,moderation,product_number,orders): router.include_router(r.router)
