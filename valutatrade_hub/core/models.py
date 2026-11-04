"""Содержит реализацию классов."""

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Self

from valutatrade_hub.core.utils import assert_var_isinstance_of_type


class User:
    """Пользователь системы."""

    __SALT_LEN = 16  # TOD - вынести в файл констант
    __PASSWORD_MIN_LEN = 4
    __DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
    __TIMEZONE = UTC

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
        assert_var_isinstance_of_type(user_id, int)
        assert_var_isinstance_of_type(username, str)
        assert_var_isinstance_of_type(hashed_password, str)
        assert_var_isinstance_of_type(salt, str)
        assert_var_isinstance_of_type(registration_date, datetime)

        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date.astimezone(tz=User.__TIMEZONE)

    @staticmethod
    def generate_hash(password: str, salt: str) -> str:
        """Генерирует хеш по паролю и соли."""
        return hashlib.sha256((password + salt).encode()).hexdigest()

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
    def change_password(self, new_password: str) -> None:
        """Меняет пароль пользователя вместе с солью."""
        if not isinstance(new_password, str):
            msg = f"new_password должен быть str, а не {type(new_password).__name__}."
            raise TypeError(msg)
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
    def change_username(self, name: str) -> int:
        """Устанавливает имя, если оно не пустое."""
        if not isinstance(name, str):
            msg = f"name должен быть str, а не {type(name).__name__}."
            raise TypeError(msg)
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
        """Выводит информацию о пользователе (без пароля)."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.strftime(
                User.__DATE_TIME_FORMAT,
            ),
        }

    # Самый простой способ для сериализации json
    def to_dict(self) -> dict:
        """Возвращает объект в виде словаря для сериализации.

        Returns:
            dict: словарь для сериализации

        """
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.strftime(
                User.__DATE_TIME_FORMAT,
            ),
            "hashed_password": self._hashed_password,
            "salt": self._salt,
        }

    @classmethod
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
            Self: User

        """
        if not isinstance(user_dict, dict):
            msg = f"user_dict должен быть dict, а не {type(user_dict).__name__}."
            raise TypeError(msg)

        try:
            return User(
                user_id=int(user_dict["user_id"]),
                username=str(user_dict["username"]),
                hashed_password=str(user_dict["hashed_password"]),
                salt=user_dict["salt"],
                registration_date=datetime.strptime(
                    user_dict["registration_date"],
                    User.__DATE_TIME_FORMAT,
                ).astimezone(tz=User.__TIMEZONE),
            )
        except (KeyError, ValueError) as e:
            msg = "user_dict имеет некорректный формат"
            raise ValueError(msg) from e
