from decimal import Decimal

# Тариф токенов за рубли:
# 50 ₽ = 7 500 токенов
# 1 ₽ = 150 токенов
RUB_PACKS = [(50, 7500)]

# Тарифы Stars
STAR_PACKS = [(25, 7500)]

BOOST_PACKS = [
    (5, 30),
    (10, 80),
    (15, 130),
    (20, 180),
]


def rub_tokens(amount: int) -> int:
    """
    Расчёт количества токенов за рубли.

    Минимум: 50 ₽
    Курс: 1 ₽ = 150 токенов

    Примеры:
    50 ₽  -> 7 500 токенов
    100 ₽ -> 15 000 токенов
    500 ₽ -> 75 000 токенов
    """
    if amount < 50:
        raise ValueError("Минимальная сумма — 50 ₽")

    return int(amount) * 150


def star_tokens(stars: int) -> int:
    if stars <= 0:
        raise ValueError("Количество Stars должно быть положительным")

    return min(stars, 7500)


def silver_total(quantity: int) -> Decimal:
    if quantity < 10:
        raise ValueError("Минимальный заказ — 10 Silver Boxes")

    return Decimal(quantity) * Decimal("1.5")