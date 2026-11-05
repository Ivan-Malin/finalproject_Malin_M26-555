"""Содержит реализацию классов."""

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Self

from valutatrade_hub.core.utils import (
    assert_non_negative,
    strict_arg_types,
)


class User:
    """Пользователь системы."""

    __SALT_LEN = 16  # TOD - вынести в файл констант
    __PASSWORD_MIN_LEN = 4
    # Теперь формат включает явное указание UTC (+00:00)
    __DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

    @strict_arg_types
    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        """Инициализирует пользователя.

        Args:
            user_id (int): уникальный идентификатор пользователя.
            username (str): имя пользователя.
            hashed_password (str): пароль в зашифрованном виде.
            salt (str): уникальная соль для пользователя.
            registration_date (datetime): дата регистрации пользователя.

        """
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt

        # Приводим всё к UTC при инициализации для единообразия хранения
        if registration_date.tzinfo is None:
            # Если TZ не указан, считаем, что это уже UTC
            self._registration_date = registration_date.replace(tzinfo=UTC)
        else:
            self._registration_date = registration_date.astimezone(UTC)

    @strict_arg_types
    @staticmethod
    def generate_hash(password: str, salt: str) -> str:
        """Генерирует хеш по паролю и соли."""
        return hashlib.sha256((password + salt).encode()).hexdigest()

    @strict_arg_types
    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль на совпадение с зарегестрированным."""
        return User.generate_hash(password, self._salt) == self._hashed_password

    @property
    def password_info(self) -> tuple[str, str]:
        """Возвращает пару (хеш пароля, соль)."""
        return self._hashed_password, self._salt

    # Не добавлен сеттер через проперти, т.к.
    # сеттер имеет 1 формат, а геттер другой, что нарушает
    # красоту синтаксического сахара питона и может
    # привести к ошибкам пользователя
    @strict_arg_types
    def change_password(self, new_password: str) -> None:
        """Меняет пароль пользователя вместе с солью."""
        if len(new_password) < User.__PASSWORD_MIN_LEN:
            msg = f"Пароль должен быть длиннее {User.__PASSWORD_MIN_LEN} символов."
            raise ValueError(msg)

        self._salt = secrets.token_hex(User.__SALT_LEN)
        self._hashed_password = User.generate_hash(new_password, self._salt)

    @property
    def user_id(self) -> int:
        """Геттер для приватного поля."""
        return self._user_id

    @property
    def username(self) -> int:
        """Геттер для приватного поля."""
        return self._username

    @username.setter
    @strict_arg_types
    def username(self, name: str) -> None:
        """Устанавливает имя, если оно не пустое."""
        if not name:
            msg = "Имя не может быть пустым."
            raise ValueError(msg)

        self._username = str(name)

    @property
    def registration_date(self) -> datetime:
        """Геттер для приватного поля."""
        # datetime является имутабельным, поэтому можем так передавать
        return self._registration_date

    def get_user_info(self) -> dict:
        """Выводит информацию о пользователе (без пароля).

        Формат:
        {
            "user_id": int,
            "username": str,
            "registration_date": str в UTC,
        }

        Returns:
            dict: информация.

        """
        return {
            "user_id": self._user_id,
            "username": self._username,
            # Используем тот же формат с явным UTC
            "registration_date": self._registration_date.strftime(
                User.__DATE_TIME_FORMAT,
            ),
        }

    def to_dict(self) -> dict:
        """Возвращает объект в виде словаря для сериализации."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            # Сохраняем строку вида "2025-01-01T12:00:00+00:00"
            "registration_date": self._registration_date.strftime(
                User.__DATE_TIME_FORMAT,
            ),
            "hashed_password": self._hashed_password,
            "salt": self._salt,
        }

    @classmethod
    @strict_arg_types
    def from_dict(cls, user_dict: dict) -> Self:
        """Инициализирует объект на основе словаря, полученного из json.

        Args:
            user_dict (dict): словарь формата
            {
                "user_id": 1,
                "username": "alice",
                "hashed_password": "3e2a19...",
                "salt": "x5T9!",
                "registration_date": "2025-10-09T12:00:00"
            }

        Raises:
            TypeError: в случае если аргумент не словарь.
            ValueError: в случае некорректного словаря.

        Returns:
            Self: объект пользователя.

        """
        try:
            return cls(
                user_id=int(user_dict["user_id"]),
                username=str(user_dict["username"]),
                hashed_password=str(user_dict["hashed_password"]),
                salt=user_dict["salt"],
                registration_date=datetime.strptime(
                    user_dict["registration_date"],
                    User.__DATE_TIME_FORMAT,
                ),
            )
        except (KeyError, ValueError) as e:
            msg = f"user_dict имеет некорректный формат. {e}"
            raise ValueError(msg) from e


class Wallet:
    """Кошелёк пользователя для одной конкретной валюты."""

    @strict_arg_types
    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        """Инициализирует кошелёк.

        Args:
            currency_code (str): код валюты (например, "USD", "BTC")
            balance (float): не отрицательный баланс в данной валюте.
                По умолчанию 0.0

        """
        assert_non_negative(balance, "balance")

        self._currency_code = currency_code
        self._balance = balance

    # Сеттер к нему не сделан, т.к. он не имеет смысла в контексте задачи
    @property
    def currency_code(self) -> None:
        """Геттер для приватного поля."""
        return self._currency_code

    @property
    def balance(self) -> None:
        """Геттер для приватного поля."""
        return self._balance

    @balance.setter
    @strict_arg_types
    def balance(self, balance: float) -> None:
        """Сеттер для приватного поля.

        Args:
            balance (float): баланс. Должен быть неотрицательным.

        """
        assert_non_negative(balance, "balance")

        self._balance = balance

    @strict_arg_types
    def deposit(self, amount: float) -> None:
        """Пополнение баланса.

        Args:
           amount (float): сумма пополнения.
               Должна быть неотрицательной.

        """
        assert_non_negative(amount, "amount")

        self.balance += amount

    @strict_arg_types
    def withdraw(self, amount: float) -> None:
        """Снятие средств.

        Args:
            amount (float): сумма снятия.
                Должна быть неотрицательной.

        """
        assert_non_negative(amount, "amount")

        self.balance -= amount

    def get_balance_info(self) -> dict:
        """Выводит информацию о текущем балансе.

        Формат:
        {
            "currency_code": int,
            "balance": int
        }

        Returns:
            dict: информация.

        """
        return {"currency_code": self._currency_code, "balance": self.balance}

    # Самый простой способ для сериализации json
    def to_dict(self) -> dict:
        """Возвращает объект в виде словаря для сериализации.

        Returns:
            dict: словарь для сериализации

        """
        return {"currency_code": self._currency_code, "balance": self.balance}

    @classmethod
    @strict_arg_types
    def from_dict(cls, wallet_dict: dict) -> Self:
        """Инициализирует объект на основе словаря, полученного из json.

        Args:
            wallet_dict (dict): словарь формата
            {
                "currency_code": "UTC",
                "balance": 0.0
            }

        Raises:
            TypeError: в случае если аргумент не словарь.
            ValueError: в случае некорректного словаря.

        Returns:
            Self: User

        """
        try:
            return cls(
                currency_code=wallet_dict["currency_code"],
                balance=wallet_dict["balance"],
            )
        except (KeyError, ValueError) as e:
            msg = f"wallet_dict имеет некорректный формат. {e}"
            raise ValueError(msg) from e
