# subscription.py

"""Хранение оплаченных пользователей."""

import json
import os

PAID_USERS_FILE = "paid_users.json"


def _load() -> set:
    if os.path.exists(PAID_USERS_FILE):
        try:
            with open(PAID_USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception:
            pass
    return set()


def _save(users: set) -> None:
    try:
        with open(PAID_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


SUBSCRIBERS = _load()


def has_active_subscription(user_id: int) -> bool:
    """Проверяет, есть ли пользователь в списке тех, кто уже оплатил."""
    return user_id in SUBSCRIBERS


def add_subscription(user_id: int) -> None:
    """Добавляет пользователя в список оплаченных и сохраняет его."""
    SUBSCRIBERS.add(user_id)
    _save(SUBSCRIBERS)