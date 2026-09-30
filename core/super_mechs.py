from decimal import Decimal

# Эти тарифы оставлены для разделов магазина, которые не относятся к выставлению
# пользовательского товара. Оптовой механики в продаже пользовательских токенов нет.
RUB_PACKS = [(50, 7500)]
STAR_PACKS = [(25, 7500)]
BOOST_PACKS = [(5, 30), (10, 80), (15, 130), (20, 180)]


def rub_tokens(amount: int) -> int:
    if amount < 50:
        raise ValueError("Минимум 50 ₽")
    return min(int(amount), 7500)


def star_tokens(stars: int) -> int:
    if stars <= 0:
        raise ValueError("Количество Stars должно быть положительным")
    return min(stars, 7500)


def silver_total(quantity: int) -> Decimal:
    if quantity < 10:
        raise ValueError("Минимальный заказ — 10 Silver Boxes")
    return Decimal(quantity) * Decimal("1.5")
