from decimal import Decimal
RUB_PACKS=[(50,7500),(100,15000),(150,22500),(200,30000),(250,37500),(300,45000),(350,52500),(400,60000),(450,67500),(500,75000)]
STAR_PACKS=[(25,7500),(50,15000),(75,22500),(100,30000),(175,37500),(250,45000)]
BOOST_PACKS=[(5,30),(10,80),(15,130),(20,180)]
def rub_tokens(amount:int)->int:
    if amount<500: raise ValueError("Минимум 500 ₽ для опта")
    return amount*150
def star_tokens(stars:int)->int:
    if stars<250:
        v=dict(STAR_PACKS).get(stars)
        if v is None: raise ValueError("Для этого количества Stars нет тарифа")
        return v
    if (stars-250)%25: raise ValueError("Количество Stars после 250 должно быть кратно 25")
    return 45000+((stars-250)//25)*7500
def silver_total(quantity:int)->Decimal:
    if quantity<10: raise ValueError("Минимальный заказ — 10 Silver Boxes")
    return Decimal(quantity)*Decimal("1.5")
