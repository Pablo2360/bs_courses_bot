# subscription.py

"""
Здесь мы храним тех, кто уже оплатил.
Простейшая реализация — в памяти, с помощью множества (set).
При перезапуске бота память сбросится, но до этого момента
юзер не будет видеть экран оплаты второй раз.
"""

SUBSCRIBERS = set()

def has_active_subscription(user_id: int) -> bool:
    """
    Проверяет, есть ли пользователь в списке тех, кто уже оплатил.
    """
    return user_id in SUBSCRIBERS

def add_subscription(user_id: int):
    """
    Добавляет пользователя в список оплаченных.
    """
    SUBSCRIBERS.add(user_id)
