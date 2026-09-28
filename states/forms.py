from aiogram.fsm.state import State,StatesGroup
class SellForm(StatesGroup):
    kind=State(); game=State(); description=State(); media=State(); contact=State(); payment=State()
    price_rub=State(); price_stars=State(); preview=State()
class BuySearch(StatesGroup): query=State()
class AdminRating(StatesGroup): user_id=State(); rating=State()
class AdminWatermark(StatesGroup): photo=State()
class AdminPaymentDetails(StatesGroup): value=State()
class AdminReplacePhoto(StatesGroup): ad_id=State()
class PriceEdit(StatesGroup): new_price=State()
class ProductNumberEdit(StatesGroup): number=State()
class AdminBlock(StatesGroup): user_id=State(); reason=State()
class AdminProductManage(StatesGroup): product_number=State()
class AdminUserSearch(StatesGroup): user_id=State()
class AdminLogs(StatesGroup): pass
class ComplaintState(StatesGroup): reason=State()
class OrderFlow(StatesGroup): quantity=State(); payment=State(); receipt=State()
